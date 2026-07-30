"""Environment-driven configuration for the public /v1 service.

Mirrors the plain-os.environ approach of chan_training_api.config so both
services are configured the same way, with no extra dependency.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_DEFAULT_RULES_DIR = Path("/var/lib/chan/rules")

# Repo-relative fallback so the service runs from a checkout without env vars.
# This file is codebase/gateway/src/chan_api/config.py, so four parents up is
# codebase/, whose sibling of gateway/ is rules/.
_REPO_RULES_DIR = Path(__file__).resolve().parents[3] / "rules"


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _rules_dir() -> Path:
    raw = os.environ.get("CHAN_RULES_DIR", "").strip()
    if raw:
        return Path(raw)
    if (_REPO_RULES_DIR / "bundle.json").exists():
        return _REPO_RULES_DIR
    return _DEFAULT_RULES_DIR


@dataclass(frozen=True)
class AppConfig:
    database_url: str
    rules_dir: Path

    redis_url: str = ""
    cors_origins: tuple[str, ...] = ()

    # Auth
    device_token_ttl_days: int = 90

    # Rate limiting (§7.3 — stop /analyze being used as a free LLM proxy)
    analyze_per_device_per_minute: int = 20
    analyze_per_ip_per_minute: int = 60
    lookup_per_device_per_minute: int = 120
    report_per_device_per_day: int = 30

    # L3
    l3_provider: str = "local"
    similarity_beta: float = 0.0
    similarity_enabled: bool = False
    llm_model: str = "claude-sonnet-5"
    llm_timeout_seconds: float = 8.0
    llm_api_key: str = ""

    # OCR
    ocr_provider: str = "stub"
    ocr_max_bytes: int = 6 * 1024 * 1024

    # Feedback → private training-plane bridge
    training_api_url: str = ""
    training_api_key: str = ""

    # Retention (§7.2)
    analyses_retention_days: int = 90
    access_log_retention_days: int = 30

    model_poll_seconds: int = 60
    request_timeout_seconds: float = 5.0
    forbidden_labels: tuple[str, ...] = field(
        default=("safe", "ok", "clean", "an toàn", "an toan")
    )

    @property
    def bundle_path(self) -> Path:
        return self.rules_dir / "bundle.json"

    @property
    def hotlines_path(self) -> Path:
        return self.rules_dir / "hotlines.json"

    @classmethod
    def from_environment(cls) -> "AppConfig":
        provider = os.environ.get("CHAN_L3_PROVIDER", "local").strip().lower()
        if provider not in {"local", "llm", "ensemble"}:
            raise ValueError("CHAN_L3_PROVIDER must be local, llm or ensemble")
        ocr_provider = os.environ.get("CHAN_OCR_PROVIDER", "stub").strip().lower()
        if ocr_provider not in {"stub", "paddle"}:
            raise ValueError("CHAN_OCR_PROVIDER must be stub or paddle")

        similarity_beta = _env_float("CHAN_SIMILARITY_BETA", 0.0)
        if similarity_beta < 0:
            raise ValueError("CHAN_SIMILARITY_BETA cannot be negative")

        return cls(
            database_url=os.environ.get("CHAN_DATABASE_URL", ""),
            rules_dir=_rules_dir(),
            redis_url=os.environ.get("CHAN_REDIS_URL", ""),
            cors_origins=_env_list("CHAN_CORS_ORIGINS", ()),
            device_token_ttl_days=_env_int("CHAN_DEVICE_TOKEN_TTL_DAYS", 90),
            analyze_per_device_per_minute=_env_int(
                "CHAN_ANALYZE_PER_DEVICE_PER_MINUTE", 20
            ),
            analyze_per_ip_per_minute=_env_int("CHAN_ANALYZE_PER_IP_PER_MINUTE", 60),
            lookup_per_device_per_minute=_env_int(
                "CHAN_LOOKUP_PER_DEVICE_PER_MINUTE", 120
            ),
            report_per_device_per_day=_env_int("CHAN_REPORT_PER_DEVICE_PER_DAY", 30),
            l3_provider=provider,
            similarity_beta=similarity_beta,
            similarity_enabled=_env_bool("CHAN_SIMILARITY_ENABLED", False),
            llm_model=os.environ.get("CHAN_LLM_MODEL", "claude-sonnet-5"),
            llm_timeout_seconds=_env_float("CHAN_LLM_TIMEOUT_SECONDS", 8.0),
            llm_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            ocr_provider=ocr_provider,
            ocr_max_bytes=_env_int("CHAN_OCR_MAX_BYTES", 6 * 1024 * 1024),
            training_api_url=os.environ.get("CHAN_TRAINING_API_URL", ""),
            training_api_key=os.environ.get("CHAN_TRAINING_API_KEY", ""),
            analyses_retention_days=_env_int("CHAN_ANALYSES_RETENTION_DAYS", 90),
            access_log_retention_days=_env_int("CHAN_ACCESS_LOG_RETENTION_DAYS", 30),
            model_poll_seconds=_env_int("CHAN_MODEL_POLL_SECONDS", 60),
            request_timeout_seconds=_env_float("CHAN_REQUEST_TIMEOUT_SECONDS", 5.0),
        )


@lru_cache
def get_config() -> AppConfig:
    return AppConfig.from_environment()
