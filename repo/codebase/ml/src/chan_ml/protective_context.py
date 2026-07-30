"""Suppress model shortcuts when a message clearly gives protective advice."""

from __future__ import annotations

import re
import unicodedata

import numpy as np

from .constants import SIGNAL_CODES
from .local_rules import correct_common_typos
from .normalize import normalize_for_model
from .guidance import is_victim_recovery_request


_SAFETY_PATTERNS = (
    re.compile(
        r"\b(?:khong|ko)\s+(?:bao gio\s+)?(?:can\s+|yeu cau\s+|nen\s+)?"
        r"(?:cung cap|chia se|doc|gui|chuyen|nap|thanh toan|cai|bat|bam|mo|quet)\b"
    ),
    re.compile(r"\bday khong phai (?:la\s+)?yeu cau\b"),
    re.compile(r"\bneu khong thuc hien giao dich\b"),
    re.compile(r"\btu (?:goi|mo|tra cuu|kiem tra)\b"),
    re.compile(r"\bchi (?:thuc hien|cai|thanh toan|tra cuu).*\bchinh thuc\b"),
)

_ACTION_VERB_PATTERN = re.compile(
    r"\b(?:chuyen|gui|nop|thanh toan|doc|cung cap|tai|cai|bat|quet)\b"
)
_ACTION_TARGET_PATTERN = re.compile(
    r"(?:<account>|<otp>|apk|tai khoan|quyen|phan mem|ung dung|ma qr|qr)"
)
_NEGATED_ACTION_PREFIX = re.compile(r"(?:khong|ko)(?:\s+\w+){0,8}\s*$")
_BENIGN_CONTEXT_PATTERNS = (
    re.compile(r"\bchuc .{0,24}(?:ngay|buoi).{0,20}tot (?:lanh|lang|dep|vui)\b"),
    re.compile(
        r"\b(?:so du|bien dong so du)\b.{0,100}"
        r"(?:\bref\b|\bluong\b|\bnoi dung\b)"
    ),
)
_LOW_INFORMATION_ALLOWED = {
    "alo",
    "account",
    "anh",
    "bac",
    "chi",
    "em",
    "hello",
    "oke",
    "ok",
}


def _ascii_normalized(text: str) -> str:
    normalized = normalize_for_model(text)
    ascii_text = "".join(
        char
        for char in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")
    return correct_common_typos(ascii_text)


def _has_positive_request(text: str) -> bool:
    for match in _ACTION_VERB_PATTERN.finditer(text):
        prefix = text[max(0, match.start() - 30) : match.start()]
        suffix = text[match.end() : match.end() + 60]
        if _ACTION_TARGET_PATTERN.search(suffix) and not _NEGATED_ACTION_PREFIX.search(
            prefix
        ):
            return True
    return False


def _is_low_information(text: str) -> bool:
    without_placeholders = re.sub(r"<[^>]+>", " account ", text)
    words = re.findall(r"\b[a-z]+\b", without_placeholders)
    return bool(words) and len(words) <= 6 and set(words) <= _LOW_INFORMATION_ALLOWED


def is_protective_message(text: str) -> bool:
    """Return whether explicit safety context should suppress rule/model hits."""

    normalized = _ascii_normalized(text)
    if is_victim_recovery_request(text):
        return True
    has_safety_instruction = any(
        pattern.search(normalized) for pattern in _SAFETY_PATTERNS
    )
    benign_context = any(
        pattern.search(normalized) for pattern in _BENIGN_CONTEXT_PATTERNS
    )
    return (
        has_safety_instruction
        or benign_context
        or _is_low_information(normalized)
    ) and not _has_positive_request(normalized)


def apply_protective_context(
    text: str,
    signal_probabilities: np.ndarray,
    scam_probability: float,
) -> tuple[np.ndarray, float]:
    """Lower unsupported alerts for explicit safety instructions.

    A mixed message that later contains a positive request for credentials,
    money, an APK, or device permissions is not suppressed.
    """

    if is_victim_recovery_request(text):
        adjusted = np.asarray(signal_probabilities, dtype=float).copy()
        adjusted *= 0.02
        return adjusted, min(float(scam_probability) * 0.05, 0.05)
    if is_protective_message(text):
        adjusted = np.asarray(signal_probabilities, dtype=float).copy()
        adjusted *= 0.02
        return adjusted, min(float(scam_probability) * 0.05, 0.05)
    normalized = _ascii_normalized(text)
    has_safety_instruction = any(
        pattern.search(normalized) for pattern in _SAFETY_PATTERNS
    )
    if not has_safety_instruction or _has_positive_request(normalized):
        return signal_probabilities, scam_probability

    adjusted = np.asarray(signal_probabilities, dtype=float).copy()
    adjusted *= 0.05
    # OTP is a hard L4 override, so ensure clear "do not share" instructions
    # cannot cross the signal decision threshold due to lexical overlap.
    otp_index = SIGNAL_CODES.index("yeu_cau_otp")
    adjusted[otp_index] = min(adjusted[otp_index], 0.05)
    return adjusted, min(float(scam_probability) * 0.10, 0.10)
