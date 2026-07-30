"""GET /v1/lookup/{account,phone,url} — k-anonymity lookup (§7, I4).

The protocol, from the architecture document:

    1. client: h = SHA256(normalize(value))
    2. client: GET /v1/lookup/account?prefix=<first 5 hex of h>
    3. server: returns the whole cluster sharing that prefix (20–200 entries)
    4. client: compares h against the cluster, locally

The server therefore never learns which value was looked up. Two consequences
are enforced here rather than documented: the endpoint accepts no parameter
other than a 5-hex prefix, and the prefix is never written to a log or the
access table — logging prefixes repeatedly would narrow the space over time.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from starlette.concurrency import run_in_threadpool

from ..auth import Caller, require_device
from ..config import AppConfig, get_config
from ..deps import get_rate_limiter, get_repository, get_rule_store
from ..logging_safe import log_event
from ..ratelimit import RateLimiter
from ..repository import GatewayRepository
from ..rules import RuleBundleStore
from ..schemas import LookupResponse

router = APIRouter(tags=["lookup"])

_NO_MATCH = {
    "account": "Chưa có báo cáo về số tài khoản này.",
    "phone": "Chưa có báo cáo về số điện thoại này.",
    "url": "Chưa có báo cáo về đường liên kết này.",
}


@router.get("/v1/lookup/{kind}", response_model=LookupResponse)
async def lookup(
    kind: str = Path(pattern="^(account|phone|url)$"),
    prefix: str = Query(
        ...,
        pattern="^[0-9a-f]{5}$",
        description="Đúng 5 ký tự hex đầu của SHA256(normalize(value)). "
        "Endpoint này KHÔNG nhận giá trị thô.",
    ),
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    repository: GatewayRepository = Depends(get_repository),
    rule_store: RuleBundleStore = Depends(get_rule_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> LookupResponse:
    if not limiter.check(
        scope="lookup:device",
        identity=caller.device_id,
        limit=config.lookup_per_device_per_minute,
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")

    entries = await run_in_threadpool(repository.blocklist_cluster, kind, prefix)

    # cluster_size only — never the prefix itself (I4).
    log_event("lookup", kind=kind, cluster_size=len(entries), device_id=caller.device_id)

    return LookupResponse(
        prefix=prefix,
        kind=kind,  # type: ignore[arg-type]
        hashes=[
            {
                "hash": entry.hash,
                "report_cnt": entry.report_cnt,
                "first_seen": entry.first_seen.isoformat(),
                "last_seen": entry.last_seen.isoformat(),
                "origin": entry.origin,
            }
            for entry in entries
        ],  # type: ignore[arg-type]
        cluster_size=len(entries),
        bundle_version=rule_store.get().version,
        no_match_message=_NO_MATCH[kind],
    )
