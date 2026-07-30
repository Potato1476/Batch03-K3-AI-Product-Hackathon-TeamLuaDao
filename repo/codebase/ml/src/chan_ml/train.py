"""Train and persist the CHẮN multi-label signal model."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib

from .data import read_records
from .metrics import evaluate_records
from .model import ModelConfig, PhishingSignalModel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the CHAN signal classifier.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/chan-signal-model.joblib")
    )
    parser.add_argument(
        "--metrics-output", type=Path, default=Path("artifacts/validation-metrics.json")
    )
    parser.add_argument("--word-features", type=int, default=40_000)
    parser.add_argument("--char-features", type=int, default=80_000)
    parser.add_argument("--min-df", type=int, default=2)
    parser.add_argument("--c", type=float, default=4.0)
    parser.add_argument("--max-iter", type=int, default=500)
    parser.add_argument("--probability-temperature", type=float, default=0.35)
    parser.add_argument("--scam-prior-weight", type=float, default=0.405)
    parser.add_argument("--scam-word-features", type=int, default=60_000)
    parser.add_argument("--scam-c", type=float, default=1.0)
    parser.add_argument("--limit", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manifest_path = Path(str(args.dataset) + ".manifest.json")
    dataset_manifest: dict[str, object] = {}
    if manifest_path.exists():
        dataset_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    train_records = list(read_records(args.dataset, split="train", limit=args.limit))
    validation_limit = None if args.limit is None else max(100, args.limit // 8)
    validation_records = list(
        read_records(args.dataset, split="validation", limit=validation_limit)
    )
    config = ModelConfig(
        word_features=args.word_features,
        char_features=args.char_features,
        min_df=args.min_df,
        regularization_c=args.c,
        max_iter=args.max_iter,
        probability_temperature=args.probability_temperature,
        scam_prior_weight=args.scam_prior_weight,
        scam_word_features=args.scam_word_features,
        scam_regularization_c=args.scam_c,
    )
    model = PhishingSignalModel(config)
    model.fit(
        [record.text for record in train_records],
        [record.signals for record in train_records],
        is_phishing=[record.is_phishing for record in train_records],
        metadata={
            "trained_at": datetime.now(UTC).isoformat(),
            "dataset": args.dataset.name,
            "train_split_examples": len(train_records),
            "dataset_generator_version": dataset_manifest.get("generator_version"),
            "dataset_content_sha256": dataset_manifest.get(
                "content_sha256_uncompressed_jsonl"
            ),
        },
    )
    metrics = evaluate_records(model, validation_records)
    metrics["split"] = "validation"
    metrics["synthetic_only"] = all(record.synthetic for record in validation_records)
    metrics["model_config"] = {
        "word_features": config.word_features,
        "char_features": config.char_features,
        "min_df": config.min_df,
        "regularization_c": config.regularization_c,
        "probability_temperature": config.probability_temperature,
        "scam_prior_weight": config.scam_prior_weight,
        "scam_word_features": config.scam_word_features,
        "scam_regularization_c": config.scam_regularization_c,
    }
    metrics["dataset_generator_version"] = dataset_manifest.get("generator_version")
    metrics["dataset_content_sha256"] = dataset_manifest.get(
        "content_sha256_uncompressed_jsonl"
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.output, compress=3)
    args.metrics_output.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "model": str(args.output),
                "metrics": str(args.metrics_output),
                "training_examples": len(train_records),
                "validation": metrics,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
