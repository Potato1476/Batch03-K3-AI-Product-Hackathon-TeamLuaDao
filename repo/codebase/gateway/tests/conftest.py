"""Shared fixtures.

The whole suite runs offline: Postgres is replaced by an in-memory fake and the
model is a small real sklearn fit, so nothing here needs infrastructure. Tests
that genuinely need the database constraints are marked `postgres` and skip
unless CHAN_TEST_DATABASE_URL is set.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from chan_api.auth import hash_token
from chan_api.config import AppConfig
from chan_api.deps import (
    get_detection_client,
    get_hotlines,
    get_intel_client,
    get_rate_limiter,
    get_repository,
    get_rule_store,
)
from chan_api.config import get_config
from chan_api.main import create_app
from chan_api.ratelimit import InProcessBackend, RateLimiter
from chan_api.repository import Device
from chan_api.service_clients import ServiceUnavailableError

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


# --------------------------------------------------------------------- fakes --


@dataclass
class FakeRepository:
    """Dict-backed stand-in, mirroring the pattern in codebase/api/tests."""

    devices: dict[bytes, Device] = field(default_factory=dict)
    devices_by_id: dict[str, Device] = field(default_factory=dict)
    blocklists: dict[str, dict[str, dict[str, Any]]] = field(
        default_factory=lambda: {"account": {}, "phone": {}, "url": {}}
    )
    analyses: list[dict[str, Any]] = field(default_factory=list)
    feedback: list[dict[str, Any]] = field(default_factory=list)
    access: list[dict[str, Any]] = field(default_factory=list)
    _sequence: int = 0

    # devices
    def create_device(
        self,
        *,
        platform: str,
        token_hash: bytes,
        ttl_days: int,
        push_token: str | None = None,
        rotated_from: str | None = None,
    ) -> Device:
        self._sequence += 1
        device = Device(
            id=f"dev_test{self._sequence:03d}",
            platform=platform,
            expires_at=datetime.now(timezone.utc) + timedelta(days=ttl_days),
        )
        self.devices[token_hash] = device
        self.devices_by_id[device.id] = device
        if rotated_from:
            for digest, existing in list(self.devices.items()):
                if existing.id == rotated_from:
                    self.devices.pop(digest)
        return device

    def device_for_token(self, token_hash: bytes) -> Device | None:
        return self.devices.get(token_hash)

    def touch_device(self, device_id: str) -> None:
        return None

    # analyses / feedback
    def record_analysis(self, **fields: Any) -> None:
        self.analyses.append(fields)

    def analysis_exists(self, analysis_id: str) -> bool:
        return any(item["id"] == analysis_id for item in self.analyses)

    def record_feedback(
        self, *, analysis_id: str, verdict: str, contributed: bool
    ) -> bool:
        self.feedback.append(
            {
                "analysis_id": analysis_id,
                "verdict": verdict,
                "contributed": contributed,
            }
        )
        return True

    def record_access(self, **fields: Any) -> None:
        self.access.append(fields)

    def hit_rate_limit(self, bucket: str, limit: int, window_seconds: int) -> bool:
        return False

    def purge_expired(self, **kwargs: Any) -> dict[str, int]:
        return {"analyses": 0, "access_log": 0}

    # helpers for tests
    def issue_device(self, token: str, *, platform: str = "web") -> Device:
        return self.create_device(
            platform=platform, token_hash=hash_token(token), ttl_days=90
        )


# ------------------------------------------------------------------ fixtures --


class FakeDetectionClient:
    def __init__(self, intel) -> None:
        self.intel = intel
        self.available = True
        self.sequence = 0

    async def healthy(self) -> bool:
        return self.available

    async def analyze(self, body):
        if not self.available:
            raise ServiceUnavailableError("detection_service_unavailable")
        self.sequence += 1
        text = body["text"]
        from chan_ml.redact import redact_l2

        redaction = redact_l2(text)
        blocklisted = any(
            digest in self.intel.entries[kind]
            for kind, digests in (
                ("account", redaction.account_hashes),
                ("phone", redaction.phone_hashes),
                ("url", redaction.url_hashes),
            )
            for digest in digests
        )
        otp = redaction.otp_found
        unknown = text.startswith("Nha truong")
        signals = [] if unknown else [
            {
                "code": "yeu_cau_otp" if otp else "mao_danh_tham_quyen",
                "confidence": 0.92,
                "evidence": "" if otp else ("can bo thue" if "can bo thue" in text else ""),
            }
        ]
        explanation = (
            "Chưa phát hiện dấu hiệu."
            if unknown
            else (
                "Số nhận tiền này đã bị người khác báo cáo là lừa đảo."
                if blocklisted
                else "Tin nhắn tự nhận là cơ quan có thẩm quyền."
            )
        )
        if body.get("truncated") and not unknown:
            explanation += " Nội dung có thể đã bị cắt ngắn."
        return {
            "analysis_id": f"an_fake{self.sequence:06d}",
            "model_version": "ml-test-0001",
            "engine_version": "ml-test-0001",
            "risk": "unknown" if unknown else "high",
            "score": 0.05 if unknown else (1.0 if blocklisted else 0.82),
            "scam_confidence": 0.03 if unknown else 0.9,
            "signals": signals,
            "explanation": explanation,
            "questions": [] if unknown else ["Tôi có thể gọi số chính thức không?"],
            "actions": [] if unknown else (
                ["report", "share_to_guardian", "lookup_account"]
                if blocklisted
                else ["report", "share_to_guardian"]
            ),
            "verified_hotline": None,
            "rule_bundle_version": body["rule_bundle_version"],
            "truncated": body.get("truncated", False),
            "blocklist_match": blocklisted,
        }


class FakeIntelClient:
    def __init__(self) -> None:
        self.entries = {"account": {}, "phone": {}, "url": {}}
        self.reports = []

    async def lookup(self, kind, prefix):
        now = "2026-07-30T00:00:00+00:00"
        return {
            "prefix": prefix,
            "items": [
                {
                    "suffix": digest[len(prefix):],
                    "report_count": row["count"],
                    "first_seen": now,
                    "last_seen": now,
                    "confidence": "community_reviewed",
                }
                for digest, row in self.entries[kind].items()
                if digest.startswith(prefix)
            ],
        }

    async def report(self, *, kind, digest, device_id):
        self.reports.append((kind, digest, device_id))
        return {
            "accepted": 1,
            "items": [{"id": "report-test", "status": "quarantined", "duplicate": False}],
        }


@pytest.fixture
def config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        database_url="postgresql://unused",
        rules_dir=RULES_DIR,
        redis_url="",
        cors_origins=("https://chan.example",),
        analyze_per_device_per_minute=1_000,
        analyze_per_ip_per_minute=1_000,
        lookup_per_device_per_minute=1_000,
        report_per_device_per_day=30,
        detection_api_url="http://detection.test",
        detection_api_key="test-detection-key",
        intel_api_url="http://intel.test",
        intel_api_key="test-intel-key",
        ocr_provider="stub",
        training_api_url="",
        training_api_key="",
    )


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def intel() -> FakeIntelClient:
    return FakeIntelClient()


@pytest.fixture
def detection(intel: FakeIntelClient) -> FakeDetectionClient:
    return FakeDetectionClient(intel)


@pytest.fixture
def app(
    config: AppConfig,
    repository: FakeRepository,
    detection: FakeDetectionClient,
    intel: FakeIntelClient,
):
    from chan_api.hotlines import HotlineDirectory
    from chan_api.rules import RuleBundleStore

    application = create_app(config, poll_model=False)
    limiter = RateLimiter(InProcessBackend())
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_repository] = lambda: repository
    application.dependency_overrides[get_detection_client] = lambda: detection
    application.dependency_overrides[get_intel_client] = lambda: intel
    application.dependency_overrides[get_rule_store] = lambda: RuleBundleStore(
        config.bundle_path
    )
    application.dependency_overrides[get_hotlines] = lambda: HotlineDirectory(
        config.hotlines_path
    )
    application.dependency_overrides[get_rate_limiter] = lambda: limiter
    return application


@pytest.fixture
def client(app) -> TestClient:  # noqa: ANN001
    return TestClient(app)


@pytest.fixture
def token(repository: FakeRepository) -> str:
    value = "test-device-token-value"
    repository.issue_device(value)
    return value


@pytest.fixture
def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------- text samples in use --

SCAM_TEXT = (
    "Toi la can bo thue, anh chuyen 20 trieu vao 19001234567890 truoc 17h hom nay, "
    "khong noi voi ai ke ca gia dinh."
)
OTP_TEXT = "Doc ma 938271 vua gui de xac minh tai khoan."
LEGITIMATE_TEXT = "Nha truong thong bao hop phu huynh lop 5A vao sang thu 7 tuan nay."


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def requires_postgres() -> bool:
    return bool(os.environ.get("CHAN_TEST_DATABASE_URL"))
