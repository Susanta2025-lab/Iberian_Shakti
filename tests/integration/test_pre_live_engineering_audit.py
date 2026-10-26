"""Pre-live audit: real default transport/framing, fake socket/TLS boundary only.

No socket is created and no hostname is resolved. The installed SyncBackend,
SyncStream, httpcore/h11, HTTPX, runner, archive and OMIE parser all execute.
TLS negotiation itself is deliberately outside what this offline harness proves.
"""

import gzip
import io
import json
import logging
import os
import socket
import ssl
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from iberian_shakti.common.logging import configure_logging, safe_log_context
from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    IngestionResult,
    ParseOutcome,
    ResolutionResult,
    RetrievalOutcome,
    SourceRequest,
)
from iberian_shakti.ingestion._http_transport import DeadlineTransport, deadline_context
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.config import load_ingestion_settings
from iberian_shakti.ingestion.errors import ArchiveError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.omie.adapter import OmieAdapter
from iberian_shakti.ingestion.omie.calendar import intervals_for
from iberian_shakti.ingestion.omie.identity import download_url, listing_url, resolved_source
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retry import RetryPolicy
from iberian_shakti.ingestion.runner import ingest

DAY = date(2026, 10, 26)
NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
FIXTURES = Path(__file__).resolve().parents[1] / "data/omie"
LISTING = (
    b'<table><a href="/en/file-download?parents=marginalpdbc'
    b'&amp;filename=marginalpdbc_20261026.9">9</a>'
    b'<a href="/en/file-download?parents=marginalpdbc'
    b'&amp;filename=marginalpdbc_20261026.10">10</a></table>'
)


def wire(body=b"", status=200, headers=(), *, framing=True):
    fields = list(headers)
    if framing:
        fields.append(("Content-Length", str(len(body))))
    return (
        f"HTTP/1.1 {status} Audit\r\n".encode()
        + b"".join(f"{key}: {value}\r\n".encode() for key, value in fields)
        + b"\r\n"
        + body
    )


class SocketDouble:
    def __init__(self, response):
        self.response = response
        self.sent = bytearray()
        self.timeouts = []
        self.closed = False

    def setsockopt(self, *args):
        pass

    def settimeout(self, value):
        self.timeouts.append(value)

    def send(self, data):
        self.sent.extend(data)
        return len(data)

    def recv(self, size):
        if isinstance(self.response, Exception):
            raise self.response
        chunk, self.response = self.response[:size], self.response[size:]
        return chunk

    def close(self):
        self.closed = True

    def fileno(self):
        return -1


class OfflineRuntime:
    def __init__(self, root, monkeypatch):
        self.root = root
        self.plans = []
        self.connects = []
        self.sockets = []
        self.contexts = []
        self.sleeps = []
        self.seconds = 0.0
        self.archive = LocalRawArchive(root)
        monkeypatch.setattr(socket, "create_connection", self.connect)

        def wrap_tls(context, sock, *, server_hostname):
            return self.wrap_tls(context, sock, server_hostname=server_hostname)

        monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap_tls)

    def connect(self, address, timeout, *, source_address):
        self.connects.append((address, timeout, source_address))
        assert self.plans, "Unexpected extra acquisition attempt"
        plan = self.plans.pop(0)
        if isinstance(plan, tuple) and plan[0] == "connect":
            raise plan[1]
        stream = SocketDouble(plan)
        self.sockets.append(stream)
        return stream

    def wrap_tls(self, context, sock, *, server_hostname):
        self.contexts.append(context)
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        assert server_hostname == "www.omie.es"
        if isinstance(sock.response, tuple) and sock.response[0] == "tls":
            raise sock.response[1]
        return sock

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.seconds += seconds

    def run(self, plans, *, revision=1, policy=None, parsed_at=NOW):
        self.plans.extend(plans)
        adapter = OmieAdapter()
        settings = load_ingestion_settings({"RAW_ARCHIVE_ROOT": str(self.root)})
        service = HttpRetriever(
            download_url,
            retrieval_event_id=uuid4(),
            resolve_listing_url=listing_url,
            classify_unavailable=adapter.classify_unavailable,
            policy=policy or RetryPolicy.from_settings(settings),
            clock=lambda: self.seconds,
            sleeper=self.sleep,
            now=lambda: NOW + timedelta(seconds=self.seconds),
        )
        parse_time = {"parsed_at": parsed_at} if parsed_at is not None else {}
        result = ingest(
            SourceRequest(
                source_id="omie", report_id="marginalpdbc", delivery_date=DAY, revision=revision
            ),
            adapter=adapter,
            listing_retriever=service,
            retriever=service,
            archive=self.archive,
            parser=adapter.parser,
            parse_event_id=uuid4(),
            **parse_time,
        )
        assert not self.plans
        assert all(sock.closed for sock in self.sockets)
        return result


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    return OfflineRuntime(tmp_path, monkeypatch)


