# Deploy CHẮN lên Vercel

Production dùng một `Dockerfile.vercel` để chạy cùng lúc:

- React PWA qua Nginx;
- public Gateway tại `/api`;
- Detection API với model đã train;
- Threat Intel API;
- private Training API;
- OCR Tesseract `vie+eng`.

Các internal API chỉ bind vào loopback trong container. PostgreSQL là state
duy nhất bắt buộc; rate limit tự fallback sang PostgreSQL khi không cấu hình
Redis.

## 1. Chuẩn bị project

Từ thư mục này:

```bash
npx vercel login
npx vercel link
```

Trong Vercel Marketplace, kết nối một PostgreSQL managed (Neon, Supabase hoặc
Aurora). Container tự dùng `DATABASE_URL` do integration cấp. Nếu nhà cung cấp
dùng tên khác, cấu hình `CHAN_DATABASE_URL` bằng pooled connection string có
SSL.

Không commit connection string. Container mở web server ngay để đáp ứng giới
hạn cold start của Vercel, đồng thời chạy các migration idempotent dưới
`supervisord`. Loopback wait-proxy giữ request `/api` trong lúc Gateway nối
database, thay vì trả 502 ở cold start; `/api/readyz` chỉ báo sẵn sàng khi
backend và database dùng được.

Private training service nằm ở `training_api/` thay vì thư mục top-level
`api/`, vì Vercel dành riêng `api/` để tự phát hiện Functions. Public path của
Gateway vẫn giữ nguyên là `/api`.

## 2. Deploy

```bash
npx vercel deploy --prod
```

Vercel dùng `sin1`, gần người dùng Việt Nam. Web gọi API cùng origin qua
`/api`, vì vậy không cần cấu hình CORS hay `VITE_CHAN_API_BASE_URL`.

## 3. Smoke test

```bash
curl -fsS https://<domain>/api/healthz
curl -fsS https://<domain>/api/readyz
```

Sau đó mở domain và thử cả ba luồng:

1. nhập/đọc tin nhắn;
2. gửi ảnh để OCR rồi phân tích;
3. tra cứu số điện thoại, tài khoản hoặc URL.

## Lưu ý vận hành

- Vercel container là stateless. Model release đã train được đóng trong image.
- Daily retraining cần lưu artifact mới vào object storage trước khi có thể
  sống qua lần scale-down; không dùng `/tmp` làm model registry lâu dài.
- Không public các cổng 8001, 8002 và 8003.
- File OCR chỉ tồn tại trong bộ nhớ request và không được lưu xuống database.
