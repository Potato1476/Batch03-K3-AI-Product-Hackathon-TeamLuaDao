"""Compatibility exports for the shared threat-indicator hash contract."""

from __future__ import annotations

import re

from chan_ml.indicators import (
    PREFIX_LENGTH,
    indicator_digest,
    normalize_account,
    normalize_phone,
    normalize_url,
)

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_PREFIX = re.compile(rf"^[0-9a-f]{{{PREFIX_LENGTH}}}$")


def _hashed(kind: str, normalized: str) -> tuple[bytes, str]:
    digest = indicator_digest(kind, normalized)
    return digest, digest.hex()[:PREFIX_LENGTH]


def hash_url(value: str) -> tuple[bytes, str]:
    return _hashed("url", normalize_url(value))


def hash_phone(value: str) -> tuple[bytes, str]:
    return _hashed("phone", normalize_phone(value))


def hash_account(value: str) -> tuple[bytes, str]:
    return _hashed("account", normalize_account(value))


def parse_sha256_hex(value: str) -> bytes:
    normalized = value.strip()
    if not HEX_SHA256.fullmatch(normalized):
        raise ValueError("sha256_must_be_64_lowercase_hex_characters")
    return bytes.fromhex(normalized)


def validate_prefix(value: str) -> str:
    normalized = value.strip().lower()
    if not HEX_PREFIX.fullmatch(normalized):
        raise ValueError("prefix_must_be_five_lowercase_hex_characters")
    return normalized
