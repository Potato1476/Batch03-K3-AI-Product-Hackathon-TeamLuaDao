# Prototype

## CHAN ML detection engine

The shared Vietnamese phishing-signal algorithm is implemented in
[`ml/`](ml/README.md). Web and Android use the deployed
[`Detection API`](detection/README.md) instead of duplicating detection logic
or loading a Python model in a client. The exact handoff is in
[`TEAM_HANDOFF.md`](TEAM_HANDOFF.md).

It provides:

- a reproducible 100,000-record synthetic-data generator;
- predictions for the eight architecture signal codes;
- the deterministic `high` / `medium` / `unknown` L4 policy;
- train, evaluate, and privacy-safe inference commands;
- a serialized local model artifact generated from the documented commands.

## CHAN Web PWA

Frontend responsive React + TypeScript nằm trong
[`apps/web/`](apps/web/README.md). App có đầy đủ luồng kiểm tra tin nhắn và số
điện thoại theo giao kèo thiết kế, PWA manifest/share target, dark mode, linting
và automated tests.

```bash
cd codebase/apps/web
npm ci
npm run lint
npm run test
npm run build
```

The versioned 250,000-record dataset, model, metrics, sizes, and checksums are
listed in [`ml/ARTIFACTS.json`](ml/ARTIFACTS.json).

New phishing scenarios are not limited to the committed synthetic generator.
The database-backed ingestion, review, daily retraining, and guarded model
promotion service is in [`api/`](api/README.md).

**Mức prototype khai báo:** [ ] Sketch [ ] Mock [ ] Working
*(Phải khớp thực tế và khớp `spec.md` §4 — rubric R5 chấm 2 điểm riêng cho việc khai đúng.)*

## Chạy thế nào

Nhanh nhất, chạy toàn bộ Web + Gateway + Detection + Intel + Training API:

```bash
cd repo/codebase
docker compose up --build -d
```

Mở `http://localhost:3000`. Web chỉ gọi `/api`; Nginx chuyển tiếp tới Gateway,
Gateway tự gọi các service nội bộ. Kiểm tra trạng thái bằng
`curl http://localhost:3000/api/readyz`.

Để phát triển từng service:

```bash
cd repo
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'codebase/ml[dev]'
.venv/bin/python -m pip install -e 'codebase/detection[dev]'
.venv/bin/python -m pip install -e 'codebase/api[dev]'
.venv/bin/python -m pip install -e 'codebase/intel[dev]'
.venv/bin/python -m pip install -e 'codebase/gateway[dev]'

# Test toàn bộ ML + training + threat-intel platform
.venv/bin/pytest -q \
  codebase/ml/tests \
  codebase/detection/tests \
  codebase/api/tests \
  codebase/intel/tests

# Chạy private training API sau khi cấu hình PostgreSQL/.env
.venv/bin/chan-training-api

# Chạy lookup service; feed sync chạy bằng job riêng
.venv/bin/chan-intel-api
.venv/bin/chan-intel-sync phishtank

# Chạy inference nội bộ, sau đó public API mà clients gọi
.venv/bin/chan-detection-api
.venv/bin/chan-gateway
```

Biến môi trường cần thiết: xem
[`api/.env.example`](api/.env.example),
[`intel/.env.example`](intel/.env.example),
[`detection/.env.example`](detection/.env.example), và
[`gateway/.env.example`](gateway/.env.example).

## Phần THẬT vs phần MOCK

> R5 yêu cầu ghi rõ. Khai mock trung thực không bị trừ điểm; khai sai thì bị.

| Thành phần | Thật / Mock | Ghi chú |
|---|---|---|
| Bộ phân loại 8 tín hiệu | THẬT | `ml/src/chan_ml/model.py` |
| L4 risk policy | THẬT | `ml/src/chan_ml/policy.py` |
| Ingestion + daily retraining | THẬT | cần PostgreSQL và artifact storage |
| PhishTank connector + hash-only lookup | THẬT | cần PostgreSQL; PhishTank key được khuyến nghị |
| OpenPhish connector | THẬT nhưng khóa mặc định | chỉ bật sau khi có quyền bằng văn bản |
| LLM L3 / pgvector similarity | MOCK / chưa nối | giữ đúng giới hạn hackathon trong architecture |
| Gateway `/v1/analyze` | THẬT | public edge gọi Detection nội bộ |
| Gateway `/v1/ocr` | THẬT | Tesseract `vie+eng` tự host, ảnh chỉ đi qua bộ nhớ |
| Detection `/internal/v1/analyze` | THẬT | L2, Intel lookup và model inference |
| Web PWA | THẬT | L0/L1, OCR ảnh, local-only voice, `/v1/analyze` và hash-only lookup đã nối Gateway |
| Android client | Chưa có trong nhánh này | sẽ gọi chung `/v1/analyze` |

## Lời gọi AI thật ở quyết định trung tâm

- Model: bộ phân loại n-gram + Logistic Regression đa nhãn trong artifact
  `ml/artifacts/chan-signal-model.joblib`.
- Nơi gọi: `detection/src/chan_detection/runtime.py`; client chỉ gọi Gateway.
- Prompt: không áp dụng cho baseline ML; `prompts/` dành cho tầng LLM tương lai.
- Bằng chứng đánh giá/version/checksum: `eval/`, `ml/artifacts/` và
  `ml/ARTIFACTS.json`.

## Cấu trúc

```
codebase/
├── README.md
├── apps/web/       ← React + TypeScript PWA, lint và tests
├── ml/             ← dataset generator + classifier + evaluation
├── detection/      ← public inference API cho Web/Android/Zalo OA
├── api/            ← private ingestion + review + daily training
├── intel/          ← licensed feeds + hash-only lookup service
├── packages/rules/ ← normalization parity vectors cho Web/Android/API
├── prompts/        ← prompt của quyết định AI trung tâm
├── logs/           ← trace lời gọi AI thật (bằng chứng cho R5)
└── demo-backup/    ← screenshot/video dự phòng cho CP6
```

## Flow end-to-end theo lát cắt

1. Web tải Rule Bundle, chạy L0/L1; nội dung OTP dừng hoàn toàn trên thiết bị.
2. Tin đáng ngờ được gửi có Bearer device token tới Gateway `/v1/analyze`;
   Gateway chuyển qua mạng nội bộ tới Detection.
3. Detection chạy L2 redact, model + L4 policy rồi trả kết quả về Web; Gateway
   chỉ lưu hash, score, signal và version, không lưu nội dung thô.

*(Phải chạy hết được không can thiệp tay giữa chừng — R5, 3 điểm.)*
