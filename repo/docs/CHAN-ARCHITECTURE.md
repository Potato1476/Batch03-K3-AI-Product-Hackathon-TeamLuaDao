# CHẮN — Kiến trúc hệ thống (bản đặc cho agent)

> Trợ lý chống lừa đảo cho người lớn tuổi / người ít kinh nghiệm số.
> File này là nguồn sự thật duy nhất về kiến trúc. Đọc mục 0 trước khi sinh bất kỳ code nào.
> Phiên bản 1.0 · 2026-07-30 · bản đầy đủ cho người đọc: `kien-truc-he-thong-CHAN.docx`

---

## 0. Bất biến — KHÔNG được vi phạm

| # | Bất biến | Thực thi ở đâu |
|---|---|---|
| I1 | OTP / mã xác thực **không bao giờ** rời khỏi thiết bị | chặn cứng ở L1 (client) + lặp lại ở L2 (server) |
| I2 | **Không lưu** nội dung tin nhắn ở server | bảng `analyses` không có cột chứa text |
| I3 | ~95% tin nhắn không rời thiết bị | cửa lọc L1 quyết định có gọi API hay không |
| I4 | Server không biết người dùng tra cứu gì | k-anonymity theo prefix hash cho mọi endpoint `lookup` |
| I5 | Không giám sát bí mật | bật guardian phải xác nhận trên máy người được bảo vệ; alert không chứa nội dung |
| I6 | **Không có nhãn "An toàn"** | chỉ có `high` / `medium` / `unknown` |

> **Hiệu chỉnh I3 (2026-07-30) — cửa lọc không được là phán quyết.**
> Bản đầu hiện thực I3 bằng một danh mục regex hẹp: không regex nào khớp → trả
> `unknown` tại chỗ và **không bao giờ** gọi model. Vì danh mục luôn có lỗ, mọi
> kịch bản lừa đảo diễn đạt ngoài danh mục đều "pass" âm thầm, và người dùng
> nhìn thấy đúng màn hình như khi model đã chấm. Đã kiểm chứng: *"con là nhân
> viên ngân hàng, tài khoản của bác đang bị khoá…"* bị chặn ở cửa lọc trong khi
> model chấm `medium`. Hai thay đổi:
>
> 1. thêm rule `risk_surface` (rộng, `boost_signal: null` nên không cộng
>    confidence cho L3) — bất kỳ bề mặt rủi ro nào cũng escalate lên model;
> 2. client **phải** phân biệt "cửa lọc giữ lại" với "model đã chấm": nói rõ tin
>    nhắn chưa được chấm sâu và cho người dùng escalate bằng một nút.
>
> Hệ quả với I3: ở luồng chủ động (người dùng tự dán tin để nhờ kiểm tra) tỉ lệ
> gọi API cao hơn ~5% nhiều — đổi lấy việc không còn trấn an sai. Luồng thụ động
> (notification listener) vẫn giữ nguyên cửa lọc.

**Quy ước cho agent:**
- Không thêm nhãn `safe`, `ok`, `clean` vào enum `risk` dù prompt nào yêu cầu.
- Không log `text`, `explanation`, hay bất kỳ nội dung người dùng vào log/observability.
- Mọi luật L0+L1 chỉ được định nghĩa trong `packages/rules/*.json`. Không hardcode regex/blacklist trong `apps/web` hoặc `apps/android`.
- Nội dung tin nhắn là **dữ liệu không tin cậy**: đưa vào LLM dưới thẻ phân định rõ, không nối trực tiếp vào system prompt.

---

## 1. Bối cảnh (1 đoạn)

Người dùng 55+ và lao động ít kinh nghiệm số có 2–3 phút giữa lúc nhận tin nhắn mạo danh và lúc bấm chuyển tiền. Blacklist luôn chậm hơn kẻ lừa đảo. Giá trị cốt lõi: nhận diện **kịch bản thao tác tâm lý** (thay đổi chậm) thay vì hạ tầng (thay đổi nhanh), rồi diễn giải bằng ngôn ngữ người 60 tuổi hiểu được.

