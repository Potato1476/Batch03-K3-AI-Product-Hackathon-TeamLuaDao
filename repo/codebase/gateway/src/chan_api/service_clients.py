"""Typed HTTP clients for CHẮN internal services.

The gateway owns the public edge contract, but not detection, threat-intel
storage, or training. Keeping those calls here prevents routers from quietly
re-implementing another service's domain logic.
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx


class ServiceUnavailableError(RuntimeError):
    """An internal service could not produce a usable response."""


class ServiceResponseError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _detail(response: httpx.Response) -> str:
    try:
        value = response.json().get("detail")
    except (ValueError, AttributeError):
        value = None
    return value if isinstance(value, str) else "internal_service_error"


class DetectionClient:
    def __init__(
        self, base_url: str, api_key: str, *, timeout_seconds: float
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def analyze(self, body: dict[str, Any]) -> dict[str, Any]:
        if not self._base_url or not self._api_key:
            raise ServiceUnavailableError("detection_service_not_configured")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/internal/v1/analyze",
                    json=body,
                    headers={"X-CHAN-Detection-Key": self._api_key},
                )
        except httpx.HTTPError as error:
            raise ServiceUnavailableError("detection_service_unavailable") from error
        if response.status_code >= 400:
            raise ServiceResponseError(response.status_code, _detail(response))
        try:
            return response.json()
        except ValueError as error:
            raise ServiceUnavailableError("invalid_detection_response") from error

    async def healthy(self) -> bool:
        if not self._base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/healthz")
            return response.status_code == 200
        except httpx.HTTPError:
            return False


class IntelClient:
    def __init__(
        self, base_url: str, api_key: str, *, timeout_seconds: float
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def lookup(self, kind: str, prefix: str) -> dict[str, Any]:
        if not self._base_url:
            raise ServiceUnavailableError("intel_service_not_configured")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._base_url}/v1/lookup/{kind}",
                    params={"prefix": prefix},
                )
        except httpx.HTTPError as error:
            raise ServiceUnavailableError("intel_service_unavailable") from error
        if response.status_code >= 400:
            raise ServiceResponseError(response.status_code, _detail(response))
        try:
            return response.json()
        except ValueError as error:
            raise ServiceUnavailableError("invalid_intel_response") from error

    async def report(
        self, *, kind: str, digest: str, device_id: str
    ) -> dict[str, Any]:
        if not self._base_url or not self._api_key:
            raise ServiceUnavailableError("intel_service_not_configured")
        reporter_hash = hashlib.sha256(
            f"chan:reporter:v1:{device_id}".encode("utf-8")
        ).hexdigest()
        body = {
            "items": [
                {
                    "kind": kind,
                    "indicator_hash": digest,
                    "reporter_hash": reporter_hash,
                    "consented": True,
                }
            ]
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/internal/v1/intel/reports",
                    json=body,
                    headers={"X-CHAN-Intel-Key": self._api_key},
                )
        except httpx.HTTPError as error:
            raise ServiceUnavailableError("intel_service_unavailable") from error
        if response.status_code >= 400:
            raise ServiceResponseError(response.status_code, _detail(response))
        try:
            return response.json()
        except ValueError as error:
            raise ServiceUnavailableError("invalid_intel_response") from error
