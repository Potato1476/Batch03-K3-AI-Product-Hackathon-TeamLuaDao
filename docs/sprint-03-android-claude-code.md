# Sprint 03 — speech reliability and live protection status

Give Claude Code this instruction from a Windows terminal opened at
`D:\Projects\CHAN`:

> Read `docs/sprint-03-android-claude-code.md` completely, inspect the existing
> Sprint 02 implementation and tests, then implement Sprint 03 autonomously.
> Preserve unrelated local changes. Run unit tests, lint, and `assembleDebug`.
> Stop after producing and inspecting the APK. Do not install it on a phone or
> emulator, do not run connected tests, and do not commit or push.

## Role and working agreement

You are the Android developer for CHAN. Harden the existing Kotlin and Jetpack
Compose app; do not rebuild it from scratch.

The project is already a Git repository and the working tree may contain user
changes. Inspect `git status` before editing. Preserve all unrelated changes,
especially the current README, logo, Git-ignore, and Windows wrapper edits.
Do not reset, discard, commit, or push anything.

Before editing, read completely:

- `docs/sprint-01-android-claude-code.md`
- `docs/sprint-02-android-claude-code.md`
- `README.md`
- `app/src/main/AndroidManifest.xml`
- all Gradle files
- `speech/AndroidRecognizer.kt`
- `speech/SpeechToTextController.kt`
- `notification/ZaloNotificationListenerService.kt`
- `notification/ProtectionState.kt`
- `ui/ChanViewModel.kt`
- `ui/ChanStateHolder.kt`
- `ui/screens/MessageInputScreen.kt`
- `ui/screens/ProtectionScreen.kt`
- all existing speech, notification, privacy, and state-holder tests

Do not ask routine implementation questions. Make conservative choices from
this contract and report assumptions and verification results at the end.

## Verified Sprint 02 baseline

Sprint 02 has already passed:

- 81 JVM tests;
- Android lint with no errors;
- debug APK assembly;
- manual text analysis against the live backend;
- local OTP blocking with zero backend requests;
- Android share intake;
- a real Zalo notification end to end:
  `Zalo → listener → POST /v1/analyze 200 → CHAN high-risk warning`;
- raw synthetic test content was not found in Logcat.

The physical handset was a Xiaomi `24117RN76O`, Android 15 / API 35.

Two reliability gaps were observed:

1. Speech-to-text reported that speech was unavailable even though microphone
   permission was granted and Android exposed recognition providers. The
   current controller treats a runtime failure from the preferred on-device
   recognizer as terminal instead of offering the already-consented device
   service fallback.
2. The app UI currently equates Notification Access permission with active
   protection. Those are not the same. During testing, permission was enabled
   while the listener was not bound. Rebinding the listener restored the
   end-to-end flow.

The user also explained that app data/history had been cleared and protection
was not enabled again. Sprint 03 must make this state obvious. Clearing app
data is allowed to reset consent to off; CHAN must never silently restore
notification reading after that reset.

Increment:

- `versionCode` from `2` to `3`;
- `versionName` from `0.2.0-sprint02` to `0.3.0-sprint03`.

## Sprint goal

Produce a debug APK that:

1. reliably supports one-shot Vietnamese dictation on the physical phone;
2. falls back from a recognizer that fails at runtime only after explicit user
   consent;
3. releases every recognizer immediately after completion, failure, or cancel;
4. reports whether the Zalo listener is actually connected in this process,
   not merely whether permission was granted;
5. makes active, connecting, paused, and setup-required protection states
   unmistakable to an older user;
6. can request one bounded listener rebind when protection is configured but
   disconnected;
7. provides a generic, ongoing protection-status notification while the
   listener is connected, if CHAN is allowed to post notifications;
8. detects distinct risky Zalo messages repeatedly instead of stopping after
   the first warning;
9. retains all Sprint 01 and Sprint 02 behavior and privacy guarantees.

