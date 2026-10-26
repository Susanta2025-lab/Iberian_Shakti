"""Request, identity, provenance and outcome invariants, entirely offline."""

import builtins
import hashlib
import json
import socket
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import (
    ArchiveReference,
    ErrorCode,
    HttpObservations,
    IngestionResult,
    ParseOutcome,
    ParseProvenance,
    ParseResult,
    RawContentReference,
    RawPayload,
    ResolutionOutcome,
    ResolutionResult,
    ResolvedSource,
    RetrievalOutcome,
    RetrievalProvenance,
    RetrievalResult,
    SelectionMode,
    SourceRequest,
)
from iberian_shakti.contracts.market import MarketPrice


def test_request_default_and_exact_selection(source_request: SourceRequest) -> None:
    assert source_request.selection_mode is SelectionMode.LATEST_OBSERVED
    assert source_request.revision is None
    exact = SourceRequest.model_validate(
        {
            **source_request.model_dump(),
            "revision": 2,
            "selection_mode": SelectionMode.EXACT_REVISION,
        }
    )
    assert exact.selection_mode is SelectionMode.EXACT_REVISION
    assert exact.revision == 2
    assert SourceRequest.model_validate_json(exact.model_dump_json()) == exact


@pytest.mark.parametrize("revision", [0, -1, True, 1.0, "2"])
def test_invalid_revision(source_request: SourceRequest, revision: object) -> None:
    with pytest.raises(ValidationError):
        SourceRequest.model_validate({**source_request.model_dump(), "revision": revision})


@pytest.mark.parametrize("field", ["source_id", "report_id"])
@pytest.mark.parametrize("value", ["", " ", "../x", "x\n", "token=secret", 1])
def test_invalid_identifiers(source_request: SourceRequest, field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        SourceRequest.model_validate({**source_request.model_dump(), field: value})


@pytest.mark.parametrize("value", ["2026-10-26", datetime(2026, 10, 26), "2026-02-30"])
def test_strict_python_request_date(source_request: SourceRequest, value: object) -> None:
    with pytest.raises(ValidationError):
        SourceRequest.model_validate({**source_request.model_dump(), "delivery_date": value})


def test_exact_locator_preserves_revision(source_request: SourceRequest) -> None:
    exact = SourceRequest.model_validate(
        {
            **source_request.model_dump(),
            "revision": 2,
            "selection_mode": SelectionMode.EXACT_REVISION,
        }
    )
    values = dict(request=exact, filename="report.2", safe_locator="public/report.2")
    with pytest.raises(ValidationError):
        ResolvedSource.model_validate(values)
    with pytest.raises(ValidationError):
        ResolvedSource.model_validate({**values, "observed_revision": 1})
    assert ResolvedSource.model_validate({**values, "observed_revision": 2}).request == exact


@pytest.mark.parametrize(
    "locator",
    [
        "https://example.invalid/report",
        "https://user:secret@example.invalid/report",
        "public/report?token=synthetic-secret",
        "public/report?X-Amz-Signature=synthetic-secret",
        "public/report#secret",
        "public/%3Ftoken",
        "/tmp/report",
        "../report",
        "a/../report",
        "a//report",
        "a/./report",
        "a\\report",
        "a/report\n",
        "",
    ],
)
def test_unsafe_locator_rejected(resolved_source: ResolvedSource, locator: str) -> None:
    with pytest.raises(ValidationError):
        ResolvedSource.model_validate({**resolved_source.model_dump(), "safe_locator": locator})


@pytest.mark.parametrize("filename", ["../report", "/tmp/report", "a/report", "", "report?token=x"])
def test_unsafe_filename_rejected(resolved_source: ResolvedSource, filename: str) -> None:
    with pytest.raises(ValidationError):
        ResolvedSource.model_validate({**resolved_source.model_dump(), "filename": filename})


@pytest.mark.parametrize("digest", ["a" * 63, "a" * 65, "A" * 64, "z" * 64, "a" * 64 + "\n", ""])
def test_malformed_sha256(raw_payload: RawPayload, digest: str) -> None:
    with pytest.raises(ValidationError):
        RawContentReference.model_validate({**raw_payload.reference.model_dump(), "sha256": digest})


@pytest.mark.parametrize("length", [-1, True, 1.0, "12"])
def test_invalid_byte_length(raw_payload: RawPayload, length: object) -> None:
    with pytest.raises(ValidationError):
        RawContentReference.model_validate(
            {**raw_payload.reference.model_dump(), "byte_length": length}
        )


def test_exact_byte_hash_and_length(raw_payload: RawPayload) -> None:
    assert raw_payload.reference.sha256 == hashlib.sha256(raw_payload.content).hexdigest()
    for changed in (raw_payload.content.replace(b"\r\n", b"\n"), raw_payload.content + b"x"):
        with pytest.raises(ValidationError):
            RawPayload(reference=raw_payload.reference, content=changed)
    wrong_length = RawContentReference.model_validate(
        {**raw_payload.reference.model_dump(), "byte_length": len(raw_payload.content) + 1}
    )
    with pytest.raises(ValidationError):
        RawPayload(reference=wrong_length, content=raw_payload.content)
    with pytest.raises(ValidationError):
        RawPayload.model_validate({"reference": raw_payload.reference, "content": bytearray(b"x")})
    assert "content" not in raw_payload.model_dump()
    assert "synthetic original" not in repr(raw_payload)


def test_empty_body_is_retrievable_not_parse_success(raw_payload: RawPayload) -> None:
    reference = RawContentReference.model_validate(
        {
            **raw_payload.reference.model_dump(),
            "sha256": hashlib.sha256(b"").hexdigest(),
            "byte_length": 0,
        }
    )
    assert RawPayload(reference=reference, content=b"").reference.byte_length == 0


@pytest.mark.parametrize(
    "path", ["../payload.bin", "/tmp/payload.bin", "a//payload.bin", "other/payload.bin"]
)
def test_archive_path_must_identify_content(archive_reference: ArchiveReference, path: str) -> None:
    with pytest.raises(ValidationError):
        ArchiveReference.model_validate({**archive_reference.model_dump(), "relative_path": path})


def test_content_identity_has_no_revision_or_event_time(
    raw_payload: RawPayload, resolved_source: ResolvedSource
) -> None:
    assert raw_payload.reference.content_identity == (
        "omie",
        "marginalpdbc",
        date(2026, 10, 26),
        raw_payload.reference.sha256,
    )
    changed = ResolvedSource.model_validate(
        {**resolved_source.model_dump(), "observed_revision": 10}
    )
    assert changed.observed_revision != resolved_source.observed_revision
    assert "revision" not in RawContentReference.model_fields


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2026, 10, 26),
        datetime(2026, 10, 26, tzinfo=timezone(timedelta(hours=1))),
        "2026-10-26T00:00:00Z",
    ],
)
def test_retrieval_requires_utc(
    retrieval_provenance: RetrievalProvenance, timestamp: object
) -> None:
    with pytest.raises(ValidationError):
        RetrievalProvenance.model_validate(
            {**retrieval_provenance.model_dump(), "completed_at": timestamp}
        )


def test_http_observations_and_unknown_publication(
    retrieval_provenance: RetrievalProvenance,
) -> None:
    http = HttpObservations(
        content_type="application/octet-stream",
        content_encoding="identity",
        etag='W/"version-2"',
        last_modified=datetime(2026, 10, 25, 11, tzinfo=UTC),
    )
    event = RetrievalProvenance.model_validate({**retrieval_provenance.model_dump(), "http": http})
    assert event.source_published_at is None
    assert event.source.request.selection_mode is SelectionMode.LATEST_OBSERVED
    assert RetrievalProvenance.model_validate_json(event.model_dump_json()) == event
    with pytest.raises(ValidationError):
        http.content_encoding = "gzip"


