"""Immutable ingestion data and synchronous protocol boundaries.

These contracts perform no network/filesystem work. Public source references
are opaque safe identifiers, never executable URLs or credential containers.
Event IDs are caller-supplied UUIDs, retained across persistence/replay. Raw
content identity and parser/schema versions are independent of event times.
"""

import hashlib
from datetime import date
from enum import StrEnum
from typing import Annotated, Protocol, Self
from uuid import UUID

from pydantic import Field, model_validator

from iberian_shakti.contracts._base import (
    INGESTION_CONTRACT_VERSION,
    MARKET_SCHEMA_VERSION,
    PARSE_PROVENANCE_CONTRACT_VERSION,
    Filename,
    FrozenContract,
    Identifier,
    IngestionContractVersion,
    MarketSchemaVersion,
    NonnegativeInt,
    ParseProvenanceContractVersion,
    PositiveInt,
    SafeReference,
    Sha256,
    UtcDatetime,
    Version,
)
from iberian_shakti.contracts.market import MarketPrice


class SelectionMode(StrEnum):
    EXACT_REVISION = "exact_revision"
    LATEST_OBSERVED = "latest_observed"


class SourceRequest(FrozenContract):
    source_id: Identifier
    report_id: Identifier
    delivery_date: date
    revision: PositiveInt | None = None

    selection_mode: SelectionMode = SelectionMode.LATEST_OBSERVED

    @model_validator(mode="after")
    def consistent_selection(self) -> Self:
        # Derive only an omitted default during construction. Avoid data-aware
        # default factories, which are unavailable in early Pydantic v2 releases
        # permitted by the existing dependency range. Explicit modes stay strict.
        if "selection_mode" not in self.model_fields_set and self.revision is not None:
            object.__setattr__(self, "selection_mode", SelectionMode.EXACT_REVISION)
        if (self.revision is not None) != (self.selection_mode is SelectionMode.EXACT_REVISION):
            raise ValueError(
                "Exact revision selection requires a revision; latest observed omits it"
            )
        return self


class ResolvedSource(FrozenContract):
    request: SourceRequest
    filename: Filename
    observed_revision: PositiveInt | None = None
    safe_locator: SafeReference

    @model_validator(mode="after")
    def consistent_revision(self) -> Self:
        if self.request.revision is not None and self.observed_revision != self.request.revision:
            raise ValueError("Exact selection must retain the requested revision")
        return self


class ErrorCode(StrEnum):
    """Safe categories; source/body/library exception text has no field."""

    NOT_FOUND = "not_found"
    NOT_LISTED = "not_listed"
    COVERAGE_UNKNOWN = "coverage_unknown"
    DISCOVERY_SCHEMA = "discovery_schema"
    TRANSPORT_FAILURE = "transport_failure"
    TIMEOUT = "timeout"
    TLS_FAILURE = "tls_failure"
    INVALID_LOCATOR = "invalid_locator"
    HTTP_FAILURE = "http_failure"
    RATE_LIMITED = "rate_limited"
    LOCAL_FAILURE = "local_failure"
    INCOMPLETE_BODY = "incomplete_body"
    SIZE_LIMIT = "size_limit"
    BUDGET_EXCEEDED = "budget_exceeded"
    CONTENT_INVALID = "content_invalid"
    UNSUPPORTED_ENCODING = "unsupported_encoding"
    ARCHIVE_FAILURE = "archive_failure"
    INTEGRITY_FAILURE = "integrity_failure"


class ResolutionOutcome(StrEnum):
    RESOLVED = "resolved"
    UNAVAILABLE = "unavailable"
    COVERAGE_UNKNOWN = "coverage_unknown"
    FAILURE = "failure"


