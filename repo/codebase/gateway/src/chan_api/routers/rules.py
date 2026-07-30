"""GET /v1/rules/bundle — serve the Rule Bundle for on-device L0+L1 (§7).

This endpoint is what makes Web/Android equivalence a property of the data rather
than of programmer discipline (§3): both clients compile the same JSON, so their
L1 behaviour cannot drift.

It is unauthenticated on purpose. The bundle contains no user data, every client
needs it before it can obtain a device token, and gating it would only add a
failure mode to the offline path.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from ..deps import get_rule_store
from ..rules import RuleBundleStore

router = APIRouter(tags=["rules"])


@router.get("/v1/rules/bundle")
def rules_bundle(
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    rule_store: RuleBundleStore = Depends(get_rule_store),
) -> Response:
    try:
        bundle = rule_store.get()
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "rule_bundle_unavailable"
        ) from error

    etag = f'"{bundle.etag}"'
    headers = {
        "ETag": etag,
        "Cache-Control": "public, max-age=3600",
        "X-CHAN-Bundle-Version": bundle.version,
    }
    if if_none_match and if_none_match.strip() == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    # Served byte-for-byte: the ETag is the hash of these exact bytes, and both
    # client ports must parse an identical document.
    return Response(
        content=bundle.raw,
        media_type="application/json",
        headers=headers,
    )
