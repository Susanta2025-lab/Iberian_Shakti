"""Only controlled structured fields survive the logging boundary."""

import io
import json
import logging
from collections.abc import Iterator
from datetime import datetime

import pytest
from pydantic import ValidationError

from iberian_shakti.common.logging import SafeJsonFormatter, configure_logging, safe_log_context
from iberian_shakti.ingestion.config import IngestionSettings


@pytest.fixture
def log_output() -> Iterator[io.StringIO]:
    names = ("", "httpx", "httpcore", "httpx.stage1", "httpcore.stage1")
    loggers = [logging.getLogger(name) for name in names]
    previous = [(logger, logger.handlers[:], logger.level, logger.propagate) for logger in loggers]
    output = io.StringIO()
    configure_logging("DEBUG", stream=output)
    try:
        yield output
    finally:
        for logger, handlers, level, propagate in previous:
            logger.handlers[:] = handlers
            logger.setLevel(level)
            logger.propagate = propagate


def test_safe_structured_fields_remain_visible(log_output: io.StringIO) -> None:
    context = {
        "source": "omie",
        "report": "marginalpdbc",
        "delivery_date": "2026-10-26",
        "source_filename": "marginalpdbc_20261026.2",
        "revision": 2,
        "attempt": 1,
        "http_status": 200,
        "elapsed_seconds": 0.125,
        "byte_count": 2637,
        "sha256": "a" * 64,
        "archive_reference": "omie/marginalpdbc/2026-10-26/sha256/" + "a" * 64 + "/payload.bin",
        "record_count": 192,
        "parser_version": "1.0.0",
        "outcome": "success",
        "error_code": "none",
    }
    logging.getLogger("iberian_shakti.ingestion").info("ingestion_completed", extra=context)
    result = json.loads(log_output.getvalue())
    assert result == {
        **context,
        "event": "ingestion_completed",
        "level": "INFO",
        "timestamp": result["timestamp"],
    }
    assert datetime.fromisoformat(result["timestamp"]).utcoffset().total_seconds() == 0


@pytest.mark.parametrize(
    ("sensitive", "secret"),
    [
        ("https://example.invalid/report?token=synthetic-query-token", "synthetic-query-token"),
        ("https://example.invalid/?X-Amz-Signature=synthetic-signature", "synthetic-signature"),
        ("https://user:synthetic-userinfo@example.invalid/report", "synthetic-userinfo"),
        ("Authorization: Bearer synthetic-auth-secret", "synthetic-auth-secret"),
        ("Cookie: session=synthetic-cookie-secret", "synthetic-cookie-secret"),
        ("X-API-Key: synthetic-api-secret", "synthetic-api-secret"),
        ("password=synthetic-password-secret", "synthetic-password-secret"),
    ],
)
def test_sensitive_text_is_omitted_everywhere(
    log_output: io.StringIO, sensitive: str, secret: str
) -> None:
    logger = logging.getLogger("iberian_shakti.ingestion")
    logger.error(
        sensitive,
        extra={
            "source": "omie",
            "report": sensitive,
            "source_filename": sensitive,
            "archive_reference": sensitive,
            "parser_version": sensitive,
            "delivery_date": sensitive,
            "outcome": sensitive,
            "error_code": sensitive,
            "url": sensitive,
            "headers": {"Authorization": sensitive, "Cookie": sensitive},
            "api_key": secret,
            "password": secret,
            "config": {"token": secret},
            "payload": secret.encode(),
        },
    )
    logger.error("retrieval_failed: %s", sensitive)
    output = log_output.getvalue()
    assert secret not in output
    first, second = [json.loads(line) for line in output.splitlines()]
    assert first["source"] == "omie"
    assert first["event"] == second["event"] == "unstructured_event"
    assert set(first) == {"timestamp", "level", "event", "source"}


def test_exception_and_stack_text_are_omitted(log_output: io.StringIO) -> None:
    logger = logging.getLogger("iberian_shakti.ingestion")
    secret = "synthetic-exception-secret"
    try:
        raise RuntimeError("password=" + secret)
    except RuntimeError as error:
        logger.exception(
            "retrieval_failed",
            extra={"source": "omie", "error_code": "transport_failure", "exception": error},
            stack_info=True,
        )
    result = json.loads(log_output.getvalue())
    assert secret not in log_output.getvalue()
    assert "Traceback" not in log_output.getvalue()
    assert "Stack" not in log_output.getvalue()
    assert result["event"] == "retrieval_failed"
    assert result["error_code"] == "transport_failure"


