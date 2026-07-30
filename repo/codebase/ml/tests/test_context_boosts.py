import numpy as np

from chan_ml.constants import SIGNAL_CODES
from chan_ml.context_boosts import apply_context_boosts
from chan_ml.protective_context import apply_protective_context


def _low_signals() -> np.ndarray:
    return np.full(len(SIGNAL_CODES), 0.05)


def test_urgent_off_app_qr_payment_gets_bounded_intent_boost():
    _, scam_probability = apply_context_boosts(
        "Quét mã QR ngoài ứng dụng để mở khóa đơn và thanh toán ngay.",
        _low_signals(),
        0.40,
    )
    assert scam_probability == 0.95


def test_normal_merchant_qr_does_not_get_boosted():
    _, scam_probability = apply_context_boosts(
        "Mã QR tại quầy mang tên cửa hàng, hãy kiểm tra người nhận.",
        _low_signals(),
        0.10,
    )
    assert scam_probability == 0.10


def test_delivery_left_elsewhere_with_payment_request_gets_boosted():
    probabilities, scam_probability = apply_context_boosts(
        "Chào bác Lý, bác có đơn hàng ở ngoài cửa, cháu gửi hàng ở nhà "
        "hàng xóm, bác chuyển tiền giúp cháu rồi về nhận sau nhé.",
        _low_signals(),
        0.23,
    )
    transfer_index = SIGNAL_CODES.index("tk_ca_nhan")
    assert probabilities[transfer_index] == 0.72
    assert scam_probability == 0.95


def test_normal_cash_on_delivery_notice_does_not_get_boosted():
    probabilities, scam_probability = apply_context_boosts(
        "Đơn hàng sẽ được giao hôm nay, hãy kiểm tra hàng và thanh toán "
        "đúng số tiền hiển thị trên ứng dụng.",
        _low_signals(),
        0.10,
    )
    assert float(probabilities.max()) == 0.05
    assert scam_probability == 0.10


def test_protective_qr_warning_wins_after_context_boost():
    text = "Không quét mã QR lạ để thanh toán gấp ngoài ứng dụng."
    probabilities, scam_probability = apply_context_boosts(
        text,
        _low_signals(),
        0.40,
    )
    probabilities, scam_probability = apply_protective_context(
        text,
        probabilities,
        scam_probability,
    )
    assert float(probabilities.max()) < 0.50
    assert scam_probability < 0.10
