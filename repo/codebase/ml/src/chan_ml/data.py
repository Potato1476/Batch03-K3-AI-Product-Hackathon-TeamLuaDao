"""Streaming dataset I/O with privacy and schema validation."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Iterable, TextIO

from .schema import DatasetRecord


def _open_input(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def read_records(
    path: Path, *, split: str | None = None, limit: int | None = None
) -> Iterable[DatasetRecord]:
    emitted = 0
    with _open_input(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = DatasetRecord.from_dict(json.loads(line))
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            if split is not None and record.split != split:
                continue
            yield record
            emitted += 1
            if limit is not None and emitted >= limit:
                return