@pytest.fixture
def output():
    loggers = [logging.getLogger(name) for name in ("", "httpx", "httpcore")]
    saved = [(log, log.handlers[:], log.level, log.propagate) for log in loggers]
    stream = io.StringIO()
    configure_logging("INFO", stream=stream)
    try:
        yield stream
    finally:
        for log, handlers, level, propagate in saved:
            log.handlers[:] = handlers
            log.setLevel(level)
            log.propagate = propagate


@pytest.mark.parametrize(
    "scenario,attempts,code,parsed,objects",
    [
        ("valid", 1, None, True, 1),
        ("404", 1, ErrorCode.NOT_FOUND, None, 0),
        ("503-success", 2, None, True, 1),
        ("503-exhausted", 3, ErrorCode.HTTP_FAILURE, None, 0),
        ("timeout-success", 2, None, True, 1),
        ("html", 1, ErrorCode.CONTENT_INVALID, False, 1),
        ("truncated-report", 1, ErrorCode.CONTENT_INVALID, False, 1),
        ("encoding", 1, ErrorCode.UNSUPPORTED_ENCODING, False, 1),
        ("parser-schema", 1, ErrorCode.CONTENT_INVALID, False, 1),
        ("empty", 1, ErrorCode.CONTENT_INVALID, False, 1),
        ("incomplete-wire", 3, ErrorCode.INCOMPLETE_BODY, None, 0),
    ],
)
def test_default_stack_scenarios(runtime, scenario, attempts, code, parsed, objects):
    body = (FIXTURES / "marginalpdbc_20261026.1").read_bytes()
    valid = wire(body)
    plans = {
        "valid": [valid],
        "404": [wire(status=404)],
        "503-success": [wire(status=503), valid],
        "503-exhausted": [wire(status=503)] * 3,
        "timeout-success": [TimeoutError("synthetic-secret"), valid],
        "html": [wire(b"<html>synthetic-secret</html>")],
        "truncated-report": [wire(body[:-20])],
        "encoding": [wire(gzip.compress(body), headers=[("Content-Encoding", "gzip")])],
        "parser-schema": [wire(body.replace(b"MARGINALPDBC;", b"NEW_SCHEMA;"))],
        "empty": [wire()],
        "incomplete-wire": [wire(b"short", headers=[("Content-Length", "200")], framing=False)] * 3,
    }[scenario]
    result = runtime.run(plans)
    assert isinstance(result, IngestionResult)
    assert result.retrieval.attempt_count == len(runtime.connects) == attempts
    assert runtime.sleeps == [1, 2][: attempts - 1]
    assert len(list(runtime.root.rglob("payload.bin"))) == objects
    assert len(list(runtime.root.rglob("retrievals/*.json"))) == objects
    assert len(list(runtime.root.rglob("parses/*.json"))) == objects
    assert not list(runtime.root.rglob(".stage-*"))
    if parsed is None:
        assert result.parse is None and result.retrieval.error_code is code
    else:
        assert (result.parse.provenance.outcome is ParseOutcome.SUCCESS) == parsed
        assert result.parse.provenance.error_code is code
        if parsed:
            assert len(result.parse.records) == 192
            assert {r.market_area for r in result.parse.records} == {"PT", "ES"}
            assert sum(r.market_area == "PT" for r in result.parse.records) == 96
        assert (
            runtime.archive.load(result.retrieval.archive).content
            == plans[-1].split(b"\r\n\r\n", 1)[1]
        )


@pytest.mark.parametrize("scenario,count", [("compatible", 2), ("incompatible", 1), ("404", 2)])
def test_default_discovery_wiring(runtime, scenario, count):
    body = (FIXTURES / "marginalpdbc_20261026.1").read_bytes()
    plans = [wire(b"<html>changed listing</html>" if scenario == "incompatible" else LISTING)]
    if count == 2:
        plans.append(wire(body, status=404 if scenario == "404" else 200))
    result = runtime.run(plans, revision=None)
    assert len(runtime.connects) == count
    assert bytes(runtime.sockets[0].sent).startswith(
        b"GET /en/file-access-list?realdir=marginalpdbc HTTP/1.1\r\n"
    )
    if scenario == "incompatible":
        assert (
            isinstance(result, ResolutionResult) and result.error_code is ErrorCode.DISCOVERY_SCHEMA
        )
    else:
        assert result.retrieval.source.observed_revision == 10
        assert bytes(runtime.sockets[1].sent).startswith(
            b"GET /en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.10 HTTP/1.1"
        )
        if scenario == "404":
            assert result.retrieval.outcome is RetrievalOutcome.UNAVAILABLE
        else:
            assert len(result.parse.records) == 192