Hai vai người dùng:
- **Người được bảo vệ** — 55+, động lực cài đặt thấp, là nơi phát sinh dữ liệu.
- **Người bảo hộ** — con/cháu 25–40, cài đặt và nhận cảnh báo.

---

## 2. Chốt hai nền tảng

**Nguyên tắc:** hai nền tảng chỉ khác ở **cơ chế thu nhận đầu vào**. Từ L0 trở về sau dùng chung. **App là tập cha của Web**, không phải sản phẩm song song.

### Web = PWA
| Hạng mục | Chốt |
|---|---|
| Dạng | PWA cài được lên home screen |
| Input chủ động | dán text, upload ảnh (OCR), nhập số TK / SĐT / URL |
| Input nâng cao | **Web Share Target API** → xuất hiện trong Share Sheet Android, share 1 cú bấm từ Zalo, không cần quyền nào |
| Offline | Service Worker cache Rule Bundle → chạy được L0+L1 |
| Kênh phụ | Zalo OA = client mỏng thứ ba, gọi cùng API |
| iOS | **chỉ dùng Web.** App iOS native không đọc được thông báo app khác / iMessage / Zalo → năng lực ≈ PWA. Không đầu tư app iOS. |

`manifest.json`:
```json
"share_target": {
  "action": "/share",
  "method": "POST",
  "enctype": "multipart/form-data",
  "params": {
    "title": "title", "text": "text", "url": "url",
    "files": [{ "name": "image", "accept": ["image/png", "image/jpeg"] }]
  }
}
```

### App = Android native
| Hạng mục | Chốt |
|---|---|
| Nền tảng | Kotlin + Jetpack Compose, minSdk 26 |
| Input 1 — thụ động | `NotificationListenerService` → nguồn realtime chính (bắt được cả Zalo/Messenger, không cần READ_SMS) |
| Input 2 — lịch sử | `READ_SMS` → quét 1 lần kho SMS qua WorkManager, lô 200 tin |
| Input 3 — cuộc gọi | `CallScreeningService` → gắn nhãn số gọi đến theo blocklist |
| Input 4 — chủ động | `ACTION_SEND` + ô nhập tay, **giống hệt Web** |
| Cảnh báo | notification channel ưu tiên cao; `risk=high` → FullScreenIntent |

**Giới hạn phải code cho đúng:** Android thu gọn nội dung notification khi có nhiều tin liên tiếp. Khi phát hiện text bị cắt (thiếu dấu kết câu / dài < ngưỡng / có ký tự thu gọn) → vẫn chấm điểm nhưng set `truncated: true` và mời người dùng mở app gửi bản đầy đủ.

---

## 3. Kiến trúc

```
 WEB/PWA          ANDROID APP        ZALO OA
 nhập tay         NotifListener      forward
 upload ảnh       READ_SMS
 ShareTarget      CallScreening
 tra cứu          nhập tay
 [L0+L1 device]   [L0+L1 device]
     └────────────────┼────────────────┘
                      │ HTTPS TLS1.3
                 API GATEWAY
        (auth · rate limit · schema validate)
                      │
      ┌───────────────┼───────────────┐
   LOOKUP        DETECTION         GUARDIAN
   SERVICE        ENGINE            SERVICE
   · account     L0 normalize      · pairing
   · phone       L2 redact         · fan-out
   · url         L3 LLM classify   · FCM / WebPush
   · k-anon      L4 aggregate
      └───────────────┼───────────────┘
              │                │
   PostgreSQL + pgvector    Redis
   blocklists, analyses,    cache, rate limit,
   guardians, reports       rule bundle
              │
              ▼ (một chiều, chỉ đọc)
   tinnhiemmang.vn · checkscam.vn · cảnh báo NCSC/ngân hàng
```

| Tầng | Chạy ở | Trách nhiệm |
|---|---|---|
| **L0** chuẩn hóa | client | gỡ dấu, chuẩn hóa Unicode, teencode, ký tự chèn, tách URL + số |
| **L1** luật xác định | client | đối chiếu Rule Bundle, **chặn OTP**, quyết định có gọi API (cửa lọc ~5%) |
| **L2** ẩn danh hóa | server biên | xóa PII trước khi tới LLM |
| **L3** phân loại | server | LLM chấm 8 dấu hiệu + pgvector similarity |
| **L4** tổng hợp | server | cộng điểm, áp ngưỡng, định hình output |
| **L5** hội thoại | server | so một liên hệ với chính họ trong quá khứ — phát hiện tài khoản bị chiếm |

