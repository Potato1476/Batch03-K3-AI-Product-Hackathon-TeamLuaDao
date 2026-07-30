"""§0: no user content may reach a log, ever.

This is the invariant most likely to be broken by accident, because logging a
variable is a one-line change that looks harmless. So the check is mechanical:
run a full request and assert that nothing recognisable from the message appears
in any emitted record.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

from chan_api.logging_safe import (
    ALLOWED_FIELDS,
    FORBIDDEN_FIELDS,
    LOGGER_NAME,
    ContentLeakError,
    JsonFormatter,
    SafeExtraFilter,
    configure_logging,
    log_event,
)

from conftest import OTP_TEXT, SCAM_TEXT

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "chan_api"


class Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.rendered: list[str] = []
        self.setFormatter(JsonFormatter())

    def emit(self, record: logging.LogRecord) -> None:
        self.rendered.append(self.format(record))


@pytest.fixture
def capture() -> Capture:
    """Attach an extra sink without touching the logger's own filters.

    This mirrors what a log shipper would do in production, and is exactly the
    case a handler-level filter would fail to cover.
    """
    configure_logging()
    handler = Capture()
    logger = logging.getLogger(LOGGER_NAME)
    previous_handlers = list(logger.handlers)
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    yield handler
    logger.handlers = previous_handlers


def _analyze(client, auth, text):  # noqa: ANN001, ANN202
    return client.post(
        "/v1/analyze",
        json={
            "text": text,
            "source": "web",
            "input_mode": "manual",
            "truncated": False,
            "locale": "vi-VN",
        },
        headers=auth,
    )


def test_a_full_analyze_logs_no_message_content(client, auth, capture) -> None:
    response = _analyze(client, auth, SCAM_TEXT)
    assert response.status_code == 200
    logged = "\n".join(capture.rendered)
    assert logged, "expected the request to log something"

    for fragment in (
        "can bo thue",
        "19001234567890",
        "20 trieu",
        "khong noi voi ai",
        "gia dinh",
    ):
        assert fragment not in logged, f"{fragment!r} reached the log"

    body = response.json()
    assert body["explanation"] not in logged
    for signal in body["signals"]:
        if signal["evidence"]:
            assert signal["evidence"] not in logged


def test_the_otp_path_logs_no_digits(client, auth, capture) -> None:
    _analyze(client, auth, OTP_TEXT)
    assert "938271" not in "\n".join(capture.rendered)


def test_lookup_never_logs_the_prefix(client, auth, capture) -> None:
    """Logging prefixes repeatedly would narrow the lookup space over time (I4)."""
    client.get("/v1/lookup/account?prefix=deadb", headers=auth)
    logged = "\n".join(capture.rendered)
    assert "deadb" not in logged
    # The query string must not be logged either.
    assert "prefix=" not in logged


def test_forbidden_field_is_dropped_by_default(capture) -> None:
    log_event("test", text="secret content", risk="high")
    logged = capture.rendered[-1]
    assert "secret content" not in logged
    assert '"risk": "high"' in logged
    assert "log_fields_dropped" in logged


def test_forbidden_field_raises_in_strict_mode() -> None:
    record = logging.LogRecord(
        LOGGER_NAME, logging.INFO, __file__, 1, "", None, None
    )
    record.chan_fields = {"event": "test", "explanation": "leak"}  # type: ignore[attr-defined]
    with pytest.raises(ContentLeakError, match="explanation"):
        SafeExtraFilter(strict=True).filter(record)


def test_the_formatter_ignores_the_message_string(capture) -> None:
    """A free-form message is the usual leak path, so it is never rendered."""
    logging.getLogger(LOGGER_NAME).info("this message body contains user text")
    assert "user text" not in capture.rendered[-1]


def test_allowlist_and_denylist_do_not_overlap() -> None:
    assert not (ALLOWED_FIELDS & FORBIDDEN_FIELDS)


#: Operator CLIs print aggregate counts to stdout by design (an import summary is
#: useless without them) and never touch message content. Every other module —
#: routers, pipeline, L3 — must go through log_event, which enforces the
#: allowlist. Keep this list as short as it is.
_STDOUT_ALLOWED = {"ingest.py", "retention.py"}


def test_no_module_logs_content_directly() -> None:
    """Static guard: request-path code must not format its own log output.

    An f-string is how content leaks: `logger.info(f"analyzing {text}")` looks
    harmless and defeats every runtime protection in logging_safe.
    """
    offenders: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        if path.name == "logging_safe.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("print(") and path.name in _STDOUT_ALLOWED:
                continue
            if not stripped.startswith(("logger.", "logging.", "LOGGER.", "print(")):
                continue
            if 'f"' in stripped or "f'" in stripped or "%s" in stripped:
                offenders.append(f"{path.name}:{number}: {stripped}")
    assert not offenders, offenders


#: Expressions an exempted CLI may interpolate: a count, or an argument the
#: operator typed themselves. Never a value read from the input file.
_SAFE_PRINT_EXPRESSIONS = re.compile(
    r"^(?:len\([a-z_]+\)|args\.[a-z_]+|skipped|deleted|[a-z_]+_count)$"
)


def test_the_stdout_exemption_prints_no_content() -> None:
    """Check each interpolated expression, not substrings.

    `len(digests)` is a count and fine; `digest` would be a leak. Only inspecting
    the expressions inside `{...}` can tell those apart.
    """
    for name in _STDOUT_ALLOWED:
        text = (SOURCE_ROOT / name).read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip().startswith("print("):
                continue
            for expression in re.findall(r"\{([^{}]+)\}", line):
                assert _SAFE_PRINT_EXPRESSIONS.match(expression.strip()), (
                    f"{name}:{number} prints {expression!r}, which may not be a count"
                )


def test_exception_logging_records_only_the_error_class(capture) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    try:
        raise ValueError("a message containing 938271")
    except ValueError:
        logger.warning("", exc_info=True, extra={"chan_fields": {"event": "boom"}})
    logged = capture.rendered[-1]
    assert "938271" not in logged
    assert "ValueError" in logged
