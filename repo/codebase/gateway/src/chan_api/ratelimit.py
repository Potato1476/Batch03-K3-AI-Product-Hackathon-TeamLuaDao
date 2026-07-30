"""Fixed-window rate limiting per device token and per IP.

§7.3 asks for two things: ordinary abuse protection, and specifically detecting
and blocking use of /analyze as a free LLM proxy. Both limits apply, and the
tighter of the two wins.

Redis is the intended backend. When it is absent the limiter falls back to a
Postgres counter table, and finally to an in-process dict so tests and a local
demo need no infrastructure. The fallback is per-process and therefore weaker;
that is stated rather than hidden.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Protocol


class RateLimitBackend(Protocol):
    def hit(self, bucket: str, limit: int, window_seconds: int) -> bool:
        """Return True when this hit exceeds the limit."""
        ...


@dataclass
class InProcessBackend:
    """Per-process counters. Correct for one worker, approximate for many."""

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, tuple[int, float]] = {}

    def hit(self, bucket: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            hits, expires_at = self._counters.get(bucket, (0, 0.0))
            if expires_at < now:
                hits, expires_at = 0, now + window_seconds
            hits += 1
            self._counters[bucket] = (hits, expires_at)
            if len(self._counters) > 10_000:
                self._counters = {
                    key: value
                    for key, value in self._counters.items()
                    if value[1] >= now
                }
        return hits > limit


class RedisBackend:
    """INCR with an expiry set on first hit — one round trip in the common case."""

    def __init__(self, url: str) -> None:
        import redis  # imported lazily: an optional extra

        self._client = redis.Redis.from_url(url, socket_timeout=0.25)

    def hit(self, bucket: str, limit: int, window_seconds: int) -> bool:
        pipeline = self._client.pipeline()
        pipeline.incr(bucket, 1)
        pipeline.expire(bucket, window_seconds, nx=True)
        hits = int(pipeline.execute()[0])
        return hits > limit


class PostgresBackend:
    def __init__(self, repository) -> None:  # noqa: ANN001 - GatewayRepository
        self._repository = repository

    def hit(self, bucket: str, limit: int, window_seconds: int) -> bool:
        return self._repository.hit_rate_limit(bucket, limit, window_seconds)


class RateLimiter:
    def __init__(self, backend: RateLimitBackend) -> None:
        self._backend = backend

    def check(
        self, *, scope: str, identity: str, limit: int, window_seconds: int = 60
    ) -> bool:
        """Return True when the caller is within budget."""
        window = int(time.time()) // window_seconds
        bucket = f"chan:rl:{scope}:{identity}:{window}"
        return not self._backend.hit(bucket, limit, window_seconds)


def build_backend(redis_url: str, repository=None) -> RateLimitBackend:  # noqa: ANN001
    if redis_url:
        try:
            return RedisBackend(redis_url)
        except Exception:  # pragma: no cover - depends on deployment
            # A limiter that cannot reach Redis must degrade, not fail requests.
            pass
    if repository is not None:
        return PostgresBackend(repository)
    return InProcessBackend()
