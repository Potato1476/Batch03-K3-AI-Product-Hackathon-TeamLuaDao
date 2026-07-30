"""Environment configuration for the detection service."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

DEFAULT_MODEL_PATH = Path("codebase/ml/artifacts/chan-signal-model.joblib")
DEFAULT_MODEL_SHA256 = (
    "44a885db58d96d3b9dcd378504f9b329643fbfbd05518c8b146542fbd07e8445"
)
DEFAULT_MODEL_VERSION = "chan-signal-20260730"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class DetectionConfig:
    model_path: Path
    model_sha256: str
    model_version: str

    @classmethod
    def from_env(cls) -> "DetectionConfig":
        digest = os.getenv("CHAN_MODEL_SHA256", DEFAULT_MODEL_SHA256).lower()
        if not _SHA256.fullmatch(digest):
            raise ValueError("invalid_model_sha256")
        version = os.getenv("CHAN_MODEL_VERSION", DEFAULT_MODEL_VERSION).strip()
        if not version:
            raise ValueError("invalid_model_version")
        return cls(
            model_path=Path(os.getenv("CHAN_MODEL_PATH", str(DEFAULT_MODEL_PATH))),
            model_sha256=digest,
            model_version=version,
        )
