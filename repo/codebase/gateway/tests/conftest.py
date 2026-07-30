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
from typing import Any, Sequence

import pytest
from fastapi.testclient import TestClient

from chan_ml.model import ModelConfig, PhishingSignalModel
from chan_ml.synthetic import generate_records

from chan_api.auth import hash_token
from chan_api.config import AppConfig
from chan_api.deps import (
    get_hotlines,
    get_model_registry,
    get_rate_limiter,
    get_repository,
    get_rule_store,
)
from chan_api.config import get_config
from chan_api.main import create_app
from chan_api.model_registry import ModelRegistry
from chan_api.ratelimit import InProcessBackend, RateLimiter
from chan_api.repository import ActiveModel, BlocklistEntry, Device, SimilarScenario

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
    active_model: ActiveModel | None = None
    scenarios: list[SimilarScenario] = field(default_factory=list)
    reports_today: int = 0
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

    # blocklist
    def blocklist_cluster(self, kind: str, prefix: str) -> list[BlocklistEntry]:
        now = datetime.now(timezone.utc)
        return [
            BlocklistEntry(
                hash=digest,
                report_cnt=int(row["report_cnt"]),
                first_seen=now,
                last_seen=now,
                origin=str(row["origin"]),
            )
            for digest, row in sorted(self.blocklists[kind].items())
            if digest.startswith(prefix)
        ]

    def blocklist_contains(self, kind: str, digests: Sequence[str]) -> bool:
        return any(digest in self.blocklists[kind] for digest in digests)

    def report_identifier(self, kind: str, digest: str, origin: str) -> int:
        row = self.blocklists[kind].setdefault(
            digest, {"report_cnt": 0, "origin": origin}
        )
        row["report_cnt"] = int(row["report_cnt"]) + 1
        return int(row["report_cnt"])

    def count_reports_today(self, device_id: str) -> int:
        return self.reports_today

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

    # model registry / similarity
    def get_active_model(self) -> ActiveModel | None:
        return self.active_model

    def similar_scenarios(
        self, embedding: Sequence[float], *, limit: int = 5
    ) -> list[SimilarScenario]:
        return self.scenarios[:limit]

    def hit_rate_limit(self, bucket: str, limit: int, window_seconds: int) -> bool:
        return False

    def purge_expired(self, **kwargs: Any) -> dict[str, int]:
        return {"analyses": 0, "access_log": 0}

    # helpers for tests
    def add_blocklist(self, kind: str, digest: str, *, count: int = 3) -> None:
        self.blocklists[kind][digest] = {"report_cnt": count, "origin": "user_report"}

    def issue_device(self, token: str, *, platform: str = "web") -> Device:
        return self.create_device(
            platform=platform, token_hash=hash_token(token), ttl_days=90
        )


# ------------------------------------------------------------------ fixtures --


@pytest.fixture(scope="session")
def trained_model() -> PhishingSignalModel:
    """A small but real model, so signal scores are genuine, not stubbed."""
    records = list(generate_records(4_000, seed=4242))
    train = [record for record in records if record.split == "train"]
    model = PhishingSignalModel(
        ModelConfig(word_features=8_000, char_features=12_000, min_df=1, max_iter=250)
    )
    model.fit(
        [record.text for record in train],
        [record.signals for record in train],
    )
    return model


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
        l3_provider="local",
        similarity_beta=0.0,
        similarity_enabled=False,
        ocr_provider="stub",
        training_api_url="",
        training_api_key="",
    )


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def registry(trained_model: PhishingSignalModel) -> ModelRegistry:
    provider = ModelRegistry()
    provider.install(trained_model, "ml-test-0001")
    return provider


@pytest.fixture
def app(config: AppConfig, repository: FakeRepository, registry: ModelRegistry):
    from chan_api.hotlines import HotlineDirectory
    from chan_api.rules import RuleBundleStore

    application = create_app(config, poll_model=False)
    limiter = RateLimiter(InProcessBackend())
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_repository] = lambda: repository
    application.dependency_overrides[get_model_registry] = lambda: registry
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