class ResolutionResult(FrozenContract):
    request: SourceRequest
    outcome: ResolutionOutcome
    source: ResolvedSource | None = None
    error_code: ErrorCode | None = None

    @model_validator(mode="after")
    def consistent_resolution(self) -> Self:
        if self.outcome is ResolutionOutcome.RESOLVED:
            if self.source is None or self.error_code is not None:
                raise ValueError("Resolved outcome requires source and no error")
            if self.source.request != self.request:
                raise ValueError("Resolution must retain the original request")
        elif self.source is not None or self.error_code is None:
            raise ValueError("Unresolved outcome requires an error and no source")
        elif self.outcome is ResolutionOutcome.UNAVAILABLE:
            if self.error_code not in {ErrorCode.NOT_FOUND, ErrorCode.NOT_LISTED}:
                raise ValueError("Unavailable requires explicit absence evidence")
        elif self.outcome is ResolutionOutcome.COVERAGE_UNKNOWN:
            if self.error_code not in {ErrorCode.COVERAGE_UNKNOWN, ErrorCode.DISCOVERY_SCHEMA}:
                raise ValueError("Unknown coverage requires discovery evidence")
        elif self.error_code in {
            ErrorCode.NOT_FOUND,
            ErrorCode.NOT_LISTED,
            ErrorCode.COVERAGE_UNKNOWN,
        }:
            raise ValueError("Use the explicit absence/coverage outcome")
        return self


class RawContentReference(FrozenContract):
    """Content identity includes source/report/day/hash; length guards integrity."""

    source_id: Identifier
    report_id: Identifier
    delivery_date: date
    sha256: Sha256
    byte_length: NonnegativeInt

    @property
    def content_identity(self) -> tuple[str, str, date, str]:
        return self.source_id, self.report_id, self.delivery_date, self.sha256


class RawPayload(FrozenContract):
    """Exact original bytes, excluded from repr/metadata serialization."""

    reference: RawContentReference
    content: bytes = Field(repr=False, exclude=True)

    @model_validator(mode="after")
    def verify_content(self) -> Self:
        if (
            len(self.content) != self.reference.byte_length
            or hashlib.sha256(self.content).hexdigest() != self.reference.sha256
        ):
            raise ValueError("Payload hash/length must match the exact original bytes")
        return self


class ArchiveReference(FrozenContract):
    """Relative to an execution-owned archive root; never resolves/reads a path."""

    raw: RawContentReference
    relative_path: SafeReference

    @model_validator(mode="after")
    def content_addressed_path(self) -> Self:
        expected = (
            f"{self.raw.source_id}/{self.raw.report_id}/{self.raw.delivery_date.isoformat()}/"
            f"sha256/{self.raw.sha256}/payload.bin"
        )
        if self.relative_path != expected:
            raise ValueError("Archive path must identify the linked immutable content")
        return self


class HttpObservations(FrozenContract):
    """Only parsed/allowlisted observations; never pass raw headers here.

    ETag is a bounded HTTP opaque tag, not an identity or publication time.
    Last-Modified is an observation, not a guaranteed first publication time.
    Adapters must never populate these fields with unrelated upstream values.
    """

    content_type: (
        Annotated[
            str, Field(pattern=r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+$", max_length=128)
        ]
        | None
    ) = None
    content_encoding: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,32}$")] | None = None
    etag: Annotated[str, Field(pattern=r'^(W/)?"[!#-~]{0,256}"$')] | None = None
    last_modified: UtcDatetime | None = None


class RetrievalOutcome(StrEnum):
    RETRIEVED = "retrieved"
    UNAVAILABLE = "unavailable"
    PERMANENT_FAILURE = "permanent_failure"
    RETRY_EXHAUSTED = "retry_exhausted"


