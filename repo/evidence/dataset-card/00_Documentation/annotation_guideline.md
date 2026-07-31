# CHẮN Dataset Annotation Guidelines

## Message-Level Guidelines
- **sender**: `scammer` vs `victim` (or `user_a`, `user_b` for negative).
- **stage**: one of `contact`, `building_trust`, `solicitation`, `demanding_money`, `conclusion`.
- **signals**: list of detected anti-scam signal IDs.
- **risk**: `none`, `low`, `medium`, `high`, `critical`.

## Conversation-Level Guidelines
- **outcome**:
  - `victim_transferred_money`
  - `victim_detected_and_blocked`
  - `victim_suspicious_refused`
  - `legitimate_resolved` (for negative)
- **source**: attributed seed dataset or `synthetic_llm`.
