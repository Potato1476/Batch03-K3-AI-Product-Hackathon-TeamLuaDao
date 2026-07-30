# CHAN Web

PWA responsive React + TypeScript cho luồng chủ động của CHAN. Đây là website
toàn trang, không phải mô phỏng điện thoại; ngôn ngữ hình ảnh và luồng thao tác
bám theo
[`../../../design/README.md`](../../../design/README.md) và các bất biến bảo mật
trong [`../../../docs/CHAN-ARCHITECTURE.md`](../../../docs/CHAN-ARCHITECTURE.md).

## Chạy local

Yêu cầu Node.js 22+ và npm 10+.

```bash
cd repo/codebase/apps/web
npm ci
npm run dev
```

Vite chạy tại `http://localhost:5173` và proxy `/api` tới Gateway
`http://127.0.0.1:8000`. Có thể đổi đích bằng
`CHAN_GATEWAY_DEV_PROXY_TARGET`. Route `/share` mô phỏng điểm vào từ Android
Share Sheet.

Frontend tự:

1. tải Rule Bundle và chạy L0/L1;
2. chặn OTP hoàn toàn trên thiết bị;
3. xin device token lần đầu và lưu token trên thiết bị;
4. gọi Gateway với Bearer token;
5. nếu token hết hạn, xin lại một lần rồi retry;
6. chuẩn hóa + SHA-256 chỉ báo trước lookup và chỉ gửi prefix 5 hex.

Không gọi trực tiếp Detection `:8003`, Intel `:8002` hoặc Training `:8001`.

## Kiểm tra chất lượng

```bash
npm run lint
npm run test
npm run build
```

- ESLint dùng flat config, TypeScript rules và React Hooks rules.
- Vitest + Testing Library kiểm tra flow nhập tin nhắn, cảnh báo nguy cơ cao
  và lời hứa riêng tư của tính năng tra cứu.
- `npm run build` chạy TypeScript trước khi tạo production bundle.

## Chạy toàn stack bằng Docker

Từ `repo/codebase/`:

```bash
docker compose up --build
```

Mở `http://localhost:3000`. Nginx phục vụ PWA và reverse-proxy `/api` tới
Gateway trong cùng Compose network.

## Phạm vi tích hợp

Luồng nhập text, OCR ảnh, voice input xử lý cục bộ, kết quả phân tích và lookup
đã dùng implementation thật. Guardian và các công tắc mô phỏng lỗi vẫn là
prototype. OCR dùng Gateway `/v1/ocr`; voice chỉ được bật khi trình duyệt bảo
đảm `processLocally`, không tự rơi về cloud speech.

Icon dự án do nhóm cung cấp nằm tại [`public/image.png`](public/image.png) và
được dùng cho favicon cùng PWA manifest. Logo ngang
[`public/chan-logo-horizontal.svg`](public/chan-logo-horizontal.svg) được dùng
cho phần nhận diện trên website.

Giữ nguyên enum rủi ro `high | medium | unknown`; `unknown` không phải là
“an toàn”.
