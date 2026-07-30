"""Checksum-verified, atomic active-model reload for the detection service."""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import joblib

from chan_ml.model import PhishingSignalModel

from .repository import TrainingRepository


class ActiveModelProvider:
    """Poll registry metadata and atomically swap a validated model in memory."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._version: str | None = None
        self._model: PhishingSignalModel | None = None

    @property
    def version(self) -> str | None:
        with self._lock:
            return self._version

    def refresh(self, repository: TrainingRepository) -> bool:
        metadata = repository.get_active_model()
        if metadata is None or metadata.version == self.version:
            return False
        artifact_path = Path(metadata.artifact_uri)
        digest = hashlib.sha256()
        with artifact_path.open("rb") as artifact:
            for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != metadata.artifact_sha256:
            raise ValueError("active_model_checksum_mismatch")
        candidate = joblib.load(artifact_path)
        if not isinstance(candidate, PhishingSignalModel):
            raise TypeError("active_artifact_has_wrong_model_type")
        with self._lock:
            self._model = candidate
            self._version = metadata.version
        return True

    def predict(self, redacted_text: str) -> dict[str, object]:
        with self._lock:
            model = self._model
        if model is None:
            raise RuntimeError("active_model_not_loaded")
        # Do not add logging here: redacted_text and returned evidence remain
        # ephemeral for a single /v1/analyze request.
        return model.predict(redacted_text)
