"""One fixed site and complete UTC day per explicit weather product snapshot."""

from datetime import datetime, timedelta

from iberian_shakti.contracts.ingestion import ErrorCode, ResolvedSource
from iberian_shakti.contracts.queries import (
    ApiSourceRequest,
    QueryWindow,
    WeatherOutputSelection,
    WeatherQuery,
)
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.retrieval import validate_source
from iberian_shakti.ingestion.weather import profile


def historical_request_for(window: QueryWindow, site_id: str) -> ApiSourceRequest:
    return _request_for(window, site_id, forecast=False)


def forecast_request_for(window: QueryWindow, site_id: str) -> ApiSourceRequest:
    """Pinned ICON-EU; no model override. Acquisition additionally checks next day."""
    return _request_for(window, site_id, forecast=True)


def _request_for(window: QueryWindow, site_id: str, *, forecast: bool) -> ApiSourceRequest:
    window = QueryWindow.model_validate_json(window.model_dump_json())
    start = window.start_utc
    if (
        start.hour
        or start.minute
        or start.second
        or start.microsecond
        or window.end_utc - start != timedelta(days=1)
    ):
        raise ValueError("Open-Meteo requires one complete UTC day")
    site = next((site for site in profile.SITES if site.site_id == site_id), None)
    if site is None:
        raise ValueError("Unknown Stage 5 site")
    return ApiSourceRequest(
        source_id=profile.SOURCE_ID,
        report_id=profile.FORECAST_REPORT if forecast else profile.HISTORICAL_REPORT,
        delivery_date=start.date(),
        window=window,
        query=WeatherQuery(
            site=site,
            model_id=profile.FORECAST_MODEL if forecast else profile.HISTORICAL_MODEL,
            variables=profile.VARIABLES,
            output=(
                WeatherOutputSelection(profile_version=profile.FORECAST_PROFILE_VERSION)
                if forecast
                else None
            ),
        ),
    )


def validate_forecast_window(window: QueryWindow, acquired_at: datetime) -> None:
    """Bound targets relative to acquisition, without fabricating a run/lead time.

    Replay supplies original completion time. No current clock is used by parsing.
    A request crossing acquisition midnight may fail closed at parse time.
    """
    if (
        acquired_at.utcoffset() != timedelta(0)
        or window.start_utc.date() != (acquired_at + timedelta(days=1)).date()
    ):
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST)


def validate_resolved(
    source: ResolvedSource, *, report_id: str = profile.HISTORICAL_REPORT
) -> None:
    validate_source(source)
    request = source.request
    builder = (
        forecast_request_for if report_id == profile.FORECAST_REPORT else historical_request_for
    )
    try:
        if (
            not isinstance(request, ApiSourceRequest)
            or not isinstance(request.query, WeatherQuery)
            or source != ResolvedSource.for_api(builder(request.window, request.query.site.site_id))
        ):
            raise ValueError("Unsupported weather query")
    except ValueError:
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST) from None
