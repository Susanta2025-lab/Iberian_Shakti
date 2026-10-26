"""Offline HTTP retrieval: exact representation bytes, policy, and deadlines."""

import gzip
import hashlib
import ssl
from collections.abc import Iterator
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import ErrorCode, HttpObservations, RetrievalOutcome
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.retry import RetryPolicy

from .conftest import ACQUIRED_AT, EVENT_ID


class Stream(httpx.SyncByteStream):
    def __init__(self, chunks: list[bytes], *, error: Exception | None = None) -> None:
        self.chunks = chunks
        self.error = error
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        yield from self.chunks
        if self.error:
            raise self.error

    def close(self) -> None:
        self.closed = True


def retriever(handler, clock, **kwargs):
    return HttpRetriever(
        lambda _: "https://example.invalid/report?signature=synthetic-secret",
        retrieval_event_id=EVENT_ID,
        transport=httpx.MockTransport(handler),
        clock=clock,
        sleeper=clock.sleep,
        now=lambda: ACQUIRED_AT,
        **kwargs,
    )


@pytest.mark.parametrize(
    "content", [b"line\n", b"line\r\n", b"\x00\xff\x80", b"", b"<html>unknown</html>"]
)
def test_exact_success(source, clock, content):
    requests = []
    stream = Stream([content])

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            stream=stream,
            headers={
                "Content-Type": "application/octet-stream; charset=shift_jis",
                "Content-Encoding": "identity",
                "ETag": 'W/"v1"',
                "Last-Modified": "Mon, 26 Oct 2026 10:00:00 GMT",
                "Authorization": "Bearer synthetic-secret",
                "Set-Cookie": "synthetic-secret",
            },
        )

    result = retriever(handler, clock).retrieve(source)
    assert result.payload.content == content
    assert result.payload.reference.sha256 == hashlib.sha256(content).hexdigest()
    assert result.payload.reference.byte_length == len(content)
    provenance = result.provenance
    assert provenance.source == source
    assert provenance.completed_at == ACQUIRED_AT
    assert provenance.retrieval_event_id == EVENT_ID
    assert provenance.source_published_at is None
    assert provenance.http_status == 200 and provenance.attempt_count == 1
    assert provenance.http.content_type == "application/octet-stream"
    assert provenance.http.etag == 'W/"v1"'
    assert provenance.http.last_modified.hour == 10
    assert "synthetic-secret" not in provenance.model_dump_json()
    assert requests[0].headers["accept-encoding"] == "identity"
    assert requests[0].extensions["timeout"] == dict.fromkeys(
        ["connect", "read", "write", "pool"], 10
    )
    assert stream.closed and not clock.sleeps


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "br", "unknown", "gzip, br"])
def test_encoded_bytes_are_never_decoded(source, clock, encoding):
    content = (
        gzip.compress(b"original\r\n") if encoding == "gzip" else b"\xffinvalid compressed stream"
    )
    result = retriever(
        lambda _: httpx.Response(
            200, stream=Stream([content]), headers={"Content-Encoding": encoding}
        ),
        clock,
    ).retrieve(source)
    assert result.payload.content == content
    assert result.payload.reference.sha256 == hashlib.sha256(content).hexdigest()
    assert result.provenance.http.content_encoding == encoding


@pytest.mark.parametrize(
    "header,value",
    [
        ("ETag", "not an opaque tag"),
        ("Content-Type", "bad mime"),
        ("Last-Modified", "nonsense"),
        ("Last-Modified", "Mon, 26 Oct 2026 10:00:00"),
    ],
)
def test_invalid_optional_observation_is_omitted(source, clock, header, value):
    result = retriever(
        lambda _: httpx.Response(200, stream=Stream([b"ok"]), headers={header: value}), clock
    ).retrieve(source)
    assert all(value is None for value in result.provenance.http.model_dump().values())


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_selected_http_retries_and_success(source, clock, status):
    attempts = []

    def handler(_):
        attempts.append(1)
        return httpx.Response(status if len(attempts) < 3 else 200, stream=Stream([b"ok"]))

    result = retriever(handler, clock).retrieve(source)
    assert result.payload.content == b"ok"
    assert result.provenance.attempt_count == 3
    assert len(attempts) == 3 and clock.sleeps == [1, 2]


