from pathlib import Path

from chan_ml.evaluate_product import evaluate_product_records
from chan_ml.local_rules import load_rule_bundle
from chan_ml.model import ModelConfig, PhishingSignalModel
from chan_ml.synthetic import generate_records


RULES = Path(__file__).resolve().parents[2] / "rules" / "bundle.json"


def test_product_evaluation_checks_signal_risk_invariants():
    records = list(generate_records(1_000, seed=887))
    train = [record for record in records if record.split == "train"]
    test = [record for record in records if record.split == "test"]
    model = PhishingSignalModel(
        ModelConfig(
            word_features=4_000,
            char_features=6_000,
            scam_word_features=4_000,
            scam_char_features=6_000,
            min_df=1,
            max_iter=200,
        )
    )
    model.fit(
        [record.text for record in train],
        [record.signals for record in train],
        is_phishing=[record.is_phishing for record in train],
    )

    report = evaluate_product_records(
        model,
        test,
        load_rule_bundle(RULES),
    )

    assert report["records_checked"] == len(test)
    assert report["acceptance"]["signal_risk_invariants"] is True
