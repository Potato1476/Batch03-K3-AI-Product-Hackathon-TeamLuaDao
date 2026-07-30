# CHẮN — Tài liệu API

> Hợp đồng API của hệ thống CHẮN. Nguồn sự thật về kiến trúc là
> [`CHAN-ARCHITECTURE.md`](CHAN-ARCHITECTURE.md); tài liệu này mô tả **bề mặt API
> đang chạy trong code**.
>
> Mọi request/response trong tài liệu được **chụp từ hệ thống thật** đang chạy
> (4 service + PostgreSQL 16 + Redis 7, model `ml-0.3.0`), không phải ví dụ minh
> hoạ. Ngày kiểm chứng: 2026-07-30.

---

## Mục lục

- [1. Bản đồ service](#1-bản-đồ-service)
- [2. Xác thực](#2-xác-thực)
- [3. Quy ước chung](#3-quy-ước-chung)
- [4. Public API — Gateway :8000](#4-public-api--gateway-8000)
- [5. Public Lookup — Intel :8002](#5-public-lookup--intel-8002)
- [6. Internal — Detection :8003](#6-internal--detection-8003)
- [7. Internal — Intel :8002](#7-internal--intel-8002)
- [8. Internal — Training :8001](#8-internal--training-8001)
- [9. Bảng mã lỗi](#9-bảng-mã-lỗi)
- [10. Cấu hình](#10-cấu-hình)
- [11. Bất biến mà client phải tôn trọng](#11-bất-biến-mà-client-phải-tôn-trọng)

---

## 1. Bản đồ service

```
                    Web PWA · Android · Zalo OA
                              │
                              │ HTTPS (chỉ gọi tới đây)
                    ┌─────────▼──────────┐
                    │  GATEWAY   :8000   │  public edge
                    │  device auth ·     │  CORS · rate limit
                    │  Rule Bundle · OCR │  hotline · lưu metadata
                    └──┬────────┬────────┘
          ┌────────────┘        └──────────────┐
          ▼                                    ▼
┌──────────────────┐                 ┌────────────────────┐
│ DETECTION  :8003 │                 │   INTEL     :8002  │
│ L2 redact        │────k-anon──────►│ blocklist (hash)   │
│ OTP short-circuit│    lookup       │ k-anon lookup      │
│ model L3 + L4    │                 │ feed connectors    │
└────────┬─────────┘                 │ quarantine+review  │
         │ lấy model active           └────────────────────┘
         ▼
┌──────────────────┐
│ TRAINING   :8001 │  quarantine → review → retrain → promote
└──────────────────┘
         │
   PostgreSQL + pgvector · Redis
```

| Service | Port | Public? | Sở hữu |
|---|---|---|---|
| **Gateway** (`chan-gateway`) | 8000 | ✔ toàn bộ `/v1/*` | device token, CORS, rate limit, Rule Bundle, OCR, hotline, bảng `analyses`/`feedback` |
| **Detection** (`chan-detection-api`) | 8003 | ✖ nội bộ | L2 ẩn danh hóa, chặn OTP, model inference, tổng hợp L4 |
| **Intel** (`chan-intel-api`) | 8002 | ⚠ chỉ `/v1/lookup/*` | blocklist dạng hash, k-anonymity, feed ngoài, quarantine + review |
| **Training** (`chan-training-api`) | 8001 | ✖ nội bộ | kho kịch bản, retrain, promotion gate, model registry |

**Gateway không nạp model và không chạy L2–L4.** Nó chuyển tiếp tới Detection.
**Detection không có database riêng** — nó hỏi Intel qua chính giao thức
k-anonymity mà client dùng, nên ngay cả giữa hai service nội bộ, Intel cũng
không biết Detection đang tra số nào.

---

## 2. Xác thực

| Bề mặt | Cơ chế | Header |
|---|---|---|
| Gateway `/v1/*` | device token (Bearer), hết hạn + xoay vòng được | `Authorization: Bearer <token>` |
| Gateway `/v1/rules/bundle` | **không cần** | — |
| Gateway `/v1/devices/token` | **không cần** (bootstrap, giới hạn theo IP) | — |
| Intel `/v1/lookup/*` | **không cần** | — |
| Detection `/internal/*` | shared secret | `X-CHAN-Detection-Key: <key>` |
| Intel `/internal/*` | shared secret, nhiều key có danh tính | `X-CHAN-Intel-Key: <key>` |
| Training `/internal/*` | shared secret, nhiều key có danh tính | `X-CHAN-Training-Key: <key>` |

Không có tài khoản, không có mật khẩu, **không dùng số điện thoại làm định danh**
(§7.3). Server chỉ lưu SHA-256 của device token.

Với Intel và Training, mỗi key có một **id danh tính** (ví dụ `gateway`,
`analyst`). Id đó được ghi vào `submitted_by` / `reviewed_by` và dùng để thực thi
quy tắc **bốn mắt**: người duyệt phải khác người gửi. Dùng chung một key cho cả
hai vai sẽ luôn nhận `404 quarantined_report_not_found`.

---

## 3. Quy ước chung

### Enum `risk` — chỉ ba giá trị

```
high     "Nhiều dấu hiệu lừa đảo"
medium   "Cần kiểm tra thêm"
unknown  "Chưa phát hiện dấu hiệu"
```

**Không có `safe`/`ok`/`clean`.** `unknown` nghĩa là "chưa phát hiện dấu hiệu",
**không** phải "an toàn" — client tuyệt đối không được diễn giải thành lời trấn
an. Đây là bất biến I6, được thực thi cả ở enum, ở CHECK trong database, và ở test.

### 8 mã dấu hiệu (`SignalOut.code`)

| Mã | Ý nghĩa | Trọng số |
|---|---|---|
| `mao_danh_tham_quyen` | mạo danh cơ quan có thẩm quyền | 0.20 |
| `yeu_cau_bi_mat` | yêu cầu giữ bí mật với người thân | 0.20 |
| `ap_luc_thoi_gian` | tạo áp lực thời gian | 0.15 |
| `tk_ca_nhan` | chuyển tiền vào tài khoản cá nhân | 0.15 |
| `cai_app_ngoai` | cài ứng dụng ngoài cửa hàng | 0.15 |
| `loi_ich_bat_thuong` | hứa lợi ích bất thường | 0.08 |
| `chuyen_kenh` | đề nghị chuyển kênh liên lạc | 0.07 |
| `yeu_cau_otp` | yêu cầu OTP / mã xác thực | **ghi đè → high** |

Chỉ dấu hiệu có `confidence >= 0.50` được trả về. Khi `risk = unknown`,
`signals` luôn là `[]`.

### Định dạng lỗi

Lỗi nghiệp vụ — một mã máy đọc được, không bao giờ chứa nội dung người dùng:

```json
{ "detail": "invalid_device_token" }
```

Lỗi validate schema (422) — chỉ vị trí và loại lỗi, **không echo giá trị** (một
payload bị từ chối có thể chứa OTP):

```json
{ "detail": [ { "location": ["body", "source"], "type": "literal_error" } ] }
```

### Header phản hồi

| Header | Ở đâu | Ý nghĩa |
|---|---|---|
| `X-Request-Id` | mọi response của Gateway | id ngẫu nhiên để đối chiếu log |
| `ETag` | `/v1/rules/bundle` | SHA-256 (32 hex đầu) của bundle |
| `X-CHAN-Bundle-Version` | `/v1/rules/bundle` | ví dụ `rb-2026-07-30` |

---

## 4. Public API — Gateway :8000

| Method | Path | Auth | Status |
|---|---|:--:|---|
| POST | `/v1/devices/token` | — | 201 |
| POST | `/v1/devices/token/rotate` | ✔ | 201 |
| POST | `/v1/analyze` | ✔ | 200 |
| POST | `/v1/ocr` | ✔ | 200 |
| GET | `/v1/lookup/{kind}` | ✔ | 200 |
| POST | `/v1/report` | ✔ | **202** |
| GET | `/v1/rules/bundle` | — | 200 / 304 |
| POST | `/v1/feedback` | ✔ | 200 |
| GET | `/healthz` `/readyz` | — | 200 / 503 |

`/v1/guardian/pair` và `/v1/guardian/alert` trong §7 tài liệu kiến trúc **chưa
được hiện thực** (lộ trình Giai đoạn 3). Các bảng `guardians`,
`guardian_alerts`, `guardian_pair_codes` đã tồn tại kèm ràng buộc
`consent_source = 'protected_device'`.

---

### POST /v1/devices/token

Cấp device token lần đầu. Không cần auth; giới hạn 10 lần/giờ theo IP.

**Request**

```json
{ "platform": "web", "push_token": null }
```

| Field | Type | Bắt buộc | Ghi chú |
|---|---|:--:|---|
| `platform` | `web` \| `android` \| `zalo_oa` | ✔ | |
| `push_token` | string ≤512 | | để nhận Web Push / FCM |

**Response 201** *(thật)*

```json
{
  "device_id": "dev_0f719fc3045e2663bb016df9",
  "token": "-XhhO-VvEPtMbIVjbxZgczUBOpSFdMD4xhzfZA9k5Ds",
  "expires_at": "2026-10-28T08:08:43.758479+00:00",
  "note": "Token chỉ được trả về một lần. Lưu lại trên thiết bị."
}
```

`token` chỉ xuất hiện **một lần duy nhất**. Server lưu SHA-256, nên mất token là
phải cấp lại. Mặc định hết hạn sau 90 ngày.

### POST /v1/devices/token/rotate

Cấp token kế nhiệm và **thu hồi token đang dùng**. Cùng shape response. Token cũ
lập tức trả `401 invalid_device_token`.

---

### POST /v1/analyze

Phân tích một mẩu nội dung. Đây là endpoint trung tâm.

**Request**

```json
{
  "text": "Toi la can bo thue, anh chuyen 20 trieu vao 19001234567890 truoc 17h hom nay, khong noi voi ai ke ca gia dinh",
  "source": "web",
  "input_mode": "manual",
  "app_package": null,
  "local_signals": [],
  "truncated": false,
  "locale": "vi-VN"
}
```

| Field | Type | Bắt buộc | Ghi chú |
|---|---|:--:|---|
| `text` | string 1–4000 | ✔ | nội dung cần phân tích |
| `source` | `web` \| `android` \| `zalo_oa` | ✔ | **chỉ dùng cho analytics, không đổi kết quả** |
| `input_mode` | `manual` \| `share` \| `notification` \| `sms_scan` | ✔ | |
| `app_package` | string ≤128 | | chỉ với `android` + `notification` |
| `local_signals` | string[] ≤16 | | kết quả L1 trên thiết bị — xem bên dưới |
| `truncated` | bool | | nội dung bị OS cắt ngắn |
| `locale` | string ≤16 | | mặc định `vi-VN` |

Schema dùng `extra="forbid"`: gửi field lạ → 422.

#### `local_signals` — từ vựng riêng của L1

Đây **không phải** 8 mã dấu hiệu. Đó là kết quả tầng luật chạy trên thiết bị, tên
được định nghĩa trong Rule Bundle (`l1.local_signals`):

```
url_shortened · apk_link · otp_pattern · blocklist_hit
authority_claim · secrecy_request · time_pressure
channel_switch · unusual_reward · truncation_marker
```

Rule Bundle map mỗi tên sang một mã dấu hiệu kèm mức cộng **có trần**
(≤0.30 cho một signal, ≤0.45 tổng cộng): L1 chạy trên máy người dùng kiểm soát,
nên một client bị sửa không được tự quyết định điểm. Gửi tên không có trong
bundle → `422 unknown_local_signal` (nghĩa là client và server lệch phiên bản
bundle).

**Response 200** *(thật, tin mạo danh cán bộ thuế)*

```json
{
  "analysis_id": "an_347d0869c46b",
  "risk": "high",
  "score": 1.0,
  "signals": [
    { "code": "yeu_cau_bi_mat",      "confidence": 1.0,    "evidence": "Toi la can bo thue, anh chuyen <AMOUNT:trieu> vao <ACCOUNT> truoc 17h hom nay, khong noi voi ai ke ca gia dinh" },
    { "code": "tk_ca_nhan",          "confidence": 1.0,    "evidence": "..." },
    { "code": "mao_danh_tham_quyen", "confidence": 0.6081, "evidence": "..." },
    { "code": "ap_luc_thoi_gian",    "confidence": 1.0,    "evidence": "..." },
    { "code": "chuyen_kenh",         "confidence": 0.5657, "evidence": "..." }
  ],
  "explanation": "Người gửi yêu cầu giữ bí mật với gia đình. Tin nhắn yêu cầu chuyển tiền vào tài khoản cá nhân. Tin nhắn tự nhận là cơ quan hoặc tổ chức có thẩm quyền.",
  "questions": [
    "Tại sao việc này lại không được nói với người thân?",
    "Tại sao tiền lại chuyển vào tài khoản cá nhân?"
  ],
  "verified_hotline": { "name": "Tổng cục Thuế", "number": "19008888" },
  "actions": ["report", "share_to_guardian", "lookup_account"],
  "engine_version": "ml-0.3.0",
  "rule_bundle_version": "rb-2026-07-30"
}
```

| Field | Ghi chú |
|---|---|
| `analysis_id` | `an_` + 12 hex. Dùng cho `/v1/feedback` |
| `score` | 0–1, đã áp trọng số §6 |
| `signals[].evidence` | **đoạn trích từ text ĐÃ ẩn danh hóa** — chú ý các placeholder `<ACCOUNT>`, `<AMOUNT:trieu>` |
| `explanation` | tiếng Việt cho người 60 tuổi. Không dùng "phishing", "malware" |
| `questions` | 0–2 câu người dùng có thể hỏi lại kẻ gọi |
| `verified_hotline` | luôn có mặt, `null` khi không áp dụng. Chỉ gợi ý khi có dấu hiệu mạo danh |
| `actions` | tập con của `report`, `share_to_guardian`, `lookup_account` |
| `engine_version` | phiên bản engine (`ml-*`). Cùng `rule_bundle_version` phục vụ parity test |

> `verified_hotline` là biện pháp hoá giải kịch bản mạo danh: thay vì tin số gọi
> đến, người dùng được đưa một số **họ tự gọi**. Vì vậy nó chỉ xuất hiện khi tin
> nhắn thật sự nhận là cơ quan — gắn hotline vào mọi kết quả sẽ dạy người dùng
> phớt lờ nó.

**Ba trường hợp đặc biệt** *(đều là output thật)*

<details>
<summary>Có OTP → <code>high</code>, quyết định mà không gọi model (I1)</summary>

```json
{
  "risk": "high",
  "score": 1.0,
  "signals": [{ "code": "yeu_cau_otp", "confidence": 1.0, "evidence": "" }],
  "explanation": "Tin nhắn này đang hỏi mã xác nhận của bạn. Đừng đọc mã cho bất kỳ ai."
}
```

`evidence` rỗng **có chủ ý**: trích dẫn lại sẽ echo đúng những chữ số vừa bị xoá.
</details>

<details>
<summary>Số tài khoản đã bị báo cáo → ghi đè cứng thành <code>high</code></summary>

```json
{
  "risk": "high",
  "score": 1.0,
  "explanation": "Số nhận tiền hoặc liên kết này đã bị người khác báo cáo là lừa đảo. Đừng tiếp tục giao dịch.",
  "actions": ["report", "share_to_guardian", "lookup_account"]
}
```
</details>

<details>
<summary>Tin hợp pháp → <code>unknown</code>, KHÔNG BAO GIỜ "an toàn" (I6)</summary>

```json
{
  "risk": "unknown",
  "score": 0.03093,
  "signals": [],
  "explanation": "Chưa phát hiện dấu hiệu.",
  "actions": [],
  "verified_hotline": null
}
```
</details>

**Lỗi**

| Status | `detail` | Khi nào |
|---|---|---|
| 401 | `device_token_required` / `invalid_device_token` | thiếu / sai token |
| 422 | `unknown_local_signal` | client gửi local signal không có trong bundle |
| 422 | *(mảng)* | schema sai |
| 429 | `rate_limited` | quá 20 lần/phút/device hoặc 60 lần/phút/IP |
| 503 | `detection_engine_unavailable` | Detection lỗi hoặc chưa nạp model |
| 503 | `rule_bundle_unavailable` | không đọc được Rule Bundle |

---

### GET /v1/lookup/{kind} — k-anonymity

`kind` ∈ `account` \| `phone` \| `url`.

**Giao thức bốn bước (§7):**

```
1. client: h = SHA256(normalize(giá_trị))
2. client: GET /v1/lookup/account?prefix=<5 hex đầu của h>
3. server: trả TOÀN BỘ cụm hash cùng prefix
4. client: tự đối chiếu h trong cụm, tại chỗ
```

| Param | Bắt buộc | Ràng buộc |
|---|:--:|---|
| `prefix` | ✔ | `^[0-9a-f]{5}$` — **đúng 5 ký tự hex thường** |

> Endpoint này **không nhận giá trị thô**. `?value=19001234567890` → 422.
> Prefix 4 hoặc 6 ký tự → 422. Chữ in hoa → 422. Đây là bất biến I4 được thực
> thi bằng kiểu dữ liệu, không bằng quy ước. Prefix cũng **không bao giờ được
> ghi vào log** — ghi lại nhiều lần sẽ dần thu hẹp không gian tra cứu.

**Response 200** *(thật, sau khi một số TK được duyệt)*

```json
{
  "prefix": "5497e",
  "kind": "account",
  "hashes": [
    {
      "hash": "5497e3471fe3a04bfd87e128956496b7f459cbbf013dcf5c72db44357f1956c0",
      "report_cnt": 2,
      "first_seen": "2026-07-30T08:14:47.941277Z",
      "last_seen": "2026-07-30T08:15:04.236918Z",
      "origin": "community_reviewed"
    }
  ],
  "cluster_size": 1,
  "bundle_version": "rb-2026-07-30",
  "no_match_message": "Chưa có báo cáo về số tài khoản này."
}
```

Khi không trùng, hiển thị `no_match_message`. **Không được nói "an toàn"** —
không có báo cáo chỉ nghĩa là chưa ai báo cáo.

---

### POST /v1/report

Báo cáo một số tài khoản / số điện thoại / đường liên kết lừa đảo.

**Request** — client hash trước, server không nhận giá trị thô:

```json
{
  "kind": "account",
  "value_sha256": "5497e3471fe3a04bfd87e128956496b7f459cbbf013dcf5c72db44357f1956c0",
  "analysis_id": "an_347d0869c46b"
}
```

**Response 202** *(thật)*

```json
{ "kind": "account", "report_cnt": 0, "accepted": true }
```

> **202, không phải 201, và `report_cnt` là 0.** Báo cáo đi vào **quarantine của
> Intel**, chưa vào blocklist. Nó chỉ có hiệu lực sau khi được review và đủ số
> báo cáo độc lập (mặc định 2). Gateway **không** tự tăng số đếm blocklist và
> **không** để một báo cáo chưa duyệt ảnh hưởng tới detection — nếu không, một
> thiết bị đơn lẻ có thể đầu độc blocklist của mọi người.

| Status | `detail` |
|---|---|
| 422 | `value_sha256` không phải 64 hex |
| 429 | `rate_limited` (5/phút) hoặc `daily_report_limit` (30/ngày) |
| 503 | `intel_service_unavailable` |

---

### GET /v1/rules/bundle

Tải Rule Bundle cho L0+L1 trên thiết bị. **Không cần auth** — client cần tầng
luật trước khi có token, và phải chạy được khi offline.

```bash
curl -s -D - localhost:8000/v1/rules/bundle -o bundle.json
# ETag: "dd3acf884a6022e9ca4042adb503c59a"
# Cache-Control: public, max-age=3600
# X-CHAN-Bundle-Version: rb-2026-07-30

curl -o /dev/null -w '%{http_code}\n' localhost:8000/v1/rules/bundle \
  -H 'If-None-Match: "dd3acf884a6022e9ca4042adb503c59a"'      # → 304
```

Trả về **nguyên văn byte-for-byte** `codebase/rules/bundle.json`. Bản TypeScript
(Web) và bản Kotlin (Android) đọc **cùng một file này**, nên tầng L1 của hai nền
tảng không thể lệch nhau — tương đương được bảo đảm bằng **dữ liệu**, không bằng
kỷ luật lập trình.

Cấu trúc: `l0` (Unicode/teencode/ký tự vô hình), `l1.otp_block` (regex chặn OTP
tại chỗ), `l1.local_signals` (map sang taxonomy + mức cộng), `l1.gate` (cửa lọc
~5%), `l1.identifier_extraction`, `watchlist_packages`, `risk_labels`,
`forbidden_labels`, `actions`.

---

### POST /v1/feedback

**Request**

```json
{
  "analysis_id": "an_347d0869c46b",
  "verdict": "correct",
  "contribute": false,
  "redacted_text": null,
  "signals": []
}
```

| Field | Ghi chú |
|---|---|
| `verdict` | `correct` \| `false_positive` \| `false_negative` |
| `contribute` | **opt-in**. Mặc định `false` → chỉ lưu verdict |
| `redacted_text` | chỉ khi `contribute=true`; phải đã qua L2 |
| `signals` | nhãn người dùng đề xuất, không trùng lặp |

**Response 200**: `{ "recorded": true, "contributed": false }`

Mặc định **không có nội dung nào được lưu**. Chỉ khi người dùng chủ động bấm đồng
ý góp dữ liệu thì `redacted_text` mới được chuyển sang Training API dưới dạng
`rights_basis=explicit_consent`, và nó vào **quarantine chờ người duyệt** trước
khi ảnh hưởng tới model.

Text chưa ẩn danh bị từ chối và **không bị echo lại**:

```json
{ "detail": "content_failed_redaction_check" }
```

| Status | `detail` |
|---|---|
| 404 | `analysis_not_found` |
| 422 | `content_failed_redaction_check` |

---

### POST /v1/ocr

`multipart/form-data`, field `image`. Chấp nhận `image/png`, `image/jpeg`,
`image/webp`, tối đa 6 MB.

**Response 200**: `{ "text": "...", "provider": "tesseract", "next_step": "POST /v1/analyze" }`

Trả text rồi **dừng**. Client tự gọi `/v1/analyze` — server không tự nối chuỗi,
để ảnh và phân tích không nằm trong cùng một request.

Docker Compose dùng Tesseract `vie+eng` tự host và truyền ảnh qua stdin, không
ghi file tạm. Cấu hình source mặc định vẫn là `stub` và **báo lỗi thật thà**
thay vì trả text rỗng (text rỗng sẽ khiến client hiển thị "Chưa phát hiện dấu
hiệu" cho một ảnh chưa từng được đọc):

| Status | `detail` |
|---|---|
| 413 | `image_too_large` |
| 415 | `unsupported_image_type` |
| 422 | `empty_image` |
| 501 | `ocr_provider_not_configured`, `ocr_provider_not_installed` |
| 502 | `ocr_timeout`, `ocr_engine_failed`, `ocr_no_text_detected` |

---

### GET /healthz · GET /readyz

```json
GET /healthz  →  200 {"status":"ok"}
GET /readyz   →  200 {"status":"ready"}
```

`/healthz` chỉ nói tiến trình còn sống → dùng cho **liveness probe**.
`/readyz` chỉ ready khi **Detection reachable** → dùng cho **readiness probe**;
khi không, trả 503 và `/v1/analyze` sẽ không dùng được.

---

## 5. Public Lookup — Intel :8002

Intel expose `/v1/lookup/{kind}` **không cần auth**. Gateway proxy tới đây; client
có thể gọi trực tiếp nếu được route công khai. Khác biệt so với response của
Gateway: Intel trả **`suffix`** (đã bỏ prefix) và một **bậc độ tin cậy**.

```json
{
  "prefix": "5497e",
  "items": [
    {
      "suffix": "3471fe3a04bfd87e128956496b7f459cbbf013dcf5c72db44357f1956c0",
      "report_count": 2,
      "first_seen": "2026-07-30T08:14:47.941277Z",
      "last_seen": "2026-07-30T08:15:04.236918Z",
      "confidence": "community_reviewed"
    }
  ],
  "message": "matched_locally_only"
}
```

Client ghép `prefix + suffix` rồi so với hash của mình, **tại chỗ**.

| `confidence` | Nghĩa |
|---|---|
| `feed_listed` | có trong feed ngoài, chưa xác minh |
| `community_reviewed` | đủ số báo cáo người dùng độc lập đã được duyệt |
| `verified` | đã xác minh nội bộ |
| `partner_verified` | đối tác (ngân hàng / cơ quan) xác nhận |

Độ dài prefix do `CHAN_LOOKUP_PREFIX_LENGTH` quyết định (2–5, mặc định 5). Sai độ
dài → `400 lookup_prefix_length_mismatch`.

---

## 6. Internal — Detection :8003

> Không expose ra internet. Header `X-CHAN-Detection-Key`.

### POST /internal/v1/analyze

Đây là nơi L2–L4 thực sự chạy. Thứ tự **không được đổi**:

```
L2 redact_l2(text)
   ↓  <OTP> <ACCOUNT> <PHONE> <NAME> <AMOUNT:trieu> <URL>
   ↓  hash TK/SĐT/URL giữ riêng cho lookup
kiểm tra blocklist qua Intel (k-anon prefix, không gửi giá trị)
   ↓
nếu có OTP → DỪNG: high, không gọi model (I1)
   ↓
model inference: 8 dấu hiệu + scam_confidence
   ↓
L4: chan_ml.policy.aggregate_risk(...)
```

**Request** — như `/v1/analyze` nhưng nhận thêm và mở rộng enum:

| Field | Khác với public |
|---|---|
| `text` | min 8 ký tự (public: 1) |
| `source` | thêm `internal` |
| `input_mode` | thêm `upload`, `share_target`, `sms`, `forward` |
| `app_package` | ≤255 (public: 128) |
| `rule_bundle_version` | Gateway truyền xuống để ghi vào kết quả |

**Response 200** *(thật)* — thêm ba field mà public không có:

```json
{
  "analysis_id": "an_29ff64a68eb9",
  "model_version": "ml-0.3.0-local",
  "engine_version": "ml-0.3.0",
  "risk": "high",
  "score": 1.0,
  "scam_confidence": 0.9936,
  "signals": [ { "code": "yeu_cau_bi_mat", "confidence": 1.0, "evidence": "..." } ],
  "explanation": "...",
  "questions": ["..."],
  "actions": ["report", "share_to_guardian", "verify_official_channel", "lookup_account"],
  "verified_hotline": null,
  "rule_bundle_version": "rb-2026-07-30",
  "truncated": false,
  "blocklist_match": false
}
```

| Field nội bộ | Ghi chú |
|---|---|
| `model_version` | phiên bản **artifact** đang nạp (khác `engine_version` là phiên bản **code**) |
| `scam_confidence` | classifier ý đồ toàn câu, 0–1. Chỉ là prior có trọng số giới hạn `α`, **không tự tạo nhãn `high`** |
| `blocklist_match` | số nhận tiền có trong blocklist → ghi đè cứng thành `high` |

Gateway **lọc bớt `actions`**: chỉ `report`, `share_to_guardian`,
`lookup_account` được trả ra ngoài. `verify_official_channel` ở ví dụ trên bị
loại — bề mặt public là danh sách đóng.

Công thức L4 hiện tại:

```
score = Σ(wᵢ × signalᵢ) + α × scam_confidence + β × similarity_max
α = 0.405 cho baseline ml-0.3.0
high: score ≥ 0.70 · medium: ≥ 0.35 · unknown: < 0.35
ghi đè cứng: yeu_cau_otp → high · blocklist → high · yeu_cau_bi_mat → ≥ medium
```

| Status | `detail` |
|---|---|
| 401 | `invalid_detection_api_key` |
| 422 | `content_failed_redaction_check` |
| 503 | `model_unavailable` |

`GET /healthz` → `{"status":"ok","model_version":"ml-0.3.0-local"}`, và **503
`model_unavailable`** khi chưa nạp được model. Detection lấy model active bằng
cách gọi Training API `/internal/v1/training/models/active`, tải artifact,
**verify SHA-256**, rồi hot-swap.

---

## 7. Internal — Intel :8002

> Header `X-CHAN-Intel-Key`. Mỗi key có id danh tính (ví dụ `gateway`, `analyst`).

### POST /internal/v1/intel/reports

Nạp tối đa 100 báo cáo. Gateway gọi endpoint này khi người dùng bấm báo cáo.

```json
{
  "items": [
    {
      "kind": "account",
      "indicator_hash": "5497e34...1956c0",
      "reporter_hash": "f5b5cbd...eafe",
      "evidence_hash": null,
      "consented": true
    }
  ]
}
```

| Field | Ràng buộc |
|---|---|
| `indicator_hash` | đúng 64 hex — SHA-256 của giá trị đã normalize |
| `reporter_hash` | đúng 64 hex — `SHA256("chan:reporter:v1:" + device_id)`. Cho phép đếm báo cáo **độc lập** mà không lưu định danh thiết bị |
| `consented` | phải `true` (có CHECK ở database) |

**Response 202** *(thật)*

```json
{
  "accepted": 1,
  "items": [{ "id": "55d42cb0-6484-4396-9a80-4ca4d005ace1", "status": "quarantined", "duplicate": false }]
}
```

Mọi item bắt đầu ở `quarantined`. Dedup theo `(kind, hash, reporter_hash)`: cùng
một người báo cáo hai lần chỉ tính một.

### POST /internal/v1/intel/reports/{report_id}/review

```json
{ "decision": "approve", "review_reason": "verified_by_analyst" }
```

**Response 200** *(thật — hai lần duyệt liên tiếp)*

```json
{ "id": "3b7cb1b7-...", "status": "approved", "independent_approved_reports": 1, "activated": false }
{ "id": "55d42cb0-...", "status": "approved", "independent_approved_reports": 2, "activated": true }
```

Chỉ khi `independent_approved_reports` đạt `CHAN_USER_REPORT_THRESHOLD`
(mặc định **2**) thì `activated: true` và indicator mới xuất hiện trong
`/v1/lookup` với `confidence: community_reviewed`.

**Quy tắc bốn mắt** được thực thi ở tầng dữ liệu: người duyệt phải khác người
gửi, nếu không → `404 quarantined_report_not_found`.

### GET /internal/v1/intel/sources

```json
[
  { "name": "openphish",   "enabled": false, "rights_basis": "written_permission",   "update_interval_minutes": 720,  "last_success_at": null, "last_record_count": 0, "last_error_code": null },
  { "name": "phishtank",   "enabled": true,  "rights_basis": "commercial_api_terms", "update_interval_minutes": 60,   "last_success_at": null, "last_record_count": 0, "last_error_code": null },
  { "name": "phishvn",     "enabled": true,  "rights_basis": "cc_by_4_0",            "update_interval_minutes": null, "last_success_at": null, "last_record_count": 0, "last_error_code": null },
  { "name": "user_report", "enabled": true,  "rights_basis": "explicit_consent",     "update_interval_minutes": null, "last_success_at": null, "last_record_count": 0, "last_error_code": null }
]
```

`rights_basis` được ghi rõ cho từng nguồn: OpenPhish mặc định **tắt** vì cần văn
bản cho phép. Cơ sở pháp lý là dữ liệu vận hành, không phải ghi chú trong tài liệu.

**CLI**: `chan-intel-sync` (đồng bộ feed), `chan-intel-import` (nạp snapshot).

---

## 8. Internal — Training :8001

> Header `X-CHAN-Training-Key`. Client người dùng **không bao giờ** gọi trực tiếp.

| Method | Path | Mục đích |
|---|---|---|
| POST | `/internal/v1/training/scenarios` | nạp ≤100 kịch bản đã ẩn danh vào quarantine |
| POST | `/internal/v1/training/scenarios/{id}/review` | duyệt / từ chối một item |
| POST | `/internal/v1/training/retrain` | xếp hàng một lần train (idempotent) |
| GET | `/internal/v1/training/runs/{run_id}` | trạng thái + metrics của run |
| GET | `/internal/v1/training/models/active` | metadata + checksum model đang active |

**`GET /internal/v1/training/models/active`** *(thật)* — Detection dùng để nạp model:

```json
{
  "version": "ml-0.3.0-local",
  "artifact_uri": "/.../artifacts/chan-signal-model.joblib",
  "artifact_sha256": "b594f6c59e81f2f...",
  "metrics": { "phishing_recall": 0.997326, "legitimate_false_positive_rate": 0.002655 },
  "promoted_at": "..."
}
```

**`POST /internal/v1/training/scenarios`** — mỗi item cần `redacted_text`,
`signals`, `risk`, `is_phishing`, `origin`, `rights_basis`, `consented`,
`redaction_confirmed: true`. Điều kiện dễ sai:

- `risk` phải **khớp đúng** kết quả L4 tính từ `signals`, nếu không →
  `risk_does_not_match_l4_policy`;
- item không phải lừa đảo **phải có `signals` rỗng**;
- `rights_basis=explicit_consent` **bắt buộc** `consented=true`;
- `redacted_text` phải qua kiểm tra L2, và text bị từ chối **không bị echo lại**.

Model chỉ được promote khi qua **toàn bộ** cổng: golden set ≥130 bản ghi, recall
≥90%, FP <15%, không hồi quy quá 2 điểm phần trăm ở cả hai chỉ số.

Chi tiết: [`../codebase/api/README.md`](../codebase/api/README.md).

---

## 9. Bảng mã lỗi

### Gateway (public)

| Status | `detail` | Ý nghĩa |
|---|---|---|
| 401 | `device_token_required` | thiếu header `Authorization` |
| 401 | `invalid_device_token` | token sai / hết hạn / đã thu hồi (một mã duy nhất — phân biệt sẽ giúp kẻ tấn công biết đoán nào gần đúng) |
| 404 | `analysis_not_found` | `analysis_id` không tồn tại |
| 413 | `image_too_large` | ảnh > `CHAN_OCR_MAX_BYTES` |
| 415 | `unsupported_image_type` | không phải png/jpeg/webp |
| 422 | `unknown_local_signal` | client lệch phiên bản Rule Bundle |
| 422 | `content_failed_redaction_check` | text góp dữ liệu chưa ẩn danh |
| 422 | `empty_image` | file rỗng |
| 429 | `rate_limited` | vượt giới hạn phút |
| 429 | `daily_report_limit` | vượt số report/ngày |
| 501 | `ocr_provider_not_configured` | OCR đang ở chế độ stub |
| 502 | *(mã lỗi engine)* | OCR engine lỗi |
| 503 | `detection_engine_unavailable` | Detection lỗi / chưa có model |
| 503 | `intel_service_unavailable` | Intel không phản hồi |
| 503 | `rule_bundle_unavailable` | thiếu / sai Rule Bundle |
| 503 | `internal_service_error` | service nội bộ trả lỗi không phân loại được |

### Nội bộ

| Service | Status | `detail` |
|---|---|---|
| Detection | 401 / 422 / 503 | `invalid_detection_api_key` · `content_failed_redaction_check` · `model_unavailable` |
| Intel | 400 / 401 / 404 | `lookup_prefix_length_mismatch` · `missing_intel_api_key`, `invalid_intel_api_key` · `quarantined_report_not_found` |
| Training | 401 / 404 / 503 | `training_key_required`, `invalid_training_key` · `quarantined_scenario_not_found`, `training_run_not_found`, `active_model_not_found` · `training_api_not_configured` |

---

## 10. Cấu hình

**Gateway**

```bash
CHAN_DATABASE_URL=postgresql://chan:chan@localhost:5432/chan
CHAN_DETECTION_API_URL=http://localhost:8003
CHAN_DETECTION_API_KEY=<detection key>
CHAN_INTEL_API_URL=http://localhost:8002
CHAN_INTEL_API_KEY=<intel key>
CHAN_TRAINING_API_URL=http://localhost:8001     # tuỳ chọn, cho feedback contribute
CHAN_TRAINING_API_KEY=<training key>
CHAN_REDIS_URL=redis://localhost:6379/0         # trống = đếm trong tiến trình
CHAN_CORS_ORIGINS=http://localhost:3000
CHAN_RULES_DIR=                                 # trống = tự tìm codebase/rules
CHAN_GATEWAY_PORT=8000
CHAN_DEVICE_TOKEN_TTL_DAYS=90
CHAN_ANALYZE_PER_DEVICE_PER_MINUTE=20
CHAN_ANALYZE_PER_IP_PER_MINUTE=60
CHAN_LOOKUP_PER_DEVICE_PER_MINUTE=120
CHAN_REPORT_PER_DEVICE_PER_DAY=30
CHAN_OCR_PROVIDER=tesseract                     # stub | tesseract | paddle
CHAN_OCR_MAX_BYTES=6291456
CHAN_OCR_LANGUAGE=vie+eng
CHAN_OCR_TIMEOUT_SECONDS=20
CHAN_ANALYSES_RETENTION_DAYS=90
CHAN_ACCESS_LOG_RETENTION_DAYS=30
```

**Detection**

```bash
CHAN_DETECTION_API_KEY=<key gateway phải trình>
CHAN_TRAINING_API_URL=http://localhost:8001     # để lấy model active
CHAN_TRAINING_API_KEY=<training key>
CHAN_INTEL_API_URL=http://localhost:8002        # kiểm tra blocklist
CHAN_MODEL_POLL_SECONDS=60
```

**Intel**

```bash
CHAN_DATABASE_URL=...
CHAN_INTEL_API_KEYS=gateway=<key>,analyst=<key>   # id=secret, dùng cho bốn mắt
CHAN_LOOKUP_PREFIX_LENGTH=5                        # 2–5
CHAN_USER_REPORT_THRESHOLD=2                       # số báo cáo độc lập để activate
CHAN_PHISHTANK_APP_KEY=
CHAN_OPENPHISH_LICENSE_CONFIRMED=false
```

**Training**: xem [`../codebase/api/README.md`](../codebase/api/README.md).

Cài đặt và chạy từng bước: [`../codebase/gateway/SETUP.md`](../codebase/gateway/SETUP.md).

---

## 11. Bất biến mà client phải tôn trọng

| # | Bất biến | Nghĩa vụ của client |
|---|---|---|
| **I1** | OTP không rời thiết bị | L1 phải chặn OTP **tại chỗ** và không gọi `/v1/analyze`. Server chặn lần hai, nhưng đó là phòng thủ lớp hai, không phải lớp một |
| **I2** | Không lưu nội dung tin nhắn | Server chỉ lưu hash + mã dấu hiệu + điểm. Client đừng thiết kế tính năng dựa trên việc server còn giữ text |
| **I3** | ~95% tin nhắn không rời thiết bị | Tôn trọng `l1.gate` trong Rule Bundle; chỉ gọi API khi vượt ngưỡng |
| **I4** | Server không biết người dùng tra gì | **Chỉ** gửi 5 hex đầu. Đối chiếu hash đầy đủ ở phía client |
| **I5** | Không giám sát bí mật | Bật chế độ người bảo hộ phải xác nhận trên **máy người được bảo vệ** |
| **I6** | Không có nhãn "An toàn" | `unknown` phải hiển thị là "Chưa phát hiện dấu hiệu". Tuyệt đối không map sang "an toàn"/"ok" trong UI |

Thêm hai điều dành cho client:

- **Nội dung tin nhắn là dữ liệu không tin cậy.** Prompt phía server đã bọc nó
  trong thẻ phân định; client cũng không được nối nội dung vào chỉ thị nào.
- **`source` không đổi kết quả.** Cùng một tin gửi từ `web`, `android` hay
  `zalo_oa` phải cho `risk`, `score` và `signals` **trùng khớp** — đây là điều
  kiện kiểm thử tương đương bắt buộc (§11.3), không phải mong muốn.

---

## Phụ lục — sinh client type từ OpenAPI

Cả bốn service đều expose OpenAPI. Gateway có UI tại `/docs`.

```bash
curl -s localhost:8000/openapi.json > gateway-openapi.json
npx openapi-typescript gateway-openapi.json -o src/api/types.ts
```

Lấy schema mà không cần chạy server:

```bash
.venv/bin/python -c "
import json
from chan_api.main import create_app
print(json.dumps(create_app().openapi(), ensure_ascii=False, indent=2))
" > gateway-openapi.json
```
