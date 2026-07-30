"""POST /v1/analyze — the detection engine entry point (§7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from ..auth import Caller, require_device
from ..config import AppConfig, get_config
from ..deps import (
    get_hotlines,
    get_model_registry,
    get_rate_limiter,
    get_repository,
    get_rule_store,
)
from ..hotlines import HotlineDirectory
from ..l3.base import Classification, merge
from ..l3.llm import LlmClassificationError
from ..l3.local import LocalModelClassifier
from ..l3.similarity import NullSimilarity, PgVectorSimilarity, SimilarityResult
from ..logging_safe import log_event
from ..model_registry import ModelNotLoadedError, ModelRegistry
from ..pipeline import (
    build_outcome,
    check_blocklist,
    gather_signals,
    otp_outcome,
    redact,
    text_digest,
)
from ..ratelimit import RateLimiter
from ..repository import GatewayRepository
from ..rules import RuleBundleStore
from ..schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])

_llm_classifier = None


def _build_classifier(config: AppConfig, registry: ModelRegistry):  # noqa: ANN202
    """Return (primary, fallback). The fallback is always the local model."""
    global _llm_classifier
    local = LocalModelClassifier(registry)
    if config.l3_provider == "local":
        return local, None
    if _llm_classifier is None:
        from ..l3.llm import LlmClassifier

        _llm_classifier = LlmClassifier(
            api_key=config.llm_api_key,
            model=config.llm_model,
            timeout_seconds=config.llm_timeout_seconds,
        )
    if config.l3_provider == "llm":
        return _llm_classifier, local
    return _EnsembleClassifier(local, _llm_classifier), local


class _EnsembleClassifier:
    """Max-pool the two providers; tolerate the LLM being unavailable."""

    def __init__(self, local, llm) -> None:  # noqa: ANN001
        self._local = local
        self._llm = llm

    async def classify(self, redacted_text: str) -> Classification:
        local_result = await self._local.classify(redacted_text)
        try:
            llm_result = await self._llm.classify(redacted_text)
        except LlmClassificationError as error:
            log_event("l3_llm_unavailable", error_code=str(error), l3_provider="ensemble")
            return local_result
        return merge([local_result, llm_result], provider="ensemble")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/v1/analyze",
    response_model=AnalyzeResponse,
    # No exclude_none: §7 lists verified_hotline, so it is always present and
    # explicitly null when absent. Clients get one stable response shape.
    status_code=status.HTTP_200_OK,
)
async def analyze(
    payload: AnalyzeRequest,
    request: Request,
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    repository: GatewayRepository = Depends(get_repository),
    registry: ModelRegistry = Depends(get_model_registry),
    rule_store: RuleBundleStore = Depends(get_rule_store),
    hotlines: HotlineDirectory = Depends(get_hotlines),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> AnalyzeResponse:
    # §7.3 — two limits: per token, and per IP so rotating tokens does not help
    # anyone use this as a free LLM proxy.
    if not limiter.check(
        scope="analyze:device",
        identity=caller.device_id,
        limit=config.analyze_per_device_per_minute,
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")
    if not limiter.check(
        scope="analyze:ip",
        identity=_client_ip(request),
        limit=config.analyze_per_ip_per_minute,
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")

    try:
        bundle = rule_store.get()
    except (FileNotFoundError, ValueError) as error:
        # Without a bundle there is no rule_bundle_version to report and no
        # local-signal vocabulary to validate against. Fail explicitly rather
        # than analysing against an unknown rule set.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "rule_bundle_unavailable"
        ) from error

    unknown_signals = set(payload.local_signals) - bundle.local_signal_names
    if unknown_signals:
        # The client claimed an L1 signal this bundle does not define, which
        # means the two are out of step. Refuse rather than guess.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown_local_signal")

    digest = text_digest(payload.text)

    # ---- L2 -----------------------------------------------------------------
    # Everything past this point works on redaction.text. The original text is
    # never persisted, never logged, and leaves memory when the request ends.
    redaction = redact(payload.text)
    local_boosts = bundle.boosts_for(tuple(payload.local_signals))

    if redaction.otp_found:
        outcome = otp_outcome(
            bundle=bundle,
            engine_version=registry.version or "rules-only",
            truncated=payload.truncated,
            text_sha256=digest,
        )
    else:
        blocklist_match = await check_blocklist(repository, redaction)
        # Built before the try block so `fallback` is always bound in except.
        primary, fallback = _build_classifier(config, registry)
        similarity = (
            PgVectorSimilarity(repository, _embedder(config))
            if config.similarity_enabled
            else NullSimilarity()
        )

        try:
            classification, similarity_result = await gather_signals(
                classifier=primary,
                similarity=similarity,
                redacted_text=redaction.text,
                local_boosts=local_boosts,
            )
        except ModelNotLoadedError:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "detection_engine_unavailable"
            ) from None
        except LlmClassificationError as error:
            if fallback is None:
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE, "detection_engine_unavailable"
                ) from None
            log_event("l3_fallback_to_local", error_code=str(error))
            classification, similarity_result = await gather_signals(
                classifier=fallback,
                similarity=NullSimilarity(),
                redacted_text=redaction.text,
                local_boosts=local_boosts,
            )

        evidence: dict[str, str] = {}
        if isinstance(primary, LocalModelClassifier) or fallback is not None:
            evidence = await _local_evidence(registry, classification, redaction.text)

        outcome = build_outcome(
            redacted_text=redaction.text,
            classification=classification,
            similarity=similarity_result,
            similarity_beta=config.similarity_beta,
            blocklist_match=blocklist_match,
            bundle=bundle,
            hotlines=hotlines,
            truncated=payload.truncated,
            text_sha256=digest,
            evidence=evidence,
        )

    await _persist(repository, outcome, payload, caller)

    log_event(
        "analyze",
        analysis_id=outcome.analysis_id,
        risk=outcome.risk,
        score=outcome.score,
        signal_codes=[str(item["code"]) for item in outcome.signals],
        source=payload.source,
        input_mode=payload.input_mode,
        truncated=payload.truncated,
        engine_version=outcome.engine_version,
        rule_bundle_version=outcome.rule_bundle_version,
        device_id=caller.device_id,
    )

    return AnalyzeResponse(
        analysis_id=outcome.analysis_id,
        risk=outcome.risk,
        score=outcome.score,
        signals=[dict(item) for item in outcome.signals],  # type: ignore[arg-type]
        explanation=outcome.explanation,
        questions=list(outcome.questions),
        verified_hotline=(
            outcome.verified_hotline.as_dict() if outcome.verified_hotline else None
        ),  # type: ignore[arg-type]
        actions=list(outcome.actions),  # type: ignore[arg-type]
        engine_version=outcome.engine_version,
        rule_bundle_version=outcome.rule_bundle_version,
    )


async def _local_evidence(
    registry: ModelRegistry, classification: Classification, redacted_text: str
) -> dict[str, str]:
    """Attribution quotes for reported signals, when a local model is loaded."""
    codes = [
        signal.code
        for signal in classification.signals
        if signal.confidence >= 0.5 and not signal.evidence
    ]
    if not codes or not registry.loaded:
        return {}
    try:
        return await LocalModelClassifier(registry).evidence_for(redacted_text, codes)
    except Exception:  # noqa: BLE001 - evidence is a nicety, not a gate
        return {}


async def _persist(
    repository: GatewayRepository,
    outcome,  # noqa: ANN001 - AnalysisOutcome
    payload: AnalyzeRequest,
    caller: Caller,
) -> None:
    """Store metadata only. The evidence field never reaches the database (I2)."""
    try:
        await run_in_threadpool(
            repository.record_analysis,
            id=outcome.analysis_id,
            text_sha256=outcome.text_sha256,
            risk=outcome.risk,
            score=outcome.score,
            signals=list(outcome.storable_signals),
            source=payload.source,
            input_mode=payload.input_mode,
            app_package=payload.app_package,
            truncated=payload.truncated,
            blocklist_match=outcome.blocklist_match,
            engine_version=outcome.engine_version,
            rule_version=outcome.rule_bundle_version,
            device_id=caller.device_id,
        )
    except Exception:  # noqa: BLE001 - a warning delivered beats a stored record
        log_event("analysis_persist_failed", error_code="persist_failed")


def _embedder(config: AppConfig):  # noqa: ANN202
    """Placeholder embedder hook.

    Similarity stays off until an embedding provider is chosen; §5 leaves that
    open. Enabling CHAN_SIMILARITY_ENABLED without wiring one here yields 0.0,
    which makes the β term vanish rather than bias every score.
    """

    class _Unavailable:
        async def embed(self, text: str):  # noqa: ANN202
            raise RuntimeError("embedder_not_configured")

    return _Unavailable()