@pytest.mark.parametrize(
    "error_type,code",
    [
        (httpx.ConnectError, ErrorCode.TRANSPORT_FAILURE),
        (httpx.ConnectTimeout, ErrorCode.TIMEOUT),
        (httpx.ReadTimeout, ErrorCode.TIMEOUT),
        (httpx.WriteTimeout, ErrorCode.TIMEOUT),
        (httpx.PoolTimeout, ErrorCode.TIMEOUT),
        (httpx.RemoteProtocolError, ErrorCode.INCOMPLETE_BODY),
        (httpx.ReadError, ErrorCode.INCOMPLETE_BODY),
    ],
)
@pytest.mark.parametrize("eventual_success", [True, False])
def test_transport_retry_ceiling(source, clock, error_type, code, eventual_success):
    attempts = []

    def handler(_):
        attempts.append(1)
        if eventual_success and len(attempts) == 3:
            return httpx.Response(200, stream=Stream([b"ok"]))
        raise error_type("https://secret.invalid/?token=synthetic-secret")

    result = retriever(handler, clock).retrieve(source)
    assert result.provenance.attempt_count == len(attempts) == 3
    assert clock.sleeps == [1, 2]
    if eventual_success:
        assert result.payload.content == b"ok"
    else:
        assert result.payload is None
        assert result.provenance.outcome is RetrievalOutcome.RETRY_EXHAUSTED
        assert result.provenance.error_code is code


@pytest.mark.parametrize(
    "status",
    [400, 401, 403, 404, 405, 410, 418, 422, 451, 501, 505, 201, 204, 206, 301, 302, 307, 308],
)
def test_unclassified_status_is_permanent(source, clock, status):
    handler = Mock(
        return_value=httpx.Response(
            status,
            stream=Stream([b"error page"]),
            headers={"Location": "https://example.invalid/other"},
        )
    )
    result = retriever(handler, clock).retrieve(source)
    assert result.provenance.outcome is RetrievalOutcome.PERMANENT_FAILURE
    assert result.provenance.error_code is ErrorCode.HTTP_FAILURE
    assert result.payload is None and handler.call_count == 1 and clock.sleeps == []


def test_provider_classified_404(source, clock):
    classify = Mock(return_value=ErrorCode.NOT_FOUND)
    handler = Mock(return_value=httpx.Response(404, stream=Stream([b"absent"])))
    result = retriever(handler, clock, classify_unavailable=classify).retrieve(source)
    assert result.provenance.outcome is RetrievalOutcome.UNAVAILABLE
    assert result.provenance.error_code is ErrorCode.NOT_FOUND
    assert result.provenance.source == source and result.provenance.raw is None
    assert result.payload is None and handler.call_count == 1 and clock.sleeps == []
    classify.assert_called_once_with(source, 404)


@pytest.mark.parametrize(
    "url,reason",
    [
        ("http://example.invalid/a", FailureReason.SCHEME),
        ("ftp://example.invalid/a", FailureReason.SCHEME),
        ("file:///tmp/x", FailureReason.SCHEME),
        ("relative/path", FailureReason.SCHEME),
        ("https:///missing", FailureReason.LOCATOR),
        ("https://example.invalid:bad/a", FailureReason.LOCATOR),
        ("https://user:synthetic-secret@example.invalid/a", FailureReason.LOCATOR),
        ("https://example.invalid/a#fragment", FailureReason.LOCATOR),
    ],
)
def test_invalid_url_without_attempt(source, clock, url, reason):
    handler = Mock(side_effect=AssertionError("Must not request"))
    service = retriever(handler, clock)
    service.resolve_url = lambda _: url
    with pytest.raises(ExecutionError) as caught:
        service.retrieve(source)
    assert caught.value.reason is reason
    assert "synthetic-secret" not in str(caught.value)
    handler.assert_not_called()
    assert clock.sleeps == []


def test_tls_failure_never_retries(source, clock):
    def handler(_):
        try:
            raise ssl.SSLCertVerificationError("synthetic-secret")
        except ssl.SSLCertVerificationError as error:
            raise httpx.ConnectError("unsafe synthetic-secret") from error

    result = retriever(handler, clock).retrieve(source)
    assert result.provenance.error_code is ErrorCode.TLS_FAILURE
    assert result.provenance.attempt_count == 1 and clock.sleeps == []


