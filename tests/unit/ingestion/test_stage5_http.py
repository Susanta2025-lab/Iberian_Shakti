"""Retry/deadline and framing boundaries through the existing HTTP engine."""

import httpcore
import httpx
import pytest

from iberian_shakti.contracts.ingestion import ErrorCode, RetrievalOutcome
from iberian_shakti.ingestion._http_transport import DeadlineTransport
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.retry import RetryPolicy

from .conftest import EVENT_ID
from .test_http import Stream, retriever


@pytest.mark.parametrize("success_attempt", [1, 2, 3, None])
@pytest.mark.parametrize("failure", ["503", "timeout", "interrupted"])
def test_exact_attempt_ceiling_and_success_boundaries(source, clock, success_attempt, failure):
    calls = []
    streams = []

    def handler(_):
        calls.append(1)
        assert len(calls) <= 3
        if len(calls) == success_attempt:
            stream = Stream([b"complete"])
            status = 200
        elif failure == "timeout":
            raise httpx.ReadTimeout("Bearer synthetic-secret")
        elif failure == "interrupted":
            stream = Stream([b"discard"], error=httpx.ReadError("synthetic-secret"))
            status = 200
        else:
            stream = Stream([b"error page"])
            status = 503
        streams.append(stream)
        return httpx.Response(status, stream=stream)

    result = retriever(handler, clock).retrieve(source)
    expected = success_attempt or 3
    assert len(calls) == result.provenance.attempt_count == expected
    assert clock.sleeps == [1, 2][: expected - 1]
    assert all(stream.closed for stream in streams)
    if success_attempt:
        assert result.payload.content == b"complete"
    else:
        assert result.payload is None
        assert result.provenance.outcome is RetrievalOutcome.RETRY_EXHAUSTED


@pytest.mark.parametrize("delay,attempts,sleeps", [(3, 2, [3]), (4, 1, []), (5, 1, [])])
def test_retry_after_compared_to_actual_remaining_budget(source, clock, delay, attempts, sleeps):
    calls = []

    def handler(_):
        calls.append(1)
        if len(calls) == 1:
            clock.time += 1
            return httpx.Response(429, stream=Stream([]), headers={"Retry-After": str(delay)})
        return httpx.Response(200, stream=Stream([b"ok"]))

    result = retriever(handler, clock, policy=RetryPolicy(operation_timeout_seconds=5)).retrieve(
        source
    )
    assert len(calls) == result.provenance.attempt_count == attempts
    assert clock.sleeps == sleeps
    if attempts == 1:
        assert result.provenance.error_code is ErrorCode.RATE_LIMITED
    else:
        assert result.payload.content == b"ok"


def test_stream_deadline_discards_attempt_then_recovers_once(source, clock):
    streams = []

    class ExpiredStream(Stream):
        def __iter__(self):
            yield b"discard"
            clock.time += 1
            yield b"late"

    def handler(_):
        stream = ExpiredStream([]) if not streams else Stream([b"complete"])
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    result = retriever(
        handler, clock, policy=RetryPolicy(attempt_timeout_seconds=1, operation_timeout_seconds=5)
    ).retrieve(source)
    assert result.payload.content == b"complete"
    assert result.provenance.attempt_count == 2
    assert clock.sleeps == [1] and all(stream.closed for stream in streams)


@pytest.mark.parametrize("remaining", [0.5, 1.0])
def test_fallback_backoff_equal_or_larger_than_remaining_budget(source, clock, remaining):
    calls = []

    def handler(_):
        calls.append(1)
        clock.time += 5 - remaining
        return httpx.Response(503, stream=Stream([]))

    result = retriever(handler, clock, policy=RetryPolicy(operation_timeout_seconds=5)).retrieve(
        source
    )
    assert result.provenance.error_code is ErrorCode.BUDGET_EXCEEDED
    assert len(calls) == 1 and clock.sleeps == []


@pytest.mark.parametrize("lengths", [["3", "3"], ["3", "4"], ["", "3"]])
def test_mock_duplicate_content_length_fails_closed(source, clock, lengths):
    calls = []

    def handler(_):
        calls.append(1)
        return httpx.Response(
            200, stream=Stream([b"abc"]), headers=[("Content-Length", value) for value in lengths]
        )

    result = retriever(handler, clock).retrieve(source)
    assert result.payload is None
    assert result.provenance.error_code is ErrorCode.INCOMPLETE_BODY
    assert len(calls) == 3 and clock.sleeps == [1, 2]


@pytest.mark.parametrize("second,success", [(b"3", True), (b"4", False)])
def test_wire_duplicate_content_length_protocol_validation(source, clock, second, success):
    wire = b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nContent-Length: " + second + b"\r\n\r\nabc"
    result = HttpRetriever(
        lambda _: "https://example.invalid/report",
        retrieval_event_id=EVENT_ID,
        clock=clock,
        sleeper=clock.sleep,
        transport=DeadlineTransport(backend=httpcore.MockBackend([wire])),
    ).retrieve(source)
    if success:
        # h11 validates and combines identical wire declarations before HTTPX.
        assert result.payload.content == b"abc"
        assert result.provenance.attempt_count == 1
    else:
        assert result.payload is None
        assert result.provenance.error_code is ErrorCode.INCOMPLETE_BODY
        assert result.provenance.attempt_count == 3


@pytest.mark.parametrize("status", [200, 204, 299, 300, 305, 507, 508, 511, 599])
def test_only_complete_200_is_acquisition_success(source, clock, status):
    stream = Stream([])
    result = retriever(lambda _: httpx.Response(status, stream=stream), clock).retrieve(source)
    assert result.provenance.attempt_count == 1 and not clock.sleeps and stream.closed
    if status == 200:
        assert result.payload.content == b""
    else:
        assert result.payload is None and result.provenance.error_code is ErrorCode.HTTP_FAILURE


def test_redirect_does_not_iterate_body_or_follow_secret_location(source, clock):
    class ForbiddenBody(Stream):
        def __iter__(self):
            pytest.fail("Redirect body must never be consumed")

    stream = ForbiddenBody([])
    calls = []

    def handler(_):
        calls.append(1)
        return httpx.Response(
            302,
            stream=stream,
            headers={"Location": "https://user:synthetic-secret@example.invalid/?signature=secret"},
        )

    result = retriever(handler, clock).retrieve(source)
    assert len(calls) == 1 and stream.closed
    assert result.provenance.error_code is ErrorCode.HTTP_FAILURE
    assert "synthetic-secret" not in result.model_dump_json()
