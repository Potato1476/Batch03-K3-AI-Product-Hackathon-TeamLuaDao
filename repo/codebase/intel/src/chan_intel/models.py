"""Internal threat-intelligence records that never contain raw indicators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HashedIndicator:
    kind: str
    digest: bytes
    prefix: str
    source_item_hash: bytes
    first_seen: datetime
    last_seen: datetime
    confidence: str


@dataclass(frozen=True)
class SourceState:
    name: str
    etag: str | None
    last_modified: str | None
    last_success_at: datetime | None
    last_record_count: int


@dataclass(frozen=True)
class FetchResult:
    source: str
    modified: bool
    indicators: tuple[HashedIndicator, ...]
    etag: str | None
    last_modified: str | None


@dataclass(frozen=True)
class LookupRecord:
    digest_hex: str
    report_count: int
    first_seen: datetime
    last_seen: datetime
    confidence: str


@dataclass(frozen=True)
class ReportReceiptRecord:
    id: str
    status: str
    duplicate: bool


@dataclass(frozen=True)
class SourceStatusRecord:
    name: str
    enabled: bool
    rights_basis: str
    update_interval_minutes: int | None
    last_success_at: datetime | None
    last_record_count: int
    last_error_code: str | None
