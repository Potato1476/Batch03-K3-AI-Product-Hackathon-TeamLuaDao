"""Safe CLI inference: accepts text but never logs or writes it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib

from .model import PhishingSignalModel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify one redacted message.")
    parser.add_argument("--model", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument(
        "--stdin",
        action="store_true",
        help="Read one message from stdin; input is not persisted.",
    )
    parser.add_argument("--similarity-max", type=float, default=0.0)
    parser.add_argument("--similarity-beta", type=float, default=0.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    text = sys.stdin.read() if args.stdin else args.text
    if not text or not text.strip():
        raise ValueError("message text cannot be empty")
    model = joblib.load(args.model)
    if not isinstance(model, PhishingSignalModel):
        raise TypeError("artifact is not a PhishingSignalModel")
    prediction = model.predict(
        text,
        similarity_max=args.similarity_max,
        similarity_beta=args.similarity_beta,
    )
    print(json.dumps(prediction, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
