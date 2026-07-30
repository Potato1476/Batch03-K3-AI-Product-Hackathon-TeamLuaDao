"""Python parity helper for the shared Web/Android L0/L1 rule bundle."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata

from .constants import SIGNAL_CODES

MAX_SINGLE_BOOST = 0.30
MAX_TOTAL_BOOST = 0.45


def _strip_diacritics(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d").replace("Đ", "D")


def _join_separated_runs(text: str, separators: list[str]) -> str:
    compact = [character for character in separators if character != " "]
    if not compact:
        return text
    characters = "".join(re.escape(character) for character in compact)
    runs = re.compile(
        rf"(?<![^\W_])(?:[^\W_][{characters}])+[^\W_](?![^\W_])",
        flags=re.UNICODE,
    )
    separators_pattern = re.compile(f"[{characters}]")
    return runs.sub(
        lambda match: separators_pattern.sub("", match.group(0)),
        text,
    )


def normalize_for_rules(text: str, bundle: dict) -> str:
    l0 = bundle["l0"]
    normalized = unicodedata.normalize(str(l0["unicode_form"]), text)
    for character in l0.get("strip_invisible", []):
        normalized = normalized.replace(str(character), "")
    if l0.get("lowercase"):
        normalized = normalized.lower()
    if l0.get("collapse_whitespace"):
        normalized = " ".join(normalized.split())
    normalized = _join_separated_runs(
        normalized,
        [str(item) for item in l0.get("separator_characters", [])],
    )
    if l0.get("strip_diacritics_for_matching"):
        normalized = _strip_diacritics(normalized)
    teencode = l0.get("teencode", {})
    return " ".join(str(teencode.get(word, word)) for word in normalized.split(" "))


def _compile_pattern(source: str) -> re.Pattern[str] | None:
    if not source or source == "__see_otp_block__":
        return None
    return re.compile(_strip_diacritics(source))


def _matches_any(text: str, sources: list[str]) -> bool:
    return any(
        compiled.search(text)
        for source in sources
        if (compiled := _compile_pattern(source)) is not None
    )


@dataclass(frozen=True)
class LocalRuleResult:
    normalized: str
    otp_blocked: bool
    local_signals: tuple[str, ...]
    signal_boosts: dict[str, float]


def evaluate_local_rules(text: str, bundle: dict) -> LocalRuleResult:
    normalized = normalize_for_rules(text, bundle)
    l1 = bundle["l1"]
    otp_blocked = _matches_any(
        normalized,
        [str(item) for item in l1["otp_block"]["patterns"]],
    )
    matched: list[str] = []
    boosts: dict[str, float] = {}
    total = 0.0
    for name, rule in l1["local_signals"].items():
        if not _matches_any(
            normalized,
            [str(item) for item in rule.get("patterns", [])],
        ):
            continue
        matched.append(str(name))
        code = rule.get("boost_signal")
        if code not in SIGNAL_CODES:
            continue
        amount = min(float(rule.get("boost", 0.0)), MAX_SINGLE_BOOST)
        allowed = min(amount, max(0.0, MAX_TOTAL_BOOST - total))
        if allowed <= 0:
            continue
        boosts[str(code)] = boosts.get(str(code), 0.0) + allowed
        total += allowed
    return LocalRuleResult(
        normalized=normalized,
        otp_blocked=otp_blocked,
        local_signals=tuple(matched),
        signal_boosts=boosts,
    )


def load_rule_bundle(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