def test_default_exact_canonical_wire_and_replay(runtime, monkeypatch):
    body = (FIXTURES / "marginalpdbc_20261026.1").read_bytes()
    first = runtime.run([wire(body)])
    second = runtime.run([wire(body)])
    assert first.retrieval.archive == second.retrieval.archive
    assert first.retrieval.retrieval_event_id != second.retrieval.retrieval_event_id
    assert len(list(runtime.root.rglob("payload.bin"))) == 1
    assert len(list(runtime.root.rglob("retrievals/*.json"))) == 2
    for sock in runtime.sockets:
        assert bytes(sock.sent).startswith(
            b"GET /en/file-download?parents=marginalpdbc"
            b"&filename=marginalpdbc_20261026.1 HTTP/1.1\r\n"
        )
        assert b"Accept-Encoding: identity\r\n" in sock.sent
        assert all(0 < timeout <= 10 for timeout in sock.timeouts)
    assert runtime.connects == [(("www.omie.es", 443), 10, None)] * 2
    before = {p: p.read_bytes() for p in runtime.root.rglob("*.json")}

    def forbidden(*args, **kwargs):
        pytest.fail("Replay cannot construct a network client")

    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    acquired = replay(runtime.archive, first.retrieval.archive, first.retrieval.retrieval_event_id)
    parsed = OmieAdapter().parser.parse(
        acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=uuid4()
    )
    runtime.archive.persist_parse(parsed.provenance)
    assert acquired.provenance == first.retrieval
    assert (
        parsed.provenance.normalized_content_identity
        == first.parse.provenance.normalized_content_identity
    )
    assert all(path.read_bytes() == content for path, content in before.items())


@pytest.mark.parametrize("status", [403, 429, 500, 502, 503, 504, 302])
def test_default_status_outcome_and_safe_diagnostics(runtime, output, status):
    attempts = 3 if status in {429, 500, 502, 503, 504} else 1
    headers = [("Location", "https://user:synthetic-secret@elsewhere.invalid/")]
    result = runtime.run([wire(status=status, headers=headers)] * attempts)
    assert len(runtime.connects) == attempts and result.parse is None
    assert result.retrieval.http_status == status
    events = [json.loads(line) for line in output.getvalue().splitlines()]
    last = next(
        e for e in reversed(events) if e["event"] in {"retrieval_failed", "retry_exhausted"}
    )
    assert last["http_status"] == status
    assert last["attempt"] == attempts
    assert last["reason"] == ("rate_limited" if status == 429 else "http_failure")
    assert last["elapsed_seconds"] == sum(runtime.sleeps)
    assert "synthetic-secret" not in output.getvalue()


@pytest.mark.parametrize(
    "plan,code,reason,attempts",
    [
        (
            ("connect", socket.gaierror("synthetic-secret")),
            ErrorCode.TRANSPORT_FAILURE,
            "connection_failure",
            3,
        ),
        (
            ("connect", ConnectionRefusedError("synthetic-secret")),
            ErrorCode.TRANSPORT_FAILURE,
            "connection_failure",
            3,
        ),
        (("connect", TimeoutError("synthetic-secret")), ErrorCode.TIMEOUT, "connect_timeout", 3),
        (TimeoutError("synthetic-secret"), ErrorCode.TIMEOUT, "read_timeout", 3),
        (
            ("tls", ssl.SSLCertVerificationError("synthetic-secret")),
            ErrorCode.TLS_FAILURE,
            "tls_verification_failure",
            1,
        ),
    ],
)
def test_real_sync_exception_translation(runtime, output, plan, code, reason, attempts):
    result = runtime.run([plan] * attempts)
    assert result.retrieval.error_code is code
    assert len(runtime.connects) == attempts
    last = json.loads(output.getvalue().splitlines()[-1])
    assert last["reason"] == reason
    assert last["attempt"] == attempts
    assert "synthetic-secret" not in output.getvalue()


def test_discovery_failure_keeps_diagnostic_status(runtime, output):
    result = runtime.run([wire(status=403)], revision=None)
    assert result.error_code is ErrorCode.HTTP_FAILURE
    events = [json.loads(line) for line in output.getvalue().splitlines()]
    failed = next(e for e in events if e["event"] == "retrieval_failed")
    assert failed["http_status"] == 403
    assert failed["safe_locator"] == "omie/marginalpdbc/listing"


def test_archive_failure_does_not_retry_default_transport(runtime, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("synthetic-secret")

    monkeypatch.setattr(os, "link", denied)
    with pytest.raises(ArchiveError):
        runtime.run([wire((FIXTURES / "marginalpdbc_20261026.1").read_bytes())])
    assert len(runtime.connects) == 1
    assert all(sock.closed for sock in runtime.sockets)
    assert not list(runtime.root.rglob(".stage-*"))


def test_default_parse_time_is_captured_after_acquisition_persistence(runtime, monkeypatch):
    from iberian_shakti.ingestion import runner

    def parse_now():
        assert len(list(runtime.root.rglob("retrievals/*.json"))) == 1
        assert not list(runtime.root.rglob("parses/*.json"))
        return NOW + timedelta(seconds=runtime.seconds + 1)

    monkeypatch.setattr(runner, "utc_now", parse_now, raising=False)
    result = runtime.run(
        [wire(status=503), wire((FIXTURES / "marginalpdbc_20261026.1").read_bytes())],
        parsed_at=None,
    )
    assert result.retrieval.completed_at == NOW + timedelta(seconds=1)
    assert result.parse.provenance.parsed_at == NOW + timedelta(seconds=2)
    assert result.parse.provenance.parsed_at > result.retrieval.completed_at


@pytest.mark.parametrize(
    "encoding", [None, "identity", "IDENTITY", "gzip", "br", "gzip, br", "GZIP ,\tBR"]
)
def test_default_encoding_raw_preservation(runtime, encoding):
    body = (FIXTURES / "marginalpdbc_20261026.1").read_bytes()
    encoded = gzip.compress(body) if encoding == "gzip" else body
    headers = [("Content-Encoding", encoding)] if encoding else []
    result = runtime.run([wire(encoded, headers=headers)])
    assert runtime.archive.load(result.retrieval.archive).content == encoded
    assert (result.parse.provenance.outcome is ParseOutcome.SUCCESS) == (
        encoding is None or encoding.lower() == "identity"
    )


@pytest.mark.parametrize("framing", ["absent", "exact", "equal-duplicates", "chunked"])
def test_default_complete_framing(runtime, framing):
    body = (FIXTURES / "marginalpdbc_20261026.1").read_bytes()
    headers = []
    encoded = body
    if framing == "equal-duplicates":
        headers = [("Content-Length", str(len(body)))] * 2
    elif framing == "chunked":
        headers = [("Transfer-Encoding", "chunked")]
        encoded = f"{len(body):x}\r\n".encode() + body + b"\r\n0\r\n\r\n"
    result = runtime.run([wire(encoded, headers=headers, framing=framing == "exact")])
    assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    assert runtime.archive.load(result.retrieval.archive).content == body


def test_both_acquisitions_reach_third_attempt_without_extra_requests(runtime):
    valid = wire((FIXTURES / "marginalpdbc_20261026.1").read_bytes())
    result = runtime.run(
        [
            wire(status=503),
            wire(status=503),
            wire(LISTING),
            wire(status=503),
            wire(status=503),
            valid,
        ],
        revision=None,
    )
    assert len(runtime.connects) == 6 and runtime.sleeps == [1, 2, 1, 2]
    assert result.parse.provenance.outcome is ParseOutcome.SUCCESS


def test_httpx_write_error_is_connection_failure():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.WriteError("synthetic-secret")

    source = resolved_source(
        SourceRequest(source_id="omie", report_id="marginalpdbc", delivery_date=DAY, revision=1), 1
    )
    result = HttpRetriever(
        download_url,
        retrieval_event_id=uuid4(),
        transport=httpx.MockTransport(handler),
        sleeper=lambda _: None,
    ).retrieve(source)
    assert result.provenance.error_code is ErrorCode.TRANSPORT_FAILURE
    assert len(calls) == 3


@pytest.mark.parametrize("timezone", ["UTC", "America/New_York", "Asia/Kolkata"])
def test_machine_timezone_does_not_change_market_calendar(monkeypatch, timezone):
    previous = os.environ.get("TZ")
    try:
        monkeypatch.setenv("TZ", timezone)
        time.tzset()
        intervals = intervals_for(DAY)
        assert len(intervals) == 96
        assert intervals[0].duration_minutes == 15
        assert intervals[0].interval_start_utc == datetime(2026, 10, 25, 23, tzinfo=UTC)
        assert intervals[-1].interval_end_utc == datetime(2026, 10, 26, 23, tzinfo=UTC)
    finally:
        if previous is None:
            monkeypatch.delenv("TZ")
        else:
            monkeypatch.setenv("TZ", previous)
        time.tzset()


@pytest.mark.parametrize(
    "field,value",
    [
        ("reason", "password=synthetic-secret"),
        ("safe_locator", "https://user:synthetic-secret@example.invalid/?token=secret"),
    ],
)
def test_new_diagnostic_fields_reject_unsafe_text(field, value):
    assert safe_log_context({field: value}) == {}


def test_deadline_transport_public_construction_and_context_cleanup():
    transport = DeadlineTransport()
    transport.close()
    with pytest.raises(LookupError):
        deadline_context.get()
