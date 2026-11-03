"""Real REN/shared components, synthetic bytes and network-denied normalized replay."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    MeasurementParseProvenance,
    ParseOutcome,
    ResolvedSource,
    RetrievalOutcome,
    parse_event_from_json,
)
from iberian_shakti.contracts.measurements import RecordSchema, SchemaFamily
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.errors import ArchiveError, ReplayError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.ren import profile
from iberian_shakti.ingestion.ren.adapter import RenAdapter
from iberian_shakti.ingestion.ren.identity import request_for
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import result_for
from iberian_shakti.ingestion.runner import ingest_resolved

ROOT = Path(__file__).resolve().parents[1] / "data/ren"
INVENTORY = json.loads((ROOT / "manifest.json").read_bytes())
NOW = datetime(2026, 10, 28, tzinfo=UTC)


def execute(archive, name="synthetic_ordinary.json", event=1, statuses=(200,), body=None):
    calls, waits = [], []
    adapter = RenAdapter()
    day = date.fromisoformat(INVENTORY[name]["source_day"])
    content = (ROOT / name).read_bytes() if body is None else body

    def handler(request):
        calls.append(request)
        return httpx.Response(
            statuses[min(len(calls) - 1, len(statuses) - 1)],
            headers={"content-type": "text/plain"},
            stream=httpx.ByteStream(content),
        )

    retriever = adapter.retriever(
        retrieval_event_id=UUID(int=event),
        transport=httpx.MockTransport(handler),
        now=lambda: NOW + timedelta(seconds=event),
        sleeper=waits.append,
    )
    result = ingest_resolved(
        adapter.resolve(request_for(day)),
        retriever=retriever,
        archive=archive,
        parser=adapter.parser,
        parse_event_id=UUID(int=event + 100),
        parsed_at=NOW,
    )
    return result, calls, waits


@pytest.mark.parametrize("name,entry", sorted(INVENTORY.items()))
def test_real_components_archive_original_bytes_then_persist_outcome_and_replay(
    tmp_path, monkeypatch, name, entry
):
    archive = LocalRawArchive(tmp_path)
    original_persist = archive.persist_parse

    def persist(event):
        # Real original bytes and acquisition metadata must exist before semantic publication.
        assert archive.load(event.archive).content == (ROOT / name).read_bytes()
        assert archive.load_retrieval(event.archive, event.retrieval_event_id).raw == event.raw
        original_persist(event)

    monkeypatch.setattr(archive, "persist_parse", persist)
    result, calls, waits = execute(archive, name)
    assert len(calls) == 1 and waits == []
    call = calls[0]
    assert call.method == "GET" and call.headers["accept-encoding"] == "identity"
    assert call.url.host == "servicebus.ren.pt" and call.url.path == profile.ENDPOINT_PATH
    assert dict(call.url.params) == {"culture": "en-US", "date": entry["source_day"]}
    assert "x-api-key" not in call.headers and "authorization" not in call.headers
    assert result.retrieval.http_status == 200
    assert result.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert result.parse.provenance.outcome.value == entry["outcome"]
    assert result.parse.provenance.error_code == entry["error_code"]
    assert len(result.parse.records) == entry["record_count"]
    event_path = next(tmp_path.rglob("parses/*.json"))
    assert parse_event_from_json(event_path.read_bytes()) == result.parse.provenance
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    monkeypatch.setattr(HttpRetriever, "retrieve", lambda *_: pytest.fail("Replay acquired data"))
    acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
    repeated = RenAdapter().parser.parse(
        acquired.payload,
        acquired.provenance,
        parsed_at=NOW + timedelta(days=1),
        parse_event_id=UUID(int=999),
    )
    archive.persist_parse(repeated.provenance)
    assert len(repeated.records) == len(result.parse.records)
    for original, reproduced in zip(result.parse.records, repeated.records, strict=True):
        assert original.model_dump(exclude={"parse_event_id"}) == reproduced.model_dump(
            exclude={"parse_event_id"}
        )
        assert original.business_identity == reproduced.business_identity
    assert repeated.provenance.error_code == result.parse.provenance.error_code
    assert (
        repeated.provenance.normalized_content_identity
        == result.parse.provenance.normalized_content_identity
    )
    assert all(p.read_bytes() == body for p, body in before.items())
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2


@pytest.mark.parametrize("name", ["ordinary", "spring", "autumn"])
def test_legacy_acquisition_replays_with_new_profile_without_rewriting_history(
    tmp_path, monkeypatch, name
):
    archive = LocalRawArchive(tmp_path)
    filename = f"synthetic_{name}.json"
    day = date.fromisoformat(INVENTORY[filename]["source_day"])
    current = request_for(day)
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    legacy = ApiSourceRequest(
        source_id="ren",
        report_id="ElectricityProductionBreakdownDaily.en-US.v0.1.0",
        delivery_date=day,
        window=QueryWindow(start_utc=start, end_utc=start + timedelta(days=1)),
        query=current.query,
    )
    source = ResolvedSource.for_api(legacy)
    # Legacy identity is accepted only by parsing, never as a new fetch override.
    from iberian_shakti.ingestion.errors import ExecutionError

    with pytest.raises(ExecutionError):
        RenAdapter().transport_url(source)
    acquired = result_for(source, UUID(int=1), NOW, content=(ROOT / filename).read_bytes())
    reference = archive.persist(acquired.payload, acquired.provenance)
    stored = archive.load_retrieval(reference, UUID(int=1))
    old_event = MeasurementParseProvenance(
        retrieval_event_id=UUID(int=1),
        raw=stored.raw,
        archive=reference,
        parser_id=profile.PARSER_ID,
        parser_version="0.1.0",
        record_schema=RecordSchema(family=SchemaFamily.SYSTEM_MEASUREMENT),
        catalogue_version="0.1.0",
        parsed_at=NOW,
        parse_event_id=UUID(int=2),
        outcome=ParseOutcome.CONTENT_FAILURE,
        error_code=ErrorCode.TIME_SEMANTICS_UNKNOWN,
        record_count=0,
    )
    archive.persist_parse(old_event)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    monkeypatch.setattr(
        HttpRetriever, "retrieve", lambda *_: pytest.fail("Legacy replay acquired data")
    )
    loaded = replay(archive, reference, UUID(int=1))
    parsed = RenAdapter().parser.parse(
        loaded.payload, loaded.provenance, parsed_at=NOW, parse_event_id=UUID(int=3)
    )
    archive.persist_parse(parsed.provenance)
    assert parsed.provenance.outcome is ParseOutcome.SUCCESS
    assert len(parsed.records) == INVENTORY[filename]["record_count"]
    assert parsed.provenance.catalogue_version == parsed.provenance.parser_version == "0.2.0"
    assert parsed.provenance.raw == stored.raw
    assert parsed.provenance.normalized_content_identity != old_event.normalized_content_identity
    assert all(r.native.profile_version == "0.2.0" for r in parsed.records)
    assert all(
        r.report_id == legacy.report_id and r.retrieval_event_id == UUID(int=1)
        for r in parsed.records
    )
    assert all(p.read_bytes() == content for p, content in before.items())
    assert archive.load_retrieval(reference, UUID(int=1)).source.request == legacy
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2


def test_identical_acquisitions_and_synthetic_correction_preserve_all_history(tmp_path):
    archive = LocalRawArchive(tmp_path)
    first, _, _ = execute(archive)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    second, _, _ = execute(archive, event=2)
    third, _, _ = execute(archive, "synthetic_corrected.json", event=3)
    assert first.retrieval.raw == second.retrieval.raw != third.retrieval.raw
    assert first.retrieval.source == second.retrieval.source == third.retrieval.source
    assert all(r.parse.provenance.outcome is ParseOutcome.SUCCESS for r in (first, second, third))
    assert first.parse.records[0].value != third.parse.records[0].value
    assert first.parse.records[0].business_identity == third.parse.records[0].business_identity
    assert len(list(tmp_path.rglob("payload.bin"))) == 2
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 3
    assert len(list(tmp_path.rglob("parses/*.json"))) == 3
    assert all(p.read_bytes() == body for p, body in before.items())
    for result in (first, second, third):
        acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
        assert archive.persist(acquired.payload, acquired.provenance) == result.retrieval.archive
        archive.persist_parse(result.parse.provenance)
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 3


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410, 422])
def test_permanent_http_failures_never_poll_or_invent_no_data(tmp_path, status):
    result, calls, waits = execute(LocalRawArchive(tmp_path), statuses=(status,))
    assert len(calls) == 1 and waits == [] and result.parse is None
    assert result.retrieval.outcome is RetrievalOutcome.PERMANENT_FAILURE
    assert result.retrieval.error_code is not ErrorCode.NOT_FOUND
    assert not list(tmp_path.rglob("payload.bin"))


@pytest.mark.parametrize("statuses", [(503, 503, 200), (503, 503, 503)])
def test_shared_retry_ceiling_and_default_backoff(tmp_path, statuses):
    result, calls, waits = execute(LocalRawArchive(tmp_path), statuses=statuses)
    assert len(calls) == 3 and waits == [1.0, 2.0]
    assert result.retrieval.attempt_count == 3
    if statuses[-1] == 200:
        assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
        assert len(result.parse.records) == 1056
    else:
        assert result.retrieval.outcome is RetrievalOutcome.RETRY_EXHAUSTED
        assert result.parse is None


def test_response_cap_prevents_complete_archive(tmp_path):
    result, calls, waits = execute(LocalRawArchive(tmp_path), body=b"x" * (profile.MAX_BYTES + 1))
    assert len(calls) == 1 and waits == []
    assert result.retrieval.error_code is ErrorCode.SIZE_LIMIT and result.parse is None
    assert not list(tmp_path.rglob("payload.bin"))


def test_corrupt_archive_does_not_refetch(tmp_path, monkeypatch):
    archive = LocalRawArchive(tmp_path)
    result, _, _ = execute(archive)
    payload = tmp_path / result.retrieval.archive.relative_path
    payload.chmod(0o600)
    payload.write_bytes(b"corrupt")
    monkeypatch.setattr(HttpRetriever, "retrieve", lambda *_: pytest.fail("Network fallback"))
    with pytest.raises(ReplayError):
        replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)


def test_wrong_retrieval_linkage_cannot_be_replayed(tmp_path):
    archive = LocalRawArchive(tmp_path)
    first, _, _ = execute(archive)
    second, _, _ = execute(archive, "synthetic_corrected.json", event=2)
    with pytest.raises(ReplayError):
        replay(archive, second.retrieval.archive, first.retrieval.retrieval_event_id)


def test_parse_persistence_failure_prevents_ingestion_result(tmp_path, monkeypatch):
    from iberian_shakti.ingestion.errors import FailureReason

    archive = LocalRawArchive(tmp_path)

    def fail(_):
        raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.METADATA)

    monkeypatch.setattr(archive, "persist_parse", fail)
    with pytest.raises(ArchiveError):
        execute(archive)
    assert len(list(tmp_path.rglob("payload.bin"))) == 1
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1


def test_default_ren_transport_is_denied_by_repository_guard():
    adapter = RenAdapter()
    with pytest.raises(AssertionError, match="Default pytest forbids network"):
        adapter.retriever(retrieval_event_id=UUID(int=1)).retrieve(
            adapter.resolve(request_for(date(2026, 10, 24)))
        )


@pytest.mark.parametrize("encoding", ["gzip", "br", "gzip, br"])
def test_anonymous_nonidentity_bytes_are_archived_then_rejected(tmp_path, encoding):
    archive = LocalRawArchive(tmp_path)
    adapter = RenAdapter()
    body = b"synthetic encoded bytes, not a real compressed stream"
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, headers={"content-encoding": encoding}, stream=httpx.ByteStream(body)
        )

    result = ingest_resolved(
        adapter.resolve(request_for(date(2026, 10, 24))),
        retriever=adapter.retriever(
            retrieval_event_id=UUID(int=1), transport=httpx.MockTransport(handler)
        ),
        archive=archive,
        parser=adapter.parser,
        parse_event_id=UUID(int=2),
        parsed_at=NOW,
    )
    assert len(calls) == 1 and result.retrieval.http_status == 200
    assert archive.load(result.retrieval.archive).content == body
    assert result.parse.provenance.error_code is ErrorCode.UNSUPPORTED_ENCODING
    assert result.parse.records == ()


def test_redirect_is_terminal_without_following_target(tmp_path):
    calls = []
    adapter = RenAdapter()

    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"location": "https://other.invalid/forbidden"})

    result = ingest_resolved(
        adapter.resolve(request_for(date(2026, 10, 24))),
        retriever=adapter.retriever(
            retrieval_event_id=UUID(int=1), transport=httpx.MockTransport(handler)
        ),
        archive=LocalRawArchive(tmp_path),
        parser=adapter.parser,
        parse_event_id=UUID(int=2),
        parsed_at=NOW,
    )
    assert len(calls) == 1 and result.retrieval.error_code is ErrorCode.HTTP_FAILURE
    assert result.parse is None


def test_managed_logs_never_include_provider_strings_or_full_transport_url(tmp_path):
    import io
    import logging

    from iberian_shakti.common.logging import configure_logging

    loggers = [logging.getLogger(name) for name in ("", "httpx", "httpcore")]
    saved = [(log, log.handlers[:], log.level, log.propagate) for log in loggers]
    stream = io.StringIO()
    configure_logging("DEBUG", stream=stream)
    try:
        data = json.loads((ROOT / "synthetic_ordinary.json").read_bytes())
        data["series"][0]["name"] = "synthetic-token-source-string"
        result, _, _ = execute(LocalRawArchive(tmp_path), body=json.dumps(data).encode())
    finally:
        for log, handlers, level, propagate in saved:
            log.handlers[:] = handlers
            log.setLevel(level)
            log.propagate = propagate
    text = stream.getvalue()
    assert "synthetic-token-source-string" not in text
    assert "https://" not in text and "servicebus.ren.pt" not in text
    assert "xAxis" not in text and "tooltipOptions" not in text
    events = [json.loads(line) for line in text.splitlines()]
    assert any(e.get("error_code") == "schema_unsupported" for e in events)
    assert result.parse.records == ()
