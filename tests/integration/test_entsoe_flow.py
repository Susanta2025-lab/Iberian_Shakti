"""Real shared transport/archive/parser/replay, synthetic ENTSO-E bytes, zero network."""

import io
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote, quote_plus
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
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.entsoe.adapter import EntsoeAdapter
from iberian_shakti.ingestion.entsoe.identity import request_for
from iberian_shakti.ingestion.errors import ArchiveError, ExecutionError, FailureReason, ReplayError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.runner import ingest_resolved

ROOT = Path(__file__).resolve().parents[1] / "data/entsoe"
BODY = (ROOT / "synthetic_es_load.xml").read_bytes()
TOKEN = 'synthetic-ENTSOE-only-token-"+/?='
NOW = datetime(2026, 11, 3, tzinfo=UTC)
START = datetime(2026, 10, 25, tzinfo=UTC)


@pytest.fixture
def managed_output():
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


def execute(
    archive,
    *,
    body=BODY,
    event=1,
    statuses=(200,),
    headers=None,
    timeout=False,
    product="actual_load",
    country="ES",
    interrupted=False,
):
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        assert request.url.params["securityToken"] == TOKEN
        if timeout:
            raise httpx.ReadTimeout(TOKEN, request=request)
        if interrupted:

            class Broken(httpx.SyncByteStream):
                def __iter__(self):
                    yield b"<broken>"
                    raise httpx.ReadError(TOKEN, request=request)

            stream = Broken()
        else:
            stream = httpx.ByteStream(body)
        return httpx.Response(
            statuses[min(len(calls) - 1, len(statuses) - 1)],
            headers=headers or {"content-type": "application/xml"},
            stream=stream,
        )

    adapter = EntsoeAdapter()
    result = ingest_resolved(
        adapter.resolve(
            request_for(
                product,
                country,
                QueryWindow(start_utc=START, end_utc=START + timedelta(hours=3)),
            )
        ),
        retriever=adapter.retriever(
            retrieval_event_id=UUID(int=event),
            environ={"ENTSOE_API_TOKEN": TOKEN},
            transport=httpx.MockTransport(handler),
            now=lambda: NOW + timedelta(seconds=event),
            sleeper=waits.append,
        ),
        archive=archive,
        parser=adapter.parser,
        parse_event_id=UUID(int=100 + event),
        parsed_at=NOW + timedelta(minutes=1),
    )
    return result, calls, waits


