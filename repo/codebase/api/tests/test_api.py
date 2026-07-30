from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from chan_ml.continuous import PromotionPolicy
from chan_training_api.config import AppConfig, get_config
from chan_training_api.main import create_app
from chan_training_api.repository import (
    ScenarioReceiptRecord,
    TrainingRun,
    get_repository,
)


class FakeRepository:
    def __init__(self) -> None:
        self.scenarios = {}
        self.runs = {}

    def submit_scenarios(self, items, actor):
        receipts = []
        for item in items:
            scenario_id = str(uuid4())
            self.scenarios[scenario_id] = {
                "text": item.redacted_text,
                "status": "quarantined",
                "actor": actor,
            }
            receipts.append(
                ScenarioReceiptRecord(
                    id=scenario_id,
                    status="quarantined",
                    duplicate=False,
                )
            )
        return receipts

    def review_scenario(self, scenario_id, decision, reason, actor):
        scenario = self.scenarios.get(scenario_id)
        if (
            not scenario
            or scenario["status"] != "quarantined"
            or scenario["actor"] == actor
        ):
            return None
        scenario["status"] = (
            "approved" if decision == "approve" else "rejected"
        )
        if decision == "reject":
            scenario["text"] = None
        return scenario["status"]

    def queue_training(self, idempotency_key, actor):
        for run in self.runs.values():
            if run["key"] == idempotency_key:
                return run["value"]
        now = datetime.now(UTC)
        run = TrainingRun(
            id=str(uuid4()),
            status="queued",
            submitted_at=now,
            started_at=None,
            finished_at=None,
            approved_scenario_count=None,
            candidate_version=None,
            metrics=None,
            promotion_reasons=(),
            error_code=None,
        )
        self.runs[run.id] = {"key": idempotency_key, "value": run}
        return run

    def get_training_run(self, run_id):
        entry = self.runs.get(run_id)
        return entry["value"] if entry else None

    def get_active_model(self):
        return None


def _client(tmp_path: Path) -> tuple[TestClient, FakeRepository]:
    repository = FakeRepository()
    config = AppConfig(
        database_url="postgresql://unused",
        api_keys={
            "submitter": "this-is-a-long-test-secret",
            "reviewer": "this-is-a-reviewer-test-secret",
        },
        artifact_root=tmp_path / "models",
        base_dataset_path=tmp_path / "base.jsonl.gz",
        golden_dataset_path=tmp_path / "golden.jsonl.gz",
        promotion_policy=PromotionPolicy(),
    )
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_config] = lambda: config
    return TestClient(app), repository


def _headers() -> dict[str, str]:
    return {"X-CHAN-Training-Key": "this-is-a-long-test-secret"}


def _review_headers() -> dict[str, str]:
    return {"X-CHAN-Training-Key": "this-is-a-reviewer-test-secret"}


def _valid_scenario() -> dict[str, object]:
    return {
        "redacted_text": (
            "Công an yêu cầu chuyển <AMOUNT:trieu> vào <ACCOUNT> ngay."
        ),
        "signals": [
            "mao_danh_tham_quyen",
            "ap_luc_thoi_gian",
            "tk_ca_nhan",
        ],
        "risk": "medium",
        "is_phishing": True,
        "origin": "licensed_partner",
        "source_ref": "partner-case-123",
        "rights_basis": "licensed_threat_intel",
        "consented": False,
        "redaction_confirmed": True,
    }


def test_training_endpoints_require_private_key(tmp_path):
    client, _ = _client(tmp_path)
    response = client.post(
        "/internal/v1/training/scenarios",
        json={"items": [_valid_scenario()]},
    )
    assert response.status_code == 401


def test_submit_returns_metadata_only_and_review_can_erase(tmp_path):
    client, repository = _client(tmp_path)
    response = client.post(
        "/internal/v1/training/scenarios",
        headers=_headers(),
        json={"items": [_valid_scenario()]},
    )
    assert response.status_code == 202
    assert "redacted_text" not in response.text
    receipt = response.json()["items"][0]
    assert receipt["status"] == "quarantined"

    review = client.post(
        f"/internal/v1/training/scenarios/{receipt['id']}/review",
        headers=_review_headers(),
        json={"decision": "reject", "review_reason": "incorrect_label"},
    )
    assert review.status_code == 200
    assert repository.scenarios[receipt["id"]]["text"] is None


def test_submitter_cannot_approve_own_scenario(tmp_path):
    client, _ = _client(tmp_path)
    submitted = client.post(
        "/internal/v1/training/scenarios",
        headers=_headers(),
        json={"items": [_valid_scenario()]},
    )
    scenario_id = submitted.json()["items"][0]["id"]
    review = client.post(
        f"/internal/v1/training/scenarios/{scenario_id}/review",
        headers=_headers(),
        json={"decision": "approve", "review_reason": "labels_verified"},
    )
    assert review.status_code == 404


def test_redaction_failure_does_not_echo_raw_content(tmp_path):
    client, _ = _client(tmp_path)
    scenario = _valid_scenario()
    scenario["redacted_text"] = "Gửi mã 938271 cho tôi ngay."
    scenario["signals"] = ["yeu_cau_otp"]
    scenario["risk"] = "high"
    response = client.post(
        "/internal/v1/training/scenarios",
        headers=_headers(),
        json={"items": [scenario]},
    )
    assert response.status_code == 422
    assert "938271" not in response.text
    assert "redacted_text" in response.text


def test_consent_contract_is_enforced(tmp_path):
    client, _ = _client(tmp_path)
    scenario = _valid_scenario()
    scenario["rights_basis"] = "explicit_consent"
    response = client.post(
        "/internal/v1/training/scenarios",
        headers=_headers(),
        json={"items": [scenario]},
    )
    assert response.status_code == 422


def test_retraining_request_is_idempotent(tmp_path):
    client, _ = _client(tmp_path)
    payload = {"idempotency_key": "daily-2026-07-30"}
    first = client.post(
        "/internal/v1/training/retrain", headers=_headers(), json=payload
    )
    second = client.post(
        "/internal/v1/training/retrain", headers=_headers(), json=payload
    )
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