L0+L1 sinh từ **cùng một** `packages/rules/*.json` cho cả TS và Kotlin → tương đương được bảo đảm bằng **dữ liệu**, không bằng kỷ luật lập trình.

---

## 4. L2 — Ẩn danh hóa

```
OTP / mã xác thực → <OTP>        # đã chặn ở L1, đây là phòng thủ lớp 2
số tài khoản      → <ACCOUNT>    # giữ riêng để đưa vào Lookup Service
số điện thoại     → <PHONE>
tên riêng         → <NAME>
số tiền           → <AMOUNT:trieu>   # giữ bậc độ lớn, bỏ giá trị chính xác
```
Bậc độ lớn số tiền là tín hiệu phân loại có ý nghĩa; giá trị chính xác thì không.

---

## 5. L3 — Taxonomy 8 dấu hiệu

LLM phải trả JSON có cấu trúc, chấm 0–1 cho từng dấu hiệu, **kèm `evidence` là đoạn text làm căn cứ** (giảm bịa đặt + là nguyên liệu sinh explanation cụ thể).

| Mã | Dấu hiệu | Nhận biết | Weight |
|---|---|---|---|
| `mao_danh_tham_quyen` | Mạo danh cơ quan thẩm quyền | công an, thuế, điện lực, nhà trường, ngân hàng | 0.20 |
| `yeu_cau_bi_mat` | Yêu cầu giữ bí mật với người thân | "không nói với ai kể cả gia đình" | 0.20 |
| `ap_luc_thoi_gian` | Tạo áp lực thời gian | "trong 2 giờ", "trước 17h nếu không sẽ bị khóa" | 0.15 |
| `tk_ca_nhan` | Chuyển tiền vào TK cá nhân | tự nhận là tổ chức nhưng TK đứng tên cá nhân | 0.15 |
| `cai_app_ngoai` | Cài app ngoài store | gửi APK, yêu cầu bật quyền trợ năng | 0.15 |
| `loi_ich_bat_thuong` | Hứa lợi ích bất thường | trúng thưởng, việc lương cao không cần kinh nghiệm | 0.08 |
| `chuyen_kenh` | Đề nghị chuyển kênh liên lạc | từ SMS/gọi sang Zalo, Telegram riêng | 0.07 |
| `yeu_cau_otp` | Yêu cầu OTP / mã xác thực | "đọc mã vừa gửi để xác minh" | **override** |

`yeu_cau_bi_mat` có weight cao nhất cùng `mao_danh_tham_quyen` vì nó gần như không xuất hiện trong giao tiếp hợp pháp → tỷ lệ báo sai thấp nhất.

Song song:

- classifier ý đồ toàn câu → `scam_confidence` 0–1; giữ ngữ cảnh phủ định
  thay vì max-pool theo câu;
- embedding text đã ẩn danh → pgvector so với kho kịch bản đã gán nhãn →
  trả nhãn gần nhất + cosine distance.

`scam_confidence` chỉ là prior có trọng số giới hạn, không tự tạo nhãn
`high`. Câu bảo vệ rõ ràng như “không chia sẻ OTP” được L0/L3 hạ confidence,
trừ khi phía sau vẫn có yêu cầu chủ động gửi tiền, mã, APK hoặc quyền thiết bị.

---

## 6. L4 — Ngưỡng và chính sách

```
score = Σ(wᵢ × signalᵢ) + α × scam_confidence + β × similarity_max

α = 0.405 cho baseline `ml-0.3.0`, chọn trên validation và phải được
re-calibrate bằng golden set thật trước production.

score ≥ 0.70          → high     "Nhiều dấu hiệu lừa đảo"
0.35 ≤ score < 0.70   → medium   "Cần kiểm tra thêm"
score < 0.35          → unknown  "Chưa phát hiện dấu hiệu"

Ghi đè cứng (bỏ qua score):
  yeu_cau_otp                    → high
  số TK có trong blocklist        → high
  yeu_cau_bi_mat                 → tối thiểu medium
```

