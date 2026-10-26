"""Finite listing execution through the Stage 3 retry loop; no live HTTP."""

from datetime import date
from html import escape
from unittest.mock import Mock
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ListingRequest,
    ListingResult,
    ResolutionOutcome,
    RetrievalOutcome,
    SourceRequest,
)
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.omie.adapter import MAX_LISTING_LINKS, MAX_LISTING_PAGES, OmieAdapter
from iberian_shakti.ingestion.omie.identity import (
    LISTING_LOCATOR,
    LISTING_URL,
    download_url,
    filename_parts,
    listing_url,
    resolved_source,
)
from iberian_shakti.ingestion.retry import RetryPolicy


def link(filename, **kwargs):
    href = kwargs.get("href", f"/en/file-download?parents=marginalpdbc&filename={filename}")
    return f'<a href="{escape(href, quote=True)}">{escape(filename)}</a>'


def table(*names):
    return (
        "<html><table>"
        + "".join(f"<tr><td>{link(name)}</td></tr>" for name in names)
        + "</table></html>"
    ).encode()


def listing_retriever(content):
    return Mock(
        retrieve_listing=Mock(
            return_value=ListingResult(
                outcome=RetrievalOutcome.RETRIEVED,
                attempt_count=1,
                http_status=200,
                content=content,
            )
        )
    )


class Stream(httpx.SyncByteStream):
    def __init__(self, content):
        self.content = content

    def __iter__(self):
        yield self.content


def http_service(handler, clock, **kwargs):
    return HttpRetriever(
        download_url,
        resolve_listing_url=listing_url,
        retrieval_event_id=UUID(int=401),
        classify_unavailable=OmieAdapter().classify_unavailable,
        transport=httpx.MockTransport(handler),
        clock=clock,
        sleeper=clock.sleep,
        **kwargs,
    )


def test_exact_revision_never_discovers(omie_request):
    request = SourceRequest.model_validate(
        {**omie_request.model_dump(exclude={"selection_mode"}), "revision": 10}
    )
    retriever = Mock()
    result = OmieAdapter().resolve(request, retriever)
    retriever.retrieve_listing.assert_not_called()
    assert result.source.filename == "marginalpdbc_20261026.10"
    assert result.source.observed_revision == 10
    assert result.source.request == request
    assert result.source.safe_locator == "omie/marginalpdbc/marginalpdbc_20261026.10"
    assert (
        download_url(result.source)
        == "https://www.omie.es/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.10"
    )
    assert "?" not in result.model_dump_json()


@pytest.mark.parametrize(
    "revisions,expected",
    [([1], 1), ([1, 2], 2), ([2], 2), ([9, 10], 10), ([10, 9], 10), ([2, 2, 1], 2)],
)
def test_numeric_latest(omie_request, revisions, expected):
    retriever = listing_retriever(table(*(f"marginalpdbc_20261026.{r}" for r in revisions)))
    result = OmieAdapter().resolve(omie_request, retriever)
    assert result.outcome is ResolutionOutcome.RESOLVED
    assert result.source.observed_revision == expected
    retriever.retrieve_listing.assert_called_once_with(ListingRequest(safe_locator=LISTING_LOCATOR))


@pytest.mark.parametrize(
    "unrelated",
    [
        "marginalpdbc_20261025.99",
        "marginalpdbc_20261027.99",
        "other_20261026.99",
        "marginalpdbc_20261026.x",
        "marginalpdbc_20261026.0",
        "marginalpdbc_20261026.-1",
        "marginalpdbc_20261026.01",
        "marginalpdbc_20261026.1.2",
        "marginalpdbc_20261326.1",
    ],
)
def test_ignore_unrelated_and_malformed(omie_request, unrelated):
    result = OmieAdapter().resolve(
        omie_request, listing_retriever(table(unrelated, "marginalpdbc_20261026.2"))
    )
    assert result.source.observed_revision == 2


@pytest.mark.parametrize(
    "href",
    [
        "https://evil.invalid/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99",
        "https://www.omie.es.evil.invalid/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99",
        "http://www.omie.es/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99",
        "https://user:synthetic-secret@www.omie.es/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99",
        "/unexpected?parents=marginalpdbc&filename=marginalpdbc_20261026.99",
        "/en/file-download?parents=other&filename=marginalpdbc_20261026.99",
        "/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99&secret=synthetic-secret",
        "/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99#fragment",
        "/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99&filename=marginalpdbc_20261026.100",
        "javascript:alert(1)",
    ],
)
def test_rejected_links_never_select_or_execute(omie_request, href):
    content = (
        "<table>"
        + link("marginalpdbc_20261026.99", href=href)
        + link("marginalpdbc_20261026.2")
        + "</table>"
    ).encode()
    result = OmieAdapter().resolve(omie_request, listing_retriever(content))
    assert result.source.observed_revision == 2
    assert "synthetic-secret" not in result.model_dump_json()


