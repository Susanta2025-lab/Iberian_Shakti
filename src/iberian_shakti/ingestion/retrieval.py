"""Shared result assembly and offline file acquisition; no archive side effects."""

import hashlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    HttpObservations,
    RawContentReference,
    RawPayload,
    ResolvedSource,
    RetrievalOutcome,
    RetrievalProvenance,
    RetrievalResult,
)
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason

DEFAULT_MAX_BYTES = 4 * 1024 * 1024
logger = logging.getLogger(__name__)


def source_context(source: ResolvedSource) -> dict[str, object]:
    return {
        "source": source.request.source_id,
        "report": source.request.report_id,
        "delivery_date": source.request.delivery_date.isoformat(),
        "source_filename": source.filename,
        "revision": source.observed_revision,
    }


def require_identity_encoding(provenance: RetrievalProvenance) -> None:
    """Plain-byte parser precondition; call after archiving for diagnosis.

    Never guess, decompress, or silently pass encoded bytes as source text.
    """
    encoding = provenance.http.content_encoding if provenance.http is not None else None
    if encoding is not None and encoding.lower() != "identity":
        raise ExecutionError(ErrorCode.UNSUPPORTED_ENCODING, FailureReason.ENCODING)


def utc_now() -> datetime:
    return datetime.now(UTC)


def validate_source(source: ResolvedSource) -> None:
    try:
        # Revalidate nested state too, including unsupported Pydantic bypasses.
        ResolvedSource.model_validate_json(source.model_dump_json())
    except (ValidationError, AttributeError, TypeError, ValueError) as error:
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST) from error


def validate_size(max_bytes: int) -> None:
    if type(max_bytes) is not int or max_bytes < 1:
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION)


def validate_event_id(event_id: UUID) -> None:
    if not isinstance(event_id, UUID):
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION)


def result_for(
    source: ResolvedSource,
    event_id: UUID,
    completed_at: datetime,
    *,
    attempt: int = 1,
    outcome: RetrievalOutcome = RetrievalOutcome.RETRIEVED,
    content: bytes | None = None,
    code: ErrorCode | None = None,
    status: int | None = None,
    observations: HttpObservations | None = None,
) -> RetrievalResult:
    payload = None
    if content is not None:
        request = source.request
        raw = RawContentReference(
            source_id=request.source_id,
            report_id=request.report_id,
            delivery_date=request.delivery_date,
            sha256=hashlib.sha256(content).hexdigest(),
            byte_length=len(content),
        )
        payload = RawPayload(reference=raw, content=content)
    return RetrievalResult(
        payload=payload,
        provenance=RetrievalProvenance(
            source=source,
            completed_at=completed_at,
            retrieval_event_id=event_id,
            outcome=outcome,
            attempt_count=attempt,
            http_status=status,
            http=observations,
            raw=payload.reference if payload else None,
            error_code=code,
        ),
    )


def contained_path(root: Path, relative: str) -> Path:
    """Reject absolute/traversing paths and symlinks under a trusted local root.

    The root is operator configuration. Its directory tree must not be writable
    by hostile local users; this is not a sandbox against directory-swap attacks.
    """
    parts = relative.split("/")
    if (
        not relative
        or Path(relative).is_absolute()
        or any(p in {"", ".", ".."} for p in parts)
        or "\\" in relative
        or ":" in relative
        or "\x00" in relative
    ):
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.PATH)
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.PATH)
    return path


class LocalFileRetriever:
    """Safe locators are relative to an explicit trusted input root; no file URLs.

    One instance represents one caller-supplied acquisition event. Retrying the
    same event with a changed timestamp is a metadata conflict, not an overwrite.
    """

    def __init__(
        self,
        root: Path,
        *,
        retrieval_event_id: UUID,
        now: Callable[[], datetime] = utc_now,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        validate_size(max_bytes)
        validate_event_id(retrieval_event_id)
        self.root = root
        self.event_id = retrieval_event_id
        self.now = now
        self.max_bytes = max_bytes

    def retrieve(self, source: ResolvedSource) -> RetrievalResult:
        validate_source(source)
        context = source_context(source)
        logger.info("retrieval_attempt", extra={**context, "attempt": 1})
        try:
            path = contained_path(self.root, source.safe_locator)
            with path.open("rb") as stream:
                content = stream.read(self.max_bytes + 1)
        except FileNotFoundError as error:
            logger.warning("retrieval_failed", extra={**context, "error_code": "local_failure"})
            raise ExecutionError(ErrorCode.LOCAL_FAILURE, FailureReason.MISSING) from error
        except OSError as error:
            logger.warning("retrieval_failed", extra={**context, "error_code": "local_failure"})
            raise ExecutionError(ErrorCode.LOCAL_FAILURE, FailureReason.UNREADABLE) from error
        if len(content) > self.max_bytes:
            raise ExecutionError(ErrorCode.SIZE_LIMIT, FailureReason.SIZE)
        logger.info("retrieval_completed", extra={**context, "byte_count": len(content)})
        return result_for(source, self.event_id, self.now(), content=content)
