# Handoff cho Web và Android

## Thành phần dùng chung

| Nhu cầu | Thành phần | Cách dùng |
|---|---|---|
| Public API | `gateway/` | Clients gọi `POST /v1/analyze` qua HTTPS |
| Phân tích tin nhắn | `detection/` | Chỉ Gateway gọi `/internal/v1/analyze` |
| Contract request/response | `detection/src/chan_detection/schemas.py` | Sinh type hoặc map sang TypeScript/Kotlin |
| Model đã train | `ml/artifacts/chan-signal-model.joblib` | Chỉ Detection API Python nạp |
| Dataset nhóm đã làm sạch | `ml/data/generated/chan-team-clean-v4.jsonl.gz` | ML/backend tự tạo từ raw data để train và đánh giá |
| Dataset replay 250.000 dòng | `ml/data/generated/chan-synthetic.jsonl.gz` | Bổ sung coverage khi train, không dùng làm test nhóm |
| Adapter data nhóm | `ml/src/chan_ml/team_dataset.py` | ML chạy để redaction/deduplicate/split `CHAN-Dataset` trước train |
| Version + checksum | `ml/ARTIFACTS.json` | CI/deployment xác minh trước khi chạy |
| Kết quả frozen + typo | `eval/team-robust-final-golden-results.json` | 20/20 gốc và 136/136 biến thể |
| Kết quả product test | `eval/team-robust-final-product-test.json` | Recall/FPR/signal metrics và toàn bộ mismatch ID |

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

Lệnh chuẩn bị dữ liệu, train có bounded replay, chạy team test và chạy đủ file
Excel golden set nằm trong `ml/README.md`. Raw `CHAN-Dataset` không được đưa
vào Web/Android hoặc commit lên Git; hai client chỉ dùng Rule Bundle và API.

Artifact `ml-0.5.0` hiện đạt 20/20 frozen case, 136/136 typo variant, test
recall 93,60%, false-positive 8,22% và supported-signal macro-F1 86,61%. Đây
là kết quả trên bộ đã đo; trước production,
đội vẫn cần mở rộng frozen set bằng dữ liệu thật được phép sử dụng, gán nhãn
thủ công, L2-redacted và theo dõi drift.
