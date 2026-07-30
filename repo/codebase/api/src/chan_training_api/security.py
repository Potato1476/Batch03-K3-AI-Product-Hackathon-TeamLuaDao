"""Constant-time authentication for private training endpoints."""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, status

from .config import AppConfig, get_config


def require_training_actor(
    presented: str | None = Header(default=None, alias="X-CHAN-Training-Key"),
    config: AppConfig = Depends(get_config),
) -> str:
    if not config.api_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="training_api_not_configured",
        )
    if not presented:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="training_key_required",
        )
    for key_id, expected in config.api_keys.items():
        if secrets.compare_digest(presented, expected):
            return key_id
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid_training_key",
    )
