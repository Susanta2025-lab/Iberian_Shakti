"""Synthetic Stage 3 objects and an advancing clock; no provider fixtures."""

import hashlib
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import (
    ParseOutcome,
    ParseProvenance,
    RawContentReference,
    RawPayload,
    ResolvedSource,
    RetrievalOutcome,
    RetrievalProvenance,
    SourceRequest,
)
from iberian_shakti.ingestion.archive import archive_reference

ACQUIRED_AT = datetime(2026, 10, 26, 12, tzinfo=UTC)
EVENT_ID = UUID(int=101)


class FakeClock:
    def __init__(self) -> None:
        self.time = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.time

    def sleep(self, seconds: float) -> None:
        assert seconds >= 0
        self.sleeps.append(seconds)
        self.time += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def source() -> ResolvedSource:
    return ResolvedSource(
        request=SourceRequest(
            source_id="synthetic", report_id="prices", delivery_date=date(2026, 10, 26)
        ),
        filename="report.1",
        observed_revision=1,
        safe_locator="public/report.1",
    )


@pytest.fixture
def payload(source: ResolvedSource) -> RawPayload:
    content = b"synthetic\r\n\x00\xff"
    return RawPayload(
        reference=RawContentReference(
            source_id=source.request.source_id,
            report_id=source.request.report_id,
            delivery_date=source.request.delivery_date,
            sha256=hashlib.sha256(content).hexdigest(),
            byte_length=len(content),
        ),
        content=content,
    )


@pytest.fixture
def acquisition(source: ResolvedSource, payload: RawPayload) -> RetrievalProvenance:
    return RetrievalProvenance(
        source=source,
        completed_at=ACQUIRED_AT,
        retrieval_event_id=EVENT_ID,
        outcome=RetrievalOutcome.RETRIEVED,
        attempt_count=1,
        http_status=200,
        raw=payload.reference,
    )


@pytest.fixture
def parse_event(payload: RawPayload) -> ParseProvenance:
    return ParseProvenance(
        retrieval_event_id=EVENT_ID,
        raw=payload.reference,
        archive=archive_reference(payload.reference),
        parser_id="synthetic",
        parser_version="1.0.0",
        parsed_at=ACQUIRED_AT,
        parse_event_id=UUID(int=102),
        outcome=ParseOutcome.SUCCESS,
        record_count=1,
    )
