"""L2 anonymisation — the server-edge redactor from CHAN-ARCHITECTURE.md §4.

Two services need identical L2 behaviour: the public gateway redacts before any
content reaches a model (I1, I2), and the private training API validates that
submitted scenarios were already redacted. Keeping one implementation here means
the two cannot drift.

Placeholders are fixed by the architecture and must not be renamed:

    OTP / mã xác thực → <OTP>          # already blocked at L1; this is layer two
    số tài khoản      → <ACCOUNT>      # hash kept aside for the Lookup Service
    số điện thoại     → <PHONE>
    tên riêng         → <NAME>
    số tiền           → <AMOUNT:trieu> # magnitude survives, exact value does not

This module never logs and never returns an offending value in an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .indicators import (
    PREFIX_LENGTH,
    hash_identifier,
    hash_prefix,
    normalize_account,
    normalize_phone,
    normalize_url,
)

__all__ = [
    "RedactionError",
    "RedactionResult",
    "redact_l2",
    "verify_redacted",
    "hash_identifier",
    "hash_prefix",
    "normalize_account",
    "normalize_phone",
    "normalize_url",
    "PREFIX_LENGTH",
]

# --- L2 detection patterns -------------------------------------------------
#
# Ordering matters and is enforced by redact_l2: OTP first (an OTP is also a
# plain digit run, and I1 says it must never survive), then accounts, then
# phones, then money. Every pattern is deliberately greedy about digits so a
# near-miss redacts too much rather than too little.

# Digit runs are written as `\d(?:[sep]?\d){n,m}` rather than `(?:\d[sep]?){n,m}`
# so a separator is only consumed *between* digits. The naive form lets the last
# repetition swallow the following space and glues the placeholder to the next
# word, which corrupts the tokens the model is about to see.

# "ma 938271", "OTP: 12 34 56", "mã xác thực 4821"
_OTP_LABELLED = re.compile(
    r"(?i)\b(?:m[ãa]\s*(?:otp|pin|x[áa]c\s*(?:thực|thuc|minh|nhận|nhan))?|otp|pin)"
    r"\s*(?:l[àa]|is|:|=|-)?\s*(\d(?:[\s.\-]?\d){3,7})(?!\d)"
)
# A bare 4-8 digit run adjacent to verification wording.
_OTP_CONTEXTUAL = re.compile(
    r"(?i)(?<!\d)(\d(?:[\s.\-]?\d){3,7})\s*(?:l[àa]\s*)?"
    r"(?:m[ãa]\s*(?:otp|x[áa]c\s*(?:thực|thuc|minh))|otp)"
)

# Vietnamese bank accounts run 8-19 digits; card numbers reach 19.
_ACCOUNT = re.compile(r"(?<!\d)(\d(?:[\s.\-]?\d){7,18})(?!\d)")
# Domestic mobile numbers: 0xxxxxxxxx / +84xxxxxxxxx, 9-11 digits.
_PHONE = re.compile(r"(?<!\d)((?:\+?84|0)(?:[\s.\-]?\d){8,10})(?!\d)")
# Any leftover identifier-shaped digit run after the specific rules ran.
_RESIDUAL_DIGITS = re.compile(r"(?<!\d)\d(?:[\s.\-]?\d){3,}(?!\d)")

_MONEY = re.compile(
    r"(?i)(\d+(?:[.,]\d+)*)\s*"
    r"(triệu|trieu|tỷ|ty|nghìn|nghin|ngàn|ngan|k\b|vnđ|vnd|đồng|dong|đ\b)"
)

_URL = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>\"']+"
    r"|\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|net|org|vn|info|xyz|top|icu|cc|co|io|me|shop|online|site|link|app)"
    r"(?:/[^\s<>\"']*)?"
)

_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")

# Vietnamese given names appear after an honorific. We only redact the name that
# follows a title, because bare capitalised words are far too often ordinary
# nouns in a message and over-redaction destroys classification signal.
# The honorific match is case-insensitive, but the name must stay case-SENSITIVE:
# a scoped `(?i:...)` group is required, because a pattern-wide `(?i)` would also
# apply to `[A-ZÀ-Ỹ]` and turn every lowercase word after a title into a name.
_NAME_AFTER_HONORIFIC = re.compile(
    r"\b(?i:(anh|chị|chi|ông|ong|bà|ba|bác|bac|cô|co|chú|chu|"
    r"em|cậu|cau|dì|di|thầy|thay))\s+"
    r"((?:[A-ZÀ-Ỹ][\wÀ-ỹ]*)(?:\s+[A-ZÀ-Ỹ][\wÀ-ỹ]*){0,2})(?!\w)"
)

# --- verification patterns (defence in depth, shared with the training API) --

_EXPECTED_PLACEHOLDER = re.compile(
    r"<(?:OTP|ACCOUNT|PHONE|NAME|URL|AMOUNT(?::[a-zA-Z_-]+)?)>"
)
_LONG_DIGIT_SEQUENCE = re.compile(r"(?<!\d)(?:\d[\s.\-]?){4,}(?!\d)")
_EXACT_MONEY = re.compile(
    r"(?i)\b\d+(?:[.,]\d+)?\s*(?:triệu|trieu|tỷ|ty|vnd|vnđ|đồng|dong|đ)\b"
)

_MAGNITUDES: tuple[tuple[float, str], ...] = (
    (1_000_000_000, "ty"),
    (1_000_000, "trieu"),
    (1_000, "nghin"),
)

_UNIT_SCALE: dict[str, float] = {
    "triệu": 1_000_000,
    "trieu": 1_000_000,
    "tỷ": 1_000_000_000,
    "ty": 1_000_000_000,
    "nghìn": 1_000,
    "nghin": 1_000,
    "ngàn": 1_000,
    "ngan": 1_000,
    "k": 1_000,
    "vnđ": 1,
    "vnd": 1,
    "đồng": 1,
    "dong": 1,
    "đ": 1,
}


class RedactionError(ValueError):
    """Raised when text still looks like it carries a raw identifier."""


@dataclass(frozen=True)
class RedactionResult:
    """The only value allowed to leave L2. `text` is RAM-only, per §7.2."""

    text: str
    otp_found: bool = False
    account_hashes: tuple[str, ...] = field(default=())
    phone_hashes: tuple[str, ...] = field(default=())
    url_hashes: tuple[str, ...] = field(default=())

    @property
    def all_hashes(self) -> tuple[str, ...]:
        return self.account_hashes + self.phone_hashes + self.url_hashes


# --- the redactor -----------------------------------------------------------


def _money_placeholder(amount: str, unit: str) -> str:
    """Keep the order of magnitude, drop the exact value (§4)."""
    scale = _UNIT_SCALE.get(unit.lower(), 1.0)
    try:
        quantity = float(amount.replace(".", "").replace(",", "."))
    except ValueError:
        quantity = 1.0
    total = quantity * scale
    for threshold, label in _MAGNITUDES:
        if total >= threshold:
            return f"<AMOUNT:{label}>"
    return "<AMOUNT:nho>"


def redact_l2(text: str) -> RedactionResult:
    """Replace every identifier with a placeholder; keep hashes for lookup.

    The returned text is safe to hand to a model. The returned hashes are safe
    to compare against the blocklist. Neither may be written to a log.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    account_hashes: list[str] = []
    phone_hashes: list[str] = []
    url_hashes: list[str] = []
    otp_found = False
    working = text

    # 1. Email before URL: an address ends in a domain, so the URL rule would
    #    otherwise leave the local part exposed as "someone@<URL>".
    working = _EMAIL.sub("<NAME>", working)

    # 2. URLs next: a link can contain digit runs that would otherwise be
    #    mistaken for an account number.
    def _take_url(match: re.Match[str]) -> str:
        host = normalize_url(match.group(0))
        if host:
            url_hashes.append(hash_identifier(host, kind="url"))
        return "<URL>"

    working = _URL.sub(_take_url, working)

    # 3. OTP before any other digit rule — I1 allows no exception.
    def _take_otp(match: re.Match[str]) -> str:
        nonlocal otp_found
        otp_found = True
        return match.group(0).replace(match.group(1), "<OTP>")

    working, labelled = _OTP_LABELLED.subn(_take_otp, working)
    working, contextual = _OTP_CONTEXTUAL.subn(_take_otp, working)
    if labelled or contextual:
        otp_found = True

    # 4. Money before accounts: "20 triệu" must not be read as an account.
    working = _MONEY.sub(
        lambda match: _money_placeholder(match.group(1), match.group(2)), working
    )

    # 5. Phones before accounts: a phone is a shorter, more specific pattern.
    def _take_phone(match: re.Match[str]) -> str:
        normalized = normalize_phone(match.group(1))
        if normalized:
            phone_hashes.append(hash_identifier(normalized, kind="phone"))
        return "<PHONE>"

    working = _PHONE.sub(_take_phone, working)

    def _take_account(match: re.Match[str]) -> str:
        normalized = normalize_account(match.group(1))
        if normalized:
            account_hashes.append(hash_identifier(normalized))
        return "<ACCOUNT>"

    working = _ACCOUNT.sub(_take_account, working)

    # 6. Any remaining 4+ digit run is an unclassified identifier. Redact it
    #    rather than let it through: verify_redacted would reject it anyway.
    working = _RESIDUAL_DIGITS.sub("<ACCOUNT>", working)

    # 7. Names last — the honorific itself is a useful signal, so it stays.
    working = _NAME_AFTER_HONORIFIC.sub(
        lambda match: f"{match.group(1)} <NAME>", working
    )

    return RedactionResult(
        text=working,
        otp_found=otp_found,
        account_hashes=tuple(dict.fromkeys(account_hashes)),
        phone_hashes=tuple(dict.fromkeys(phone_hashes)),
        url_hashes=tuple(dict.fromkeys(url_hashes)),
    )


def verify_redacted(text: str) -> str:
    """Reject likely raw identifiers without returning the offending value."""
    if _EMAIL.search(text):
        raise RedactionError("content_failed_redaction_check")
    without_placeholders = _EXPECTED_PLACEHOLDER.sub("", text)
    if _LONG_DIGIT_SEQUENCE.search(without_placeholders):
        raise RedactionError("content_failed_redaction_check")
    if _EXACT_MONEY.search(without_placeholders):
        raise RedactionError("content_failed_redaction_check")
    return text