class RetrievalProvenance(FrozenContract):
    contract_version: IngestionContractVersion = INGESTION_CONTRACT_VERSION
    source: ResolvedSource
    completed_at: UtcDatetime
    retrieval_event_id: UUID
    outcome: RetrievalOutcome
    attempt_count: PositiveInt
    http_status: Annotated[int, Field(ge=100, le=599)] | None = None
    http: HttpObservations | None = None
    raw: RawContentReference | None = None
    archive: ArchiveReference | None = None
    error_code: ErrorCode | None = None
    source_published_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def consistent_retrieval(self) -> Self:
        if self.http is not None and self.http_status is None:
            raise ValueError("HTTP observations require HTTP status")
        if self.outcome is RetrievalOutcome.RETRIEVED:
            if self.raw is None or self.error_code is not None:
                raise ValueError("Retrieved outcome requires raw identity and no error")
            if self.http_status is not None and self.http_status != 200:
                raise ValueError("A retrieved HTTP report requires status 200")
        elif self.raw is not None or self.archive is not None or self.error_code is None:
            raise ValueError("Failed/unavailable acquisition requires error and no raw report")
        elif self.outcome is RetrievalOutcome.UNAVAILABLE:
            if self.error_code not in {ErrorCode.NOT_FOUND, ErrorCode.NOT_LISTED}:
                raise ValueError("Unavailable requires an explicit absence reason")
        elif self.error_code in {
            ErrorCode.NOT_FOUND,
            ErrorCode.NOT_LISTED,
            ErrorCode.COVERAGE_UNKNOWN,
            ErrorCode.DISCOVERY_SCHEMA,
            ErrorCode.CONTENT_INVALID,
            ErrorCode.UNSUPPORTED_ENCODING,
            ErrorCode.ARCHIVE_FAILURE,
            ErrorCode.INTEGRITY_FAILURE,
        }:
            raise ValueError("Use the separate absence/discovery/parse/archive failure boundary")
        elif self.outcome is RetrievalOutcome.RETRY_EXHAUSTED and self.error_code in {
            ErrorCode.TLS_FAILURE,
            ErrorCode.INVALID_LOCATOR,
            ErrorCode.LOCAL_FAILURE,
            ErrorCode.SIZE_LIMIT,
        }:
            raise ValueError("Permanent failures cannot exhaust retries")
        if self.raw is not None:
            request = self.source.request
            if (self.raw.source_id, self.raw.report_id, self.raw.delivery_date) != (
                request.source_id,
                request.report_id,
                request.delivery_date,
            ):
                raise ValueError("Raw reference must match source request")
        if self.archive is not None and self.archive.raw != self.raw:
            raise ValueError("Archive must identify the retrieved content")
        return self


class RetrievalResult(FrozenContract):
    provenance: RetrievalProvenance
    payload: RawPayload | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def consistent_payload(self) -> Self:
        if self.provenance.outcome is RetrievalOutcome.RETRIEVED:
            if self.payload is None or self.payload.reference != self.provenance.raw:
                raise ValueError("Retrieved result requires the linked original payload")
        elif self.payload is not None:
            raise ValueError("Unsuccessful retrieval cannot return a payload")
        return self


class ParseOutcome(StrEnum):
    SUCCESS = "success"
    CONTENT_FAILURE = "content_failure"


class ParseProvenance(FrozenContract):
    contract_version: ParseProvenanceContractVersion = PARSE_PROVENANCE_CONTRACT_VERSION
    retrieval_event_id: UUID
    raw: RawContentReference
    archive: ArchiveReference | None = None
    parser_id: Identifier
    parser_version: Version
    schema_version: MarketSchemaVersion = MARKET_SCHEMA_VERSION
    parsed_at: UtcDatetime
    parse_event_id: UUID
    outcome: ParseOutcome
    error_code: ErrorCode | None = None
    record_count: NonnegativeInt

    @model_validator(mode="after")
    def consistent_parse(self) -> Self:
        if self.outcome is ParseOutcome.SUCCESS:
            if self.record_count == 0 or self.error_code is not None:
                raise ValueError("Successful market parsing requires records and no error")
        elif self.record_count != 0 or self.error_code not in {
            ErrorCode.CONTENT_INVALID,
            ErrorCode.UNSUPPORTED_ENCODING,
            ErrorCode.INTEGRITY_FAILURE,
        }:
            raise ValueError("Failed parsing requires a content/integrity code and zero records")
        if self.archive is not None and self.archive.raw != self.raw:
            raise ValueError("Parse archive must identify original raw content")
        return self

    @property
    def normalized_content_identity(self) -> tuple[tuple[str, str, date, str], str, str, str]:
        return (
            self.raw.content_identity,
            self.parser_id,
            self.parser_version,
            self.schema_version,
        )


