"""Synthetic credentials stay outside application output and persisted events."""

import io
import json
import logging
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.common.logging import configure_logging
from iberian_shakti.contracts.ingestion import HttpObservations, ResolvedSource
from iberian_shakti.ingestion.archive import LocalRawArchive, persist_retrieval
from iberian_shakti.ingestion.config import ConfigurationError, load_ingestion_settings
from iberian_shakti.ingestion.errors import ArchiveError, ExecutionError, ReplayError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import result_for

from .conftest import ACQUIRED_AT, EVENT_ID
from .test_archive import change, replace_bytes
from .test_http import Stream, retriever

SECRET = "stage5-synthetic-credential"
SENSITIVE = [
    f"https://user:{SECRET}@example.invalid/report",
    f"https://example.invalid/report?token={SECRET}",
    f"https://example.invalid/report?X-Amz-Signature={SECRET}",
    f"Authorization: Bearer {SECRET}",
    f"Cookie: session={SECRET}",
    f"X-API-Key: {SECRET}",
    f"password={SECRET}",
]


@pytest.fixture
def safe_output():
    root = logging.getLogger()
    names = {"httpx", "httpcore"} | {
        name for name in root.manager.loggerDict if name.startswith(("httpx.", "httpcore."))
    }
    loggers = [root, *(logging.getLogger(name) for name in names)]
    saved = [(log, log.handlers[:], log.level, log.propagate) for log in loggers]
    output = io.StringIO()
    configure_logging("DEBUG", stream=output)
    try:
        yield output
    finally:
        for log, handlers, level, propagate in saved:
            log.handlers[:] = handlers
            log.setLevel(level)
            log.propagate = propagate


@pytest.mark.parametrize("sensitive", SENSITIVE)
def test_rejected_locator_and_config_are_safe_even_when_exception_is_logged(
    source, sensitive, safe_output
):
    for invoke in (
        lambda: ResolvedSource.model_validate({**source.model_dump(), "safe_locator": sensitive}),
        lambda: load_ingestion_settings({"INGESTION_TIMEOUT_SECONDS": sensitive}),
    ):
        with pytest.raises((ValidationError, ConfigurationError)) as caught:
            invoke()
        assert SECRET not in str(caught.value) and SECRET not in repr(caught.value)
        logging.getLogger("iberian_shakti").exception(
            "ingestion_failed",
            exc_info=caught.value,
            extra={"validation_errors": getattr(caught.value, "errors", lambda: [])()},
        )
    assert SECRET not in safe_output.getvalue()


@pytest.mark.parametrize("sensitive", SENSITIVE)
def test_private_transport_query_headers_and_invalid_metadata_never_persist(
    tmp_path, source, clock, sensitive, safe_output
):
    def handler(_):
        return httpx.Response(
            200,
            stream=Stream([b"original bytes"]),
            headers={
                "Authorization": sensitive,
                "Cookie": sensitive,
                "Set-Cookie": sensitive,
                "X-API-Key": sensitive,
                "X-Transport-URL": sensitive,
                "Content-Type": f"application/octet-stream; private={SECRET}",
                "ETag": f"invalid {sensitive}",
                "Last-Modified": sensitive,
            },
        )

    service = retriever(handler, clock)
    service.resolve_url = lambda _: f"https://example.invalid/report?signature={SECRET}"
    archive = LocalRawArchive(tmp_path)
    acquired = persist_retrieval(service.retrieve(source), archive)
    serialized = acquired.provenance.model_dump_json()
    assert acquired.provenance.http == HttpObservations(content_type="application/octet-stream")
    assert acquired.provenance.source.safe_locator == source.safe_locator
    assert SECRET not in serialized and "signature=" not in serialized
    for path in tmp_path.rglob("*.json"):
        assert SECRET not in path.read_text()
        data = json.loads(path.read_bytes())
        assert set(data["http"]) == {"content_type", "content_encoding", "etag", "last_modified"}
    assert SECRET not in safe_output.getvalue()
    assert "file-download?" not in safe_output.getvalue()


@pytest.mark.parametrize("sensitive", SENSITIVE)
def test_transport_exception_and_malformed_encoding_do_not_echo_input(
    source, clock, sensitive, safe_output
):
    calls = []

    def handler(_):
        calls.append(1)
        raise httpx.ReadTimeout(sensitive)

    result = retriever(handler, clock).retrieve(source)
    assert result.payload is None and len(calls) == 3
    assert SECRET not in result.model_dump_json()
    with pytest.raises(ExecutionError) as caught:
        retriever(
            lambda _: httpx.Response(
                200, stream=Stream([b"raw"]), headers={"Content-Encoding": sensitive}
            ),
            clock,
        ).retrieve(source)
    logging.getLogger("iberian_shakti").exception("ingestion_failed", exc_info=caught.value)
    assert SECRET not in str(caught.value) and SECRET not in safe_output.getvalue()


@pytest.mark.parametrize("stage", ["archive", "replay", "local", "locator"])
def test_chained_os_and_locator_errors_are_safe_when_actively_logged(
    tmp_path, source, payload, acquisition, clock, monkeypatch, safe_output, stage
):
    archive = LocalRawArchive(tmp_path)

    def denied(*args, **kwargs):
        raise PermissionError(f"password={SECRET}")

    if stage == "archive":
        monkeypatch.setattr(Path, "mkdir", denied)

        def operation():
            return archive.persist(payload, acquisition)
    elif stage == "replay":
        ref = archive.persist(payload, acquisition)
        replace_bytes(tmp_path / ref.relative_path, f"password={SECRET}".encode())

        def operation():
            return replay(archive, ref, EVENT_ID)
    elif stage == "local":
        from iberian_shakti.ingestion.retrieval import LocalFileRetriever

        monkeypatch.setattr(Path, "open", denied)

        def operation():
            return LocalFileRetriever(tmp_path, retrieval_event_id=EVENT_ID).retrieve(source)
    else:

        def invalid(_):
            raise ValueError(f"https://user:{SECRET}@example.invalid")

        def operation():
            return HttpRetriever(invalid, retrieval_event_id=EVENT_ID).retrieve(source)

    with pytest.raises((ArchiveError, ReplayError, ExecutionError)) as caught:
        operation()
    logging.getLogger("iberian_shakti").exception(
        "ingestion_failed", exc_info=caught.value, stack_info=True
    )
    assert SECRET not in str(caught.value) and SECRET not in repr(caught.value)
    assert SECRET not in safe_output.getvalue()
    assert "Traceback" not in safe_output.getvalue()


@pytest.mark.parametrize("variant", ["time", "event", "revision", "etag", "modified", "status"])
def test_acquisition_observations_do_not_change_raw_content_identity(source, variant):
    original = result_for(source, EVENT_ID, ACQUIRED_AT, content=b"same bytes", status=200)
    kwargs = {"status": 200}
    event, completed = EVENT_ID, ACQUIRED_AT
    if variant == "time":
        completed += timedelta(days=1)
    elif variant == "event":
        event = UUID(int=999)
    elif variant == "revision":
        source = change(
            source, observed_revision=10, filename="report.10", safe_locator="public/report.10"
        )
    elif variant == "etag":
        kwargs["observations"] = HttpObservations(etag='"new-version"')
    elif variant == "modified":
        kwargs["observations"] = HttpObservations(last_modified=ACQUIRED_AT)
    else:
        kwargs["status"] = None  # Local acquisition versus HTTP 200.
    changed = result_for(source, event, completed, content=b"same bytes", **kwargs)
    assert changed.provenance != original.provenance
    assert changed.payload.reference.content_identity == original.payload.reference.content_identity
