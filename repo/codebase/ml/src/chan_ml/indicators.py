"""Canonical normalization and hashing for all threat-indicator consumers."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import SplitResult, urlsplit, urlunsplit

PREFIX_LENGTH = 5


def normalize_url(value: str) -> str:
    raw = value.strip()
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if (
        scheme not in {"http", "https"}
        or not parsed.hostname
        or "." not in parsed.hostname
    ):
        raise ValueError("invalid_http_url")
    hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = hostname if port is None else f"{hostname}:{port}"
    return urlunsplit(
        SplitResult(scheme, netloc, parsed.path or "/", parsed.query, "")
    )


def normalize_phone(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    if normalized.startswith("+"):
        normalized = normalized[1:]
    digits = re.sub(r"[\s().-]", "", normalized)
    if digits.startswith("0084"):
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 10:
        digits = "84" + digits[1:]
    if not digits.isdigit() or not 8 <= len(digits) <= 15:
        raise ValueError("invalid_phone")
    return digits


def normalize_account(value: str) -> str:
    compact = re.sub(
        r"[\s.-]", "", unicodedata.normalize("NFKC", value).strip().upper()
    )
    if not re.fullmatch(r"[A-Z0-9]{6,34}", compact):
        raise ValueError("invalid_account")
    return compact


def normalize_indicator(kind: str, value: str) -> str:
    if kind == "account":
        return normalize_account(value)
    if kind == "phone":
        return normalize_phone(value)
    if kind == "url":
        return normalize_url(value)
    raise ValueError("unsupported_indicator_kind")


def indicator_digest(kind: str, normalized_value: str) -> bytes:
    if kind not in {"account", "phone", "url"}:
        raise ValueError("unsupported_indicator_kind")
    return hashlib.sha256(
        f"chan:{kind}:v1:{normalized_value}".encode("utf-8")
    ).digest()


def hash_identifier(value: str, *, kind: str = "account") -> str:
    return indicator_digest(kind, normalize_indicator(kind, value)).hex()


def hash_prefix(digest: str) -> str:
    return digest[:PREFIX_LENGTH]
