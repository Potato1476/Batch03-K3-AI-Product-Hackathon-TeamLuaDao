"""POST /v1/analyze — authenticated edge delegation to Detection."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from chan_ml.normalize import normalize_for_model
from chan_ml.local_rules import evaluate_local_rules

from ..auth import Caller, require_device
from ..config import AppConfig, get_config
from ..deps import (
    get_detection_client,
    get_hotlines,
    get_rate_limiter,
    get_repository,
    get_rule_store,
)
from ..logging_safe import log_event
from ..hotlines import HotlineDirectory
from ..ratelimit import RateLimiter
from ..repository import GatewayRepository
from ..rules import RuleBundleStore
from ..schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeThreadRequest,
    AnalyzeThreadResponse,
)
from ..service_clients import (
    DetectionClient,
    ServiceResponseError,
    ServiceUnavailableError,
)

router = APIRouter(tags=["analyze"])
_PUBLIC_ACTIONS = {"report", "share_to_guardian", "lookup_account"}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest,
    request: Request,
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    repository: GatewayRepository = Depends(get_repository),
    rule_store: RuleBundleStore = Depends(get_rule_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
    detection: DetectionClient = Depends(get_detection_client),
    hotlines: HotlineDirectory = Depends(get_hotlines),
) -> AnalyzeResponse:
    if not limiter.check(
        scope="analyze:device",
        identity=caller.device_id,
        limit=config.analyze_per_device_per_minute,
    ) or not limiter.check(
        scope="analyze:ip",
        identity=_client_ip(request),
        limit=config.analyze_per_ip_per_minute,
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")

    try:
        bundle = rule_store.get()
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "rule_bundle_unavailable"
        ) from error

    if set(payload.local_signals) - bundle.local_signal_names:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown_local_signal"
        )

    verified_local_signals = evaluate_local_rules(
        payload.text,
        bundle.payload,
    ).local_signals
    body = payload.model_dump()
    body["local_signals"] = list(verified_local_signals)
    body["rule_bundle_version"] = bundle.version
    body["local_boosts"] = bundle.boosts_for(verified_local_signals)
    try:
        result = await detection.analyze(body)
    except ServiceResponseError as error:
        if error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            raise HTTPException(error.status_code, error.detail) from None
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "detection_engine_unavailable"
        ) from None
    except ServiceUnavailableError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "detection_engine_unavailable"
        ) from None

    actions = [
        action for action in result.get("actions", []) if action in _PUBLIC_ACTIONS
    ]
    signal_codes = frozenset(
        str(item.get("code")) for item in result.get("signals", [])
    )
    hotline = result.get("verified_hotline")
    if hotline is None and result.get("risk") != "unknown":
        resolved = hotlines.resolve(payload.text, signal_codes=signal_codes)
        if resolved is not None:
            hotline = {"name": resolved.name, "number": resolved.number}

    response = AnalyzeResponse(
        analysis_id=str(result["analysis_id"]),
        risk=result["risk"],
        score=float(result["score"]),
        signals=result.get("signals", []),
        explanation=str(result["explanation"]),
        questions=list(result.get("questions", [])),
        verified_hotline=hotline,
        actions=actions,
        engine_version=str(result["engine_version"]),
        rule_bundle_version=bundle.version,
    )

    text_sha256 = hashlib.sha256(
        normalize_for_model(payload.text).encode("utf-8")
    ).digest()
    try:
        await run_in_threadpool(
            repository.record_analysis,
            id=response.analysis_id,
            text_sha256=text_sha256,
            risk=response.risk,
            score=response.score,
            signals=[
                {"code": item.code, "confidence": item.confidence}
                for item in response.signals
            ],
            source=payload.source,
            input_mode=payload.input_mode,
            app_package=payload.app_package,
            truncated=payload.truncated,
            blocklist_match=bool(result.get("blocklist_match", False)),
            engine_version=response.engine_version,
            rule_version=bundle.version,
            device_id=caller.device_id,
        )
    except Exception as error:  # noqa: BLE001 - inference remains available
        log_event("analysis_persist_failed", error_code=type(error).__name__)
    return response


@router.post("/v1/analyze-thread", response_model=AnalyzeThreadResponse)
async def analyze_conversation(
    payload: AnalyzeThreadRequest,
    request: Request,
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    rule_store: RuleBundleStore = Depends(get_rule_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
    detection: DetectionClient = Depends(get_detection_client),
) -> AnalyzeThreadResponse:
    """L5 — analyse a conversation instead of a message.

    A thread costs more privacy than a single message, so it is rate limited on
    the same buckets and, like `/v1/analyze`, nothing about its content reaches
    the database: I2 forbids storing message text, and a thread verdict has no
    row to write.
    """
    if not limiter.check(
        scope="analyze:device",
        identity=caller.device_id,
        limit=config.analyze_per_device_per_minute,
    ) or not limiter.check(
        scope="analyze:ip",
        identity=_client_ip(request),
        limit=config.analyze_per_ip_per_minute,
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")

    try:
        bundle = rule_store.get()
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "rule_bundle_unavailable"
        ) from error

    body = payload.model_dump()
    body["rule_bundle_version"] = bundle.version
    try:
        result = await detection.analyze_thread(body)
    except ServiceResponseError as error:
        if error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            raise HTTPException(error.status_code, error.detail) from None
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "detection_engine_unavailable"
        ) from None
    except ServiceUnavailableError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "detection_engine_unavailable"
        ) from None

    result["actions"] = [
        action for action in result.get("actions", []) if action in _PUBLIC_ACTIONS
    ]
    result["rule_bundle_version"] = bundle.version
    return AnalyzeThreadResponse(**result)
