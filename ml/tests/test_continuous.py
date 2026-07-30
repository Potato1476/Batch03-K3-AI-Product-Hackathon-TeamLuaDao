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
