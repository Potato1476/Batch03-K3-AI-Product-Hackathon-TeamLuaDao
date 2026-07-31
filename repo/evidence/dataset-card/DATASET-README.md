# 📖 CHẮN Dataset — Hướng Dẫn Sử Dụng Chi Tiết

> **Phiên bản:** 1.0  
> **Ngày tạo:** 2026-07-30  
> **Dự án:** CHẮN — Chống Lừa Đảo bằng AI  
> **Team:** TeamLuaDao — Batch03 K3 AI Product Hackathon

---

## 📑 Mục lục

1. [Tổng quan Dataset](#1-tổng-quan-dataset)
2. [Cấu trúc Folder](#2-cấu-trúc-folder)
3. [Chi tiết từng Folder](#3-chi-tiết-từng-folder)
4. [Schema dữ liệu](#4-schema-dữ-liệu)
5. [Bảng kịch bản đầy đủ](#5-bảng-kịch-bản-đầy-đủ)
6. [Hệ thống Signal](#6-hệ-thống-signal)
7. [Hướng dẫn đọc & sử dụng dữ liệu](#7-hướng-dẫn-đọc--sử-dụng-dữ-liệu)
8. [Hướng dẫn mở rộng dữ liệu](#8-hướng-dẫn-mở-rộng-dữ-liệu)
9. [Use Cases](#9-use-cases)
10. [Lưu ý quan trọng](#10-lưu-ý-quan-trọng)

---

## 1. Tổng quan Dataset

### 1.1 Mục đích

CHẮN Dataset là bộ dữ liệu hội thoại lừa đảo đa kịch bản bằng **tiếng Việt**, được thiết kế để:

- 🤖 **Huấn luyện mô hình AI** phân loại và phát hiện lừa đảo
- 🔍 **RAG / Vector Database** — tìm kiếm ngữ nghĩa các pattern lừa đảo
- 📊 **Đánh giá mô hình** — benchmark performance trên golden set
- 🖼️ **OCR** — nhận diện lừa đảo từ ảnh chụp màn hình
- 💬 **Phản hồi người dùng** — thu thập và cải thiện liên tục

### 1.2 Thống kê tổng quan

| Thành phần | Số lượng |
|---|---|
| Tổng files | **110,064** |
| Emotion groups | **9** |
| Scenarios (kịch bản) | **32** |
| Scam conversations | **6,720** |
| Negative conversations (hợp pháp) | **1,100** |
| Evaluation files | **8,020** |
| Tổng messages (ước tính) | **~80,000+** |
| Ngôn ngữ | Tiếng Việt (chính), Anh-Việt (một số kịch bản quốc tế) |
| Nguồn dữ liệu | 6 seed datasets + synthetic LLM |

### 1.3 Nguyên tắc thiết kế

1. **Chia theo Emotion trước**, không theo nguồn dữ liệu → phản ánh đúng tâm lý nạn nhân
2. **Conversation là đơn vị chính** → mỗi file JSON = 1 cuộc hội thoại hoàn chỉnh
3. **Message dùng cho classifier** → mỗi tin nhắn có thể train riêng biệt
4. **Dữ liệu đã ẩn danh** → không chứa thông tin cá nhân thật
5. **Tách riêng Negative** → giảm false positive khi huấn luyện
6. **Evaluation bất biến** → tập test không được dùng để huấn luyện

---

## 2. Cấu trúc Folder

```
CHAN-Dataset/
│
├── 00_Documentation/          # Tài liệu, hướng dẫn, định nghĩa
│   ├── taxonomy.md
│   ├── annotation_guideline.md
│   ├── label_definition.json
│   └── version.md
│
├── 01_Scenarios/              # ⭐ DỮ LIỆU CHÍNH — Hội thoại lừa đảo
│   ├── Fear/                  # Nhóm cảm xúc: Sợ hãi
│   │   ├── Police/
│   │   ├── Tax/
│   │   ├── Electricity/
│   │   ├── Court/
│   │   ├── Bank/
│   │   └── Customs/
│   ├── Greed/                 # Nhóm cảm xúc: Lòng tham
│   │   ├── Crypto/
│   │   ├── Forex/
│   │   ├── Stock/
│   │   ├── MLM/
│   │   ├── AI_Bot/
│   │   └── Task/
│   ├── Compassion/            # Nhóm cảm xúc: Lòng trắc ẩn
│   │   ├── Charity/
│   │   └── Sick_Urgent/
│   ├── Romance/               # Nhóm cảm xúc: Tình cảm
│   │   ├── Facebook/
│   │   ├── Tinder/
│   │   ├── Telegram/
│   │   └── DatingApp/
│   ├── Lust/                  # Nhóm cảm xúc: Dục vọng
│   │   ├── Sextortion/
│   │   └── Sugar/
│   ├── Curiosity/             # Nhóm cảm xúc: Hiếu kỳ
│   │   ├── Prize/
│   │   ├── Refund/
│   │   └── Package_Foreign/
│   ├── Authority/             # Nhóm cảm xúc: Quyền lực
│   │   ├── Police/
│   │   └── Bank/
│   ├── Social/                # Nhóm cảm xúc: Xã hội
│   │   ├── Hacked_FB/
│   │   ├── Hacked_Zalo/
│   │   ├── Relative_Borrow/
│   │   └── School/
│   └── Hybrid/                # Nhóm kết hợp nhiều cảm xúc
│       ├── Telegram_Redirect/
│       ├── VideoCall/
│       └── Deepfake/
│
├── 02_Negative/               # Hội thoại HỢP PHÁP (không phải lừa đảo)
│   ├── Family/
│   ├── Bank/
│   ├── School/
│   ├── Hospital/
│   ├── Shopping/
│   ├── Work/
│   ├── OTP_Real/
│   ├── Government/
│   ├── Delivery/
│   └── Utilities/
│
├── 03_OCR/                    # Ảnh chụp màn hình + kết quả OCR
├── 04_Audio/                  # File ghi âm + transcript
├── 05_Call/                   # Metadata cuộc gọi + transcript
├── 06_URL/                    # Liên kết, domain, QR code
├── 07_Feedback/               # Phản hồi người dùng
│   ├── correct/
│   ├── wrong/
│   └── unsure/
├── 08_Embeddings/             # Vector embedding
├── 09_Evaluation/             # Tập đánh giá mô hình
│   ├── train/
│   ├── validation/
│   ├── test/
│   └── benchmark/
│
└── metadata/                  # Metadata toàn bộ dataset
    ├── scenario_tree.json
    ├── emotion_tree.json
    ├── signal_tree.json
    ├── languages.json
    └── sources.json
```

---

## 3. Chi tiết từng Folder

### 3.1 `00_Documentation/` — Tài liệu

| File | Mô tả |
|------|--------|
| `taxonomy.md` | Phân loại chi tiết 9 Emotion groups, 32 Scenarios, 5 Stages |
| `annotation_guideline.md` | Hướng dẫn gắn nhãn: cách xác định sender, stage, signals, risk |
| `label_definition.json` | Định nghĩa tất cả labels dùng trong dataset dưới dạng JSON |
| `version.md` | Lịch sử version và changelog |

### 3.2 `01_Scenarios/` — Dữ liệu chính ⭐

Đây là folder **quan trọng nhất**, chứa toàn bộ hội thoại lừa đảo.

**Cấu trúc bên trong mỗi Scenario:**

```
01_Scenarios/Fear/Bank/
├── metadata.json              # Thông tin mô tả kịch bản
├── conversations/             # ⭐ Hội thoại hoàn chỉnh (1 file = 1 cuộc trò chuyện)
│   ├── conv_fear_bank_001.json
│   ├── conv_fear_bank_002.json
│   └── ... (210 files)
├── messages/                  # Tin nhắn tách rời (dùng cho message-level classifier)
│   ├── msg_conv_fear_bank_001_001.json
│   └── ... (~2,400 files)
├── signals/                   # Signals phát hiện trong kịch bản
└── entities/                  # Thực thể trích xuất (tên, STK, URL...)
```

**Thống kê theo Emotion Group:**

| Emotion | Scenarios | Conversations | Messages (ước tính) | Mô tả |
|---------|-----------|---------------|---------------------|--------|
| **Fear** | 6 | 1,260 | ~14,500 | Giả công an, ngân hàng, thuế, điện lực, tòa án, hải quan |
| **Greed** | 6 | 1,260 | ~14,500 | Crypto, Forex, chứng khoán, đa cấp, AI Bot, nhiệm vụ TikTok |
| **Romance** | 4 | 840 | ~9,900 | Lừa tình qua Facebook, Tinder, Telegram, app hẹn hò |
| **Social** | 4 | 840 | ~10,700 | Hack FB/Zalo mượn tiền, giả trường học, người thân |
| **Curiosity** | 3 | 630 | ~8,000 | Trúng thưởng, hoàn tiền TMĐT, gửi quà nước ngoài |
| **Hybrid** | 3 | 630 | ~8,000 | Chuyển Telegram, video call lừa đảo, deepfake |
| **Authority** | 2 | 420 | ~5,300 | Mạo danh quyền lực (công an, ngân hàng) |
| **Compassion** | 2 | 420 | ~4,700 | Từ thiện giả, bệnh nặng cần tiền |
| **Lust** | 2 | 420 | ~5,400 | Sextortion, Sugar scam |
| **Tổng** | **32** | **6,720** | **~80,000+** | |

### 3.3 `02_Negative/` — Hội thoại hợp pháp

Chứa **1,100 conversations** (110/category) — đây là những tin nhắn **KHÔNG phải lừa đảo**, dùng để:
- Huấn luyện mô hình phân biệt lừa đảo vs hợp pháp
- Giảm tỉ lệ **false positive** (báo nhầm tin nhắn thường là lừa đảo)

| Category | Conversations | Ví dụ nội dung |
|----------|---------------|----------------|
| Family | 110 | Nhắn người thân hỏi thăm, nhờ mua đồ |
| Bank | 110 | Thông báo giao dịch thật từ ngân hàng |
| School | 110 | Nhà trường thông báo họp phụ huynh, học phí |
| Hospital | 110 | Nhắc lịch khám, kết quả xét nghiệm |
| Shopping | 110 | Xác nhận đơn hàng, giao hàng TMĐT |
| Work | 110 | Trao đổi công việc bình thường |
| OTP_Real | 110 | Mã OTP thật từ ngân hàng, app |
| Government | 110 | Thông báo thật từ cơ quan nhà nước |
| Delivery | 110 | Shipper gọi giao hàng thật |
| Utilities | 110 | Thông báo tiền điện, nước thật |

### 3.4 `09_Evaluation/` — Tập đánh giá

```
09_Evaluation/
├── train/          # Tập huấn luyện (~60%)
├── validation/     # Tập kiểm định (~20%)
├── test/           # Tập kiểm tra (~15%)
└── benchmark/      # Golden set (~5%) — KHÔNG ĐƯỢC DÙNG ĐỂ HUẤN LUYỆN
```

> ⚠️ **QUAN TRỌNG:** Tập `test/` và `benchmark/` là bất biến. Tuyệt đối không dùng để huấn luyện hay fine-tune mô hình.

### 3.5 `metadata/` — Metadata toàn cục

| File | Nội dung |
|------|----------|
| `scenario_tree.json` | Cây phân loại 32 kịch bản, mapping emotion → scenario → code → source |
| `emotion_tree.json` | 9 emotion groups với mô tả |
| `signal_tree.json` | 27 loại signal với severity, category, description |
| `languages.json` | Ngôn ngữ: `vi` (chính), `en` (phụ) |
| `sources.json` | 6 seed sources + synthetic LLM |

---

## 4. Schema dữ liệu

### 4.1 Conversation Schema (`conversations/*.json`)

Mỗi file là **1 cuộc hội thoại hoàn chỉnh**:

```json
{
  "conversation_id": "conv_fear_bank_001",
  "scenario": "Bank",
  "sub_scenario": "bank_variant_1",
  "code": "#2",
  "emotion": "Fear",
  "source": "seed_sms_spam",
  "source_type": "seed",
  "platform": "Phone",
  "language": "vi",
  "total_messages": 13,
  "stages_present": [
    "contact",
    "building_trust",
    "solicitation",
    "demanding_money",
    "conclusion"
  ],
  "outcome": "victim_transferred_money",
  "risk_score": 0.82,
  "created_at": "2026-07-15T16:59:00Z",
  "messages": [ ... ]
}
```

**Giải thích từng field:**

| Field | Kiểu | Mô tả |
|-------|------|--------|
| `conversation_id` | string | ID duy nhất: `conv_{emotion}_{scenario}_{số thứ tự}` |
| `scenario` | string | Tên kịch bản: `Bank`, `Crypto`, `Sextortion`... |
| `sub_scenario` | string | Biến thể cụ thể: `bank_variant_1`, `copy_trade`... |
| `code` | string | Mã kịch bản gốc: `#1` → `#25` |
| `emotion` | string | Nhóm cảm xúc: `Fear`, `Greed`, `Romance`... |
| `source` | string | Nguồn dữ liệu: `seed_phishvn`, `synthetic_llm`... |
| `source_type` | string | Loại nguồn: `seed` (thu thập) hoặc `synthetic` (tạo) |
| `platform` | string | Nền tảng: `Zalo`, `Facebook`, `Phone`, `Telegram`... |
| `language` | string | Ngôn ngữ: `vi` hoặc `en` |
| `total_messages` | int | Số tin nhắn trong cuộc hội thoại |
| `stages_present` | array | Các giai đoạn xuất hiện (xem mục 4.3) |
| `outcome` | string | Kết quả cuộc hội thoại (xem mục 4.4) |
| `risk_score` | float | Điểm rủi ro tổng: 0.0 → 1.0 |
| `created_at` | string | Timestamp ISO 8601 |
| `messages` | array | Mảng các tin nhắn (xem mục 4.2) |

### 4.2 Message Schema (trong `messages` array)

```json
{
  "message_id": "msg_conv_fear_bank_001_003",
  "sender": "scammer",
  "sender_name": "Cố vấn Nguyễn Hoàng Nam",
  "text": "Tài khoản của quý khách nằm trong danh sách bị rò rỉ dữ liệu thẻ thanh toán quốc tế.",
  "timestamp": "2026-07-15T17:03:00Z",
  "stage": "building_trust",
  "signals": ["bank_impersonation", "urgent_threat"],
  "risk": "high"
}
```

| Field | Kiểu | Mô tả |
|-------|------|--------|
| `message_id` | string | ID duy nhất: `msg_{conversation_id}_{số thứ tự}` |
| `sender` | string | `scammer` hoặc `victim` |
| `sender_name` | string | Tên hiển thị (giả danh hoặc "Nạn nhân") |
| `text` | string | Nội dung tin nhắn tiếng Việt |
| `timestamp` | string | Thời gian gửi ISO 8601 |
| `stage` | string | Giai đoạn trong kịch bản (xem mục 4.3) |
| `signals` | array | Danh sách signal phát hiện (xem mục 6) |
| `risk` | string | Mức rủi ro: `none`, `low`, `medium`, `high`, `critical` |

### 4.3 Stages (Giai đoạn lừa đảo)

Mỗi cuộc hội thoại lừa đảo thường trải qua **5 giai đoạn**:

| Stage | Tên tiếng Việt | Mô tả |
|-------|---------------|--------|
| `contact` | Tiếp cận | Tin nhắn đầu tiên, giới thiệu giả danh |
| `building_trust` | Tạo tin tưởng | Xây dựng uy tín, tạo áp lực tâm lý |
| `solicitation` | Dụ dỗ | Đưa ra "mồi câu" — OTP, link, cơ hội đầu tư |
| `demanding_money` | Yêu cầu tiền | Đòi chuyển tiền, nạp tiền, cung cấp STK |
| `conclusion` | Kết thúc | Phản ứng nạn nhân — chuyển tiền / phát hiện / từ chối |

### 4.4 Outcomes (Kết quả)

| Outcome | Mô tả |
|---------|--------|
| `victim_transferred_money` | Nạn nhân chuyển tiền thành công (bị lừa) |
| `victim_detected_and_blocked` | Nạn nhân phát hiện và chặn scammer |
| `victim_suspicious_refused` | Nạn nhân nghi ngờ nhưng chưa rõ, từ chối |
| `legitimate_resolved` | *(Chỉ Negative)* Hội thoại hợp pháp hoàn tất bình thường |

---

## 5. Bảng kịch bản đầy đủ

### 5.1 Mapping 25 kịch bản gốc → Emotion → Folder

| # | Kịch bản gốc | Emotion | Folder Path | Nguồn | Conversations |
|---|---|---|---|---|---|
| 1 | Giả công an | Fear + Authority | `Fear/Police` + `Authority/Police` | seed_phishvn | 210 + 210 |
| 2 | Giả ngân hàng | Fear + Authority | `Fear/Bank` + `Authority/Bank` | seed_sms_spam | 210 + 210 |
| 3 | Giả thuế | Fear | `Fear/Tax` | seed_phishvn | 210 |
| 4 | Giả điện lực | Fear | `Fear/Electricity` | seed_sms_spam | 210 |
| 5 | Giả bưu điện | Fear | `Fear/Customs` | seed_phishvn | 210 |
| 6 | Giả trường học | Social | `Social/School` | seed_chongluadao | 210 |
| 7 | Người thân mượn tiền | Social | `Social/Relative_Borrow` | seed_conscambench | 210 |
| 8 | Facebook bị hack | Social | `Social/Hacked_FB` | seed_chongluadao | 210 |
| 9 | Zalo bị hack | Social | `Social/Hacked_Zalo` | seed_chongluadao | 210 |
| 10 | Romance Scam | Romance | `Romance/Facebook` + `Romance/Tinder` + `Romance/DatingApp` | seed + synthetic | 630 |
| 11 | Sugar Scam | Lust | `Lust/Sugar` | synthetic_llm | 210 |
| 12 | Crypto | Greed | `Greed/Crypto` | synthetic_llm | 210 |
| 13 | Forex | Greed | `Greed/Forex` | synthetic_llm | 210 |
| 14 | Nhóm chứng khoán VIP | Greed | `Greed/Stock` | synthetic_llm | 210 |
| 15 | Hoàn tiền TMĐT | Curiosity | `Curiosity/Refund` | seed_sms_spam | 210 |
| 16 | Trúng thưởng | Curiosity | `Curiosity/Prize` | seed_sms_spam | 210 |
| 17 | Việc làm online | Greed | `Greed/Task` | seed_emscad | 210 |
| 18 | Nhiệm vụ TikTok | Greed | `Greed/Task` | synthetic_llm | *(chung #17)* |
| 19 | Từ thiện giả | Compassion | `Compassion/Charity` | synthetic_llm | 210 |
| 20 | Bệnh nặng cần tiền | Compassion | `Compassion/Sick_Urgent` | synthetic_llm | 210 |
| 21 | Gửi quà nước ngoài | Curiosity | `Curiosity/Package_Foreign` | synthetic_llm | 210 |
| 22 | Sextortion | Lust | `Lust/Sextortion` | synthetic_llm | 210 |
| 23 | Video call lừa đảo | Hybrid | `Hybrid/VideoCall` | synthetic_llm | 210 |
| 24 | Chuyển sang Telegram | Hybrid | `Hybrid/Telegram_Redirect` | seed_scc | 210 |
| 25 | Deepfake người quen | Hybrid | `Hybrid/Deepfake` | synthetic_llm | 210 |
| — | Đa cấp (MLM) | Greed | `Greed/MLM` | synthetic_llm | 210 |
| — | AI Bot lừa đảo | Greed | `Greed/AI_Bot` | synthetic_llm | 210 |
| — | Tòa án giả | Fear | `Fear/Court` | synthetic_llm | 210 |
| — | Romance Telegram | Romance | `Romance/Telegram` | synthetic_llm | 210 |

---

## 6. Hệ thống Signal

Dataset sử dụng **27 loại signal** để đánh dấu các dấu hiệu lừa đảo trong từng tin nhắn:

### 6.1 Signal theo Severity

**🔴 Critical (Nguy hiểm nhất):**

| Signal ID | Tên | Mô tả |
|-----------|-----|--------|
| `authority_impersonation` | Giả danh cơ quan công quyền | Giả làm công an, viện kiểm sát, tòa án |
| `urgent_threat` | Đe dọa khẩn cấp | Đe dọa bắt giam, niêm phong tài sản |
| `otp_phishing` | Yêu cầu mã OTP/Mật khẩu | Dụ dỗ cung cấp mã xác thực OTP |
| `sextortion_blackmail` | Tống tiền bằng ảnh/clip nhạy cảm | Đe dọa tung ảnh/video |
| `emergency_family_accident` | Báo tin cấp cứu tai nạn | Giả bác sĩ/công an báo người thân cấp cứu |
| `tax_app_installation` | Yêu cầu cài app Thuế giả | Dụ dỗ tải file APK chiếm quyền phone |
| `fake_court_subpoena` | Lệnh triệu tập tòa án giả | Gửi giấy triệu tập tòa án qua mạng |
| `school_accident_scam` | Học sinh cấp cứu | Báo phụ huynh con ngã trường học |

**🟠 High:**

| Signal ID | Tên | Mô tả |
|-----------|-----|--------|
| `bank_impersonation` | Giả danh ngân hàng | Giả cán bộ ngân hàng thông báo khóa tài khoản |
| `high_profit_guarantee` | Cam kết lợi nhuận cao | Hứa hẹn lợi nhuận 20-50% không rủi ro |
| `advance_fee_request` | Yêu cầu ứng phí trước | Yêu cầu đóng phí thủ tục, phí giải ngân |
| `malicious_link` | Gửi liên kết giả mạo/độc hại | Gửi URL lạ, trang web giả mạo hoặc app APK |
| `fake_job_task` | Nhiệm vụ online kiếm tiền | Xem video, thả tim TikTok, nâng cấp VIP |
| `sugar_baby_trap` | Bẫy bao nuôi Sugar | Hứa trợ cấp tiền nhưng bắt nộp phí xác thực |
| `account_takeover_borrow` | Tài khoản bị hack mượn tiền | Hack Zalo/FB nhắn mượn tiền bạn bè |
| `foreign_package_customs` | Hàng ngoại thông quan | Gửi quà nước ngoài bị giữ hải quan cần tiền |
| `deepfake_video_call` | Cuộc gọi video Deepfake | Gọi video chớp chờn 5s rồi cúp máy |
| `crypto_copy_trade` | Dụ dỗ sàn Crypto rác | Mời đầu tư coin rác, copy trade |
| `prize_claim_fee` | Trúng thưởng đòi phí | Thông báo trúng xe/tiền rồi đòi đóng thuế |
| `fake_qr_code` | Mã QR chuyển tiền độc hại | Gửi mã QR giả mạo chiếm tài khoản bank |

**🟡 Medium:**

| Signal ID | Tên | Mô tả |
|-----------|-----|--------|
| `relocation_to_telegram` | Yêu cầu chuyển sang Telegram | Yêu cầu thoát Zalo/FB chuyển qua Telegram |
| `fake_receipt_screenshot` | Ảnh biên lai giả | Gửi ảnh xác nhận chuyển khoản Photoshop |
| `romance_trap` | Dụ dỗ tình cảm | Tạo mối quan hệ yêu đương ảo để vay tiền |
| `charity_fraud` | Kêu gọi từ thiện giả | Lợi dụng hoàn cảnh thương tâm nhận tiền |
| `e_commerce_refund` | Hoàn tiền TMĐT | Thông báo đơn bị hàng hỏng đòi click link |
| `fake_utility_bill` | Giả nợ tiền điện/nước | Dọa cắt điện nước nếu không nộp tiền gấp |
| `pyramid_mlm_recruitment` | Chiêu dụ đa cấp VIP | Lôi kéo đóng tiền làm hệ thống đa cấp |

---

## 7. Hướng dẫn đọc & sử dụng dữ liệu

### 7.1 Load 1 conversation bằng Python

```python
import json
import os

# Đọc 1 file conversation
with open("CHAN-Dataset/01_Scenarios/Fear/Bank/conversations/conv_fear_bank_001.json", "r", encoding="utf-8") as f:
    conv = json.load(f)

print(f"Kịch bản: {conv['scenario']} ({conv['emotion']})")
print(f"Kết quả: {conv['outcome']}")
print(f"Số tin nhắn: {conv['total_messages']}")
print(f"Giai đoạn: {', '.join(conv['stages_present'])}")
print(f"Nền tảng: {conv['platform']}")
print()

for msg in conv["messages"]:
    risk_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(msg["risk"], "⚪")
    print(f"{risk_icon} [{msg['stage']}] {msg['sender_name']}: {msg['text']}")
    if msg["signals"]:
        print(f"   ⚠️ Signals: {', '.join(msg['signals'])}")
    print()
```

### 7.2 Load toàn bộ dataset bằng Python

```python
import json
import os
from pathlib import Path

def load_all_conversations(base_path="CHAN-Dataset/01_Scenarios"):
    """Load tất cả conversations từ 01_Scenarios."""
    conversations = []
    base = Path(base_path)
    
    for conv_file in base.rglob("conversations/*.json"):
        with open(conv_file, "r", encoding="utf-8") as f:
            conv = json.load(f)
            conv["_file_path"] = str(conv_file)
            conversations.append(conv)
    
    return conversations

# Sử dụng
convs = load_all_conversations()
print(f"Tổng conversations: {len(convs)}")

# Lọc theo emotion
fear_convs = [c for c in convs if c["emotion"] == "Fear"]
print(f"Fear conversations: {len(fear_convs)}")

# Lọc theo outcome
success_scams = [c for c in convs if c["outcome"] == "victim_transferred_money"]
detected = [c for c in convs if c["outcome"] == "victim_detected_and_blocked"]
print(f"Bị lừa thành công: {len(success_scams)}")
print(f"Phát hiện chặn: {len(detected)}")
```

### 7.3 Load Negative dataset

```python
def load_negative_conversations(base_path="CHAN-Dataset/02_Negative"):
    """Load tất cả negative (hợp pháp) conversations."""
    negatives = []
    base = Path(base_path)
    
    for conv_file in base.rglob("conversations/*.json"):
        with open(conv_file, "r", encoding="utf-8") as f:
            negatives.append(json.load(f))
    
    return negatives

negatives = load_negative_conversations()
print(f"Negative conversations: {len(negatives)}")
```

### 7.4 Tạo DataFrame cho phân tích

```python
import pandas as pd

def conversations_to_dataframe(conversations):
    """Chuyển conversations thành DataFrame phẳng."""
    rows = []
    for conv in conversations:
        for msg in conv.get("messages", []):
            rows.append({
                "conversation_id": conv["conversation_id"],
                "scenario": conv["scenario"],
                "emotion": conv["emotion"],
                "platform": conv["platform"],
                "outcome": conv["outcome"],
                "risk_score": conv.get("risk_score", 0),
                "message_id": msg["message_id"],
                "sender": msg["sender"],
                "text": msg["text"],
                "stage": msg["stage"],
                "risk": msg["risk"],
                "signals": "|".join(msg.get("signals", [])),
                "signal_count": len(msg.get("signals", [])),
            })
    return pd.DataFrame(rows)

df = conversations_to_dataframe(convs)
print(df.shape)
print(df.groupby("emotion")["conversation_id"].nunique())
```

### 7.5 Load metadata

```python
# Scenario tree
with open("CHAN-Dataset/metadata/scenario_tree.json", "r", encoding="utf-8") as f:
    scenario_tree = json.load(f)

# Signal tree
with open("CHAN-Dataset/metadata/signal_tree.json", "r", encoding="utf-8") as f:
    signal_tree = json.load(f)

# Xem tất cả signals
for signal in signal_tree:
    print(f"[{signal['severity'].upper()}] {signal['id']}: {signal['name']}")
```

---

## 8. Hướng dẫn mở rộng dữ liệu

### 8.1 Thêm conversations mới

1. **Chọn Emotion group** phù hợp từ 9 nhóm
2. **Tạo file JSON** theo đúng schema (mục 4.1, 4.2)
3. **Đặt tên file:** `conv_{emotion}_{scenario}_{số thứ tự}.json`
4. **Lưu vào:** `01_Scenarios/{Emotion}/{Scenario}/conversations/`
5. **Tạo message files** tương ứng trong `messages/`
6. **Cập nhật** `metadata/scenario_tree.json` nếu thêm kịch bản mới

### 8.2 Thêm Emotion group mới

1. Tạo folder mới trong `01_Scenarios/`
2. Tạo sub-folders cho từng Scenario
3. Mỗi Scenario phải có: `conversations/`, `messages/`, `signals/`, `entities/`
4. Cập nhật `metadata/emotion_tree.json`

### 8.3 Thêm Signal mới

1. Thêm entry vào `metadata/signal_tree.json`
2. Format:
```json
{
  "id": "new_signal_id",
  "name": "Tên signal tiếng Việt",
  "severity": "high",
  "category": "Category",
  "description": "Mô tả chi tiết"
}
```

### 8.4 Quy ước đặt tên

| Loại | Format | Ví dụ |
|------|--------|-------|
| Conversation ID | `conv_{emotion}_{scenario}_{3 chữ số}` | `conv_fear_bank_001` |
| Message ID | `msg_{conversation_id}_{3 chữ số}` | `msg_conv_fear_bank_001_003` |
| File conversation | `{conversation_id}.json` | `conv_fear_bank_001.json` |
| File message | `{message_id}.json` | `msg_conv_fear_bank_001_003.json` |

---

## 9. Use Cases

### 9.1 Huấn luyện Text Classifier

```python
# Binary classification: Scam vs Legitimate
X_scam = [msg["text"] for conv in scam_convs for msg in conv["messages"]]
y_scam = [1] * len(X_scam)

X_legit = [msg["text"] for conv in negative_convs for msg in conv["messages"]]
y_legit = [0] * len(X_legit)

X = X_scam + X_legit
y = y_scam + y_legit
```

### 9.2 Multi-label Signal Detection

```python
# Predict signals cho mỗi message
from sklearn.preprocessing import MultiLabelBinarizer

mlb = MultiLabelBinarizer()
X = [msg["text"] for conv in scam_convs for msg in conv["messages"]]
y = mlb.fit_transform([msg["signals"] for conv in scam_convs for msg in conv["messages"]])
```

### 9.3 Conversation Stage Classification

```python
# Predict stage của từng message trong hội thoại
X = [msg["text"] for conv in scam_convs for msg in conv["messages"]]
y = [msg["stage"] for conv in scam_convs for msg in conv["messages"]]
```

### 9.4 RAG cho Chatbot cảnh báo

```python
# Index conversations vào vector DB
from langchain.text_splitter import RecursiveCharacterTextSplitter

documents = []
for conv in scam_convs:
    full_text = "\n".join([f"{m['sender']}: {m['text']}" for m in conv["messages"]])
    documents.append({
        "text": full_text,
        "metadata": {
            "scenario": conv["scenario"],
            "emotion": conv["emotion"],
            "signals": conv["stages_present"],
            "outcome": conv["outcome"]
        }
    })
```

### 9.5 Đánh giá mô hình với Golden Set

```python
# Load benchmark set
benchmark_convs = load_all_conversations("CHAN-Dataset/09_Evaluation/benchmark")

# Chạy inference + tính metrics
from sklearn.metrics import classification_report
# ... (tùy mô hình)
```

---

## 10. Lưu ý quan trọng

### ⚠️ Bảo mật & Đạo đức

- Tất cả dữ liệu đã được **ẩn danh hóa** — không chứa thông tin cá nhân thật
- Số tài khoản, URL, số điện thoại trong dataset đều là **giả/hư cấu**
- **Không sử dụng** dataset để tạo công cụ lừa đảo
- Dataset chỉ phục vụ mục đích **nghiên cứu và bảo vệ người dùng**

### ⚠️ Encoding

- Tất cả file JSON đều sử dụng **UTF-8**
- Khi đọc bằng Python, luôn dùng `encoding="utf-8"`
- PowerShell có thể hiển thị sai dấu tiếng Việt — đây là lỗi hiển thị, file gốc vẫn đúng

### ⚠️ Nguồn dữ liệu

| Loại | Mô tả | Scenarios |
|------|--------|-----------|
| `seed` | Thu thập từ nguồn công khai, chuyển đổi format | 12 kịch bản đầu |
| `synthetic` | Tạo bằng LLM, kiểm tra chất lượng | 13 kịch bản khó + bổ sung |

**6 Seed Sources:**

| Source ID | Nguồn gốc |
|-----------|-----------|
| `seed_phishvn` | PhishVN Dataset — Mendeley Data |
| `seed_sms_spam` | Vietnamese SMS Spam — VNCERT & GitHub |
| `seed_conscambench` | ConScamBench-278 |
| `seed_emscad` | Employment Scam Aegean Dataset (EMSCAD) |
| `seed_scc` | Scam Conversation Corpus — Zenodo |
| `seed_chongluadao` | ChongLuaDao.vn Anti-Scam Database |

---

> **Liên hệ:** TeamLuaDao — Batch03 K3 AI Product Hackathon  
> **Cập nhật lần cuối:** 2026-07-30 v1.0
