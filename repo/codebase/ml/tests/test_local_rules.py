import json
from pathlib import Path

from chan_ml.local_rules import evaluate_local_rules, load_rule_bundle


RULES = Path(__file__).resolve().parents[2] / "rules" / "bundle.json"


def test_obfuscated_authority_claim_is_normalized():
    result = evaluate_local_rules(
        "Tôi là c.a.n b.o t.h.u.e, cập nhật hồ sơ ngay.",
        load_rule_bundle(RULES),
    )
    assert "authority_claim" in result.local_signals
    assert result.signal_boosts["mao_danh_tham_quyen"] == 0.20


def test_otp_notice_is_blocked_locally():
    result = evaluate_local_rules(
        "Mã OTP chuyển khoản của bạn là 839201. Không chia sẻ mã này.",
        load_rule_bundle(RULES),
    )
    assert result.otp_blocked is True


def test_bundle_is_valid_json():
    assert json.loads(RULES.read_text(encoding="utf-8"))["schema_version"] == 1


def test_common_one_character_typos_are_corrected_for_rules():
    result = evaluate_local_rules(
        "Thong tin thue bao SIM chua chuab hoa, se khoai SIM sau 24h.",
        load_rule_bundle(RULES),
    )
    assert "sim_lock_notice" in result.local_signals


def test_risk_surface_escalates_a_scam_no_narrow_rule_covers():
    """The narrow catalogue used to gate this message into a silent unknown."""
    bundle = load_rule_bundle(RULES)
    result = evaluate_local_rules(
        "Chào bác, con là nhân viên ngân hàng, tài khoản của bác đang bị khoá, "
        "bác cho con thông tin để mở lại nhé",
        bundle,
    )
    assert "risk_surface" in result.local_signals
    assert "risk_surface" in bundle["l1"]["gate"]["always_call_when_local_signal"]
    # Escalation only: it must not push confidence into any L3 signal.
    assert result.signal_boosts == {}


def test_risk_surface_leaves_ordinary_family_messages_on_the_device():
    result = evaluate_local_rules(
        "Mai con về ăn cơm với bố mẹ nhé",
        load_rule_bundle(RULES),
    )
    assert result.local_signals == ()


def test_meeting_up_is_not_read_as_time_pressure():
    """L0 strips diacritics, so "gặp" and "gấp" collapse to the same token."""
    bundle = load_rule_bundle(RULES)
    for text in (
        "Hẹn gặp bác tại cửa hàng ngày mai lúc 9 giờ",
        "Mai mình gặp nhau ở quán cũ nhé",
        "Chiều nay con qua gặp bố",
        "Em gặp vấn đề với đơn hàng",
    ):
        result = evaluate_local_rules(text, bundle)
        assert "time_pressure" not in result.local_signals, text


def test_real_urgency_still_matches_time_pressure():
    bundle = load_rule_bundle(RULES)
    for text in (
        "Bác chuyển gấp giúp cháu",
        "Con đang cần tiền gấp",
        "Việc này gấp lắm bác ơi",
        "Khẩn cấp: tài khoản sẽ bị khoá",
    ):
        result = evaluate_local_rules(text, bundle)
        assert "time_pressure" in result.local_signals, text


def test_every_bundle_local_signal_is_accepted_by_the_model():
    """A name the bundle emits but the model rejects turns /analyze into a 500."""
    from chan_ml.model import _KNOWN_LOCAL_RULES

    bundle = load_rule_bundle(RULES)
    assert set(bundle["l1"]["local_signals"]) <= set(_KNOWN_LOCAL_RULES)


def test_personal_transfer_request_is_detected():
    result = evaluate_local_rules(
        "Chuyển tiền vào STK 123456789 ngay.",
        load_rule_bundle(RULES),
    )
    assert "personal_transfer_request" in result.local_signals
