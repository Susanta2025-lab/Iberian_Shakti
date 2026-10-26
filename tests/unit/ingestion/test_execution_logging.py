"""Actual failure paths use the Stage 1 closed JSON logging boundary."""

import io
import json
import logging
from pathlib import Path

import httpx
import pytest

from iberian_shakti.common.logging import configure_logging
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.errors import ArchiveError, ReplayError
from iberian_shakti.ingestion.replay import replay

from .conftest import EVENT_ID
from .test_http import Stream, retriever


@pytest.fixture
def output():
    loggers = [logging.getLogger(name) for name in ("", "httpx", "httpcore")]
    saved = [(log, log.handlers[:], log.level, log.propagate) for log in loggers]
    stream = io.StringIO()
    configure_logging("DEBUG", stream=stream)
    try:
        yield stream
    finally:
        for log, handlers, level, propagate in saved:
            log.handlers[:] = handlers
            log.setLevel(level)
            log.propagate = propagate


@pytest.mark.parametrize("failure", ["transport", "permanent", "unavailable"])
def test_http_failures_do_not_log_secrets(source, clock, output, failure):
    def handler(_):
        if failure == "transport":
            raise httpx.ReadTimeout(
                "https://user:synthetic-secret@example.invalid/?token=synthetic-secret"
            )
        return httpx.Response(
            404 if failure == "unavailable" else 403,
            stream=Stream([b"synthetic-secret"]),
            headers={"Set-Cookie": "synthetic-secret", "Authorization": "Bearer synthetic-secret"},
        )

    from iberian_shakti.contracts.ingestion import ErrorCode

    result = retriever(
        handler, clock, classify_unavailable=lambda *_: ErrorCode.NOT_FOUND
    ).retrieve(source)
    text = output.getvalue()
    assert "synthetic-secret" not in text
    events = [json.loads(line) for line in text.splitlines()]
    assert "retrieval_attempt" in {event["event"] for event in events}
    assert all(
        event.get("source") == "synthetic"
        for event in events
        if event["event"] != "unstructured_event"
    )
    assert result.payload is None


def test_archive_replay_events_and_integrity_failures(tmp_path, payload, acquisition, output):
    archive = LocalRawArchive(tmp_path)
    reference = archive.persist(payload, acquisition)
    archive.persist(payload, acquisition)
    replay(archive, reference, EVENT_ID)
    path = tmp_path / reference.relative_path
    path.chmod(0o600)
    path.write_bytes(b"synthetic-secret")
    with pytest.raises(ReplayError):
        replay(archive, reference, EVENT_ID)
    text = output.getvalue()
    assert "synthetic-secret" not in text
    events = {json.loads(line)["event"] for line in text.splitlines()}
    assert events >= {
        "archive_completed",
        "content_reused",
        "retrieval_provenance_persisted",
        "replay_started",
        "replay_completed",
        "archive_integrity_error",
        "replay_integrity_failure",
    }


def test_metadata_failure_has_safe_chained_cause(
    tmp_path, payload, acquisition, output, monkeypatch
):
    def denied(*args, **kwargs):
        raise PermissionError("synthetic-secret")

    monkeypatch.setattr(Path, "mkdir", denied)
    with pytest.raises(ArchiveError) as caught:
        LocalRawArchive(tmp_path).persist(payload, acquisition)
    logging.getLogger("iberian_shakti.ingestion").exception(
        "ingestion_failed", exc_info=caught.value
    )
    assert "synthetic-secret" not in output.getvalue()
    assert isinstance(caught.value.__cause__, PermissionError)
