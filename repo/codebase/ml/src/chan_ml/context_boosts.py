"""Conservative L0 context boosts for attacks requiring another detector."""

from __future__ import annotations

import re
import unicodedata

import numpy as np

from .constants import SIGNAL_CODES
from .normalize import normalize_for_model


_QR_MARKER = re.compile(r"\b(?:quet ma|ma qr|qr)\b")
_QR_ACTION = re.compile(
    r"\b(?:mo khoa|hoan tien|thanh toan|chuyen|nop|gui anh bien lai)\b"
)
_QR_PRESSURE = re.compile(r"\b(?:ngay|gap|trong \d+ phut|ngoai ung dung|link la)\b")
_DELIVERY_MARKER = re.compile(r"\b(?:don hang|giao hang|shipper|buu pham|goi hang)\b")
_PAYMENT_REQUEST = re.compile(
    r"\b(?:chuyen (?:tien|khoan)|gui tien|thanh toan (?:ho|truoc)|"
    r"dong phi|tra tien giup)\b"
)
_SUSPICIOUS_DELIVERY_HANDOFF = re.compile(
    r"\b(?:ngoai cua|nha hang xom|nhan sau|lay sau|giu don|"
    r"don chua thanh toan|giao nham|hoi vien|huy don|dang ky)\b"
)


def _ascii_normalized(text: str) -> str:
    normalized = normalize_for_model(text)
    return "".join(
        char
        for char in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")


def apply_context_boosts(
    text: str,
    signal_probabilities: np.ndarray,
    scam_probability: float,
) -> tuple[np.ndarray, float]:
    """Apply bounded boosts for high-signal multi-phrase scam contexts.

    A single delivery or payment phrase is deliberately insufficient: the
    delivery boost requires the conjunction of a parcel marker, a request for
    money, and an unusual handoff/subscription context.
    """

    normalized = _ascii_normalized(text)
    if (
        _QR_MARKER.search(normalized)
        and _QR_ACTION.search(normalized)
        and _QR_PRESSURE.search(normalized)
    ):
        scam_probability = max(float(scam_probability), 0.95)

    if (
        _DELIVERY_MARKER.search(normalized)
        and _PAYMENT_REQUEST.search(normalized)
        and _SUSPICIOUS_DELIVERY_HANDOFF.search(normalized)
    ):
        signal_probabilities = signal_probabilities.copy()
        transfer_index = SIGNAL_CODES.index("tk_ca_nhan")
        signal_probabilities[transfer_index] = max(
            float(signal_probabilities[transfer_index]), 0.72
        )
        scam_probability = max(float(scam_probability), 0.95)

    return signal_probabilities, scam_probability
