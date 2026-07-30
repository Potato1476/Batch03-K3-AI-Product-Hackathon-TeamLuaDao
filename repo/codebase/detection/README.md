# CHẮN Detection API

This is the shared inference boundary for Web, Android, and Zalo OA. Clients
call `POST /v1/analyze`; they do not load the Python `joblib` artifact and do
not bundle the training dataset.

The service:

- performs L2 redaction in memory before inference;
- loads the versioned model only after SHA-256 verification;
- returns the architecture's `high`, `medium`, or `unknown` contract;
- never returns `safe`, never persists message content, and disables access
  logs;
- sanitizes validation errors so rejected input is not echoed.

The API must sit behind the API Gateway's TLS, authentication, schema
validation, and rate limiting in deployed environments.

## Run locally

Use Python 3.11–3.13 from the `repo/` directory:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'codebase/ml[dev]'
.venv/bin/python -m pip install -e 'codebase/detection[dev]'
.venv/bin/chan-detection-api
```

The defaults point to the versioned model in
`codebase/ml/artifacts/chan-signal-model.joblib`. Check readiness:

```bash
curl --fail http://127.0.0.1:8000/healthz
```

Analyze a message:

```bash
curl --fail http://127.0.0.1:8000/v1/analyze \
  -H 'Content-Type: application/json' \
  --data '{
    "text": "Công an yêu cầu giữ bí mật và chuyển 12 triệu vào tài khoản 123456789012 ngay.",
    "source": "web",
    "input_mode": "manual",
    "local_signals": [],
    "truncated": false,
    "locale": "vi-VN",
    "rule_bundle_version": "rb-2026-07-30"
  }'
```

L1 on the device must stop OTP values before any network request. L2 repeats
redaction at the service boundary as defense in depth. Names need the client
rule/NER layer described in the architecture; the current L2 implementation
handles OTP, email, exact money, phone, and account-number patterns.

## Web/PWA integration

```ts
export type AnalyzeRequest = {
  text: string;
  source: "web";
  input_mode: "manual" | "upload" | "share";
  local_signals: string[];
  truncated: boolean;
  locale: "vi-VN";
  rule_bundle_version?: string;
};

export async function analyze(
  apiBaseUrl: string,
  request: AnalyzeRequest,
) {
  const response = await fetch(`${apiBaseUrl}/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`analyze_failed_${response.status}`);
  return response.json();
}
```

The deployed API base URL belongs in environment configuration, not source
code. The client must render `unknown` as “Chưa phát hiện dấu hiệu”, never
“An toàn”.

## Android integration

Retrofit contract:

```kotlin
data class AnalyzeRequest(
    val text: String,
    val source: String = "android",
    val input_mode: String,
    val app_package: String? = null,
    val local_signals: List<String> = emptyList(),
    val truncated: Boolean = false,
    val locale: String = "vi-VN",
    val rule_bundle_version: String? = null,
)

data class SignalResult(
    val code: String,
    val confidence: Double,
    val evidence: String,
)

data class AnalyzeResponse(
    val analysis_id: String,
    val risk: String,
    val score: Double,
    val scam_confidence: Double,
    val signals: List<SignalResult>,
    val explanation: String,
    val questions: List<String>,
    val actions: List<String>,
    val engine_version: String,
    val model_version: String,
)

interface ChanDetectionApi {
    @POST("v1/analyze")
    suspend fun analyze(@Body body: AnalyzeRequest): AnalyzeResponse
}
```

Use `input_mode="notification"` for NotificationListener content and
`input_mode="sms_scan"` for the SMS flow. Do not log the request or response
because evidence can contain redacted source fragments.

## Docker

Build from `repo/` so the image can copy both packages and the model:

```bash
docker build -f codebase/detection/Dockerfile -t chan-detection:20260730 .
docker run --rm -p 8000:8000 chan-detection:20260730
```

Override all three values together when promoting a new model:

```text
CHAN_MODEL_PATH
CHAN_MODEL_SHA256
CHAN_MODEL_VERSION
```

Loading fails closed with HTTP 503 if the artifact is missing, has the wrong
checksum, or is not a `PhishingSignalModel`.

## Tests

```bash
.venv/bin/pytest -q codebase/detection/tests
```

The synthetic baseline is ready for integration and demos, but it is not a
production safety certification. See
[`../ml/MODEL_CARD.md`](../ml/MODEL_CARD.md) and
[`../ml/ARTIFACTS.json`](../ml/ARTIFACTS.json).
