"""Evaluate the complete L0–L4 product path, including server-verified rules."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import precision_recall_fscore_support

from .constants import SIGNAL_CODES
from .data import read_records
from .local_rules import evaluate_local_rules, load_rule_bundle
from .model import PhishingSignalModel
from .redact import redact_l2
from .schema import DatasetRecord


def _predict_product(
    model: PhishingSignalModel,
    record: DatasetRecord,
    bundle: dict,
) -> dict[str, object]:
    local = evaluate_local_rules(record.text, bundle)
    redaction = redact_l2(record.text)
    if local.otp_blocked or redaction.otp_found:
        return {
            "risk": "high",
            "score": 1.0,
            "signals": [{"code": "yeu_cau_otp", "confidence": 1.0}],
        }
    return model.predict(
        redaction.text,
        signal_boosts=local.signal_boosts,
        verified_local_signals=local.local_signals,
    )


def evaluate_product_records(
    model: PhishingSignalModel,
    records: list[DatasetRecord],
    bundle: dict,
) -> dict[str, object]:
    if not records:
        raise ValueError("evaluation records cannot be empty")
    predictions = [_predict_product(model, record, bundle) for record in records]
    predicted_risks = [str(prediction["risk"]) for prediction in predictions]
    true_risks = [record.risk for record in records]
    truth = np.asarray([record.is_phishing for record in records], dtype=bool)
    flagged = np.asarray(
        [risk in {"medium", "high"} for risk in predicted_risks],
        dtype=bool,
    )
    predicted_signals = np.asarray(
        [
            [
                code
                in {
                    str(item["code"])
                    for item in prediction.get("signals", [])
                }
                for code in SIGNAL_CODES
            ]
            for prediction in predictions
        ],
        dtype=bool,
    )
    true_signals = np.asarray(
        [
            [float(record.signals.get(code, 0.0)) >= 0.5 for code in SIGNAL_CODES]
            for record in records
        ],
        dtype=bool,
    )
    precision, recall, f1, support = precision_recall_fscore_support(
        true_signals,
        predicted_signals,
        average=None,
        zero_division=0,
    )
    phishing_total = max(1, int(truth.sum()))
    legitimate_total = max(1, int((~truth).sum()))
    phishing_recall = float((flagged & truth).sum() / phishing_total)
    false_positive_rate = float((flagged & ~truth).sum() / legitimate_total)
    by_signal = {
        code: {
            "precision": round(float(precision[index]), 6),
            "recall": round(float(recall[index]), 6),
            "f1": round(float(f1[index]), 6),
            "support": int(support[index]),
        }
        for index, code in enumerate(SIGNAL_CODES)
    }
    supported_f1 = [
        float(by_signal[code]["f1"])
        for code in SIGNAL_CODES
        if int(by_signal[code]["support"]) > 0
    ]
    confusion = Counter(zip(true_risks, predicted_risks))
    mismatches = []
    invariant_errors = []
    for record, prediction in zip(records, predictions):
        actual_codes = sorted(
            str(item["code"]) for item in prediction.get("signals", [])
        )
        expected_codes = sorted(record.signals)
        if (
            prediction["risk"] != record.risk
            or actual_codes != expected_codes
        ):
            mismatches.append(
                {
                    "id": record.id,
                    "split": record.split,
                    "expected_risk": record.risk,
                    "actual_risk": prediction["risk"],
                    "expected_signals": expected_codes,
                    "actual_signals": actual_codes,
                }
            )
        if prediction["risk"] == "unknown" and actual_codes:
            invariant_errors.append(
                {"id": record.id, "reason": "unknown_risk_exposes_signals"}
            )
        if "yeu_cau_otp" in actual_codes and prediction["risk"] != "high":
            invariant_errors.append(
                {"id": record.id, "reason": "otp_signal_not_high"}
            )

    return {
        "evaluated_at": datetime.now(UTC).isoformat(),
        "records_checked": len(records),
        "phishing_records": int(truth.sum()),
        "legitimate_records": int((~truth).sum()),
        "phishing_recall": round(phishing_recall, 6),
        "legitimate_false_positive_rate": round(false_positive_rate, 6),
        "risk_accuracy": round(
            float(np.mean(np.asarray(predicted_risks) == np.asarray(true_risks))),
            6,
        ),
        "by_signal": by_signal,
        "supported_signal_macro_f1": round(
            sum(supported_f1) / max(1, len(supported_f1)),
            6,
        ),
        "risk_confusion": {
            f"{expected}->{actual}": count
            for (expected, actual), count in sorted(confusion.items())
        },
        "acceptance": {
            "recall_at_least_0_90": phishing_recall >= 0.90,
            "false_positive_below_0_15": false_positive_rate < 0.15,
            "signal_risk_invariants": not invariant_errors,
            "passed": (
                phishing_recall >= 0.90
                and false_positive_rate < 0.15
                and not invariant_errors
            ),
        },
        "invariant_errors": invariant_errors,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate the full product path with verified L1 rules."
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument(
        "--split",
        choices=("train", "validation", "test"),
        default="test",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    model = joblib.load(args.model)
    if not isinstance(model, PhishingSignalModel):
        raise TypeError("artifact is not a PhishingSignalModel")
    records = list(read_records(args.dataset, split=args.split))
    report = evaluate_product_records(
        model,
        records,
        load_rule_bundle(args.rules),
    )
    report["split"] = args.split
    report["rule_bundle_version"] = load_rule_bundle(args.rules)[
        "bundle_version"
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["acceptance"]["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
