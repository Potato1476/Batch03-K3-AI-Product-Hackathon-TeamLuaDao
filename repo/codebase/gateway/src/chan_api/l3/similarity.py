"""Nearest-scenario similarity via pgvector (§5, second signal source).

`similarity_max` feeds the `β × similarity_max` term of the L4 score. It is only
meaningful once the scenario store holds embeddings, and the store only accepts
rows the user explicitly consented to contribute (§7.2). With an empty store the
provider returns 0.0 and β should stay 0.0, which makes the term vanish rather
than quietly bias every score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from starlette.concurrency import run_in_threadpool

from ..repository import GatewayRepository


@dataclass(frozen=True)
class SimilarityResult:
    similarity_max: float = 0.0
    nearest_labels: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return self.similarity_max > 0.0


class Embedder(Protocol):
    async def embed(self, text: str) -> Sequence[float]: ...


class NullSimilarity:
    """Used when similarity is disabled or no embedder is configured."""

    async def score(self, redacted_text: str) -> SimilarityResult:
        return SimilarityResult()


class PgVectorSimilarity:
    def __init__(self, repository: GatewayRepository, embedder: Embedder) -> None:
        self._repository = repository
        self._embedder = embedder

    async def score(self, redacted_text: str) -> SimilarityResult:
        try:
            embedding = await self._embedder.embed(redacted_text)
            matches = await run_in_threadpool(
                self._repository.similar_scenarios, embedding
            )
        except Exception:  # noqa: BLE001 - similarity is an enhancement, not a gate
            return SimilarityResult()
        if not matches:
            return SimilarityResult()
        nearest = max(matches, key=lambda match: match.similarity)
        return SimilarityResult(
            similarity_max=min(1.0, max(0.0, nearest.similarity)),
            nearest_labels=nearest.labels,
        )
