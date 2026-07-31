<p align="center">
  <img src="docs/chan-logo-horizontal-corrected.svg" alt="CHAN" width="320">
</p>

<h1 align="center">CHAN — Ứng dụng Android</h1>

<p align="center">
  Trợ lý giúp người lớn tuổi nhận ra tin nhắn lừa đảo, viết riêng cho người Việt từ 55 tuổi trở lên.
</p>

<p align="center">
  <a href="https://github.com/lystiger/CHAN/releases/latest/download/app-debug.apk"><b>⬇ Tải APK mới nhất</b></a>
  ·
  <a href="docs/FRIEND_INSTALL.md">Hướng dẫn cài trên điện thoại</a>
  ·
  <a href="https://github.com/Potato1476/Batch03-K3-AI-Product-Hackathon-TeamLuaDao">Repo chính của nhóm</a>
</p>

---

## CHAN là gì

Người lớn tuổi hiếm khi bị lừa vì thiếu thông tin. Họ bị lừa vì tin nhắn được
viết để tạo áp lực: gấp gáp, có vẻ chính danh, và yêu cầu làm ngay trước khi kịp
hỏi ai.

CHAN là ứng dụng Android đọc giúp những tin nhắn đó và nói ra **dấu hiệu thúc
ép** mà nó nhìn thấy, bằng tiếng Việt đơn giản, chữ to, không thuật ngữ.

Ứng dụng cố ý **không bao giờ nói một tin nhắn là "an toàn"**. Khi không thấy dấu
hiệu nào, CHAN chỉ nói *"Chưa phát hiện dấu hiệu"* — vì một lời trấn an sai còn
nguy hiểm hơn việc im lặng.

## Tính năng chính

| | Tính năng | Mô tả |
|---|---|---|
| 📋 | **Kiểm tra tin nhắn** | Dán nội dung tin nhắn vào ứng dụng, CHAN phân tích và giải thích từng dấu hiệu đáng ngờ. |
| 🎤 | **Đọc bằng micro** | Không cần gõ chữ. CHAN ưu tiên nhận giọng nói **ngay trên máy**; nếu không được, ứng dụng **hỏi ý kiến trước** khi dùng dịch vụ giọng nói của điện thoại. |
| 🔔 | **Bảo vệ thông báo Zalo** | CHAN xem giúp thông báo Zalo và cảnh báo khi thấy dấu hiệu lừa đảo. Mặc định **tắt**, chỉ bật khi người dùng đồng ý. |
| 🔎 | **Tra cứu tài khoản, số điện thoại** | Đối chiếu với danh sách cảnh báo mà không gửi số đầy đủ lên máy chủ. |
| 📴 | **Quy tắc chạy trên máy** | Các dấu hiệu nguy hiểm rõ ràng — ví dụ tin nhắn hỏi **mã OTP** — được chặn ngay trên điện thoại, **không cần mạng và không gửi đi đâu cả**. |

## Tải và cài đặt

