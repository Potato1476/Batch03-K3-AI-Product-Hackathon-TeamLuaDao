from chan_ml.continuous import PromotionPolicy, decide_promotion


def test_candidate_must_pass_absolute_gates():
    decision = decide_promotion(
        {
            "records": 130,
            "phishing_recall": 0.89,
            "legitimate_false_positive_rate": 0.05,
        }
    )
    assert decision.promote is False
    assert any(reason.startswith("recall_below_gate") for reason in decision.reasons)


def test_candidate_must_not_regress_against_active_model():
    decision = decide_promotion(
        {
            "records": 200,
            "phishing_recall": 0.93,
            "legitimate_false_positive_rate": 0.04,
        },
        active={
            "phishing_recall": 0.98,
            "legitimate_false_positive_rate": 0.01,
        },
    )
    assert decision.promote is False
    assert {reason.split(":", 1)[0] for reason in decision.reasons} == {
        "recall_regression",
        "false_positive_regression",
    }


def test_passing_candidate_is_promoted():
    decision = decide_promotion(
        {
            "records": 200,
            "phishing_recall": 0.96,
            "legitimate_false_positive_rate": 0.02,
        },
        active={
            "phishing_recall": 0.97,
            "legitimate_false_positive_rate": 0.01,
        },
        policy=PromotionPolicy(),
    )
    assert decision.promote is True
    assert decision.reasons == ()


def test_candidate_must_cover_scenario_families_without_hidden_misses():
    decision = decide_promotion(
        {
            "records": 200,
            "phishing_recall": 0.96,
            "legitimate_false_positive_rate": 0.02,
            "by_scenario": {
                "fake_bank_otp": {
                    "phishing_records": 20,
                    "phishing_recall": 0.95,
                },
                "online_kidnapping": {
                    "phishing_records": 20,
                    "phishing_recall": 0.60,
                },
            },
        },
        policy=PromotionPolicy(
            minimum_scenario_families=2,
            minimum_scenario_records=3,
            minimum_scenario_recall=0.75,
        ),
    )
    assert decision.promote is False
    assert any(
        reason.startswith("scenario_recall_below_gate:online_kidnapping")
        for reason in decision.reasons
    )


def test_candidate_rejects_legitimate_scenario_false_positive_spike():
    decision = decide_promotion(
        {
            "records": 200,
            "phishing_recall": 0.96,
            "legitimate_false_positive_rate": 0.02,
            "by_scenario": {
                "fake_bank_otp": {
                    "phishing_records": 20,
                    "legitimate_records": 0,
                    "phishing_recall": 0.95,
                },
                "legitimate_otp_warning": {
                    "phishing_records": 0,
                    "legitimate_records": 20,
                    "false_positive_rate": 0.25,
                },
            },
        },
        policy=PromotionPolicy(
            minimum_scenario_families=1,
            minimum_scenario_records=3,
            maximum_scenario_false_positive_rate=0.15,
        ),
    )
    assert decision.promote is False
    assert any(
        reason.startswith(
            "scenario_false_positive_at_or_above_gate:" "legitimate_otp_warning"
        )
        for reason in decision.reasons
    )
