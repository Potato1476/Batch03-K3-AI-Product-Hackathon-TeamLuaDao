from __future__ import annotations

import pytest

from chan_ml.privacy import RedactionError, redact_l2, validate_l2_redacted


def test_l2_placeholders_are_accepted() -> None:
    text = "Chuyển <AMOUNT:trieu> vào <ACCOUNT> rồi gửi <OTP>."
    assert validate_l2_redacted(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "Liên hệ victim@example.com để xác minh.",
        "Chuyển vào 1234 5678 9012 ngay.",
        "Chuyển 12 triệu đồng ngay.",
    ],
)
def test_likely_raw_identifiers_are_rejected_without_echo(text: str) -> None:
    with pytest.raises(
        RedactionError, match=r"^content_failed_redaction_check$"
    ):
        validate_l2_redacted(text)


def test_l2_redacts_values_but_keeps_semantic_placeholders() -> None:
    raw = (
        "Gửi OTP 938271 và chuyển 12 triệu vào tài khoản "
        "1234 5678 9012. Liên hệ victim@example.com."
    )
    assert redact_l2(raw) == (
        "Gửi OTP <OTP> và chuyển <AMOUNT:trieu> vào tài khoản "
        "<ACCOUNT>. Liên hệ <NAME>."
    )


def test_l2_distinguishes_phone_from_account_using_context() -> None:
    assert redact_l2("Gọi số điện thoại 090 123 4567.") == (
        "Gọi số điện thoại <PHONE>."
    )
