# Nhóm [XX] · Zone [X] — [Tên lát cắt]

Hướng: [ ] A — VLearn · [ ] B — Trợ lý Học viên · [x] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn · [ ] Tính năng mới

**Lát cắt một câu:** _(1 user · 1 việc · 1 quyết định AI · 1 kết quả — copy y hệt spec.md §4)_

## Thành viên

| # | Mã HV | Họ tên | Vai trò chính |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

## Phân công có tên từng phần

> R7 chấm mục này: mỗi phần phải có tên người cụ thể, không ghi "cả nhóm".

| Phần | File / artifact | Người chịu trách nhiệm | Người hỗ trợ |
|---|---|---|---|
| Spec (tổng hợp, §3-§4-§6) | `spec.md` | | |
| Evidence & impact (§1-§2) | `spec.md` + log mining/khảo sát | | |
| Prompt & quyết định AI | `codebase/prompts/` | | |
| Code prototype | `codebase/` | | |
| Golden set & đo (§7) | `eval/` | | |
| Validation với user | `validation/` | | |
| Slide & demo | `demo-slides.pdf` | | |

Mỗi thành viên nói ≥1 phần ở CP6; ai đứng tên phần nào phải giải thích được phần đó (vibe-coding rule, rubric §Reflection).

## Cấu trúc repo

```
repo/
├── README.md          ← file này: thành viên + phân công
├── spec.md            ← AI Spec (hạn cứng: commit trước 23:59 ngày 1)
├── demo-slides.pdf    ← slide 6 trang theo 02-guide.md §5.1
├── codebase/          ← prototype (ghi rõ phần nào mock)
├── eval/              ← golden set + bảng kết quả các lượt chạy
├── validation/        ← feedback log từ vòng user test
└── reflection/        ← mỗi người 1 file
```

## Chạy prototype

Xem [codebase/README.md](codebase/README.md).

## Tiến độ checkpoint

| Mốc | Hạn | Artifact | Trạng thái |
|---|---|---|---|
| CP1 · Canvas | | Canvas 7 dòng | ☐ |
| CP2 · Bấm được | | flow chính + commit đầu | ☐ |
| CP3 · AI thật + đo lượt 1 | | `eval/` golden set + kết quả lượt 1 | ☐ |
| CP4 · Chốt spec | 23:59 N1 | `spec.md` (quality bar chốt) | ☐ |
| CP5 · Validation + dry run | | `validation/` ≥5 mẩu + slide final | ☐ |
| CP6 · Demo | | `demo-slides.pdf` | ☐ |
