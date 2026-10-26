"""Actual OMIE adapter and Stage 3 acquisition/archive/replay, entirely offline."""

import hashlib
import socket
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    IngestionResult,
    ParseOutcome,
    ParseProvenance,
    ResolutionOutcome,
    ResolutionResult,
    RetrievalOutcome,
    SourceRequest,
)
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.errors import ArchiveError, FailureReason
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.omie.adapter import OmieAdapter
from iberian_shakti.ingestion.omie.identity import download_url, listing_url
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.runner import ingest

ROOT = Path(__file__).resolve().parents[1] / "data" / "omie"
NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def no_stage4_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Stage 4 integration must be offline")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


class Stream(httpx.SyncByteStream):
    def __init__(self, content):
        self.content = content

    def __iter__(self):
        yield self.content


def run(
    archive, content, event_id=1, revision=1, *, day=date(2026, 10, 26), status=200, encoding=None
):
    adapter = OmieAdapter()
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/en/file-access-list":
            body = (
                '<table><tr><td><a href="/en/file-download?parents=marginalpdbc'
                f'&amp;filename=marginalpdbc_{day:%Y%m%d}.2">file</a></td></tr></table>'
            ).encode()
            return httpx.Response(200, stream=Stream(body))
        return httpx.Response(
            status,
            stream=Stream(content),
            headers={"content-encoding": encoding} if encoding else {},
        )

    retriever = HttpRetriever(
        download_url,
        resolve_listing_url=listing_url,
        retrieval_event_id=UUID(int=event_id),
        classify_unavailable=adapter.classify_unavailable,
        transport=httpx.MockTransport(handler),
        now=lambda: NOW,
        sleeper=lambda _: pytest.fail("Unexpected transport retry"),
    )
    request = SourceRequest(
        source_id="omie", report_id="marginalpdbc", delivery_date=day, revision=revision
    )
    result = ingest(
        request,
        adapter=adapter,
        listing_retriever=retriever,
        retriever=retriever,
        archive=archive,
        parser=adapter.parser,
        parsed_at=NOW,
        parse_event_id=UUID(int=event_id + 1000),
    )
    return result, calls


def normalized(result):
    return [record.model_dump(exclude={"parse_event_id"}) for record in result.parse.records]


@pytest.mark.parametrize(
    "filename,day,count",
    [
        ("marginalpdbc_20261026.1", date(2026, 10, 26), 192),
        ("marginalpdbc_20260329.1", date(2026, 3, 29), 184),
        ("marginalpdbc_20261025.1", date(2026, 10, 25), 200),
    ],
)
def test_ingest_real_components(tmp_path, filename, day, count):
    content = (ROOT / filename).read_bytes()
    archive = LocalRawArchive(tmp_path)
    result, calls = run(archive, content, day=day)
    assert isinstance(result, IngestionResult)
    assert len(calls) == 1
    assert result.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert result.retrieval.archive is not None
    assert result.retrieval.raw.sha256 == hashlib.sha256(content).hexdigest()
    assert len(result.parse.records) == count
    assert result.parse.provenance.archive == result.retrieval.archive
    assert result.parse.provenance.raw == result.retrieval.raw
    assert result.parse.provenance.retrieval_event_id == result.retrieval.retrieval_event_id
    assert archive.load(result.retrieval.archive).content == content
    metadata = list(tmp_path.rglob("parses/*.json"))
    assert len(metadata) == 1
    assert ParseProvenance.model_validate_json(metadata[0].read_bytes()) == result.parse.provenance
    assert archive.load_retrieval(result.retrieval.archive, UUID(int=1)) == result.retrieval
    assert "file-download?" not in metadata[0].read_text()


def test_latest_listing_then_report_then_archive(tmp_path):
    result, calls = run(
        LocalRawArchive(tmp_path), (ROOT / "marginalpdbc_20261026.1").read_bytes(), revision=None
    )
    assert [request.url.path for request in calls] == ["/en/file-access-list", "/en/file-download"]
    assert result.retrieval.source.observed_revision == 2
    assert result.retrieval.source.request.revision is None
    assert len(list(tmp_path.rglob("payload.bin"))) == 1
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1


@pytest.mark.parametrize("second_revision", [1, 2])
def test_same_bytes_reuse_content_and_new_acquisition(tmp_path, second_revision):
    archive = LocalRawArchive(tmp_path)
    content = (ROOT / "marginalpdbc_20261026.1").read_bytes()
    first, _ = run(archive, content)
    history = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    second, _ = run(archive, content, event_id=2, revision=second_revision)
    assert first.retrieval.archive == second.retrieval.archive
    assert first.retrieval.retrieval_event_id != second.retrieval.retrieval_event_id
    assert (
        first.parse.provenance.normalized_content_identity
        == second.parse.provenance.normalized_content_identity
    )
    assert normalized(first) == normalized(second)
    assert len(list(tmp_path.rglob("payload.bin"))) == 1
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 2
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2
    assert all(path.read_bytes() == data for path, data in history.items())


