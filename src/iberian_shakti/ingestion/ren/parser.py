"""Strict archived-byte REN normalization under the provisional 0.2.0 profile."""

import logging
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import ValidationError

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
    InterchangeMeasure,
    NativeSeries,
    RecordSchema,
    SchemaFamily,
    SupportInterval,
    SystemMeasurement,
)
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.ren import profile
from iberian_shakti.ingestion.ren.identity import validate_resolved
from iberian_shakti.ingestion.ren.schema import ProfileFailure, validate_chart
from iberian_shakti.ingestion.retrieval import require_identity_encoding, source_context

logger = logging.getLogger(__name__)


class RenParser:
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
                validate_resolved(retrieval.source, allow_legacy=True)
                require_identity_encoding(retrieval)
                chart = validate_chart(payload.content)
                day = retrieval.source.request.delivery_date
                intervals = profile.day_intervals(day)
                labels = tuple(
                    period.interval_start_utc.astimezone(ZoneInfo(profile.TIMEZONE)).strftime(
                        "%H:%M"
                    )
                    for period in intervals
                )
                if chart.xAxis.categories != labels:
                    raise ProfileFailure(ErrorCode.CONTENT_INVALID)
                # Exact ordered equality above validates the whole day before
                # emission. Repeated autumn labels keep their physical position.
                records = tuple(
                    SystemMeasurement(
                        source_id=profile.SOURCE_ID,
                        report_id=retrieval.source.request.report_id,
                        delivery_date=day,
                        kind=profile.VALUE_KIND,
                        timing=SupportInterval(
                            start_utc=period.interval_start_utc,
                            end_utc=period.interval_end_utc,
                        ),
                        statistic=profile.STATISTIC,
                        cadence_seconds=profile.PERIOD_MINUTES * 60,
                        native=NativeSeries(
                            series_id=series.name, profile_version=profile.PROFILE_VERSION
                        ),
                        retrieval_event_id=retrieval.retrieval_event_id,
                        parse_event_id=parse_event_id,
                        measure=profile.SELECTED[series.name],
                        geography=(
                            profile.EXTERNAL_BOUNDARY
                            if isinstance(profile.SELECTED[series.name], InterchangeMeasure)
                            else profile.AREA
                        ),
                        unit=profile.UNIT,
                        value=value,
                        publication_status=profile.PUBLICATION_STATUS,
                    )
                    for series in chart.series
                    if series.name in profile.SELECTED
                    for period, value in zip(intervals, series.data, strict=True)
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
            "parsed" if code is None else "validation_failed",
            extra={
                **source_context(retrieval.source),
                "parser_version": self.parser_version,
                "outcome": event.outcome.value,
                "error_code": code.value if code is not None else None,
                "record_count": len(records),
            },
        )
        return ParseResult(provenance=event, records=records)
