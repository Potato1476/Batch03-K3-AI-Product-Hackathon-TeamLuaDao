"""PhishTank verified-online feed connector.

PhishTank's API data is explicitly available for commercial use. The adapter
uses the documented bulk database, conditional requests, and a descriptive
User-Agent. Raw URLs exist only while parsing and are immediately normalized
and hashed.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

import httpx

from ..models import FetchResult, HashedIndicator, SourceState
from ..normalization import hash_url
from .common import (
    FeedError,
    bounded_body,
    bounded_bz2_decompress,
    safe_datetime,
    source_item_digest,
)

BASE_URL = "https://data.phishtank.com/data"


class PhishTankConnector:
    source = "phishtank"

    def __init__(
        self,
        *,
        user_agent: str,
        app_key: str | None = None,
        maximum_bytes: int = 32 * 1024 * 1024,
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not user_agent:
            raise ValueError("descriptive_user_agent_required")
        self.user_agent = user_agent
        self.app_key = app_key
        self.maximum_bytes = maximum_bytes
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @property
    def feed_url(self) -> str:
        if self.app_key:
            return f"{BASE_URL}/{self.app_key}/online-valid.csv.bz2"
        return f"{BASE_URL}/online-valid.csv.bz2"

    def fetch(self, state: SourceState | None = None) -> FetchResult:
        headers = {
            "Accept": "application/x-bzip2, application/octet-stream",
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
                response = client.get(self.feed_url, headers=headers)
        except httpx.HTTPError as error:
            raise FeedError("phishtank_network_error") from error

        if response.status_code == 304:
            return FetchResult(
                source=self.source,
                modified=False,
                indicators=(),
                etag=response.headers.get("etag") or (state.etag if state else None),
                last_modified=response.headers.get("last-modified")
                or (state.last_modified if state else None),
            )
        if response.status_code == 509:
            raise FeedError("phishtank_rate_limited")
        if response.status_code != 200:
            raise FeedError(f"phishtank_http_{response.status_code}")

        compressed = bounded_body(response, self.maximum_bytes)
        try:
            decoded = bounded_bz2_decompress(
                compressed, self.maximum_bytes * 8
            ).decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise FeedError("phishtank_invalid_bzip2_csv") from error

        now = datetime.now(UTC)
        reader = csv.DictReader(io.StringIO(decoded))
        required = {
            "phish_id",
            "url",
            "submission_time",
            "verification_time",
            "verified",
            "online",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise FeedError("phishtank_schema_changed")

        deduplicated: dict[bytes, HashedIndicator] = {}
        invalid_rows = 0
        total_rows = 0
        for row in reader:
            total_rows += 1
            if row.get("verified", "").lower() != "yes":
                continue
            if row.get("online", "").lower() != "yes":
                continue
            try:
                digest, prefix = hash_url(row["url"])
            except (KeyError, ValueError):
                invalid_rows += 1
                continue
            first_seen = safe_datetime(row.get("submission_time"), now)
            deduplicated[digest] = HashedIndicator(
                kind="url",
                digest=digest,
                prefix=prefix,
                source_item_hash=source_item_digest(
                    self.source, row.get("phish_id", digest.hex())
                ),
                first_seen=first_seen,
                last_seen=now,
                confidence="verified",
            )

        if total_rows == 0:
            raise FeedError("phishtank_empty_snapshot")
        if invalid_rows / total_rows > 0.05:
            raise FeedError("phishtank_excessive_invalid_rows")

        return FetchResult(
            source=self.source,
            modified=True,
            indicators=tuple(deduplicated.values()),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )
