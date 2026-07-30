"""Environment-only configuration for the threat-intelligence service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _parse_api_keys(value: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for entry in value.split(","):
        if not entry.strip():
            continue
        key_id, separator, secret = entry.partition("=")
        if not separator or not key_id.strip() or len(secret.strip()) < 16:
            raise ValueError(
                "CHAN_INTEL_API_KEYS entries must be key-id=secret "
                "with secrets of at least 16 characters"
            )
        keys[key_id.strip()] = secret.strip()
    return keys


def _boolean(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


@dataclass(frozen=True)
class IntelConfig:
    database_url: str
    api_keys: dict[str, str]
    user_agent: str
    phishtank_app_key: str | None = None
    openphish_license_confirmed: bool = False
    maximum_feed_bytes: int = 32 * 1024 * 1024
    user_report_threshold: int = 2
    lookup_prefix_length: int = 5

    @classmethod
    def from_environment(cls) -> "IntelConfig":
        app_key = os.environ.get("CHAN_PHISHTANK_APP_KEY", "").strip()
        maximum_feed_bytes = int(
            os.environ.get("CHAN_INTEL_MAXIMUM_FEED_BYTES", str(32 * 1024 * 1024))
        )
        if not 1_000_000 <= maximum_feed_bytes <= 256 * 1024 * 1024:
            raise ValueError(
                "CHAN_INTEL_MAXIMUM_FEED_BYTES must be between 1MB and 256MB"
            )
        threshold = int(os.environ.get("CHAN_USER_REPORT_THRESHOLD", "2"))
        if not 1 <= threshold <= 10:
            raise ValueError("CHAN_USER_REPORT_THRESHOLD must be between 1 and 10")
        prefix_length = int(os.environ.get("CHAN_LOOKUP_PREFIX_LENGTH", "5"))
        if not 2 <= prefix_length <= 5:
            raise ValueError("CHAN_LOOKUP_PREFIX_LENGTH must be between 2 and 5")
        return cls(
            database_url=os.environ.get("CHAN_DATABASE_URL", ""),
            api_keys=_parse_api_keys(os.environ.get("CHAN_INTEL_API_KEYS", "")),
            user_agent=os.environ.get("CHAN_INTEL_USER_AGENT", "").strip(),
            phishtank_app_key=app_key or None,
            openphish_license_confirmed=_boolean(
                "CHAN_OPENPHISH_LICENSE_CONFIRMED"
            ),
            maximum_feed_bytes=maximum_feed_bytes,
            user_report_threshold=threshold,
            lookup_prefix_length=prefix_length,
        )

    def require_feed_user_agent(self) -> str:
        if len(self.user_agent) < 12 or "/" not in self.user_agent:
            raise RuntimeError(
                "CHAN_INTEL_USER_AGENT must identify the project and contact, "
                "for example chan-threat-intel/ops@example.org"
            )
        return self.user_agent


@lru_cache
def get_config() -> IntelConfig:
    return IntelConfig.from_environment()
