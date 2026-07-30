# Sprint 01 — Claude Code handoff for the CHAN Android app

Copy this file into the Android Studio project, open a terminal at that
project's root, and give Claude Code this instruction:

> Read this file completely, then implement it autonomously. Continue through
> coding, tests, and `assembleDebug`. Stop after producing and verifying the
> debug APK. Do not install or run the app on a phone or emulator.

## Your role

You are the Android mobile developer for CHAN. Implement Sprint 01 in the
Android Studio project that contains this file. Treat the existing Android
project as user-owned: inspect it first, preserve its package name and
architecture where practical, and do not overwrite unrelated work.

Work through the whole sprint without asking routine implementation questions.
Make conservative decisions from the source-of-truth documents. Ask only if
the project cannot be built without a genuinely missing product decision or
credential.

## Sources of truth

If this Android project is inside the CHAN product repository, read these files
before editing:

1. `repo/design/README.md` — colors, typography, spacing, components, screens,
   accessibility, wording, and dark mode.
2. `repo/docs/CHAN-ARCHITECTURE.md` — platform boundaries and privacy
   invariants.
3. `repo/codebase/apps/web/src/App.tsx` — reference interactions and Vietnamese
   demo copy. It is a behavior reference, not Android code to embed.
4. `repo/codebase/apps/web/src/styles.css` — visual reference when the design
   contract needs clarification.
5. `repo/codebase/TEAM_HANDOFF.md` — future shared API integration.
6. `repo/codebase/detection/src/chan_detection/schemas.py` — future request and
   response contract.

If those paths are not present in the Android project, use the requirements
below as the complete Sprint 01 contract. Do not block merely because the
reference repository is unavailable.

## Sprint goal

Produce a native Android debug APK that demonstrates the complete CHAN phone
app design and its main navigation flows for user testing.

The app is for Vietnamese adults aged 55+ who may be under pressure before
transferring money. It must prioritize large text, large touch targets, simple
Vietnamese, visible privacy promises, and immediate recommended actions.

Sprint 01 is a UI/interaction demo. It must not pretend that demo analysis or
demo community data is live production data.

## Required implementation approach

- Prefer Kotlin and Jetpack Compose with Material 3.
- If the existing app is already a well-structured XML/View app, preserve that
  architecture rather than rewriting the project solely to use Compose.
- Keep screen state in a ViewModel or the project's established state holder.
- Separate screen/UI code, theme tokens, navigation/state, and demo data.
- Persist the user's dark-mode choice locally.
- Use the existing project package/application ID.
- Respect system font scaling. Use minimum heights, not fixed heights that clip
  enlarged text.
- Support portrait phones from 360 dp wide upward.
- Do not add analytics, advertising, crash-reporting SDKs, or unnecessary
  permissions.
- Do not log message text, lookup values, shared content, analysis responses,
  OTPs, phone numbers, or account numbers.
- Do not request notification, SMS, contacts, accessibility, camera, microphone,
  or storage permissions in Sprint 01.
- Use Android's document/photo picker for image selection so broad storage
  permission is unnecessary.
- Use string resources for all user-facing text.

If the app does not already have navigation infrastructure, use a small,
maintainable Compose state/navigation implementation. Do not add a heavy
dependency for this small fixed flow unless the project already uses it.

## Scope

Implement these nine screen states plus the Android share entry:

1. Home
2. Message input
3. Android share confirmation sheet
4. Analyzing/loading
5. High-risk result
6. Community lookup form
7. Caution lookup result
8. Protection and privacy
9. Settings

The bottom navigation has four destinations:

- `Trang chủ`
- `Kiểm tra`
- `Bảo vệ`
- `Cài đặt`

The `Kiểm tra` tab remains selected throughout message analysis and community
lookup flows.

### 1. Home

Show:

- CHAN logo/wordmark.
- Greeting: `Chào bác Lý, mình cùng kiểm tra nhé.`
- Green system-status card: `Đang bảo vệ bác`.
- Primary action: `Tin nhắn đáng ngờ`.
- Secondary action: `Tài khoản, số điện thoại`.
- A recent demo item marked `CẦN CẨN TRỌNG`.
- A note that recent content is not stored.

Green is allowed here only because this is a system-protection status, not a
message-safety result.

### 2. Message input

Show:

- Back action with a touch target of at least 48 dp.
- Title: `Dán tin nhắn cần kiểm tra`.
- Text mode and image mode.
- A multiline text input.
- `Kiểm tra ngay`, disabled while the trimmed message is empty.
- Visible privacy box:
  `CHAN không lưu nội dung bác nhập. Mã OTP sẽ không bao giờ rời khỏi máy.`

Image mode must open Android's picker. For Sprint 01, selecting an image may
show a clearly labeled demo/selected state; do not claim real OCR succeeded if
OCR is not implemented.

Do not request microphone permission. A microphone/voice implementation is
outside this sprint.

### 3. Android share confirmation

Register the launcher activity (or a dedicated exported share activity) for:

- `ACTION_SEND` with `text/plain`
- `ACTION_SEND` with `image/*`

When CHAN receives shared content, show a modal bottom sheet before importing
it:

