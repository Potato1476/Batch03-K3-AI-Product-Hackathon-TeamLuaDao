"""Architecture-owned constants for the L3/L4 model boundary."""

from __future__ import annotations

ENGINE_VERSION = "ml-0.4.0"
GENERATOR_VERSION = "synthetic-1.1.0"

SIGNAL_CODES: tuple[str, ...] = (
    "mao_danh_tham_quyen",
    "yeu_cau_bi_mat",
    "ap_luc_thoi_gian",
    "tk_ca_nhan",
    "cai_app_ngoai",
    "loi_ich_bat_thuong",
    "chuyen_kenh",
    "yeu_cau_otp",
)

SIGNAL_WEIGHTS: dict[str, float] = {
    "mao_danh_tham_quyen": 0.20,
    "yeu_cau_bi_mat": 0.20,
    "ap_luc_thoi_gian": 0.15,
    "tk_ca_nhan": 0.15,
    "cai_app_ngoai": 0.15,
    "loi_ich_bat_thuong": 0.08,
    "chuyen_kenh": 0.07,
    # OTP is a hard override, not part of the weighted sum.
    "yeu_cau_otp": 0.0,
}

RISK_VALUES: tuple[str, ...] = ("high", "medium", "unknown")

HIGH_THRESHOLD = 0.70
MEDIUM_THRESHOLD = 0.35
SIGNAL_DECISION_THRESHOLD = 0.50
