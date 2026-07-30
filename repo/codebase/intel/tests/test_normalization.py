from __future__ import annotations

import hashlib

import pytest

from chan_intel.normalization import (
    hash_account,
    hash_phone,
    hash_url,
    indicator_digest,
    normalize_url,
    normalize_account,
    normalize_phone,
    parse_sha256_hex,
)


def test_url_normalization_is_deterministic_and_removes_credentials_fragment():
    normalized = normalize_url(
        "HTTPS://User:secret@BÜCHER.example:443/path?a=1#private"
    )
    assert normalized == "https://xn--bcher-kva.example/path?a=1"

    digest, prefix = hash_url(
        "HTTPS://User:secret@BÜCHER.example:443/path?a=1#private"
    )
    assert digest == indicator_digest("url", normalized)
    assert prefix == digest.hex()[:5]


def test_hash_contract_uses_domain_separation():
    value = "0123456789"
    account = indicator_digest("account", value)
    phone = indicator_digest("phone", value)
    assert account != phone
    assert account == hashlib.sha256(
        f"chan:account:v1:{value}".encode()
    ).digest()


def test_vietnam_phone_normalization_uses_e164_digits():
    assert normalize_phone("090 123 4567") == "84901234567"
    assert normalize_phone("+84 (90) 123-4567") == "84901234567"
    assert normalize_phone("0084 90 123 4567") == "84901234567"
    assert hash_phone("090 123 4567") == hash_phone("+84 90 123 4567")


def test_account_normalization_preserves_leading_zeroes():
    assert normalize_account(" 0012-345.678 ") == "0012345678"
    assert hash_account("0012-345.678") == hash_account("0012345678")


@pytest.mark.parametrize(
    "value",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://",
        "not-a-url",
    ],
)
def test_unsafe_or_non_http_urls_are_rejected(value):
    with pytest.raises(ValueError):
        normalize_url(value)


def test_sha256_input_requires_lowercase_hex():
    assert parse_sha256_hex("a" * 64) == bytes.fromhex("a" * 64)
    with pytest.raises(ValueError):
        parse_sha256_hex("A" * 64)
