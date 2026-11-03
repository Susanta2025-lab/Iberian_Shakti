"""Versioned, nonsecret product/domain/window identity using shared queries."""

from iberian_shakti.contracts.ingestion import ErrorCode, ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, SystemQuery
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.retrieval import validate_source


def request_for(
    product: profile.Product, country: profile.Country, window: QueryWindow
) -> ApiSourceRequest:
    selected = profile.product_profile(product, country)
    window = QueryWindow.model_validate_json(window.model_dump_json())
    if any(at.second or at.microsecond for at in (window.start_utc, window.end_utc)):
        raise ValueError("ENTSO-E requests require whole UTC minutes")
    return ApiSourceRequest(
        source_id=profile.SOURCE_ID,
        report_id=selected.report_id,
        delivery_date=window.start_utc.date(),
        window=window,
        query=SystemQuery(
            area=selected.area,
            series_ids=(f"{selected.document_type}.{selected.process_type}",),
        ),
    )


def validate_resolved(source: ResolvedSource) -> profile.ProductProfile:
    validate_source(source)
    request = source.request
    if isinstance(request, ApiSourceRequest):
        for selected in profile.PROFILES:
            try:
                expected = request_for(selected.product, selected.country, request.window)
            except ValueError:
                break
            if source == ResolvedSource.for_api(expected):
                return selected
    raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST)
