"""Network and parsing helpers shared by fixed-host feed connectors."""

from __future__ import annotations

import bz2
import hashlib
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


class FeedError(RuntimeError):
    """Safe error carrying a non-content-bearing operational code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def safe_datetime(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    candidate = value.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(candidate)
        except (TypeError, ValueError):
            return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def source_item_digest(source: str, external_id: str) -> bytes:
    return hashlib.sha256(
        f"chan:intel-source:v1:{source}:{external_id}".encode("utf-8")
    ).digest()


def bounded_body(response, maximum_bytes: int) -> bytes:
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > maximum_bytes:
                raise FeedError("feed_too_large")
        except ValueError:
            pass
    body = response.content
    if len(body) > maximum_bytes:
        raise FeedError("feed_too_large")
    return body


def bounded_bz2_decompress(data: bytes, maximum_bytes: int) -> bytes:
    decompressor = bz2.BZ2Decompressor()
    output = bytearray()
    for offset in range(0, len(data), 64 * 1024):
        pending = data[offset : offset + 64 * 1024]
        while pending or not decompressor.needs_input:
            remaining = maximum_bytes - len(output)
            if remaining <= 0:
                raise FeedError("decompressed_feed_too_large")
            try:
                chunk = decompressor.decompress(pending, max_length=remaining + 1)
            except OSError as error:
                raise FeedError("invalid_bzip2_feed") from error
            pending = b""
            if len(chunk) > remaining:
                raise FeedError("decompressed_feed_too_large")
            output.extend(chunk)
            if decompressor.eof:
                return bytes(output)
    if not decompressor.eof:
        raise FeedError("truncated_bzip2_feed")
    return bytes(output)
