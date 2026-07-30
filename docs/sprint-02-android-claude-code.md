# Sprint 02 — Zalo notifications, live backend, and speech-to-text

Give Claude Code this instruction from a Windows terminal opened at
`D:\Projects\CHAN`:

> Read `docs/sprint-02-android-claude-code.md` completely, inspect the existing
> Sprint 01 project, then implement Sprint 02 autonomously. Run unit tests,
> lint, and `assembleDebug`. Stop after producing and inspecting the APK. Do
> not install it on a phone or emulator.

## Role and working agreement

You are the Android developer for CHAN. Extend the existing Sprint 01 Kotlin
and Jetpack Compose application; do not rebuild it from scratch.

The project is currently not a Git repository. Preserve all existing files and
do not initialize Git, delete build outputs, or make unrelated upgrades unless
explicitly necessary for Sprint 02.

Before editing, read:

- `docs/sprint-01-android-claude-code.md`
- `app/src/main/java/com/chan/app/domain/`
- `app/src/main/java/com/chan/app/ui/`
- `app/src/main/AndroidManifest.xml`
- all Gradle files

If the product repository is available, also read:

- `repo/docs/API.md`
- `repo/docs/CHAN-ARCHITECTURE.md`
- `repo/codebase/rules/bundle.json`
- `repo/codebase/apps/web/src/api.ts`
- `repo/codebase/apps/web/src/engine.ts`
- `repo/codebase/gateway/src/chan_api/schemas.py`

Do not ask routine coding questions. Make conservative choices from this
contract and report assumptions at the end.

## Current baseline

Sprint 01 already contains:

- Kotlin, Compose, Material 3, and a ViewModel/state-holder architecture
- nine product screen states and four bottom-navigation destinations
- text/image Android share intents with confirmation
- demo analysis and lookup repositories
- dark-mode persistence
- an APK at `app/build/outputs/apk/debug/app-debug.apk`
- passing local unit tests

Sprint 02 must retain all Sprint 01 behavior while replacing demo-only
analysis/lookup paths with production-shaped integration.

Increment:

- `versionCode` from `1` to `2`
- `versionName` from `0.1.0-sprint01` to `0.2.0-sprint02`

## Sprint goal

Build a debug APK that:

1. receives Zalo notification content after explicit notification-access
   consent;
2. performs local privacy filtering and sends only qualifying content to the
   CHAN backend;
3. renders real `/v1/analyze` and lookup responses;
4. lets the user dictate Vietnamese text, review it, and explicitly submit it;
5. works safely when permissions, speech recognition, or the backend are
   unavailable.

## Non-negotiable privacy invariants

1. Never log or persist raw notification text, dictated text, manually entered
   text, OTPs, phone numbers, account numbers, URLs, or lookup values.
2. An OTP match is decided locally. Raw OTP content must never be sent to the
   backend.
3. Approximately low-risk notifications must stop locally at the L1 gate; do
   not send every Zalo notification to the server.
4. Only monitor `com.zing.zalo` in Sprint 02.
5. Notification access and microphone access require separate, contextual,
   explicit consent.
6. Speech recognition must never begin in the background.
7. Dictated text must remain editable and must never be analyzed until the
   user taps `Kiểm tra ngay`.
8. Never add a `SAFE` risk. Backend `unknown` means
   `Chưa phát hiện dấu hiệu`, not safety.
9. Do not add body-level HTTP logging. Error reporting must contain only status,
   safe error code, request ID if available, and timing.
10. Do not put raw source content into CHAN's own warning notification or onto
    the lock screen.

## Architecture to implement

Keep the existing `ChanRepository` seam, but split responsibilities:

```text
Compose UI
   │
   ├── ChanViewModel
   │     └── LiveChanRepository
   │            ├── LocalRuleEngine
   │            ├── ChanApi
   │            ├── DeviceTokenStore
   │            └── RuleBundleStore
   │
   ├── SpeechToTextController
   │
   └── ZaloNotificationListenerService
          ├── NotificationContentExtractor
          ├── NotificationGate / LocalRuleEngine
          ├── LiveChanRepository
          └── SafeAlertPublisher
```