This sprint is reliability and observability work. Do not add accounts,
analytics, cloud transcript storage, continuous audio, SMS access, contacts,
accessibility services, or unrelated product features.

## Non-negotiable privacy and truthfulness rules

1. Never log, persist, or include in notifications any dictated text, Zalo
   text, sender, OTP, account, phone number, URL, or analysis evidence.
2. Speech starts only from a visible user action and remains one utterance.
3. Final speech is editable and is never analyzed automatically.
4. On-device recognition remains the first choice.
5. A recognizer reported as “available” is not assumed to work until it
   actually starts and returns callbacks.
6. Never switch from on-device recognition to a service that may send audio to
   a provider without a fresh, explicit confirmation.
7. A green protection indicator means “listener connected and scanning
   enabled,” never “this message is safe.”
8. Notification Access permission alone must not render as fully active.
9. Do not persist a current `connected=true` flag. It becomes a lie after
   process death. Runtime connection state starts unknown in every new process.
10. Timestamps and connection-state metadata may be stored, but message
    content may not.
11. Do not use a foreground service merely to keep the process alive in this
    sprint. `NotificationListenerService` remains the system-managed intake.
12. Do not claim that a low-importance status notification proves the process
    can never be killed. It reflects the latest listener lifecycle state.

## Part A — fix Vietnamese speech-to-text

### A1. Model recognizer stages explicitly

Refactor the speech seam so the controller knows which recognizer produced a
callback:

- `ON_DEVICE`
- `DEVICE_SERVICE`

Add user-facing states sufficient to distinguish:

- idle;
- listening on device;
- listening through the device speech service;
- partial result;
- final editable result;
- no speech;
- busy;
- permission denied;
- Vietnamese language unavailable;
- on-device recognizer failed and device-service consent is required;
- device speech service unavailable;
- temporary provider/network failure.

Names may differ, but the state model must preserve these distinctions. Do not
collapse every platform error into one generic unavailable state.

Each listening attempt must have a monotonically increasing session ID or
equivalent token. Ignore callbacks from a destroyed/previous recognizer so a
late callback cannot overwrite a newer attempt.

### A2. Runtime failure must lead to an explicit fallback choice

The current failure path occurs after the on-device factory succeeds. Handle
failures from:

- recognizer construction;
- `setRecognitionListener`;
- `startListening`;
- an asynchronous `onError` callback.

Map the complete platform error set available at compile SDK 35, including:

- no match and speech timeout;
- recognizer busy;
- insufficient permission;
- network and network timeout;
- server and server disconnected;
- client error;
- too many requests;
- language not supported;
- language unavailable.

If the on-device recognizer fails because its service disconnects, its
language model is unavailable, the server/provider rejects the request, or the
platform otherwise cannot run it:

1. cancel and destroy that handle immediately;
2. retain no transcript/audio;
3. show a plain-language explanation;
4. offer `Dùng dịch vụ giọng nói của máy`;
5. start the device-service recognizer only after the user taps that action.

Suggested Vietnamese copy:

`Nhận giọng nói trên máy chưa hoạt động. Bác có thể thử lại, dán chữ, hoặc đồng ý dùng dịch vụ giọng nói của máy.`

Before device-service use, retain the existing privacy explanation:

`Dịch vụ giọng nói của máy có thể gửi âm thanh đến nhà cung cấp để nhận dạng. CHAN không lưu bản ghi âm.`

Actions:

- `Dùng dịch vụ giọng nói của máy`
- `Thử lại trên máy`
- `Để sau`

Consent is for the current user-initiated attempt. Do not silently remember it
as permanent consent unless the existing product already contains a separate,
clear preference for that purpose.

If the device-service recognizer also fails, return to the editable input and
offer paste/image entry. Do not loop between providers.

### A3. Recognizer lifetime

All `SpeechRecognizer` calls must occur on the main thread.

For every session:

1. create one handle;
2. attach its listener;
3. call `startListening`;
4. on final result, error, cancel, screen exit, or app background:
   cancel when appropriate, detach callbacks, and call `destroy()` exactly
   once;
