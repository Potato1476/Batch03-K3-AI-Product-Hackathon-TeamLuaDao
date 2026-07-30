# CHẮN continuous-training platform

The live scenario database is PostgreSQL. It is not a JSON file committed in
the product folder. Git contains only the schema, API, training algorithm,
tests, and reproducible synthetic seed generator.

```text
licensed feed / consented contribution
                  │
                  ▼
       private ingestion API
       L2 check · rights check
                  │
                  ▼
        PostgreSQL quarantine
                  │ human review
                  ▼
        approved scenario store
                  │
         daily Cloud Run Job / cron
                  ▼
   base corpus + approved new scenarios
                  │
                  ▼
      candidate model + frozen golden set
                  │
        safety gates + regression gates
          ┌───────┴────────┐
          ▼                ▼
     active model      rejected model
```

Do not train immediately after every submission. Daily batching plus review
reduces data poisoning, label mistakes, and unstable model changes.
Approved live examples receive bounded replay weight during training so a new
scenario is not lost among tens of thousands of base examples. The default is
10 and the service caps it at 20.

## Privacy boundary

- End-user Web and Android clients never call this internal API directly.
- Raw OTP, account, phone, email, exact money values, or names must not enter
  this service.
- The endpoint accepts only L2-redacted text and checks for common redaction
  failures without echoing rejected text.
- A user-derived scenario requires explicit consent. A feed-derived scenario
  requires a licensed threat-intelligence rights basis.
- Every item starts in `quarantined`; approval is a separate authenticated
  action.
- Rejection and seven-day quarantine expiry erase `redacted_text`.
- Logs and training-run records contain IDs, counts, hashes, metrics, and error
  classes only—not message content, evidence, or explanations.
- The existing `/v1/feedback` flow should continue storing only verdict
  metadata unless the user separately opts in to contribute a redacted
  scenario.

## Local setup

Use Python 3.11–3.13 and PostgreSQL:

```bash
cd repo
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'codebase/ml[dev]'
.venv/bin/python -m pip install -e 'codebase/api[dev]'

createdb chan
psql chan < codebase/api/migrations/001_continuous_training.sql

export CHAN_DATABASE_URL='postgresql://localhost/chan'
export CHAN_TRAINING_API_KEYS='feed-ingest=first-long-random-secret,ml-reviewer=second-long-random-secret'
export CHAN_MODEL_ARTIFACT_ROOT="$PWD/.local/model-registry"
export CHAN_BASE_DATASET_PATH="$PWD/codebase/ml/data/generated/chan-synthetic.jsonl.gz"
export CHAN_GOLDEN_DATASET_PATH="$PWD/path/to/frozen-golden.jsonl.gz"

.venv/bin/chan-training-api
```

Generate the base corpus with `chan-generate` as documented in
[`../ml/README.md`](../ml/README.md). Production must use a
separate frozen, human-reviewed golden set—not the daily training rows.

Build the service container from inside the `repo/` project root:

```bash
docker build -f codebase/api/Dockerfile -t chan-training-api .
```

Use the same image with the command `chan-training-worker --enqueue` for a
scheduled one-shot training job.

## Submit new scenarios

This endpoint is private and should sit behind the API gateway, service
identity, rate limits, and TLS.

```bash
curl -X POST http://localhost:8001/internal/v1/training/scenarios \
  -H 'Content-Type: application/json' \
  -H "X-CHAN-Training-Key: $CHAN_TRAINING_KEY" \
  -d '{
    "items": [{
      "redacted_text": "Cơ quan thuế yêu cầu giữ bí mật và chuyển <AMOUNT:trieu> vào <ACCOUNT> ngay.",
      "signals": [
        "mao_danh_tham_quyen",
        "yeu_cau_bi_mat",
        "ap_luc_thoi_gian",
        "tk_ca_nhan"
      ],
      "risk": "high",
      "is_phishing": true,
      "origin": "licensed_partner",
      "source_ref": "partner-case-2026-001",
      "rights_basis": "licensed_threat_intel",
      "consented": false,
      "redaction_confirmed": true
    }]
  }'
```

The response contains only scenario IDs, quarantine status, and deduplication
status. `source_ref` is stored as SHA-256, not plaintext.

## Review and approve

```bash
curl -X POST \
  http://localhost:8001/internal/v1/training/scenarios/SCENARIO_UUID/review \
  -H 'Content-Type: application/json' \
  -H "X-CHAN-Training-Key: $CHAN_REVIEWER_KEY" \
  -d '{"decision":"approve","review_reason":"labels_verified"}'
```

The database rejects approval by the same key identity that submitted the
scenario. Use separate ingestion and reviewer keys; database role separation
should also be enforced by the deployment.

## Queue and run training

Manual or scheduler-triggered queue:

```bash
curl -X POST http://localhost:8001/internal/v1/training/retrain \
  -H 'Content-Type: application/json' \
  -H "X-CHAN-Training-Key: $CHAN_TRAINING_KEY" \
  -d '{"idempotency_key":"daily-2026-07-30"}'
```

Daily worker:

```bash
.venv/bin/chan-training-worker --enqueue
```

`--enqueue` uses `daily-YYYY-MM-DD`, so retries do not create duplicate runs.
The worker also expires unreviewed quarantine rows older than seven days.

A candidate is promoted only when:

- frozen golden set size is at least 130;
- phishing recall is at least 90%;
- legitimate false-positive rate is below 15%;
- recall has not regressed by more than two percentage points;
- false positives have not regressed by more than two percentage points.
- enough scenario families are represented in the frozen golden set;
- no represented phishing family has recall below 75%;
- no represented legitimate family has false-positive rate at or above 15%.

All gates are configurable through environment variables, but production
values should not be weakened to force a promotion.

## Scheduling

Recommended production setup:

1. Deploy `chan-training-api` as a private Cloud Run service.
2. Run PostgreSQL on managed Cloud SQL with encryption, backups, and private
   networking.
3. Mount or download datasets/model artifacts from a private versioned object
   store; do not use the container filesystem as the registry.
4. Create a Cloud Run Job using the same image and command
   `chan-training-worker --enqueue`.
5. Trigger it daily with Cloud Scheduler using service identity.
6. Let `/v1/analyze` poll `model_versions` for the active version, verify the
   artifact SHA-256, load it in the background, and atomically swap the in-memory
   model. `ActiveModelProvider` in `src/chan_training_api/active_model.py`
   implements this loader. Keep the previous active version for rollback.

## Internal endpoints

| Endpoint | Purpose |
|---|---|
| `POST /internal/v1/training/scenarios` | Batch ingest up to 100 redacted scenarios |
| `POST /internal/v1/training/scenarios/{id}/review` | Approve or reject one quarantined item |
| `POST /internal/v1/training/retrain` | Idempotently queue a run |
| `GET /internal/v1/training/runs/{id}` | Read aggregate run state and metrics |
| `GET /internal/v1/training/models/active` | Read active model metadata and checksum |

These endpoints are an internal control plane. They are not part of the
end-user API contract.