class ParseResult(FrozenContract):
    provenance: ParseProvenance
    records: tuple[MarketPrice, ...] = ()

    @model_validator(mode="after")
    def consistent_records(self) -> Self:
        if len(self.records) != self.provenance.record_count:
            raise ValueError("Records must match parse record count")
        raw = self.provenance.raw
        for record in self.records:
            if (
                record.parse_event_id != self.provenance.parse_event_id
                or record.schema_version != self.provenance.schema_version
                or (record.source_id, record.report_id, record.delivery_date)
                != (raw.source_id, raw.report_id, raw.delivery_date)
            ):
                raise ValueError("Normalized records must link to their parse event and raw source")
        return self


class IngestionResult(FrozenContract):
    """Runner result: unavailable has no parse; success requires archived history.

    Archive I/O failures are raised by execution using stable archive error
    codes; an orphan payload or unpersisted event cannot be ingestion success.
    """

    retrieval: RetrievalProvenance
    parse: ParseResult | None = None

    @model_validator(mode="after")
    def consistent_history(self) -> Self:
        if self.retrieval.outcome is RetrievalOutcome.RETRIEVED:
            if self.retrieval.archive is None or self.parse is None:
                raise ValueError("Completed ingestion requires archived retrieval and parse result")
            provenance = self.parse.provenance
            if (
                provenance.retrieval_event_id != self.retrieval.retrieval_event_id
                or provenance.raw != self.retrieval.raw
                or provenance.archive != self.retrieval.archive
            ):
                raise ValueError("Parse must retain original acquisition history")
        elif self.parse is not None:
            raise ValueError("Unsuccessful acquisition cannot have a parse result")
        return self


class SourceAdapter(Protocol):
    def resolve(self, request: SourceRequest, retriever: "Retriever") -> ResolutionResult:
        """Resolve exact/latest observed selection with bounded discovery if needed."""
        ...

    def classify_unavailable(self, source: ResolvedSource, http_status: int) -> ErrorCode | None:
        """Interpret source-specific absence; no transport or retry execution."""
        ...


class Retriever(Protocol):
    def retrieve(self, source: ResolvedSource) -> RetrievalResult:
        """Acquire exact bytes with bounded transport/retry policy; do not parse."""
        ...


class RawArchive(Protocol):
    def persist(self, payload: RawPayload, provenance: RetrievalProvenance) -> ArchiveReference:
        """Persist immutable payload/acquisition event or raise a stable archive failure."""
        ...

    def load(self, reference: ArchiveReference) -> RawPayload:
        """Load and verify exact bytes; no acquisition event is fabricated."""
        ...

    def load_retrieval(
        self, reference: ArchiveReference, retrieval_event_id: UUID
    ) -> RetrievalProvenance:
        """Read original acquisition history for replay, without creating an event."""
        ...

    def persist_parse(self, provenance: ParseProvenance) -> None:
        """Persist a separate immutable parse event, never overwrite retrieval history."""
        ...


class Parser(Protocol):
    def parse(
        self,
        payload: RawPayload,
        retrieval: RetrievalProvenance,
        *,
        parsed_at: UtcDatetime,
        parse_event_id: UUID,
    ) -> ParseResult:
        """Validate whole content, produce records and a distinct versioned parse event."""
        ...