5. clear the handle and listening mode.

Receiving final text must destroy the recognizer before publishing
`FinalText`. The final string then enters the normal editable message field.

`onEndOfSpeech` is not itself a final result. Allow the provider a short,
bounded result window rather than immediately replacing a pending result with
`NoSpeech`. Use a lifecycle-aware coroutine/timer and cancel it when a final
result or error arrives. Do not introduce indefinite waiting.

Catch platform `RuntimeException`, `SecurityException`, and invalid-state
failures at the adapter boundary and translate them into safe controller
events. Never display exception text.

### A4. Recognition request

Retain:

- `ACTION_RECOGNIZE_SPEECH`;
- `LANGUAGE_MODEL_FREE_FORM`;
- language `vi-VN`;
- partial results;
- maximum one result;
- offline preference for the on-device attempt.

For the explicitly consented device-service attempt, do not describe
`EXTRA_PREFER_OFFLINE` as a guarantee. The UI must identify whether the active
attempt is on-device or uses the phone's speech service.

Do not hardcode Google, Claude, Xiaomi, or another provider package. Use the
system-selected recognition service. If no compatible service exists, provide
an action to Android/app settings and keep paste/image input available.

### A5. Message-input UX

The microphone area must:

- have a minimum 48 dp touch target;
- show `Đang nghe trên máy…` for a true on-device attempt;
- show `Đang dùng dịch vụ giọng nói của máy…` for a consented fallback;
- provide stop/cancel;
- show partial text without submitting it;
- copy only a final result into the editable field;
- preserve any text already typed unless the user clearly chooses to replace
  it;
- keep `Kiểm tra ngay` as the only analysis action;
- expose state and actions through accessibility semantics.

Do not request microphone permission during app startup. Request it only after
the microphone action.

## Part B — truthful protection health

### B1. Runtime connection monitor

Add a small process-scoped `ProtectionRuntimeMonitor` or equivalent,
constructor-injected through the existing graph.

It exposes a `StateFlow` with at least:

- `Unknown` — new process, no listener callback yet;
- `Connecting`;
- `Connected(connectedAt)`;
- `Disconnected(reasonCategory?)`.

Update it only from real lifecycle evidence:

- `onCreate` / a rebind request may move to `Connecting`;
- `NotificationListenerService.onListenerConnected()` moves to `Connected`;
- `onListenerDisconnected()` moves to `Disconnected`;
- `onDestroy()` moves to `Disconnected`.

The monitor must start `Unknown` on every process start. Do not restore
`Connected` from preferences.

Optionally persist only `lastConnectedAt` for explanatory copy such as
`Kết nối gần nhất lúc 18:42`. A historical timestamp must never be interpreted
as current health.

### B2. Effective protection state

Compute the user-facing state from all relevant layers:

```text
in-app scanning preference
  + Android Notification Access grant
  + listener runtime connection
  + CHAN warning-notification permission
```

Required states and suggested Vietnamese copy:

- preference off:
  `Bảo vệ Zalo đang tắt`
- preference on, access missing:
  `Cần bật Truy cập thông báo`
- preference on, access granted, runtime unknown/connecting:
  `Đang kết nối bảo vệ Zalo…`
- preference on, listener disconnected:
  `Bảo vệ Zalo đang mất kết nối`
- preference on, listener connected, warnings allowed:
  `CHAN đang bảo vệ thông báo Zalo`
- listener connected, CHAN warning permission missing:
  `Đang kiểm tra nhưng chưa thể hiện cảnh báo`

Clearing app data must return the local scanning preference to off. On next
launch, show `Bảo vệ Zalo đang tắt` with a clear setup action, even if Android
still happens to retain Notification Access. Do not silently re-enable
scanning.

Do not attempt to claim whether Zalo's own notifications are globally enabled;
ordinary apps cannot reliably query another app's full notification settings.
Provide an explanatory checklist/action to open Zalo's app-notification
settings when no Zalo events are arriving, without displaying a false detected
state.

### B3. Bounded reconnect

When the app returns to the foreground and all are true:

- the in-app preference is on;
- Android Notification Access is granted;
- runtime state is `Unknown` or `Disconnected`;

then:

1. set `Connecting`;
2. call `NotificationListenerService.requestRebind()` with CHAN's component;
3. wait for the real `onListenerConnected` callback;
4. if no callback arrives within a bounded window such as 5 seconds, render
   `Disconnected` and show `Kết nối lại`.

Do this at most once automatically per foreground/resume event. Do not create
a retry loop, alarm, or WorkManager job. A user-tapped reconnect may try once
again.

If access is missing, open Notification Access settings instead of requesting
a rebind. Refresh all states when returning from system settings.

### B4. Visible protection indicator

Add a low-importance notification channel:

- ID: `chan_protection_status`
- user-visible name: `Trạng thái bảo vệ`
- importance: low;
- no sound or vibration;
- lock-screen visibility: private.

When and only when:

- scanning preference is on;
- Notification Access is granted;
- `onListenerConnected` has occurred in the current process;
- CHAN may post notifications;

publish one ongoing generic status notification:

- title: `CHAN đang bảo vệ Zalo`
- body: `Chạm để xem trạng thái bảo vệ.`

It must contain no sender, message, analysis, or evidence. Tapping it opens the
Protection screen.

Cancel this status notification when:

- the user pauses protection;
- Notification Access is revoked;
- `onListenerDisconnected` occurs;
- the listener/service is destroyed;
- app state is reconciled and the prerequisites are not all true.

On app startup, reconcile/cancel a stale status notification before reporting
the current runtime state. It may be reposted only after a fresh
`onListenerConnected` callback.

Do not reuse the high-risk or caution channels. Do not change their importance.
The status notification is an indicator, not an alert and not a guarantee that
Android will never kill the process.

### B5. In-app placement

Show the effective protection state in two places:

1. a compact status row/card on Home;
2. the detailed layer cards on `Bảo vệ`.

The Home status must be understandable without opening settings:

- green check + `CHAN đang bảo vệ Zalo`;
- neutral progress + `Đang kết nối…`;
- amber warning + `Bảo vệ Zalo cần bật lại`;
- gray pause + `Bảo vệ Zalo đang tắt`.

State must not rely on color alone. Use an icon, text, and accessible content
description. Tapping the row opens `Bảo vệ`.

On the detailed screen, keep separate rows for:

- local rules;
- in-app Zalo scanning preference;
- Notification Access grant;
- listener connected now;
- CHAN warning permission.

This separation is important: a single green switch must not hide a broken
layer.

## Part C — small Sprint 02 hardening

Keep this section tightly scoped to already-observed issues.

### C1. Analyze request retry policy

The notification contract allows one bounded analysis attempt and no hidden
automatic replay of raw message content. Audit the OkHttp client:

- do not rely on `retryOnConnectionFailure(true)` for `POST /v1/analyze`;
- set `retryOnConnectionFailure(false)` globally unless a method-specific,
  privacy-safe policy proves otherwise;
- retain the explicit single `401 → renew device token → retry once` behavior;
- do not otherwise retry analyze requests;
- keep bundle `GET` refresh behavior safe and bounded.

Add a MockWebServer test proving a failed analyze connection is not
automatically replayed.

### C2. Base URL documentation and build behavior

Make README and Gradle behavior agree. The existing build reads a Gradle
project property. Either:

- document only the verified command-line form
  `-PCHAN_API_BASE_URL=http://.../`; or
- deliberately add and test reading the property from `local.properties`.

Do not claim arbitrary `local.properties` keys work unless the build actually
loads them. Never commit a machine LAN address.

## Part D — repeated Zalo detections

### D1. Confirmed Sprint 02 failure modes

Physical testing found that one high-risk Zalo message produced a warning, but
later test messages did not produce another visible warning.

