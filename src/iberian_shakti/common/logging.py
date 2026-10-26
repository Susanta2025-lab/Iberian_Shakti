"""Explicit JSON logging with a closed event/context boundary.

Callers supply static event names and controlled identifiers, never upstream
free text. URLs, headers, payloads, settings, and exceptions have no output
field. Unknown messages become ``unstructured_event``; arguments and tracebacks
are deliberately omitted. This formatter does not mutate the shared LogRecord.
"""

import json
import logging
import math
import re
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TextIO


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


_LEVELS: dict[str, int] = {level.value: getattr(logging, level.value) for level in LogLevel}
_EVENTS: frozenset[str] = frozenset(
    {
        "configuration_validated",
        "ingestion_started",
        "retrieval_attempt",
        "retrieval_completed",
        "retrieval_unavailable",
        "retrieval_failed",
        "retry_scheduled",
        "retry_exhausted",
        "archive_completed",
        "archive_integrity_error",
        "retrieval_provenance_persisted",
        "content_reused",
        "parse_completed",
        "omie_parse_started",
        "omie_resolution_completed",
        "validation_failed",
        "replay_completed",
        "replay_started",
        "replay_integrity_failure",
        "ingestion_completed",
        "ingestion_failed",
    }
)
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", re.ASCII)
_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", re.ASCII)
_ARCHIVE_REFERENCE = re.compile(r"[A-Za-z0-9_./-]{1,512}", re.ASCII)
_SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)
_IDENTIFIER_FIELDS = frozenset({"source", "report", "outcome", "error_code"})
_INTEGER_FIELDS: dict[str, tuple[int, int | None]] = {
    "revision": (1, None),
    "attempt": (1, None),
    "http_status": (100, 599),
    "byte_count": (0, None),
    "record_count": (0, None),
}


def _safe_string(field: str, value: str) -> bool:
    if field in _IDENTIFIER_FIELDS:
        return _IDENTIFIER.fullmatch(value) is not None
    if field in {"source_filename", "parser_version"}:
        return _FILENAME.fullmatch(value) is not None
    if field == "sha256":
        return _SHA256.fullmatch(value) is not None
    if field == "delivery_date":
        try:
            return date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if field == "archive_reference":
        return (
            _ARCHIVE_REFERENCE.fullmatch(value) is not None
            and not value.startswith("/")
            and all(part not in {"", ".", ".."} for part in value.split("/"))
        )
    return False


def safe_log_context(context: dict[str, object]) -> dict[str, str | int | float]:
    """Keep only allowlisted scalar fields with bounded, field-specific syntax.

    Identifiers/paths must be chosen by application code, not copied from
    arbitrary response text. In particular, there is intentionally no URL or
    header field. Invalid values are omitted without stringifying objects.
    """
    safe: dict[str, str | int | float] = {}
    for field, value in context.items():
        if type(value) is str and _safe_string(field, value):
            safe[field] = value
        elif field in _INTEGER_FIELDS and type(value) is int:
            minimum, maximum = _INTEGER_FIELDS[field]
            if value >= minimum and (maximum is None or value <= maximum):
                safe[field] = value
        elif field == "elapsed_seconds" and (type(value) is int or type(value) is float):
            if 0 <= value <= 1e308 and math.isfinite(value):
                safe[field] = value
    return safe


class SafeJsonFormatter(logging.Formatter):
    """Serialize only fixed envelope fields and safe context, never free text."""

    def format(self, record: logging.LogRecord) -> str:
        event = (
            record.msg
            if type(record.msg) is str and record.msg in _EVENTS
            else "unstructured_event"
        )
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": next(
                (name for name, number in _LEVELS.items() if number == record.levelno), "UNKNOWN"
            ),
            "event": event,
        }
        payload.update(safe_log_context(vars(record)))
        return json.dumps(payload, allow_nan=False, sort_keys=True)


def configure_logging(
    level: LogLevel | str = LogLevel.INFO, *, stream: TextIO | None = None
) -> None:
    """Replace root handlers explicitly at application startup.

    All application output must use this managed handler. Existing HTTPX and
    httpcore handlers (including child loggers) are removed and their verbosity
    restricted so transport diagnostics cannot bypass the formatter. Calling
    this again replaces the handler rather than duplicating output.
    """
    try:
        validated_level = LogLevel(level.strip().upper())
    except ValueError:
        raise ValueError("Invalid log level") from None

    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeJsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(_LEVELS[validated_level])

    transport_names = {"httpx", "httpcore"}
    transport_names.update(
        name for name in root.manager.loggerDict if name.startswith(("httpx.", "httpcore."))
    )
    for name in transport_names:
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.WARNING)
