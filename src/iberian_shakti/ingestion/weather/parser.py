"""Explicit hourly weather products with strict coverage and shared provenance."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal
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
    NativeSeries,
    RecordSchema,
    SchemaFamily,
    Statistic,
    SupportInterval,
    ValidInstant,
    ValueKind,
    WeatherMeasurement,
    WeatherVariable,
)
from iberian_shakti.contracts.queries import ApiSourceRequest, WeatherQuery
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.retrieval import require_identity_encoding, source_context
from iberian_shakti.ingestion.weather import profile
from iberian_shakti.ingestion.weather.identity import validate_forecast_window, validate_resolved
from iberian_shakti.ingestion.weather.schema import ProfileFailure, validate_document

logger = logging.getLogger(__name__)

_VARIABLES: tuple[tuple[str, WeatherVariable, float | None, Literal["°C", "m/s", "W/m²"]], ...] = (
    ("temperature_2m", WeatherVariable.TEMPERATURE, 2.0, "°C"),
    ("wind_speed_10m", WeatherVariable.WIND_SPEED, 10.0, "m/s"),
    ("shortwave_radiation", WeatherVariable.SHORTWAVE_RADIATION, None, "W/m²"),
)


class OpenMeteoParser:
    parser_id = profile.PARSER_ID
    parser_version = profile.PARSER_VERSION
    profile_version = profile.PROFILE_VERSION
    report_id = profile.HISTORICAL_REPORT
    model_id = profile.HISTORICAL_MODEL
    kind = ValueKind.REANALYSIS

    def parse(
        self,
        payload: RawPayload,
        retrieval: RetrievalProvenance,
        *,
        parsed_at: datetime,
        parse_event_id: UUID,
    ) -> ParseResult:
        code: ErrorCode | None = None
        records: tuple[WeatherMeasurement, ...] = ()
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
                validate_resolved(retrieval.source, report_id=self.report_id)
                require_identity_encoding(retrieval)
                request = retrieval.source.request
                assert isinstance(request, ApiSourceRequest) and isinstance(
                    request.query, WeatherQuery
                )
                if self.kind is ValueKind.FORECAST:
                    validate_forecast_window(request.window, retrieval.completed_at)
                document = validate_document(payload.content, model_id=self.model_id)
                times = tuple(datetime.fromtimestamp(t, UTC) for t in document.hourly.time)
                expected = tuple(request.window.start_utc + timedelta(hours=i) for i in range(24))
                if times != expected:
                    # Reject missing/duplicate/unordered/off-grid/outside values;
                    # UTC day coverage is strict, without filling or sorting.
                    raise ValueError("Incomplete or invalid hourly UTC coverage")
                grid = document.grid()
                records = tuple(
                    WeatherMeasurement(
                        source_id=profile.SOURCE_ID,
                        report_id=request.report_id,
                        delivery_date=request.delivery_date,
                        kind=self.kind,
                        model_id=request.query.model_id,
                        site=request.query.site,
                        returned_grid=grid,
                        variable=variable,
                        height_m=height,
                        unit=unit,
                        value=getattr(document.hourly, name)[i],
                        timing=(
                            SupportInterval(start_utc=at - timedelta(hours=1), end_utc=at)
                            if variable is WeatherVariable.SHORTWAVE_RADIATION
                            else ValidInstant(at_utc=at)
                        ),
                        statistic=(
                            Statistic.MEAN
                            if variable is WeatherVariable.SHORTWAVE_RADIATION
                            else Statistic.INSTANT
                        ),
                        cadence_seconds=profile.CADENCE_SECONDS,
                        native=NativeSeries(series_id=name, profile_version=self.profile_version),
                        retrieval_event_id=retrieval.retrieval_event_id,
                        parse_event_id=parse_event_id,
                    )
                    for i, at in enumerate(times)
                    for name, variable, height, unit in _VARIABLES
                )
            except ExecutionError as error:
                code = (
                    ErrorCode.UNSUPPORTED_ENCODING
                    if error.code is ErrorCode.UNSUPPORTED_ENCODING
                    else ErrorCode.SCHEMA_UNSUPPORTED
                )
            except ProfileFailure as error:
                code = error.code
            except (ValidationError, ValueError, OverflowError, OSError):
                code = ErrorCode.CONTENT_INVALID
        outcome = (
            ParseOutcome.SUCCESS
            if code is None
            else (
                ParseOutcome.PROVIDER_REJECTED
                if code is ErrorCode.PROVIDER_REJECTED
                else ParseOutcome.CONTENT_FAILURE
            )
        )
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
            record_schema=RecordSchema(family=SchemaFamily.WEATHER_MEASUREMENT),
            catalogue_version=self.profile_version,
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
                "error_code": code.value if code else None,
                "record_count": len(records),
            },
        )
        return ParseResult(provenance=event, records=records)


class IconEuParser(OpenMeteoParser):
    parser_id = profile.FORECAST_PARSER_ID
    parser_version = profile.FORECAST_PARSER_VERSION
    profile_version = profile.FORECAST_PROFILE_VERSION
    report_id = profile.FORECAST_REPORT
    model_id = profile.FORECAST_MODEL
    kind = ValueKind.FORECAST
