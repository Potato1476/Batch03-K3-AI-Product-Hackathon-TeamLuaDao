# logs/ — trace lời gọi AI thật

> Rubric R5 cho 3 điểm: "≥1 lời gọi AI thật ở quyết định trung tâm, có log/trace
> trong repo". File dưới đây là trace **thật**, gọi lên production, không dựng lại.

## `ai-call-trace-20260731T024301Z.jsonl`

6 lời gọi `POST /v1/analyze` lên `https://chan-flame.vercel.app`, mỗi dòng một
JSON gồm request đầy đủ, response đầy đủ, và latency đo được.

| Case | Kết quả | Score | Latency |
|---|---|---|---|
| G01 mạo danh cán bộ thuế + ép thời gian | `high` | 0.76 | 5.260 ms |
| G03 chuyển tiền + giữ bí mật | `high` | 0.99 | 5.618 ms |
| G15 SMS số dư ngân hàng **thật** | `unknown` | 0.02 | 5.174 ms |
| G16 cảnh báo của Công an (ngữ cảnh bảo vệ) | `unknown` | 0.05 | 2.905 ms |
| Học phí nhà trường — bản không dấu | `medium` | 0.49 | 3.253 ms |
| Học phí nhà trường — bản có dấu | **`high`** | 0.70 | 2.913 ms |

Hai dòng cuối là **failure nguy hiểm nhất** của nhóm, ghi vào log đúng như nó
xảy ra. Cùng một tin nhắn hợp lệ của nhà trường: bản không dấu ra `medium`, bản
có dấu ra `high` kèm `mao_danh_tham_quyen`. Xem phân tích trong
[`../../eval/results.md`](../../eval/results.md).

**Latency:** 2,9-5,6 giây mỗi lời gọi. Đây là số đo trên Vercel container đang
ấm; lần gọi đầu sau khi container ngủ còn lâu hơn — lý do màn hình chờ phải đếm
giây và nói rõ đang khởi động.

## Quyết định AI nằm ở đâu

- Model: n-gram + Logistic Regression đa nhãn, artifact
  `../ml/artifacts/chan-signal-model.joblib`, engine `ml-0.5.0`.
- Nơi chạy: `../detection/src/chan_detection/runtime.py` → `ModelRuntime.predict`.
- Client không bao giờ chạy model; chỉ gọi Gateway `/v1/analyze`.

## Chạy lại

```bash
TOKEN=$(curl -s -X POST https://chan-flame.vercel.app/api/v1/devices/token \
  -H 'Content-Type: application/json' \
  -d '{"platform":"web","push_token":null}' | jq -r .token)

curl -s -X POST https://chan-flame.vercel.app/api/v1/analyze \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"Chao anh, em la can bo thue quan 1...","source":"web",
       "input_mode":"manual","app_package":null,"local_signals":[],
       "truncated":false,"locale":"vi-VN"}' | jq
```

**Lưu ý riêng tư (I2):** file này chứa nội dung tin nhắn vì đó là **case kiểm thử
của nhóm**, không phải tin nhắn của người dùng thật. Server không lưu nội dung
tin nhắn của người dùng — bảng `analyses` chỉ có hash, điểm và mã dấu hiệu.
