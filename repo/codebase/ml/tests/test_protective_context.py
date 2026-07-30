import numpy as np

from chan_ml.constants import SIGNAL_CODES
from chan_ml.protective_context import apply_protective_context


def _all_high() -> np.ndarray:
    return np.full(len(SIGNAL_CODES), 0.95)


def test_clear_safety_warning_suppresses_lexical_shortcuts():
    probabilities, scam_probability = apply_protective_context(
        "Không chia sẻ <OTP> cho bất kỳ ai. Hãy tự gọi số trên thẻ.",
        _all_high(),
        0.90,
    )
    assert float(probabilities.max()) < 0.50
    assert probabilities[SIGNAL_CODES.index("yeu_cau_otp")] < 0.50
    assert scam_probability < 0.10


def test_safety_preface_does_not_hide_later_positive_request():
    probabilities, scam_probability = apply_protective_context(
        "Không chia sẻ OTP cho ai khác. Hãy gửi <OTP> cho tôi ngay.",
        _all_high(),
        0.90,
    )
    assert float(probabilities.max()) == 0.95
    assert scam_probability == 0.90


def test_off_platform_payment_request_is_not_suppressed():
    probabilities, scam_probability = apply_protective_context(
        "Không thanh toán qua sàn. Chuyển cọc vào <ACCOUNT> ngay.",
        _all_high(),
        0.90,
    )
    assert float(probabilities.max()) == 0.95
    assert scam_probability == 0.90


def test_bare_numeric_noise_is_not_treated_as_a_scam_request():
    probabilities, scam_probability = apply_protective_context(
        "Alo / <ACCOUNT> / ???",
        _all_high(),
        0.99,
    )
    assert float(probabilities.max()) < 0.05
    assert scam_probability < 0.05


def test_balance_notification_without_a_request_is_suppressed():
    probabilities, scam_probability = apply_protective_context(
        "Vietcombank: So du TK <ACCOUNT> +<AMOUNT:nho>. Ref: Luong T7.",
        _all_high(),
        0.99,
    )
    assert float(probabilities.max()) < 0.05
    assert scam_probability < 0.05


def test_balance_notification_with_transfer_request_is_not_suppressed():
    probabilities, scam_probability = apply_protective_context(
        "So du <ACCOUNT>. Ref: Luong T7. Chuyen vao <ACCOUNT> ngay.",
        _all_high(),
        0.90,
    )
    assert float(probabilities.max()) == 0.95
    assert scam_probability == 0.90
