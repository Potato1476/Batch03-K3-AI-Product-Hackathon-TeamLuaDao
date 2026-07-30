from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from chan_intel.config import IntelConfig, get_config
from chan_intel.main import create_app
from chan_intel.models import (
    LookupRecord,
    ReportReceiptRecord,
    SourceStatusRecord,
)
from chan_intel.repository import get_repository


class FakeRepository:
    def __init__(self) -> None:
        self.reports = {}
        self.approved_by_hash: dict[tuple[str, str], set[str]] = {}

    def lookup(self, kind, prefix):
        assert kind == "url"
        assert prefix == "ab"
        return [
            LookupRecord(
                digest_hex="ab" + "1" * 62,
                report_count=2,
                first_seen=datetime(2026, 7, 1, tzinfo=UTC),
                last_seen=datetime(2026, 7, 30, tzinfo=UTC),
                confidence="verified",
            )
        ]

    def submit_reports(self, items, actor):
        receipts = []
        for item in items:
            key = (item.kind, item.indicator_hash, item.reporter_hash)
            existing = next(
                (
                    report_id
                    for report_id, report in self.reports.items()
                    if report["key"] == key
                ),
                None,
            )
            if existing:
                receipts.append(
                    ReportReceiptRecord(
                        id=existing,
                        status=self.reports[existing]["status"],
                        duplicate=True,
                    )
                )
                continue
            report_id = str(uuid4())
            self.reports[report_id] = {
                "key": key,
                "status": "quarantined",
                "actor": actor,
            }
            receipts.append(
                ReportReceiptRecord(
                    id=report_id,
                    status="quarantined",
                    duplicate=False,
                )
            )
        return receipts

    def review_report(
        self, report_id, decision, reason, actor, consensus_threshold
    ):
        report = self.reports.get(report_id)
        if (
            report is None
            or report["status"] != "quarantined"
            or report["actor"] == actor
        ):
            return None
        report["status"] = "approved" if decision == "approve" else "rejected"
        if decision == "reject":
            return "rejected", 0, False
        kind, digest, reporter = report["key"]
        reporters = self.approved_by_hash.setdefault((kind, digest), set())
        reporters.add(reporter)
        count = len(reporters)
        return "approved", count, count >= consensus_threshold

    def list_sources(self):
        return [
            SourceStatusRecord(
                name="phishtank",
                enabled=True,
                rights_basis="commercial_api_terms",
                update_interval_minutes=60,
                last_success_at=None,
                last_record_count=0,
                last_error_code=None,
            )
        ]


def _client(tmp_path: Path) -> tuple[TestClient, FakeRepository]:
    repository = FakeRepository()
    config = IntelConfig(
        database_url="postgresql://unused",
        api_keys={
            "reporter": "this-is-a-long-report-secret",
            "reviewer": "this-is-a-long-review-secret",
        },
        user_agent="chan-tests/test@example.org",
        user_report_threshold=2,
        lookup_prefix_length=2,
    )
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_config] = lambda: config
    return TestClient(app), repository


def _headers() -> dict[str, str]:
    return {"X-CHAN-Intel-Key": "this-is-a-long-report-secret"}


def _review_headers() -> dict[str, str]:
    return {"X-CHAN-Intel-Key": "this-is-a-long-review-secret"}


def _report(reporter_hash: str = "b" * 64) -> dict[str, object]:
    return {
        "kind": "phone",
        "indicator_hash": "a" * 64,
        "reporter_hash": reporter_hash,
        "evidence_hash": "c" * 64,
        "consented": True,
    }


def test_lookup_returns_suffixes_not_full_hashes(tmp_path):
    client, _ = _client(tmp_path)
    response = client.get("/v1/lookup/url?prefix=ab")
    assert response.status_code == 200
    body = response.json()
    assert body["prefix"] == "ab"
    assert body["items"][0]["suffix"] == "1" * 62
    assert "digest_hex" not in response.text


def test_internal_routes_require_authentication(tmp_path):
    client, _ = _client(tmp_path)
    response = client.post(
        "/internal/v1/intel/reports", json={"items": [_report()]}
    )
    assert response.status_code == 401


def test_independent_reports_are_quarantined_and_need_consensus(tmp_path):
    client, _ = _client(tmp_path)
    first = client.post(
        "/internal/v1/intel/reports",
        headers=_headers(),
        json={"items": [_report("b" * 64)]},
    )
    first_id = first.json()["items"][0]["id"]
    first_review = client.post(
        f"/internal/v1/intel/reports/{first_id}/review",
        headers=_review_headers(),
        json={"decision": "approve", "review_reason": "evidence_verified"},
    )
    assert first_review.json()["activated"] is False
    assert first_review.json()["independent_approved_reports"] == 1

    second = client.post(
        "/internal/v1/intel/reports",
        headers=_headers(),
        json={"items": [_report("d" * 64)]},
    )
    second_id = second.json()["items"][0]["id"]
    second_review = client.post(
        f"/internal/v1/intel/reports/{second_id}/review",
        headers=_review_headers(),
        json={"decision": "approve", "review_reason": "evidence_verified"},
    )
    assert second_review.json()["activated"] is True
    assert second_review.json()["independent_approved_reports"] == 2


def test_submitter_cannot_review_own_report(tmp_path):
    client, _ = _client(tmp_path)
    submitted = client.post(
        "/internal/v1/intel/reports",
        headers=_headers(),
        json={"items": [_report()]},
    )
    report_id = submitted.json()["items"][0]["id"]
    reviewed = client.post(
        f"/internal/v1/intel/reports/{report_id}/review",
        headers=_headers(),
        json={"decision": "approve", "review_reason": "evidence_verified"},
    )
    assert reviewed.status_code == 404


def test_hash_validation_does_not_echo_invalid_value(tmp_path):
    client, _ = _client(tmp_path)
    payload = _report()
    payload["indicator_hash"] = "RAW-PHONE-0900000000"
    response = client.post(
        "/internal/v1/intel/reports",
        headers=_headers(),
        json={"items": [payload]},
    )
    assert response.status_code == 422
    assert "0900000000" not in response.text
