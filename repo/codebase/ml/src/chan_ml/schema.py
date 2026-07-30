"""Strict JSONL schema for synthetic and consented training examples."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .constants import GENERATOR_VERSION, RISK_VALUES, SIGNAL_CODES


@dataclass(frozen=True)
class DatasetRecord:
    id: str
    text: str
    risk: str
    signals: dict[str, float]
    is_phishing: bool
    scenario: str
    template_id: str
    source: str
    input_mode: str
    truncated: bool
    split: str
    synthetic: bool = True
    consented: bool = False
    rights_basis: str = "synthetic"
    generator_version: str = GENERATOR_VERSION

    def validate(self) -> None:
        if not self.id or not self.text.strip():
            raise ValueError("id and text are required")
        if self.risk not in RISK_VALUES:
            raise ValueError(f"invalid risk: {self.risk}")
        if self.split not in {"train", "validation", "test"}:
            raise ValueError(f"invalid split: {self.split}")
        if self.source not in {"web", "android", "zalo_oa"}:
            raise ValueError(f"invalid source: {self.source}")
        if self.input_mode not in {
            "manual",
            "share",
            "notification",
            "sms_scan",
        }:
            raise ValueError(f"invalid input_mode: {self.input_mode}")
        unknown = set(self.signals) - set(SIGNAL_CODES)
        if unknown:
            raise ValueError(f"unknown signals: {sorted(unknown)}")
        for code, confidence in self.signals.items():
            if not 0.0 <= float(confidence) <= 1.0:
                raise ValueError(f"{code} confidence must be between 0 and 1")
        if self.rights_basis not in {
            "synthetic",
            "explicit_consent",
            "licensed_threat_intel",
        }:
            raise ValueError(f"invalid rights_basis: {self.rights_basis}")
        if self.synthetic and self.rights_basis != "synthetic":
            raise ValueError("synthetic records must use rights_basis=synthetic")
        if not self.synthetic and self.rights_basis == "synthetic":
            raise ValueError("non-synthetic records require a non-synthetic rights basis")
        if self.rights_basis == "explicit_consent" and not self.consented:
            raise ValueError("explicit_consent records require consented=true")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DatasetRecord":
        record = cls(**value)
        record.validate()
        return record
