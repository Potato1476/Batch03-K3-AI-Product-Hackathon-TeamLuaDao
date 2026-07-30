"""OpenPhish Community connector with a hard license gate.

The public Community Feed terms limit use to personal purposes unless
OpenPhish grants prior written consent. This adapter therefore refuses to run
until an operator explicitly confirms that the project has suitable rights.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from ..models import FetchResult, HashedIndicator, SourceState
from ..normalization import hash_url
from .common import FeedError, bounded_body, source_item_digest

FEED_URL = (
    "https://raw.githubusercontent.com/openphish/public_feed/"
    "refs/heads/main/feed.txt"
)


class OpenPhishConnector:
    source = "openphish"

    def __init__(
        self,
        *,
        user_agent: str,
        license_confirmed: bool,
        maximum_bytes: int = 32 * 1024 * 1024,
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.license_confirmed = license_confirmed
        self.maximum_bytes = maximum_bytes
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def fetch(self, state: SourceState | None = None) -> FetchResult:
        if not self.license_confirmed:
            raise FeedError("openphish_written_permission_required")
        headers = {
            "Accept": "text/plain",
            "User-Agent": self.user_agent,
        }
        if state and state.etag:
            headers["If-None-Match"] = state.etag
        if state and state.last_modified:
            headers["If-Modified-Since"] = state.last_modified
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                transport=self.transport,
            ) as client:
                response = client.get(FEED_URL, headers=headers)
        except httpx.HTTPError as error:
            raise FeedError("openphish_network_error") from error
        if response.status_code == 304:
            return FetchResult(
                source=self.source,
                modified=False,
                indicators=(),
                etag=response.headers.get("etag") or (state.etag if state else None),
                last_modified=response.headers.get("last-modified")
                or (state.last_modified if state else None),
            )
        if response.status_code != 200:
            raise FeedError(f"openphish_http_{response.status_code}")
        try:
            text = bounded_body(response, self.maximum_bytes).decode("utf-8")
        except UnicodeDecodeError as error:
            raise FeedError("openphish_invalid_utf8") from error

        now = datetime.now(UTC)
        indicators: dict[bytes, HashedIndicator] = {}
        invalid = 0
        nonempty = 0
        for line_number, line in enumerate(text.splitlines(), start=1):
            raw = line.strip()
            if not raw:
                continue
            nonempty += 1
            try:
                digest, prefix = hash_url(raw)
            except ValueError:
                invalid += 1
                continue
            indicators[digest] = HashedIndicator(
                kind="url",
                digest=digest,
                prefix=prefix,
                source_item_hash=source_item_digest(
                    self.source, f"{line_number}:{digest.hex()}"
                ),
                first_seen=now,
                last_seen=now,
                confidence="feed_listed",
            )
        if not nonempty:
            raise FeedError("openphish_empty_snapshot")
        if invalid / nonempty > 0.05:
            raise FeedError("openphish_excessive_invalid_rows")
        return FetchResult(
            source=self.source,
            modified=True,
            indicators=tuple(indicators.values()),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )
