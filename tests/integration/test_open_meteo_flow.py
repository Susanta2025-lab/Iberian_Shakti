"""Real shared archive/transport/replay with synthetic Open-Meteo bodies only."""

import io
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from iberian_shakti.common.logging import configure_logging
from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ParseOutcome,
    RetrievalOutcome,
    parse_event_from_json,
)
from iberian_shakti.contracts.queries import QueryWindow
from iberian_shakti.ingestion import config
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.errors import (
    ArchiveError,
    FailureReason,
    ReplayError,
)
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.runner import ingest_resolved
from iberian_shakti.ingestion.weather import profile
from iberian_shakti.ingestion.weather.adapter import OpenMeteoAdapter, OpenMeteoForecastAdapter
from iberian_shakti.ingestion.weather.identity import forecast_request_for, historical_request_for

BODY = (Path(__file__).resolve().parents[1] / "data/open_meteo/synthetic_era5.json").read_bytes()
START = datetime(2026, 10, 25, tzinfo=UTC)
NOW = datetime(2026, 11, 3, tzinfo=UTC)


def execute_product(
    archive,
    *,
    body=None,
    event=1,
    site="PT.lisbon",
    statuses=(200,),
    headers=None,
    timeout=False,
    forecast=False,
    stream=None,
):
    if body is None:
        body = (
            (
                Path(__file__).resolve().parents[1] / "data/open_meteo/synthetic_icon_eu.json"
            ).read_bytes()
            if forecast
            else BODY
        )
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        assert request.headers["accept-encoding"] == "identity"
        assert "authorization" not in request.headers and "x-api-key" not in request.headers
        assert "apikey" not in request.url.params
        assert request.url.params["models"] == ("icon_eu" if forecast else "era5")
        if timeout:
            raise httpx.ReadTimeout("untrusted transport detail", request=request)
        return httpx.Response(
            statuses[min(len(calls) - 1, len(statuses) - 1)],
            headers=headers or {"content-type": "application/json"},
            stream=stream if stream is not None else httpx.ByteStream(body),
        )

    adapter = OpenMeteoForecastAdapter() if forecast else OpenMeteoAdapter()
    builder = forecast_request_for if forecast else historical_request_for
    result = ingest_resolved(
        adapter.resolve(
            builder(QueryWindow(start_utc=START, end_utc=START + timedelta(days=1)), site)
        ),
        retriever=adapter.retriever(
            retrieval_event_id=UUID(int=event),
            transport=httpx.MockTransport(handler),
            now=lambda: (
                (START - timedelta(hours=12) if forecast else NOW) + timedelta(seconds=event)
            ),
            sleeper=waits.append,
        ),
        archive=archive,
        parser=adapter.parser,
        parse_event_id=UUID(int=100 + event),
        parsed_at=NOW + timedelta(minutes=1),
    )
    return result, calls, waits


@pytest.fixture(params=[False, True], ids=["historical_era5", "forecast_icon_eu"])
def forecast(request):
    return request.param


@pytest.fixture
def execute(forecast):
    def selected(*args, **kwargs):
        return execute_product(*args, forecast=forecast, **kwargs)

    return selected


@pytest.fixture
def expected_body(forecast):
    return (
        (
            Path(__file__).resolve().parents[1] / "data/open_meteo/synthetic_icon_eu.json"
        ).read_bytes()
        if forecast
        else BODY
    )


@pytest.mark.parametrize("site", [site.site_id for site in profile.SITES])
def test_success_archives_original_bytes_before_parse_and_replays_without_network(
    tmp_path, monkeypatch, site, execute, forecast, expected_body
):
    archive = LocalRawArchive(tmp_path)
    original = archive.persist_parse

    def persist(event):
        assert archive.load(event.archive).content == expected_body
        assert archive.load_retrieval(event.archive, event.retrieval_event_id).raw == event.raw
        original(event)

    monkeypatch.setattr(archive, "persist_parse", persist)
    result, calls, waits = execute(archive, site=site)
    assert len(calls) == 1 and waits == []
    assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    assert (
        parse_event_from_json(next(tmp_path.rglob("parses/*.json")).read_bytes())
        == result.parse.provenance
    )
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("Replay attempted acquisition/network")

    monkeypatch.setattr(HttpRetriever, "retrieve", forbidden)
    monkeypatch.setattr(HttpRetriever, "__init__", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    monkeypatch.setattr(config, "load_provider_auth", forbidden)
    acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
    parser = OpenMeteoForecastAdapter().parser if forecast else OpenMeteoAdapter().parser
    parsed = parser.parse(
        acquired.payload,
        acquired.provenance,
        parsed_at=NOW + timedelta(days=1),
        parse_event_id=UUID(int=999),
    )
    archive.persist_parse(parsed.provenance)
    assert (
        parsed.provenance.normalized_content_identity
        == result.parse.provenance.normalized_content_identity
    )
    assert parsed.provenance.raw == result.retrieval.raw
    for first, second in zip(result.parse.records, parsed.records, strict=True):
        assert first.model_dump(exclude={"parse_event_id"}) == second.model_dump(
            exclude={"parse_event_id"}
        )
        assert first.business_identity == second.business_identity
    assert all(p.read_bytes() == body for p, body in before.items())
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2


def test_identical_and_changed_bodies_preserve_content_and_acquisition_histories(
    tmp_path, execute, forecast, expected_body
):
    archive = LocalRawArchive(tmp_path)
    first, _, _ = execute(archive)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    second, _, _ = execute(archive, event=2)
    changed = expected_body.replace(b"12.25", b"13.25", 1)
    third, _, _ = execute(archive, event=3, body=changed)
    assert first.retrieval.source == second.retrieval.source == third.retrieval.source
    assert first.retrieval.raw == second.retrieval.raw != third.retrieval.raw
    assert first.parse.records[0].value != third.parse.records[0].value
    assert (
        first.parse.records[0].business_identity == third.parse.records[0].business_identity
    ) is (not forecast)
    if forecast:
        assert first.parse.records[0].business_identity != second.parse.records[0].business_identity
    assert all(p.read_bytes() == body for p, body in before.items())
    assert len(list(tmp_path.rglob("payload.bin"))) == 2
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 3
    assert len(list(tmp_path.rglob("parses/*.json"))) == 3
    for result, expected in [(first, expected_body), (second, expected_body), (third, changed)]:
        acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
        assert acquired.payload.content == expected
        assert archive.persist(acquired.payload, acquired.provenance) == result.retrieval.archive
        archive.persist_parse(result.parse.provenance)


@pytest.mark.parametrize(
    "body,outcome",
    [
        (b"not JSON", ParseOutcome.CONTENT_FAILURE),
        (b'{"error":true,"reason":"untrusted provider detail"}', ParseOutcome.PROVIDER_REJECTED),
        (b'{"error":false}', ParseOutcome.CONTENT_FAILURE),
    ],
)
def test_http_200_bad_content_or_provider_error_archives_then_fails_without_retry(
    tmp_path, body, outcome, caplog, execute, forecast, expected_body
):
    result, calls, waits = execute(LocalRawArchive(tmp_path), body=body)
    assert len(calls) == 1 and waits == []
    assert result.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert LocalRawArchive(tmp_path).load(result.retrieval.archive).content == body
    assert result.parse.records == () and result.parse.provenance.outcome is outcome
    assert "untrusted provider detail" not in caplog.text + result.model_dump_json()


@pytest.mark.parametrize(
    "status,code",
    [
        (400, ErrorCode.HTTP_FAILURE),
        (404, ErrorCode.HTTP_FAILURE),
        (401, ErrorCode.AUTHENTICATION_FAILURE),
        (403, ErrorCode.AUTHORIZATION_FAILURE),
    ],
)
def test_terminal_http_errors_no_invented_no_data_or_body_logging(
    tmp_path, status, code, caplog, execute, forecast, expected_body
):
    result, calls, waits = execute(
        LocalRawArchive(tmp_path),
        statuses=(status,),
        body=b'{"error":true,"reason":"untrusted provider detail"}',
    )
    assert len(calls) == 1 and waits == [] and result.parse is None
    assert (
        result.retrieval.error_code is code
        and result.retrieval.outcome is RetrievalOutcome.PERMANENT_FAILURE
    )
    assert not list(tmp_path.rglob("payload.bin"))
    assert "untrusted provider detail" not in caplog.text + result.model_dump_json()


@pytest.mark.parametrize("statuses", [(503, 503, 200), (500, 500, 500), (429, 429, 429)])
def test_shared_retry_bounds_and_backoff(tmp_path, statuses, execute, forecast, expected_body):
    result, calls, waits = execute(LocalRawArchive(tmp_path), statuses=statuses)
    assert len(calls) == 3 and waits == [1.0, 2.0]
    if statuses[-1] == 200:
        assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    else:
        assert result.retrieval.outcome is RetrievalOutcome.RETRY_EXHAUSTED and result.parse is None


def test_shared_retry_after_and_timeout(tmp_path, execute, forecast, expected_body):
    result, calls, waits = execute(
        LocalRawArchive(tmp_path), statuses=(429, 200), headers={"retry-after": "3"}
    )
    assert (
        len(calls) == 2
        and waits == [3.0]
        and result.parse.provenance.outcome is ParseOutcome.SUCCESS
    )
    result, calls, waits = execute(LocalRawArchive(tmp_path), event=2, timeout=True)
    assert (
        len(calls) == 3 and waits == [1.0, 2.0] and result.retrieval.error_code is ErrorCode.TIMEOUT
    )


def test_response_byte_limit_prevents_publication(tmp_path, execute, forecast, expected_body):
    result, calls, waits = execute(LocalRawArchive(tmp_path), body=b"x" * (profile.MAX_BYTES + 1))
    assert len(calls) == 1 and waits == [] and result.parse is None
    assert result.retrieval.error_code is ErrorCode.SIZE_LIMIT
    assert not list(tmp_path.rglob("payload.bin"))


@pytest.mark.parametrize("encoding", ["gzip", "br"])
def test_unsupported_encoding_remains_original_archived_bytes(
    tmp_path, encoding, execute, forecast, expected_body
):
    archive = LocalRawArchive(tmp_path)
    result, _, _ = execute(archive, headers={"content-encoding": encoding})
    assert (
        result.parse.records == ()
        and result.parse.provenance.error_code is ErrorCode.UNSUPPORTED_ENCODING
    )
    assert archive.load(result.retrieval.archive).content == expected_body


@pytest.mark.parametrize("corruption", ["bytes", "hash", "retrieval_linkage", "missing_event"])
def test_corrupt_replay_fails_without_refetch(
    tmp_path, monkeypatch, corruption, execute, forecast, expected_body
):
    archive = LocalRawArchive(tmp_path)
    result, _, _ = execute(archive)
    reference = result.retrieval.archive
    if corruption == "bytes":
        path = tmp_path / result.retrieval.archive.relative_path
        content = b"corrupt"
    elif corruption == "retrieval_linkage":
        path = next(tmp_path.rglob("retrievals/*.json"))
        data = json.loads(path.read_bytes())
        data["raw"]["sha256"] = "0" * 64
        content = json.dumps(data).encode()
    elif corruption == "hash":
        reference = reference.model_copy(
            update={"raw": reference.raw.model_copy(update={"sha256": "0" * 64})}
        )
    if corruption in {"bytes", "retrieval_linkage"}:
        path.chmod(0o600)
        path.write_bytes(content)
    monkeypatch.setattr(HttpRetriever, "retrieve", lambda *_: pytest.fail("Refetch attempted"))
    monkeypatch.setattr(httpx, "Client", lambda *_: pytest.fail("Client construction attempted"))
    event_id = (
        UUID(int=9876) if corruption == "missing_event" else result.retrieval.retrieval_event_id
    )
    with pytest.raises(ReplayError):
        replay(archive, reference, event_id)


def test_parse_persistence_failure_prevents_success(
    tmp_path, monkeypatch, execute, forecast, expected_body
):
    archive = LocalRawArchive(tmp_path)

    def fail(_):
        raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.METADATA)

    monkeypatch.setattr(archive, "persist_parse", fail)
    with pytest.raises(ArchiveError):
        execute(archive)
    assert len(list(tmp_path.rglob("payload.bin"))) == 1
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1


