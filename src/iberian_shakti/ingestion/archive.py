"""Local immutable content/events using same-filesystem staging and hard links.

The configured root is trusted and must be excluded from Git. No mkdir or I/O
occurs at construction. Published files are never opened for writing. Hard-link
publication fails atomically if a destination exists; the losing writer verifies
the winner. This requires a local filesystem supporting hard links and fsync.
"""

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import (
    ArchiveReference,
    ErrorCode,
    ParseProvenance,
    RawArchive,
    RawContentReference,
    RawPayload,
    RetrievalOutcome,
    RetrievalProvenance,
    RetrievalResult,
)
from iberian_shakti.ingestion.config import IngestionSettings
from iberian_shakti.ingestion.errors import ArchiveError, ExecutionError, FailureReason
from iberian_shakti.ingestion.retrieval import contained_path

logger = logging.getLogger(__name__)
_METADATA_MAX_BYTES = 64 * 1024


def archive_reference(raw: RawContentReference) -> ArchiveReference:
    return ArchiveReference(
        raw=raw,
        relative_path=(
            f"{raw.source_id}/{raw.report_id}/{raw.delivery_date}/sha256/{raw.sha256}/payload.bin"
        ),
    )


def _canonical(event: RetrievalProvenance | ParseProvenance) -> bytes:
    return json.dumps(
        json.loads(event.model_dump_json()),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _integrity() -> ArchiveError:
    logger.error("archive_integrity_error", extra={"error_code": ErrorCode.INTEGRITY_FAILURE.value})
    return ArchiveError(ErrorCode.INTEGRITY_FAILURE, FailureReason.INTEGRITY)


class LocalRawArchive:
    def __init__(self, root: Path = Path("data/raw")) -> None:
        self.root = root

    @classmethod
    def from_settings(cls, settings: IngestionSettings) -> "LocalRawArchive":
        return cls(settings.raw_archive_root)

    def _path(self, reference: ArchiveReference) -> Path:
        try:
            ArchiveReference.model_validate_json(reference.model_dump_json())
            return contained_path(self.root, reference.relative_path)
        except (ValidationError, ExecutionError, ValueError) as error:
            raise ArchiveError(ErrorCode.INVALID_LOCATOR, FailureReason.PATH) from error
        except OSError as error:
            raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.PERMISSION) from error

    def _event_path(self, reference: ArchiveReference, category: str, event_id: UUID) -> Path:
        if not isinstance(event_id, UUID):
            raise ArchiveError(ErrorCode.INVALID_LOCATOR, FailureReason.PATH)
        payload = self._path(reference)
        relative = str(Path(reference.relative_path).parent / category / f"{event_id}.json")
        try:
            path = contained_path(self.root, relative)
        except ExecutionError as error:
            raise ArchiveError(ErrorCode.INVALID_LOCATOR, FailureReason.PATH) from error
        except OSError as error:
            raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.PERMISSION) from error
        assert path.parent.parent == payload.parent
        return path

    @staticmethod
    def _read(path: Path, limit: int) -> bytes:
        try:
            with path.open("rb") as stream:
                content = bytearray()
                remaining = limit + 1
                while remaining:
                    chunk = stream.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    content.extend(chunk)
                    remaining -= len(chunk)
        except FileNotFoundError as error:
            raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.MISSING) from error
        except OSError as error:
            raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.UNREADABLE) from error
        if len(content) > limit:
            raise _integrity()
        return bytes(content)

    @staticmethod
    def _stage_write(descriptor: int, data: bytes) -> None:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o444)

    def _publish(self, path: Path, data: bytes, *, metadata: bool) -> bool:
        staged: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Recheck the path after directory creation, before any file write.
            contained_path(self.root, path.relative_to(self.root).as_posix())
            descriptor, name = tempfile.mkstemp(prefix=".stage-", dir=path.parent)
            staged = Path(name)
            self._stage_write(descriptor, data)
            created = True
            try:
                os.link(staged, path, follow_symlinks=False)
            except FileExistsError as error:
                created = False
                if path.is_symlink() or self._read(path, len(data)) != data:
                    raise _integrity() from error
            if created:
                directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            return created
        except PermissionError as error:
            raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, FailureReason.PERMISSION) from error
        except ExecutionError as error:
            if isinstance(error, ArchiveError):
                raise
            raise ArchiveError(ErrorCode.INVALID_LOCATOR, FailureReason.PATH) from error
        except OSError as error:
            reason = FailureReason.METADATA if metadata else FailureReason.ARCHIVE_IO
            raise ArchiveError(ErrorCode.ARCHIVE_FAILURE, reason) from error
        finally:
            if staged is not None:
                try:
                    staged.unlink(missing_ok=True)
                except OSError as error:
                    raise ArchiveError(
                        ErrorCode.ARCHIVE_FAILURE, FailureReason.PERMISSION
                    ) from error

    def persist(self, payload: RawPayload, provenance: RetrievalProvenance) -> ArchiveReference:
        reference = archive_reference(payload.reference)
        try:
            # Validate all linkage before creating directories or writing bytes.
            RawPayload(reference=payload.reference, content=payload.content)
            if (
                provenance.raw != payload.reference
                or provenance.outcome is not RetrievalOutcome.RETRIEVED
            ):
                raise _integrity()
            if provenance.archive is not None and provenance.archive != reference:
                raise _integrity()
            event = RetrievalProvenance.model_validate(
                {**provenance.model_dump(), "archive": reference}
            )
            event = RetrievalProvenance.model_validate_json(event.model_dump_json())
        except ValidationError as error:
            raise _integrity() from error
        path = self._path(reference)
        created = self._publish(path, payload.content, metadata=False)
        # Check hash/length even when another writer supplied the existing file.
        self.load(reference)
        context = {
            "source": reference.raw.source_id,
            "report": reference.raw.report_id,
            "delivery_date": reference.raw.delivery_date.isoformat(),
            "sha256": reference.raw.sha256,
            "byte_count": reference.raw.byte_length,
            "archive_reference": reference.relative_path,
        }
        logger.info("archive_completed" if created else "content_reused", extra=context)
        self._publish(
            self._event_path(reference, "retrievals", event.retrieval_event_id),
            _canonical(event),
            metadata=True,
        )
        logger.info("retrieval_provenance_persisted", extra=context)
        return reference

    def load(self, reference: ArchiveReference) -> RawPayload:
        path = self._path(reference)
        content = self._read(path, reference.raw.byte_length)
        if (
            len(content) != reference.raw.byte_length
            or hashlib.sha256(content).hexdigest() != reference.raw.sha256
        ):
            raise _integrity()
        return RawPayload(reference=reference.raw, content=content)

    def load_retrieval(
        self, reference: ArchiveReference, retrieval_event_id: UUID
    ) -> RetrievalProvenance:
        path = self._event_path(reference, "retrievals", retrieval_event_id)
        content = self._read(path, _METADATA_MAX_BYTES)
        try:
            event = RetrievalProvenance.model_validate_json(content)
        except ValidationError as error:
            raise _integrity() from error
        if (
            event.archive != reference
            or event.raw != reference.raw
            or event.retrieval_event_id != retrieval_event_id
            or event.outcome is not RetrievalOutcome.RETRIEVED
        ):
            raise _integrity()
        return event

    def persist_parse(self, provenance: ParseProvenance) -> None:
        try:
            event = ParseProvenance.model_validate_json(provenance.model_dump_json())
        except ValidationError as error:
            raise _integrity() from error
        if event.archive is None:
            raise _integrity()
        self.load(event.archive)
        retrieval = self.load_retrieval(event.archive, event.retrieval_event_id)
        if retrieval.raw != event.raw or event.parse_event_id == event.retrieval_event_id:
            raise _integrity()
        self._publish(
            self._event_path(event.archive, "parses", event.parse_event_id),
            _canonical(event),
            metadata=True,
        )


def persist_retrieval(result: RetrievalResult, archive: RawArchive) -> RetrievalResult:
    """Return archived acquisition only after both payload and event have persisted."""
    if result.payload is None:
        return result
    reference = archive.persist(result.payload, result.provenance)
    provenance = RetrievalProvenance.model_validate(
        {**result.provenance.model_dump(), "archive": reference}
    )
    return RetrievalResult(provenance=provenance, payload=result.payload)
