"""Generic mocked acquisition/archive/replay/parse linkage; no source adapters."""

import gzip
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ParseOutcome,
    ParseProvenance,
    ParseResult,
    RawPayload,
    ResolvedSource,
    RetrievalProvenance,
    SourceRequest,
)
from iberian_shakti.contracts.market import MarketPrice
from iberian_shakti.ingestion.archive import LocalRawArchive, persist_retrieval
from iberian_shakti.ingestion.errors import ArchiveError, ExecutionError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import LocalFileRetriever, require_identity_encoding


class SyntheticParser:
    """A test-only Parser protocol implementation, unrelated to market reports."""

    def parse(
        self,
        payload: RawPayload,
        retrieval: RetrievalProvenance,
        *,
        parsed_at: datetime,
        parse_event_id: UUID,
    ) -> ParseResult:
        require_identity_encoding(retrieval)
        assert payload.content == b"synthetic\r\n"
        provenance = ParseProvenance(
            retrieval_event_id=retrieval.retrieval_event_id,
            raw=payload.reference,
            archive=retrieval.archive,
            parser_id="synthetic",
            parser_version="1.0.0",
            parsed_at=parsed_at,
            parse_event_id=parse_event_id,
            outcome=ParseOutcome.SUCCESS,
            record_count=1,
        )
        raw = payload.reference
        start = datetime(2026, 10, 26, tzinfo=UTC)
        return ParseResult(
            provenance=provenance,
            records=(
                MarketPrice(
                    source_id=raw.source_id,
                    report_id=raw.report_id,
                    market="synthetic",
                    market_area="XX",
                    delivery_date=raw.delivery_date,
                    period_index=1,
                    duration_minutes=60,
                    interval_start_utc=start,
                    interval_end_utc=start + timedelta(hours=1),
                    price=Decimal("1.00"),
                    currency="EUR",
                    price_unit="MWh",
                    parse_event_id=parse_event_id,
                ),
            ),
        )


class BytesStream(httpx.SyncByteStream):
    def __init__(self, content: bytes, *, interrupted: bool = False):
        self.content = content
        self.interrupted = interrupted

    def __iter__(self) -> Iterator[bytes]:
        yield self.content
        if self.interrupted:
            raise httpx.RemoteProtocolError("synthetic-secret")


@pytest.fixture
def source():
    return ResolvedSource(
        request=SourceRequest(
            source_id="synthetic", report_id="prices", delivery_date=date(2026, 10, 26)
        ),
        filename="report.1",
        observed_revision=1,
        safe_locator="public/report.1",
    )


def service(content, *, encoding=None, interrupted=False, max_bytes=1024):
    return HttpRetriever(
        lambda _: "https://example.invalid/report?signature=synthetic-secret",
        retrieval_event_id=UUID(int=1),
        now=lambda: datetime(2026, 10, 25, tzinfo=UTC),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                stream=BytesStream(content, interrupted=interrupted),
                headers={"Content-Encoding": encoding} if encoding else {},
            )
        ),
        sleeper=lambda _: None,
        max_bytes=max_bytes,
    )


def test_acquire_persist_replay_new_synthetic_parse(tmp_path, source, monkeypatch):
    archive = LocalRawArchive(tmp_path)
    acquired = persist_retrieval(service(b"synthetic\r\n").retrieve(source), archive)
    parser = SyntheticParser()
    first = parser.parse(
        acquired.payload,
        acquired.provenance,
        parsed_at=datetime(2026, 10, 26, tzinfo=UTC),
        parse_event_id=UUID(int=2),
    )
    archive.persist_parse(first.provenance)
    history = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("No replay HTTP client")

    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    replayed = replay(archive, acquired.provenance.archive, UUID(int=1))
    second = parser.parse(
        replayed.payload,
        replayed.provenance,
        parsed_at=datetime(2026, 10, 27, tzinfo=UTC),
        parse_event_id=UUID(int=3),
    )
    archive.persist_parse(second.provenance)
    assert replayed == acquired
    assert (
        first.provenance.normalized_content_identity
        == second.provenance.normalized_content_identity
    )
    assert first.records[0].business_identity == second.records[0].business_identity
    assert first.records[0].price == second.records[0].price
    assert all(p.read_bytes() == data for p, data in history.items())
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2


