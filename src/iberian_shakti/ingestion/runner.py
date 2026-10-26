"""Synchronous composition of existing acquisition/archive/parser boundaries."""

from datetime import datetime
from uuid import UUID

from iberian_shakti.contracts.ingestion import (
    IngestionResult,
    ListingRetriever,
    Parser,
    RawArchive,
    ResolutionResult,
    Retriever,
    SourceAdapter,
    SourceRequest,
)
from iberian_shakti.ingestion.archive import persist_retrieval
from iberian_shakti.ingestion.retrieval import utc_now


def ingest(
    request: SourceRequest,
    *,
    adapter: SourceAdapter,
    listing_retriever: ListingRetriever,
    retriever: Retriever,
    archive: RawArchive,
    parser: Parser,
    parse_event_id: UUID,
    parsed_at: datetime | None = None,
) -> IngestionResult | ResolutionResult:
    """Unresolved requests retain explicit resolution outcomes without fabricated retrieval.

    Callers can use one HTTP retriever for both boundaries, or independently
    inject a listing acquirer and an offline report retriever. Archive errors
    propagate outside acquisition; there is no retry loop here.
    Capture the parse time after acquisition persistence unless the caller
    explicitly supplies one for deterministic execution.
    """
    resolution = adapter.resolve(request, listing_retriever)
    if resolution.source is None:
        return resolution
    acquired = persist_retrieval(retriever.retrieve(resolution.source), archive)
    if acquired.payload is None:
        return IngestionResult(retrieval=acquired.provenance)
    parsed = parser.parse(
        acquired.payload,
        acquired.provenance,
        parsed_at=parsed_at if parsed_at is not None else utc_now(),
        parse_event_id=parse_event_id,
    )
    archive.persist_parse(parsed.provenance)
    return IngestionResult(retrieval=acquired.provenance, parse=parsed)