def test_pydantic_rejected_inputs_are_not_logged(log_output: io.StringIO) -> None:
    secret = "synthetic-pydantic-secret"
    try:
        IngestionSettings.model_validate({"timeout_seconds": secret})
    except ValidationError as error:
        logging.getLogger("iberian_shakti.ingestion").exception(
            error,
            extra={"errors": error.errors(), "config": {"timeout_seconds": secret}},
        )
    assert secret not in log_output.getvalue()
    assert json.loads(log_output.getvalue())["event"] == "unstructured_event"


def test_objects_are_not_stringified(log_output: io.StringIO) -> None:
    # Pytest attaches capture handlers after fixture setup; exercise only the
    # explicitly managed handler when a value must never be stringified.
    configure_logging("DEBUG", stream=log_output)

    class Unsafe:
        def __str__(self) -> str:
            raise AssertionError("Unsafe value was stringified")

        def __repr__(self) -> str:
            raise AssertionError("Unsafe value was represented")

    logging.getLogger("iberian_shakti.ingestion").warning(
        Unsafe(), extra={"source_filename": Unsafe(), "source": Unsafe(), "payload": Unsafe()}
    )
    assert json.loads(log_output.getvalue())["event"] == "unstructured_event"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("attempt", 0),
        ("attempt", True),
        ("revision", -1),
        ("byte_count", -1),
        ("record_count", 1.5),
        ("http_status", 999),
        ("elapsed_seconds", float("nan")),
        ("elapsed_seconds", float("inf")),
        ("elapsed_seconds", -1),
        ("elapsed_seconds", 10**400),
        ("sha256", "not-a-hash"),
        ("delivery_date", "2026-02-30"),
        ("delivery_date", "20261026"),
        ("source_filename", "../payload.bin"),
        ("archive_reference", "../payload.bin"),
        ("archive_reference", "/tmp/payload.bin"),
        ("archive_reference", "data//payload.bin"),
        ("source", "omie\nforged-log-line"),
        ("report", "x" * 65),
    ],
)
def test_invalid_structured_fields_are_omitted(field: str, value: object) -> None:
    assert safe_log_context(
        {field: value, "source": "omie"} if field != "source" else {field: value}
    ) == ({"source": "omie"} if field != "source" else {})


def test_transport_logging_cannot_emit_raw_messages(log_output: io.StringIO) -> None:
    # Even a warning reaching the root is formatted without its URL/exception.
    logger = logging.getLogger("httpx.stage1")
    bypass = io.StringIO()
    logger.addHandler(logging.StreamHandler(bypass))
    configure_logging("DEBUG", stream=log_output)
    logger.debug("Authorization: Bearer synthetic-debug-secret")
    logger.warning("https://user:synthetic-warning-secret@example.invalid/?token=synthetic-token")
    assert bypass.getvalue() == ""
    assert "synthetic" not in log_output.getvalue()
    assert len(log_output.getvalue().splitlines()) == 1
    assert json.loads(log_output.getvalue())["event"] == "unstructured_event"


def test_configuration_is_explicit_repeatable_and_respects_level(log_output: io.StringIO) -> None:
    configure_logging("WARNING", stream=log_output)
    configure_logging("WARNING", stream=log_output)
    logger = logging.getLogger("iberian_shakti.ingestion")
    logger.info("ingestion_started")
    logger.warning("retrieval_unavailable", extra={"outcome": "not_found"})
    assert len(log_output.getvalue().splitlines()) == 1
    assert json.loads(log_output.getvalue())["outcome"] == "not_found"


def test_invalid_log_level_does_not_reconfigure_or_echo_input(log_output: io.StringIO) -> None:
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    with pytest.raises(ValueError) as caught:
        configure_logging("password=synthetic-level-secret")
    assert "synthetic-level-secret" not in str(caught.value)
    assert root.handlers == handlers
    assert root.level == level


def test_formatter_does_not_mutate_the_shared_record() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "retrieval_failed", (), None)
    record.stack_info = "synthetic-stack-secret"
    before = vars(record).copy()
    SafeJsonFormatter().format(record)
    assert vars(record) == before