@pytest.mark.parametrize("content", [b"", b"<html>unknown body</html>", b"malformed\xff"])
def test_complete_invalid_content_archived_before_parse_failure(tmp_path, source, content):
    archive = LocalRawArchive(tmp_path)
    result = persist_retrieval(service(content).retrieve(source), archive)
    failure = ParseProvenance(
        retrieval_event_id=UUID(int=1),
        raw=result.payload.reference,
        archive=result.provenance.archive,
        parser_id="synthetic",
        parser_version="1.0.0",
        parsed_at=datetime(2026, 10, 26, tzinfo=UTC),
        parse_event_id=UUID(int=2),
        outcome=ParseOutcome.CONTENT_FAILURE,
        error_code=ErrorCode.CONTENT_INVALID,
        record_count=0,
    )
    archive.persist_parse(failure)
    assert replay(archive, result.provenance.archive, UUID(int=1)).payload.content == content
    assert result.provenance.attempt_count == 1


@pytest.mark.parametrize("encoding", ["gzip", "unknown", "gzip, br"])
def test_unsupported_encoding_preserved_then_explicit_failure(tmp_path, source, encoding):
    content = gzip.compress(b"synthetic\r\n") if encoding == "gzip" else b"encoded\xff"
    archive = LocalRawArchive(tmp_path)
    result = persist_retrieval(service(content, encoding=encoding).retrieve(source), archive)
    with pytest.raises(ExecutionError) as caught:
        require_identity_encoding(result.provenance)
    assert caught.value.code is ErrorCode.UNSUPPORTED_ENCODING
    assert replay(archive, result.provenance.archive, UUID(int=1)).payload.content == content
    assert result.provenance.attempt_count == 1


@pytest.mark.parametrize("failure", ["oversized", "interrupted"])
def test_incomplete_reports_never_archived(tmp_path, source, failure):
    result = service(
        b"synthetic\r\n",
        max_bytes=4 if failure == "oversized" else 1024,
        interrupted=failure == "interrupted",
    ).retrieve(source)
    returned = persist_retrieval(result, LocalRawArchive(tmp_path))
    assert returned.payload is None and not list(tmp_path.iterdir())


def test_archive_failure_never_reenters_transport_loop(tmp_path, source, monkeypatch):
    calls = []

    def handler(_):
        calls.append(1)
        return httpx.Response(200, stream=BytesStream(b"synthetic\r\n"))

    retriever = service(b"")
    retriever.transport = httpx.MockTransport(handler)

    def denied(*args, **kwargs):
        raise PermissionError("synthetic-secret")

    monkeypatch.setattr(Path, "mkdir", denied)
    with pytest.raises(ArchiveError):
        persist_retrieval(retriever.retrieve(source), LocalRawArchive(tmp_path))
    assert calls == [1]


def test_local_file_acquisition_and_replay_share_contracts(tmp_path, source, monkeypatch):
    input_root = tmp_path / "input"
    path = input_root / source.safe_locator
    path.parent.mkdir(parents=True)
    path.write_bytes(b"local\r\n\xff")

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline local acquisition and replay")

    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    retriever = LocalFileRetriever(input_root, retrieval_event_id=UUID(int=1))
    archive = LocalRawArchive(tmp_path / "archive")
    acquired = persist_retrieval(retriever.retrieve(source), archive)
    replayed = replay(archive, acquired.provenance.archive, UUID(int=1))
    assert replayed == acquired and replayed.payload.content == b"local\r\n\xff"
    assert replayed.provenance.http is None and replayed.provenance.http_status is None
