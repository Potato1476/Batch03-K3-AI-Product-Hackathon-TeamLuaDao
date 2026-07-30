# CHAN — Android

Native Android client for CHAN, a scam-detection assistant written for
Vietnamese adults aged 55+. Kotlin, Jetpack Compose, Material 3.

> [English setup and testing](#building) | [Hướng dẫn tiếng Việt](#hướng-dẫn-cài-đặt-và-kiểm-thử)

Current sprint: **Sprint 02** (`0.2.0-sprint02`, `versionCode` 2) — live backend
integration, passive Zalo notification protection, and Vietnamese
speech-to-text. See `docs/sprint-02-android-claude-code.md`.

---

## Building

### Requirements and clone

- Android Studio with Android SDK 35 and Build Tools 36
- JDK 21 (the project targets JVM 17)
- Android 7.0 / API 24 or newer
- A CHAN-compatible backend for live analysis (not included here)

```powershell
git clone https://github.com/lystiger/CHAN.git
cd CHAN
```

Open the repository root in Android Studio and wait for Gradle sync. Android Studio normally creates the ignored `local.properties` file with your SDK path.

```powershell
.\gradlew.bat testDebugUnitTest
.\gradlew.bat lintDebug
.\gradlew.bat assembleDebug
```

The debug APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

Toolchain: JDK 21, AGP 8.7.3, Kotlin 2.0.21, Gradle 8.10.2, `compileSdk` 35,
`minSdk` 24. The SDK location comes from `local.properties` (gitignored).

---

## Backend base URL

The API base URL is never hardcoded in Kotlin. It is exposed as
`BuildConfig.CHAN_API_BASE_URL` and set per build type:

| Build | Source | Default |
|---|---|---|
| debug | `CHAN_API_BASE_URL` Gradle property | `http://10.0.2.2:8000/` |
| release | `CHAN_RELEASE_API_BASE_URL` Gradle property | **none — the build fails** |

`10.0.2.2` is the Android *emulator's* alias for the host machine's loopback.

### A physical phone cannot use `localhost` or `10.0.2.2`

On a real handset both of those addresses mean the *phone itself*, so the
request never reaches your computer. A physical phone must use the development
computer's **LAN IPv4 address**, and the phone and computer must be on the same
network with that connection allowed (many guest and corporate Wi-Fi networks
block device-to-device traffic; a hotspot from the phone usually works).

Find the address:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
  Select-Object InterfaceAlias,IPAddress
```

Then put it in an **uncommitted** `local.properties` at the repo root:

```properties
CHAN_API_BASE_URL=http://192.168.1.42:8000/
```

or pass it for one build:

```powershell
.\gradlew.bat assembleDebug -PCHAN_API_BASE_URL=http://192.168.1.42:8000/
```

Docker must also publish the gateway on all interfaces (`0.0.0.0:8000`), not
only on loopback, and the Windows firewall must allow inbound TCP 8000 on the
private network profile.

### Cleartext and release builds

Cleartext HTTP is permitted **only** in the debug build, through a
`network-security-config` that lives in the debug source set. The default
configuration used by release sets `cleartextTrafficPermitted="false"`, and
`verifyReleaseApiBaseUrl` fails any release build whose base URL is missing or
does not start with `https://`. `PrivacyStaticAnalysisTest` fails the build if
either of those protections is removed.

---

## Backend development stack

The backend is maintained separately and is not included in this Android repository. Start a CHAN-compatible backend, expose it on port 8000, and verify its `/readyz` endpoint before testing live analysis.

```powershell
wsl -d Ubuntu -- bash -lc 'cd /home/lystiger/projects/Batch03-K3-AI-Product-Hackathon-TeamLuaDao/repo/codebase && docker compose up --build -d'
Invoke-RestMethod http://localhost:8000/readyz
```

`/readyz` returns `{"status":"ready"}` only when the detection service is
reachable with a model loaded. Until then `/v1/analyze` will answer 503 and CHAN
will show *"Dịch vụ phân tích đang tạm nghỉ."*

---

## Architecture

```text
Compose UI
   │
   ├── ChanViewModel ── ChanStateHolder      (Android-free, unit tested)
   │     └── LiveChanRepository
   │            ├── LocalRuleEngine          L0/L1 from the shared Rule Bundle
   │            ├── ChanApi                  device token, analyze, lookup
   │            ├── DeviceTokenStore         Android Keystore (AES/GCM)
   │            └── RuleBundleStore          bootstrap asset + ETag refresh
   │
   ├── SpeechToTextController                on-device first, user initiated
   │
   └── ZaloNotificationListenerService
          ├── NotificationContentExtractor   pure, JVM tested
          ├── NotificationDedupeCache        SHA-256 digests, bounded TTL
          ├── LiveChanRepository             one bounded attempt
          └── SafeAlertPublisher             generic warnings, no content
```

Dependencies are wired by hand in `data/ChanGraph.kt`. No DI framework.

### Privacy invariants enforced by tests

- OTP content and below-gate content make **zero** HTTP requests.
- Lookup sends five hex characters; the full-hash comparison is local.
- Only `com.zing.zalo` is monitored passively.
- Warning notifications contain no sender, message, or evidence.
- No `Risk.SAFE`; `unknown` renders as *"Chưa phát hiện dấu hiệu"*.
- No HTTP body logging is wired up anywhere.
- No SMS, contacts, call-log, storage, or accessibility permission is declared.

`app/src/test/resources/l0-l1-parity-vectors.json` pins the Kotlin L0/L1 port to
the behaviour of the TypeScript engine over the same Rule Bundle.

---

## Manual physical-phone checklist

**Not executed by the build.** An APK is not evidence that notification access,
Zalo extraction, networking, or the phone's speech provider works. A human must
perform and record these steps on a real handset.

1. Install the debug APK manually (`adb install`, or copy and open it).
2. Build with the debug API URL pointing at the computer's LAN address.
3. Start the Docker stack and confirm `/readyz` answers `ready`.
4. Open CHAN → **Bảo vệ** → turn on *Kiểm tra thông báo Zalo*.
5. Confirm Android lists CHAN under Settings → Notification Access.
6. Send a benign Zalo message from another account — **no warning expected**.
7. Send a clearly manipulative test message — **warning expected**.
8. Send an OTP-request test — high warning, and **no `/v1/analyze` request**
   should appear in the gateway log.
9. Turn Wi-Fi off and repeat step 8 — local OTP protection still works.
10. Hide notification content on the lock screen — the app must not crash or
    invent content.
11. Disable Zalo's own notifications — the protection screen must explain that
    passive scanning cannot operate.
12. Deny CHAN's notification permission — the in-app status must read
    *"Đang kiểm tra nhưng chưa thể hiện cảnh báo"*.
13. Deny the microphone — paste and image paths must remain usable.
14. Dictate Vietnamese, edit the recognized text, then submit manually.
15. Revoke Notification Access, return to CHAN — the status must update to
    *"Đã tắt trong cài đặt máy"*.

Do not use real passwords, OTPs, banking details, or personal data in tests.

---

## Hướng dẫn cài đặt và kiểm thử

### Yêu cầu

- Android Studio, Android SDK 35 và Build Tools 36
- JDK 21 (dự án dùng JVM target 17)
- Máy ảo hoặc điện thoại Android 7.0 / API 24 trở lên
- Backend tương thích CHAN để phân tích trực tuyến (không nằm trong repository)

### Tải, build và kiểm thử

```powershell
git clone https://github.com/lystiger/CHAN.git
cd CHAN
.\gradlew.bat testDebugUnitTest
.\gradlew.bat lintDebug
.\gradlew.bat assembleDebug
```

Mở thư mục gốc bằng Android Studio và chờ Gradle sync. `local.properties` chứa đường dẫn Android SDK, đã được Git bỏ qua và không được commit. APK debug nằm tại `app/build/outputs/apk/debug/app-debug.apk`.

### Kết nối backend

Máy ảo dùng mặc định `http://10.0.2.2:8000/`. Với điện thoại thật, điện thoại và máy tính phải cùng mạng. Thêm IPv4 LAN của máy tính vào `local.properties`:

```properties
CHAN_API_BASE_URL=http://192.168.1.42:8000/
```

Thay địa chỉ mẫu bằng địa chỉ thật. Backend phải lắng nghe tại `0.0.0.0:8000` và tường lửa phải cho phép TCP 8000. Điện thoại thật không thể dùng `localhost` hoặc `10.0.2.2` để truy cập máy tính.

### Kiểm thử trên điện thoại

1. Cài APK, khởi động backend, dán văn bản vào CHAN và kiểm tra kết quả.
2. Thử giọng nói tiếng Việt, chỉnh sửa kết quả nhận dạng rồi gửi.
3. Mở **Bảo vệ**, bật **Kiểm tra thông báo Zalo** và cấp quyền.
4. Gửi tin Zalo bình thường; ứng dụng không nên cảnh báo.
5. Gửi tin thử có dấu hiệu lừa đảo rõ ràng; ứng dụng nên cảnh báo.
6. Gửi nội dung thử yêu cầu OTP; phải cảnh báo nguy cơ cao và không gọi `/v1/analyze`.
7. Tắt Wi-Fi và thử lại OTP; bảo vệ cục bộ vẫn phải hoạt động.
8. Thu hồi quyền micro hoặc Truy cập thông báo; ứng dụng vẫn phải dùng được và hiển thị đúng trạng thái.

Không dùng mật khẩu, OTP, thông tin ngân hàng hoặc dữ liệu cá nhân thật để thử.