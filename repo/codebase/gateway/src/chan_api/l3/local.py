"""L3 backed by the local chan_ml model.

Default provider: no network, no per-call cost, p50 ≈ 2.3 ms. The model is
sklearn and therefore synchronous, so inference runs in a worker thread to keep
the event loop free — /v1/analyze has a p95 budget of five seconds (§11.4).
"""

from __future__ import annotations

from starlette.concurrency import run_in_threadpool

from chan_ml.constants import SIGNAL_CODES

from ..model_registry import ModelRegistry
from .base import Classification, SignalScore


class LocalModelClassifier:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    async def classify(self, redacted_text: str) -> Classification:
        return await run_in_threadpool(self._classify_sync, redacted_text)

    def _classify_sync(self, redacted_text: str) -> Classification:
        model = self._registry.model()
        probabilities = model.predict_probabilities([redacted_text])[0]
        # predict() would already apply L4, and it drops sub-threshold signals.
        # The gateway needs the full vector so blocklist and similarity inputs
        # can join the same aggregation.
        signals = tuple(
            SignalScore(
                code=code,
                confidence=round(float(probabilities[index]), 4),
                evidence="",
            )
            for index, code in enumerate(SIGNAL_CODES)
        )
        return Classification(
            signals=signals,
            provider="local",
            engine_version=self._registry.version
            or str(model.metadata.get("engine_version", "unknown")),
        )

    async def evidence_for(self, redacted_text: str, codes: list[str]) -> dict[str, str]:
        """Attribution-based quotes for the signals that ended up reported."""
        if not codes:
            return {}
        return await run_in_threadpool(self._evidence_sync, redacted_text, codes)

    def _evidence_sync(self, redacted_text: str, codes: list[str]) -> dict[str, str]:
        model = self._registry.model()
        # _evidence is private but is the only attribution path that returns a
        # real source sentence rather than a regex match, which §5 requires.
        return {code: model._evidence(redacted_text, code) for code in codes}