Output cho `unknown` **phải** là "Chưa phát hiện dấu hiệu", không bao giờ là "An toàn". Lý do: trấn an sai chuyển trách nhiệm phán đoán từ người dùng sang hệ thống trong đúng tình huống hệ thống có thể sai.

> **Phát hiện khi hiện thực (2026-07-30) — cần hiệu chỉnh trọng số.**
> Với bộ trọng số ở Phụ lục A, một số tổ hợp dấu hiệu **không thể** đạt ngưỡng `medium` dù cả hai dấu hiệu đạt confidence 1.0:
>
> | Tổ hợp | Điểm tối đa | Kết luận |
> |---|---|---|
> | `loi_ich_bat_thuong` + `chuyen_kenh` | 0.08 + 0.07 = **0.15** | `unknown` |
> | + thêm `cai_app_ngoai` | **0.30** | `unknown` |
> | `loi_ich_bat_thuong` + `ap_luc_thoi_gian` | **0.23** | `unknown` |
>
> Nghĩa là kịch bản **trúng thưởng → chuyển sang Zalo riêng** — một dạng lừa đảo phổ biến — luôn trả về `unknown` theo đúng thiết kế hiện tại. Đã kiểm chứng bằng `aggregate_risk` thật.
>
> Phụ lục A đã nói trọng số là "giá trị khởi tạo, cần hiệu chỉnh trên bộ dữ liệu vàng", nên **không tự ý sửa** trong lần hiện thực này. Cần quyết định khi có golden set: nâng trọng số hai dấu hiệu này, hạ ngưỡng `medium`, hoặc thêm luật ghi đè cho tổ hợp "lợi ích bất thường + chuyển kênh".

Văn phong `explanation` và `questions`: viết cho người 60 tuổi đọc trên điện thoại. Câu ngắn. **Cấm** dùng "phishing", "xác thực hai lớp", "social engineering", "malware".

---

## 6b. L5 — Hội thoại: tài khoản người quen bị chiếm

Kịch bản: tài khoản Facebook/Zalo của một người bị chiếm, kẻ xấu đọc lịch sử
chat, bắt chước cách xưng hô rồi nhắn cho người thân và bạn bè để vay tiền.

**Vì sao L0-L4 không bắt được.** Tin nhắn đến từ đúng tài khoản thật, đúng tên
thật, và câu hỏi vay tiền là câu một người bạn thật cũng nhắn. Chấm từng tin một
thì không có gì để bám: hoặc bỏ sót, hoặc báo nhầm mọi lần có người hỏi vay tiền.

**Quyết định nằm ở đâu.** Không nằm trong nội dung tin nhắn mà nằm ở **độ lệch
giữa người này hôm nay và chính họ trước đó**. Bốn đặc trưng, tất cả đều xác
định, không cần dữ liệu huấn luyện:

| Tín hiệu L5 | Đo cái gì |
|---|---|
| `doi_giong_van` | Hồ sơ cách gõ: tỉ lệ dùng dấu, độ dài tin, emoji, dấu câu cuối câu, viết hoa đầu câu, tập từ xưng hô — so đoạn trước và đoạn sau lúc hỏi tiền |
| `yeu_cau_tien_dot_ngot` | Lần đầu tiên có lời hỏi tiền trong cả đoạn |
| `ne_goi_thoai` | Người dùng đề nghị gọi điện/video, phía kia lảng đi ("đang họp", "mic hỏng", "nhắn tin thôi") |
| `tk_khac_ten` | Tên chủ tài khoản viết trong tin khác tên người dùng lưu liên hệ |

**Bất biến.** Vốn từ L5 tách hẳn khỏi 8 signal code của L3: `mao_danh_tham_quyen`
nghĩa là mạo danh cơ quan chức năng, dùng lại nó cho một người bạn bị hack sẽ
sinh ra lời giải thích sai sự thật với người dùng. I1 vẫn thắng: OTP xuất hiện ở
bất kỳ tin nào trong đoạn thì chặn ngay trên máy, cả đoạn không rời thiết bị. L5
không ghi gì xuống database — I2 áp cho hội thoại y như cho tin nhắn.

