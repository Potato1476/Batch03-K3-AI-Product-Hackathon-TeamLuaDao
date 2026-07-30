"""Dependency providers.

Everything the routers need arrives through these functions so tests can replace
any single piece via `app.dependency_overrides`, the pattern the training API's
tests already use.

Each provider takes its config through `Depends(get_config)` rather than a plain
default: a bare annotated parameter would be read by FastAPI as a *query
parameter*, which would both break the signature and expose it to callers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from .config import AppConfig, get_config
from .hotlines import HotlineDirectory
from .service_clients import DetectionClient, IntelClient
from .ratelimit import RateLimiter, build_backend
from .repository import GatewayRepository, PostgresGatewayRepository
from .rules import RuleBundleStore


@lru_cache
def _repository_singleton(dsn: str) -> PostgresGatewayRepository:
    return PostgresGatewayRepository(dsn)


def get_repository(
    config: AppConfig = Depends(get_config),
) -> GatewayRepository:
    return _repository_singleton(config.database_url)


@lru_cache(maxsize=8)
def _detection_client(url: str, key: str, timeout: float) -> DetectionClient:
    return DetectionClient(url, key, timeout_seconds=timeout)


def get_detection_client(
    config: AppConfig = Depends(get_config),
) -> DetectionClient:
    return _detection_client(
        config.detection_api_url,
        config.detection_api_key,
        config.request_timeout_seconds,
    )


@lru_cache(maxsize=8)
def _intel_client(url: str, key: str, timeout: float) -> IntelClient:
    return IntelClient(url, key, timeout_seconds=timeout)


def get_intel_client(config: AppConfig = Depends(get_config)) -> IntelClient:
    return _intel_client(
        config.intel_api_url, config.intel_api_key, config.request_timeout_seconds
    )


@lru_cache
def _rule_store(path: str) -> RuleBundleStore:
    return RuleBundleStore(Path(path))


def get_rule_store(config: AppConfig = Depends(get_config)) -> RuleBundleStore:
    return _rule_store(str(config.bundle_path))


@lru_cache
def _hotline_directory(path: str) -> HotlineDirectory:
    return HotlineDirectory(Path(path))


def get_hotlines(config: AppConfig = Depends(get_config)) -> HotlineDirectory:
    return _hotline_directory(str(config.hotlines_path))


# Not lru_cache'd on the repository: a test fake may be an unhashable dataclass,
# and the in-process counter state must survive across requests either way.
_LIMITERS: dict[str, RateLimiter] = {}


def get_rate_limiter(
    config: AppConfig = Depends(get_config),
    repository: GatewayRepository = Depends(get_repository),
) -> RateLimiter:
    limiter = _LIMITERS.get(config.redis_url)
    if limiter is None:
        limiter = RateLimiter(build_backend(config.redis_url, repository))
        _LIMITERS[config.redis_url] = limiter
    return limiter


def reset_caches() -> None:
    """Drop memoised singletons. Used by tests and by config reloads."""
    _repository_singleton.cache_clear()
    _detection_client.cache_clear()
    _intel_client.cache_clear()
    _rule_store.cache_clear()
    _hotline_directory.cache_clear()
    _LIMITERS.clear()
    get_config.cache_clear()
