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
Aurora). Sau đó map connection string của integration thành biến production:

```text
CHAN_DATABASE_URL=<PostgreSQL pooled connection string, SSL enabled>
```

Không commit connection string. Container tự chạy các migration idempotent
trước khi nhận traffic.

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
