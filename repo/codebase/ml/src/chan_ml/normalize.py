"""Minimal L3 normalization.

The authoritative L0/L1 rules still belong in packages/rules/*.json. This
module only makes model input stable after L2 redaction; it does not implement
client-side detection rules.
"""

from __future__ import annotations

import re
import unicodedata

_INVISIBLE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
_WHITESPACE = re.compile(r"\s+")


def normalize_for_model(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    value = unicodedata.normalize("NFKC", text)
    value = _INVISIBLE.sub("", value)
    value = _WHITESPACE.sub(" ", value).strip().lower()
    return value
