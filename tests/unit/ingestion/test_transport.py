"""Exercise HTTP framing and shrinking socket budgets without sockets/network."""

import ssl
from unittest.mock import Mock

import httpcore
import httpx
import pytest

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion._http_transport import (
    DeadlineBackend,
    DeadlineStream,
    DeadlineTransport,
    deadline_context,
)
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.retry import RetryPolicy

from .conftest import ACQUIRED_AT, EVENT_ID


def test_core_http_raw_framing(source, clock):
    raw = b"\xffraw\r\n"
    backend = httpcore.MockBackend(
        [
            b"HTTP/1.1 200 OK\r\nContent-Length: 6\r\nContent-Encoding: gzip\r\n\r\n" + raw,
        ]
    )
    transport = DeadlineTransport(backend=backend)
    result = HttpRetriever(
        lambda _: "https://example.invalid/report",
        retrieval_event_id=EVENT_ID,
        transport=transport,
        clock=clock,
        sleeper=clock.sleep,
        now=lambda: ACQUIRED_AT,
    ).retrieve(source)
    assert result.payload.content == raw
    assert result.provenance.http.content_encoding == "gzip"


@pytest.mark.parametrize("phase", ["headers", "body"])
def test_slow_wire_reads_obey_total_deadline(source, clock, phase):
    reads = []
    tls_contexts = []

    class SlowWire(httpcore.NetworkStream):
        def read(self, max_bytes, timeout=None):
            reads.append(timeout)
            clock.time += 0.25
            if phase == "body" and len(reads) == 1:
                return b"HTTP/1.1 200 OK\r\nContent-Length: 1000\r\n\r\n"
            return b"H" if phase == "headers" else b"x"

        def write(self, buffer, timeout=None):
            assert timeout <= 1

        def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            tls_contexts.append(ssl_context)
            return self

        def close(self):
            pass

    backend = Mock(spec=httpcore.NetworkBackend)
    backend.connect_tcp.return_value = SlowWire()
    result = HttpRetriever(
        lambda _: "https://example.invalid/report",
        retrieval_event_id=EVENT_ID,
        transport=DeadlineTransport(backend=backend),
        policy=RetryPolicy(max_attempts=1, attempt_timeout_seconds=1, operation_timeout_seconds=1),
        clock=clock,
        sleeper=clock.sleep,
    ).retrieve(source)
    assert result.payload is None and result.provenance.error_code is ErrorCode.BUDGET_EXCEEDED
    assert clock.time == 1 and not clock.sleeps
    assert reads == [1, 0.75, 0.5, 0.25]
    assert tls_contexts[0].check_hostname
    assert tls_contexts[0].verify_mode == ssl.CERT_REQUIRED


@pytest.mark.parametrize("operation", ["read", "write", "tls", "connect"])
def test_each_network_operation_uses_remaining_budget(clock, operation):
    stream = Mock(spec=httpcore.NetworkStream)
    stream.start_tls.return_value = stream
    backend = Mock(spec=httpcore.NetworkBackend)
    backend.connect_tcp.return_value = stream
    wrapped = DeadlineStream(stream)
    token = deadline_context.set((5, clock))
    try:
        clock.time = 4.5
        if operation == "read":
            wrapped.read(10, timeout=10)
            stream.read.assert_called_once_with(10, timeout=0.5)
        elif operation == "write":
            wrapped.write(b"x", timeout=10)
            stream.write.assert_called_once_with(b"x", timeout=0.5)
        elif operation == "tls":
            context = ssl.create_default_context()
            wrapped.start_tls(context, "example.invalid", timeout=10)
            stream.start_tls.assert_called_once_with(context, "example.invalid", 0.5)
        else:
            DeadlineBackend(backend).connect_tcp("example.invalid", 443, timeout=10)
            backend.connect_tcp.assert_called_once_with("example.invalid", 443, 0.5, None, None)
        clock.time = 5
        with pytest.raises(ExecutionError):
            wrapped.read(10, timeout=10)
    finally:
        deadline_context.reset(token)


@pytest.mark.parametrize(
    "wire",
    [
        b"HTTP/1.1 200 OK\r\nContent-Length: 20\r\n\r\nshort",
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nabc",
    ],
)
def test_core_incomplete_response_retries_without_partial_payload(source, clock, wire):
    service = HttpRetriever(
        lambda _: "https://example.invalid/report",
        retrieval_event_id=EVENT_ID,
        transport=DeadlineTransport(backend=httpcore.MockBackend([wire])),
        clock=clock,
        sleeper=clock.sleep,
    )
    result = service.retrieve(source)
    assert result.payload is None and result.provenance.error_code is ErrorCode.INCOMPLETE_BODY
    assert result.provenance.attempt_count == 3 and clock.sleeps == [1, 2]


def test_no_io_during_public_construction(tmp_path, monkeypatch):
    from iberian_shakti.ingestion.archive import LocalRawArchive
    from iberian_shakti.ingestion.retrieval import LocalFileRetriever

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected construction I/O")

    for method in ("mkdir", "resolve", "stat", "open", "read_bytes"):
        monkeypatch.setattr(type(tmp_path), method, forbidden)
    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    HttpRetriever(lambda _: "https://example.invalid/report", retrieval_event_id=EVENT_ID)
    LocalFileRetriever(tmp_path, retrieval_event_id=EVENT_ID)
    LocalRawArchive(tmp_path)
