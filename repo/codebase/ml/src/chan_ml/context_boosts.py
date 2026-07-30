"""Conservative L0 context boosts for attacks requiring another detector."""

from __future__ import annotations

import re
import unicodedata

import numpy as np

from .normalize import normalize_for_model


_QR_MARKER = re.compile(r"\b(?:quet ma|ma qr|qr)\b")
_QR_ACTION = re.compile(
    r"\b(?:mo khoa|hoan tien|thanh toan|chuyen|nop|gui anh bien lai)\b"
)
_QR_PRESSURE = re.compile(r"\b(?:ngay|gap|trong \d+ phut|ngoai ung dung|link la)\b")


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
    """Boost scam intent only for a QR marker plus action and pressure.

    This does not authenticate or decode the QR. Clients must still decode the
    payload and send its URL/account hash to the Lookup service.
    """

    normalized = _ascii_normalized(text)
    if (
        _QR_MARKER.search(normalized)
        and _QR_ACTION.search(normalized)
        and _QR_PRESSURE.search(normalized)
    ):
        return signal_probabilities, max(float(scam_probability), 0.95)
    return signal_probabilities, scam_probability