def test_success_archives_before_parse_and_replays_identically_without_network(
    tmp_path, monkeypatch
):
    archive = LocalRawArchive(tmp_path)
    original = archive.persist_parse

    def persist(event):
        assert archive.load(event.archive).content == BODY
        assert archive.load_retrieval(event.archive, event.retrieval_event_id).raw == event.raw
        original(event)

    monkeypatch.setattr(archive, "persist_parse", persist)
    result, calls, waits = execute(archive)
    assert len(calls) == 1 and waits == []
    assert calls[0].url.path == "/api"
    assert set(calls[0].url.params) == {
        "documentType",
        "processType",
        "outBiddingZone_Domain",
        "periodStart",
        "periodEnd",
        "securityToken",
    }
    assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    assert (
        parse_event_from_json(next(tmp_path.rglob("parses/*.json")).read_bytes())
        == result.parse.provenance
    )
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("Replay attempted network or acquisition")

    monkeypatch.setattr(HttpRetriever, "retrieve", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
    parsed = EntsoeAdapter().parser.parse(
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
    for original_record, reproduced in zip(result.parse.records, parsed.records, strict=True):
        assert original_record.model_dump(exclude={"parse_event_id"}) == reproduced.model_dump(
            exclude={"parse_event_id"}
        )
        assert original_record.business_identity == reproduced.business_identity
    assert all(p.read_bytes() == body for p, body in before.items())
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2


def test_same_query_same_body_and_revised_body_preserve_all_histories(tmp_path):
    archive = LocalRawArchive(tmp_path)
    first, _, _ = execute(archive)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    second, _, _ = execute(archive, event=2)
    changed = BODY.replace(b"23000.12300", b"24000.12300")
    third, _, _ = execute(archive, event=3, body=changed)
    assert first.retrieval.source == second.retrieval.source == third.retrieval.source
    assert first.retrieval.raw == second.retrieval.raw != third.retrieval.raw
    assert first.parse.records[0].value != third.parse.records[0].value
    # Actual corrections retain business identity and separate raw/acquisition history.
    assert len({r.parse.records[0].business_identity for r in (first, second, third)}) == 1
    assert all(p.read_bytes() == body for p, body in before.items())
    assert len(list(tmp_path.rglob("payload.bin"))) == 2
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 3
    assert len(list(tmp_path.rglob("parses/*.json"))) == 3
    for result, expected in [(first, BODY), (second, BODY), (third, changed)]:
        acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
        assert acquired.payload.content == expected
        assert archive.persist(acquired.payload, acquired.provenance) == result.retrieval.archive
        archive.persist_parse(result.parse.provenance)
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 3


@pytest.mark.parametrize(
    "body",
    [b"not XML", b"<broken>", BODY.replace(b"<type>A65</type>", b"<type>A69</type>")],
)
def test_safe_bad_content_is_archived_before_terminal_semantic_failure(tmp_path, body):
    archive = LocalRawArchive(tmp_path)
    result, calls, waits = execute(archive, body=body)
    assert len(calls) == 1 and waits == []
    assert result.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert archive.load(result.retrieval.archive).content == body
    assert result.parse.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert result.parse.records == ()
    loaded = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
    parsed = EntsoeAdapter().parser.parse(
        loaded.payload, loaded.provenance, parsed_at=NOW, parse_event_id=UUID(int=999)
    )
    assert parsed.provenance.error_code == result.parse.provenance.error_code


@pytest.mark.parametrize(
    "status,code",
    [
        (401, ErrorCode.AUTHENTICATION_FAILURE),
        (403, ErrorCode.AUTHORIZATION_FAILURE),
        (404, ErrorCode.HTTP_FAILURE),
        (400, ErrorCode.HTTP_FAILURE),
    ],
)
def test_terminal_http_errors_are_typed_without_archive_or_retry(
    tmp_path, status, code, managed_output
):
    result, calls, waits = execute(
        LocalRawArchive(tmp_path), statuses=(status,), body=TOKEN.encode()
    )
    assert len(calls) == 1 and waits == [] and result.parse is None
    assert result.retrieval.outcome is RetrievalOutcome.PERMANENT_FAILURE
    assert result.retrieval.error_code is code
    assert not list(tmp_path.rglob("payload.bin"))
    assert TOKEN not in result.model_dump_json() + managed_output.getvalue()


@pytest.mark.parametrize("statuses", [(503, 503, 200), (500, 500, 500), (502, 502, 502)])
def test_shared_bounded_retry_and_backoff(tmp_path, statuses):
    result, calls, waits = execute(LocalRawArchive(tmp_path), statuses=statuses)
    assert len(calls) == 3 and waits == [1.0, 2.0]
    assert result.retrieval.attempt_count == 3
    if statuses[-1] == 200:
        assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    else:
        assert result.retrieval.outcome is RetrievalOutcome.RETRY_EXHAUSTED and result.parse is None


def test_entsoe_rate_limit_retry_after_ends_invocation_without_early_retry(tmp_path):
    result, calls, waits = execute(
        LocalRawArchive(tmp_path), statuses=(429, 200), headers={"retry-after": "3"}
    )
    assert len(calls) == 1 and waits == []
    assert result.parse is None
    assert result.retrieval.error_code is ErrorCode.RATE_LIMITED


def test_timeout_has_bounded_retries_and_safe_diagnostics(tmp_path, managed_output):
    result, calls, waits = execute(LocalRawArchive(tmp_path), timeout=True)
    assert len(calls) == 3 and waits == [1.0, 2.0]
    assert result.retrieval.error_code is ErrorCode.TIMEOUT and result.parse is None
    assert TOKEN not in result.model_dump_json() + managed_output.getvalue()
    assert not list(tmp_path.rglob("payload.bin"))


def test_oversized_body_is_not_published(tmp_path):
    result, calls, waits = execute(LocalRawArchive(tmp_path), body=b"x" * (profile.MAX_BYTES + 1))
    assert len(calls) == 1 and waits == [] and result.parse is None
    assert result.retrieval.error_code is ErrorCode.SIZE_LIMIT
    assert not list(tmp_path.rglob("payload.bin"))


@pytest.mark.parametrize(
    "form", [lambda s: s, lambda s: quote(s, safe=""), quote_plus, lambda s: json.dumps(s)[1:-1]]
)
def test_echoed_secret_is_rejected_before_raw_or_metadata_publication(
    tmp_path, managed_output, form
):
    result, calls, waits = execute(LocalRawArchive(tmp_path), body=form(TOKEN).encode())
    assert len(calls) == 1 and waits == [] and result.parse is None
    assert result.retrieval.error_code is ErrorCode.SENSITIVE_RESPONSE
    assert result.retrieval.raw is None
    assert not list(tmp_path.rglob("payload.bin"))
    assert TOKEN not in result.model_dump_json() + managed_output.getvalue()
    assert all(TOKEN.encode() not in p.read_bytes() for p in tmp_path.rglob("*.json"))


def test_success_is_secret_safe_across_logs_query_locators_and_all_serialized_metadata(
    tmp_path, managed_output
):
    result, _, _ = execute(LocalRawArchive(tmp_path), headers={"etag": TOKEN})
    assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    assert result.retrieval.http is None
    combined = (
        result.model_dump_json()
        + result.retrieval.source.model_dump_json()
        + managed_output.getvalue()
    )
    for p in tmp_path.rglob("*"):
        if p.is_file():
            combined += p.read_text()
        combined += str(p.relative_to(tmp_path))
    for secret in (TOKEN, quote(TOKEN, safe=""), quote_plus(TOKEN), json.dumps(TOKEN)[1:-1]):
        assert secret not in combined
    assert (
        "x-api-key" not in combined and "https://web-api.tp.entsoe" not in managed_output.getvalue()
    )
    assert any(
        json.loads(line).get("event") == "parse_completed"
        for line in managed_output.getvalue().splitlines()
    )


@pytest.mark.parametrize("encoding", ["gzip", "br"])
def test_authenticated_encoded_body_is_terminal_before_publication(
    tmp_path, encoding, managed_output
):
    with pytest.raises(ExecutionError) as caught:
        execute(LocalRawArchive(tmp_path), headers={"content-encoding": encoding})
    assert caught.value.code is ErrorCode.UNSUPPORTED_ENCODING
    assert TOKEN not in str(caught.value) + repr(caught.value) + managed_output.getvalue()
    assert not list(tmp_path.rglob("payload.bin"))


def test_corrupt_archive_replay_has_no_acquisition_fallback(tmp_path, monkeypatch):
    archive = LocalRawArchive(tmp_path)
    result, _, _ = execute(archive)
    payload_path = tmp_path / result.retrieval.archive.relative_path
    payload_path.chmod(0o600)
    payload_path.write_bytes(b"corrupt")
    monkeypatch.setattr(HttpRetriever, "retrieve", lambda *_: pytest.fail("Network fallback"))
    with pytest.raises(ReplayError):
        replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)


def test_persistence_failure_prevents_success(tmp_path, monkeypatch):
    archive = LocalRawArchive(tmp_path)

    def fail(_):
        raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.METADATA)

    monkeypatch.setattr(archive, "persist_parse", fail)
    with pytest.raises(ArchiveError):
        execute(archive)
    assert len(list(tmp_path.rglob("payload.bin"))) == 1
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1


