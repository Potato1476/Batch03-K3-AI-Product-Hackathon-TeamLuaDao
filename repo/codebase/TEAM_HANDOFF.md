# Handoff cho Web và Android

## Thành phần dùng chung

| Nhu cầu | Thành phần | Cách dùng |
|---|---|---|
| Phân tích tin nhắn | `detection/` | Gọi `POST /v1/analyze` qua HTTPS |
| Contract request/response | `detection/src/chan_detection/schemas.py` | Sinh type hoặc map sang TypeScript/Kotlin |
| Model đã train | `ml/artifacts/chan-signal-model.joblib` | Chỉ Detection API Python nạp |
| Dataset 250.000 dòng | `ml/data/generated/chan-synthetic.jsonl.gz` | ML/backend dùng để tái lập và đánh giá |
| Version + checksum | `ml/ARTIFACTS.json` | CI/deployment xác minh trước khi chạy |
| Metric | `eval/chan-ml-synthetic-v1.0.json` | Hiển thị đúng giới hạn synthetic |

Web và Android không cần cài Python, không tải dataset, và không nhúng model
vào ứng dụng. Chỉ backend/deployment cần model artifact. Cách này giữ một kết
quả thống nhất cho mọi client và cho phép đổi model hằng ngày mà không phát
hành lại Web/App.

## Việc mỗi đội cần làm

Web:

1. Chạy L0+L1 dùng Rule Bundle chung.
2. Nếu L1 phát hiện OTP thì cảnh báo tại chỗ, không gọi mạng.
3. Nếu vượt cửa lọc thì gọi `/v1/analyze` theo ví dụ trong
   `detection/README.md`.
4. Render `risk`, `signals`, `explanation`, `questions`, `actions`.

Android:

1. Dùng cùng Rule Bundle và parity vectors với Web.
2. Gửi `source="android"` và đúng `input_mode`.
3. Với notification bị cắt, đặt `truncated=true`.
4. Không log nội dung request/response.

Backend/DevOps:

1. Deploy `codebase/detection/Dockerfile` sau API Gateway.
2. Giữ model path, SHA-256 và version đồng bộ.
3. Health check `/healthz`; chỉ route traffic khi model load thành công.
4. Dùng private Training API cho ingest/retrain; không expose nó cho client.

## Cập nhật model

Daily trainer ghi candidate vào model registry và chỉ promote khi qua golden
set. Detection API phải được chuyển sang artifact + checksum mới theo cơ chế
atomic rollout. Web/Android không đổi contract và không cần cập nhật app.

Baseline hiện tại chỉ đạt gate trên synthetic regression. Trước production,
đội phải bổ sung frozen golden set gồm dữ liệu thật đã được phép sử dụng, gán
nhãn thủ công và L2-redacted.
