# CHẮN Gateway — public `/v1` edge

Gateway là public edge dùng chung cho Web, Android và Zalo OA. Nó sở hữu:

- device authentication, CORS và rate limiting;
- public request/response contract;
- Rule Bundle và OCR;
- metadata-only analysis/feedback persistence;
- orchestration tới các internal services.

Gateway không load model, không chạy L2–L4 và không sở hữu threat-intel tables.

```text
clients
   │
   ▼
Gateway :8000
   ├── POST /v1/analyze ──────► Detection :8003
   ├── GET  /v1/lookup/* ─────► Intel :8002
   ├── POST /v1/report ───────► Intel quarantine
   └── POST /v1/feedback ─────► Training API :8001 (khi có consent)
```

## Configuration

```text
CHAN_DATABASE_URL
CHAN_DETECTION_API_URL=http://localhost:8003
CHAN_DETECTION_API_KEY=<internal detection key>
CHAN_INTEL_API_URL=http://localhost:8002
CHAN_INTEL_API_KEY=<internal reporter key>
CHAN_TRAINING_API_URL=http://localhost:8001
CHAN_TRAINING_API_KEY=<internal training key>
```

`/readyz` chỉ trả ready khi Detection reachable. Intel failures được trả dưới
dạng `503 intel_service_unavailable`; Detection failures dùng
`503 detection_engine_unavailable`.

Community reports trả `202 Accepted` và nằm trong Intel quarantine. Gateway
không tự tăng blocklist count hoặc cho report ảnh hưởng detection trước review.

## Tests

```bash
PYTHONPATH=codebase/ml/src:codebase/gateway/src \
  .venv/bin/pytest -q codebase/gateway/tests
```
