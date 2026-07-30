# CHẮN ML pipeline

This directory provides a reproducible large-dataset generator, an
interpretable Vietnamese hybrid scam/signal model, scenario-level evaluation
gates, and safe inference. It follows the architecture's eight-signal taxonomy
and three risk values.

## Quick start

Use Python 3.11–3.13:

```bash
cd repo
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'codebase/ml[dev]'
.venv/bin/python -m pip install -e 'codebase/api[dev]'

# Generate 250,000 deterministic, compressed examples.
.venv/bin/chan-generate \
  --size 250000 \
  --seed 20260730 \
  --output codebase/ml/data/generated/chan-synthetic.jsonl.gz

# Train on the held-out train split and evaluate validation.
.venv/bin/chan-train \
  --dataset codebase/ml/data/generated/chan-synthetic.jsonl.gz \
  --output codebase/ml/artifacts/chan-signal-model.joblib \
  --metrics-output codebase/ml/artifacts/validation-metrics.json

# Evaluate once on the held-out test split.
.venv/bin/chan-evaluate \
  --model codebase/ml/artifacts/chan-signal-model.joblib \
  --dataset codebase/ml/data/generated/chan-synthetic.jsonl.gz \
  --split test \
  --output codebase/ml/artifacts/test-metrics.json

# L2-redacted inference. Stdin avoids shell-history exposure.
printf '%s' 'Công an yêu cầu giữ bí mật và chuyển <AMOUNT:trieu> vào <ACCOUNT> ngay.' \
  | .venv/bin/chan-predict \
      --model codebase/ml/artifacts/chan-signal-model.joblib \
      --stdin
```

For a fast smoke run, generate 5,000 records and train with
`--word-features 8000 --char-features 12000`.

## Train with `CHAN-Dataset`

Do not train directly from the JSON files in `CHAN-Dataset`. The source
duplicates messages across conversations/messages/signals/entities, uses 27
labels while the product contract has eight, and its published benchmark
overlaps training conversations. The adapter reads conversation sources only,
redacts identifiers, accepts a signal only when the text contains supporting
evidence, removes post-redaction duplicates, and assigns a stable text-hash
split.

The current audit of the project folder is:

- 89,837 source messages;
- 1,807 unique records after L2 redaction;
- 88,030 duplicate messages merged;
- 1,464 train, 145 validation, 198 test;
- zero exact normalized-text overlap between those three splits.

Because the cleaned team train split is small and has very few positive OTP,
secrecy and channel-switch samples, use bounded replay from the existing
curated corpus. The primary dataset is repeated four times, replay is capped
at 15,000 examples, and one deterministic typo variant is generated for every
effective training row. This produces 41,712 training examples while the
validation and test results still come only from untouched team data.

Run these commands in the foreground from `repo/`:

```bash
cd /Users/nguyenbao/Batch03-K3-AI-Product-Hackathon-TeamLuaDao/repo

python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'codebase/ml[dev,workbook]'

TEAM_DATA=codebase/ml/data/generated/chan-team-clean-v4.jsonl.gz
RUN_ID=team-robust-final
CANDIDATE_DIR=codebase/ml/artifacts/candidates/$RUN_ID

.venv/bin/chan-prepare-team-data \
  --input CHAN-Dataset \
  --output "$TEAM_DATA" \
  --seed 20260731

.venv/bin/chan-audit-dataset \
  --dataset "$TEAM_DATA" \
  --output eval/team-dataset-v4-audit.json

.venv/bin/python -m json.tool "$TEAM_DATA.manifest.json"

time .venv/bin/chan-train \
  --dataset "$TEAM_DATA" \
  --replay-dataset codebase/ml/data/generated/chan-synthetic.jsonl.gz \
  --replay-limit 15000 \
  --primary-weight 4 \
  --typo-augmentations 1 \
  --augmentation-seed 20260731 \
  --c 2.0 \
  --scam-c 0.5 \
  --probability-temperature 0.50 \
  --max-iter 1000 \
  --output "$CANDIDATE_DIR/chan-signal-model.joblib" \
  --metrics-output "$CANDIDATE_DIR/validation-metrics.json"

.venv/bin/chan-evaluate \
  --model "$CANDIDATE_DIR/chan-signal-model.joblib" \
  --dataset "$TEAM_DATA" \
  --split test \
  --output "$CANDIDATE_DIR/test-metrics.json"

.venv/bin/chan-evaluate-workbook \
  --model "$CANDIDATE_DIR/chan-signal-model.joblib" \
  --workbook '/Users/nguyenbao/Downloads/CHẮN_System_TestCases_v1.2.xlsx' \
  --rules codebase/rules/bundle.json \
  --typo-variants 8 \
  --typo-seed 20260731 \
  --output "eval/$RUN_ID-golden-results.json"

.venv/bin/chan-evaluate-product \
  --model "$CANDIDATE_DIR/chan-signal-model.joblib" \
  --dataset "$TEAM_DATA" \
  --rules codebase/rules/bundle.json \
  --split test \
  --output "eval/$RUN_ID-product-test.json"
```

