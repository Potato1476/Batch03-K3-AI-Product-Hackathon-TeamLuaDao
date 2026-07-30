# CHẮN Gateway — public /v1 API

API Gateway + Detection Engine (L2–L4) + Lookup Service. Đây là mặt phẳng bảo
đảm tính tương đương: Web PWA, Android và Zalo OA gọi **cùng tập endpoint** và
nhận **cùng cấu trúc phản hồi**.

**Cài đặt và chạy: xem [SETUP.md](SETUP.md).**

```
   WEB/PWA        ANDROID APP       ZALO OA
   [L0+L1 on device — Rule Bundle dùng chung]
        └───────────────┼───────────────┘
                        │ HTTPS
              ┌─────────▼─────────┐
              │  GATEWAY :8000    │  auth · rate limit · schema validate
              └─────────┬─────────┘
        ┌───────────────┼───────────────┐
     LOOKUP        DETECTION        (GUARDIAN)
     k-anon        L2 redact         giai đoạn 3
                   L3 classify
                   L4 aggregate
        └───────────────┼───────────────┘
              PostgreSQL + pgvector · Redis
```

## Endpoint

| Endpoint | Method | Auth | Mục đích |
|---|---|:--:|---|
| `/v1/analyze` | POST | ✔ | phân tích một mẩu nội dung |
| `/v1/ocr` | POST | ✔ | ảnh → text, client tự gọi tiếp `/analyze` |
| `/v1/lookup/{account,phone,url}` | GET | ✔ | tra theo prefix hash (k-anonymity) |
| `/v1/report` | POST | ✔ | báo cáo TK/SĐT/link lừa đảo |
| `/v1/rules/bundle` | GET | — | tải Rule Bundle cho L0+L1 |
| `/v1/feedback` | POST | ✔ | đánh dấu kết quả đúng/sai |
| `/v1/devices/token` | POST | — | cấp device token |
| `/v1/devices/token/rotate` | POST | ✔ | xoay vòng token |

`/v1/guardian/pair` và `/v1/guardian/alert` **chưa hiện thực** — theo lộ trình
§13 chúng thuộc giai đoạn 3. Nhưng các bảng `guardians`, `guardian_alerts` và
`guardian_pair_codes` đã có trong migration, kèm ràng buộc
`consent_source = 'protected_device'`: bất biến I5 phải được thực thi ở tầng dữ
liệu trước khi ai đó viết endpoint.

`/v1/devices/token*` không nằm trong bảng §7. Nó cần thiết để bảng đó dùng được:
§7.3 yêu cầu xác thực bằng device token có thời hạn và xoay vòng, §8 định nghĩa
bảng `devices`, nhưng không có gì cấp token. Đây là bước bootstrap còn thiếu.

## Đường đi của một request `/v1/analyze`

```
auth + rate limit
   ↓
schema validate (extra="forbid")
   ↓
L2 redact  ──────────────► <OTP> <ACCOUNT> <PHONE> <NAME> <AMOUNT:trieu> <URL>
   ↓                       hash TK/SĐT/URL giữ riêng cho Lookup
   ├─ có OTP? ────────────► DỪNG: high, không gọi model (I1)
   ↓
blocklist lookup (hash server tự tính)
   ↓
L3 classify ─┬─ local: chan_ml (mặc định)      ─┐
             ├─ llm: Claude structured JSON     ├─ song song với
             └─ ensemble: max-pool cả hai       ─┘  pgvector similarity
   ↓
L4 aggregate ──────────► chan_ml.policy.aggregate_risk (KHÔNG viết lại công thức)
   ↓
shape response ────────► analysis_id · hotline · actions · versions
   ↓
persist metadata ──────► signals ĐÃ BỎ evidence (I2)
```

Điểm quan trọng: quyết định risk **không** được đưa ra ở đây. Nó được uỷ cho
`chan_ml.policy.aggregate_risk` — cùng một hàm mà model và training API dùng —
nên một ngưỡng chỉ có thể bị đổi ở đúng một chỗ.

## Sáu bất biến được thực thi ở đâu

| # | Bất biến | Thực thi bằng |
|---|---|---|
| I1 | OTP không rời thiết bị | `redact_l2` + short-circuit trước khi gọi model |
| I2 | Không lưu nội dung | bảng `analyses` không có cột text + CHECK từ chối `evidence` |
| I3 | ~95% tin không rời thiết bị | cửa lọc L1 khai báo trong Rule Bundle |
| I4 | Server không biết tra cứu gì | schema chỉ nhận `^[0-9a-f]{5}$`; prefix không vào log |
| I5 | Không giám sát bí mật | CHECK `consent_source = 'protected_device'` |
| I6 | Không có nhãn "An toàn" | enum `risk` + CHECK ở DB + test fuzz |

Mỗi bất biến có test tương ứng trong [`tests/test_invariants.py`](tests/test_invariants.py).

## Cấu trúc

```
src/chan_api/
├─ main.py            app + middleware + healthz/readyz + model poller
├─ config.py          AppConfig.from_environment()
├─ deps.py            DI providers (test override được từng mảnh)
├─ auth.py            device token: cấp, xác thực, xoay vòng
├─ ratelimit.py       Redis → Postgres → in-process (giảm cấp, không fail)
├─ logging_safe.py    allowlist field; nội dung KHÔNG thể vào log
├─ schemas.py         hợp đồng §7, extra="forbid"
├─ repository.py      psycopg3 + pool, không import training plane
├─ model_registry.py  đọc model_versions, verify SHA-256, hot-swap
├─ pipeline.py        L2 → OTP → blocklist → L3 → L4 → shape
├─ rules.py           Rule Bundle + map local_signals (có trần)
├─ hotlines.py        verified_hotline theo cơ quan bị mạo danh
├─ l3/                base · local · llm · similarity
├─ ocr/               base · stub · paddle
└─ routers/           analyze · ocr · lookup · report · rules · feedback · devices
```

## Ghi chú thiết kế

**`logging_safe` đảo ngược mặc định.** Không có cách nào truyền một chuỗi tự do
vào log — `log_event(event, **fields)` chỉ nhận field trong allowlist, và filter
gắn ở **logger** (không phải handler) nên thêm sink mới cũng không vượt qua được.
Ghi log là cách rò rỉ dễ xảy ra nhất vì nó chỉ là một dòng trông vô hại.

**Tầng L3 là interface, không phải điều kiện if.** `chan_ml` local là mặc định
vì nó offline, chi phí 0 và p50 ~2ms; LLM là provider thay thế theo §5. Cả hai
trả về cùng `Classification`, nên L4 không biết và không cần biết ai chấm điểm.

**`local_signals` không phải 8 dấu hiệu.** Đây là từ vựng riêng của L1
(`url_shortened`, `apk_link`, …). Rule Bundle map chúng sang taxonomy kèm mức
cộng có trần (`MAX_SINGLE_BOOST`, `MAX_TOTAL_BOOST`) — L1 chạy trên máy người
dùng kiểm soát, nên một client bị sửa không được tự quyết định điểm.

**Không có nhãn trấn an, ở mọi tầng.** `unknown` nghĩa là "chưa phát hiện dấu
hiệu", không phải "an toàn". Một lời trấn an sai chuyển trách nhiệm phán đoán từ
người dùng sang hệ thống đúng lúc hệ thống có thể sai.
