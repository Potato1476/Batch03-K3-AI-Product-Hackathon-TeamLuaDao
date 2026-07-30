"""Constant-time API-key authentication for internal control-plane routes."""

from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException, status

from .config import IntelConfig, get_config


def require_intel_actor(
    x_chan_intel_key: str | None = Header(default=None),
    config: IntelConfig = Depends(get_config),
) -> str:
    if not x_chan_intel_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_intel_api_key",
        )
    matched_actor: str | None = None
    for actor, expected in config.api_keys.items():
        if hmac.compare_digest(x_chan_intel_key, expected):
            matched_actor = actor
    if matched_actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_intel_api_key",
        )
    return matched_actor