@pytest.mark.parametrize(
    "name,outcome,code",
    [
        ("listing_covering.html", ResolutionOutcome.UNAVAILABLE, ErrorCode.NOT_LISTED),
        ("listing_paginated.html", ResolutionOutcome.COVERAGE_UNKNOWN, ErrorCode.COVERAGE_UNKNOWN),
        ("listing_malformed.html", ResolutionOutcome.FAILURE, ErrorCode.DISCOVERY_SCHEMA),
    ],
)
def test_listing_fixtures(omie_request, fixture_root, name, outcome, code):
    result = OmieAdapter().resolve(
        omie_request, listing_retriever((fixture_root / name).read_bytes())
    )
    assert result.outcome is outcome and result.error_code is code
    assert result.source is None


@pytest.mark.parametrize(
    "content",
    [
        table("marginalpdbc_20261025.1"),
        table("marginalpdbc_20261027.1"),
        table("marginalpdbc_20200101.1", "marginalpdbc_20200102.1"),
    ],
)
def test_outside_observed_window_is_unknown(omie_request, content):
    result = OmieAdapter().resolve(omie_request, listing_retriever(content))
    assert result.outcome is ResolutionOutcome.COVERAGE_UNKNOWN


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"<table></table>",
        b"<table>\xff</table>",
        ("<table>" + link("marginalpdbc_20261026.1")).encode(),
        link("marginalpdbc_20261026.1").encode(),
        ("<script>" + link("marginalpdbc_20261026.1") + "</script>").encode(),
        ("<table>" + link("marginalpdbc_20261026.x") + "</table>").encode(),
        b'<table><a href="x" href="y">duplicate</a></table>',
    ],
)
def test_unrecognized_schema_is_not_unavailable(omie_request, content):
    result = OmieAdapter().resolve(omie_request, listing_retriever(content))
    assert (
        result.outcome is ResolutionOutcome.FAILURE
        and result.error_code is ErrorCode.DISCOVERY_SCHEMA
    )


@pytest.mark.parametrize("bound", ["size", "candidates"])
def test_listing_parse_bounds(omie_request, bound):
    content = (
        b"x" * (1024 * 1024 + 1)
        if bound == "size"
        else b"<table>" + b'<a href="x">x</a>' * (MAX_LISTING_LINKS + 1) + b"</table>"
    )
    result = OmieAdapter().resolve(omie_request, listing_retriever(content))
    assert result.outcome is ResolutionOutcome.FAILURE
    assert result.error_code is (
        ErrorCode.SIZE_LIMIT if bound == "size" else ErrorCode.DISCOVERY_SCHEMA
    )


def test_bounded_pagination_never_followed(omie_request, fixture_root, clock):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200, stream=Stream((fixture_root / "listing_paginated.html").read_bytes())
        )

    result = OmieAdapter().resolve(omie_request, http_service(handler, clock))
    assert result.outcome is ResolutionOutcome.COVERAGE_UNKNOWN
    assert MAX_LISTING_PAGES == len(requests) == 1
    assert str(requests[0].url) == LISTING_URL
    assert requests[0].extensions["timeout"] == dict.fromkeys(
        ["connect", "read", "write", "pool"], 10
    )


@pytest.mark.parametrize(
    "status,expected_calls,code",
    [
        (302, 1, ErrorCode.HTTP_FAILURE),
        (404, 1, ErrorCode.HTTP_FAILURE),
        (503, 3, ErrorCode.HTTP_FAILURE),
    ],
)
def test_listing_uses_single_existing_retry_loop(omie_request, clock, status, expected_calls, code):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            status, headers={"location": "https://evil.invalid"}, stream=Stream(b"bad")
        )

    result = OmieAdapter().resolve(omie_request, http_service(handler, clock))
    assert result.outcome is ResolutionOutcome.FAILURE and result.error_code is code
    assert len(requests) == expected_calls
    assert all(str(request.url) == LISTING_URL for request in requests)
    assert clock.sleeps == ([1, 2] if status == 503 else [])


def test_listing_retry_success_and_report_disappearance(omie_request, clock):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/en/file-access-list":
            if len(requests) == 1:
                return httpx.Response(503, stream=Stream(b"bad"))
            return httpx.Response(200, stream=Stream(table("marginalpdbc_20261026.2")))
        return httpx.Response(404, stream=Stream(b"missing"))

    service = http_service(handler, clock)
    result = OmieAdapter().resolve(omie_request, service)
    disappeared = service.retrieve(result.source)
    assert result.source.observed_revision == 2
    assert disappeared.provenance.outcome is RetrievalOutcome.UNAVAILABLE
    assert disappeared.provenance.error_code is ErrorCode.NOT_FOUND
    assert disappeared.provenance.attempt_count == 1 and disappeared.payload is None
    assert len(requests) == 3 and clock.sleeps == [1]


