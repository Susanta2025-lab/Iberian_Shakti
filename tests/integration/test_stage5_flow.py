"""Full real-component scenarios with mocked HTTP and immutable local storage."""

import hashlib
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import httpx
import pytest

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    IngestionResult,
    ParseOutcome,
    ParseProvenance,
    ResolutionOutcome,
    RetrievalOutcome,
    RetrievalResult,
    SourceRequest,
)
from iberian_shakti.ingestion.archive import LocalRawArchive, persist_retrieval
from iberian_shakti.ingestion.config import load_ingestion_settings
from iberian_shakti.ingestion.errors import ArchiveError, ReplayError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.omie.adapter import OmieAdapter
from iberian_shakti.ingestion.omie.identity import download_url, listing_url
from iberian_shakti.ingestion.omie.parser import OmieParser
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import LocalFileRetriever
from iberian_shakti.ingestion.runner import ingest

ROOT = Path(__file__).resolve().parents[1] / "data" / "omie"
NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
ORIGINAL = (ROOT / "marginalpdbc_20261026.1").read_bytes()
REVISED = (ROOT / "revised_marginalpdbc_20261026.2").read_bytes()
LISTING = (
    b'<table><a href="/en/file-download?parents=marginalpdbc'
    b'&amp;filename=marginalpdbc_20261026.9">9</a>'
    b'<a href="/en/file-download?parents=marginalpdbc'
    b'&amp;filename=marginalpdbc_20261026.10">10</a></table>'
)


def history(root):
    return {p: (p.read_bytes(), p.stat().st_ino) for p in root.rglob("*") if p.is_file()}


def preserved(before):
    assert all((p.read_bytes(), p.stat().st_ino) == value for p, value in before.items())


def normalized(parsed):
    return tuple(record.model_dump(exclude={"parse_event_id"}) for record in parsed.records)


def execute(archive, handler, *, event=1, revision=1, parser=None):
    adapter = OmieAdapter()
    calls, sleeps = [], []
    time = [0.0]

    def sleep(seconds):
        sleeps.append(seconds)
        time[0] += seconds

    def recorded(request):
        calls.append(request)
        return handler(request)

    service = HttpRetriever(
        download_url,
        resolve_listing_url=listing_url,
        retrieval_event_id=UUID(int=event),
        classify_unavailable=adapter.classify_unavailable,
        transport=httpx.MockTransport(recorded),
        now=lambda: NOW + timedelta(seconds=event),
        clock=lambda: time[0],
        sleeper=sleep,
    )
    result = ingest(
        SourceRequest(
            source_id="omie",
            report_id="marginalpdbc",
            delivery_date=date(2026, 10, 26),
            revision=revision,
        ),
        adapter=adapter,
        listing_retriever=service,
        retriever=service,
        archive=archive,
        parser=parser if parser is not None else OmieParser(),
        parsed_at=NOW + timedelta(minutes=event),
        parse_event_id=UUID(int=1000 + event),
    )
    return result, calls, sleeps


def response(content=ORIGINAL, status=200, **kwargs):
    return httpx.Response(status, stream=httpx.ByteStream(content), **kwargs)


@pytest.mark.parametrize("revision", [1, None])
@pytest.mark.parametrize("success_attempt", [1, 2, 3, None])
def test_exact_and_latest_complete_retry_chain(tmp_path, revision, success_attempt):
    archive = LocalRawArchive(tmp_path)
    archive_spy = Mock(wraps=archive)
    parser = Mock(wraps=OmieParser())
    attempts = []

    def handler(request):
        if request.url.path == "/en/file-access-list":
            return response(LISTING)
        attempts.append(request)
        return response(status=200 if len(attempts) == success_attempt else 503)

    result, calls, sleeps = execute(archive_spy, handler, revision=revision, parser=parser)
    assert len(attempts) == (success_attempt or 3)
    assert len(calls) == len(attempts) + (revision is None)
    assert sleeps == [1, 2][: len(attempts) - 1]
    if success_attempt is None:
        assert result.retrieval.outcome is RetrievalOutcome.RETRY_EXHAUSTED
        assert result.parse is None and not list(tmp_path.iterdir())
        parser.parse.assert_not_called()
        archive_spy.persist.assert_not_called()
        archive_spy.persist_parse.assert_not_called()
        return
    assert isinstance(result, IngestionResult)
    assert result.retrieval.source.observed_revision == (revision or 10)
    assert result.retrieval.raw.sha256 == hashlib.sha256(ORIGINAL).hexdigest()
    assert result.retrieval.attempt_count == success_attempt
    assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    assert len(result.parse.records) == 192
    parser.parse.assert_called_once()
    archive_spy.persist.assert_called_once()
    archive_spy.persist_parse.assert_called_once_with(result.parse.provenance)
    assert archive.load(result.retrieval.archive).content == ORIGINAL
    assert archive.load_retrieval(result.retrieval.archive, UUID(int=1)) == result.retrieval
    stored = ParseProvenance.model_validate_json(next(tmp_path.rglob("parses/*.json")).read_bytes())
    assert stored == result.parse.provenance