@pytest.mark.parametrize(
    "value,expected",
    [
        ("3", 3),
        ("0", 1),
        (" 2 ", 2),
        ("invalid", 1),
        ("-1", 1),
        ("1.5", 1),
        ("Mon, 26 Oct 2026 12:00:10 GMT", 1),
    ],
)
def test_retry_after_subset(source, clock, value, expected):
    calls = []

    def handler(_):
        calls.append(1)
        return httpx.Response(
            429 if len(calls) == 1 else 200, stream=Stream([b"ok"]), headers={"Retry-After": value}
        )

    assert retriever(handler, clock).retrieve(source).payload.content == b"ok"
    assert clock.sleeps == [expected]


@pytest.mark.parametrize("value", ["5", "60", "9999999999", "9" * 100])
def test_retry_after_cannot_fit_budget(source, clock, value):
    handler = Mock(
        return_value=httpx.Response(429, stream=Stream([]), headers={"Retry-After": value})
    )
    result = retriever(handler, clock, policy=RetryPolicy(operation_timeout_seconds=5)).retrieve(
        source
    )
    assert result.provenance.error_code is ErrorCode.RATE_LIMITED
    assert result.provenance.outcome is RetrievalOutcome.RETRY_EXHAUSTED
    assert handler.call_count == 1 and clock.sleeps == []


def test_rate_limit_ceiling(source, clock):
    handler = Mock(side_effect=lambda _: httpx.Response(429, stream=Stream([])))
    result = retriever(handler, clock).retrieve(source)
    assert result.provenance.error_code is ErrorCode.RATE_LIMITED
    assert handler.call_count == 3 and clock.sleeps == [1, 2]


@pytest.mark.parametrize("size", [3, 4, 5])
def test_actual_size_boundary(source, clock, size):
    result = retriever(
        lambda _: httpx.Response(200, stream=Stream([b"x" * size])), clock, max_bytes=4
    ).retrieve(source)
    if size <= 4:
        assert result.payload.content == b"x" * size
    else:
        assert result.payload is None and result.provenance.error_code is ErrorCode.SIZE_LIMIT
        assert result.provenance.attempt_count == 1
    assert clock.sleeps == []


@pytest.mark.parametrize("length", ["0", "2", "100", "invalid"])
def test_content_length_is_not_trusted(source, clock, length):
    handler = Mock(
        side_effect=lambda _: httpx.Response(
            200, stream=Stream([b"abc"]), headers={"Content-Length": length}
        )
    )
    result = retriever(handler, clock).retrieve(source)
    assert result.payload is None and result.provenance.error_code is ErrorCode.INCOMPLETE_BODY
    assert handler.call_count == 3


def test_size_count_across_chunks_and_false_length(source, clock):
    result = retriever(
        lambda _: httpx.Response(
            200, stream=Stream([b"ab", b"cd", b"e"]), headers={"Content-Length": "4"}
        ),
        clock,
        max_bytes=4,
    ).retrieve(source)
    assert result.payload is None and result.provenance.error_code is ErrorCode.SIZE_LIMIT


def test_interrupted_attempt_bytes_are_discarded(source, clock):
    streams = []

    def handler(_):
        stream = (
            Stream([b"partial"], error=httpx.RemoteProtocolError("synthetic-secret"))
            if not streams
            else Stream([b"complete"])
        )
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    result = retriever(handler, clock).retrieve(source)
    assert result.payload.content == b"complete" and len(streams) == 2
    assert all(s.closed for s in streams)


def test_slow_stream_deadline(source, clock):
    class SlowStream(Stream):
        def __iter__(self):
            for _ in range(1000):
                clock.time += 0.4
                yield b"x"

    streams = []

    def handler(_):
        stream = SlowStream([])
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    result = retriever(
        handler, clock, policy=RetryPolicy(attempt_timeout_seconds=1, operation_timeout_seconds=2)
    ).retrieve(source)
    assert result.payload is None and result.provenance.error_code is ErrorCode.BUDGET_EXCEEDED
    assert len(streams) == 1 and clock.time < 2 and not clock.sleeps
    assert all(s.closed for s in streams)