Use constructor injection manually or follow the existing simple architecture.
Do not add Hilt solely for this sprint.

## Part A — live backend integration

### A1. Dependencies

Use stable dependencies compatible with the current project:

- Retrofit
- OkHttp
- Kotlin serialization converter or Moshi
- kotlinx-coroutines Android
- MockWebServer for API tests

Do not add an HTTP logging interceptor. If one is already introduced during
implementation, configure it to log no request or response bodies and justify
why it remains.

### A2. Base URL configuration

Never hardcode a production URL or secret in Kotlin.

Expose a `BuildConfig.CHAN_API_BASE_URL`:

- debug default for Android emulator: `http://10.0.2.2:8000/`
- physical phone: overridable from an uncommitted local Gradle property such
  as `CHAN_API_BASE_URL=http://192.168.x.x:8000/`
- release: require an explicit HTTPS URL and fail the release build if missing

Document in `README.md` that a physical phone cannot use `localhost` or
`10.0.2.2`; it must use the development computer's LAN address, with Docker
and the phone on the same reachable network.

Permit cleartext traffic only in the debug build using a debug-only network
security configuration. Release must reject cleartext.

### A3. Device token

Implement:

```http
POST /v1/devices/token
Content-Type: application/json

{"platform":"android","push_token":null}
```

Store the returned token using an Android Keystore-backed implementation. The
token is returned only once and normally expires after 90 days.

All authenticated requests use:

```http
Authorization: Bearer <device-token>
```

On one `401` only:

1. remove the invalid token;
2. issue a new token;
3. retry the original request once.

Never retry a second `401`. Deduplicate concurrent token creation so several
requests do not issue several device identities.

Do not use a compile-time API key. The Android client uses only its issued
device token.

### A4. Rule Bundle and local engine

Implement:

```http
GET /v1/rules/bundle
```

Requirements:

- package a known-good bootstrap Rule Bundle in `app/src/main/assets/`;
- on startup, use the cached server bundle if valid, otherwise bootstrap;
- refresh in the background using `ETag` and `If-None-Match`;
- validate the schema and bundle version before an atomic replacement;
- never leave the app without a usable bundle after a failed refresh.

Port the L0/L1 behavior from the web engine:

- Unicode NFKC normalization
- invisible-character removal
- lowercase using Vietnamese locale behavior
- whitespace collapse
- accent-insensitive matching copy
- teencode substitutions from the bundle
- OTP block
- local signal matching
- local gate score and `always_call_when_local_signal`

The Rule Bundle is the source of truth. Do not hardcode scam regexes in Kotlin.

Local outcomes:

- OTP match → local `HIGH`, no network call, empty evidence
- below the gate → local `UNKNOWN`, no network call
- at/above the gate → call `/v1/analyze`

Cache no message content. Bundle data itself is safe to persist.

### A5. Analyze API

Implement:

```http
POST /v1/analyze
Authorization: Bearer <token>
Content-Type: application/json
```

Exact request fields:

```json
{
  "text": "raw content for this one request only",
  "source": "android",
  "input_mode": "manual",
  "app_package": null,
  "local_signals": [],
  "truncated": false,
  "locale": "vi-VN"
}
```

Allowed `input_mode` values used this sprint:

- manual text and reviewed speech: `manual`
- Android share sheet: `share`
- Zalo notification: `notification`

For a Zalo notification:

```json
{
  "source": "android",
  "input_mode": "notification",
  "app_package": "com.zing.zalo"
}
```

Map the response into domain models without Android resource IDs in the data
layer. The UI maps signal codes to localized labels:

- `mao_danh_tham_quyen`
- `de_doa`
- `ap_luc_thoi_gian`
- `yeu_cau_bi_mat`
- `yeu_cau_otp`
- `tk_ca_nhan`
- `link_gia`
- `loi_hua_loi_ich`

Preserve unknown future signal codes as a generic, accessible row instead of
crashing.

Render backend:

- `risk`
- `score`
- `signals`
- `explanation`
- `questions`
- `verified_hotline`
- `actions`
- `engine_version`
- `rule_bundle_version`

