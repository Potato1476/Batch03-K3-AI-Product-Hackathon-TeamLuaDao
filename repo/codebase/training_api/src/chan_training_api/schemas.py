"""Public request/response contracts without content-bearing responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from chan_ml.policy import aggregate_risk

from .privacy import validate_l2_redacted

Risk = Literal["high", "medium", "unknown"]
RightsBasis = Literal[
    "explicit_consent",
    "licensed_threat_intel",
    "synthetic",
]
ScenarioStatus = Literal["quarantined", "approved", "rejected", "expired"]
RunStatus = Literal["queued", "running", "promoted", "rejected", "failed"]


class ScenarioSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    redacted_text: str = Field(min_length=8, max_length=4_000)
    signals: list[
        Literal[
            "mao_danh_tham_quyen",
            "yeu_cau_bi_mat",
            "ap_luc_thoi_gian",
            "tk_ca_nhan",
            "cai_app_ngoai",
            "loi_ich_bat_thuong",
            "chuyen_kenh",
            "yeu_cau_otp",
        ]
    ] = Field(default_factory=list)
    risk: Risk
    is_phishing: bool
    origin: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    source_ref: str | None = Field(default=None, max_length=512)
    rights_basis: RightsBasis
    consented: bool = False
    redaction_confirmed: Literal[True]

    @field_validator("redacted_text")
    @classmethod
    def validate_redaction(cls, value: str) -> str:
        return validate_l2_redacted(value)

    @model_validator(mode="after")
    def validate_training_contract(self) -> "ScenarioSubmission":
        if len(set(self.signals)) != len(self.signals):
            raise ValueError("duplicate_signal_codes")
        if self.rights_basis == "explicit_consent" and not self.consented:
            raise ValueError("explicit_consent_requires_consented_true")
        if self.rights_basis != "explicit_consent" and self.consented:
            raise ValueError("consented_only_valid_for_explicit_consent")
        if not self.is_phishing and self.signals:
            raise ValueError("non_phishing_control_must_have_no_signals")
        expected = aggregate_risk({code: 1.0 for code in self.signals}).risk
        if self.risk != expected:
            raise ValueError("risk_does_not_match_l4_policy")
        return self


class ScenarioBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ScenarioSubmission] = Field(min_length=1, max_length=100)


class ScenarioReceipt(BaseModel):
    id: str
    status: ScenarioStatus
    duplicate: bool


class ScenarioBatchResponse(BaseModel):
    accepted: int
    items: list[ScenarioReceipt]


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: Literal["approve", "reject"]
    review_reason: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")


class ReviewResponse(BaseModel):
    id: str
    status: ScenarioStatus


class RetrainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    idempotency_key: str = Field(
        min_length=8, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$"
    )


class TrainingRunResponse(BaseModel):
    id: str
    status: RunStatus
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    approved_scenario_count: int | None = None
    candidate_version: str | None = None
    metrics: dict[str, object] | None = None
    promotion_reasons: list[str] = Field(default_factory=list)
    error_code: str | None = None


class ActiveModelResponse(BaseModel):
    version: str
    artifact_uri: str
    artifact_sha256: str
    metrics: dict[str, object]
    promoted_at: datetime