def test_no_attempt_after_oversleep(source, clock):
    handler = Mock(side_effect=lambda _: httpx.Response(503, stream=Stream([])))
    service = retriever(handler, clock, policy=RetryPolicy(operation_timeout_seconds=2))
    service.sleeper = lambda _: setattr(clock, "time", 2)
    result = service.retrieve(source)
    assert result.provenance.attempt_count == 1 and handler.call_count == 1
    assert result.provenance.error_code is ErrorCode.BUDGET_EXCEEDED


def test_phase_timeouts_clamped_to_remaining(source, clock):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, stream=Stream([]))

    retriever(handler, clock, policy=RetryPolicy(operation_timeout_seconds=0.5)).retrieve(source)
    assert set(requests[0].extensions["timeout"].values()) == {0.5}


def test_bypassed_source_rejected_before_io(source, clock):
    invalid = source.model_copy(update={"safe_locator": "../synthetic-secret"})
    handler = Mock(side_effect=AssertionError("Must not request"))
    with pytest.raises(ExecutionError) as caught:
        retriever(handler, clock).retrieve(invalid)
    assert caught.value.reason is FailureReason.SOURCE_REQUEST
    handler.assert_not_called()


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_http_exhaustion_exactly_three_attempts(source, clock, status):
    handler = Mock(side_effect=lambda _: httpx.Response(status, stream=Stream([])))
    result = retriever(handler, clock).retrieve(source)
    assert result.payload is None
    assert result.provenance.outcome is RetrievalOutcome.RETRY_EXHAUSTED
    assert result.provenance.error_code is ErrorCode.HTTP_FAILURE
    assert result.provenance.attempt_count == handler.call_count == 3
    assert clock.sleeps == [1, 2]


@pytest.mark.parametrize("encoding", ["gzip,,br", "a" * 33, "gzip;unknown"])
def test_unrepresentable_encoding_fails_closed_without_retry(source, clock, encoding):
    handler = Mock(
        return_value=httpx.Response(
            200, stream=Stream([b"encoded"]), headers={"Content-Encoding": encoding}
        )
    )
    with pytest.raises(ExecutionError) as caught:
        retriever(handler, clock).retrieve(source)
    assert caught.value.code is ErrorCode.UNSUPPORTED_ENCODING
    assert handler.call_count == 1 and not clock.sleeps


def test_preconsumed_transport_response_rejected(source, clock):
    result = retriever(lambda _: httpx.Response(200, content=b"already consumed"), clock).retrieve(
        source
    )
    assert result.payload is None and result.provenance.error_code is ErrorCode.INCOMPLETE_BODY
    assert result.provenance.attempt_count == 1 and not clock.sleeps


def test_no_first_attempt_after_deadline(source, clock):
    times = iter([0, 100])
    handler = Mock(side_effect=AssertionError("No budget"))
    service = retriever(handler, clock)
    service.clock = lambda: next(times)
    with pytest.raises(ExecutionError) as caught:
        service.retrieve(source)
    assert caught.value.code is ErrorCode.BUDGET_EXCEEDED
    handler.assert_not_called()


def test_single_attempt_setting_has_no_backoff(source, clock):
    handler = Mock(return_value=httpx.Response(503, stream=Stream([])))
    result = retriever(handler, clock, policy=RetryPolicy(max_attempts=1)).retrieve(source)
    assert result.provenance.attempt_count == handler.call_count == 1
    assert not clock.sleeps


def test_backoff_cannot_consume_last_operation_budget(source, clock):
    result = retriever(
        lambda _: httpx.Response(503, stream=Stream([])),
        clock,
        policy=RetryPolicy(operation_timeout_seconds=1),
    ).retrieve(source)
    assert result.provenance.error_code is ErrorCode.BUDGET_EXCEEDED
    assert result.provenance.attempt_count == 1 and not clock.sleeps


@pytest.mark.parametrize("encoding", ["identity", "gzip", "gzip, br", "gzip,deflate", "gzip,\tbr"])
def test_encoding_list_contract_compatible_roundtrip(encoding):
    observation = HttpObservations(content_encoding=encoding)
    assert HttpObservations.model_validate_json(observation.model_dump_json()) == observation


@pytest.mark.parametrize(
    "encoding", ["", "gzip,", "gzip,,br", "gzip\nsecret", "a" * 33, ", ".join(["a" * 32] * 4)]
)
def test_encoding_list_contract_stays_bounded(encoding):
    with pytest.raises(ValidationError):
        HttpObservations(content_encoding=encoding)
