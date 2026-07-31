# Nhóm LuaDao · CHAN — Trợ lý chống lừa đảo

Hướng: [ ] A — VLearn · [ ] B — Trợ lý Học viên · [x] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn · [ ] Tính năng mới

**Lát cắt một câu:** Khi người dùng nhận một tin nhắn đáng ngờ, CHẮN phân
tích các dấu hiệu thao túng và đưa ra mức cảnh báo cùng câu hỏi kiểm tra trước
khi người dùng chuyển tiền hoặc cung cấp thông tin.

## Thành phần kỹ thuật

- [`docs/CHAN-ARCHITECTURE.md`](docs/CHAN-ARCHITECTURE.md): nguồn sự thật duy
  nhất về kiến trúc và các bất biến bảo mật.
- [`design/`](design/README.md): giao kèo thiết kế — màu, chữ, khoảng cách,
  component và layout. Đọc trước khi viết dòng UI đầu tiên.
- [`codebase/ml/`](codebase/ml/README.md): generator dữ liệu, model 8 tín hiệu,
  L4 policy và evaluation.
- [`codebase/detection/`](codebase/detection/README.md): `/v1/analyze` dùng
  chung cho Web, Android và Zalo OA.
- [`codebase/TEAM_HANDOFF.md`](codebase/TEAM_HANDOFF.md): hướng dẫn tích hợp,
  vị trí dataset/model và trách nhiệm từng đội.
- [`codebase/training_api/`](codebase/training_api/README.md): PostgreSQL ingestion, quarantine,
  review, daily retraining, model registry và hot reload.
- [`codebase/intel/`](codebase/intel/README.md): PhishTank/PhishVN ingestion,
  hash-only blocklists, k-anonymous lookup và community report consensus.
- [`eval/`](eval/README.md): golden set, kết quả đo và synthetic baseline.

## Thành viên

| # | Mã HV | Họ tên | Vai trò chính |
|---|---|---|---|
| 1 | 2A2026019318 | Nguyễn Gia Bảo | PM · Solution Architect |
| 2 | 2A2026001669 | Nguyễn Tuấn Anh | Chuẩn bị dataset |
| 3 | 2A2026001175 | Đỗ Hùng Anh | Android Developer |
| 4 | 2A202601962 | Nguyễn Thị Lý | FE Web · Testing |
| 5 | 2A202601573 | Nguyễn Lê Minh | BE Web |

> **Kiểm lại hai mã HV trước khi nộp:** ba mã đầu có 12 ký tự
> (`2A2026019318`, `2A2026001669`, `2A2026001175`), hai mã cuối chỉ có 11
> (`2A202601962`, `2A202601573`). Có thể thiếu một chữ số khi chép.

## Phân công có tên từng phần

> R7 chấm mục này: mỗi phần phải có tên người cụ thể, không ghi "cả nhóm".

| Phần | File / artifact | Người chịu trách nhiệm | Người hỗ trợ |
|---|---|---|---|
| Spec (tổng hợp §3-§4-§6) | [`spec.md`](spec.md) | Nguyễn Gia Bảo | Nguyễn Tuấn Anh |
| Evidence & impact (§1-§2) | `spec.md` + [`evidence/`](evidence/) | Nguyễn Gia Bảo | Nguyễn Tuấn Anh |
| Kiến trúc & bất biến bảo mật | [`docs/CHAN-ARCHITECTURE.md`](docs/CHAN-ARCHITECTURE.md) | Nguyễn Gia Bảo | |
| **Dataset** — corpus 15.840 hội thoại, taxonomy, nhãn | `CHAN-Dataset/` *(xem cảnh báo dưới)* + [`evidence/mining-results.md`](evidence/mining-results.md) | Nguyễn Tuấn Anh | Nguyễn Gia Bảo |
| Model 8 dấu hiệu + L4 policy | [`codebase/ml/`](codebase/ml/), [`codebase/detection/`](codebase/detection/) | Nguyễn Gia Bảo | Nguyễn Tuấn Anh |
| **BE Web** — Gateway, Intel, Training API | [`codebase/gateway/`](codebase/gateway/), [`codebase/intel/`](codebase/intel/), [`codebase/training_api/`](codebase/training_api/) | Nguyễn Lê Minh | Nguyễn Gia Bảo |
| **FE Web** — giao diện + kiểm thử | [`codebase/apps/web/`](codebase/apps/web/), [`design/`](design/) | Nguyễn Thị Lý | Nguyễn Lê Minh |
| Golden set & đo (§7) | [`eval/`](eval/) | Nguyễn Tuấn Anh | Nguyễn Thị Lý |
| Client Android | *(chưa có trong nhánh này)* | Đỗ Hùng Anh | |
| Validation với user | [`validation/`](validation/) | **TODO — chốt tên trước CP5** | |
| Slide & demo | [`demo-slides.pdf`](demo-slides.pdf) | **TODO — chốt người trình bày** | |

> **Bảng này là phân công, chưa phải xác nhận.** Luật vibe-coding: bị hỏi tại
> CP5/CP6 mà không giải thích được phần có tên mình thì phần đó 0 điểm. Mỗi người
> đọc lại dòng có tên mình, sửa nếu không đúng thực tế, và đảm bảo mở được file đó
> ra giải thích. **Hai dòng TODO còn lại cần tên người trước CP5.**

Mỗi thành viên nói ≥1 phần ở CP6; ai đứng tên phần nào phải giải thích được phần đó (vibe-coding rule, rubric §Reflection).

## Cấu trúc repo

```
repo/
├── README.md          ← file này: thành viên + phân công
├── spec.md            ← AI Spec (hạn cứng: commit trước 23:59 ngày 1)
├── demo-slides.pdf    ← slide 6 trang theo 02-guide.md §5.1
├── slides/            ← nguồn sinh ra demo-slides.pdf (build_deck.py)
├── design/            ← giao kèo layout & theme (cả nhóm ký chốt)
├── codebase/          ← prototype (ghi rõ phần nào mock)
├── eval/              ← golden set + bảng kết quả các lượt chạy
├── validation/        ← feedback log từ vòng user test
└── reflection/        ← mỗi người 1 file
```

## Chạy prototype

Xem [codebase/README.md](codebase/README.md).

## Tiến độ checkpoint

| Mốc | Hạn | Artifact trong repo | Có trong repo |
|---|---|---|---|
| CP1 · Canvas | 10:00 N1 | `spec.md` §4 (lát cắt) + §8 | ✅ |
| CP2 · Bấm được | 12:00 N1 | [`codebase/apps/web/`](codebase/apps/web/) + commit đầu | ✅ |
| CP3 · AI thật + đo lượt 1 | 16:00 N1 | [`eval/golden-set.md`](eval/golden-set.md) 20 case + [`eval/results.md`](eval/results.md) lượt 1 + [`codebase/logs/`](codebase/logs/) trace thật | ✅ |
| CP4 · Chốt spec | 23:59 N1 | [`spec.md`](spec.md) — quality bar chốt ở §7 | ✅ |
| CP5 · Validation + dry run | 09:00 N2 | [`validation/`](validation/) — **kịch bản sẵn, chưa có mẩu nào** | ⬜ |
| CP6 · Demo | 10:00 N2 | [`demo-slides.pdf`](demo-slides.pdf) + [`codebase/demo-backup/`](codebase/demo-backup/) | ✅ |

> Cột cuối là **có artifact trong repo hay chưa**, không phải đã nộp đúng hạn hay
> chưa — mỗi thành viên tự nộp link repo theo mốc của mình.
