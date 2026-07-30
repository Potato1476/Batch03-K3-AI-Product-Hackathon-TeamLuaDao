"""Shared normalization and hashing contracts for client/server parity."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import SplitResult, urlsplit, urlunsplit

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_PREFIX = re.compile(r"^[0-9a-f]{2,5}$")


def normalize_url(value: str) -> str:
    """Canonicalize an HTTP(S) URL without fetching it.

    Fragments never reach an HTTP server and are removed. Query strings remain
    intact because phishing kits often use them as routing or victim tokens.
    Credentials are stripped so user information embedded in a URL does not
    affect lookup or persist indirectly in a digest.
    """

    raw = value.strip()
    if len(raw) > 8_192:
        raise ValueError("url_too_long")
    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("unsupported_url_scheme")
    if not parsed.hostname:
        raise ValueError("url_hostname_required")

    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port
    except (UnicodeError, ValueError) as error:
        raise ValueError("invalid_url_hostname_or_port") from error

    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = hostname if port is None else f"{hostname}:{port}"
    path = parsed.path or "/"
    canonical = SplitResult(
        scheme=scheme,
        netloc=netloc,
        path=path,
        query=parsed.query,
        fragment="",
    )
    return urlunsplit(canonical)


def indicator_digest(kind: str, normalized_value: str) -> bytes:
    if kind not in {"account", "phone", "url"}:
        raise ValueError("unsupported_indicator_kind")
    domain_separated = f"chan:{kind}:v1:{normalized_value}"
    return hashlib.sha256(domain_separated.encode("utf-8")).digest()


def normalize_phone(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    if normalized.startswith("+"):
        normalized = normalized[1:]
    digits = re.sub(r"[\s().-]", "", normalized)
    if not digits.isdigit():
        raise ValueError("phone_must_contain_only_dialing_characters")
    if digits.startswith("0084"):
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 10:
        digits = "84" + digits[1:]
    if not 8 <= len(digits) <= 15:
        raise ValueError("phone_must_be_e164_length")
    return digits


def normalize_account(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    compact = re.sub(r"[\s.-]", "", normalized)
    if not re.fullmatch(r"[A-Z0-9]{6,34}", compact):
        raise ValueError("account_must_be_6_to_34_alphanumeric_characters")
    return compact


def hash_url(value: str) -> tuple[bytes, str]:
    digest = indicator_digest("url", normalize_url(value))
    return digest, digest.hex()[:2]


def hash_phone(value: str) -> tuple[bytes, str]:
    digest = indicator_digest("phone", normalize_phone(value))
    return digest, digest.hex()[:2]


def hash_account(value: str) -> tuple[bytes, str]:
    digest = indicator_digest("account", normalize_account(value))
    return digest, digest.hex()[:2]


def parse_sha256_hex(value: str) -> bytes:
    normalized = value.strip()
    if not HEX_SHA256.fullmatch(normalized):
        raise ValueError("sha256_must_be_64_lowercase_hex_characters")
    return bytes.fromhex(normalized)


def validate_prefix(value: str) -> str:
    normalized = value.strip().lower()
    if not HEX_PREFIX.fullmatch(normalized):
        raise ValueError("prefix_must_be_2_to_5_lowercase_hex_characters")
    return normalized