**Ngưỡng.** Cần tối thiểu 3 tin nhắn cũ của liên hệ trước lúc hỏi tiền thì mới so
được. Dưới ngưỡng đó, hệ thống **nói rõ là chưa đủ dữ kiện** (lớp chỗ khó ①) chứ
không đoán bừa và cũng không im lặng.

**Đầu vào khác nhau theo client.** Android đọc được luồng tin nhắn nên gửi thẳng
danh sách tin. Web không có quyền đó, nên đường vào là ảnh chụp màn hình đoạn
chat: `/v1/ocr/thread` đọc bố cục bong bóng (trái = người kia, phải = người dùng)
để dựng lại ai nhắn gì. **Suy đoán này có thể sai**, nên client bắt buộc cho
người dùng sửa từng dòng trước khi phân tích.

---

## 7. Hợp đồng API

Mặt phẳng bảo đảm tương đương. Mọi client gọi cùng tập endpoint, nhận cùng cấu trúc. `source` chỉ dùng cho analytics, **không** làm thay đổi logic.

| Endpoint | Method | Mục đích |
|---|---|---|
| `/v1/analyze` | POST | phân tích một mẩu nội dung |
| `/v1/ocr` | POST | ảnh → text, client gọi tiếp `/analyze` |
| `/v1/analyze-thread` | POST | phân tích cả một đoạn hội thoại (L5) |
| `/v1/ocr/thread` | POST | ảnh chụp đoạn chat → danh sách tin nhắn có người gửi, client gọi tiếp `/analyze-thread` |
| `/v1/lookup/account` | GET | tra TK theo prefix hash |
| `/v1/lookup/phone` | GET | tra SĐT đã bị báo cáo |
| `/v1/lookup/url` | GET | tra tên miền / link |
| `/v1/report` | POST | người dùng báo cáo TK/SĐT/tin nhắn |
| `/v1/rules/bundle` | GET | tải Rule Bundle cho L0+L1 |
| `/v1/guardian/pair` | POST | tạo / xác nhận mã ghép cặp |
| `/v1/guardian/alert` | POST | phát tán cảnh báo cho người bảo hộ |
| `/v1/feedback` | POST | đánh dấu kết quả đúng/sai |

### POST /v1/analyze

```jsonc
// Request
{
  "text": "Chao anh, em la can bo thue...",
  "source": "web" | "android" | "zalo_oa",
  "input_mode": "manual" | "share" | "notification" | "sms_scan",
  "app_package": "com.zing.zalo",      // chỉ với android/notification
  "local_signals": ["url_shortened"],  // kết quả L1 trên thiết bị
  "truncated": false,
  "locale": "vi-VN"
}
```

```jsonc
// Response 200
{
  "analysis_id": "an_7f3c91",
  "risk": "high",                      // high | medium | unknown
  "score": 0.86,
  "signals": [
    { "code": "mao_danh_tham_quyen", "confidence": 0.94, "evidence": "em la can bo thue" },
    { "code": "ap_luc_thoi_gian",    "confidence": 0.88, "evidence": "truoc 17h hom nay" }
  ],
  "explanation": "Tin nhắn này tự nhận là cán bộ thuế và bắt bạn làm gấp trong hôm nay. Cơ quan thuế không bao giờ nhắc nộp tiền qua tin nhắn như vậy.",
  "questions": [
    "Anh/chị cho tôi số điện thoại cơ quan để tôi gọi lại?",
    "Tại sao tiền lại chuyển vào tài khoản cá nhân?"
  ],
  "verified_hotline": { "name": "Tổng cục Thuế", "number": "19008888" },
  "actions": ["report", "share_to_guardian", "lookup_account"],
  "engine_version": "ml-20260730-101500-a1b2c3d4",
  "rule_bundle_version": "rb-2026-07-30"
}
```

`engine_version` + `rule_bundle_version` phục vụ parity test: hai client cùng phiên bản phải cho cùng kết quả trên cùng input.