@pytest.mark.parametrize(
    "country,product,filename,expected",
    [
        ("ES", "actual_load", "synthetic_es_load.xml", 3),
        ("PT", "wind_solar_forecast", "synthetic_pt_forecast.xml", 8),
        ("ES", "wind_solar_forecast", "synthetic_es_forecast.xml", 12),
    ],
)
def test_each_selected_product_replays_offline_with_native_identity(
    tmp_path, monkeypatch, country, product, filename, expected
):
    body = (ROOT / filename).read_bytes()
    archive = LocalRawArchive(tmp_path)
    result, calls, waits = execute(archive, body=body, product=product, country=country)
    assert len(calls) == 1 and waits == []
    assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    assert len(result.parse.records) == expected
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("Replay attempted acquisition, credential loading, or network")

    monkeypatch.setattr(HttpRetriever, "retrieve", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    monkeypatch.setattr("iberian_shakti.ingestion.entsoe.adapter.load_provider_auth", forbidden)
    acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
    parsed = EntsoeAdapter.parser.parse(
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
    for original, reproduced in zip(result.parse.records, parsed.records, strict=True):
        assert original.model_dump(exclude={"parse_event_id"}) == reproduced.model_dump(
            exclude={"parse_event_id"}
        )
        assert original.business_identity == reproduced.business_identity
    assert all(p.read_bytes() == b for p, b in before.items())
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1


@pytest.mark.parametrize("country", ["PT", "ES"])
def test_forecast_unknown_editions_remain_separate_acquisition_snapshots(tmp_path, country):
    archive = LocalRawArchive(tmp_path)
    body = (ROOT / f"synthetic_{country.lower()}_forecast.xml").read_bytes()
    first, _, _ = execute(archive, body=body, product="wind_solar_forecast", country=country)
    second, _, _ = execute(
        archive, body=body, product="wind_solar_forecast", country=country, event=2
    )
    third, _, _ = execute(
        archive,
        body=body.replace(b"1000.12300", b"1100.12300"),
        product="wind_solar_forecast",
        country=country,
        event=3,
    )
    assert first.retrieval.raw == second.retrieval.raw != third.retrieval.raw
    assert len({r.parse.records[0].business_identity for r in (first, second, third)}) == 3
    assert first.parse.records[0].value != third.parse.records[0].value
    assert len(list(tmp_path.rglob("payload.bin"))) == 2
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 3


@pytest.mark.parametrize(
    "text,error",
    [
        (b"No matching data found", ErrorCode.NO_DATA),
        (b"Invalid query attributes or parameters", ErrorCode.PROVIDER_REJECTED),
        (b"More than 100 matching documents", ErrorCode.PROVIDER_REJECTED),
        (b"Unauthorized. Missing or invalid security token", ErrorCode.AUTHENTICATION_FAILURE),
        (b"unknown rejection text", ErrorCode.PROVIDER_REJECTED),
    ],
)
def test_safe_acknowledgements_archive_replay_and_never_retry(
    tmp_path, text, error, managed_output
):
    archive = LocalRawArchive(tmp_path)
    body = (
        (ROOT / "synthetic_acknowledgement.xml")
        .read_bytes()
        .replace(b"No matching data found", text)
    )
    result, calls, waits = execute(archive, body=body)
    assert len(calls) == 1 and waits == []
    assert result.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert archive.load(result.retrieval.archive).content == body
    assert result.parse.provenance.error_code is error and result.parse.records == ()
    acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
    parsed = EntsoeAdapter.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=999)
    )
    assert parsed.provenance.error_code is error and parsed.records == ()
    assert text.decode() not in managed_output.getvalue()