The Sprint 02 code has two mechanisms that can cause this:

1. `NotificationDedupeCache` hashes only package, notification key, and
   normalized content, then suppresses that digest for 10 minutes. A genuinely
   new message with identical text in the same Zalo conversation is therefore
   indistinguishable from Android repeating the same callback.
2. `AndroidSafeAlertPublisher` always calls `notify(4201, ...)`. A later
   warning updates the existing notification instead of creating a new alert
   event. Android may keep it in the shade without presenting a new heads-up
   warning.

Fix both. Do not “solve” the issue with an unbounded polling loop, by disabling
deduplication, or by stacking unlimited notifications.

### D2. Model a notification occurrence

Extend the framework snapshot with safe occurrence metadata:

- `StatusBarNotification.postTime`;
- each exposed `MessagingStyle.Message.timestamp`;
- message count or another non-content occurrence value when available.

Continue to omit sender identity. Never persist or log message text.

Use the newest messaging-message timestamp as the preferred occurrence token.
If Zalo does not expose messaging timestamps, fall back to notification
`postTime`. Combine the occurrence token with the notification key and the
normalized-content digest.

The required behavior is:

- the same callback/update for the same occurrence is processed once;
- a genuinely new message in the same conversation is processed;
- the same text sent again as a new message is processed again;
- a different text in the same conversation is processed;
- read-receipt, bubble, ranking, or presentation-only updates do not repeatedly
  analyze the same message;
- process death may reset in-memory dedupe state.

Do not use a 10-minute content-only suppression window. A short bounded
debounce may collapse callbacks for one occurrence, but it must not suppress a
new occurrence carrying the same text.

Keep only hashes, occurrence tokens, and timestamps in the bounded in-memory
cache. Do not store raw content.

### D3. Keep callback processing restartable

Audit the listener coroutine pipeline for a “works once” state:

- do not keep a global `processing=true` flag;
- if mutual exclusion or single-flight state is needed, release it in
  `finally`;
- one backend failure or thrown exception must not cancel future callbacks;
- one dedupe rejection must not stop the listener scope;
- one unknown/low result must not stop future processing;
- listener disconnect/reconnect must create a usable processing scope.

The current service owns a `CoroutineScope`. If `onDestroy()` cancels it, a
new service instance must own a fresh scope. If the platform can reconnect the
same instance on the supported API levels, explicitly verify that a cancelled
scope is never reused.

Serialize only the minimum state transition needed to prevent races. Do not
persist or enqueue raw notifications. Do not add an indefinite loop,
WorkManager queue, or background database of messages.

Add safe, content-free runtime telemetry to the in-app Protection screen or a
debug-only status section:

- last Zalo callback time;
- last pipeline outcome category, such as `duplicate`, `local_low`,
  `local_otp`, `backend_success`, `backend_failure`, or `alert_posted`;
- last alert-posted time.

These values must contain no content, sender, phone, account, URL, evidence, or
request body. User-facing production copy should remain plain language, for
example `Hoạt động gần nhất lúc 21:03`.

### D4. Publish a fresh warning event

Each distinct `HIGH` or `MEDIUM` outcome must create a fresh alert event so the
OS may present another heads-up warning.

Do not continually update fixed ID `4201`. Use one of these bounded designs:

- cancel the previous alert and post the new event with a different rotating
  notification ID; or
- keep a bounded ring of at most three alert IDs and cancel the oldest.

Prefer a rotating ID with at most one visible CHAN risk alert. It preserves the
Sprint 02 goal of avoiding a wall of warnings while still making the new event
distinct to Android.

Requirements:

- a new risk result uses a different notification event/ID from the previous
  one;
- the prior visible risk alert is cancelled before or as the new one is
  posted;
- high and caution channels remain unchanged;
- every alert remains generic and private;
- the content intent opens the newest matching redacted result;
- PendingIntent identity/request code cannot accidentally retain an older
  result;
