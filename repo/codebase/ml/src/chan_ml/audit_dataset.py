"""Audit every prepared record before a model is allowed to train."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from .constants import SIGNAL_CODES
from .data import read_records
from .normalize import normalize_for_model
from .team_dataset import _split_family_key, textual_signal_evidence


def audit_dataset(path: Path) -> dict[str, object]:
    records = list(read_records(path))
    if not records:
        raise ValueError("dataset is empty")

    canonical_owners: dict[str, set[str]] = {}
    family_owners: dict[str, set[str]] = {}
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    signal_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    phishing_without_signals: Counter[str] = Counter()

    for record in records:
        canonical = normalize_for_model(record.text)
        canonical_owners.setdefault(canonical, set()).add(record.split)
        family_owners.setdefault(_split_family_key(canonical), set()).add(
            record.split
        )
        risk_counts[record.risk] += 1
        split_counts[record.split] += 1
        signal_counts.update(record.signals)

        if not record.is_phishing and record.risk != "unknown":
            errors.append(
                {"id": record.id, "reason": "legitimate_risk_must_be_unknown"}
            )
        if not record.is_phishing and record.signals:
            errors.append(
                {"id": record.id, "reason": "legitimate_has_phishing_signal"}
            )
        if record.is_phishing and record.risk == "unknown":
            errors.append(
                {"id": record.id, "reason": "phishing_risk_cannot_be_unknown"}
            )
        if "yeu_cau_otp" in record.signals and record.risk != "high":
            errors.append({"id": record.id, "reason": "otp_request_must_be_high"})

        evidence = textual_signal_evidence(record.text)
        unsupported = set(record.signals) - evidence
        for code in sorted(unsupported):
            errors.append(
                {
                    "id": record.id,
                    "reason": f"signal_without_text_evidence:{code}",
                }
            )
        if record.is_phishing and not record.signals:
            phishing_without_signals[record.risk] += 1

    exact_cross_split = sum(
        1 for owners in canonical_owners.values() if len(owners) > 1
    )
    family_cross_split = sum(
        1 for owners in family_owners.values() if len(owners) > 1
    )
    if exact_cross_split:
        errors.append(
            {"id": "*", "reason": f"exact_text_cross_split:{exact_cross_split}"}
        )
    if family_cross_split:
        errors.append(
            {
                "id": "*",
                "reason": f"variable_family_cross_split:{family_cross_split}",
            }
        )
    if phishing_without_signals:
        warnings.append(
            {
                "id": "*",
                "reason": (
                    "phishing_without_eight_signal_labels:"
                    + ",".join(
                        f"{risk}={count}"
                        for risk, count in sorted(
                            phishing_without_signals.items()
                        )
                    )
                ),
            }
        )

    near_duplicate = _near_duplicate_audit(records)
    if near_duplicate["maximum_similarity"] >= 0.98:
        errors.append(
            {
                "id": "*",
                "reason": (
                    "near_duplicate_similarity_at_least_0.98:"
                    f"{near_duplicate['maximum_similarity']}"
                ),
            }
        )

    missing_signals = [code for code in SIGNAL_CODES if signal_counts[code] == 0]
    if missing_signals:
        errors.append(
            {
                "id": "*",
                "reason": f"missing_positive_signals:{','.join(missing_signals)}",
            }
        )

    return {
        "audited_at": datetime.now(UTC).isoformat(),
        "dataset": path.name,
        "records_checked": len(records),
        "split_counts": dict(sorted(split_counts.items())),
        "risk_counts": dict(sorted(risk_counts.items())),
        "signal_counts": {
            code: signal_counts[code] for code in SIGNAL_CODES
        },
        "exact_text_cross_split": exact_cross_split,
        "variable_family_cross_split": family_cross_split,
        "near_duplicate_audit": near_duplicate,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }


def _near_duplicate_audit(records: list) -> dict[str, object]:
    train = [record for record in records if record.split == "train"]
    heldout = [record for record in records if record.split != "train"]
    if not train or not heldout:
        return {
            "heldout_records": len(heldout),
            "maximum_similarity": 0.0,
            "at_least_0_90": 0,
            "at_least_0_95": 0,
            "at_least_0_98": 0,
        }
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        preprocessor=normalize_for_model,
    )
    matrix = vectorizer.fit_transform(
        [record.text for record in [*train, *heldout]]
    )
    similarities = linear_kernel(
        matrix[len(train) :],
        matrix[: len(train)],
    )
    maxima = np.asarray(similarities.max(axis=1), dtype=float)
    return {
        "heldout_records": len(heldout),
        "maximum_similarity": round(float(maxima.max()), 6),
        "at_least_0_90": int((maxima >= 0.90).sum()),
        "at_least_0_95": int((maxima >= 0.95).sum()),
        "at_least_0_98": int((maxima >= 0.98).sum()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit labels, signal evidence, splits, and leakage."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = audit_dataset(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
