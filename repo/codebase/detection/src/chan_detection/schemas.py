"""Public, versioned request and response contract."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

InputSource = Literal["web", "android", "zalo_oa", "internal"]
InputMode = Literal[
    "manual",
    "upload",
    "share",
    "share_target",
    "notification",
    "sms_scan",
    "sms",
    "forward",
]
Risk = Literal["high", "medium", "unknown"]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=8, max_length=4_000)
    source: InputSource
    input_mode: InputMode
    app_package: str | None = Field(default=None, max_length=255)
    local_signals: list[str] = Field(default_factory=list, max_length=32)
    truncated: bool = False
    locale: Literal["vi-VN"] = "vi-VN"
    rule_bundle_version: str | None = Field(default=None, max_length=64)

    @field_validator("text")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(character in value for character in ("\x00", "\r")):
            raise ValueError("unsupported_control_character")
        return value

    @field_validator("local_signals")
    @classmethod
    def validate_local_signals(cls, value: list[str]) -> list[str]:
        if any(not item or len(item) > 64 for item in value):
            raise ValueError("invalid_local_signal")
        return value


class SignalResult(BaseModel):
    code: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(max_length=240)


class AnalyzeResponse(BaseModel):
    analysis_id: str
    model_version: str
    engine_version: str
    risk: Risk
    score: float = Field(ge=0.0, le=1.0)
    scam_confidence: float = Field(ge=0.0, le=1.0)
    signals: list[SignalResult]
    explanation: str
    questions: list[str]
    actions: list[str]
    verified_hotline: None = None
    rule_bundle_version: str | None = None
    truncated: bool
    blocklist_match: bool = False
