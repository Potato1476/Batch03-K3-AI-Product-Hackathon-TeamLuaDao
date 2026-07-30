"""Defense-in-depth checks for content entering the consented scenario store."""

from __future__ import annotations

import re

_LONG_DIGIT_SEQUENCE = re.compile(r"(?<!\d)(?:\d[\s.\-]?){4,}(?!\d)")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")
_EXACT_MONEY = re.compile(
    r"(?i)\b\d+(?:[.,]\d+)?\s*(?:triệu|trieu|tỷ|ty|vnd|vnđ|đồng|dong|đ)\b"
)
_EXPECTED_PLACEHOLDER = re.compile(
    r"<(?:OTP|ACCOUNT|PHONE|NAME|AMOUNT(?::[a-zA-Z_-]+)?)>"
)


class RedactionError(ValueError):
    pass


def validate_l2_redacted(text: str) -> str:
    """Reject likely raw identifiers without returning the offending value."""
    if _EMAIL.search(text):
        raise RedactionError("content_failed_redaction_check")
    without_placeholders = _EXPECTED_PLACEHOLDER.sub("", text)
    if _LONG_DIGIT_SEQUENCE.search(without_placeholders):
        raise RedactionError("content_failed_redaction_check")
    if _EXACT_MONEY.search(without_placeholders):
        raise RedactionError("content_failed_redaction_check")
    return text
