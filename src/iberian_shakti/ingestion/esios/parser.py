"""Native timestamped forecast samples with original acquisition/parse linkage."""

import logging
from datetime import datetime
from itertools import pairwise
from uuid import UUID

from pydantic import ValidationError

from iberian_shakti.contracts.geography import Area
from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    MeasurementParseProvenance,
    ParseOutcome,
    ParseResult,
    RawPayload,
    RetrievalOutcome,
    RetrievalProvenance,
)
from iberian_shakti.contracts.measurements import (
    LoadMeasure,
    NativeSeries,
    RecordSchema,
    SchemaFamily,
    SourceTimes,
    Statistic,
    SystemMeasurement,
    ValidInstant,
    ValueKind,
)
from iberian_shakti.contracts.queries import ApiSourceRequest
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.esios import profile
from iberian_shakti.ingestion.esios.identity import validate_resolved
from iberian_shakti.ingestion.esios.schema import (
    ProfileFailure,
    timestamp,
    validate_indicator,
    value_time,
)
from iberian_shakti.ingestion.retrieval import require_identity_encoding, source_context

logger = logging.getLogger(__name__)


class EsiosParser:
    parser_id = profile.PARSER_ID
    parser_version = profile.PARSER_VERSION

    def parse(
        self,
        payload: RawPayload,
        retrieval: RetrievalProvenance,
        *,
        parsed_at: datetime,
        parse_event_id: UUID,
    ) -> ParseResult:
        code: ErrorCode | None = None
        records: tuple[SystemMeasurement, ...] = ()
        try:
            RawPayload(reference=payload.reference, content=payload.content)
            RetrievalProvenance.model_validate_json(retrieval.model_dump_json())
            if (
                retrieval.outcome is not RetrievalOutcome.RETRIEVED
                or retrieval.raw != payload.reference
            ):
                raise ProfileFailure(ErrorCode.INTEGRITY_FAILURE)
        except ValidationError:
            code = ErrorCode.INTEGRITY_FAILURE
        except ProfileFailure as error:
            code = error.code
        else:
            try:
                validate_resolved(retrieval.source)
                require_identity_encoding(retrieval)
                request = retrieval.source.request
                assert isinstance(request, ApiSourceRequest)
                indicator = validate_indicator(payload.content)
                times = tuple(value_time(value) for value in indicator.values)
                # Grid membership + strictly increasing timestamps validate cadence
                # while preserving genuine gaps. Duplicate samples are rejected,
                # including equal duplicates; there is no sorting/deduplication.
                if any(later <= earlier for earlier, later in pairwise(times)):
                    raise ValueError("Unordered or duplicate observations")
                # Retain a possible provider-inclusive end sample unchanged.
                # QueryWindow declares requested context, not returned support;
                # real end-date inclusivity remains a controlled-live check.
                if times[0] < request.window.start_utc or times[-1] > request.window.end_utc:
                    raise ValueError("Observation outside the bounded request")
                source_times = SourceTimes(
                    updated_at=(
                        timestamp(indicator.values_updated_at)
                        if indicator.values_updated_at is not None
                        else None
                    )
                )
                geography = Area(
                    **profile.AREA.model_dump(exclude={"native_id", "native_scheme"}),
                    native_id=str(indicator.values[0].geo_id),
                    native_scheme="provider",
                )
                records = tuple(
                    SystemMeasurement(
                        source_id=profile.SOURCE_ID,
                        report_id=request.report_id,
                        delivery_date=request.delivery_date,
                        kind=ValueKind.FORECAST,
                        timing=ValidInstant(at_utc=at),
                        statistic=Statistic.INSTANT,
                        cadence_seconds=profile.CADENCE_SECONDS,
                        source_times=source_times,
                        native=NativeSeries(
                            series_id=str(indicator.id), profile_version=profile.PROFILE_VERSION
                        ),
                        retrieval_event_id=retrieval.retrieval_event_id,
                        parse_event_id=parse_event_id,
                        measure=LoadMeasure(),
                        geography=geography,
                        unit="MW",
                        value=value.value,
                    )
                    for at, value in zip(times, indicator.values, strict=True)
                )
            except ExecutionError as error:
                code = (
                    ErrorCode.UNSUPPORTED_ENCODING
                    if error.code is ErrorCode.UNSUPPORTED_ENCODING
                    else ErrorCode.SCHEMA_UNSUPPORTED
                )
            except ProfileFailure as error:
                code = error.code
            except (ValidationError, ValueError, OverflowError):
                code = ErrorCode.CONTENT_INVALID
        event = MeasurementParseProvenance(
            retrieval_event_id=retrieval.retrieval_event_id,
            raw=payload.reference,
            archive=(
                retrieval.archive
                if retrieval.archive is not None and retrieval.archive.raw == payload.reference
                else None
            ),
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            record_schema=RecordSchema(family=SchemaFamily.SYSTEM_MEASUREMENT),
            catalogue_version=profile.PROFILE_VERSION,
            parsed_at=parsed_at,
            parse_event_id=parse_event_id,
            outcome=ParseOutcome.SUCCESS if code is None else ParseOutcome.CONTENT_FAILURE,
            error_code=code,
            record_count=len(records),
        )
        logger.info(
            "parse_completed" if code is None else "validation_failed",
            extra={
                **source_context(retrieval.source),
                "parser_version": self.parser_version,
                "outcome": event.outcome.value,
                "error_code": code.value if code is not None else None,
                "record_count": len(records),
            },
        )
        return ParseResult(provenance=event, records=records)