@pytest.mark.parametrize("mode", ["size", "duration", "encoding"])
def test_listing_acquisition_bounds(omie_request, clock, mode):
    requests = []

    def handler(request):
        requests.append(request)
        if mode == "duration":
            clock.time += 6
        return httpx.Response(
            200,
            stream=Stream(table("marginalpdbc_20261026.1")),
            headers={"content-encoding": "gzip"} if mode == "encoding" else {},
        )

    kwargs = (
        {"listing_max_bytes": 4}
        if mode == "size"
        else {"policy": RetryPolicy(operation_timeout_seconds=5)}
    )
    result = OmieAdapter().resolve(omie_request, http_service(handler, clock, **kwargs))
    assert result.outcome is ResolutionOutcome.FAILURE
    assert (
        result.error_code
        is {
            "size": ErrorCode.SIZE_LIMIT,
            "duration": ErrorCode.BUDGET_EXCEEDED,
            "encoding": ErrorCode.UNSUPPORTED_ENCODING,
        }[mode]
    )
    assert len(requests) == 1 and not clock.sleeps


@pytest.mark.parametrize("source,report", [("other", "marginalpdbc"), ("omie", "other")])
def test_unsupported_request_fails_before_io(source, report):
    retriever = Mock()
    with pytest.raises(ExecutionError):
        OmieAdapter().resolve(
            SourceRequest(source_id=source, report_id=report, delivery_date=date(2026, 10, 26)),
            retriever,
        )
    retriever.retrieve_listing.assert_not_called()


@pytest.mark.parametrize(
    "filename",
    [
        "marginalpdbc_20260230.1",
        "marginalpdbc_20261026.0",
        "marginalpdbc_20261026.01",
        "marginalpdbc_20261026.1evil",
        "marginalpdbc_20261026." + "9" * 150,
    ],
)
def test_filename_grammar(filename):
    assert filename_parts(filename) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("filename", "marginalpdbc_20261025.1"),
        ("observed_revision", 2),
        ("safe_locator", "other/report"),
    ],
)
def test_private_download_mapper_revalidates_agreement(omie_request, field, value):
    source = resolved_source(omie_request, 1)
    source = type(source).model_validate({**source.model_dump(), field: value})
    with pytest.raises(ExecutionError):
        download_url(source)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(outcome=RetrievalOutcome.RETRIEVED, attempt_count=1, http_status=200),
        dict(outcome=RetrievalOutcome.RETRIEVED, attempt_count=1, http_status=201, content=b""),
        dict(outcome=RetrievalOutcome.UNAVAILABLE, attempt_count=1, error_code=ErrorCode.NOT_FOUND),
        dict(
            outcome=RetrievalOutcome.PERMANENT_FAILURE,
            attempt_count=1,
            content=b"bad",
            error_code=ErrorCode.HTTP_FAILURE,
        ),
    ],
)
def test_listing_contract_rejects_fabricated_success_or_absence(kwargs):
    with pytest.raises(ValidationError):
        ListingResult(**kwargs)


def test_listing_bytes_are_private_and_no_report_history_created(clock):
    result = http_service(
        lambda _: httpx.Response(200, stream=Stream(b"synthetic-secret")), clock
    ).retrieve_listing(ListingRequest(safe_locator=LISTING_LOCATOR))
    assert result.content == b"synthetic-secret"
    assert (
        "synthetic-secret" not in repr(result)
        and "synthetic-secret" not in result.model_dump_json()
    )
    assert not hasattr(result, "provenance")


@pytest.mark.parametrize("kind", ["report", "listing"])
def test_locator_callback_errors_remain_safe_after_shared_loop_refinement(
    omie_request, clock, kind
):
    def invalid(_):
        raise ValueError("synthetic-secret")

    service = http_service(lambda _: pytest.fail("No HTTP expected"), clock)
    service.resolve_url = invalid
    service.resolve_listing_url = invalid
    with pytest.raises(ExecutionError) as caught:
        if kind == "report":
            service.retrieve(resolved_source(omie_request, 1))
        else:
            service.retrieve_listing(ListingRequest(safe_locator=LISTING_LOCATOR))
    assert caught.value.code is ErrorCode.INVALID_LOCATOR
    assert "synthetic-secret" not in str(caught.value)