- **APK mới nhất:** [app-debug.apk](https://github.com/lystiger/CHAN/releases/latest/download/app-debug.apk)
- **Hướng dẫn cài từng bước cho điện thoại:** [docs/FRIEND_INSTALL.md](docs/FRIEND_INSTALL.md)

| | |
|---|---|
| Phiên bản | `0.3.1-sprint03` (versionCode 4) |
| Package | `com.chan.app` |
| Android tối thiểu | Android 7.0 (API 24) |
| Backend | `https://chan-flame.vercel.app/api/` |

> ⚠️ Đây là bản **debug** dùng cho buổi demo nội bộ của nhóm, không phải bản phát
> hành trên Play Store. Android và Play Protect sẽ cảnh báo vì ứng dụng không đến
> từ cửa hàng — cách xử lý có trong hướng dẫn cài đặt ở trên.

Chỉ dùng nội dung, số tài khoản và số điện thoại **giả lập** khi thử ứng dụng.
Không nhập mật khẩu, OTP, thông tin ngân hàng hoặc dữ liệu cá nhân thật.

## Quyền riêng tư

Những điều dưới đây không phải là lời hứa suông — mỗi điều đều có bài kiểm thử tự
động làm hỏng bản build nếu bị vi phạm:

- Tin nhắn hỏi **OTP** và nội dung chưa đủ ngưỡng: **không gửi đi bất kỳ yêu cầu
  mạng nào**.
- Tra cứu chỉ gửi **năm ký tự hex**; phần so sánh đầy đủ thực hiện trên máy.
- Chỉ theo dõi đúng một ứng dụng: `com.zing.zalo`.
- Cảnh báo của CHAN **không chứa** người gửi, nội dung tin nhắn hay bằng chứng.
- **Không ghi âm**, không lưu bản ghi. Đọc bằng micro là một lượt nói duy nhất do
  người dùng chủ động bấm.
- **Không ghi log** nội dung tin nhắn ở bất cứ đâu.
- **Không khai báo** quyền SMS, danh bạ, nhật ký cuộc gọi, bộ nhớ hay trợ năng.
- CHAN không bao giờ tự gửi nội dung đi. Người dùng phải tự bấm **Kiểm tra ngay**.

Ứng dụng cũng phân biệt rõ ba thứ mà các bản trước hay gộp làm một: **lựa chọn
bật/tắt trong CHAN**, **quyền Truy cập thông báo của Android**, và **kết nối thật
sự đang chạy**. Chỉ khi Android thực sự nối dịch vụ của CHAN thì ứng dụng mới báo
*"CHAN đang bảo vệ thông báo Zalo"*.

## Công nghệ

Kotlin · Jetpack Compose · Material 3 · Retrofit + OkHttp · kotlinx.serialization
· DataStore · Android Keystore (AES/GCM) · `compileSdk` 35, `minSdk` 24

```text
Compose UI
   ├── ChanViewModel ── ChanStateHolder        (không phụ thuộc Android, có unit test)
   │     └── LiveChanRepository
   │            ├── LocalRuleEngine            L0/L1 từ Rule Bundle dùng chung với web
   │            ├── ChanApi                    device token, analyze, lookup
   │            └── DeviceTokenStore           Android Keystore (AES/GCM)
   ├── SpeechToTextController                  ưu tiên trên máy, do người dùng bấm
   ├── ProtectionRuntimeMonitor                theo dõi kết nối thật của listener
   └── ZaloNotificationListenerService
          └── NotificationPipeline             thuần tuý, test đầy đủ trên JVM
```

Bộ quy tắc L0/L1 trên máy được ghim vào đúng hành vi của engine TypeScript bên
web thông qua `app/src/test/resources/l0-l1-parity-vectors.json`, nên hai nền
tảng không thể lệch nhau mà không bị phát hiện.

## Quan hệ với repo chính

Đây là **ứng dụng Android** của sản phẩm CHAN, thuộc dự án
[Batch03-K3-AI-Product-Hackathon-TeamLuaDao](https://github.com/Potato1476/Batch03-K3-AI-Product-Hackathon-TeamLuaDao)
— Team Lụa Đào.

- Repo chính chứa đề bài, tài liệu sản phẩm, backend và web app (`repo/codebase/`).
- Nhánh `mobile-app` chứa toàn bộ mã nguồn Android trong thư mục `mobile/`.
- Ứng dụng Android gọi cùng một backend với web app: `https://chan-flame.vercel.app/api/`.

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [docs/FRIEND_INSTALL.md](docs/FRIEND_INSTALL.md) | Cài đặt và thiết lập điện thoại cho buổi demo (tiếng Việt) |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Hướng dẫn build, cấu hình backend, kiến trúc, checklist kiểm thử |
| [docs/sprint-01-android-claude-code.md](docs/sprint-01-android-claude-code.md) | Sprint 01 — giao diện và luồng màn hình |
| [docs/sprint-02-android-claude-code.md](docs/sprint-02-android-claude-code.md) | Sprint 02 — backend trực tuyến, thông báo Zalo, giọng nói |
| [docs/sprint-03-android-claude-code.md](docs/sprint-03-android-claude-code.md) | Sprint 03 — độ tin cậy giọng nói, trạng thái bảo vệ trung thực, cảnh báo lặp |

## Build nhanh

```powershell
git clone https://github.com/lystiger/CHAN.git
cd CHAN
.\gradlew.bat testDebugUnitTest
.\gradlew.bat lintDebug
.\gradlew.bat assembleDebug -PCHAN_API_BASE_URL=https://chan-flame.vercel.app/api/
```

APK nằm tại `app/build/outputs/apk/debug/app-debug.apk`. Chi tiết đầy đủ (kết nối
backend LAN, biến môi trường, checklist kiểm thử trên máy thật) xem
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
