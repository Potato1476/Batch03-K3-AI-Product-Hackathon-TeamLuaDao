"""Suppress model shortcuts when a message clearly gives protective advice."""

from __future__ import annotations

import re
import unicodedata

import numpy as np

from .constants import SIGNAL_CODES
from .normalize import normalize_for_model


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


def _ascii_normalized(text: str) -> str:
    normalized = normalize_for_model(text)
    return "".join(
        char
        for char in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")


def _has_positive_request(text: str) -> bool:
    for match in _ACTION_VERB_PATTERN.finditer(text):
        prefix = text[max(0, match.start() - 30) : match.start()]
        suffix = text[match.end() : match.end() + 60]
        if _ACTION_TARGET_PATTERN.search(suffix) and not _NEGATED_ACTION_PREFIX.search(
            prefix
        ):
            return True
    return False


def apply_protective_context(
    text: str,
    signal_probabilities: np.ndarray,
    scam_probability: float,
) -> tuple[np.ndarray, float]:
    """Lower unsupported alerts for explicit safety instructions.

    A mixed message that later contains a positive request for credentials,
    money, an APK, or device permissions is not suppressed.
    """

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
