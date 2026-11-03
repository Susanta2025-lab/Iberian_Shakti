"""Stage 4 semantic parser on the shared archive/provenance/replay contracts."""

import logging
from datetime import datetime
from uuid import UUID

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
    GenerationMeasure,
    LoadMeasure,
    NativeSeries,
    RecordSchema,
    SchemaFamily,
    Statistic,
    SupportInterval,
    SystemMeasurement,
)
from iberian_shakti.contracts.queries import ApiSourceRequest
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.entsoe.acknowledgement import validate_acknowledgement
from iberian_shakti.ingestion.entsoe.identity import validate_resolved
from iberian_shakti.ingestion.entsoe.schema import tag, validate_document
from iberian_shakti.ingestion.entsoe.xml_boundary import ProfileFailure, parse_xml
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.retrieval import require_identity_encoding, source_context

logger = logging.getLogger(__name__)


class EntsoeParser:
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
        outcome = ParseOutcome.SUCCESS
        reason: str | None = None
        records: tuple[SystemMeasurement, ...] = ()
        try:
            RawPayload(reference=payload.reference, content=payload.content)
            RetrievalProvenance.model_validate_json(retrieval.model_dump_json())
            if (
                retrieval.outcome is not RetrievalOutcome.RETRIEVED
                or retrieval.raw != payload.reference
            ):
                raise ProfileFailure(ErrorCode.INTEGRITY_FAILURE)
        except (ValidationError, ProfileFailure):
            code = ErrorCode.INTEGRITY_FAILURE
        else:
            try:
                selected = validate_resolved(retrieval.source)
                require_identity_encoding(retrieval)
                request = retrieval.source.request
                assert isinstance(request, ApiSourceRequest)
                root = parse_xml(payload.content)
                if root.tag == tag("Acknowledgement_MarketDocument", profile.ACK_NAMESPACE):
                    acknowledgement = validate_acknowledgement(root)
                    code, outcome = acknowledgement.code, acknowledgement.outcome
                    reason = acknowledgement.category.value
                elif root.tag == tag("GL_MarketDocument"):
                    document = validate_document(root, selected, request.window)
                    records = tuple(
                        SystemMeasurement(
                            source_id=profile.SOURCE_ID,
                            report_id=request.report_id,
                            delivery_date=request.delivery_date,
                            kind=selected.kind,
                            timing=SupportInterval(start_utc=sample.start, end_utc=sample.end),
                            # Explicit period power without inventing an arithmetic
                            # mean, an instant sample or energy-conversion authority.
                            statistic=Statistic.PROVIDER_PERIOD_VALUE,
                            cadence_seconds=sample.resolution,
                            native=NativeSeries(
                                series_id=series.mrid,
                                document_id=document.mrid,
                                revision_id=document.revision,
                                profile_version=profile.PROFILE_VERSION,
                            ),
                            retrieval_event_id=retrieval.retrieval_event_id,
                            parse_event_id=parse_event_id,
                            measure=(
                                GenerationMeasure(technology=profile.TECHNOLOGIES[series.psr])
                                if series.psr is not None
                                else LoadMeasure()
                            ),
                            geography=selected.area,
                            unit="MW",
                            value=sample.value,
                        )
                        for series in document.series
                        for sample in series.samples
                    )
                    # createdDateTime is retained in the original XML identified
                    # by native.document_id, never promoted to forecast issue/run,
                    # source update or publication metadata without evidence.
                else:
                    raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
            except ExecutionError as error:
                code = (
                    ErrorCode.UNSUPPORTED_ENCODING
                    if error.code is ErrorCode.UNSUPPORTED_ENCODING
                    else ErrorCode.SCHEMA_UNSUPPORTED
                )
            except ProfileFailure as error:
                code = error.code
                if code is ErrorCode.UNSUPPORTED_DOMAIN:
                    outcome = ParseOutcome.PROVIDER_REJECTED
            except (ValidationError, ValueError, OverflowError):
                code = ErrorCode.CONTENT_INVALID
        if code is not None and outcome is ParseOutcome.SUCCESS:
            outcome = ParseOutcome.CONTENT_FAILURE
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
            outcome=outcome,
            error_code=code,
            record_count=len(records),
        )
        logger.info(
            "parse_completed" if code is None else "validation_failed",
            extra={
                **source_context(retrieval.source),
                "parser_version": self.parser_version,
                "outcome": outcome.value,
                "error_code": code.value if code is not None else None,
                "reason": reason,
                "record_count": len(records),
            },
        )
        return ParseResult(provenance=event, records=records)
