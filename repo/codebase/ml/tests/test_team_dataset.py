import json
from pathlib import Path

from chan_ml.team_dataset import derive_signal_codes, prepare_records


def _write_conversation(
    root: Path,
    relative: str,
    *,
    label: str,
    sender: str,
    text: str,
    risk: str,
    signals: list[str],
) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "conversation_id": path.stem,
                "label": label,
                "platform": "sms",
                "scenario": "test",
                "emotion": "fear",
                "messages": [
                    {
                        "sender": sender,
                        "text": text,
                        "risk": risk,
                        "signals": signals,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_signal_mapping_requires_textual_evidence():
    noisy = derive_signal_codes(
        "Xin chào, hồ sơ của bạn đã được tiếp nhận.",
        ["otp_phishing", "advance_fee_request", "malicious_link"],
        is_phishing=True,
    )
    assert noisy == frozenset()

    supported = derive_signal_codes(
        "Nhắn tin qua Telegram và cung cấp mã OTP cho tôi.",
        ["relocation_to_telegram", "otp_phishing"],
        is_phishing=True,
    )
    assert supported == frozenset({"chuyen_kenh", "yeu_cau_otp"})


def test_preparation_redacts_deduplicates_and_prevents_split_leakage(
    tmp_path: Path,
):
    phishing = "Công an yêu cầu chuyển 5 triệu vào STK 123456789 ngay."
    _write_conversation(
        tmp_path,
        "01_Scenarios/fear/bank/conversations/scam.json",
        label="scam",
        sender="scammer",
        text=phishing,
        risk="high",
        signals=["authority_impersonation", "advance_fee_request"],
    )
    _write_conversation(
        tmp_path,
        "01_Scenarios/fear/police/conversations/duplicate.json",
        label="scam",
        sender="scammer",
        text=phishing,
        risk="high",
        signals=["authority_impersonation", "advance_fee_request"],
    )
    _write_conversation(
        tmp_path,
        "02_Negative/bank/conversations/legitimate.json",
        label="legitimate",
        sender="service",
        text="Lịch hẹn của bác tại cửa hàng là sáng mai.",
        risk="none",
        signals=[],
    )

    records, manifest = prepare_records(tmp_path)

    assert len(records) == 2
    assert manifest["merged_duplicate_messages"] == 1
    assert manifest["exact_text_leakage_across_splits"] == {
        "train_validation": 0,
        "train_test": 0,
        "validation_test": 0,
    }
    scam = next(record for record in records if record.is_phishing)
    assert "<AMOUNT:trieu>" in scam.text
    assert "<ACCOUNT>" in scam.text
    assert "123456789" not in scam.text
    assert scam.rights_basis == "project_provided"
