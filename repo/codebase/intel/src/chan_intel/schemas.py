"""External contracts for k-anonymous lookup and hash-only reporting."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .normalization import parse_sha256_hex

IndicatorKind = Literal["account", "phone", "url"]
ReportStatus = Literal["quarantined", "approved", "rejected", "expired"]
Confidence = Literal[
    "feed_listed",
    "community_reviewed",
    "verified",
    "partner_verified",
]


class LookupItem(BaseModel):
    suffix: str
    report_count: int
    first_seen: datetime
    last_seen: datetime
    confidence: Confidence


class LookupResponse(BaseModel):
    prefix: str
    items: list[LookupItem]
    message: Literal["matched_locally_only"] = "matched_locally_only"


class IndicatorReportSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: IndicatorKind
    indicator_hash: str = Field(min_length=64, max_length=64)
    reporter_hash: str = Field(min_length=64, max_length=64)
    evidence_hash: str | None = Field(default=None, min_length=64, max_length=64)
    consented: Literal[True]

    @field_validator("indicator_hash", "reporter_hash", "evidence_hash")
    @classmethod
    def validate_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parse_sha256_hex(value)
        return value


class IndicatorReportBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[IndicatorReportSubmission] = Field(min_length=1, max_length=100)


class IndicatorReportReceipt(BaseModel):
    id: str
    status: ReportStatus
    duplicate: bool


class IndicatorReportBatchResponse(BaseModel):
    accepted: int
    items: list[IndicatorReportReceipt]


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: Literal["approve", "reject"]
    review_reason: str = Field(
        min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$"
    )


class ReviewResponse(BaseModel):
    id: str
    status: ReportStatus
    independent_approved_reports: int
    activated: bool


class SourceStatusResponse(BaseModel):
    name: str
    enabled: bool
    rights_basis: str
    update_interval_minutes: int | None
    last_success_at: datetime | None
    last_record_count: int
    last_error_code: str | None