`chan-train` now refuses to run when phishing/legitimate coverage is missing
or any of the eight signals has no positive training example. It calibrates
the medium/high scam-intent thresholds using only the team validation split.
Training augmentation covers missing accents, deletion, adjacent swap,
keyboard-neighbor replacement, separator insertion, and whitespace changes;
it never changes validation or test data. The Excel evaluator prints the real
result as `x/20`, evaluates separately generated typo variants, and saves every
case including failures. Do not replace the active artifact until both
`test-metrics.json` and the frozen Excel result have been reviewed.

The promoted `ml-0.5.0` artifact reached 20/20 on the frozen workbook and
136/136 on deterministic unseen typo variants. On the stricter variable-family
held-out team test split it reached 93.60% phishing recall with an 8.22%
legitimate false-positive rate. Full-product signal macro-F1 was 86.61% for
signals represented in that split. These figures describe the checked
datasets, not all future scams.

## API integration

Load the artifact once at FastAPI startup. The request text must pass through
L2 in memory before model inference.

```python
import joblib

model = joblib.load("codebase/ml/artifacts/chan-signal-model.joblib")

def classify_redacted(redacted_text: str, similarity_max: float) -> dict:
    return model.predict(
        redacted_text,
        similarity_max=similarity_max,
        similarity_beta=0.15,
    )
```

The returned object contains `risk`, `score`, `signals` with grounded evidence,
short Vietnamese explanation/questions, and `engine_version`. The API layer
adds `analysis_id`, allowed actions, verified hotline data, and the rule-bundle
version.

Do not log `redacted_text`, evidence, or explanation. Do not persist the text.
The pgvector similarity value must come only from consented, L2-redacted
scenarios.

## Files

- `DATASET_CARD.md`: schema, composition, privacy, and limitations.
- `MODEL_CARD.md`: algorithm, intended role, evaluation, and limitations.
- `SCENARIO_COVERAGE.md`: versioned 36-family coverage and advisory basis.
- `src/chan_ml/synthetic.py`: scalable deterministic generator.
- `src/chan_ml/team_dataset.py`: audited adapter for project-provided data.
- `src/chan_ml/audit_dataset.py`: all-record label/evidence/leakage audit.
- `src/chan_ml/model.py`: word/character TF-IDF plus multi-label logistic
  regression.
- `src/chan_ml/evaluate_workbook.py`: full frozen-golden-set result writer.
- `src/chan_ml/evaluate_product.py`: L0–L4 product-path evaluation.
- `src/chan_ml/policy.py`: exact L4 risk thresholds and overrides.
- `src/chan_ml/metrics.py`: architecture acceptance metrics.
- `tests/`: policy, leakage, privacy, hard-negative, and end-to-end tests.

The reproducible `chan-synthetic-baseline-20260730` dataset, trained artifact,
and metrics are versioned for team integration. Their paths and SHA-256
digests are in [`ARTIFACTS.json`](ARTIFACTS.json). Future large/live datasets
belong in controlled object storage or the reviewed scenario database; do not
commit private messages.

## Continuous updates

The synthetic corpus is a seed and regression fixture, not the live database.
The product's private ingestion API, PostgreSQL migration, quarantine/review
flow, daily trainer, and guarded model registry are documented in
[`../api/README.md`](../api/README.md).

Daily training combines the stable base corpus with approved, L2-redacted
scenarios from PostgreSQL. A candidate is evaluated against a separate frozen
golden set and becomes active only if absolute safety gates and regression
gates pass. Web and Android clients continue calling `/v1/analyze`; they never
download the training database or call the internal training API.

The runnable shared endpoint and Web/Android examples are in
[`../detection/README.md`](../detection/README.md).