@pytest.mark.parametrize("revision", [1, None])
def test_explicit_unavailable_has_no_payload_or_parse(tmp_path, revision):
    archive = Mock(wraps=LocalRawArchive(tmp_path))
    parser = Mock(wraps=OmieParser())
    result, calls, sleeps = execute(
        archive,
        lambda req: (
            response(LISTING) if req.url.path == "/en/file-access-list" else response(status=404)
        ),
        revision=revision,
        parser=parser,
    )
    assert result.retrieval.outcome is RetrievalOutcome.UNAVAILABLE
    assert result.retrieval.error_code is ErrorCode.NOT_FOUND
    assert result.retrieval.raw is None and result.parse is None
    assert len(calls) == (1 if revision else 2) and sleeps == []
    archive.persist.assert_not_called()
    parser.parse.assert_not_called()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("listing", [b"<html>irrelevant</html>", None])
def test_listing_failure_never_retrieves_report(tmp_path, listing):
    parser = Mock(wraps=OmieParser())
    result, calls, sleeps = execute(
        LocalRawArchive(tmp_path),
        lambda _: response(listing or b"failed", status=200 if listing else 503),
        revision=None,
        parser=parser,
    )
    assert result.outcome is ResolutionOutcome.FAILURE and result.source is None
    assert result.error_code is (ErrorCode.DISCOVERY_SCHEMA if listing else ErrorCode.HTTP_FAILURE)
    assert len(calls) == (1 if listing else 3)
    assert sleeps == ([] if listing else [1, 2])
    assert {req.url.path for req in calls} == {"/en/file-access-list"}
    parser.parse.assert_not_called()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "content,encoding",
    [(b"", None), (b"malformed", None), (ORIGINAL, "br"), (ORIGINAL, "gzip, br")],
)
def test_malformed_or_encoded_complete_report_survives_repeated_failed_replay(
    tmp_path, content, encoding
):
    archive = LocalRawArchive(tmp_path)
    headers = {"Content-Encoding": encoding} if encoding else {}
    first, calls, sleeps = execute(archive, lambda _: response(content, headers=headers))
    assert first.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert first.parse.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert first.parse.records == () and len(calls) == 1 and sleeps == []
    before = history(tmp_path)
    for event in (2000, 2001):
        acquired = replay(archive, first.retrieval.archive, UUID(int=1))
        parsed = OmieParser().parse(
            acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=event)
        )
        archive.persist_parse(parsed.provenance)
        assert (
            parsed.records == ()
            and parsed.provenance.error_code == first.parse.provenance.error_code
        )
        assert (
            parsed.provenance.normalized_content_identity
            == first.parse.provenance.normalized_content_identity
        )
    preserved(before)
    assert (
        len(list(tmp_path.rglob("payload.bin")))
        == len(list(tmp_path.rglob("retrievals/*.json")))
        == 1
    )
    assert len(list(tmp_path.rglob("parses/*.json"))) == 3


@pytest.mark.parametrize("revision", [1, 2])
@pytest.mark.parametrize("changed", [False, True])
def test_revision_and_republication_identity_matrix(tmp_path, monkeypatch, revision, changed):
    archive = LocalRawArchive(tmp_path)
    first, _, _ = execute(archive, lambda _: response())
    before = history(tmp_path)
    second, _, _ = execute(
        archive, lambda _: response(REVISED if changed else ORIGINAL), event=2, revision=revision
    )
    assert second.retrieval.source.observed_revision == revision
    assert second.retrieval.retrieval_event_id != first.retrieval.retrieval_event_id
    assert (first.retrieval.raw.content_identity == second.retrieval.raw.content_identity) == (
        not changed
    )
    assert (
        first.parse.provenance.normalized_content_identity
        == second.parse.provenance.normalized_content_identity
    ) == (not changed)
    assert len(list(tmp_path.rglob("payload.bin"))) == (2 if changed else 1)
    assert (
        len(list(tmp_path.rglob("retrievals/*.json")))
        == len(list(tmp_path.rglob("parses/*.json")))
        == 2
    )
    assert [r.business_identity for r in first.parse.records] == [
        r.business_identity for r in second.parse.records
    ]
    assert (normalized(first.parse) == normalized(second.parse)) == (not changed)
    preserved(before)

    def forbidden(*args, **kwargs):
        pytest.fail("Replay must not construct HTTP or acquire anything")

    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    monkeypatch.setattr(HttpRetriever, "retrieve", forbidden)
    before_replay = history(tmp_path)
    for index, result in enumerate((first, second)):
        acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
        parsed = OmieParser().parse(
            acquired.payload,
            acquired.provenance,
            parsed_at=NOW + timedelta(days=1),
            parse_event_id=UUID(int=3000 + index),
        )
        archive.persist_parse(parsed.provenance)
        assert normalized(parsed) == normalized(result.parse)
        assert acquired.provenance == result.retrieval
    preserved(before_replay)
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 2


