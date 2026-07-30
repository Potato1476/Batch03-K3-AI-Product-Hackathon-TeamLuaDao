"""Shared privacy checks at the L2-redacted model boundary."""

from __future__ import annotations

import re

_LONG_DIGIT_SEQUENCE = re.compile(r"(?<!\d)\d(?:[\s.\-]?\d){3,}(?!\d)")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")
_EXACT_MONEY = re.compile(
    r"(?i)\b\d+(?:[.,]\d+)?\s*(?:triệu|trieu|tỷ|ty|vnd|vnđ|đồng|dong|đ)\b"
)
_EXPECTED_PLACEHOLDER = re.compile(
    r"<(?:OTP|ACCOUNT|PHONE|NAME|AMOUNT(?::[a-zA-Z_-]+)?)>"
)
_OTP_WITH_VALUE = re.compile(
    r"(?i)(\b(?:otp|mã\s+(?:xác\s+thực|xác\s+nhận|bảo\s+mật))"
    r"\b[^\d<>]{0,30})(\d(?:[\s.\-]?\d){3,7})(?!\d)"
)
_ACCOUNT_CONTEXT = re.compile(
    r"(?i)(?:tài\s*khoản|tai\s*khoan|số\s*tk|stk|chuyển\s*khoản|"
    r"chuyen\s*khoan|ngân\s*hàng|ngan\s*hang)"
)
_PHONE_CONTEXT = re.compile(
    r"(?i)(?:số\s*điện\s*thoại|so\s*dien\s*thoai|sđt|sdt|"
    r"điện\s*thoại|dien\s*thoai|gọi|goi|liên\s*hệ|lien\s*he)"
)


class RedactionError(ValueError):
    """Raised without retaining or returning the rejected content."""


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


def redact_l2(text: str) -> str:
    """Redact common Vietnamese PII in memory before model inference.

    This is defense in depth for the server boundary. Clients must still stop
    raw OTP values at L1, and this function must run before logging, tracing,
    persistence, or any model/provider call.
    """

    redacted = _EMAIL.sub("<NAME>", text)

    def replace_money(match: re.Match[str]) -> str:
        token = match.group(0).casefold()
        if "tỷ" in token or re.search(r"\bty\b", token):
            magnitude = "ty"
        elif "triệu" in token or "trieu" in token:
            magnitude = "trieu"
        else:
            magnitude = "vnd"
        return f"<AMOUNT:{magnitude}>"

    redacted = _EXACT_MONEY.sub(replace_money, redacted)
    redacted = _OTP_WITH_VALUE.sub(lambda match: f"{match.group(1)}<OTP>", redacted)

    def replace_digits(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        start, end = match.span()
        context = redacted[max(0, start - 48) : min(len(redacted), end + 32)]
        if _ACCOUNT_CONTEXT.search(context):
            return "<ACCOUNT>"
        if _PHONE_CONTEXT.search(context):
            return "<PHONE>"
        if 4 <= len(digits) <= 8:
            return "<OTP>"
        if 9 <= len(digits) <= 11:
            return "<PHONE>"
        return "<ACCOUNT>"

    redacted = _LONG_DIGIT_SEQUENCE.sub(replace_digits, redacted)
    return validate_l2_redacted(redacted)
