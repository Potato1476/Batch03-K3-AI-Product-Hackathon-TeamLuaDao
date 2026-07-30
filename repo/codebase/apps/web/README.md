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

Mở URL Vite in ra ở terminal. Route `/share` mô phỏng điểm vào từ Android
Share Sheet.

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

## Phạm vi tích hợp

Đây là frontend prototype có đủ 9 trạng thái trong giao kèo thiết kế, chế độ
tối, các trạng thái lỗi có đường thoát và PWA
shell (manifest, service worker, share target). Kết quả phân tích và tra cứu
hiện là **dữ liệu demo**, không phải kết quả thật từ server. Không có nội dung
người dùng nào được lưu hoặc gửi đi.

Icon dự án do nhóm cung cấp nằm tại [`public/image.png`](public/image.png) và
được dùng cho favicon cùng PWA manifest. Logo ngang
[`public/chan-logo-horizontal.svg`](public/chan-logo-horizontal.svg) được dùng
cho phần nhận diện trên website.

Khi nối backend:

1. Thay dữ liệu demo bằng `POST /v1/analyze` và các endpoint lookup đã mô tả
   trong architecture.
2. Sinh L0/L1 từ Rule Bundle dùng chung; không hardcode regex trong app web.
3. Chặn OTP trên thiết bị trước mọi network call.
4. Giữ nguyên enum rủi ro `high | medium | unknown`; không thêm nhãn “safe”.
