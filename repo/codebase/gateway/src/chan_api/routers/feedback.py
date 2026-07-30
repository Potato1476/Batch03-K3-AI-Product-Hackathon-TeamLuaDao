"""POST /v1/feedback — the user marks a result right or wrong (§7).

By default this stores a verdict and nothing else. If, and only if, the user
separately opts in to contribute the example, the redacted text is forwarded to
the private training plane as an `explicit_consent` scenario, where it lands in
quarantine for human review before it can influence a model.

That bridge is the single link from the public service to the training plane, and
it is one-way: this service can submit, never approve.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from chan_ml.policy import aggregate_risk
from chan_ml.redact import RedactionError, verify_redacted

from ..auth import Caller, require_device
from ..config import AppConfig, get_config
from ..deps import get_repository
from ..logging_safe import log_event
from ..repository import GatewayRepository
from ..schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(tags=["feedback"])


@router.post("/v1/feedback", response_model=FeedbackResponse)
async def feedback(
    payload: FeedbackRequest,
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    repository: GatewayRepository = Depends(get_repository),
) -> FeedbackResponse:
    exists = await run_in_threadpool(repository.analysis_exists, payload.analysis_id)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "analysis_not_found")

    contributed = False
    if payload.contribute and payload.redacted_text:
        try:
            verify_redacted(payload.redacted_text)
        except RedactionError:
            # Never echo the offending content back.
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "content_failed_redaction_check"
            ) from None
        contributed = await _forward_to_training_plane(config, payload)

    recorded = await run_in_threadpool(
        repository.record_feedback,
        analysis_id=payload.analysis_id,
        verdict=payload.verdict,
        contributed=contributed,
    )

    log_event(
        "feedback",
        analysis_id=payload.analysis_id,
        verdict=payload.verdict,
        device_id=caller.device_id,
        count=1 if contributed else 0,
    )
    return FeedbackResponse(recorded=recorded, contributed=contributed)


async def _forward_to_training_plane(
    config: AppConfig, payload: FeedbackRequest
) -> bool:
    """Submit one consented scenario for quarantine + human review."""
    if not config.training_api_url or not config.training_api_key:
        log_event("feedback_contribution_skipped", error_code="training_plane_not_configured")
        return False
    import httpx

    # A false positive means the user says it was NOT phishing, and the training
    # contract requires a non-phishing control to carry no signals at all.
    is_phishing = payload.verdict != "false_positive"
    signals = list(payload.signals) if is_phishing else []
    if is_phishing and not signals:
        # The submission would be rejected as a risk/policy mismatch. Record the
        # verdict, skip the contribution, and say so.
        log_event("feedback_contribution_skipped", error_code="signals_required")
        return False

    # `risk` must equal what L4 derives from those signals, or the training API
    # rejects the item with `risk_does_not_match_l4_policy`. Derive it with the
    # same function rather than asserting a label.
    risk = aggregate_risk({code: 1.0 for code in signals}).risk

    body = {
        "items": [
            {
                "redacted_text": payload.redacted_text,
                "signals": signals,
                "risk": risk,
                "is_phishing": is_phishing,
                "origin": "user_feedback",
                "rights_basis": "explicit_consent",
                "consented": True,
                "redaction_confirmed": True,
            }
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{config.training_api_url.rstrip('/')}/internal/v1/training/scenarios",
                json=body,
                headers={"X-CHAN-Training-Key": config.training_api_key},
            )
        if response.status_code >= 400:
            log_event(
                "feedback_contribution_rejected", error_code=f"http_{response.status_code}"
            )
            return False
    except Exception as error:  # noqa: BLE001 - feedback must still be recorded
        log_event("feedback_contribution_failed", error_code=type(error).__name__)
        return False
    return True
