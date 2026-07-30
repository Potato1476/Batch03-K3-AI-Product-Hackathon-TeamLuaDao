import pytest

from chan_ml.policy import aggregate_risk


def test_policy_only_returns_architecture_risks():
    results = [
        aggregate_risk({}),
        aggregate_risk({"mao_danh_tham_quyen": 1.0, "ap_luc_thoi_gian": 1.0}),
        aggregate_risk({"yeu_cau_otp": 0.9}),
    ]
    assert {result.risk for result in results} <= {"high", "medium", "unknown"}


def test_otp_is_high_override():
    result = aggregate_risk({"yeu_cau_otp": 0.5})
    assert result.risk == "high"
    assert result.score == 0.0


def test_secrecy_is_at_least_medium():
    result = aggregate_risk({"yeu_cau_bi_mat": 0.8})
    assert result.risk == "medium"


def test_weighted_thresholds():
    medium = aggregate_risk(
        {"mao_danh_tham_quyen": 1.0, "ap_luc_thoi_gian": 1.0}
    )
    high = aggregate_risk(
        {
            "mao_danh_tham_quyen": 1.0,
            "yeu_cau_bi_mat": 1.0,
            "ap_luc_thoi_gian": 1.0,
            "tk_ca_nhan": 1.0,
        }
    )
    assert medium.risk == "medium"
    assert high.risk == "high"


def test_unknown_signal_is_rejected():
    with pytest.raises(ValueError, match="unknown signal"):
        aggregate_risk({"safe": 1.0})
