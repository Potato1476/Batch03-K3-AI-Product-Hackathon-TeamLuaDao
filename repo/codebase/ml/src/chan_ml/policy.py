"""Deterministic L4 aggregation policy from CHAN-ARCHITECTURE.md."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .constants import (
    HIGH_THRESHOLD,
    MEDIUM_THRESHOLD,
    SIGNAL_CODES,
    SIGNAL_DECISION_THRESHOLD,
    SIGNAL_WEIGHTS,
)


@dataclass(frozen=True)
class PolicyResult:
    risk: str
    score: float


def aggregate_risk(
    signals: Mapping[str, float],
    *,
    scam_probability: float = 0.0,
    scam_beta: float = 0.0,
    similarity_max: float = 0.0,
    similarity_beta: float = 0.0,
    blocklist_match: bool = False,
    decision_threshold: float = SIGNAL_DECISION_THRESHOLD,
    medium_scam_threshold: float = 0.55,
    high_scam_threshold: float = 0.90,
) -> PolicyResult:
    """Aggregate signal confidences without ever producing a reassuring label."""
    unknown = set(signals) - set(SIGNAL_CODES)
    if unknown:
        raise ValueError(f"unknown signal codes: {sorted(unknown)}")
    if not 0.0 <= similarity_max <= 1.0:
        raise ValueError("similarity_max must be between 0 and 1")
    if not 0.0 <= scam_probability <= 1.0:
        raise ValueError("scam_probability must be between 0 and 1")
    if scam_beta < 0:
        raise ValueError("scam_beta cannot be negative")
    if not 0.0 <= medium_scam_threshold <= high_scam_threshold <= 1.0:
        raise ValueError("invalid scam intent thresholds")
    if similarity_beta < 0:
        raise ValueError("similarity_beta cannot be negative")

    clipped = {
        code: min(1.0, max(0.0, float(signals.get(code, 0.0)))) for code in SIGNAL_CODES
    }
    score = sum(SIGNAL_WEIGHTS[code] * clipped[code] for code in SIGNAL_CODES)
    score += scam_beta * scam_probability
    score += similarity_beta * similarity_max
    score = min(1.0, max(0.0, score))

    dangerous_signal = max(
        clipped["mao_danh_tham_quyen"],
        clipped["ap_luc_thoi_gian"],
        clipped["tk_ca_nhan"],
        clipped["cai_app_ngoai"],
        clipped["loi_ich_bat_thuong"],
    )
    corroborating_dangerous_signals = sum(
        clipped[code] >= decision_threshold
        for code in (
            "mao_danh_tham_quyen",
            "ap_luc_thoi_gian",
            "tk_ca_nhan",
            "cai_app_ngoai",
            "loi_ich_bat_thuong",
        )
    )
    has_high_impact_signal = max(
        clipped["mao_danh_tham_quyen"],
        clipped["tk_ca_nhan"],
        clipped["cai_app_ngoai"],
    ) >= decision_threshold
    if (
        blocklist_match
        or clipped["yeu_cau_otp"] >= decision_threshold
        or score >= HIGH_THRESHOLD
        or (
            has_high_impact_signal
            and corroborating_dangerous_signals >= 2
            and score >= 0.60
        )
        or (
            scam_probability >= high_scam_threshold
            and dangerous_signal >= decision_threshold
        )
        or scam_probability >= 0.985
    ):
        risk = "high"
        score = max(score, HIGH_THRESHOLD)
    elif (
        score >= MEDIUM_THRESHOLD
        or clipped["yeu_cau_bi_mat"] >= decision_threshold
        or scam_probability >= medium_scam_threshold
    ):
        risk = "medium"
        score = max(score, MEDIUM_THRESHOLD)
    else:
        risk = "unknown"
    return PolicyResult(risk=risk, score=round(score, 6))
