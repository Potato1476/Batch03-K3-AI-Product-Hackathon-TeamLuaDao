from chan_ml.metrics import evaluate_records
from chan_ml.model import ModelConfig, PhishingSignalModel
from chan_ml.synthetic import generate_records


def test_small_end_to_end_training_run():
    records = list(generate_records(4_000, seed=99))
    train = [record for record in records if record.split == "train"]
    test = [record for record in records if record.split == "test"]
    model = PhishingSignalModel(
        ModelConfig(
            word_features=8_000,
            char_features=12_000,
            min_df=1,
            max_iter=250,
        )
    )
    model.fit(
        [record.text for record in train],
        [record.signals for record in train],
    )
    metrics = evaluate_records(model, test)
    # This is a tiny smoke fit; architecture gates are measured on the full run.
    assert metrics["phishing_recall"] >= 0.75
    assert metrics["legitimate_false_positive_rate"] < 0.25

    result = model.predict(
        "Công an yêu cầu giữ bí mật, chuyển <AMOUNT:trieu> vào <ACCOUNT> ngay."
    )
    assert result["risk"] in {"high", "medium"}
    assert result["engine_version"]
