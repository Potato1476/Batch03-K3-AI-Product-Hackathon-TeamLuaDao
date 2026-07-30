from chan_ml.constants import SIGNAL_CODES
from chan_ml.synthetic import ALL_TEMPLATES, generate_records


def test_generation_is_deterministic():
    first = list(generate_records(50, seed=11))
    second = list(generate_records(50, seed=11))
    assert first == second


def test_records_follow_schema_and_privacy_contract():
    records = list(generate_records(500, seed=12))
    for record in records:
        record.validate()
        assert record.risk in {"high", "medium", "unknown"}
        assert set(record.signals) <= set(SIGNAL_CODES)
        assert record.synthetic is True
        assert record.consented is False
        assert record.rights_basis == "synthetic"
        assert "@" not in record.text
    assert any(record.is_phishing for record in records)
    assert any(not record.is_phishing for record in records)
    assert any(record.truncated for record in records)


def test_template_text_is_held_out_by_split():
    template_ids_by_split = {
        split: {template.id for template in ALL_TEMPLATES if template.split == split}
        for split in ("train", "validation", "test")
    }
    assert template_ids_by_split["train"].isdisjoint(
        template_ids_by_split["validation"]
    )
    assert template_ids_by_split["train"].isdisjoint(template_ids_by_split["test"])
    assert template_ids_by_split["validation"].isdisjoint(
        template_ids_by_split["test"]
    )


def test_hard_negative_otp_warning_has_no_otp_request_label():
    records = list(generate_records(2_000, seed=13))
    hard_negatives = [
        record
        for record in records
        if record.scenario == "legitimate_otp_warning"
    ]
    assert hard_negatives
    assert all("yeu_cau_otp" not in record.signals for record in hard_negatives)
    assert all(record.risk == "unknown" for record in hard_negatives)
