# Prototype

## CHẮN ML detection engine

The shared Vietnamese phishing-signal algorithm is implemented in
[`../../ml/`](../../ml/README.md). Web, Android, and API developers should use
that package as the common L3/L4 contract instead of duplicating detection
logic in a client.

It provides:

- a reproducible 100,000-record synthetic-data generator;
- predictions for the eight architecture signal codes;
- the deterministic `high` / `medium` / `unknown` L4 policy;
- train, evaluate, and privacy-safe inference commands;
- a serialized local model artifact generated from the documented commands.

FastAPI integration is shown in the
[`ml/README.md` API section](../../ml/README.md#api-integration). Generated
datasets and model artifacts are intentionally ignored by Git.

**Mức prototype khai báo:** [ ] Sketch [ ] Mock [ ] Working
*(Phải khớp thực tế và khớp `spec.md` §4 — rubric R5 chấm 2 điểm riêng cho việc khai đúng.)*

## Chạy thế nào

```bash
# TODO: lệnh cài + lệnh chạy
```

Biến môi trường cần thiết: xem `.env.example`.

## Phần THẬT vs phần MOCK

> R5 yêu cầu ghi rõ. Khai mock trung thực không bị trừ điểm; khai sai thì bị.

| Thành phần | Thật / Mock | Ghi chú |
|---|---|---|
| Quyết định AI trung tâm | THẬT | lời gọi model thật, log tại `logs/` |
| | | |
| | | |

## Lời gọi AI thật ở quyết định trung tâm

- Model: TODO
- Nơi gọi: `TODO/path.ts`
- Prompt: `prompts/`
- Log/trace commit trong repo: `logs/` *(bắt buộc cho R5 — không hardcode output)*

## Cấu trúc

```
codebase/
├── README.md
├── prompts/        ← prompt của quyết định AI trung tâm
├── logs/           ← trace lời gọi AI thật (bằng chứng cho R5)
└── demo-backup/    ← screenshot/video dự phòng cho CP6
```

## Flow end-to-end theo lát cắt

1. TODO
2. TODO
3. TODO

*(Phải chạy hết được không can thiệp tay giữa chừng — R5, 3 điểm.)*
