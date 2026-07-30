"""POST /v1/devices/token — bootstrap and rotate a device token.

Not listed in §7's endpoint table, but required to make that table usable: §7.3
mandates authentication by an expiring, rotatable device token, and §8 defines a
`devices` table, yet nothing issues one. This is the missing bootstrap step.

No account, no phone number, no email. A token is an opaque random string bound
to a platform, and the server stores only its SHA-256 digest.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from starlette.concurrency import run_in_threadpool

from ..auth import Caller, hash_token, issue_token, require_device
from ..config import AppConfig, get_config
from ..deps import get_rate_limiter, get_repository
from ..logging_safe import log_event
from ..ratelimit import RateLimiter
from ..repository import GatewayRepository
from ..schemas import DeviceRotateRequest, DeviceTokenRequest, DeviceTokenResponse

router = APIRouter(tags=["devices"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/v1/devices/token",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_token(
    payload: DeviceTokenRequest,
    request: Request,
    config: AppConfig = Depends(get_config),
    repository: GatewayRepository = Depends(get_repository),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> DeviceTokenResponse:
    # Unauthenticated by necessity, so the only guard is the source address.
    if not limiter.check(
        scope="devices:ip", identity=_client_ip(request), limit=10, window_seconds=3600
    ):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited")

    token, digest = issue_token()
    device = await run_in_threadpool(
        repository.create_device,
        platform=payload.platform,
        token_hash=digest,
        ttl_days=config.device_token_ttl_days,
        push_token=payload.push_token,
    )
    log_event("device_created", device_id=device.id, source=payload.platform)
    return DeviceTokenResponse(
        device_id=device.id,
        token=token,
        expires_at=device.expires_at.isoformat(),
    )


@router.post(
    "/v1/devices/token/rotate",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def rotate_token(
    payload: DeviceRotateRequest,
    caller: Caller = Depends(require_device),
    config: AppConfig = Depends(get_config),
    repository: GatewayRepository = Depends(get_repository),
) -> DeviceTokenResponse:
    """Issue a successor token and revoke the presented one (§7.3 rotation)."""
    token, digest = issue_token()
    device = await run_in_threadpool(
        repository.create_device,
        platform=caller.platform,
        token_hash=digest,
        ttl_days=config.device_token_ttl_days,
        push_token=payload.push_token,
        rotated_from=caller.device_id,
    )
    log_event("device_rotated", device_id=device.id)
    return DeviceTokenResponse(
        device_id=device.id,
        token=token,
        expires_at=device.expires_at.isoformat(),
    )
