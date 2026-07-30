"""Pydantic contract for the public /v1 API — CHAN-ARCHITECTURE.md §7.

Every model uses `extra="forbid"`: an unexpected field is a client bug or an
attack, and silently ignoring it hides both.

Note what is deliberately absent: no request model accepts a raw account number,
phone number, or URL for lookup. I4 says the server must never learn what a user
looked up, so the only accepted lookup input is a 5-hex prefix. That is enforced
by the type, not by a comment.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chan_ml.constants import SIGNAL_CODES

Risk = Literal["high", "medium", "unknown"]
Source = Literal["web", "android", "zalo_oa"]
InputMode = Literal["manual", "share", "notification", "sms_scan"]
Platform = Literal["web", "android", "zalo_oa"]
SignalCode = Literal[
    "mao_danh_tham_quyen",
    "yeu_cau_bi_mat",
    "ap_luc_thoi_gian",
    "tk_ca_nhan",
    "cai_app_ngoai",
    "loi_ich_bat_thuong",
    "chuyen_kenh",
    "yeu_cau_otp",
]
BlocklistKind = Literal["account", "phone", "url"]
Verdict = Literal["correct", "false_positive", "false_negative"]
Action = Literal["report", "share_to_guardian", "lookup_account"]

#: I4: exactly five lowercase hex characters, nothing else.
HashPrefix = Annotated[str, Field(pattern=r"^[0-9a-f]{5}$")]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

assert set(SIGNAL_CODES) == set(SignalCode.__args__), (
    "SignalCode must mirror chan_ml.constants.SIGNAL_CODES"
)


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- devices ----------------------------------------------------------------


class DeviceTokenRequest(Base):
    platform: Platform
    push_token: str | None = Field(default=None, max_length=512)


class DeviceTokenResponse(Base):
    device_id: str
    token: str
    expires_at: str
    note: str = "Token chỉ được trả về một lần. Lưu lại trên thiết bị."


class DeviceRotateRequest(Base):
    push_token: str | None = Field(default=None, max_length=512)


# --- analyze ----------------------------------------------------------------


class AnalyzeRequest(Base):
    text: str = Field(min_length=1, max_length=4_000)
    source: Source
    input_mode: InputMode
    app_package: str | None = Field(default=None, max_length=128)
    local_signals: list[str] = Field(default_factory=list, max_length=16)
    truncated: bool = False
    locale: str = Field(default="vi-VN", max_length=16)

    @field_validator("local_signals")
    @classmethod
    def validate_local_signals(cls, value: list[str]) -> list[str]:
        # L1 vocabulary, not the eight-signal taxonomy. Names are checked
        # against the Rule Bundle at request time; here we only bound the shape.
        for item in value:
            if not item or len(item) > 64 or not item.replace("_", "").isalnum():
                raise ValueError("invalid_local_signal")
        return value


class SignalOut(Base):
    code: SignalCode
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(default="", max_length=240)


class HotlineOut(Base):
    name: str
    number: str


class AnalyzeResponse(Base):
    analysis_id: str
    risk: Risk
    score: float = Field(ge=0.0, le=1.0)
    signals: list[SignalOut]
    explanation: str
    questions: list[str]
    verified_hotline: HotlineOut | None = None
    actions: list[Action]
    engine_version: str
    rule_bundle_version: str


# --- lookup -----------------------------------------------------------------


class BlocklistHit(Base):
    hash: Sha256Hex
    report_cnt: int
    first_seen: str
    last_seen: str
    origin: str


class LookupResponse(Base):
    prefix: HashPrefix
    kind: BlocklistKind
    hashes: list[BlocklistHit]
    cluster_size: int
    bundle_version: str
    #: Shown when the client finds no match. Never says "safe" (I6).
    no_match_message: str = "Chưa có báo cáo về số này."


# --- report -----------------------------------------------------------------


class ReportRequest(Base):
    kind: BlocklistKind
    #: The client hashes before sending: the server has no use for the value.
    value_sha256: Sha256Hex
    analysis_id: str | None = Field(default=None, max_length=64)


class ReportResponse(Base):
    kind: BlocklistKind
    report_cnt: int
    accepted: bool = True


# --- feedback ---------------------------------------------------------------


class FeedbackRequest(Base):
    analysis_id: str = Field(min_length=3, max_length=64)
    verdict: Verdict
    #: Opt-in contribution to the training corpus. Off unless the user acts.
    contribute: bool = False
    redacted_text: str | None = Field(default=None, min_length=8, max_length=4_000)
    signals: list[SignalCode] = Field(default_factory=list)

    @field_validator("signals")
    @classmethod
    def validate_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("duplicate_signal_codes")
        return value


class FeedbackResponse(Base):
    recorded: bool
    contributed: bool = False


# --- ocr --------------------------------------------------------------------


class OcrResponse(Base):
    text: str
    provider: str
    #: The client calls /v1/analyze itself (§7); the server never chains.
    next_step: str = "POST /v1/analyze"


# --- errors -----------------------------------------------------------------


class ErrorResponse(Base):
    detail: str
