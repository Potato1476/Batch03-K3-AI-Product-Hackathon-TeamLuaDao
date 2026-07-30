"""Rule Bundle loading and the L1 local-signal mapping.

The bundle is the single source of truth for L0+L1 (§0). The server does not run
those rules — clients do — but it serves the bundle and owns the mapping from
L1's local-signal vocabulary onto the eight-signal taxonomy, so a client cannot
inject an arbitrary score by naming a signal itself.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from chan_ml.constants import SIGNAL_CODES

#: A single local signal may not contribute more than this, and the total boost
#: is capped as well. L1 runs on a device the user controls; a compromised or
#: modified client must not be able to drive the score on its own.
MAX_SINGLE_BOOST = 0.30
MAX_TOTAL_BOOST = 0.45


@dataclass(frozen=True)
class RuleBundle:
    version: str
    payload: dict[str, Any]
    etag: str
    raw: bytes

    @property
    def local_signal_names(self) -> frozenset[str]:
        return frozenset(self.payload.get("l1", {}).get("local_signals", {}))

    def boosts_for(self, local_signals: tuple[str, ...]) -> dict[str, float]:
        """Map L1 findings onto taxonomy codes with bounded, capped boosts."""
        mapping = self.payload.get("l1", {}).get("local_signals", {})
        boosts: dict[str, float] = {}
        total = 0.0
        for name in dict.fromkeys(local_signals):
            rule = mapping.get(name)
            if not isinstance(rule, dict):
                continue
            code = rule.get("boost_signal")
            if code not in SIGNAL_CODES:
                continue
            boost = min(float(rule.get("boost", 0.0)), MAX_SINGLE_BOOST)
            if boost <= 0:
                continue
            allowed = min(boost, max(0.0, MAX_TOTAL_BOOST - total))
            if allowed <= 0:
                break
            boosts[str(code)] = min(1.0, boosts.get(str(code), 0.0) + allowed)
            total += allowed
        return boosts

    def gate(self) -> Mapping[str, Any]:
        return self.payload.get("l1", {}).get("gate", {})


class RuleBundleStore:
    """Load once, serve from memory, reload when the file changes on disk."""

    def __init__(self, bundle_path: Path) -> None:
        self._path = bundle_path
        self._lock = threading.RLock()
        self._bundle: RuleBundle | None = None
        self._mtime: float | None = None

    def get(self) -> RuleBundle:
        with self._lock:
            try:
                mtime = self._path.stat().st_mtime
            except OSError as error:
                if self._bundle is not None:
                    return self._bundle
                raise FileNotFoundError("rule_bundle_missing") from error
            if self._bundle is None or mtime != self._mtime:
                self._bundle = self._load()
                self._mtime = mtime
            return self._bundle

    def _load(self) -> RuleBundle:
        raw = self._path.read_bytes()
        payload = json.loads(raw)
        version = str(payload.get("bundle_version") or "")
        if not version:
            raise ValueError("rule_bundle_missing_version")
        forbidden = {str(label).lower() for label in payload.get("forbidden_labels", [])}
        labels = {str(key).lower() for key in payload.get("risk_labels", {})}
        if labels & forbidden:
            # I6 belongs in the bundle too: a reassuring label must not be
            # serveable to clients under any circumstances.
            raise ValueError("rule_bundle_declares_forbidden_label")
        return RuleBundle(
            version=version,
            payload=payload,
            etag=hashlib.sha256(raw).hexdigest()[:32],
            raw=raw,
        )
