"""One bounded family-listing observation; no revision probing or crawler."""

import logging
from datetime import date
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ListingRequest,
    ListingRetriever,
    ResolutionOutcome,
    ResolutionResult,
    ResolvedSource,
    RetrievalOutcome,
    SourceRequest,
)
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.omie.identity import (
    LISTING_LOCATOR,
    LISTING_URL,
    ORIGIN,
    REPORT_ID,
    filename_parts,
    resolved_source,
    validate_request,
    validate_resolved,
)
from iberian_shakti.ingestion.omie.parser import OmieParser

MAX_LISTING_PAGES = 1
MAX_LISTING_BYTES = 1024 * 1024
MAX_LISTING_LINKS = 10_000
logger = logging.getLogger(__name__)


class _Listing(HTMLParser):
    """Recognize download anchors inside complete tables; reject ambiguous coverage.

    The observed date span is the only coverage window considered. Pagination
    is detected but never followed. No timestamps/text/HTML enter provenance.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.files: set[tuple[date, int]] = set()
        self.table_depth = 0
        self.closed_tables = 0
        self.links = 0
        self.paginated = False
        self.invalid = False
        self.rejected = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table":
            self.table_depth += 1
        if "pager" in (attributes.get("class") or "").lower():
            self.paginated = True
        if tag != "a":
            return
        self.links += 1
        if self.links > MAX_LISTING_LINKS:
            raise ValueError("candidate_limit")
        href = attributes.get("href")
        if not href:
            return
        if len([key for key, _ in attrs if key == "href"]) != 1:
            self.invalid = True
            return
        try:
            url = urlsplit(urljoin(LISTING_URL, href))
            query = parse_qs(url.query, keep_blank_values=True, max_num_fields=10)
        except ValueError:
            self.rejected = True
            return
        if (
            url.path == "/en/file-access-list"
            and query.get("realdir") == [REPORT_ID]
            and ("page" in query or "next" in (attributes.get("rel") or "").split())
        ):
            self.paginated = True
        if url.path != "/en/file-download":
            return
        filenames = query.get("filename", [])
        if not any(name.startswith("marginalpdbc_") for name in filenames):
            return
        if (
            f"{url.scheme}://{url.netloc}" != ORIGIN
            or url.fragment
            or set(query) != {"parents", "filename"}
            or query.get("parents") != [REPORT_ID]
            or len(filenames) != 1
            or any(character in href for character in "\r\n\t\\")
        ):
            self.rejected = True
            return
        parts = filename_parts(filenames[0])
        if parts is None:
            self.rejected = True
        elif self.table_depth:
            self.files.add(parts)

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            if self.table_depth == 0:
                self.invalid = True
            else:
                self.table_depth -= 1
                self.closed_tables += 1


def _unresolved(
    request: SourceRequest, outcome: ResolutionOutcome, code: ErrorCode
) -> ResolutionResult:
    logger.info(
        "omie_resolution_completed",
        extra={
            "source": request.source_id,
            "report": request.report_id,
            "delivery_date": request.delivery_date.isoformat(),
            "outcome": outcome.value,
            "error_code": code.value,
        },
    )
    return ResolutionResult(request=request, outcome=outcome, error_code=code)


class OmieAdapter:
    parser = OmieParser()

    def resolve(self, request: SourceRequest, retriever: ListingRetriever) -> ResolutionResult:
        validate_request(request)
        if request.revision is not None:
            return self._selected(request, request.revision)
        try:
            acquired = retriever.retrieve_listing(ListingRequest(safe_locator=LISTING_LOCATOR))
        except ExecutionError as error:
            return _unresolved(request, ResolutionOutcome.FAILURE, error.code)
        if acquired.outcome is not RetrievalOutcome.RETRIEVED:
            return _unresolved(
                request, ResolutionOutcome.FAILURE, acquired.error_code or ErrorCode.HTTP_FAILURE
            )
        assert acquired.content is not None
        if len(acquired.content) > MAX_LISTING_BYTES:
            return _unresolved(request, ResolutionOutcome.FAILURE, ErrorCode.SIZE_LIMIT)
        encoding = acquired.http.content_encoding if acquired.http else None
        if encoding is not None and encoding.lower() != "identity":
            return _unresolved(request, ResolutionOutcome.FAILURE, ErrorCode.UNSUPPORTED_ENCODING)
        listing = _Listing()
        try:
            listing.feed(acquired.content.decode("utf-8", errors="strict"))
            listing.close()
        except (ValueError, UnicodeError):
            return _unresolved(request, ResolutionOutcome.FAILURE, ErrorCode.DISCOVERY_SCHEMA)
        if listing.invalid or listing.table_depth or not listing.closed_tables or not listing.files:
            return _unresolved(request, ResolutionOutcome.FAILURE, ErrorCode.DISCOVERY_SCHEMA)
        if listing.paginated:
            return _unresolved(
                request, ResolutionOutcome.COVERAGE_UNKNOWN, ErrorCode.COVERAGE_UNKNOWN
            )
        revisions = [revision for day, revision in listing.files if day == request.delivery_date]
        if revisions:
            return self._selected(request, max(revisions))
        dates = [day for day, _ in listing.files]
        if listing.rejected or not min(dates) <= request.delivery_date <= max(dates):
            return _unresolved(
                request, ResolutionOutcome.COVERAGE_UNKNOWN, ErrorCode.COVERAGE_UNKNOWN
            )
        return _unresolved(request, ResolutionOutcome.UNAVAILABLE, ErrorCode.NOT_LISTED)

    @staticmethod
    def _selected(request: SourceRequest, revision: int) -> ResolutionResult:
        source = resolved_source(request, revision)
        logger.info(
            "omie_resolution_completed",
            extra={
                "source": request.source_id,
                "report": request.report_id,
                "delivery_date": request.delivery_date.isoformat(),
                "revision": revision,
                "source_filename": source.filename,
                "outcome": ResolutionOutcome.RESOLVED.value,
            },
        )
        return ResolutionResult(request=request, outcome=ResolutionOutcome.RESOLVED, source=source)

    def classify_unavailable(self, source: ResolvedSource, http_status: int) -> ErrorCode | None:
        validate_resolved(source)
        return ErrorCode.NOT_FOUND if http_status == 404 else None