@pytest.mark.parametrize("target", ["payload.bin", "retrievals", "parses"])
def test_runner_persistence_failure_order_and_explicit_offline_recovery(
    tmp_path, monkeypatch, target
):
    archive = LocalRawArchive(tmp_path)
    archive_spy = Mock(wraps=archive)
    parser = Mock(wraps=OmieParser())
    calls = []
    real_link = os.link

    def failing_link(src, dst, **kwargs):
        path = Path(dst)
        if path.name == target or path.parent.name == target:
            raise OSError("password=synthetic-disk-secret")
        return real_link(src, dst, **kwargs)

    def handler(request):
        calls.append(request)
        return response()

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", failing_link)
        with pytest.raises(ArchiveError) as caught:
            execute(archive_spy, handler, parser=parser)
    assert caught.value.code is ErrorCode.ARCHIVE_FAILURE
    assert len(calls) == 1
    assert parser.parse.call_count == (1 if target == "parses" else 0)
    assert len(list(tmp_path.rglob("parses/*.json"))) == 0
    assert not list(tmp_path.rglob(".stage-*"))
    payload, provenance = archive_spy.persist.call_args.args
    if target == "retrievals":
        # A payload orphan is insufficient replay history; never fabricate it.
        from iberian_shakti.ingestion.archive import archive_reference

        with pytest.raises(ReplayError):
            replay(archive, archive_reference(payload.reference), UUID(int=1))
    before = history(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("Explicit recovery reuses already acquired content without HTTP")

    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    acquired = persist_retrieval(RetrievalResult(payload=payload, provenance=provenance), archive)
    parsed = OmieParser().parse(
        acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=9000)
    )
    archive.persist_parse(parsed.provenance)
    recovered = IngestionResult(retrieval=acquired.provenance, parse=parsed)
    assert recovered.parse.provenance.outcome is ParseOutcome.SUCCESS
    assert len(recovered.parse.records) == 192
    preserved(before)
    assert (
        len(list(tmp_path.rglob("payload.bin")))
        == len(list(tmp_path.rglob("retrievals/*.json")))
        == len(list(tmp_path.rglob("parses/*.json")))
        == 1
    )


def test_replay_parse_event_failure_retains_original_history(tmp_path, monkeypatch):
    archive = LocalRawArchive(tmp_path)
    first, _, _ = execute(archive, lambda _: response())
    before = history(tmp_path)
    acquired = replay(archive, first.retrieval.archive, UUID(int=1))
    parsed = OmieParser().parse(
        acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=4000)
    )
    real_link = os.link

    def fail(src, dst, **kwargs):
        if Path(dst).parent.name == "parses":
            raise OSError("synthetic-secret")
        return real_link(src, dst, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", fail)
        with pytest.raises(ArchiveError):
            archive.persist_parse(parsed.provenance)
    preserved(before)
    assert history(tmp_path) == before
    archive.persist_parse(parsed.provenance)
    preserved(before)


def test_parser_version_changes_normalized_identity_but_not_values_or_business_identity(
    tmp_path, monkeypatch
):
    archive = LocalRawArchive(tmp_path)
    first, _, _ = execute(archive, lambda _: response())
    acquired = replay(archive, first.retrieval.archive, UUID(int=1))
    parser = OmieParser()
    monkeypatch.setattr(parser, "parser_version", "1.0.1")
    parsed = parser.parse(
        acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=5000)
    )
    archive.persist_parse(parsed.provenance)
    assert (
        parsed.provenance.normalized_content_identity
        != first.parse.provenance.normalized_content_identity
    )
    assert parsed.provenance.raw.content_identity == first.retrieval.raw.content_identity
    assert normalized(parsed) == normalized(first.parse)
    assert (
        parsed.provenance.normalized_content_identity[-1]
        == parsed.provenance.schema_version
        == "1.0.0"
    )


def test_full_local_ingestion_needs_no_environment_or_credentials(tmp_path, monkeypatch):
    for key in tuple(os.environ):
        if key.startswith(("ESIOS", "ENTSO", "SNOWFLAKE", "OMIE", "INGESTION_")) or key in {
            "RAW_ARCHIVE_ROOT",
            "LOG_LEVEL",
        }:
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("INGESTION_TIMEOUT_SECONDS=invalid\nESIOS_API_TOKEN=unused\n")
    assert load_ingestion_settings().timeout_seconds == 10
    source_path = tmp_path / "input/omie/marginalpdbc/marginalpdbc_20261026.1"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(ORIGINAL)
    listing = Mock()
    result = ingest(
        SourceRequest(
            source_id="omie", report_id="marginalpdbc", delivery_date=date(2026, 10, 26), revision=1
        ),
        adapter=OmieAdapter(),
        listing_retriever=listing,
        retriever=LocalFileRetriever(tmp_path / "input", retrieval_event_id=UUID(int=1)),
        archive=LocalRawArchive(tmp_path / "archive"),
        parser=OmieParser(),
        parsed_at=NOW,
        parse_event_id=UUID(int=1001),
    )
    assert result.parse.provenance.outcome is ParseOutcome.SUCCESS
    assert len(result.parse.records) == 192
    assert result.retrieval.http_status is None and result.retrieval.http is None
    listing.retrieve_listing.assert_not_called()
