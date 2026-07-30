# CHẮN Synthetic Vietnamese Message Dataset

## Purpose

This dataset trains and evaluates a Vietnamese multi-label classifier for the
eight behavioral signals in `CHAN-ARCHITECTURE.md`. It is not a generic spam
dataset. Every record is designed for the L2 → L3 boundary, after personal
information has been replaced with placeholders.

The generator creates 100,000 records by default and can create millions
without committing a large generated file to Git.

## Schema

Each JSONL row contains:

| Field | Meaning |
|---|---|
| `id` | Deterministic synthetic record ID |
| `text` | Synthetic, L2-redacted Vietnamese content |
| `risk` | `high`, `medium`, or `unknown` |
| `signals` | Map of architecture signal code to ground-truth strength |
| `is_phishing` | Evaluation-only ground truth; not an API risk enum |
| `scenario` | Scenario family used for slice metrics |
| `template_id` | Template provenance and leakage auditing |
| `source` / `input_mode` | Client metadata matching `/v1/analyze` |
| `truncated` | Whether notification-style truncation was applied |
| `split` | `train`, `validation`, or `test` |
| `synthetic` / `consented` | Privacy and provenance controls |
| `generator_version` | Reproducibility |

The adjacent manifest records the seed, counts, and an SHA-256 digest of the
uncompressed canonical JSONL.

## Composition

- Scam scenarios: fake investigations, OTP theft, malicious APK installation,
  fake prizes, fake jobs, school impersonation, utility impersonation, and
  family-emergency impersonation.
- Hard negatives: legitimate OTP warnings, bank alerts, school deadlines,
  utility notices, store-delivered app updates, private family surprises,
  normal recruitment, and legitimate channel changes.
- Perturbations: missing Vietnamese diacritics, teencode, inserted separators,
  casing, whitespace, and notification truncation.
- Split strategy: templates are assigned to exactly one split. Test and
  validation phrasings are held out from training.

## Privacy

- The generator uses no real person data.
- URLs use the reserved `.invalid` top-level domain.
- Accounts, phone numbers, amounts, names, and OTP values use L2 placeholders.
- A non-synthetic record fails schema validation unless `consented=true`.
- Generated datasets and model artifacts are ignored by Git.

Do not convert production messages into a training corpus automatically. A
message may enter the long-lived scenario store only after L2 redaction and
explicit user consent, as required by the architecture.

## Known limitations

Synthetic accuracy is not production accuracy. Repeated vocabulary and a
finite template family make the task easier than real Vietnamese scams. The
dataset does not satisfy the architecture requirement for at least 100
hand-labeled real scams. That golden set must be collected from permitted,
consented, redacted sources and evaluated separately.

The generator should be expanded when feedback identifies a missed scenario,
but test cases that triggered a change must remain in a frozen regression set.
Never tune on the final test split.
