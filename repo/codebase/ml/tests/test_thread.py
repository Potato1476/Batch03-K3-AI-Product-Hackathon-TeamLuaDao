"""L5 conversation analysis — the hijacked-account scenario.

The hard part is not catching the scam thread. It is leaving a real friend
who genuinely needs to borrow money alone, because that conversation contains
the same sentence.
"""

from __future__ import annotations

import pytest

from chan_ml.thread import (
    MIN_BASELINE_MESSAGES,
    ThreadMessage,
    analyze_thread,
)


def thread(*turns: tuple[str, str]) -> list[ThreadMessage]:
    return [ThreadMessage(sender=sender, text=text) for sender, text in turns]


HIJACKED = thread(
    ("contact", "Chào cậu, dạo này công việc thế nào rồi? 😊"),
    ("user", "Tớ vẫn ổn, cậu sao rồi"),
    ("contact", "Mình cũng bình thường thôi. Cuối tuần này rảnh không? ☕"),
    ("user", "Chắc rảnh, sao thế"),
    ("contact", "Đi cà phê nhé, lâu lắm không gặp rồi. 🙂"),
    ("contact", "e dang ket tien qua, ck giup a 15 trieu vao stk 0912345678 duoc k"),
    ("user", "Ơ sao lại cần gấp thế, gọi video cho tớ cái"),
    ("contact", "dang hop k goi dc, nhan tin thoi, chuyen gap giup a"),
)

REAL_FRIEND = thread(
    ("contact", "Chào cậu, dạo này công việc thế nào rồi? 😊"),
    ("user", "Tớ vẫn ổn, cậu sao rồi"),
    ("contact", "Mình cũng bình thường thôi. Cuối tuần này rảnh không? ☕"),
    ("user", "Chắc rảnh, sao thế"),
    ("contact", "Đi cà phê nhé, lâu lắm không gặp rồi. 🙂"),
    ("contact", "Mà này, tháng này mình kẹt quá, cho mình mượn 2 triệu được không? 🙏"),
    ("user", "Được chứ, gọi video cho tớ cái"),
    ("contact", "Ok để mình gọi luôn nhé! 😄"),
)


def test_hijacked_account_thread_is_flagged_high():
    result = analyze_thread(HIJACKED, contact_name="Minh")
    assert result.risk == "high"
    codes = {signal.code for signal in result.thread_signals}
    assert "doi_giong_van" in codes
    assert "ne_goi_thoai" in codes
    assert "gọi video" in result.questions[0].lower()


def test_the_same_request_from_the_real_friend_is_not_flagged_high():
    """Borrowing money is not a scam. Only the change in behaviour is."""
    result = analyze_thread(REAL_FRIEND, contact_name="Minh")
    assert result.risk != "high"
    codes = {signal.code for signal in result.thread_signals}
    assert "doi_giong_van" not in codes
    assert "ne_goi_thoai" not in codes


def test_a_thread_with_no_money_request_stays_unknown():
    result = analyze_thread(
        thread(
            ("contact", "Chào cậu, dạo này thế nào?"),
            ("user", "Ổn cậu ạ"),
            ("contact", "Cuối tuần đi cà phê nhé."),
        )
    )
    assert result.risk == "unknown"
    assert result.thread_signals == ()
    assert "chưa phải kết luận" in result.explanation.lower()


def test_too_little_history_is_reported_not_guessed():
    """Class ①: no baseline to compare against is not the same as no risk."""
    result = analyze_thread(
        thread(
            ("contact", "chao ban"),
            ("contact", "ck giup minh 5 trieu vao stk 0912345678 nhe"),
        ),
        contact_name="Minh",
    )
    assert result.insufficient_history is True
    assert result.baseline_messages < MIN_BASELINE_MESSAGES
    assert result.style_distance is None
    assert "chưa đủ để so" in result.explanation
    assert "doi_giong_van" not in {s.code for s in result.thread_signals}


def test_account_holder_name_differing_from_the_contact_is_high():
    result = analyze_thread(
        thread(
            ("contact", "Chào cậu, dạo này thế nào? 😊"),
            ("user", "Ổn cậu ạ"),
            ("contact", "Cuối tuần đi cà phê nhé. 🙂"),
            ("contact", "Mình cần gấp, chuyển 10 triệu, chủ tài khoản là Tran Van Bao nhé"),
        ),
        contact_name="Nguyen Le Minh",
    )
    codes = {signal.code for signal in result.thread_signals}
    assert "tk_khac_ten" in codes
    assert result.risk == "high"


def test_style_distance_is_reported_for_audit():
    result = analyze_thread(HIJACKED, contact_name="Minh")
    assert result.style_distance is not None
    assert 0.0 <= result.style_distance <= 1.0


@pytest.mark.parametrize(
    "refusal",
    [
        "dang hop k goi dc",
        "mic minh bi hong roi",
        "nhan tin thoi nhe",
        "dang lai xe, goi sau",
    ],
)
def test_common_call_deflections_are_caught(refusal: str):
    result = analyze_thread(
        thread(
            ("contact", "Chào cậu, dạo này thế nào? 😊"),
            ("user", "Ổn cậu ạ"),
            ("contact", "Cuối tuần đi cà phê nhé. 🙂"),
            ("contact", "chuyen giup minh 5 trieu vao stk 0912345678"),
            ("user", "gọi video cho tớ cái"),
            ("contact", refusal),
        )
    )
    assert "ne_goi_thoai" in {s.code for s in result.thread_signals}


def test_no_thread_signal_code_collides_with_the_eight_message_signals():
    from chan_ml.constants import SIGNAL_CODES
    from chan_ml.thread import THREAD_SIGNAL_CODES

    assert not set(THREAD_SIGNAL_CODES) & set(SIGNAL_CODES)
