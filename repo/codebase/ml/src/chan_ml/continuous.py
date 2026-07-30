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
    minimum_scenario_recall: float = 0.75
    minimum_scenario_records: int = 3
    minimum_scenario_families: int = 0
    maximum_scenario_false_positive_rate: float = 0.15


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    reasons: tuple[str, ...]


def _metric_float(metrics: Mapping[str, object], key: str, default: float) -> float:
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
        reasons.append(f"golden_set_too_small:{records}<{rules.minimum_golden_records}")
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

    if rules.minimum_scenario_families:
        raw_by_scenario = candidate.get("by_scenario")
        by_scenario = raw_by_scenario if isinstance(raw_by_scenario, Mapping) else {}
        qualifying: dict[str, float] = {}
        qualifying_legitimate: dict[str, float] = {}
        for scenario, raw_metrics in by_scenario.items():
            if not isinstance(raw_metrics, Mapping):
                continue
            phishing_records = _metric_int(raw_metrics, "phishing_records", 0)
            if phishing_records < rules.minimum_scenario_records:
                legitimate_records = _metric_int(raw_metrics, "legitimate_records", 0)
                if legitimate_records >= rules.minimum_scenario_records:
                    qualifying_legitimate[str(scenario)] = _metric_float(
                        raw_metrics, "false_positive_rate", 1.0
                    )
            else:
                qualifying[str(scenario)] = _metric_float(
                    raw_metrics, "phishing_recall", 0.0
                )
        if len(qualifying) < rules.minimum_scenario_families:
            reasons.append(
                "scenario_families_below_gate:"
                f"{len(qualifying)}<{rules.minimum_scenario_families}"
            )
        below_gate = sorted(
            (scenario, recall)
            for scenario, recall in qualifying.items()
            if recall < rules.minimum_scenario_recall
        )
        reasons.extend(
            "scenario_recall_below_gate:"
            f"{scenario}:{recall:.6f}<{rules.minimum_scenario_recall:.6f}"
            for scenario, recall in below_gate
        )
        false_positive_above_gate = sorted(
            (scenario, false_positive_rate)
            for scenario, false_positive_rate in qualifying_legitimate.items()
            if false_positive_rate >= rules.maximum_scenario_false_positive_rate
        )
        reasons.extend(
            "scenario_false_positive_at_or_above_gate:"
            f"{scenario}:{false_positive_rate:.6f}>="
            f"{rules.maximum_scenario_false_positive_rate:.6f}"
            for scenario, false_positive_rate in false_positive_above_gate
        )
    return PromotionDecision(promote=not reasons, reasons=tuple(reasons))
