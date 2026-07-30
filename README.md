# CHAN — Android

Native Android client for CHAN, a scam-detection assistant written for
Vietnamese adults aged 55+. Kotlin, Jetpack Compose, Material 3.

> [English setup and testing](#building) | [Hướng dẫn tiếng Việt](#hướng-dẫn-cài-đặt-và-kiểm-thử)

## Sprint 03 demo APK

The Android demo build connects to the hosted CHAN API at
`https://chan-flame.vercel.app/api/`.

- [Download the CHAN demo APK](https://github.com/lystiger/CHAN/releases/download/sprint03-demo/app-debug.apk)
- [Morning installation and phone setup](docs/FRIEND_INSTALL.md)

This is a debug-signed APK for the private team demo, not a Play Store release.

Current sprint: **Sprint 03** (`0.3.0-sprint03`, `versionCode` 3) — speech
reliability, truthful live protection status, and repeated Zalo detections. See
`docs/sprint-03-android-claude-code.md`.

Sprint 02 (`0.2.0-sprint02`) added live backend integration, passive Zalo
notification protection, and Vietnamese speech-to-text.

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
| debug | `-PCHAN_API_BASE_URL`, then `CHAN_API_BASE_URL` in `local.properties` | `http://10.0.2.2:8000/` |
| release | `-PCHAN_RELEASE_API_BASE_URL` only | **none — the build fails** |

Gradle loads `gradle.properties` by itself but **not** `local.properties`. The
`local.properties` form works because `app/build.gradle.kts` reads that file
explicitly (`localProperty(…)`); the command-line `-P` value wins when both are
present. Only the key `CHAN_API_BASE_URL` is read — no other key in
`local.properties` reaches the build. A release URL must be passed on the
command line, so a LAN address cannot reach a release build.

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
   │      └── RecognizerProvider             ON_DEVICE / DEVICE_SERVICE stages
   │
   ├── ProtectionRuntimeMonitor              listener liveness in this process
   │      ├── EffectiveProtection            preference + grant + connection
   │      ├── ProtectionReconnectController  one bounded rebind per resume
   │      └── ProtectionStatusNotifier       low-importance ongoing indicator
   │
   └── ZaloNotificationListenerService
          └── NotificationPipeline           pure, JVM tested end to end
                 ├── NotificationContentExtractor
                 ├── NotificationOccurrenceCache  digest + occurrence token
                 ├── LiveChanRepository           one bounded attempt
                 ├── PendingAlertStore            newest redacted result
                 └── SafeAlertPublisher           fresh, rotating alert events
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

- The listener's current connection is never persisted as a boolean.
- The ongoing status notification has no parameter that could carry content.
- No audio is recorded or stored; dictation is one utterance via the platform.
- Analyze requests have no transport-level retry.

`app/src/test/resources/l0-l1-parity-vectors.json` pins the Kotlin L0/L1 port to
the behaviour of the TypeScript engine over the same Rule Bundle.

---

## Speech: on-device first, fallback only by consent

CHAN asks Android for an **on-device** recognizer first (API 31+) and shows
*"Đang nghe trên máy…"* only while that one is genuinely running.

A recognizer that is reported as available is not assumed to work. If it fails
after starting — its service disconnects, its Vietnamese model is unavailable,
the provider rejects the request — CHAN destroys the handle immediately, keeps
no audio, and explains what happened:

> Nhận giọng nói trên máy chưa hoạt động. Bác có thể thử lại, dán chữ, hoặc đồng
> ý dùng dịch vụ giọng nói của máy.

The phone's own speech service is offered as a choice, never taken
automatically, and always under the privacy consequence:

> Dịch vụ giọng nói của máy có thể gửi âm thanh đến nhà cung cấp để nhận dạng.
> CHAN không lưu bản ghi âm.

The three actions are *Dùng dịch vụ giọng nói của máy*, *Thử lại trên máy*, and
*Để sau*. Consent applies to that one attempt; it is not remembered. While a
consented fallback is listening the status reads *"Đang dùng dịch vụ giọng nói
của máy…"* — the on-device claim is never made for it. If that also fails, CHAN
stops and returns to paste/image input rather than bouncing between providers.

The recognizer is destroyed exactly once at every terminal boundary (final
result, error, cancel, leaving the screen), and the final text always lands in
the editable field. Nothing is ever analyzed until *Kiểm tra ngay* is pressed.

---

## Protection: permission, preference, and a live connection are three things

Sprint 02 treated Android's Notification Access grant as proof that CHAN was
protecting the user. On a real phone the grant was on while the listener was not
bound, and every screen still showed green. Sprint 03 separates the layers:

| Layer | What it means |
|---|---|
| Quy tắc trên máy | The on-device rule engine, always running |
| Lựa chọn trong CHAN | The in-app scanning preference (default **off**) |
| Quyền Truy cập thông báo | Android's Notification Access grant — a *setting* |
| Kết nối ngay lúc này | `onListenerConnected` happened in **this** process |
| Cảnh báo của CHAN | Whether CHAN may post its own warnings |

"Listener connected" means exactly one thing: `onListenerConnected()` was
delivered to CHAN's `NotificationListenerService` in the currently running
process, and no disconnect or destroy has happened since. It starts *unknown* in
every new process and is never restored from storage. Only `lastConnectedAt` is
persisted, and only as history ("Kết nối gần nhất lúc 18:42").

The resulting states are:

- `Bảo vệ Zalo đang tắt` — the preference is off;
- `Cần bật Truy cập thông báo` — preference on, grant missing;
- `Đang kết nối bảo vệ Zalo…` — granted, no listener callback yet;
- `Đang thử kết nối lại…` — a rebind the user asked for is outstanding;
- `Android chưa kết nối CHAN với thông báo Zalo` — not connected;
- `CHAN đang bảo vệ thông báo Zalo` — connected and able to warn;
- `Đang kiểm tra nhưng chưa thể hiện cảnh báo` — connected, warnings denied.

### When Android will not bind the listener

Physical testing on the Xiaomi found the state that matters: CHAN's process
alive, scanning on, Notification Access granted, and CHAN absent from Android's
live listener list for over thirty seconds — with `requestRebind()` producing no
callback at all. The platform is free to ignore that request, and on this device
it does.

CHAN therefore does not describe it as a connection that dropped. The screen
names the actor, rules out what a worried person would otherwise go and check,
and leads with the remedy that actually works:

> **Android chưa kết nối CHAN với thông báo Zalo**
> Đây không phải lỗi mạng hay lỗi đăng nhập Zalo.
> Bác tắt CHAN rồi bật lại trong màn hình này, sau đó quay về ứng dụng.
> **[ Mở cài đặt Truy cập thông báo ]**  [ Kết nối lại ]

When the app comes forward with the preference on, access granted, and no live
listener, CHAN still requests **one** rebind and says *"Đang thử kết nối lại…"*
while it is outstanding — with the reconnect control disabled, because a second
request to a system already ignoring the first changes nothing. There is no
retry loop, alarm, or background job.

If no `onListenerConnected` arrives within five seconds, CHAN stops claiming to
be connecting and shows the state above. That window bounds *the claim*, not the
platform: waiting longer does not make an ignored `requestRebind` any less
ignored, which is why the fix offered is the manual toggle rather than a longer
timeout. `Kết nối lại` remains available underneath it, because it costs nothing
on the devices where it does work.

### The ongoing status notification

While — and only while — the preference is on, access is granted,
`onListenerConnected` has occurred in this process, and CHAN may post
notifications, it publishes one ongoing indicator on a low-importance channel
(`chan_protection_status`, *Trạng thái bảo vệ*, no sound, private on the lock
screen):

> **CHAN đang bảo vệ Zalo** — Chạm để xem trạng thái bảo vệ.

It contains no sender, message, or evidence, and tapping it opens the protection
screen. It is cancelled when protection is paused, access is revoked, the
listener disconnects, or the service is destroyed, and a stale one left by a
killed process is cancelled at startup before any state is reported. It is an
indicator, not a promise that Android will never kill the process.

### After clearing app data

Clearing CHAN's app data resets the in-app scanning preference to **off**. On
the next launch protection reads *"Bảo vệ Zalo đang tắt"* with a setup action,
even if Android still lists CHAN under Notification Access. CHAN never silently
resumes reading notifications after that reset.

---

## Repeated Zalo detections

Sprint 02 suppressed a digest of package + notification key + content for ten
minutes, so a second scam message with the same wording was indistinguishable
from Android repeating one callback — and never warned about. It also reused one
notification id, which Android treats as an update to a warning the user has
already seen rather than a new event.

Sprint 03 hashes *when the message happened* alongside what it said. The
occurrence token is the newest `MessagingStyle.Message.timestamp`, falling back
to the notification's `postTime`, folded together with the notification key and
the normalized-content digest. So:

- the same callback delivered twice is analyzed once;
- a read receipt or ranking update does not re-analyze anything;
- a genuinely new message is analyzed, **including** identical text;
- different text in the same conversation is never suppressed.

Each `HIGH` or `MEDIUM` outcome then publishes a *fresh* alert event with a
rotating notification id from a bounded ring of three, cancelling the previous
warning as the new one is posted — one visible CHAN warning, but a new event the
OS is free to raise again. The newest redacted result replaces the old one
before its notification exists, and each warning carries its own PendingIntent
identity so a tap can never open an older result.

A backend failure, an unknown result, a duplicate, or a disconnect never stops
later callbacks from being processed: the listener's coroutine scope is rebuilt
if it was cancelled, and no single-flight flag survives a failure.

The protection screen shows content-free evidence of all this — *"Hoạt động gần
nhất lúc 21:03"* and the last warning time. Debug builds additionally show the
last outcome category (`DUPLICATE`, `LOCAL_OTP`, `BACKEND_FAILURE`,
`ALERT_POSTED`, …). No sender, message, account, link, or request body is
recorded anywhere.

---

## Manual physical-phone checklist

**Not executed by the build.** An APK is not evidence that notification access,
Zalo extraction, networking, or the phone's speech provider works. A human must
perform and record these steps on a real handset.

Build with the debug API URL pointing at the computer's LAN address, start the
backend, and confirm `/readyz` answers `ready` before beginning.

1. Install the debug APK manually on the Xiaomi Android 15 phone.
2. Confirm microphone and notification permissions are requested only in
   context — never at first launch.
3. Tap speech, speak a Vietnamese sentence, edit the result, and manually tap
   *Kiểm tra ngay*.
4. If on-device recognition fails, confirm CHAN asks before using the device
   speech service.
5. Deny that fallback and confirm paste/image still work.
6. Accept it and confirm one-shot dictation returns editable Vietnamese text.
7. Confirm no dictated text appears in Logcat or app storage.
8. Enable Zalo protection and confirm Home and **Bảo vệ** show *"CHAN đang bảo
   vệ Zalo"* only after the listener connects.
9. Confirm the low-importance ongoing status notification appears and opens the
   protection screen.
10. Revoke Notification Access and confirm the active indicator disappears.
11. Re-enable access and use *Kết nối lại*; confirm the listener becomes active
    without reinstalling. If it does not, confirm the screen reads *"Android
    chưa kết nối CHAN với thông báo Zalo"*, that a second tap is refused while
    an attempt is outstanding, and that toggling CHAN off and on inside
    Notification Access does restore it.
12. Clear app data, reopen CHAN, and confirm protection is visibly off and is
    not silently restored.
13. With protection active, send a synthetic high-risk Zalo message and confirm
    `/v1/analyze` returns 200 and CHAN warns.
14. Dismiss the warning, then send a second, *different* synthetic high-risk
    message in the same conversation; confirm a second analyze request and a
    fresh heads-up warning.
15. Send the exact same synthetic high-risk text again as a new message; confirm
    it is treated as a new occurrence and warns again.
16. Cause Zalo to update the same notification without a new message; confirm it
    creates no further analyze request or warning.
17. Send a synthetic OTP request and confirm a high warning with **zero**
    analyze requests, including with Wi-Fi off.
18. Send a benign Zalo message — no warning expected.
19. Hide notification content on the lock screen — the app must not crash or
    invent content.
20. Deny CHAN's notification permission — the status must read *"Đang kiểm tra
    nhưng chưa thể hiện cảnh báo"*.

Do not use real OTPs, passwords, banking details, or personal data in tests.

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

Máy ảo dùng mặc định `http://10.0.2.2:8000/`. Với điện thoại thật, điện thoại và máy tính phải cùng mạng. Thêm IPv4 LAN của máy tính vào `local.properties` (bản build đọc đúng khoá này):

```properties
CHAN_API_BASE_URL=http://192.168.1.42:8000/
```

hoặc truyền cho một lần build:

```powershell
.\gradlew.bat assembleDebug -PCHAN_API_BASE_URL=http://192.168.1.42:8000/
```

Thay địa chỉ mẫu bằng địa chỉ thật. Backend phải lắng nghe tại `0.0.0.0:8000` và tường lửa phải cho phép TCP 8000. Điện thoại thật không thể dùng `localhost` hoặc `10.0.2.2` để truy cập máy tính.

### Ba lớp bảo vệ khác nhau

- **Lựa chọn trong CHAN**: công tắc trong ứng dụng, mặc định tắt. Xoá dữ liệu ứng dụng sẽ đưa nó về tắt và CHAN không tự bật lại.
- **Quyền Truy cập thông báo**: quyền của Android. Đây chỉ là một cài đặt.
- **Kết nối ngay lúc này**: hệ thống đã thực sự nối dịch vụ của CHAN trong tiến trình đang chạy. Chỉ khi có kết nối thật, CHAN mới báo *"CHAN đang bảo vệ thông báo Zalo"* và mới hiện thông báo trạng thái thường trực.

Khi mất kết nối, CHAN xin nối lại **một lần**, chờ 5 giây, rồi hiện nút *Kết nối lại* để bác tự bấm.

### Kiểm thử trên điện thoại

1. Cài APK, khởi động backend, dán văn bản vào CHAN và kiểm tra kết quả.
2. Thử giọng nói tiếng Việt, chỉnh sửa kết quả nhận dạng rồi bấm **Kiểm tra ngay**.
3. Nếu nhận giọng nói trên máy hỏng, CHAN phải hỏi trước khi dùng dịch vụ giọng nói của máy.
4. Mở **Bảo vệ**, bật **Kiểm tra thông báo Zalo** và cấp quyền.
5. Gửi tin Zalo bình thường; ứng dụng không nên cảnh báo.
6. Gửi tin thử có dấu hiệu lừa đảo rõ ràng; ứng dụng nên cảnh báo.
7. Gửi tiếp tin thử **khác** trong cùng cuộc trò chuyện; phải có cảnh báo mới.
8. Gửi lại đúng nội dung cũ như một tin mới; vẫn phải cảnh báo lần nữa.
9. Gửi nội dung thử yêu cầu OTP; phải cảnh báo nguy cơ cao và không gọi `/v1/analyze`.
10. Tắt Wi-Fi và thử lại OTP; bảo vệ cục bộ vẫn phải hoạt động.
11. Thu hồi quyền micro hoặc Truy cập thông báo; ứng dụng vẫn phải dùng được và hiển thị đúng trạng thái.
12. Xoá dữ liệu ứng dụng, mở lại CHAN; bảo vệ phải hiện là đang tắt.

Không dùng mật khẩu, OTP, thông tin ngân hàng hoặc dữ liệu cá nhân thật để thử.
