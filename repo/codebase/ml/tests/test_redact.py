"""L2 redaction is invariant I1 and I2 in executable form."""

from __future__ import annotations

import pytest

from chan_ml.redact import (
    RedactionError,
    hash_identifier,
    hash_prefix,
    normalize_account,
    normalize_phone,
    normalize_url,
    redact_l2,
    verify_redacted,
)


def test_otp_never_survives_redaction() -> None:
    """I1: an OTP must not reach the model even as a fragment."""
    for text in (
        "Doc ma 938271 de xac minh",
        "OTP: 12 34 56 gui cho toi",
        "Ma xac thuc 4821 vua gui, doc cho anh",
        "ma otp la 55-66-77",
    ):
        result = redact_l2(text)
        assert result.otp_found is True, text
        assert "<OTP>" in result.text
        for digits in ("938271", "1234", "4821", "556677"):
            assert digits not in result.text.replace(" ", "")


def test_every_placeholder_shape_is_the_architecture_shape() -> None:
    result = redact_l2(
        "Anh Nguyen Van A chuyen 20 trieu vao 19001234567890, goi 0912345678, "
        "xem http://scam-site.xyz/a"
    )
    assert "<NAME>" in result.text
    assert "<AMOUNT:trieu>" in result.text
    assert "<ACCOUNT>" in result.text
    assert "<PHONE>" in result.text
    assert "<URL>" in result.text


def test_redacted_output_always_passes_its_own_verifier() -> None:
    """redact_l2 and verify_redacted must agree, or the training bridge breaks."""
    for text in (
        "Chuyen 1.500.000 dong vao tk 19001234567890 cua anh Hung",
        "Goi lai so 0912345678 hoac +84987654321 nhe",
        "Lien he email scam@fake.com",
        "Trung thuong 500 trieu, truy cap bit.ly/abc de nhan",
        "Nha truong thong bao hop phu huynh sang thu 7",
    ):
        verify_redacted(redact_l2(text).text)


def test_money_keeps_magnitude_and_drops_exact_value() -> None:
    assert "<AMOUNT:trieu>" in redact_l2("chuyen 20 trieu").text
    assert "<AMOUNT:trieu>" in redact_l2("chuyen 1.500.000 dong").text
    assert "<AMOUNT:ty>" in redact_l2("trung thuong 2 ty").text
    assert "<AMOUNT:nghin>" in redact_l2("phi 500 nghin").text
    assert "1.500.000" not in redact_l2("chuyen 1.500.000 dong").text


def test_legitimate_message_is_left_intact() -> None:
    """Over-redaction destroys the signal the model needs. Small numbers stay."""
    text = "Nha truong thong bao hop phu huynh sang thu 7 tai lop 5A"
    assert redact_l2(text).text == text


def test_lowercase_word_after_honorific_is_not_a_name() -> None:
    """A pattern-wide (?i) would wrongly redact 'thue' in 'can bo thue'."""
    result = redact_l2("Toi la can bo thue, moi anh len lam viec")
    assert "thue" in result.text
    assert result.text.count("<NAME>") == 0


def test_placeholder_does_not_swallow_the_next_word() -> None:
    result = redact_l2("chuyen vao 0123456789 truoc 17h")
    assert "> truoc" in result.text


def test_hashes_are_kept_for_lookup_but_text_is_not() -> None:
    """§4: the account hash is retained for Lookup; the digits are not."""
    result = redact_l2("chuyen vao tk 19001234567890 ngay")
    assert result.account_hashes
    assert len(result.account_hashes[0]) == 64
    assert "19001234567890" not in result.text
    assert result.account_hashes[0] == hash_identifier("19001234567890")


def test_identifier_normalisation_collapses_equivalent_forms() -> None:
    assert normalize_account("1900 1234-567890") == "19001234567890"
    assert normalize_phone("+84912345678") == "84912345678"
    assert normalize_phone("0912 345 678") == "84912345678"
    assert normalize_url("https://WWW.Scam-Site.xyz/login?a=1") == (
        "https://www.scam-site.xyz/login?a=1"
    )
    assert normalize_url("http://scam-site.xyz") == "http://scam-site.xyz/"


def test_prefix_is_five_hex_characters() -> None:
    """I4: the k-anonymity bucket is exactly five hex characters."""
    prefix = hash_prefix(hash_identifier("19001234567890"))
    assert len(prefix) == 5
    assert all(character in "0123456789abcdef" for character in prefix)


def test_verifier_rejects_raw_identifiers_without_echoing_them() -> None:
    for text in ("Gui ma 938271 cho toi", "chuyen 20 trieu", "mail a@b.com"):
        with pytest.raises(RedactionError) as error:
            verify_redacted(text)
        assert str(error.value) == "content_failed_redaction_check"


def test_redactor_rejects_non_string() -> None:
    with pytest.raises(TypeError):
        redact_l2(None)  # type: ignore[arg-type]
