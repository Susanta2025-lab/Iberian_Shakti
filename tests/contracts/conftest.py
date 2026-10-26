"""Synthetic immutable contract examples; no source fixtures or I/O."""

import hashlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import (
    ArchiveReference,
    ParseOutcome,
    ParseProvenance,
    RawContentReference,
    RawPayload,
    ResolvedSource,
    RetrievalOutcome,
    RetrievalProvenance,
    SourceRequest,
)
from iberian_shakti.contracts.market import MarketPrice


@pytest.fixture
def source_request() -> SourceRequest:
    return SourceRequest(
        source_id="omie", report_id="marginalpdbc", delivery_date=date(2026, 10, 26)
    )


@pytest.fixture
def resolved_source(source_request: SourceRequest) -> ResolvedSource:
    return ResolvedSource(
        request=source_request,
        filename="marginalpdbc_20261026.2",
        observed_revision=2,
        safe_locator="public/marginalpdbc/marginalpdbc_20261026.2",
    )


@pytest.fixture
def raw_payload(source_request: SourceRequest) -> RawPayload:
    content = b"synthetic original bytes\r\n"
    return RawPayload(
        reference=RawContentReference(
            source_id=source_request.source_id,
            report_id=source_request.report_id,
            delivery_date=source_request.delivery_date,
            sha256=hashlib.sha256(content).hexdigest(),
            byte_length=len(content),
        ),
        content=content,
    )


@pytest.fixture
def archive_reference(raw_payload: RawPayload) -> ArchiveReference:
    raw = raw_payload.reference
    return ArchiveReference(
        raw=raw,
        relative_path=(
            f"{raw.source_id}/{raw.report_id}/{raw.delivery_date}/sha256/{raw.sha256}/payload.bin"
        ),
    )


@pytest.fixture
def retrieval_provenance(
    resolved_source: ResolvedSource, raw_payload: RawPayload, archive_reference: ArchiveReference
) -> RetrievalProvenance:
    return RetrievalProvenance(
        source=resolved_source,
        completed_at=datetime(2026, 10, 25, 12, tzinfo=UTC),
        retrieval_event_id=UUID(int=1),
        outcome=RetrievalOutcome.RETRIEVED,
        attempt_count=1,
        http_status=200,
        raw=raw_payload.reference,
        archive=archive_reference,
    )


@pytest.fixture
def parse_provenance(
    retrieval_provenance: RetrievalProvenance,
    raw_payload: RawPayload,
    archive_reference: ArchiveReference,
) -> ParseProvenance:
    return ParseProvenance(
        retrieval_event_id=retrieval_provenance.retrieval_event_id,
        raw=raw_payload.reference,
        archive=archive_reference,
        parser_id="synthetic_parser",
        parser_version="1.0.0",
        parsed_at=datetime(2026, 10, 25, 12, 1, tzinfo=UTC),
        parse_event_id=UUID(int=2),
        outcome=ParseOutcome.SUCCESS,
        record_count=1,
    )


@pytest.fixture
def market_price(parse_provenance: ParseProvenance) -> MarketPrice:
    start = datetime(2026, 10, 25, 23, tzinfo=UTC)
    return MarketPrice(
        source_id="omie",
        report_id="marginalpdbc",
        market="day_ahead",
        market_area="PT",
        delivery_date=date(2026, 10, 26),
        period_index=1,
        duration_minutes=15,
        interval_start_utc=start,
        interval_end_utc=start + timedelta(minutes=15),
        price=Decimal("+12.3400"),
        currency="EUR",
        price_unit="MWh",
        parse_event_id=parse_provenance.parse_event_id,
    )
