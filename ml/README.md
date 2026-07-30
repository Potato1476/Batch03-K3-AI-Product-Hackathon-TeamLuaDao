# CHẮN ML pipeline

This directory provides a reproducible large-dataset generator, an
interpretable Vietnamese phishing-signal model, evaluation gates, and safe
inference. It follows the architecture's eight-signal taxonomy and three risk
values.

## Quick start

Use Python 3.11–3.13:

```bash
cd ml
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

# Generate 100,000 deterministic, compressed examples.
.venv/bin/chan-generate \
  --size 100000 \
  --seed 20260730 \
  --output data/generated/chan-synthetic.jsonl.gz

# Train on the held-out train split and evaluate validation.
.venv/bin/chan-train \
  --dataset data/generated/chan-synthetic.jsonl.gz \
  --output artifacts/chan-signal-model.joblib \
  --metrics-output artifacts/validation-metrics.json

# Evaluate once on the held-out test split.
.venv/bin/chan-evaluate \
  --model artifacts/chan-signal-model.joblib \
  --dataset data/generated/chan-synthetic.jsonl.gz \
  --split test \
  --output artifacts/test-metrics.json

# L2-redacted inference. Stdin avoids shell-history exposure.
printf '%s' 'Công an yêu cầu giữ bí mật và chuyển <AMOUNT:trieu> vào <ACCOUNT> ngay.' \
  | .venv/bin/chan-predict \
      --model artifacts/chan-signal-model.joblib \
      --stdin
```

For a fast smoke run, generate 5,000 records and train with
`--word-features 8000 --char-features 12000`.

## API integration

Load the artifact once at FastAPI startup. The request text must pass through
L2 in memory before model inference.

```python
import joblib

model = joblib.load("artifacts/chan-signal-model.joblib")

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
- `src/chan_ml/synthetic.py`: scalable deterministic generator.
- `src/chan_ml/model.py`: word/character TF-IDF plus multi-label logistic
  regression.
- `src/chan_ml/policy.py`: exact L4 risk thresholds and overrides.
- `src/chan_ml/metrics.py`: architecture acceptance metrics.
- `tests/`: policy, leakage, privacy, hard-negative, and end-to-end tests.

Generated data and artifacts stay outside Git by default. Commit metrics and a
small reviewed golden set under the repository's `eval/` directory when the
team is ready; do not commit private messages.