def test_provider_prose_never_crosses_managed_debug_logging_boundary(
    tmp_path, execute, forecast, expected_body
):
    loggers = [logging.getLogger(name) for name in ("", "httpx", "httpcore")]
    saved = [(log, log.handlers[:], log.level, log.propagate) for log in loggers]
    stream = io.StringIO()
    configure_logging("DEBUG", stream=stream)
    try:
        result, _, _ = execute(
            LocalRawArchive(tmp_path), body=b'{"error":true,"reason":"untrusted provider detail"}'
        )
        assert result.parse.provenance.outcome is ParseOutcome.PROVIDER_REJECTED
        assert "untrusted provider detail" not in stream.getvalue()
        assert "https://" not in stream.getvalue()
        assert "provider_rejected" in stream.getvalue()
    finally:
        for log, handlers, level, propagate in saved:
            log.handlers[:] = handlers
            log.setLevel(level)
            log.propagate = propagate


def test_interrupted_response_never_publishes_complete_acquisition(tmp_path, execute):
    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"latitude":38.75'
            raise httpx.ReadError("unchecked interruption detail")

    result, calls, waits = execute(LocalRawArchive(tmp_path), stream=Interrupted())
    assert len(calls) == 3 and waits == [1.0, 2.0]
    assert result.retrieval.outcome is RetrievalOutcome.RETRY_EXHAUSTED
    assert result.parse is None and not list(tmp_path.rglob("payload.bin"))
    assert not list(tmp_path.rglob("retrievals/*.json"))
