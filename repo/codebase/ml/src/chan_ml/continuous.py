"""Safety gates for continuously trained candidate models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class PromotionPolicy:
    minimum_phishing_recall: float = 0.90
    maximum_false_positive_rate: float = 0.15
    maximum_recall_regression: float = 0.02
    maximum_false_positive_regression: float = 0.02
    minimum_golden_records: int = 130


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    reasons: tuple[str, ...]


def _metric_float(
    metrics: Mapping[str, object], key: str, default: float
) -> float:
    value = metrics.get(key, default)
    if isinstance(value, (int, float, str)):
        return float(value)
    return default


def _metric_int(metrics: Mapping[str, object], key: str, default: int) -> int:
    value = metrics.get(key, default)
    if isinstance(value, (int, float, str)):
        return int(value)
    return default


def decide_promotion(
    candidate: Mapping[str, object],
    *,
    active: Mapping[str, object] | None = None,
    policy: PromotionPolicy | None = None,
) -> PromotionDecision:
    """Evaluate a candidate using only aggregate metrics, never message text."""
    rules = policy or PromotionPolicy()
    reasons: list[str] = []
    records = _metric_int(candidate, "records", 0)
    recall = _metric_float(candidate, "phishing_recall", 0.0)
    false_positive_rate = _metric_float(
        candidate, "legitimate_false_positive_rate", 1.0
    )

    if records < rules.minimum_golden_records:
        reasons.append(
            f"golden_set_too_small:{records}<{rules.minimum_golden_records}"
        )
    if recall < rules.minimum_phishing_recall:
        reasons.append(
            f"recall_below_gate:{recall:.6f}<{rules.minimum_phishing_recall:.6f}"
        )
    if false_positive_rate >= rules.maximum_false_positive_rate:
        reasons.append(
            "false_positive_at_or_above_gate:"
            f"{false_positive_rate:.6f}>={rules.maximum_false_positive_rate:.6f}"
        )

    if active:
        active_recall = _metric_float(active, "phishing_recall", 0.0)
        active_false_positive_rate = _metric_float(
            active, "legitimate_false_positive_rate", 1.0
        )
        if recall < active_recall - rules.maximum_recall_regression:
            reasons.append(
                "recall_regression:"
                f"{recall:.6f}<{active_recall - rules.maximum_recall_regression:.6f}"
            )
        if (
            false_positive_rate
            > active_false_positive_rate + rules.maximum_false_positive_regression
        ):
            reasons.append(
                "false_positive_regression:"
                f"{false_positive_rate:.6f}>"
                f"{active_false_positive_rate + rules.maximum_false_positive_regression:.6f}"
            )
    return PromotionDecision(promote=not reasons, reasons=tuple(reasons))
