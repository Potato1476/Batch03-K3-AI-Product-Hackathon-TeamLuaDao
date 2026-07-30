"""Device-token authentication.

§7.3: authenticate with a device token issued at first launch — no account, no
phone number as identity — and expire/rotate it. The token is stored only as a
SHA-256 digest, so a database leak does not yield usable credentials.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from .config import AppConfig, get_config
from .deps import get_repository
from .repository import Device, GatewayRepository

_TOKEN_BYTES = 32


def issue_token() -> tuple[str, bytes]:
    """Return (plaintext token shown once, digest to store)."""
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    return token, hash_token(token)


def hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


@dataclass(frozen=True)
class Caller:
    device: Device

    @property
    def device_id(self) -> str:
        return self.device.id

    @property
    def platform(self) -> str:
        return self.device.platform


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def require_device(
    authorization: str | None = Header(default=None),
    repository: GatewayRepository = Depends(get_repository),
    config: AppConfig = Depends(get_config),
) -> Caller:
    token = _bearer(authorization)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="device_token_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    device = repository.device_for_token(hash_token(token))
    if device is None:
        # One code for absent, expired, revoked and wrong tokens: distinguishing
        # them tells an attacker which guess was closer.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_device_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Caller(device=device)