- no `setOnlyAlertOnce(true)`;
- no full-screen intent;
- the OS still has final control over whether a heads-up banner appears.

`PendingAlertStore` may continue to keep only the newest redacted result, but a
new result must atomically replace the old one before its notification is
posted.

### D5. Repeated-detection acceptance matrix

Add deterministic tests for:

| Scenario | Repository calls | Warning publishes |
|---|---:|---:|
| same OS callback delivered twice | 1 | 1 |
| same text, same occurrence timestamp | 1 | 1 |
| same text, later message timestamp | 2 | 2 |
| different text, same Zalo conversation | 2 | outcome-dependent |
| first result unknown, second result high | 2 | 1 |
| first backend call fails, second is high | 2 | 1 |
| listener disconnects and reconnects, then high | processed after reconnect | 1 |
| two distinct high-risk messages | 2 | 2 fresh alert events |

For outcome-dependent rows, fake the repository response explicitly so the
assertion is deterministic.

## Tests

### JVM tests

Add or update tests proving:

1. on-device recognition is still preferred;
2. device-service fallback is never created without explicit consent;
3. a runtime on-device failure produces the fallback-consent state;
4. consenting after that state creates exactly one device-service attempt;
5. the device-service failure does not loop back to on-device;
6. final, error, cancel, and dispose each destroy the active handle exactly
   once;
7. a stale callback from an old session is ignored;
8. end-of-speech waits for a bounded final-result window;
9. final speech remains editable and never auto-submits;
10. every speech state has safe user-facing copy;
11. the runtime monitor starts unknown in a new instance;
12. only `onListenerConnected` marks it connected;
13. disconnect/destroy removes connected state;
14. access granted plus scanning enabled but listener unknown is connecting,
    not active;
15. clearing/resetting preferences renders protection off;
16. automatic rebind is bounded to one attempt per foreground event;
17. status notification publishes only from a real connected state;
18. status notification is cancelled for every inactive prerequisite;
19. status notification contains no source content;
20. failed analyze transport is not automatically replayed;
21. duplicate callbacks for one occurrence are analyzed once;
22. identical text with a later occurrence timestamp is analyzed again;
23. different text in the same conversation is not suppressed;
24. a failure/unknown result does not prevent the next notification;
25. listener reconnect leaves a usable processing scope;
26. two distinct high-risk outcomes create two distinct alert events;
27. alert IDs are bounded and old warnings are removed;
28. PendingIntent identity opens the newest redacted result;
29. all existing Sprint 01 and Sprint 02 tests remain green.

Prefer pure Kotlin seams and fakes. Do not make JVM tests depend on a real
speech provider or notification listener.

### Static/privacy checks

Retain and extend static checks so the build fails if:

- speech or notification content is logged;
- the status notification accepts raw source text;
- current runtime connection is persisted as a trusted boolean;
- continuous audio recording or audio-file storage is added;
- a foreground service, SMS, contacts, accessibility, call-log, or storage
  permission is introduced;
- HTTP body logging is enabled;
- analyze auto-retry is enabled.

### Manual physical-phone checklist

Document this checklist in README, but do not execute it during implementation:

1. Install the debug APK manually on the Xiaomi Android 15 phone.
2. Confirm microphone and notification permissions are requested only in
   context.
3. Tap speech, speak a Vietnamese sentence, edit the result, and manually tap
   `Kiểm tra ngay`.
4. If on-device recognition fails, confirm CHAN asks before using the device
   speech service.
5. Deny that fallback and confirm paste/image still work.
6. Accept it and confirm one-shot dictation returns editable Vietnamese text.
7. Confirm no dictated text appears in Logcat or app storage.
8. Enable Zalo protection and confirm Home and Protection show
   `CHAN đang bảo vệ Zalo` only after listener connection.
9. Confirm the low-importance ongoing status notification appears and opens
   the Protection screen.
10. Revoke Notification Access and confirm the active indicator disappears.
11. Re-enable access and use `Kết nối lại`; confirm the listener becomes
    active without reinstalling.
