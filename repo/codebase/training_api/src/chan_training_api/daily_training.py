"""One-shot daily trainer with guarded model promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import joblib

from chan_ml.continuous import decide_promotion
from chan_ml.data import read_records
from chan_ml.metrics import evaluate_records
from chan_ml.model import PhishingSignalModel
from chan_ml.schema import DatasetRecord

from .config import AppConfig, get_config
from .repository import (
    ApprovedScenario,
    PostgresTrainingRepository,
    TrainingRepository,
)

LOGGER = logging.getLogger("chan.training")


def _live_record(item: ApprovedScenario) -> DatasetRecord:
    return DatasetRecord(
        id=f"live_{item.id}",
        text=item.redacted_text,
        risk=item.risk,
        signals={code: 1.0 for code in item.signals},
        is_phishing=item.is_phishing,
        scenario=item.origin,
        template_id=f"live:{item.id}",
        source="web",
        input_mode="manual",
        truncated=False,
        split="train",
        synthetic=False,
        consented=item.consented,
        rights_basis=item.rights_basis,
        generator_version="live-db-v1",
    )


def _content_fingerprint(
    approved: list[ApprovedScenario], base_dataset_path: Path
) -> str:
    digest = hashlib.sha256()
    manifest_path = Path(str(base_dataset_path) + ".manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        digest.update(
            str(manifest.get("content_sha256_uncompressed_jsonl", "")).encode("utf-8")
        )
    for item in approved:
        # IDs are enough to version the immutable approved rows without
        # putting content in logs or run metadata.
        digest.update(item.id.encode("utf-8"))
    return digest.hexdigest()


def train_claimed_run(
    repository: TrainingRepository,
    config: AppConfig,
) -> str | None:
    run = repository.claim_training_run()
    if run is None:
        return None
    LOGGER.info("training_run_started run_id=%s", run.id)
    try:
        if not config.base_dataset_path.exists():
            raise FileNotFoundError("base_dataset_missing")
        if not config.golden_dataset_path.exists():
            raise FileNotFoundError("golden_dataset_missing")

        base_records = list(read_records(config.base_dataset_path, split="train"))
        approved = repository.list_approved_scenarios()
        live_records = [_live_record(item) for item in approved]
        weighted_live_records = [
            record for record in live_records for _ in range(config.live_example_repeat)
        ]
        training_records = base_records + weighted_live_records

        golden_records = list(read_records(config.golden_dataset_path, split="test"))
        if not golden_records:
            golden_records = list(read_records(config.golden_dataset_path))

        model = PhishingSignalModel()
        model.fit(
            [record.text for record in training_records],
            [record.signals for record in training_records],
            is_phishing=[record.is_phishing for record in training_records],
            metadata={
                "training_run_id": run.id,
                "base_examples": len(base_records),
                "approved_live_examples": len(live_records),
                "weighted_live_training_rows": len(weighted_live_records),
                "dataset_fingerprint": _content_fingerprint(
                    approved, config.base_dataset_path
                ),
            },
        )
        metrics = evaluate_records(model, golden_records)
        metrics.update(
            {
                "base_training_records": len(base_records),
                "approved_live_training_records": len(live_records),
                "weighted_live_training_rows": len(weighted_live_records),
                "golden_set_frozen": True,
                "evaluated_at": datetime.now(UTC).isoformat(),
            }
        )

        active = repository.get_active_model()
        decision = decide_promotion(
            metrics,
            active=active.metrics if active else None,
            policy=config.promotion_policy,
        )
        candidate_version = (
            "ml-"
            + datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            + "-"
            + run.id.replace("-", "")[:8]
        )
        config.artifact_root.mkdir(parents=True, exist_ok=True)
        artifact_path = config.artifact_root / f"{candidate_version}.joblib"
        joblib.dump(model, artifact_path, compress=3)
        artifact_digest = hashlib.sha256()
        with artifact_path.open("rb") as artifact:
            for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                artifact_digest.update(chunk)
        artifact_hash = artifact_digest.hexdigest()

        repository.complete_training_run(
            run_id=run.id,
            candidate_version=candidate_version,
            artifact_uri=str(artifact_path),
            artifact_sha256=artifact_hash,
            metrics=metrics,
            approved_scenario_count=len(live_records),
            promote=decision.promote,
            reasons=decision.reasons,
        )
        LOGGER.info(
            "training_run_finished run_id=%s promoted=%s live_count=%s",
            run.id,
            decision.promote,
            len(live_records),
        )
        return run.id
    except Exception as error:
        # Store only the exception class. Some library exceptions may contain
        # input values, so their messages must never enter logs or the DB.
        error_code = type(error).__name__
        repository.fail_training_run(run.id, error_code)
        LOGGER.error("training_run_failed run_id=%s error_code=%s", run.id, error_code)
        return run.id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process one CHAN continuous-training run."
    )
    parser.add_argument(
        "--enqueue",
        action="store_true",
        help="Queue today's idempotent daily run before processing.",
    )
    parser.add_argument(
        "--idempotency-key",
        help="Explicit key when enqueueing; defaults to daily-YYYY-MM-DD.",
    )
    parser.add_argument("--retention-days", type=int, default=7)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = get_config()
    repository = PostgresTrainingRepository(config.database_url)
    expired = repository.expire_quarantine(args.retention_days)
    LOGGER.info("quarantine_cleanup expired_count=%s", expired)
    if args.enqueue:
        key = args.idempotency_key or ("daily-" + datetime.now(UTC).date().isoformat())
        repository.queue_training(key, "daily-scheduler")
    run_id = train_claimed_run(repository, config)
    print(json.dumps({"processed_run_id": run_id}))


if __name__ == "__main__":
    main()
