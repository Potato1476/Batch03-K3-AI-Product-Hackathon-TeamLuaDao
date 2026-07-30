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


def evaluate_records(
    model: PhishingSignalModel, records: Sequence[DatasetRecord]
) -> dict[str, object]:
    if not records:
        raise ValueError("evaluation records cannot be empty")
    texts = [record.text for record in records]
    probabilities = model.predict_probabilities(texts)
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
            }
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
            "passed": phishing_recall >= 0.90 and false_positive_rate < 0.15,
        },
        "by_signal": by_signal,
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
                float((truncated_flagged & truncated_phishing).sum() / total)
                if total
                else 0.0,
                6,
            ),
        }
    return result