- Eyebrow: `CHIA SẺ TỪ ỨNG DỤNG KHÁC`
- Title: `Kiểm tra nội dung này?`
- Explanation that CHAN looks for pressure/manipulation and does not store the
  content.
- Actions: `Huỷ` and `Mở trong CHAN`.

On confirmation, open the message-input screen. Populate shared text. For a
shared image, retain only the URI needed for the active screen and do not copy
or upload it.

Handle a new share intent while the activity is already open.

### 4. Loading

Show a centered, accessible progress state:

- `Đang đọc tin nhắn…`
- `Máy đang tìm các câu thúc ép bác.`

For demo mode, transition to the result after a short deterministic delay.
Avoid infinite animation when the system requests reduced motion.

### 5. High-risk result

Use the fixed Sprint 01 demo result:

- Risk pill: `NGUY CƠ CAO`
- Title: `Nhiều dấu hiệu lừa đảo`
- First instruction:
  `Đừng chuyển tiền. Đừng đọc mã OTP.`
- Source card.
- Heading: `Trúng 4/8 dấu hiệu thao túng`.
- Render all eight signals in this exact order:
  1. Mạo danh cơ quan chức năng
  2. Doạ hậu quả pháp lý
  3. Ép gấp về thời gian
  4. Yêu cầu giữ bí mật
  5. Đòi mã OTP
  6. Yêu cầu chuyển tiền
  7. Đường link giả mạo
  8. Hứa lợi ích bất thường
- Mark demo hits for signals 1, 3, 4, and 6 and show evidence excerpts.
- Recommendation panel headed `Bác hãy hỏi lại họ`.
- Hotline row for `156`; tapping it may open `ACTION_DIAL` with `tel:156`.
- Secondary action: `Kiểm tra tin khác`.

The demo data must live outside the composable/view so it can later be replaced
by a repository/API response.

### 6. Community lookup

Show:

- Title: `Tra cứu trước khi chuyển`.
- Three choices: `Tài khoản`, `Điện thoại`, `Đường link`.
- Input appropriate to the selected type.
- `Tra cứu báo cáo`, disabled while input is empty.
- Visible privacy explanation:
  `Máy biến thông tin thành mã rút gọn. Hệ thống không nhận giá trị gốc bác nhập.`

This sprint uses demo results only. Do not make a real network call, and do not
log or persist the lookup value.

### 7. Caution lookup result

Show:

- Amber pill: `CẦN CẨN TRỌNG`.
- Title: `Đã có người báo cáo`.
- Instruction to stop and call a relative before transferring money.
- Demo statistics: `12 lượt báo cáo`, `3 ngày lần gần nhất`.
- A recommendation panel.
- This disclaimer exactly:
  `Đây là báo cáo của người dùng, không phải kết luận chính thức. Không có báo cáo không có nghĩa là an toàn.`
- Action to look up different information.

Never show a green `An toàn`, `Safe`, `OK`, or equivalent result. Do not infer
safety from an absent report.

### 8. Protection and privacy

Show:

- Title: `Bảo vệ & riêng tư`.
- Green system-status card: `Hai lớp chạy trên máy`.
- Commitments:
  - `Không lưu nội dung tin nhắn.`
  - `Không gửi mã OTP khỏi thiết bị.`
  - `Không âm thầm báo cho người khác.`
  - `Bác luôn có thể dừng chia sẻ.`
- Demo guardian card:
  `Độ · Con Trai`, receiving only high-risk alerts and no content.
- `Ngừng chia sẻ` as a demo action with a confirmation dialog. Keep this state
  local; do not contact anyone.

### 9. Settings

Show:

- Dark-mode switch with explanatory copy.
- A read-only permissions section explaining that Sprint 01 has not been
  granted microphone or image-library access.
- The privacy box:
  `CHAN không giám sát bí mật. Mọi quyền đều cần bác chủ động đồng ý.`

Do not include the web prototype's error-simulation switches in the APK. The
design contract marks them prototype-only.

## Visual contract

Create centralized theme tokens. Do not scatter raw colors through screens.

### Light colors

| Token | Value |
|---|---|
| screen background | `#F5F8FE` |
| information tint | `#EAF0FC` |
| divider | `#DCE6F8` |
| default border | `#C3D2EE` |
| disabled | `#93A6CC` |
| muted text | `#6B7C9E` |
| body text | `#4A5B85` |
| secondary heading | `#33436B` |
| brand | `#26339E` |
| raised brand | `#3A49C0` |
| danger | `#DC2626` |
| danger dark | `#991B1B` |
| danger surface | `#FEF2F2` |
| danger border | `#FCA5A5` |
| warning | `#D97706` |
| warning dark | `#92400E` |
| warning surface | `#FFFBEB` |
| warning border | `#FCD34D` |
| system-success | `#059669` |
| system-success dark | `#065F46` |
| system-success surface | `#ECFDF5` |
| system-success border | `#6EE7B7` |

### Dark colors

