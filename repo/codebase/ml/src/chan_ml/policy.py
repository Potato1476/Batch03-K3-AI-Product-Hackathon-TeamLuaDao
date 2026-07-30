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
    if similarity_beta < 0:
        raise ValueError("similarity_beta cannot be negative")

    clipped = {
        code: min(1.0, max(0.0, float(signals.get(code, 0.0)))) for code in SIGNAL_CODES
    }
    score = sum(SIGNAL_WEIGHTS[code] * clipped[code] for code in SIGNAL_CODES)
    score += scam_beta * scam_probability
    score += similarity_beta * similarity_max
    score = min(1.0, max(0.0, score))

    if (
        blocklist_match
        or clipped["yeu_cau_otp"] >= decision_threshold
        or score >= HIGH_THRESHOLD
    ):
        risk = "high"
    elif score >= MEDIUM_THRESHOLD or clipped["yeu_cau_bi_mat"] >= decision_threshold:
        risk = "medium"
    else:
        risk = "unknown"
    return PolicyResult(risk=risk, score=round(score, 6))
