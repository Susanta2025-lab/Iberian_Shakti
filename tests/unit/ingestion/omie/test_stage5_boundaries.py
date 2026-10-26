"""Strict parser/calendar and adversarial bounded discovery regressions."""

from datetime import date, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import pytest
from test_discovery import http_service, link, listing_retriever, table
from test_parser import ROOT

from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome, ResolutionOutcome
from iberian_shakti.ingestion.omie.adapter import (
    MAX_LISTING_BYTES,
    MAX_LISTING_LINKS,
    OmieAdapter,
)
from iberian_shakti.ingestion.omie.calendar import intervals_for


@pytest.mark.parametrize("price", ["-0", "0.0", "0.00", "+0.00", "999999999999999999999999.99"])
def test_price_precision_and_signed_zero_preserved(price, parse_report):
    body = (ROOT / "marginalpdbc_20261026.1").read_bytes().replace(b"228.59", price.encode(), 1)
    result = parse_report(body)
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.records[0].price.as_tuple() == Decimal(price).as_tuple()


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(lambda rows: [rows[0]], id="header-only"),
        pytest.param(lambda rows: ["*"], id="terminator-only"),
        pytest.param(lambda rows: [" " + rows[0]] + rows[1:], id="leading-header-space"),
        pytest.param(lambda rows: [rows[0] + " "] + rows[1:], id="trailing-header-space"),
        pytest.param(lambda rows: rows[:1] + [" " + rows[1]] + rows[2:], id="leading-row-space"),
        pytest.param(lambda rows: rows[:1] + [rows[1] + " "] + rows[2:], id="trailing-row-space"),
        pytest.param(lambda rows: rows[:-1] + [rows[-2], "*"], id="duplicate-final-period"),
        pytest.param(
            lambda rows: rows[:-1] + [rows[-2].replace(";96;", ";97;"), "*"], id="extra-period"
        ),
        pytest.param(lambda rows: rows[:-1] + ["*", rows[1]], id="data-after-marker"),
        pytest.param(lambda rows: rows[:-1] + ["*", "*"], id="multiple-markers"),
        pytest.param(
            lambda rows: [row.replace(";1;228", ";-1;228") for row in rows], id="negative-period"
        ),
        pytest.param(
            lambda rows: [row.replace(";1;228", ";True;228") for row in rows], id="boolean-period"
        ),
        pytest.param(
            lambda rows: [row.replace(";1;228", ';"1";228') for row in rows], id="quoted-period"
        ),
    ],
)
def test_whole_report_rejected_at_additional_grammar_boundaries(mutation, parse_report):
    rows = (ROOT / "marginalpdbc_20261026.1").read_bytes().decode("ascii").splitlines()
    result = parse_report("\n".join(mutation(rows)).encode())
    assert result.provenance.error_code is ErrorCode.CONTENT_INVALID
    assert result.provenance.record_count == 0 and result.records == ()


@pytest.mark.parametrize("price", ["1.001", "true", '"1.00"', "*", " 1.00 ", "9" * 10_000 + "x"])
def test_bounded_adversarial_price_input_rejected_without_partial_records(price, parse_report):
    content = (ROOT / "marginalpdbc_20261026.1").read_bytes().replace(b"228.59", price.encode(), 1)
    result = parse_report(content)
    assert result.provenance.error_code is ErrorCode.CONTENT_INVALID
    assert result.records == ()


@pytest.mark.parametrize("kind", ["cr-only", "mixed", "nonascii-eof", "bom"])
def test_line_ending_and_byte_boundaries(parse_report, kind):
    body = (ROOT / "marginalpdbc_20261026.1").read_bytes()
    content = {
        "cr-only": body.replace(b"\r\n", b"\r"),
        "mixed": body.replace(b"\r\n", b"\n", 1),
        "nonascii-eof": body + b"\xff",
        "bom": b"\xef\xbb\xbf" + body,
    }[kind]
    result = parse_report(content)
    if kind == "mixed":
        # Each supported line separator is unambiguous; no whitespace is stripped.
        assert result.provenance.outcome is ParseOutcome.SUCCESS
    else:
        assert result.records == ()
        assert result.provenance.error_code is (
            ErrorCode.CONTENT_INVALID if kind == "cr-only" else ErrorCode.UNSUPPORTED_ENCODING
        )


@pytest.mark.parametrize(
    "day,count,expected",
    [
        (date(2026, 3, 29), 96, 92),
        (date(2026, 10, 25), 96, 100),
        (date(2026, 10, 26), 24, 96),
        (date(2025, 9, 30), 96, 24),
        (date(2025, 10, 1), 24, 96),
    ],
)
def test_wrong_day_resolution_or_dst_count_is_rejected(parse_report, day, count, expected):
    body = "\n".join(
        ["MARGINALPDBC;"]
        + [f"{day.year};{day.month};{day.day};{index};1.00;2.00;" for index in range(1, count + 1)]
        + ["*"]
    ).encode()
    assert len(intervals_for(day)) == expected
    result = parse_report(body, day)
    assert result.provenance.error_code is ErrorCode.CONTENT_INVALID and result.records == ()


