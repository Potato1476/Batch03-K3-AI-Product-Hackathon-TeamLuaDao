"""The L3 classification seam.

§5 fixes what L3 must produce: a 0–1 score for each of the eight signals, each
with `evidence` quoted from the text. It does not fix how. Two implementations
exist — the local sklearn model and a commercial LLM — and both must satisfy
this interface so L4 stays a single deterministic function.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from chan_ml.constants import SIGNAL_CODES


@dataclass(frozen=True)
class SignalScore:
    code: str
    confidence: float
    evidence: str = ""

    def __post_init__(self) -> None:
        if self.code not in SIGNAL_CODES:
            raise ValueError(f"unknown signal code: {self.code}")


@dataclass(frozen=True)
class Classification:
    """Raw L3 output. The risk decision belongs to L4, never to a classifier."""

    signals: tuple[SignalScore, ...]
    provider: str
    engine_version: str

    def as_map(self) -> dict[str, float]:
        return {signal.code: signal.confidence for signal in self.signals}

    def evidence_map(self) -> dict[str, str]:
        return {signal.code: signal.evidence for signal in self.signals}


class SignalClassifier(Protocol):
    async def classify(self, redacted_text: str) -> Classification: ...


def merge(classifications: Sequence[Classification], *, provider: str) -> Classification:
    """Max-pool per signal code across providers.

    §11 prioritises recall over precision: if either provider is confident about
    a signal, the aggregate is confident. Evidence follows the winning score so
    the explanation still quotes real text.
    """
    if not classifications:
        raise ValueError("no classifications to merge")
    if len(classifications) == 1:
        return classifications[0]
    best: dict[str, SignalScore] = {}
    for classification in classifications:
        for signal in classification.signals:
            current = best.get(signal.code)
            if current is None or signal.confidence > current.confidence:
                best[signal.code] = signal
    versions = "+".join(
        sorted({classification.engine_version for classification in classifications})
    )
    return Classification(
        signals=tuple(best[code] for code in SIGNAL_CODES if code in best),
        provider=provider,
        engine_version=versions,
    )


def apply_local_signal_boosts(
    classification: Classification,
    boosts: Mapping[str, float],
) -> Classification:
    """Fold on-device L1 findings into the L3 scores.

    `local_signals` from the request use L1's own vocabulary (`url_shortened`,
    `apk_link`, …), which is NOT the eight-signal taxonomy — `aggregate_risk`
    rejects anything outside it. The Rule Bundle maps each local signal to a
    taxonomy code plus a bounded boost, and that mapping is applied here so the
    client cannot inject an arbitrary score.
    """
    if not boosts:
        return classification
    scores = dict(classification.as_map())
    evidence = dict(classification.evidence_map())
    for code, boost in boosts.items():
        if code not in SIGNAL_CODES:
            continue
        scores[code] = min(1.0, scores.get(code, 0.0) + boost)
        evidence.setdefault(code, "")
    return Classification(
        signals=tuple(
            SignalScore(code=code, confidence=scores[code], evidence=evidence.get(code, ""))
            for code in SIGNAL_CODES
            if code in scores
        ),
        provider=classification.provider,
        engine_version=classification.engine_version,
    )