> **Đính chính (2026-07-30).** Bản 1.0 của tài liệu ghi ví dụ `"engine_version": "de-1.4.0"`. Giá trị thực tế là phiên bản của model đang active, do `chan_ml.constants.ENGINE_VERSION` và `daily_training` sinh ra, dạng `ml-*` (ví dụ `ml-0.2.0`, `ml-20260730-101500-a1b2c3d4`). Không có thành phần nào phát ra chuỗi `de-*`. Tên trường giữ nguyên.

### GET /v1/lookup/account — k-anonymity

```
1. client: h = SHA256("chan:account:v1:" + normalize(so_tai_khoan))
2. client: GET /v1/lookup/account?prefix=<2 hex đầu của h>
3. server: trả toàn bộ cụm hash cùng prefix (mục tiêu 20–500 phần tử)
4. client: tự đối chiếu h trong cụm, tại chỗ
```
→ server không bao giờ biết người dùng tra số nào (I4).

Không trùng → hiển thị "Chưa có báo cáo về số tài khoản này". **Không** nói an toàn.

---

## 8. Mô hình dữ liệu

```sql
-- KHÔNG có cột nào chứa nội dung tin nhắn (I2)
CREATE TABLE analyses (
  id              text PRIMARY KEY,
  text_sha256     bytea NOT NULL,       -- hash của text đã chuẩn hóa
  risk            text NOT NULL CHECK (risk IN ('high','medium','unknown')),
  score           real NOT NULL,
  signals         jsonb NOT NULL,       -- [{code, confidence}] — KHÔNG lưu evidence
  source          text NOT NULL,
  input_mode      text NOT NULL,
  app_package     text,
  truncated       boolean DEFAULT false,
  engine_version  text NOT NULL,
  rule_version    text NOT NULL,
  created_at      timestamptz DEFAULT now()   -- TTL 90 ngày
);

CREATE TABLE scenarios (               -- kho kịch bản đã gán nhãn
  id          bigserial PRIMARY KEY,
  redacted    text NOT NULL,           -- đã qua L2
  embedding   vector(1024),
  labels      text[] NOT NULL,
  consented   boolean DEFAULT false    -- chỉ lưu khi user bấm đồng ý góp dữ liệu
);

CREATE TABLE blocklist_accounts (
  hash        bytea PRIMARY KEY,       -- SHA256("chan:account:v1:" + normalize(số TK))
  prefix      char(2) NOT NULL,        -- 2 hex đầu, index cho k-anon v1
  report_cnt  int DEFAULT 1,
  first_seen  timestamptz DEFAULT now(),
  last_seen   timestamptz DEFAULT now(),
  origin      text                     -- tinnhiemmang | checkscam | user_report
);
CREATE INDEX ON blocklist_accounts (prefix);

CREATE TABLE blocklist_phones (LIKE blocklist_accounts INCLUDING ALL);
CREATE TABLE blocklist_urls   (LIKE blocklist_accounts INCLUDING ALL);

CREATE TABLE devices (
  id           text PRIMARY KEY,
  token_hash   bytea NOT NULL,
  platform     text NOT NULL,          -- web | android
  push_token   text,
  created_at   timestamptz DEFAULT now()
);

CREATE TABLE guardians (
  protected_device  text REFERENCES devices(id),
  guardian_device   text REFERENCES devices(id),
  consented_at      timestamptz NOT NULL,   -- BẮT BUỘC, xác nhận trên máy người được bảo vệ (I5)
  consent_source    text NOT NULL CHECK (consent_source = 'protected_device'),
  revoked_at        timestamptz,
  PRIMARY KEY (protected_device, guardian_device)
);

CREATE TABLE guardian_alerts (         -- KHÔNG chứa nội dung tin nhắn (I5)
  id          bigserial PRIMARY KEY,
  pair        text NOT NULL,
  risk        text NOT NULL,
  signals     text[] NOT NULL,
  app_package text,
  sent_at     timestamptz DEFAULT now()
);

CREATE TABLE feedback (
  analysis_id text REFERENCES analyses(id),
  verdict     text CHECK (verdict IN ('correct','false_positive','false_negative')),
  created_at  timestamptz DEFAULT now()
);
```

Ràng buộc `consent_source = 'protected_device'` là cách thực thi I5 ở tầng dữ liệu, không chỉ ở tầng UI.

