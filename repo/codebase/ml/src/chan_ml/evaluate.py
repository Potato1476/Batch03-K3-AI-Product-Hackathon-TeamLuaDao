"""Evaluate a trained model without logging or persisting message text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib

from .data import read_records
from .metrics import evaluate_records
from .model import PhishingSignalModel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the CHAN signal model.")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--split", choices=("train", "validation", "test"), default="test"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    model = joblib.load(args.model)
    if not isinstance(model, PhishingSignalModel):
        raise TypeError("artifact is not a PhishingSignalModel")
    records = list(read_records(args.dataset, split=args.split, limit=args.limit))
    metrics = evaluate_records(model, records)
    metrics["split"] = args.split
    metrics["synthetic_only"] = all(record.synthetic for record in records)
    payload = json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