Evidence returned by the backend is already redacted. Do not attempt to restore
placeholders such as `<ACCOUNT>` or `<AMOUNT:trieu>`.

### A6. Lookup API

Replace demo lookup with the real k-anonymity flow:

1. normalize locally by type;
2. calculate:
   `SHA256("chan:" + kind + ":v1:" + normalizedValue)`;
3. send only the first five lowercase hex characters as `prefix`;
4. compare full returned hashes locally;
5. discard the raw lookup value after leaving the result flow.

Never send the raw account, phone, or URL to the lookup endpoint.

Use:

```http
GET /v1/lookup/{account|phone|url}?prefix=<five-hex-prefix>
Authorization: Bearer <token>
```

Keep the disclaimer:

`Đây là báo cáo của người dùng, không phải kết luận chính thức. Không có báo cáo không có nghĩa là an toàn.`

### A7. User-safe backend states

Add normal-language states with an alternate path:

- offline:
  `CHAN vẫn kiểm tra quy tắc trên máy, nhưng chưa kết nối được danh sách báo cáo.`
- timeout:
  `Máy chủ trả lời chậm. Bác thử lại hoặc hỏi người thân trước khi làm tiếp.`
- rate limit:
  `Bác đã kiểm tra nhiều lần liên tiếp. Xin đợi một chút rồi thử lại.`
- backend unavailable:
  `Dịch vụ phân tích đang tạm nghỉ. Bác đừng chuyển tiền nếu vẫn còn nghi ngờ.`
- bundle mismatch:
  refresh the bundle once; if still mismatched, stop the request and show a
  retry path

Never expose stack traces, JSON, HTTP codes, or internal identifiers in the UI.

## Part B — Zalo notification protection

### B1. Manifest service

Add a service derived from `NotificationListenerService`:

```xml
<service
    android:name=".notification.ZaloNotificationListenerService"
    android:exported="false"
    android:label="@string/notification_access_service_label"
    android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE">
    <intent-filter>
        <action android:name="android.service.notification.NotificationListenerService" />
    </intent-filter>
    <meta-data
        android:name="android.service.notification.default_filter_types"
        android:value="conversations|alerting" />
    <meta-data
        android:name="android.service.notification.disabled_filter_types"
        android:value="ongoing|silent" />
</service>
```

`BIND_NOTIFICATION_LISTENER_SERVICE` is a system-bound service permission, not
a runtime permission dialog. The user must explicitly enable CHAN in Android's
Notification Access settings.

Do not add `READ_SMS`, contacts, accessibility, call-log, storage, or Zalo
account permissions.

### B2. Consent UI

Extend `Bảo vệ & riêng tư`:

- switch/card: `Kiểm tra thông báo Zalo`
- status: `Chưa bật`, `Đang bảo vệ`, or `Đã tắt trong cài đặt máy`
- explanation before leaving the app:
  `Khi bác bật, CHAN chỉ đọc thông báo từ Zalo để tìm dấu hiệu thúc ép. Nội dung không được lưu.`
- primary action opens Android Notification Access settings
- on returning to the foreground, refresh actual access state

Use the platform's enabled-listener state; do not assume access was granted
because the settings screen was opened.

Add a separate local preference allowing the user to pause Zalo scanning even
while system notification access remains granted.

Provide `Tắt bảo vệ Zalo` in the app. It disables processing immediately and
may guide the user back to system settings to revoke access.

### B3. Extract notification text safely

Create a pure/testable `NotificationContentExtractor`. Consider:

- `Notification.EXTRA_BIG_TEXT`
- `Notification.EXTRA_TEXT`
- `Notification.EXTRA_TEXT_LINES`
- `Notification.EXTRA_TITLE`
- messaging-style messages when exposed by Android

Rules:

- accept only package `com.zing.zalo`;
- ignore CHAN's own package;
- ignore empty content;
- ignore ongoing service notifications;
- ignore group-summary duplicates;
- collapse repeated title/body segments;
- cap input to the API's 4,000-character maximum;
- never print extracted content to Logcat;
- release references to the notification object after processing.

