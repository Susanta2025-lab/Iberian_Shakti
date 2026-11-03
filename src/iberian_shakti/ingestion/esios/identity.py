"""Bounded native-cadence indicator queries, with no secret or aggregation fields."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from iberian_shakti.contracts.ingestion import ErrorCode, ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, SystemQuery
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.esios import profile
from iberian_shakti.ingestion.retrieval import validate_source


def wire_end(window: QueryWindow) -> datetime:
    """Inclusive last grid sample for profile 0.2.0; no local fold guessing."""
    end = window.end_utc - timedelta(seconds=profile.CADENCE_SECONDS)
    for instant in (window.start_utc, window.end_utc):
        if instant.second or instant.microsecond or instant.minute % 5:
            raise ValueError("ESIOS bounded windows require five-minute grid boundaries")
    for instant in (window.start_utc, end):
        local = instant.astimezone(ZoneInfo("Europe/Madrid"))
        if local.replace(fold=0).utcoffset() != local.replace(fold=1).utcoffset():
            raise ValueError("ESIOS ambiguous local wire boundary is unsupported")
    return end


def request_for(window: QueryWindow, *, bounded: bool = False) -> ApiSourceRequest:
    window = QueryWindow.model_validate_json(window.model_dump_json())
    if bounded:
        wire_end(window)
    return ApiSourceRequest(
        source_id=profile.SOURCE_ID,
        report_id=profile.BOUNDED_REPORT_ID if bounded else profile.REPORT_ID,
        delivery_date=window.start_utc.date(),
        window=window,
        query=SystemQuery(area=profile.AREA, series_ids=(str(profile.INDICATOR_ID),)),
    )


def validate_resolved(source: ResolvedSource, *, bounded: bool = False) -> None:
    validate_source(source)
    if not isinstance(source.request, ApiSourceRequest) or source != ResolvedSource.for_api(
        request_for(source.request.window, bounded=bounded)
    ):
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST)
