"""Structured logging that cannot carry message content.

CHAN-ARCHITECTURE.md §0 forbids logging `text`, `explanation`, or any user
content, and §7.2 gives access logs a 30-day life with no content at all. A
convention is not enough here: one careless f-string in a later change would
silently break invariant I2.

So this module inverts the default. A log record may only carry fields from an
allowlist, and a filter drops any record that smuggles anything else. Reaching
for `logger.info("... %s", text)` fails loudly instead of leaking.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping

LOGGER_NAME = "chan.gateway"

#: The only keys allowed to reach a log sink. Everything here is metadata: an
#: identifier, a count, a class of error, or a duration.
ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "event",
        "request_id",
        "device_id",
        "endpoint",
        "method",
        "status",
        "latency_ms",
        "risk",
        "score",
        "signal_codes",
        "source",
        "input_mode",
        "app_package",
        "truncated",
        "analysis_id",
        "engine_version",
        "rule_bundle_version",
        "bundle_version",
        "l3_provider",
        "error_code",
        "count",
        "cluster_size",
        "kind",
        "verdict",
        "gate",
        "cached",
        "model_version",
        "retained",
        "deleted",
        "reason",
    }
)

#: Field names that must never appear, even if someone adds them to a call site.
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "text",
        "redacted_text",
        "raw_text",
        "content",
        "message",
        "explanation",
        "questions",
        "evidence",
        "signals",
        "prompt",
        "response",
        "prefix",  # I4: repeated prefixes narrow the lookup space
        "value",
        "hash",
        "token",
        "account",
        "phone",
        "url",
        "image",
    }
)


class ContentLeakError(RuntimeError):
    """Raised in tests/dev when a log call carries a forbidden field."""


class SafeExtraFilter(logging.Filter):
    """Drop any record carrying a field outside the allowlist."""

    def __init__(self, *, strict: bool = False) -> None:
        super().__init__()
        self.strict = strict

    def filter(self, record: logging.LogRecord) -> bool:
        fields = getattr(record, "chan_fields", None)
        if fields is None:
            return True
        offending = {
            key
            for key in fields
            if key in FORBIDDEN_FIELDS or key not in ALLOWED_FIELDS
        }
        if offending:
            if self.strict:
                raise ContentLeakError(
                    f"forbidden log fields: {sorted(offending)}"
                )
            safe_fields = {
                key: value for key, value in fields.items() if key not in offending
            }
            safe_fields["error_code"] = "log_fields_dropped"
            setattr(record, "chan_fields", safe_fields)
        return True


class JsonFormatter(logging.Formatter):
    """Render only level, logger, and allowlisted fields. Never the message."""

    def format(self, record: logging.LogRecord) -> str:
        fields: Mapping[str, Any] = getattr(record, "chan_fields", {}) or {}
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
        }
        payload.update(fields)
        if record.exc_info:
            # The class only. A traceback message can contain content.
            payload["error_code"] = record.exc_info[0].__name__ if record.exc_info[0] else "unknown"
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def configure_logging(*, level: int = logging.INFO, strict: bool = False) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger(LOGGER_NAME)
    root.handlers.clear()
    root.addHandler(handler)
    # The filter belongs on the LOGGER, not on the handler. A handler filter only
    # protects that one handler, so anything that attaches another sink — a test,
    # a log shipper, uvicorn — would silently bypass the redaction. On the logger
    # it runs once, before any handler sees the record.
    root.filters.clear()
    root.addFilter(SafeExtraFilter(strict=strict))
    root.setLevel(level)
    root.propagate = False


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def log_event(event: str, **fields: Any) -> None:
    """Emit one structured event. `event` names it; fields must be allowlisted.

    There is deliberately no way to pass a free-form message string.
    """
    logger = get_logger()
    if not logger.isEnabledFor(logging.INFO):
        return
    logger.info("", extra={"chan_fields": {"event": event, **fields}})


def log_error(event: str, error_code: str, **fields: Any) -> None:
    get_logger().warning(
        "", extra={"chan_fields": {"event": event, "error_code": error_code, **fields}}
    )