| Role | Value |
|---|---|
| screen background | `#0B1220` |
| card | `#17223C` |
| inner surface | `#111B31` |
| information tint | `#243252` |
| border | `#2E3D61` |
| brand heading | `#BACDF8` |
| strong heading | `#E3EAF9` |
| body | `#BCC9E2` |
| muted | `#8EA0C2` |
| primary button | `#3B4BD4` |
| disabled button | `#3A4A70` |

In dark mode, do not use `#26339E` as the main filled-brand surface; use
`#3B4BD4`.

Risk colors have semantic meaning:

- Red is only for high risk.
- Amber is only for medium/caution risk.
- Green is only for system protection, on-device protection layers, and a real
  OCR-success status.
- Green must never describe a message, caller, account, phone number, or link as
  safe.

### Type and sizing

- Use the system sans-serif/Inter if already bundled; do not add a network font
  dependency.
- Page title: 28 sp, extra bold.
- Risk hero: 30 sp, extra bold.
- Section title: 22 sp, extra bold.
- Card title: 20 sp, bold.
- Decision-making body copy: at least 18 sp.
- Captions/meta may be 15–16 sp.
- Eyebrow labels may be 13–14 sp.
- Never use text smaller than 13 sp.
- Respect the device font scale and verify layouts at 1.3×.

### Layout and interaction

- Standard horizontal screen padding: 20 dp.
- Major section gaps: 20–22 dp.
- Card gaps: 10–12 dp.
- Primary CTA: full width, at least 64 dp high, 16 dp corners.
- Secondary buttons: at least 52–56 dp high.
- Every touch target: at least 48×48 dp.
- Bottom navigation item: at least 56 dp high.
- Default card corners: 14–16 dp.
- Bottom sheet top corners: 24 dp.
- Do not communicate state by color alone; always include text and/or an icon.
- Add content descriptions to icon-only controls.
- Use short Vietnamese sentences, address the person as `bác`, and refer to the
  product as `CHAN` in the logo or `CHẮN` in prose.
- Do not use technical terms such as `k-anonymity` in the main flow.

## Demo data and future integration seam

Create an interface such as `ChanRepository` with a demo implementation. Exact
names may follow the project's conventions.

It should expose:

- analyze message
- lookup account/phone/URL

The UI must consume typed domain models with risk restricted to:

- `HIGH`
- `MEDIUM`
- `UNKNOWN`

Do not add a `SAFE` risk.

Keep the future request mapping documented near the interface, but do not add a
backend URL or network dependency in Sprint 01. Future Android requests will
use:

- `source = "android"`
- the correct `input_mode`
- `truncated = true` only for genuinely truncated notification content
- no request/response content logging

Do not implement `NotificationListenerService`, SMS scanning, background
workers, guardian messaging, real OCR, real voice input, or API authentication
in this sprint.

## Tests

Add tests appropriate to the existing project. At minimum cover:

1. Empty trimmed message disables analysis.
2. Analysis demo exposes `HIGH` and exactly 4 of 8 signals as hits.
3. Lookup demo exposes `MEDIUM` and the required disclaimer.
4. The risk model has no `SAFE` state.
5. Dark-mode preference survives recreation/reload at the state or repository
   level.
6. Shared text is imported only after confirmation.
7. Canceling the share sheet does not retain shared content.

If Compose UI tests are already supported, also verify navigation labels and
that all four bottom destinations are reachable.

## Build and verification

Before editing:

1. Inspect `AGENTS.md`, `CLAUDE.md`, Gradle files, module structure, and Git
   status.
2. Preserve all unrelated user changes.
3. Identify the app module and current build variants.

After implementation, run the closest applicable commands:

```bash
./gradlew test
./gradlew lint
./gradlew assembleDebug
```

If the project defines variant-specific tasks, use those equivalents. Fix
implementation-caused failures. Do not suppress meaningful lint or test
failures simply to obtain an APK.

Then verify, without installing:

```bash
find . -path "*/build/outputs/apk/*" -name "*.apk" -type f
```

If available, use `apkanalyzer` or `aapt dump badging` only to inspect the APK's
package, version, SDK levels, and launcher activity. This is read-only and does
not install anything.

## Hard stop: do not install

The sprint ends when a valid debug APK has been built and its path reported.

Do **not**:

- run `adb install` or any other `adb` mutation;
- run `./gradlew installDebug` or another `install*` task;
- press Android Studio's Run button;
- launch an emulator;
- connect to, authorize, or modify a physical phone;
- upload or distribute the APK.

Do not ask to install the app as part of this task. Stop before installation and
report:

- what was implemented;
- files/modules materially changed;
- test, lint, and build results;
- the absolute or project-relative APK path;
- any known Sprint 01 limitations;
- the exact next manual step as:
  `Stopped before device installation, as requested.`

## Definition of done

Sprint 01 is complete only when:

- all nine screen states and four bottom navigation destinations are present;
- Android text/image share intents reach the confirmation sheet;
- light and dark modes render without clipped decision text;
- no message or lookup result is labeled safe;
- no sensitive content is logged or persisted;
- the app requests no unnecessary dangerous permission;
- relevant tests pass;
- lint has no new blocking issue;
- `assembleDebug` succeeds;
- the APK path is reported;
- no phone/emulator installation has been attempted.
