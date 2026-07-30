"""Authentication for the internal inference route."""

from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException, status

from .config import DetectionConfig


def require_gateway(
    presented: str | None = Header(default=None, alias="X-CHAN-Detection-Key"),
    config: DetectionConfig = Depends(DetectionConfig.from_env),
) -> None:
    if not presented or not hmac.compare_digest(
        presented, config.detection_api_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_detection_api_key",
        )
