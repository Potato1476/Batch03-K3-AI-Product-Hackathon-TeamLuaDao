# CHẮN Signal Classifier Model Card

## Model

The baseline is a CPU-friendly multi-label linear classifier:

1. Vietnamese text is normalized with Unicode NFKC, invisible-character
   removal, whitespace folding, lowercase conversion, and bounded joining of
   single-character separator obfuscation such as `c.a.n b.o`.
2. Word 1–2 grams capture phrases and negation.
3. Character 3–5 grams improve robustness to missing diacritics, teencode,
   typos, and inserted characters.
4. Training adds deterministic, label-preserving variants with missing
   accents, a deleted/swapped/replaced character, separator obfuscation, or
   whitespace changes. URL, number, and redaction placeholders are preserved.
5. A bounded one-edit correction layer protects high-risk vocabulary before
   L1 rules, while ambiguous common Vietnamese words are excluded from
   correction to limit false positives.
6. Eight independent class-balanced logistic regressions estimate confidence
   for the eight architecture signals.
7. A separate whole-message word 1–3 gram plus character 3–5 gram logistic
   regression estimates scam intent. Character features improve robustness to
   spelling variants and missing diacritics while whole-message features
   preserve negation context that sentence max-pooling can lose.
8. Clear protective instructions such as "do not share OTP" suppress lexical
   shortcuts unless the message later contains a positive request for money,
   credentials, an APK, or device permissions.
9. Whole-message and individual-sentence signal predictions are max-pooled so one
   suspicious clause is not diluted by unrelated notification text.
10. A temperature sharpens conservative independent probabilities. Medium and
   high scam-intent thresholds are then selected on the primary validation
   split under recall and false-positive safety gates before L4 computes risk.
11. The Gateway independently verifies L1 rules against the raw request. Those
   verified rules can apply conservative signal/scam floors; unverified client
   claims are discarded. Additive boosts remain capped at 0.45.

The L4 score combines signal confidence, a bounded validation-selected scam
prior (`0.405`), optional consented-scenario similarity, and blocklist
overrides. The model never learns or emits a `safe` label. It returns only `high`,
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
- per-scenario phishing recall and legitimate false-positive rate.

Architecture gates are recall ≥ 0.90 and false-positive rate < 0.15. Synthetic
evaluation additionally requires every phishing family to reach recall ≥ 0.80
and every legitimate family to remain below 0.15 false positives. A pass on
synthetic data is a pipeline check only. Release requires the frozen,
human-labeled golden set and p95 end-to-end latency measurement.

The `ml-0.5.0` release scored 20/20 on the frozen team workbook and 136/136 on
deterministically generated, train-unseen typo variants. Its stricter
variable-family held-out team test recall is 93.60%, legitimate false-positive
rate is 8.22%, and full-product supported-signal macro-F1 is 86.61%.

## Limitations

- Linear n-grams cannot reason as broadly as an LLM about unseen manipulation.
- Robustness is measured for the tested one-edit and formatting mutations; it
  is not a guarantee for arbitrary corruption or future scam families.
- Synthetic template language can inflate measured performance.
- The project-provided source currently collapses from 89,837 messages to
  1,807 unique post-redaction texts. Variable-collapsed message families stay
  in one split. Replay preserves rare secrecy/channel coverage but does not
  turn duplicates into independent evidence.
- Model probabilities are not yet calibrated on real traffic.
- Similarity is accepted as an input to L4 but must come from the separate
  consented pgvector scenario store.
- The model is Vietnamese-first and has not been validated for other locales.
