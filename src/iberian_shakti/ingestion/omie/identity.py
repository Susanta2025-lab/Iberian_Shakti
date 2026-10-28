"""Selected report identity and execution-private URL construction."""

import re
from datetime import date
from urllib.parse import urlencode

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ListingRequest,
    ResolvedSource,
    SourceRequest,
)
from iberian_shakti.contracts.queries import ApiSourceRequest
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason

SOURCE_ID = "omie"
REPORT_ID = "marginalpdbc"
MARKET = "day_ahead"
PARSER_ID = "omie.marginalpdbc"
PARSER_VERSION = "1.0.0"
ORIGIN = "https://www.omie.es"
LISTING_LOCATOR = "omie/marginalpdbc/listing"
LISTING_URL = f"{ORIGIN}/en/file-access-list?realdir=marginalpdbc"
FILENAME = re.compile(r"marginalpdbc_([0-9]{8})\.([1-9][0-9]*)", re.ASCII)


def validate_request(request: SourceRequest | ApiSourceRequest) -> None:
    SourceRequest.model_validate_json(request.model_dump_json())
    if (request.source_id, request.report_id) != (SOURCE_ID, REPORT_ID):
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST)


def filename_for(day: date, revision: int) -> str:
    return f"marginalpdbc_{day.year:04d}{day.month:02d}{day.day:02d}.{revision}"


def filename_parts(filename: str) -> tuple[date, int] | None:
    if len(filename) > 128:
        return None
    match = FILENAME.fullmatch(filename)
    if match is None:
        return None
    stamp, revision = match.groups()
    try:
        day = date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:]))
    except ValueError:
        return None
    return day, int(revision)


def resolved_source(request: SourceRequest, revision: int) -> ResolvedSource:
    validate_request(request)
    filename = filename_for(request.delivery_date, revision)
    source = ResolvedSource(
        request=request,
        filename=filename,
        observed_revision=revision,
        safe_locator=f"omie/marginalpdbc/{filename}",
    )
    validate_resolved(source)
    return source


def validate_resolved(source: ResolvedSource) -> None:
    validate_request(source.request)
    expected = (source.request.delivery_date, source.observed_revision)
    if (
        filename_parts(source.filename) != expected
        or source.safe_locator != f"omie/marginalpdbc/{source.filename}"
    ):
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SOURCE_REQUEST)


def download_url(source: ResolvedSource) -> str:
    validate_resolved(source)
    return f"{ORIGIN}/en/file-download?" + urlencode(
        {"parents": REPORT_ID, "filename": source.filename}
    )


def listing_url(request: ListingRequest) -> str:
    if request.safe_locator != LISTING_LOCATOR:
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR)
    return LISTING_URL
