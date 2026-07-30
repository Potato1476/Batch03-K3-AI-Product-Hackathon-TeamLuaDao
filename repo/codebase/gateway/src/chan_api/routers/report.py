"""POST /v1/report — authenticated edge delegation to Intel quarantine."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import Caller, require_device
from ..config import AppConfig, get_config
from ..deps import get_intel_client, get_rate_limiter
from ..logging_safe import log_event
from ..ratelimit import RateLimiter
from ..schemas import ReportRequest, ReportResponse
from ..service_clients import IntelClient, ServiceResponseError, ServiceUnavailableError

router = APIRouter(tags=["report"])


@router.post(
    "/v1/report", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED
)
async def report(
    payload: ReportRequest,
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    limiter: RateLimiter = Depends(get_rate_limiter),
    intel: IntelClient = Depends(get_intel_client),
) -> ReportResponse:
    if not limiter.check(
        scope="report:device",
        identity=caller.device_id,
        limit=config.report_per_device_per_day,
        window_seconds=86_400,
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "daily_report_limit")
    try:
        result = await intel.report(
            kind=payload.kind,
            digest=payload.value_sha256,
            device_id=caller.device_id,
        )
    except ServiceResponseError as error:
        raise HTTPException(error.status_code, error.detail) from None
    except ServiceUnavailableError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "intel_service_unavailable"
        ) from None

    accepted = int(result.get("accepted", 0))
    log_event(
        "report", kind=payload.kind, count=accepted, device_id=caller.device_id
    )
    # Intel deliberately quarantines community reports. A public report count
    # would imply immediate activation, so it remains zero until review.
    return ReportResponse(
        kind=payload.kind, report_cnt=0, accepted=accepted == 1
    )
