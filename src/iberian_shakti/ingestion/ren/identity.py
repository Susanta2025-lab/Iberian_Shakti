"""Safe REN query identity, with exact legacy identities retained for replay."""

from datetime import UTC, date, datetime, time, timedelta

from pydantic import TypeAdapter, ValidationError

from iberian_shakti.contracts.ingestion import ErrorCode, ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, SystemQuery
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.ren import profile
from iberian_shakti.ingestion.retrieval import validate_source

_DATE = TypeAdapter(date, config={"strict": True})


def request_for(source_day: date) -> ApiSourceRequest:
    """Physical source-day window under the pinned provisional empirical profile."""
    day = _DATE.validate_python(source_day)
    intervals = profile.day_intervals(day)
    return ApiSourceRequest(
        source_id=profile.SOURCE_ID,
        report_id=profile.REPORT_ID,
        delivery_date=day,
        window=QueryWindow(
            start_utc=intervals[0].interval_start_utc,
            end_utc=intervals[-1].interval_end_utc,
        ),
        query=SystemQuery(area=profile.AREA, series_ids=tuple(profile.SELECTED)),
    )


def validate_resolved(source: ResolvedSource, *, allow_legacy: bool = False) -> None:
    validate_source(source)
    try:
        request = request_for(source.request.delivery_date)
        if (
            allow_legacy
            and source.request.report_id == f"{profile.PRODUCT}.{profile.CULTURE}.v0.1.0"
        ):
            # Original 0.1.0 windows were UTC partition context only. Reconstruct
            # the exact old contract; never alter archived acquisition metadata.
            start = datetime.combine(request.delivery_date, time.min, UTC)
            request = ApiSourceRequest(
                source_id=request.source_id,
                report_id=f"{profile.PRODUCT}.{profile.CULTURE}.v0.1.0",
                delivery_date=request.delivery_date,
                window=QueryWindow(start_utc=start, end_utc=start + timedelta(days=1)),
                query=request.query,
            )
        expected = ResolvedSource.for_api(request)
    except (ValidationError, ValueError, OverflowError):
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST) from None
    if source != expected:
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST)
