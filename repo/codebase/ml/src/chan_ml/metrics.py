"""Evaluation metrics that mirror the architecture acceptance thresholds."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

import numpy as np
from sklearn.metrics import precision_recall_fscore_support

from .constants import SIGNAL_CODES
from .model import PhishingSignalModel
from .policy import aggregate_risk
from .schema import DatasetRecord

SCENARIO_RECALL_THRESHOLD = 0.80
SCENARIO_FALSE_POSITIVE_THRESHOLD = 0.15


def evaluate_records(
    model: PhishingSignalModel, records: Sequence[DatasetRecord]
) -> dict[str, object]:
    if not records:
        raise ValueError("evaluation records cannot be empty")
    texts = [record.text for record in records]
    probabilities, scam_probabilities = model.predict_components(texts)
    binary_predictions = probabilities >= 0.5
    binary_truth = np.asarray(
        [
            [float(record.signals.get(code, 0.0)) >= 0.5 for code in SIGNAL_CODES]
            for record in records
        ],
        dtype=bool,
    )
    precision, recall, f1, support = precision_recall_fscore_support(
        binary_truth,
        binary_predictions,
        average=None,
        zero_division=0,
    )
    predicted_risks = [
        aggregate_risk(
            {
                code: float(probabilities[row_index, signal_index])
                for signal_index, code in enumerate(SIGNAL_CODES)
            },
            scam_probability=float(scam_probabilities[row_index]),
            scam_beta=model.config.scam_prior_weight,
        ).risk
        for row_index in range(len(records))
    ]
    true_risks = [record.risk for record in records]
    is_phishing = np.asarray([record.is_phishing for record in records], dtype=bool)
    is_flagged = np.asarray(
        [risk in {"high", "medium"} for risk in predicted_risks], dtype=bool
    )

    phishing_total = int(is_phishing.sum())
    legitimate_total = int((~is_phishing).sum())
    phishing_recall = (
        float((is_flagged & is_phishing).sum() / phishing_total)
        if phishing_total
        else 0.0
    )
    false_positive_rate = (
        float((is_flagged & ~is_phishing).sum() / legitimate_total)
        if legitimate_total
        else 0.0
    )
    risk_accuracy = float(
        np.mean(np.asarray(predicted_risks) == np.asarray(true_risks))
    )

    by_signal = {
        code: {
            "precision": round(float(precision[index]), 6),
            "recall": round(float(recall[index]), 6),
            "f1": round(float(f1[index]), 6),
            "support": int(support[index]),
        }
        for index, code in enumerate(SIGNAL_CODES)
    }
    confusion = Counter(zip(true_risks, predicted_risks))
    by_scenario: dict[str, dict[str, int | float]] = {}
    phishing_scenario_recalls: dict[str, float] = {}
    legitimate_scenario_false_positives: dict[str, float] = {}
    for scenario in sorted({record.scenario for record in records}):
        indexes = [
            index for index, record in enumerate(records) if record.scenario == scenario
        ]
        scenario_phishing = is_phishing[indexes]
        scenario_flagged = is_flagged[indexes]
        phishing_count = int(scenario_phishing.sum())
        legitimate_count = int((~scenario_phishing).sum())
        scenario_metrics: dict[str, int | float] = {
            "records": len(indexes),
            "phishing_records": phishing_count,
            "legitimate_records": legitimate_count,
        }
        if phishing_count:
            scenario_recall = float(
                (scenario_flagged & scenario_phishing).sum() / phishing_count
            )
            scenario_metrics["phishing_recall"] = round(scenario_recall, 6)
            phishing_scenario_recalls[scenario] = scenario_recall
        if legitimate_count:
            scenario_false_positive = float(
                (scenario_flagged & ~scenario_phishing).sum() / legitimate_count
            )
            scenario_metrics["false_positive_rate"] = round(scenario_false_positive, 6)
            legitimate_scenario_false_positives[scenario] = scenario_false_positive
        by_scenario[scenario] = scenario_metrics

    below_scenario_gate = sorted(
        scenario
        for scenario, recall_value in phishing_scenario_recalls.items()
        if recall_value < SCENARIO_RECALL_THRESHOLD
    )
    minimum_scenario_recall = (
        min(phishing_scenario_recalls.values()) if phishing_scenario_recalls else 0.0
    )
    above_false_positive_gate = sorted(
        scenario
        for scenario, false_positive in legitimate_scenario_false_positives.items()
        if false_positive >= SCENARIO_FALSE_POSITIVE_THRESHOLD
    )
    maximum_scenario_false_positive = (
        max(legitimate_scenario_false_positives.values())
        if legitimate_scenario_false_positives
        else 1.0
    )
    scenario_coverage_passed = (
        bool(phishing_scenario_recalls)
        and bool(legitimate_scenario_false_positives)
        and not below_scenario_gate
        and not above_false_positive_gate
    )
    result = {
        "records": len(records),
        "phishing_records": phishing_total,
        "legitimate_records": legitimate_total,
        "phishing_recall": round(phishing_recall, 6),
        "legitimate_false_positive_rate": round(false_positive_rate, 6),
        "risk_accuracy": round(risk_accuracy, 6),
        "acceptance": {
            "recall_at_least_0_90": phishing_recall >= 0.90,
            "false_positive_below_0_15": false_positive_rate < 0.15,
            "every_phishing_scenario_recall_at_least_0_80": (not below_scenario_gate),
            "every_legitimate_scenario_false_positive_below_0_15": (
                not above_false_positive_gate
            ),
            "passed": (
                phishing_recall >= 0.90
                and false_positive_rate < 0.15
                and scenario_coverage_passed
            ),
        },
        "by_signal": by_signal,
        "by_scenario": by_scenario,
        "scenario_coverage": {
            "phishing_scenario_count": len(phishing_scenario_recalls),
            "minimum_phishing_scenario_recall": round(minimum_scenario_recall, 6),
            "threshold": SCENARIO_RECALL_THRESHOLD,
            "below_threshold": below_scenario_gate,
            "maximum_legitimate_scenario_false_positive_rate": round(
                maximum_scenario_false_positive, 6
            ),
            "false_positive_threshold": SCENARIO_FALSE_POSITIVE_THRESHOLD,
            "above_false_positive_threshold": above_false_positive_gate,
            "passed": scenario_coverage_passed,
        },
        "risk_confusion": {
            f"{truth}->{predicted}": count
            for (truth, predicted), count in sorted(confusion.items())
        },
    }

    truncated = [record for record in records if record.truncated]
    if truncated:
        truncated_indexes = [i for i, record in enumerate(records) if record.truncated]
        truncated_phishing = is_phishing[truncated_indexes]
        truncated_flagged = is_flagged[truncated_indexes]
        total = int(truncated_phishing.sum())
        result["truncated"] = {
            "records": len(truncated),
            "phishing_recall": round(
                (
                    float((truncated_flagged & truncated_phishing).sum() / total)
                    if total
                    else 0.0
                ),
                6,
            ),
        }
    return result