### Vòng đời dữ liệu
```
nội dung tin nhắn      : 0 giây phía server, không bao giờ ghi ra đĩa
text đã ẩn danh        : chỉ trong RAM, trong một lần gọi
hash + signals + score : 90 ngày
embedding (ẩn danh)    : lâu dài, CHỈ khi consented = true
log truy cập           : 30 ngày, không chứa nội dung
cặp guardian           : tới khi người dùng hủy
```

---

## 9. Luồng nghiệp vụ

**Luồng A — chủ động (Web + App):** input → L0 → L1 → nếu thấy OTP: dừng, cảnh báo tại chỗ; nếu dưới ngưỡng: trả `unknown` tại chỗ; nếu vượt: `POST /analyze` → L2 → L3 (+ lookup hash) → L4 → render → tùy chọn `POST /guardian/alert`.

**Luồng B — thụ động (App):**
1. Notification đến → `ScamNotificationListener` bắt, kiểm tra package có trong watchlist
2. Local Engine chạy L0+L1 **hoàn toàn trên thiết bị**
3. Dưới ngưỡng → kết thúc, không có byte nào rời máy (~95% trường hợp)
4. Vượt ngưỡng → `/v1/analyze` với `input_mode: "notification"`
5. `high` → FullScreenIntent; `medium` → notification ưu tiên cao
6. Nếu đã ghép cặp + `high` → `/v1/guardian/alert`
7. Người dùng phản hồi → `/v1/feedback`

**Luồng C — chặn tại điểm chuyển tiền:** nhập số TK người nhận → hash → prefix lookup → đối chiếu cục bộ → nếu trùng: hiện số lượt báo cáo + thời điểm gần nhất. Tỷ lệ cứu được tiền cao nhất, cần ít dữ liệu cá nhân nhất.

---

## 10. Ma trận tương đương

| Chức năng | Web/PWA | Android | Ghi chú |
|---|:--:|:--:|---|
| Nhập tin nhắn thủ công | ✔ | ✔ | cùng UI, cùng kết quả |
| Nhận qua Share Sheet | ✔ | ✔ | Web Share Target ↔ ACTION_SEND |
| OCR ảnh chụp màn hình | ✔ | ✔ | cùng `/v1/ocr` |
| Tra cứu số tài khoản | ✔ | ✔ | cùng k-anonymity |
| Tra cứu SĐT / link | ✔ | ✔ | |
| Giải thích + câu hỏi gợi ý | ✔ | ✔ | cùng response Engine |
| Báo cáo TK lừa đảo | ✔ | ✔ | |
| Ghép cặp người bảo hộ | ✔ | ✔ | |
| Nhận cảnh báo (vai guardian) | ✔ | ✔ | WebPush ↔ FCM |
| Chạy tầng luật khi offline | ✔ | ✔ | ServiceWorker ↔ Room |
| Quét thụ động tin nhắn đến | ✖ | ✔ | trình duyệt không có API |
| Quét lịch sử SMS | ✖ | ✔ | cần READ_SMS |
| Cảnh báo cuộc gọi đến | ✖ | ✔ | cần CallScreeningService |
| Cảnh báo khi app đang đóng | ✖ | ✔ | Web chỉ nhận push |
| Dùng được không cần cài | ✔ | ✖ | lợi thế riêng Web |
| Dùng được trên iOS | ✔ | ✖ | xem mục 2 |

10 dòng đầu = tương đương tuyệt đối. 4 dòng giữa = năng lực bổ sung của App do giới hạn nền tảng. 2 dòng cuối = lợi thế riêng Web. **Không có dòng nào App thiếu chức năng chủ động mà Web có.**

---

## 11. Kiểm thử bắt buộc

1. **Golden set:** ≥100 tin lừa đảo thật + ≥30 tin **hợp pháp nhưng trông đáng ngờ** (thông báo thật của ngân hàng, nhắc học phí của trường). Gán nhãn tay theo 8 dấu hiệu.
2. **Parity test L0+L1:** bản TypeScript và bản Kotlin chạy toàn bộ golden set, `signals` và quyết định vượt ngưỡng phải trùng **100%**. Lệch 1 case = fail CI.
3. **E2E parity:** cùng một tin gửi từ 3 client → so `risk` + `signals` → phải trùng.
4. **Ngưỡng chấp nhận:** recall ≥ 90% trên nhóm lừa đảo · false positive < 15% trên nhóm hợp pháp · p95 latency < 5s.