@pytest.mark.parametrize("second_revision", [1, 2])
def test_changed_bytes_preserve_both_under_same_or_changed_revision(tmp_path, second_revision):
    archive = LocalRawArchive(tmp_path)
    original = (ROOT / "marginalpdbc_20261026.1").read_bytes()
    revised = (ROOT / "revised_marginalpdbc_20261026.2").read_bytes()
    first, _ = run(archive, original)
    second, _ = run(archive, revised, event_id=2, revision=second_revision)
    assert first.retrieval.raw.sha256 != second.retrieval.raw.sha256
    assert (
        first.parse.provenance.normalized_content_identity
        != second.parse.provenance.normalized_content_identity
    )
    assert first.parse.records[0].price != second.parse.records[0].price
    assert first.parse.records[0].business_identity == second.parse.records[0].business_identity
    assert archive.load(first.retrieval.archive).content == original
    assert archive.load(second.retrieval.archive).content == revised
    assert len(list(tmp_path.rglob("payload.bin"))) == 2
    for result in [first, second]:
        assert result.parse.provenance.raw == result.retrieval.raw


@pytest.mark.parametrize(
    "filename,encoding",
    [
        ("invalid_price.omie", None),
        ("html_body.omie", None),
        ("non_ascii.omie", None),
        ("marginalpdbc_20261026.1", "gzip"),
    ],
)
def test_complete_malformed_bytes_archived_and_failure_persisted_without_retry(
    tmp_path, filename, encoding
):
    archive = LocalRawArchive(tmp_path)
    content = (ROOT / filename).read_bytes()
    result, calls = run(archive, content, encoding=encoding)
    assert len(calls) == 1 and result.retrieval.attempt_count == 1
    assert result.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert result.parse.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert result.parse.records == ()
    assert archive.load(result.retrieval.archive).content == content
    event = ParseProvenance.model_validate_json(next(tmp_path.rglob("parses/*.json")).read_bytes())
    assert event == result.parse.provenance
    assert event.error_code in {ErrorCode.CONTENT_INVALID, ErrorCode.UNSUPPORTED_ENCODING}


def test_replay_actual_parser_no_network_preserves_original_acquisition(tmp_path, monkeypatch):
    archive = LocalRawArchive(tmp_path)
    first, _ = run(archive, (ROOT / "marginalpdbc_20261026.1").read_bytes())
    history = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("No HTTP/retrieval on replay")

    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    monkeypatch.setattr(HttpRetriever, "retrieve", forbidden)
    replayed = replay(archive, first.retrieval.archive, first.retrieval.retrieval_event_id)
    parsed = OmieAdapter().parser.parse(
        replayed.payload,
        replayed.provenance,
        parsed_at=datetime(2026, 10, 27, tzinfo=UTC),
        parse_event_id=UUID(int=9999),
    )
    archive.persist_parse(parsed.provenance)
    assert replayed.provenance == first.retrieval
    assert parsed.provenance.parsed_at != first.parse.provenance.parsed_at
    assert parsed.provenance.parse_event_id != first.parse.provenance.parse_event_id
    assert (
        parsed.provenance.normalized_content_identity
        == first.parse.provenance.normalized_content_identity
    )
    assert [r.model_dump(exclude={"parse_event_id"}) for r in parsed.records] == normalized(first)
    assert all(path.read_bytes() == data for path, data in history.items())
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2


def test_disappeared_revision_has_no_archive_or_parse(tmp_path):
    result, calls = run(LocalRawArchive(tmp_path), b"missing", status=404, revision=None)
    assert result.retrieval.outcome is RetrievalOutcome.UNAVAILABLE
    assert result.retrieval.source.observed_revision == 2
    assert result.parse is None and result.retrieval.raw is None
    assert len(calls) == 2 and not list(tmp_path.iterdir())


def test_unknown_resolution_has_no_report_retrieval_or_archive(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=Stream((ROOT / "listing_paginated.html").read_bytes()))

    adapter = OmieAdapter()
    retriever = HttpRetriever(
        download_url,
        resolve_listing_url=listing_url,
        retrieval_event_id=UUID(int=1),
        transport=httpx.MockTransport(handler),
    )
    result = ingest(
        SourceRequest(source_id="omie", report_id="marginalpdbc", delivery_date=date(2026, 10, 26)),
        adapter=adapter,
        listing_retriever=retriever,
        retriever=retriever,
        archive=LocalRawArchive(tmp_path),
        parser=adapter.parser,
        parsed_at=NOW,
        parse_event_id=UUID(int=2),
    )
    assert (
        isinstance(result, ResolutionResult)
        and result.outcome is ResolutionOutcome.COVERAGE_UNKNOWN
    )
    assert len(calls) == 1 and not list(tmp_path.iterdir())


@pytest.mark.parametrize("phase", ["retrieval", "parse"])
def test_persistence_failure_cannot_report_ingestion_success(tmp_path, monkeypatch, phase):
    archive = LocalRawArchive(tmp_path)
    content = (ROOT / "marginalpdbc_20261026.1").read_bytes()
    calls = []
    original = archive._publish

    def fail(path, data, *, metadata):
        calls.append(path)
        if (phase == "retrieval" and path.parent.name == "retrievals") or (
            phase == "parse" and path.parent.name == "parses"
        ):
            raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.METADATA)
        return original(path, data, metadata=metadata)

    monkeypatch.setattr(archive, "_publish", fail)
    with pytest.raises(ArchiveError):
        run(archive, content)
    assert len(list(tmp_path.rglob("payload.bin"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 0
    if phase == "parse":
        assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert calls