@pytest.mark.parametrize(
    "form",
    [
        lambda s: "".join(f"&#{ord(c)};" for c in s),
        lambda s: "".join(f"&#x{ord(c):X};" for c in s),
        lambda s: "".join(f"&#{'0' * 16}{ord(c)};" for c in s),
        lambda s: "".join(f"&#x{'0' * 16}{ord(c):X};" for c in s),
        lambda s: s.replace('"', "&quot;").replace("/", "&#47;"),
    ],
)
def test_xml_character_reference_credential_echoes_cannot_enter_archive_or_records(
    tmp_path, managed_output, form
):
    # A valid XML mRID could otherwise decode secret characters after the shared
    # literal/URL/JSON guard, leaking them into native identity/provenance.
    body = BODY.replace(b"synthetic-load-document", form(TOKEN).encode())
    result, calls, waits = execute(LocalRawArchive(tmp_path), body=body)
    assert len(calls) == 1 and waits == []
    assert result.parse is None and result.retrieval.error_code is ErrorCode.SENSITIVE_RESPONSE
    assert not list(tmp_path.rglob("payload.bin"))
    assert TOKEN not in result.model_dump_json() + managed_output.getvalue()


def test_interrupted_stream_never_publishes_complete_acquisition(tmp_path, managed_output):
    result, calls, waits = execute(LocalRawArchive(tmp_path), interrupted=True)
    assert len(calls) == 3 and waits == [1.0, 2.0]
    assert result.parse is None and result.retrieval.raw is None
    assert result.retrieval.error_code is ErrorCode.INCOMPLETE_BODY
    assert not list(tmp_path.rglob("payload.bin"))
    assert TOKEN not in result.model_dump_json() + managed_output.getvalue()


@pytest.mark.parametrize("component", ["retrieval", "hash_linkage"])
def test_corrupt_replay_metadata_fails_without_refetch(tmp_path, monkeypatch, component):
    archive = LocalRawArchive(tmp_path)
    result, _, _ = execute(archive)
    retrieval_path = next(tmp_path.rglob("retrievals/*.json"))
    data = json.loads(retrieval_path.read_bytes())
    if component == "retrieval":
        data["retrieval_event_id"] = str(UUID(int=999))
    else:
        data["raw"]["sha256"] = "a" * 64
    retrieval_path.chmod(0o600)
    retrieval_path.write_text(json.dumps(data))
    monkeypatch.setattr(HttpRetriever, "retrieve", lambda *_: pytest.fail("Refetch"))
    with pytest.raises(ReplayError):
        replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
