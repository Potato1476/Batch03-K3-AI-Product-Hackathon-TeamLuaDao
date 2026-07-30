# CHẮN Detection API

Detection là inference boundary nội bộ, chạy mặc định trên `:8003`. Chỉ Gateway
gọi `POST /internal/v1/analyze`.

Service:

- thực hiện L2 redaction và OTP short-circuit trước model;
- kiểm tra blocklist qua k-anonymous Intel lookup;
- chạy model và trả `high`, `medium` hoặc `unknown`;
- lấy active-model metadata từ Training API;
- kiểm SHA-256 trước khi hot-swap model;
- giữ model đang chạy nếu Training API tạm thời unavailable.

```text
CHAN_TRAINING_API_URL=http://localhost:8001
CHAN_TRAINING_API_KEY=<internal training key>
CHAN_INTEL_API_URL=http://localhost:8002
CHAN_DETECTION_API_KEY=<shared gateway-to-detection key>
CHAN_MODEL_POLL_SECONDS=60
```

Artifact URI do Training API trả về phải nằm trên storage mà Detection đọc
được. Trong production nên dùng shared, versioned object storage hoặc volume
read-only; không dùng đường dẫn chỉ tồn tại trong container Training API.

```bash
.venv/bin/pip install -e 'codebase/detection[dev]'
.venv/bin/chan-detection-api
```
