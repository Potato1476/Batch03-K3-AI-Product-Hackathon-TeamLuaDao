"""String-only compatibility facade over the canonical L2 redactor."""

from __future__ import annotations

from .redact import RedactionError, redact_l2 as _redact_l2, verify_redacted

__all__ = ["RedactionError", "redact_l2", "validate_l2_redacted"]


def validate_l2_redacted(text: str) -> str:
    return verify_redacted(text)


def redact_l2(text: str) -> str:
    return _redact_l2(text).text
