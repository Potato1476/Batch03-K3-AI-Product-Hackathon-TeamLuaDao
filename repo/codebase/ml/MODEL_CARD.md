# CHẮN Signal Classifier Model Card

## Model

The baseline is a CPU-friendly multi-label linear classifier:

1. Vietnamese text is normalized with Unicode NFKC, invisible-character
   removal, whitespace folding, and lowercase conversion.
2. Word 1–2 grams capture phrases and negation.
3. Character 3–5 grams improve robustness to missing diacritics, teencode,
   typos, and inserted characters.
4. Eight independent class-balanced logistic regressions estimate confidence
   for the eight architecture signals.
5. Whole-message and individual-sentence predictions are max-pooled so one
   suspicious clause is not diluted by unrelated notification text.
6. A temperature selected on validation sharpens conservative independent
   probabilities before the immutable L4 policy computes risk.

The model never learns or emits a `safe` label. It returns only `high`,
`medium`, or `unknown`. OTP and blocklist handling remain hard overrides.

## Intended role

This is an inexpensive L3 benchmark/fallback and a possible signal prior for
the LLM described in the architecture. It does not fine-tune a foundation
model, so it remains compatible with the hackathon's “no LLM fine-tuning”
scope. Its output contract can be placed behind `/v1/analyze` without changing
clients.

The trained artifact must receive only ephemeral, L2-redacted content. Do not
log model input, explanation, or evidence. Predictions may be persisted only
as content hash, signal codes/confidences, score, and version metadata.

## Evidence

Evidence sentences are selected from positive, signal-specific word n-gram
contributions in the linear model and copied from the source text. They are
model-supported spans, not detection regexes. The API can instead use the
LLM's more precise grounded evidence when the primary L3 path is available.

## Acceptance

The evaluation command measures:

- phishing recall: fraction of phishing records predicted `high` or `medium`;
- legitimate false-positive rate: fraction of legitimate records predicted
  `high` or `medium`;
- per-signal precision, recall, and F1;
- exact risk accuracy and risk confusion;
- recall on truncated notifications.

Architecture gates are recall ≥ 0.90 and false-positive rate < 0.15. A pass on
synthetic data is a pipeline check only. Release requires the frozen,
human-labeled golden set and p95 end-to-end latency measurement.

## Limitations

- Linear n-grams cannot reason as broadly as an LLM about unseen manipulation.
- Synthetic template language can inflate measured performance.
- Model probabilities are not yet calibrated on real traffic.
- Similarity is accepted as an input to L4 but must come from the separate
  consented pgvector scenario store.
- The model is Vietnamese-first and has not been validated for other locales.
