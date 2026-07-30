"""Defense-in-depth checks for content entering the consented scenario store.

The implementation lives in ``chan_ml.redact`` so the public gateway (which
performs L2 redaction) and this private API (which verifies it was performed)
can never disagree about what "redacted" means. This module stays as the
service-local name for that check.
"""

from __future__ import annotations

from chan_ml.redact import RedactionError, verify_redacted

__all__ = ["RedactionError", "validate_l2_redacted"]


def validate_l2_redacted(text: str) -> str:
    """Reject likely raw identifiers without returning the offending value."""
    return verify_redacted(text)
