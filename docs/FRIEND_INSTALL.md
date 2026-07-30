# Cài CHAN cho buổi demo

Hướng dẫn này dành cho người cài CHAN trên điện thoại Android mà không cần cáp
USB hoặc Android Studio.

## 1. Tải và cài ứng dụng

1. Mở liên kết sau bằng Chrome trên điện thoại:
   [Tải CHAN-demo.apk](https://github.com/lystiger/CHAN/releases/download/sprint03-demo/CHAN-demo.apk).
2. Nếu Chrome hỏi, chọn **Vẫn tải xuống**. Đây là bản demo do nhóm tự build nên
   không đến từ Play Store.
3. Mở file `CHAN-demo.apk` vừa tải.
4. Nếu Android chặn, chọn **Cài đặt** và bật **Cho phép từ nguồn này** cho
   Chrome, sau đó quay lại và chọn **Cài đặt**.
5. Nếu Play Protect cảnh báo ứng dụng chưa được nhận diện, chỉ tiếp tục vì đây
   là file demo lấy từ kho GitHub chính thức của nhóm.

Thông tin bản demo:

- package: `com.chan.app`
- phiên bản: `0.3.0-sprint03`
- Android tối thiểu: Android 7
- backend: `https://chan-flame.vercel.app/api/`

## 2. Kiểm tra backend

Trước buổi demo, mở hai liên kết này trên điện thoại:

- [Health](https://chan-flame.vercel.app/api/healthz) phải hiện
  `{"status":"ok"}`.
- [Ready](https://chan-flame.vercel.app/api/readyz) phải hiện
  `{"status":"ready"}`.

Mở CHAN, vào **Kiểm tra**, dán một tin nhắn thử rồi bấm **Kiểm tra ngay**. Nếu
thấy thông báo đã kiểm tra quá nhiều lần, đừng xoá dữ liệu ứng dụng; đổi từ
Wi-Fi sang dữ liệu di động hoặc chờ tối đa một giờ rồi thử lại. Token thiết bị
được lưu trên máy và bình thường có hiệu lực 90 ngày.

## 3. Bật đọc bằng micro

1. Vào **Kiểm tra**.
2. Bấm **Đọc bằng micro**.
3. Cho phép quyền micro khi Android hỏi.
4. Nếu nhận dạng trên máy không hoạt động, CHAN sẽ hỏi trước khi dùng dịch vụ
   giọng nói của điện thoại. Chọn dùng dịch vụ đó cho lần demo nếu cần.
5. Kiểm tra lại nội dung đã nhận dạng rồi tự bấm **Kiểm tra ngay**.

CHAN không tự gửi nội dung chỉ vì micro đã nhận dạng xong.

## 4. Bật bảo vệ thông báo Zalo

Quyền này cho phép CHAN đọc nội dung thông báo, vì vậy chỉ bật cho file APK demo
được tải từ liên kết GitHub ở trên.

1. Nhấn giữ biểu tượng **CHAN** → **Thông tin ứng dụng**.
2. Mở menu ba chấm phía trên → **Cho phép cài đặt bị hạn chế** (*Allow
   restricted settings*). Xác thực nếu Android yêu cầu.
3. Mở CHAN → **Bảo vệ** → bật kiểm tra thông báo Zalo.
4. Khi Android mở trang **Đọc, trả lời và điều khiển thông báo**, bật **CHAN**.
5. Quay lại CHAN. Trạng thái đúng là **CHAN đang bảo vệ thông báo Zalo** và
   Android hiện thông báo trạng thái thường trực của CHAN.

Nếu CHAN báo Android chưa kết nối:

1. Mở lại trang **Đọc, trả lời và điều khiển thông báo**.
2. Tắt CHAN, chờ vài giây, rồi bật lại.
3. Quay lại ứng dụng và bấm **Kết nối lại** nếu nút này còn hiện.

Đây là kết nối nội bộ của dịch vụ thông báo Android, không phải lỗi đăng nhập
Zalo hoặc lỗi mạng.

## 5. Kịch bản kiểm tra nhanh

1. Dán một tin nhắn bình thường: CHAN không được gọi đó là “an toàn”; ứng dụng
   chỉ nói chưa phát hiện dấu hiệu.
2. Dán một tin nhắn giả lập yêu cầu chuyển tiền gấp: ứng dụng phải đưa ra kết
   quả phân tích từ backend.
3. Dán tin nhắn giả lập hỏi mã OTP: CHAN phải cảnh báo nguy cơ cao ngay trên
   máy.
4. Gửi hai thông báo Zalo thử nghiệm có nội dung đáng ngờ: mỗi thông báo mới
   phải có thể tạo một cảnh báo mới.

Chỉ dùng nội dung và số tài khoản giả lập trong buổi demo.

## Khi cần cài lại

Có thể cài bản APK mới đè lên bản demo cũ nếu cả hai được build bằng cùng debug
key. Nếu Android báo xung đột chữ ký, gỡ CHAN cũ rồi cài lại; sau đó phải bật
lại quyền micro, quyền thông báo và bảo vệ Zalo.
