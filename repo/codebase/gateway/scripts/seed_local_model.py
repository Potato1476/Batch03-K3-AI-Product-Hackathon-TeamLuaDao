"""Train a model and register it as active — LOCAL DEVELOPMENT ONLY.

Why this exists: the gateway loads whatever `model_versions` says is active, and
refuses to serve /v1/analyze without one (503). In production that row is written
by the training plane only after the promotion gates pass — recall ≥ 90%, FP <
15%, no regression (see codebase/api/README.md). This script bypasses those
gates, so it must never run against a production database.

Usage, from the repo/ project root:

    .venv/bin/python codebase/gateway/scripts/seed_local_model.py --size 40000

It writes the artifact under CHAN_MODEL_ARTIFACT_ROOT (default .local/), computes
the SHA-256 the gateway will verify, and inserts a single active row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
import psycopg

from chan_ml.metrics import evaluate_records
from chan_ml.model import ModelConfig, PhishingSignalModel
from chan_ml.synthetic import generate_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed a local active model (development only)."
    )
    parser.add_argument("--size", type=int, default=40_000)
    parser.add_argument("--seed", type=int, default=20260730)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path(os.environ.get("CHAN_MODEL_ARTIFACT_ROOT", ".local/model-registry")),
    )
    parser.add_argument(
        "--database-url", default=os.environ.get("CHAN_DATABASE_URL", "")
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.database_url:
        raise SystemExit("CHAN_DATABASE_URL is required (or pass --database-url)")

    print(f"generating {args.size} synthetic records...")
    records = list(generate_records(args.size, seed=args.seed))
    train = [record for record in records if record.split == "train"]
    validation = [record for record in records if record.split == "validation"]

    print(f"training on {len(train)} records...")
    model = PhishingSignalModel(ModelConfig())
    model.fit(
        [record.text for record in train],
        [record.signals for record in train],
        metadata={"seeded_locally": True},
    )

    print(f"evaluating on {len(validation)} records...")
    metrics = evaluate_records(model, validation)
    print(
        "  recall={recall:.4f} fpr={fpr:.4f} risk_accuracy={accuracy:.4f}".format(
            recall=metrics["phishing_recall"],
            fpr=metrics["legitimate_false_positive_rate"],
            accuracy=metrics["risk_accuracy"],
        )
    )
    acceptance = metrics["acceptance"]
    if not acceptance["passed"]:  # type: ignore[index]
        # Seeded anyway — this script is for a working local demo, not a release.
        print("  WARNING: does not meet the §11.4 acceptance thresholds")

    args.artifact_root.mkdir(parents=True, exist_ok=True)
    version = "ml-local-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    artifact_path = (args.artifact_root / f"{version}.joblib").resolve()
    joblib.dump(model, artifact_path, compress=3)

    digest = hashlib.sha256()
    with artifact_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = digest.hexdigest()

    run_id = str(uuid.uuid4())
    with psycopg.connect(args.database_url) as connection:
        # model_versions.training_run_id is NOT NULL and references training_runs,
        # so a placeholder run row is required even for a local seed.
        connection.execute(
            """
            INSERT INTO training_runs (id, idempotency_key, status, submitted_by,
                                       finished_at, candidate_version, metrics)
            VALUES (%s, %s, 'promoted', 'local-seed', now(), %s, %s)
            """,
            (run_id, f"local-seed-{version}", version, json.dumps(metrics)),
        )
        connection.execute(
            "UPDATE model_versions SET status = 'archived' WHERE status = 'active'"
        )
        connection.execute(
            """
            INSERT INTO model_versions (version, artifact_uri, artifact_sha256,
                                        metrics, status, training_run_id, promoted_at)
            VALUES (%s, %s, %s, %s, 'active', %s, now())
            """,
            (version, str(artifact_path), checksum, json.dumps(metrics), run_id),
        )

    print(f"\nactive model: {version}")
    print(f"artifact:     {artifact_path}")
    print("the gateway will pick it up within CHAN_MODEL_POLL_SECONDS (default 60s)")


if __name__ == "__main__":
    main()
