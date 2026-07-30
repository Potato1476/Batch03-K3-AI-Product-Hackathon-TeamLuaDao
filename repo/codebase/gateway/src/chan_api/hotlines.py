"""Resolve `verified_hotline` for the analyze response.

This field is the practical countermeasure to an impersonation scenario: rather
than trusting the number that called, the user is handed a number they can dial
themselves. It is only offered when the message actually claims an authority —
attaching a random hotline to every result trains people to ignore it.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path

from chan_ml.normalize import normalize_for_model


@dataclass(frozen=True)
class Hotline:
    name: str
    number: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "number": self.number}


class HotlineDirectory:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._entries: list[tuple[Hotline, tuple[str, ...]]] | None = None
        self._default: Hotline | None = None

    def _ensure_loaded(self) -> None:
        with self._lock:
            if self._entries is not None:
                return
            try:
                payload = json.loads(self._path.read_bytes())
            except (OSError, json.JSONDecodeError):
                self._entries = []
                self._default = None
                return
            self._entries = [
                (
                    Hotline(
                        name=str(entry.get("name", "")),
                        number=str(entry.get("number", "")),
                    ),
                    tuple(
                        normalize_for_model(str(keyword))
                        for keyword in entry.get("keywords", [])
                    ),
                )
                for entry in payload.get("entries", [])
            ]
            default = payload.get("default")
            self._default = (
                Hotline(
                    name=str(default.get("name", "")),
                    number=str(default.get("number", "")),
                )
                if isinstance(default, dict)
                else None
            )

    def resolve(self, redacted_text: str, *, signal_codes: frozenset[str]) -> Hotline | None:
        """Match on the redacted text; only when an authority is being claimed."""
        if "mao_danh_tham_quyen" not in signal_codes:
            return None
        self._ensure_loaded()
        haystack = normalize_for_model(redacted_text)
        best: tuple[int, Hotline] | None = None
        for hotline, keywords in self._entries or []:
            score = sum(1 for keyword in keywords if keyword and keyword in haystack)
            if score and (best is None or score > best[0]):
                best = (score, hotline)
        if best is not None:
            return best[1]
        return self._default
