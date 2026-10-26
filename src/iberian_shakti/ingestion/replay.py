"""Offline verified replay exposes existing payload and original acquisition."""

import logging
from uuid import UUID

from iberian_shakti.contracts.ingestion import (
    ArchiveReference,
    RawArchive,
    RetrievalResult,
)
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason, ReplayError

logger = logging.getLogger(__name__)


def replay(
    archive: RawArchive, reference: ArchiveReference, retrieval_event_id: UUID
) -> RetrievalResult:
    """No retriever, clock, event factory, or network dependency exists here.

    Later parsers consume this result using Parser.parse with explicit new
    parse_event_id/parsed_at; RawArchive.persist_parse stores that separate event.
    """
    context = {
        "source": reference.raw.source_id,
        "report": reference.raw.report_id,
        "sha256": reference.raw.sha256,
        "archive_reference": reference.relative_path,
    }
    logger.info("replay_started", extra=context)
    try:
        payload = archive.load(reference)
        acquisition = archive.load_retrieval(reference, retrieval_event_id)
    except ExecutionError as error:
        logger.error("replay_integrity_failure", extra={**context, "error_code": error.code.value})
        raise ReplayError(error.code, FailureReason.REPLAY) from error
    result = RetrievalResult(payload=payload, provenance=acquisition)
    logger.info("replay_completed", extra=context)
    return result
