from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from chan_ml.continuous import PromotionPolicy
from chan_ml.synthetic import generate_records, write_dataset
from chan_training_api.active_model import ActiveModelProvider
from chan_training_api.config import AppConfig
from chan_training_api.daily_training import train_claimed_run
from chan_training_api.repository import ActiveModel, ApprovedScenario, TrainingRun


class WorkerRepository:
    def __init__(self) -> None:
        self.run = TrainingRun(
            id=str(uuid4()),
            status="running",
            submitted_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            finished_at=None,
            approved_scenario_count=None,
            candidate_version=None,
            metrics=None,
            promotion_reasons=(),
            error_code=None,
        )
        self.claimed = False
        self.completed = None
        self.failed = None

    def claim_training_run(self):
        if self.claimed:
            return None
        self.claimed = True
        return self.run

    def list_approved_scenarios(self):
        return [
            ApprovedScenario(
                id=str(uuid4()),
                redacted_text=(
                    "Cơ quan thuế yêu cầu giữ bí mật và chuyển "
                    "<AMOUNT:trieu> vào <ACCOUNT> ngay."
                ),
                signals=(
                    "mao_danh_tham_quyen",
                    "yeu_cau_bi_mat",
                    "ap_luc_thoi_gian",
                    "tk_ca_nhan",
                ),
                risk="high",
                is_phishing=True,
                origin="licensed_partner",
                rights_basis="licensed_threat_intel",
                consented=False,
            )
        ]

    def get_active_model(self):
        if self.completed and self.completed["promote"]:
            return ActiveModel(
                version=self.completed["candidate_version"],
                artifact_uri=self.completed["artifact_uri"],
                artifact_sha256=self.completed["artifact_sha256"],
                metrics=self.completed["metrics"],
                promoted_at=datetime.now(UTC),
            )
        return None

    def complete_training_run(self, **kwargs):
        self.completed = kwargs

    def fail_training_run(self, run_id, error_code):
        self.failed = (run_id, error_code)


def _dataset(path: Path) -> None:
    records = generate_records(3_000, seed=71)
    write_dataset(
        records,
        path,
        seed=71,
        requested_size=3_000,
        phishing_ratio=0.55,
    )


def test_daily_worker_builds_and_registers_candidate(tmp_path):
    dataset = tmp_path / "base.jsonl.gz"
    _dataset(dataset)
    config = AppConfig(
        database_url="postgresql://unused",
        api_keys={},
        artifact_root=tmp_path / "models",
        base_dataset_path=dataset,
        golden_dataset_path=dataset,
        promotion_policy=PromotionPolicy(
            minimum_phishing_recall=0.40,
            maximum_false_positive_rate=0.60,
            maximum_recall_regression=1.0,
            maximum_false_positive_regression=1.0,
            minimum_golden_records=50,
        ),
    )
    repository = WorkerRepository()

    processed = train_claimed_run(repository, config)

    assert processed == repository.run.id
    assert repository.failed is None
    assert repository.completed is not None
    assert repository.completed["approved_scenario_count"] == 1
    assert repository.completed["promote"] is True
    artifact = Path(repository.completed["artifact_uri"])
    assert artifact.exists()
    assert len(repository.completed["artifact_sha256"]) == 64

    provider = ActiveModelProvider()
    assert provider.refresh(repository) is True
    assert provider.version == repository.completed["candidate_version"]
    prediction = provider.predict(
        "Cơ quan thuế yêu cầu giữ bí mật và chuyển "
        "<AMOUNT:trieu> vào <ACCOUNT> ngay."
    )
    assert prediction["risk"] in {"high", "medium"}
