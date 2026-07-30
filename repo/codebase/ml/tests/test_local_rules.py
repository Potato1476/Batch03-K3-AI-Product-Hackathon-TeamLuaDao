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


def test_personal_transfer_request_is_detected():
    result = evaluate_local_rules(
        "Chuyển tiền vào STK 123456789 ngay.",
        load_rule_bundle(RULES),
    )
    assert "personal_transfer_request" in result.local_signals
