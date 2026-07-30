"""Environment configuration for the internal Detection service."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

_REPO_BOOTSTRAP_MODEL = (
    Path(__file__).resolve().parents[3]
    / "ml"
    / "artifacts"
    / "chan-signal-model.joblib"
)
_BOOTSTRAP_SHA256 = (
    "44a885db58d96d3b9dcd378504f9b329643fbfbd05518c8b146542fbd07e8445"
)


@dataclass(frozen=True)
class DetectionConfig:
    training_api_url: str
    training_api_key: str
    intel_api_url: str
    detection_api_key: str
    model_poll_seconds: int = 60
    request_timeout_seconds: float = 5.0
    bootstrap_model_path: str = ""
    bootstrap_model_sha256: str = ""
    bootstrap_model_version: str = "chan-signal-20260730"

    @classmethod
    def from_env(cls) -> "DetectionConfig":
        url = os.getenv("CHAN_TRAINING_API_URL", "").strip().rstrip("/")
        key = os.getenv("CHAN_TRAINING_API_KEY", "").strip()
        intel_url = os.getenv("CHAN_INTEL_API_URL", "").strip().rstrip("/")
        detection_key = os.getenv("CHAN_DETECTION_API_KEY", "").strip()
        bootstrap_path = os.getenv(
            "CHAN_BOOTSTRAP_MODEL_PATH",
            str(_REPO_BOOTSTRAP_MODEL) if _REPO_BOOTSTRAP_MODEL.exists() else "",
        ).strip()
        bootstrap_sha256 = os.getenv(
            "CHAN_BOOTSTRAP_MODEL_SHA256",
            _BOOTSTRAP_SHA256 if bootstrap_path else "",
        ).strip()
        if not url:
            raise ValueError("training_api_url_required")
        if not key:
            raise ValueError("training_api_key_required")
        if not intel_url:
            raise ValueError("intel_api_url_required")
        if not detection_key:
            raise ValueError("detection_api_key_required")
        return cls(
            training_api_url=url,
            training_api_key=key,
            intel_api_url=intel_url,
            detection_api_key=detection_key,
            model_poll_seconds=max(
                5, int(os.getenv("CHAN_MODEL_POLL_SECONDS", "60"))
            ),
            request_timeout_seconds=float(
                os.getenv("CHAN_REQUEST_TIMEOUT_SECONDS", "5")
            ),
            bootstrap_model_path=bootstrap_path,
            bootstrap_model_sha256=bootstrap_sha256,
            bootstrap_model_version=os.getenv(
                "CHAN_BOOTSTRAP_MODEL_VERSION",
                "chan-signal-20260730",
            ).strip(),
        )
