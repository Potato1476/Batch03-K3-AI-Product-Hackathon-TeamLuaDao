"""Deterministic, label-preserving Vietnamese typo augmentation for train only."""

from __future__ import annotations

import hashlib
import random
import re
import unicodedata

_PROTECTED = re.compile(
    r"(<[^>]+>|https?://\S+|\bwww\.\S+|\b\d(?:[\d.,:+-]*\d)?\b)",
    flags=re.IGNORECASE,
)
_WORD = re.compile(r"\b[^\W\d_]{4,}\b", flags=re.UNICODE)
_ASCII_NEIGHBOURS = {
    "a": "sqw",
    "b": "vgn",
    "c": "xdfv",
    "d": "serfcx",
    "e": "wrsd",
    "g": "ftyhbv",
    "h": "gyujnb",
    "i": "uojk",
    "k": "ijolm",
    "l": "kop",
    "m": "njk",
    "n": "bhjm",
    "o": "ipkl",
    "p": "ol",
    "q": "wa",
    "r": "etdf",
    "s": "awedxz",
    "t": "ryfg",
    "u": "yihj",
    "v": "cfgb",
    "x": "zsdc",
    "y": "tugh",
}


def without_diacritics(text: str) -> str:
    return (
        "".join(
            character
            for character in unicodedata.normalize("NFD", text)
            if unicodedata.category(character) != "Mn"
        )
        .replace("đ", "d")
        .replace("Đ", "D")
    )


def _on_unprotected(text: str, transform) -> str:
    parts = _PROTECTED.split(text)
    return "".join(
        part if _PROTECTED.fullmatch(part) else transform(part)
        for part in parts
    )


def _eligible_words(text: str) -> list[re.Match[str]]:
    return [
        match
        for match in _WORD.finditer(text)
        if len(without_diacritics(match.group(0))) >= 5
    ]


def _replace_word(text: str, match: re.Match[str], replacement: str) -> str:
    return text[: match.start()] + replacement + text[match.end() :]


def _drop_character(text: str, rng: random.Random) -> str:
    words = _eligible_words(text)
    if not words:
        return text
    match = rng.choice(words)
    word = match.group(0)
    position = rng.randrange(1, len(word) - 1)
    return _replace_word(text, match, word[:position] + word[position + 1 :])


def _swap_characters(text: str, rng: random.Random) -> str:
    words = _eligible_words(text)
    if not words:
        return text
    match = rng.choice(words)
    word = match.group(0)
    position = rng.randrange(1, len(word) - 2)
    swapped = (
        word[:position]
        + word[position + 1]
        + word[position]
        + word[position + 2 :]
    )
    return _replace_word(text, match, swapped)


def _keyboard_substitution(text: str, rng: random.Random) -> str:
    candidates: list[tuple[re.Match[str], int, str]] = []
    for match in _eligible_words(text):
        ascii_word = without_diacritics(match.group(0)).lower()
        for position, character in enumerate(ascii_word):
            neighbours = _ASCII_NEIGHBOURS.get(character)
            if neighbours:
                candidates.append((match, position, neighbours))
    if not candidates:
        return text
    match, position, neighbours = rng.choice(candidates)
    word = match.group(0)
    replacement = rng.choice(neighbours)
    if word[position].isupper():
        replacement = replacement.upper()
    return _replace_word(
        text,
        match,
        word[:position] + replacement + word[position + 1 :],
    )


def _insert_separators(text: str, rng: random.Random) -> str:
    words = _eligible_words(text)
    if not words:
        return text
    match = rng.choice(words)
    separator = rng.choice((".", "-", "_", "*"))
    return _replace_word(text, match, separator.join(match.group(0)))


def _merge_or_expand_space(text: str, rng: random.Random) -> str:
    spaces = [match for match in re.finditer(r" ", text)]
    if not spaces:
        return text
    match = rng.choice(spaces)
    replacement = rng.choice(("", "  ", "   "))
    return text[: match.start()] + replacement + text[match.end() :]


def augment_text(text: str, *, seed: int, variant: int) -> str:
    """Return a reproducible typo variant while preserving PII placeholders."""

    digest = hashlib.sha256(
        f"{seed}:{variant}:{text}".encode("utf-8")
    ).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    transforms = (
        _drop_character,
        _swap_characters,
        _keyboard_substitution,
        _insert_separators,
        _merge_or_expand_space,
    )
    transformed = text
    if variant % 3 != 2:
        transformed = _on_unprotected(transformed, without_diacritics)
    count = 1 + (variant % 2)
    for offset in range(count):
        transform = transforms[(variant + offset + rng.randrange(5)) % len(transforms)]
        transformed = _on_unprotected(
            transformed,
            lambda value, chosen=transform: chosen(value, rng),
        )
    return transformed


def augmented_variants(
    text: str,
    *,
    count: int,
    seed: int,
) -> list[str]:
    variants: list[str] = []
    seen = {text}
    for variant in range(count):
        candidate = augment_text(text, seed=seed, variant=variant)
        if candidate not in seen:
            variants.append(candidate)
            seen.add(candidate)
    return variants