12. Clear app data, reopen CHAN, and confirm protection is visibly off and is
    not silently restored.
13. With protection active, send a synthetic high-risk Zalo message and confirm
    `/v1/analyze` returns 200 and CHAN warns.
14. Dismiss the warning, then send a second, different synthetic high-risk
    message in the same conversation; confirm a second analyze request and a
    fresh heads-up warning.
15. Send the exact same synthetic high-risk text again as a new message;
    confirm it is treated as a new occurrence and warns again.
16. Cause Zalo to update the same notification without a new message; confirm
    it does not create another analyze request or warning.
17. Send a synthetic OTP request and confirm a high warning with zero analyze
    requests.
18. Do not use real OTPs, passwords, banking details, or personal data.

## README and version updates

Update README to:

- identify Sprint 03 and version `0.3.0-sprint03`;
- describe on-device-first speech with explicit runtime fallback consent;
- explain the difference between permission, scanning preference, and live
  listener connection;
- explain the ongoing protection-status notification;
- explain what happens after clearing app data;
- explain that each distinct risky Zalo message can generate a fresh warning
  while duplicate Android callbacks are ignored;
- include the physical checklist above;
- make base-URL instructions match the actual Gradle implementation.

Do not rewrite unrelated README content.

## Build verification

From Windows PowerShell at `D:\Projects\CHAN`, run:

```powershell
.\gradlew.bat testDebugUnitTest
.\gradlew.bat lintDebug
.\gradlew.bat assembleDebug
```

If the wrapper cannot locate Java, use the installed Android Studio JBR for the
current shell without committing a machine-specific path:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
```

Inspect:

- test count and failures;
- lint error/warning count;
- APK path, size, version name, and version code;
- `git diff --check`;
- `git status --short`;
- the APK for accidental secrets or a committed LAN address.

Do not run `connectedDebugAndroidTest`; it installs test artifacts. Do not run
`adb install`, Android Studio Run, an emulator deployment, or any command that
installs the app.

## Required completion report

At the end, report:

- files changed;
- architecture and UX decisions;
- exact speech fallback behavior;
- exact definition of “listener connected”;
- tests added and total passing count;
- lint result;
- APK path, size, version name, and version code;
- remaining warnings or limitations;
- manual physical tests still required;
- confirmation that no installation, commit, or push occurred.

## Hard stop before device installation

Stop once the debug APK has been built and inspected.

Do not:

- install the APK;
- launch it on a phone or emulator;
- run connected tests;
- modify phone permissions;
- start or stop the backend;
- commit or push.

The user will perform the physical-phone phase separately.

## Definition of done

Sprint 03 implementation is complete when:

- Sprint 01 and Sprint 02 behavior is preserved;
- version is `0.3.0-sprint03` / code `3`;
- runtime failure of the on-device recognizer offers an explicit, consented
  device-service fallback;
- recognizers are destroyed exactly once at every terminal boundary;
- recognized Vietnamese text is editable and never auto-submitted;
- Notification Access is no longer presented as proof of a live listener;
- a real `onListenerConnected` callback drives the active state;
- reconnect behavior is bounded and user-visible;
- the generic status notification accurately reflects the latest live
  connection state and contains no source content;
- duplicate callbacks are suppressed by occurrence rather than a long
  content-only TTL;
- identical text sent as a new Zalo message is analyzed again;
- later high/medium outcomes produce fresh, bounded warning events instead of
  silently updating notification ID `4201`;
- a failure, low result, or disconnect does not prevent later notifications
  from being processed;
- clearing app data leaves protection visibly off;
- analyze requests have no hidden transport replay;
- base-URL documentation matches the build;
- unit tests, lint, and debug APK assembly pass;
- no app has been installed by Claude Code.

Passing the build is not proof that a particular speech provider or Xiaomi
listener lifecycle works. Sprint 03 is accepted only after the manual
physical-phone checklist passes.