@pytest.mark.parametrize(
    "day,count,duration",
    [
        (date(2025, 9, 30), 24, 60),
        (date(2025, 10, 1), 96, 15),
        (date(2025, 10, 2), 96, 15),
        (date(2024, 2, 29), 24, 60),
        (date(2028, 2, 29), 96, 15),
        (date(2026, 1, 15), 96, 15),
        (date(2026, 7, 15), 96, 15),
        (date(2026, 3, 28), 96, 15),
        (date(2026, 3, 29), 92, 15),
        (date(2026, 3, 30), 96, 15),
        (date(2026, 10, 24), 96, 15),
        (date(2026, 10, 25), 100, 15),
        (date(2026, 10, 26), 96, 15),
    ],
)
def test_calendar_full_local_day_and_utc_continuity(day, count, duration):
    periods = intervals_for(day)
    timezone = ZoneInfo("Europe/Madrid")
    assert len(periods) == count
    start = periods[0].interval_start_utc
    end = periods[-1].interval_end_utc
    assert start.astimezone(timezone).date() == day
    assert end.astimezone(timezone).date() == day + timedelta(days=1)
    assert start.astimezone(timezone).hour == end.astimezone(timezone).hour == 0
    assert end - start == timedelta(minutes=count * duration)
    assert all(p.duration_minutes == duration for p in periods)
    assert all(
        a.interval_end_utc == b.interval_start_utc
        for a, b in zip(periods, periods[1:], strict=False)
    )
    for fold in (0, 1):
        repeated = [
            p.interval_start_utc.astimezone(timezone)
            for p in periods
            if p.interval_start_utc.astimezone(timezone).hour == 2
            and p.interval_start_utc.astimezone(timezone).fold == fold
        ]
        if day == date(2026, 10, 25):
            assert len(repeated) == 4
        elif day == date(2026, 3, 29):
            assert repeated == []


@pytest.mark.parametrize("extra", [0, 1])
@pytest.mark.parametrize("bound", ["bytes", "candidates"])
def test_listing_exact_bounds(omie_request, clock, bound, extra):
    valid = table("marginalpdbc_20261026.10")
    content = (
        valid + b" " * (MAX_LISTING_BYTES + extra - len(valid))
        if bound == "bytes"
        else b"<table>"
        + link("marginalpdbc_20261026.10").encode()
        + b'<a href="x">x</a>' * (MAX_LISTING_LINKS + extra - 1)
        + b"</table>"
    )
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(content))

    result = OmieAdapter().resolve(omie_request, http_service(handler, clock))
    assert len(calls) == 1 and not clock.sleeps
    if extra:
        assert result.outcome is ResolutionOutcome.FAILURE
        assert result.error_code is (
            ErrorCode.SIZE_LIMIT if bound == "bytes" else ErrorCode.DISCOVERY_SCHEMA
        )
    else:
        assert result.source.observed_revision == 10


@pytest.mark.parametrize(
    "href",
    [
        "/en/%66ile-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99",
        "/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99%26token%3Dsecret",
        "/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026%252e99",
        "/en/file-download?parents=marginalpdbc&parents=marginalpdbc&filename=marginalpdbc_20261026.99",
        "/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99&%66ilename=marginalpdbc_20261026.100",
        "//evil.invalid/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99",
        "/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20260230.99",
        "ftp://www.omie.es/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.99",
    ],
)
def test_encoded_or_ambiguous_links_cannot_select_revision(omie_request, href):
    content = (
        "<table>" + link("decoy", href=href) + link("marginalpdbc_20261026.2") + "</table>"
    ).encode()
    result = OmieAdapter().resolve(omie_request, listing_retriever(content))
    assert result.source.observed_revision == 2


def test_large_valid_revision_is_numeric_and_stays_within_filename_bound(omie_request):
    prefix = "marginalpdbc_20261026."
    revision = "9" * (128 - len(prefix))
    result = OmieAdapter().resolve(
        omie_request,
        listing_retriever(table(prefix + "9", prefix + "10", prefix + revision)),
    )
    assert result.source.observed_revision == int(revision)
    assert len(result.source.filename) == 128


def test_percent_encoded_safe_query_is_reconstructed_as_public_locator(omie_request):
    # URL query escaping is valid only when it decodes to the exact safe grammar.
    href = "/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026%2e10"
    result = OmieAdapter().resolve(
        omie_request, listing_retriever(("<table>" + link("file", href=href) + "</table>").encode())
    )
    assert result.source.observed_revision == 10
    assert result.source.safe_locator == "omie/marginalpdbc/marginalpdbc_20261026.10"
