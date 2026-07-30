"""Checksum-verified model runtime sourced from the Training API registry."""

from __future__ import annotations

import hashlib
from pathlib import Path
from threading import RLock
import time
from typing import cast, Mapping, TypedDict

import httpx
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
    def __init__(self, model: PhishingSignalModel, *, model_version: str) -> None:
        self._model = model
        self._model_version = model_version
        self._lock = RLock()

    @property
    def model_version(self) -> str:
        return self._model_version

    @classmethod
    def load(
        cls, *, artifact_uri: str, artifact_sha256: str, model_version: str
    ) -> "ModelRuntime":
        path = Path(artifact_uri)
        if file_sha256(path) != artifact_sha256:
            raise ValueError("model_checksum_mismatch")
        candidate = joblib.load(path)
        if not isinstance(candidate, PhishingSignalModel):
            raise TypeError("unsupported_model_artifact")
        return cls(candidate, model_version=model_version)

    def predict(
        self,
        redacted_text: str,
        *,
        signal_boosts: Mapping[str, float] | None = None,
        verified_local_signals: tuple[str, ...] = (),
    ) -> ModelPrediction:
        with self._lock:
            return cast(
                ModelPrediction,
                self._model.predict(
                    redacted_text,
                    signal_boosts=signal_boosts,
                    verified_local_signals=verified_local_signals,
                ),
            )


class RuntimeProvider:
    """Poll Training API metadata and atomically replace the active runtime."""

    def __init__(self, config: DetectionConfig) -> None:
        self._config = config
        self._runtime: ModelRuntime | None = None
        self._checked_at = 0.0
        self._lock = RLock()

    def current(self) -> ModelRuntime:
        now = time.monotonic()
        with self._lock:
            runtime = self._runtime
            refresh_due = (
                runtime is None
                or now - self._checked_at >= self._config.model_poll_seconds
            )
            if not refresh_due:
                assert runtime is not None
                return runtime
            try:
                metadata = self._fetch_metadata()
                if (
                    runtime is None
                    or runtime.model_version != str(metadata["version"])
                ):
                    runtime = ModelRuntime.load(
                        artifact_uri=str(metadata["artifact_uri"]),
                        artifact_sha256=str(metadata["artifact_sha256"]),
                        model_version=str(metadata["version"]),
                    )
                    self._runtime = runtime
                self._checked_at = now
            except (httpx.HTTPError, KeyError, OSError, TypeError, ValueError):
                # A registry outage must not evict an already validated model.
                self._checked_at = now
                if runtime is None:
                    runtime = self._load_bootstrap()
                    self._runtime = runtime
            return runtime

    def _load_bootstrap(self) -> ModelRuntime:
        """Start a fresh local stack before the registry has a promoted row."""
        if (
            not self._config.bootstrap_model_path
            or not self._config.bootstrap_model_sha256
            or not self._config.bootstrap_model_version
        ):
            raise RuntimeError("model_unavailable")
        try:
            return ModelRuntime.load(
                artifact_uri=self._config.bootstrap_model_path,
                artifact_sha256=self._config.bootstrap_model_sha256,
                model_version=self._config.bootstrap_model_version,
            )
        except (OSError, TypeError, ValueError) as error:
            raise RuntimeError("model_unavailable") from error

    def _fetch_metadata(self) -> dict[str, object]:
        with httpx.Client(timeout=self._config.request_timeout_seconds) as client:
            response = client.get(
                (
                    f"{self._config.training_api_url}"
                    "/internal/v1/training/models/active"
                ),
                headers={
                    "X-CHAN-Training-Key": self._config.training_api_key
                },
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("invalid_model_metadata")
        return payload
