"""POST /v1/report — a user reports a scam account, phone or link (§7).

The client hashes the value before sending. The server stores the digest and its
prefix, so the blocklist stays queryable by prefix (I4) while the report itself
never reveals a plaintext identifier.

Reports are the one place where users write to shared state, so the daily cap
matters: a single device must not be able to poison the blocklist for everyone.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from ..auth import Caller, require_device
from ..config import AppConfig, get_config
from ..deps import get_rate_limiter, get_repository
from ..logging_safe import log_event
from ..ratelimit import RateLimiter
from ..repository import GatewayRepository
from ..schemas import ReportRequest, ReportResponse

router = APIRouter(tags=["report"])


@router.post(
    "/v1/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED
)
async def report(
    payload: ReportRequest,
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    repository: GatewayRepository = Depends(get_repository),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> ReportResponse:
    if not limiter.check(
        scope="report:device", identity=caller.device_id, limit=5, window_seconds=60
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")

    daily = await run_in_threadpool(repository.count_reports_today, caller.device_id)
    if daily >= config.report_per_device_per_day:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "daily_report_limit")

    count = await run_in_threadpool(
        repository.report_identifier, payload.kind, payload.value_sha256, "user_report"
    )

    log_event("report", kind=payload.kind, count=count, device_id=caller.device_id)
    return ReportResponse(kind=payload.kind, report_cnt=count)
