"""GET /v1/lookup/{kind} — authenticated edge delegation to Intel."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from ..auth import Caller, require_device
from ..config import AppConfig, get_config
from ..deps import get_intel_client, get_rate_limiter, get_rule_store
from ..logging_safe import log_event
from ..ratelimit import RateLimiter
from ..rules import RuleBundleStore
from ..schemas import LookupResponse
from ..service_clients import IntelClient, ServiceResponseError, ServiceUnavailableError

router = APIRouter(tags=["lookup"])
_NO_MATCH = {
    "account": "Chưa có báo cáo về số tài khoản này.",
    "phone": "Chưa có báo cáo về số điện thoại này.",
    "url": "Chưa có báo cáo về đường liên kết này.",
}


@router.get("/v1/lookup/{kind}", response_model=LookupResponse)
async def lookup(
    kind: str = Path(pattern="^(account|phone|url)$"),
    prefix: str = Query(..., pattern="^[0-9a-f]{5}$"),
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    rule_store: RuleBundleStore = Depends(get_rule_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
    intel: IntelClient = Depends(get_intel_client),
) -> LookupResponse:
    if not limiter.check(
        scope="lookup:device",
        identity=caller.device_id,
        limit=config.lookup_per_device_per_minute,
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")
    try:
        result = await intel.lookup(kind, prefix)
    except ServiceResponseError as error:
        raise HTTPException(error.status_code, error.detail) from None
    except ServiceUnavailableError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "intel_service_unavailable"
        ) from None

    hashes = [
        {
            "hash": prefix + str(item["suffix"]),
            "report_cnt": int(item["report_count"]),
            "first_seen": str(item["first_seen"]),
            "last_seen": str(item["last_seen"]),
            "origin": str(item["confidence"]),
        }
        for item in result.get("items", [])
    ]
    log_event(
        "lookup", kind=kind, cluster_size=len(hashes), device_id=caller.device_id
    )
    return LookupResponse(
        prefix=prefix,
        kind=kind,  # type: ignore[arg-type]
        hashes=hashes,  # type: ignore[arg-type]
        cluster_size=len(hashes),
        bundle_version=rule_store.get().version,
        no_match_message=_NO_MATCH[kind],
    )
