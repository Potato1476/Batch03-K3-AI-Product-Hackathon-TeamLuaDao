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
    local_boosts: dict[str, float] = Field(default_factory=dict)
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

    @field_validator("local_boosts")
    @classmethod
    def validate_local_boosts(cls, value: dict[str, float]) -> dict[str, float]:
        from chan_ml.constants import SIGNAL_CODES

        if set(value) - set(SIGNAL_CODES):
            raise ValueError("invalid_local_boost_code")
        if any(amount < 0.0 or amount > 0.45 for amount in value.values()):
            raise ValueError("invalid_local_boost_value")
        if sum(value.values()) > 0.45 + 1e-9:
            raise ValueError("local_boost_total_exceeded")
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


# --- L5: conversation-level analysis ----------------------------------------


class ThreadMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sender: Literal["contact", "user"]
    text: str = Field(min_length=1, max_length=2_000)


class AnalyzeThreadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ThreadMessageIn] = Field(min_length=2, max_length=60)
    contact_name: str = Field(default="", max_length=80)
    source: InputSource
    locale: Literal["vi-VN"] = "vi-VN"
    rule_bundle_version: str | None = Field(default=None, max_length=64)


class ThreadSignalResult(BaseModel):
    code: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(max_length=240)


class AnalyzeThreadResponse(BaseModel):
    analysis_id: str
    risk: Risk
    thread_signals: list[ThreadSignalResult]
    explanation: str
    questions: list[str]
    actions: list[str]
    baseline_messages: int
    style_distance: float | None = None
    insufficient_history: bool = False
    #: Per-message verdict for the message that asked for money, when there is one.
    ask_message_index: int | None = None
    ask_message_risk: Risk | None = None
    ask_message_signals: list[SignalResult] = []
    engine_version: str
    rule_bundle_version: str | None = None
