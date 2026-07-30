"""Read-only, checksum-verified access to the active model artifact.

This deliberately duplicates the loading algorithm of
``chan_training_api.active_model.ActiveModelProvider`` instead of importing it.
The public process must not be able to import the private control plane, whose
repository can write to the quarantine and training tables. The cost is about
forty lines; the benefit is that a compromised gateway cannot poison training
data. Keep the two loaders in step when either changes.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import joblib

from chan_ml.model import PhishingSignalModel

from .repository import GatewayRepository


class ModelNotLoadedError(RuntimeError):
    pass


class ModelRegistry:
    """Hold one validated model in memory and swap it atomically."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._version: str | None = None
        self._model: PhishingSignalModel | None = None

    @property
    def version(self) -> str | None:
        with self._lock:
            return self._version

    @property
    def loaded(self) -> bool:
        with self._lock:
            return self._model is not None

    def refresh(self, repository: GatewayRepository) -> bool:
        """Load the active artifact when its version differs. True when swapped."""
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

    def install(self, model: PhishingSignalModel, version: str) -> None:
        """Inject a model directly. For tests and offline single-file demos."""
        with self._lock:
            self._model = model
            self._version = version

    def model(self) -> PhishingSignalModel:
        with self._lock:
            model = self._model
        if model is None:
            raise ModelNotLoadedError("active_model_not_loaded")
        return model
