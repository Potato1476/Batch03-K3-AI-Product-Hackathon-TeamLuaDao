"""Checksum-verified model loading and inference."""

from __future__ import annotations

import hashlib
from pathlib import Path
from threading import RLock
from typing import cast, TypedDict

import joblib

from chan_ml.model import PhishingSignalModel

from .config import DetectionConfig


class ModelSignal(TypedDict):
    code: str
    confidence: float
    evidence: str


class ModelPrediction(TypedDict):
    risk: str
    score: float
    scam_confidence: float
    signals: list[ModelSignal]
    explanation: str
    questions: list[str]
    engine_version: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ModelRuntime:
    """Keep one validated artifact in memory for all inference requests."""

    def __init__(
        self,
        model: PhishingSignalModel,
        *,
        model_version: str,
    ) -> None:
        self._model = model
        self._model_version = model_version
        self._lock = RLock()

    @property
    def model_version(self) -> str:
        return self._model_version

    @classmethod
    def load(cls, config: DetectionConfig) -> "ModelRuntime":
        if file_sha256(config.model_path) != config.model_sha256:
            raise ValueError("model_checksum_mismatch")
        candidate = joblib.load(config.model_path)
        if not isinstance(candidate, PhishingSignalModel):
            raise TypeError("unsupported_model_artifact")
        return cls(candidate, model_version=config.model_version)

    def predict(self, redacted_text: str) -> ModelPrediction:
        # Scikit-learn inference is read-only, but the lock also protects us
        # from future runtime swaps. Never log or persist redacted_text here.
        with self._lock:
            return cast(ModelPrediction, self._model.predict(redacted_text))