Ưu tiên **recall trên precision**: bỏ lọt = mất tiền; báo sai = mất niềm tin. Nhưng báo sai quá nhiều thì người dùng bỏ app, nên FP là chỉ số theo dõi chính, không phải chỉ số bỏ qua.

---

## 12. Stack và repo

| Lớp | Chốt |
|---|---|
| Web | Next.js + TypeScript + Tailwind, PWA |
| Android | Kotlin + Compose + Room + WorkManager |
| Backend | FastAPI + Pydantic |
| LLM | API thương mại, structured JSON output. Không fine-tune trong phạm vi hackathon |
| OCR | PaddleOCR self-host (tiếng Việt có dấu tốt, không phí theo lượt), fallback Cloud Vision |
| DB | PostgreSQL + pgvector |
| Cache | Redis (rule bundle, cụm hash, rate limit counter) |
| Hạ tầng | Docker + Cloud Run hoặc VPS sau Nginx |
| CI/CD | GitHub Actions; hạ tầng khai báo bằng Terraform |

```
chan/
├─ packages/
│  ├─ rules/            # Rule Bundle JSON + generator — NGUỒN DUY NHẤT
│  ├─ engine-core/      # L0+L1 TypeScript → dùng cho Web
│  └─ contracts/        # OpenAPI schema, sinh type cho cả 3 client
├─ apps/
│  ├─ web/              # Next.js PWA
│  ├─ android/          # Kotlin (port L0+L1 + parity test)
│  ├─ api/              # FastAPI
│  └─ zalo-oa/          # webhook mỏng
├─ tests/
│  ├─ golden/           # golden set
│  └─ parity/           # parity Web ↔ Android
└─ infra/               # Terraform, Dockerfile, CI workflow
```

Môi trường: `local` (docker compose, LLM ở chế độ mô phỏng để không tốn phí) · `staging` (dữ liệu tổng hợp, full log để đo FP) · `prod` (chỉ bật sau khi parity + golden set đạt ngưỡng).

---

## 13. Ngoài phạm vi / giới hạn đã biết

- **Không** xử lý lừa đảo qua cuộc gọi thoại trực tiếp (chỉ gắn nhãn số gọi đến). Đây là kênh thiệt hại lớn nhất và nằm ngoài phạm vi.
- Luồng thụ động **mất hiệu lực hoàn toàn** nếu người dùng tắt thông báo Zalo.
- Nội dung notification có thể bị OS cắt ngắn → giảm độ chính xác.
- Kịch bản hoàn toàn mới vẫn có thể lọt; taxonomy cần rà soát định kỳ theo dữ liệu `feedback`.
- **Rào cản phân phối:** Google Play chỉ mở ngoại lệ READ_SMS cho nhóm anti-smishing khi nhà phát triển đã có thành tích được ngành công nhận (báo cáo analyst, benchmark, ấn phẩm ngành) → team hackathon không đủ điều kiện. Đường khả thi hơn cho bản phát hành thật: đóng gói theo nhóm ngoại lệ **"Caller ID, spam detection and/or spam blocking"**. Trong hackathon: bản Android trình bày bằng cài trực tiếp + tài liệu kiến trúc.
- Không dùng SDK analytics bên thứ ba trong luồng xử lý nội dung (I6).

### Lộ trình
| GĐ | Nội dung |
|---|---|
| 1 — Hackathon | Web PWA đầy đủ (luồng A + C), Zalo OA, Engine L0–L4, golden set, ma trận tương đương. Android ở dạng thiết kế + kiến trúc. |
| 2 | Android native với NotificationListener + CallScreening; parity test tự động. |
| 3 | Guardian Service hoàn chỉnh; vòng phản hồi cải thiện ngưỡng + taxonomy. |
| 4 | Đàm phán tiếp cận dữ liệu TK nghi ngờ ở cấp tổ chức → từ công cụ cá nhân thành hạ tầng bảo vệ. |