Do not read Zalo's private files, database, accessibility tree, or network
traffic. Notification access is the only passive input for Sprint 02.

### B4. Truncation and deduplication

Set `truncated=true` if available content appears shortened, including:

- an ellipsis/truncation marker;
- a notification summary indicating additional messages;
- text-line aggregation where only the latest lines are available;
- other deterministic markers from the shared Rule Bundle.

Do not claim truncation merely because a message is short.

Deduplicate notification updates by a SHA-256 digest of:

```text
package + notification key + normalized extracted content
```

Keep only digests and timestamps, never raw content. Use a bounded in-memory
TTL cache so edits/updates are not repeatedly analyzed. Process death may reset
the cache; that is acceptable for Sprint 02.

### B5. Service processing

Notification callbacks arrive on the main thread on supported project API
levels. Offload local matching and any network request to a structured
coroutine scope owned by the service. Cancel it in `onDestroy`.

Pipeline:

```text
Zalo notification
  → consent and package checks
  → safe extraction
  → dedupe
  → L0/L1 on device
      → OTP: local high, never network
      → below gate: stop silently
      → above gate: POST /v1/analyze
  → publish CHAN warning for high/medium only
```

Network failure must not retry indefinitely in the background. Use one bounded
attempt. Do not enqueue raw content in WorkManager or persist it for later.

### B6. CHAN warning notifications

To publish CHAN's own warnings on Android 13+, request
`POST_NOTIFICATIONS` contextually when the user enables Zalo protection.

Create two channels:

- `chan_high_risk` — high importance
- `chan_caution` — default importance

Warning content must be generic:

- high title: `CHAN phát hiện nguy cơ cao`
- high body: `Đừng chuyển tiền hoặc đọc mã OTP. Mở CHAN để xem lý do.`
- medium title: `Tin nhắn cần cẩn trọng`
- medium body: `Mở CHAN để kiểm tra trước khi làm theo.`

Set lock-screen visibility to private. Do not include Zalo sender, message
text, phone, account, URL, or evidence in the notification.

Tapping the warning opens the matching result screen. Transfer only a redacted
domain result. If persistence is required across process death, store a
minimal, redacted result with a short expiry and delete it after display.
Never store raw source content.

Do not implement a full-screen intent in Sprint 02. Use a high-importance
heads-up notification where the OS permits it; full-screen intents have stricter
platform and distribution policy constraints.

If CHAN notification permission is denied, local scanning may continue only if
the user explicitly left protection enabled. Show the in-app status
`Đang kiểm tra nhưng chưa thể hiện cảnh báo` and an action to open notification
settings.

## Part C — Vietnamese speech-to-text

### C1. Permission and availability

Add only:

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

Request it only after the user taps the microphone control. Explain first:

`Micro chỉ nghe khi bác bấm nút. CHAN không lưu bản ghi âm.`

Add the recognition-service query required for Android 11+:

```xml
<queries>
    <intent>
        <action android:name="android.speech.RecognitionService" />
    </intent>
</queries>
```

If the permission is denied:

- keep paste/text input usable;
- show `Bác có thể dán chữ hoặc mở quyền micro trong Cài đặt.`;
- if permanently denied, provide an app-settings action.

### C2. On-device-first recognition

Create a lifecycle-aware `SpeechToTextController` behind an interface so it can
be unit tested.

On API 31+:

1. check `SpeechRecognizer.isOnDeviceRecognitionAvailable(context)`;
2. prefer `SpeechRecognizer.createOnDeviceSpeechRecognizer(context)`;
3. catch `UnsupportedOperationException`.

When on-device recognition is unavailable, do not silently use a recognizer
that may stream audio to a provider. Show:

`Máy này chưa có nhận giọng nói trên thiết bị. Bác có thể dán chữ, hoặc đồng ý dùng dịch vụ giọng nói của máy.`

Only after explicit confirmation may the app use
`SpeechRecognizer.createSpeechRecognizer(context)`.

Configure `RecognizerIntent`:

- action `ACTION_RECOGNIZE_SPEECH`
- language model `LANGUAGE_MODEL_FREE_FORM`
- language `vi-VN`
- partial results enabled
- offline preference enabled
- one user-initiated utterance, not continuous listening

The offline preference is a request to the provider, not a guarantee. The UI
copy must not promise on-device privacy unless the on-device recognizer factory
is actually used.

### C3. Lifecycle and UI state

All `SpeechRecognizer` calls occur on the main thread.

Call `setRecognitionListener` before `startListening`.
Always call `destroy()` when the controller is disposed. Cancel listening when
the app goes to the background or the input screen is left.

Represent at least:

- idle
- requesting permission
- listening
- receiving partial text
- final text
- no speech
- recognizer busy
- network/provider unavailable
- permission denied

While listening:

- show a large stop button and `Đang nghe…`;
- expose status through accessibility semantics;
- respect reduced-motion settings;
- never start analysis automatically.

Partial text may be visible but final text is copied into the normal editable
message field. The user must review and tap `Kiểm tra ngay`.

Do not record audio files and do not add a custom audio recorder.

## UI changes

### Message input

Replace the Sprint 01 non-functional voice affordance with:

- a large microphone button;
- current speech state;
- stop/cancel;
- fallback to paste or image;
- editable recognized text.

Keep image selection and share intake working.

### Protection screen

Show separate status cards:

1. local rules available/offline;
2. Zalo notification access;
3. CHAN warning-notification permission.

Green may indicate that these system layers are active. It must not indicate
that a Zalo message is safe.

### Settings

Update the permission list with live states:

- Notification access
- CHAN warning notifications
- Microphone

Every item opens the appropriate system settings or contextual permission
flow. Do not request all permissions at first launch.

### Result screens

Render live backend results while preserving the Sprint 01 visual contract.
Add a visible note when a notification was truncated:

`Thông báo có thể chưa đủ nội dung. Bác mở Zalo và chia sẻ cả tin nhắn để kiểm tra kỹ hơn.`

Do not display a green result for `unknown`.

## Error handling and resilience

- Use explicit timeouts appropriate for an interactive mobile request.
- Cancel in-flight manual analysis when the screen/ViewModel is cleared.
- Do not automatically retry non-idempotent analysis requests.
- A manual retry must be user initiated.
- Notification analysis has one bounded attempt and drops raw content
  afterward.
- Backend errors never crash the notification listener.
- Speech errors always return the user to an editable text input.
- App restart must not retain raw shared, dictated, or notification content.

## Tests

Keep all Sprint 01 tests passing and add:

### Unit tests

1. Device token is requested with `platform=android`.
2. Concurrent authenticated calls issue only one token.
3. One `401` reissues a token and retries once.
4. A second `401` stops.
5. Analyze request uses exact schema and no extra fields.
6. Manual/share/notification map to correct `input_mode`.
7. Notification request uses `app_package=com.zing.zalo`.
8. OTP produces local high and makes zero HTTP requests.
9. Below-gate content makes zero HTTP requests.
10. Above-gate content sends only allowed local signal names.
11. Rule Bundle falls back to bootstrap when refresh fails.
12. ETag `304` retains the cached bundle.
13. Kotlin L0/L1 matches the shared parity vectors.
14. Lookup sends only a five-character hash prefix.
15. Full lookup matching happens locally.
16. Notification extractor combines big text/text lines without duplication.
17. Non-Zalo notifications are ignored.
18. Group summaries, ongoing, empty, and duplicate notifications are ignored.
19. Raw notification text is absent from persisted state.
20. Safe alert text contains no raw sender or message content.
21. Speech controller prefers on-device recognition when available.
22. Speech fallback requires explicit confirmation.
23. Final speech remains editable and does not auto-analyze.
24. Leaving the screen destroys/cancels the recognizer.

Use MockWebServer or equivalent for HTTP behavior. Use fakes around Android
speech and notification framework classes so most tests run on the JVM.

### Static/privacy checks

Add a test or Gradle verification that fails if:

- `DemoChanRepository` is the production default;
- `Risk.SAFE` appears;
- body logging is enabled;
- a production base URL is cleartext;
- `READ_SMS`, contacts, accessibility, storage, or call-log permission appears;
- raw-content field names appear in a persistence entity.

### Manual physical-phone checklist

Document but do not execute:

1. Install the debug APK manually.
2. Point debug API URL to the computer's LAN address.
3. Start the Docker stack and confirm `/readyz`.
4. Open CHAN and enable Zalo protection.
5. Confirm Android shows CHAN under Notification Access.
6. Send a benign Zalo message from another account: no warning expected.
7. Send a clearly manipulative test message: warning expected.
8. Send an OTP-request test: high warning with no backend analyze request.
9. Turn Wi-Fi off: local OTP protection still works.
10. Hide notification content on the lock screen: app must not crash or invent
    content.
11. Disable Zalo notifications: protection screen must explain that passive
    scanning cannot operate.
12. Deny CHAN notification permission: in-app status explains warnings cannot
    be shown.
13. Deny microphone: paste/image paths remain usable.
14. Dictate Vietnamese, edit the text, then submit manually.
15. Revoke Notification Access: CHAN updates status after returning.

## Backend development setup

The backend lives in the product repository, not this Android project.

Start it from Windows PowerShell:

```powershell
wsl -d Ubuntu -- bash -lc 'cd /home/lystiger/projects/Batch03-K3-AI-Product-Hackathon-TeamLuaDao/repo/codebase && docker compose up --build -d'
```

Verify:

```powershell
Invoke-RestMethod http://localhost:8000/readyz
```

For an emulator, use `http://10.0.2.2:8000/`.

For a physical phone, determine the Windows computer's LAN IPv4 address:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
  Select-Object InterfaceAlias,IPAddress
```

Use `http://<LAN-IP>:8000/` only in debug. The phone and computer must be on a
network that allows that connection. Do not weaken release network security.

## Build verification

From `D:\Projects\CHAN` in Windows PowerShell:

```powershell
.\gradlew.bat testDebugUnitTest
.\gradlew.bat lintDebug
.\gradlew.bat assembleDebug
```

Fix all implementation-caused errors and blocking lint findings. Existing
dependency-update warnings are not a reason for unrelated library upgrades.

Verify the artifact without installing:

```powershell
Get-Item .\app\build\outputs\apk\debug\app-debug.apk |
  Select-Object FullName,Length,LastWriteTime
```

If available, inspect package/version/SDK/permissions with `apkanalyzer` or
`aapt dump badging`. Confirm that only intended permissions and services are
present.

## Hard stop before device installation

Do not:

- run `adb install`;
- run any Gradle `install*` task;
- launch an emulator;
- press Android Studio Run;
- connect, authorize, or modify a phone;
- enable notification access on behalf of the user.

Stop after the debug APK is built and inspected. Report:

- architecture and major files changed;
- backend base-URL configuration;
- notification and microphone permissions added;
- tests, lint, and build results;
- APK path and size;
- limitations and manual phone checklist;
- exact final sentence:
  `Stopped before device installation, as requested.`

## Definition of done

Sprint 02 is complete in source when:

- Sprint 01 tests and UI still work;
- live repository is the production/debug default, not the demo repository;
- device token issuance and one-time 401 recovery work;
- L0/L1 runs on-device from the shared Rule Bundle;
- OTP and below-gate content make no backend call;
- manual/share/notification requests use the correct backend schema;
- lookup uses a five-hex prefix and local full-hash comparison;
- Zalo is the only passively monitored package;
- notification access is explicit and accurately reflected in UI;
- warning notifications contain no source content;
- Vietnamese speech is on-device-first and user initiated;
- speech output is editable and never auto-submitted;
- no prohibited permission is present;
- privacy and network tests pass;
- lint has no new blocking error;
- `assembleDebug` produces version `0.2.0-sprint02`;
- no installation has been attempted.

Sprint 02 is complete on a physical phone only after a human performs and
records the separate manual physical-phone checklist. An APK build alone is not
evidence that notification access, Zalo extraction, networking, or the device's
speech provider works on that phone.
