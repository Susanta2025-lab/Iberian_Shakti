"""Bounded native-cadence indicator queries, with no secret or aggregation fields."""

from iberian_shakti.contracts.ingestion import ErrorCode, ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, SystemQuery
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.esios import profile
from iberian_shakti.ingestion.retrieval import validate_source


def request_for(window: QueryWindow) -> ApiSourceRequest:
    window = QueryWindow.model_validate_json(window.model_dump_json())
    return ApiSourceRequest(
        source_id=profile.SOURCE_ID,
        report_id=profile.REPORT_ID,
        delivery_date=window.start_utc.date(),
        window=window,
        query=SystemQuery(area=profile.AREA, series_ids=(str(profile.INDICATOR_ID),)),
    )


def validate_resolved(source: ResolvedSource) -> None:
    validate_source(source)
    if not isinstance(source.request, ApiSourceRequest) or source != ResolvedSource.for_api(
        request_for(source.request.window)
    ):
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST)