@pytest.mark.parametrize(
    "values",
    [
        {"Authorization": "Bearer synthetic-secret"},
        {"Cookie": "session=synthetic-secret"},
        {"headers": {"X-API-Key": "synthetic-secret"}},
        {"metadata": {"token": "synthetic-secret"}},
        {"content_type": "text/html\r\nAuthorization: secret"},
        {"etag": "token=secret"},
        {"content_encoding": "gzip\nsecret"},
        {"last_modified": datetime(2026, 10, 25)},
    ],
)
def test_unsafe_http_observations(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        HttpObservations.model_validate(values)


def test_local_retrieval_has_no_http_status(retrieval_provenance: RetrievalProvenance) -> None:
    local = RetrievalProvenance.model_validate(
        {**retrieval_provenance.model_dump(), "http_status": None}
    )
    assert local.http_status is None
    with pytest.raises(ValidationError):
        RetrievalProvenance.model_validate(
            {**local.model_dump(), "http": HttpObservations(etag='"x"')}
        )


@pytest.mark.parametrize(
    ("outcome", "code", "status"),
    [
        (RetrievalOutcome.UNAVAILABLE, ErrorCode.NOT_FOUND, 404),
        (RetrievalOutcome.PERMANENT_FAILURE, ErrorCode.HTTP_FAILURE, 403),
        (RetrievalOutcome.PERMANENT_FAILURE, ErrorCode.LOCAL_FAILURE, None),
        (RetrievalOutcome.RETRY_EXHAUSTED, ErrorCode.TIMEOUT, None),
        (RetrievalOutcome.RETRY_EXHAUSTED, ErrorCode.HTTP_FAILURE, 503),
    ],
)
def test_retrieval_terminal_results(
    retrieval_provenance: RetrievalProvenance,
    outcome: RetrievalOutcome,
    code: ErrorCode,
    status: int | None,
) -> None:
    event = RetrievalProvenance.model_validate(
        {
            **retrieval_provenance.model_dump(),
            "outcome": outcome,
            "error_code": code,
            "http_status": status,
            "raw": None,
            "archive": None,
        }
    )
    assert RetrievalResult(provenance=event).payload is None
    assert IngestionResult(retrieval=event).parse is None


@pytest.mark.parametrize(
    "updates",
    [
        {"raw": None},
        {"error_code": ErrorCode.CONTENT_INVALID},
        {"http_status": 404},
        {"http_status": 99},
        {"http_status": 600},
        {"attempt_count": 0},
        {"attempt_count": True},
        {"outcome": RetrievalOutcome.UNAVAILABLE},
        {"outcome": RetrievalOutcome.RETRY_EXHAUSTED, "error_code": ErrorCode.TIMEOUT},
        {"source_published_at": datetime(2026, 10, 25)},
        {"contract_version": "2.0.0"},
    ],
)
def test_invalid_retrieval_states(
    retrieval_provenance: RetrievalProvenance, updates: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        RetrievalProvenance.model_validate({**retrieval_provenance.model_dump(), **updates})


def test_failed_acquisition_not_absence_or_success(
    retrieval_provenance: RetrievalProvenance,
) -> None:
    base = {**retrieval_provenance.model_dump(), "raw": None, "archive": None}
    for outcome, code in (
        (RetrievalOutcome.UNAVAILABLE, ErrorCode.TIMEOUT),
        (RetrievalOutcome.PERMANENT_FAILURE, ErrorCode.NOT_FOUND),
        (RetrievalOutcome.RETRY_EXHAUSTED, None),
    ):
        with pytest.raises(ValidationError):
            RetrievalProvenance.model_validate({**base, "outcome": outcome, "error_code": code})


def test_raw_and_archive_linkage(
    retrieval_provenance: RetrievalProvenance, raw_payload: RawPayload
) -> None:
    other = RawContentReference.model_validate(
        {**raw_payload.reference.model_dump(), "report_id": "other"}
    )
    with pytest.raises(ValidationError):
        RetrievalProvenance.model_validate({**retrieval_provenance.model_dump(), "raw": other})
    same_source_other_hash = RawContentReference.model_validate(
        {**raw_payload.reference.model_dump(), "sha256": "f" * 64}
    )
    with pytest.raises(ValidationError):
        RetrievalProvenance.model_validate(
            {**retrieval_provenance.model_dump(), "raw": same_source_other_hash}
        )


def test_retrieval_result_requires_matching_payload(
    retrieval_provenance: RetrievalProvenance, raw_payload: RawPayload
) -> None:
    assert (
        RetrievalResult(provenance=retrieval_provenance, payload=raw_payload).payload == raw_payload
    )
    with pytest.raises(ValidationError):
        RetrievalResult(provenance=retrieval_provenance)
    failure = RetrievalProvenance.model_validate(
        {
            **retrieval_provenance.model_dump(),
            "raw": None,
            "archive": None,
            "outcome": RetrievalOutcome.PERMANENT_FAILURE,
            "error_code": ErrorCode.LOCAL_FAILURE,
        }
    )
    with pytest.raises(ValidationError):
        RetrievalResult(provenance=failure, payload=raw_payload)


def test_resolution_outcomes(
    source_request: SourceRequest, resolved_source: ResolvedSource
) -> None:
    assert (
        ResolutionResult(
            request=source_request, outcome=ResolutionOutcome.RESOLVED, source=resolved_source
        ).source
        == resolved_source
    )
    for outcome, code in (
        (ResolutionOutcome.UNAVAILABLE, ErrorCode.NOT_LISTED),
        (ResolutionOutcome.COVERAGE_UNKNOWN, ErrorCode.COVERAGE_UNKNOWN),
        (ResolutionOutcome.COVERAGE_UNKNOWN, ErrorCode.DISCOVERY_SCHEMA),
        (ResolutionOutcome.FAILURE, ErrorCode.TRANSPORT_FAILURE),
    ):
        result = ResolutionResult(request=source_request, outcome=outcome, error_code=code)
        assert result.source is None
        assert ResolutionResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    ("outcome", "code"),
    [
        (ResolutionOutcome.RESOLVED, None),
        (ResolutionOutcome.UNAVAILABLE, None),
        (ResolutionOutcome.UNAVAILABLE, ErrorCode.COVERAGE_UNKNOWN),
        (ResolutionOutcome.COVERAGE_UNKNOWN, ErrorCode.NOT_LISTED),
        (ResolutionOutcome.FAILURE, ErrorCode.NOT_FOUND),
    ],
)
def test_invalid_resolution_states(
    source_request: SourceRequest, outcome: ResolutionOutcome, code: ErrorCode | None
) -> None:
    with pytest.raises(ValidationError):
        ResolutionResult(request=source_request, outcome=outcome, error_code=code)


def test_resolution_request_linkage(
    source_request: SourceRequest, resolved_source: ResolvedSource
) -> None:
    other = SourceRequest.model_validate(
        {
            **source_request.model_dump(),
            "revision": 1,
            "selection_mode": SelectionMode.EXACT_REVISION,
        }
    )
    with pytest.raises(ValidationError):
        ResolutionResult(request=other, outcome=ResolutionOutcome.RESOLVED, source=resolved_source)
    with pytest.raises(ValidationError):
        ResolutionResult(
            request=source_request,
            outcome=ResolutionOutcome.FAILURE,
            error_code=ErrorCode.TRANSPORT_FAILURE,
            source=resolved_source,
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"record_count": 0},
        {"record_count": -1},
        {"record_count": True},
        {"parser_version": ""},
        {"parser_version": "latest"},
        {"schema_version": "2.0.0"},
        {"contract_version": "2.0.0"},
        {"parsed_at": datetime(2026, 10, 25)},
        {"parsed_at": datetime(2026, 10, 25, tzinfo=timezone(timedelta(hours=1)))},
        {"error_code": ErrorCode.CONTENT_INVALID},
        {"outcome": ParseOutcome.CONTENT_FAILURE},
    ],
)
def test_invalid_parse_states(
    parse_provenance: ParseProvenance, updates: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        ParseProvenance.model_validate({**parse_provenance.model_dump(), **updates})


@pytest.mark.parametrize(
    "code", [ErrorCode.CONTENT_INVALID, ErrorCode.UNSUPPORTED_ENCODING, ErrorCode.INTEGRITY_FAILURE]
)
def test_parse_failure_has_no_records(parse_provenance: ParseProvenance, code: ErrorCode) -> None:
    failed = ParseProvenance.model_validate(
        {
            **parse_provenance.model_dump(),
            "outcome": ParseOutcome.CONTENT_FAILURE,
            "record_count": 0,
            "error_code": code,
        }
    )
    assert ParseResult(provenance=failed).records == ()
    with pytest.raises(ValidationError):
        ParseProvenance.model_validate({**failed.model_dump(), "error_code": ErrorCode.NOT_FOUND})


def test_parse_and_ingestion_linkage(
    parse_provenance: ParseProvenance,
    market_price: MarketPrice,
    retrieval_provenance: RetrievalProvenance,
) -> None:
    parsed = ParseResult(provenance=parse_provenance, records=(market_price,))
    result = IngestionResult(retrieval=retrieval_provenance, parse=parsed)
    assert IngestionResult.model_validate_json(result.model_dump_json()) == result
    assert isinstance(result.parse.records, tuple)
    with pytest.raises(ValidationError):
        ParseResult(provenance=parse_provenance)
    with pytest.raises(ValidationError):
        ParseResult.model_validate({"provenance": parse_provenance, "records": [market_price]})
    for field, value in (("parse_event_id", UUID(int=99)), ("report_id", "other")):
        other = MarketPrice.model_validate({**market_price.model_dump(), field: value})
        with pytest.raises(ValidationError):
            ParseResult(provenance=parse_provenance, records=(other,))
    changed = ParseProvenance.model_validate(
        {**parse_provenance.model_dump(), "retrieval_event_id": UUID(int=99)}
    )
    with pytest.raises(ValidationError):
        IngestionResult(
            retrieval=retrieval_provenance,
            parse=ParseResult(provenance=changed, records=(market_price,)),
        )
    with pytest.raises(ValidationError):
        IngestionResult(retrieval=retrieval_provenance)


def test_replay_identity_retains_acquisition_history(parse_provenance: ParseProvenance) -> None:
    replay = ParseProvenance.model_validate(
        {
            **parse_provenance.model_dump(),
            "parse_event_id": UUID(int=3),
            "parsed_at": parse_provenance.parsed_at + timedelta(days=1),
        }
    )
    assert replay.retrieval_event_id == parse_provenance.retrieval_event_id
    assert replay.raw == parse_provenance.raw
    assert replay.normalized_content_identity == parse_provenance.normalized_content_identity
    changed = ParseProvenance.model_validate({**replay.model_dump(), "parser_version": "1.1.0"})
    assert changed.normalized_content_identity != replay.normalized_content_identity


def test_every_contract_frozen_closed_and_roundtrippable(
    source_request: SourceRequest,
    resolved_source: ResolvedSource,
    raw_payload: RawPayload,
    archive_reference: ArchiveReference,
    retrieval_provenance: RetrievalProvenance,
    parse_provenance: ParseProvenance,
) -> None:
    models = (
        source_request,
        resolved_source,
        raw_payload.reference,
        archive_reference,
        retrieval_provenance,
        parse_provenance,
        HttpObservations(etag='"v1"'),
    )
    for model in models:
        assert type(model).model_validate_json(model.model_dump_json()) == model
        field = next(iter(type(model).model_fields))
        with pytest.raises(ValidationError):
            setattr(model, field, getattr(model, field))
        with pytest.raises(ValidationError):
            type(model).model_validate(
                {**model.model_dump(), "metadata": {"token": "synthetic-secret"}}
            )
    assert json.loads(parse_provenance.model_dump_json())["record_count"] == 1


def test_validation_error_text_hides_rejected_values(source_request: SourceRequest) -> None:
    secret = "synthetic-secret?token=synthetic-secret"
    with pytest.raises(ValidationError) as caught:
        SourceRequest.model_validate({**source_request.model_dump(), "source_id": secret})
    assert secret not in str(caught.value)
    assert secret not in repr(caught.value)


def test_construction_never_does_io(
    monkeypatch: pytest.MonkeyPatch, source_request: SourceRequest
) -> None:
    forbidden = Mock(side_effect=AssertionError("Unexpected I/O"))
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(Path, "open", forbidden)
        patch.setattr(Path, "read_bytes", forbidden)
        patch.setattr(Path, "write_bytes", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        SourceRequest.model_validate_json(source_request.model_dump_json())
        raw = RawContentReference(
            source_id="omie",
            report_id="marginalpdbc",
            delivery_date=source_request.delivery_date,
            sha256=hashlib.sha256(b"").hexdigest(),
            byte_length=0,
        )
        RawPayload(reference=raw, content=b"")
        ArchiveReference(
            raw=raw,
            relative_path=f"omie/marginalpdbc/{raw.delivery_date}/sha256/{raw.sha256}/payload.bin",
        )
    forbidden.assert_not_called()


def test_revision_automatically_selects_exact_mode(source_request: SourceRequest) -> None:
    request = SourceRequest(
        source_id=source_request.source_id,
        report_id=source_request.report_id,
        delivery_date=source_request.delivery_date,
        revision=10,
    )
    assert request.selection_mode is SelectionMode.EXACT_REVISION
    assert SourceRequest.model_validate_json(request.model_dump_json()) == request


@pytest.mark.parametrize(
    ("revision", "mode"),
    [
        (None, SelectionMode.EXACT_REVISION),
        (2, SelectionMode.LATEST_OBSERVED),
        (None, "latest_observed"),
    ],
)
def test_selection_mode_consistency(
    source_request: SourceRequest, revision: object, mode: object
) -> None:
    with pytest.raises(ValidationError):
        SourceRequest.model_validate(
            {**source_request.model_dump(), "revision": revision, "selection_mode": mode}
        )


@pytest.mark.parametrize(
    "code",
    [
        ErrorCode.CONTENT_INVALID,
        ErrorCode.ARCHIVE_FAILURE,
        ErrorCode.COVERAGE_UNKNOWN,
        ErrorCode.TLS_FAILURE,
        ErrorCode.LOCAL_FAILURE,
    ],
)
def test_failure_boundaries_do_not_become_retry_exhaustion(
    retrieval_provenance: RetrievalProvenance, code: ErrorCode
) -> None:
    with pytest.raises(ValidationError):
        RetrievalProvenance.model_validate(
            {
                **retrieval_provenance.model_dump(),
                "raw": None,
                "archive": None,
                "outcome": RetrievalOutcome.RETRY_EXHAUSTED,
                "error_code": code,
            }
        )


def test_payload_and_nested_references_are_immutable(
    raw_payload: RawPayload, archive_reference: ArchiveReference
) -> None:
    with pytest.raises(ValidationError):
        raw_payload.content = b"changed"
    with pytest.raises(ValidationError):
        archive_reference.raw.sha256 = "f" * 64


def test_parse_archive_content_must_match(parse_provenance: ParseProvenance) -> None:
    other = RawContentReference.model_validate(
        {**parse_provenance.raw.model_dump(), "sha256": "f" * 64}
    )
    with pytest.raises(ValidationError):
        ParseProvenance.model_validate({**parse_provenance.model_dump(), "raw": other})


def test_retrieved_content_failure_keeps_original_history(
    retrieval_provenance: RetrievalProvenance, parse_provenance: ParseProvenance
) -> None:
    failed = ParseProvenance.model_validate(
        {
            **parse_provenance.model_dump(),
            "outcome": ParseOutcome.CONTENT_FAILURE,
            "record_count": 0,
            "error_code": ErrorCode.CONTENT_INVALID,
        }
    )
    result = IngestionResult(retrieval=retrieval_provenance, parse=ParseResult(provenance=failed))
    assert result.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert result.parse.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert result.retrieval.archive == result.parse.provenance.archive


def test_missing_archive_never_reports_ingestion_success(
    retrieval_provenance: RetrievalProvenance,
    parse_provenance: ParseProvenance,
    market_price: MarketPrice,
) -> None:
    unpersisted = RetrievalProvenance.model_validate(
        {**retrieval_provenance.model_dump(), "archive": None}
    )
    with pytest.raises(ValidationError):
        IngestionResult(
            retrieval=unpersisted,
            parse=ParseResult(provenance=parse_provenance, records=(market_price,)),
        )
