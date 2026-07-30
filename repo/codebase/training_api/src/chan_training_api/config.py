"""Environment-only configuration; secrets never enter source control."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from chan_ml.continuous import PromotionPolicy


def _parse_api_keys(value: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for entry in value.split(","):
        if not entry.strip():
            continue
        key_id, separator, secret = entry.partition("=")
        if not separator or not key_id.strip() or len(secret.strip()) < 16:
            raise ValueError(
                "CHAN_TRAINING_API_KEYS entries must be key-id=secret "
                "with secrets of at least 16 characters"
            )
        keys[key_id.strip()] = secret.strip()
    return keys


@dataclass(frozen=True)
class AppConfig:
    database_url: str
    api_keys: dict[str, str]
    artifact_root: Path
    base_dataset_path: Path
    golden_dataset_path: Path
    promotion_policy: PromotionPolicy
    live_example_repeat: int = 10

    @classmethod
    def from_environment(cls) -> "AppConfig":
        return cls(
            database_url=os.environ.get("CHAN_DATABASE_URL", ""),
            api_keys=_parse_api_keys(os.environ.get("CHAN_TRAINING_API_KEYS", "")),
            artifact_root=Path(
                os.environ.get(
                    "CHAN_MODEL_ARTIFACT_ROOT", "/var/lib/chan/model-registry"
                )
            ),
            base_dataset_path=Path(
                os.environ.get(
                    "CHAN_BASE_DATASET_PATH",
                    "/var/lib/chan/datasets/chan-synthetic.jsonl.gz",
                )
            ),
            golden_dataset_path=Path(
                os.environ.get(
                    "CHAN_GOLDEN_DATASET_PATH",
                    "/var/lib/chan/datasets/frozen-golden.jsonl.gz",
                )
            ),
            promotion_policy=PromotionPolicy(
                minimum_golden_records=int(
                    os.environ.get("CHAN_MINIMUM_GOLDEN_RECORDS", "130")
                ),
                minimum_phishing_recall=float(
                    os.environ.get("CHAN_MINIMUM_PHISHING_RECALL", "0.90")
                ),
                maximum_false_positive_rate=float(
                    os.environ.get("CHAN_MAXIMUM_FALSE_POSITIVE_RATE", "0.15")
                ),
                maximum_recall_regression=float(
                    os.environ.get("CHAN_MAXIMUM_RECALL_REGRESSION", "0.02")
                ),
                maximum_false_positive_regression=float(
                    os.environ.get("CHAN_MAXIMUM_FALSE_POSITIVE_REGRESSION", "0.02")
                ),
                minimum_scenario_recall=float(
                    os.environ.get("CHAN_MINIMUM_SCENARIO_RECALL", "0.75")
                ),
                minimum_scenario_records=int(
                    os.environ.get("CHAN_MINIMUM_SCENARIO_RECORDS", "3")
                ),
                minimum_scenario_families=int(
                    os.environ.get("CHAN_MINIMUM_SCENARIO_FAMILIES", "20")
                ),
                maximum_scenario_false_positive_rate=float(
                    os.environ.get("CHAN_MAXIMUM_SCENARIO_FALSE_POSITIVE_RATE", "0.15")
                ),
            ),
            live_example_repeat=max(
                1,
                min(
                    20,
                    int(os.environ.get("CHAN_LIVE_EXAMPLE_REPEAT", "10")),
                ),
            ),
        )


@lru_cache
def get_config() -> AppConfig:
    return AppConfig.from_environment()
