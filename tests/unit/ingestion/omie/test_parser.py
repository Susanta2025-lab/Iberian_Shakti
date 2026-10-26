"""Complete report grammar, fixed Decimal/area mapping and fixture integrity."""

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    HttpObservations,
    ParseOutcome,
    RetrievalProvenance,
    SourceRequest,
)
from iberian_shakti.ingestion.omie.identity import PARSER_ID, PARSER_VERSION, resolved_source
from iberian_shakti.ingestion.omie.parser import OmieParser
from iberian_shakti.ingestion.retrieval import result_for

ROOT = Path(__file__).resolve().parents[3] / "data" / "omie"
MANIFEST = json.loads((ROOT / "manifest.json").read_text())["fixtures"]
REPORTS = [item for item in MANIFEST if "valid_report" in item]


@pytest.mark.parametrize("entry", REPORTS, ids=lambda entry: entry["filename"])
def test_committed_report_fixtures(entry, parse_report):
    content = (ROOT / entry["filename"]).read_bytes()
    result = parse_report(content, date.fromisoformat(entry["delivery_date"]), entry["revision"])
    if not entry["valid_report"]:
        assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE
        assert result.provenance.error_code.value == entry["expected_error"]
        assert result.records == () and result.provenance.record_count == 0
        return
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert len(result.records) == entry["expected_period_count"] * 2
    for period in range(entry["expected_period_count"]):
        pt, es = result.records[period * 2 : period * 2 + 2]
        assert (pt.market_area, es.market_area) == ("PT", "ES")
        assert pt.period_index == es.period_index == period + 1
        assert pt.interval_start_utc == es.interval_start_utc
        assert pt.interval_end_utc == es.interval_end_utc
        assert pt.duration_minutes == es.duration_minutes == entry["resolution_minutes"]
        for record in (pt, es):
            assert isinstance(record.price, Decimal)
            assert record.interval_start_utc.utcoffset().total_seconds() == 0
            assert (
                record.market == "day_ahead"
                and record.currency == "EUR"
                and record.price_unit == "MWh"
            )
            assert (record.source_id, record.report_id) == ("omie", "marginalpdbc")
            assert record.delivery_date == date.fromisoformat(entry["delivery_date"])
            assert record.parse_event_id == result.provenance.parse_event_id
    assert len({r.business_identity for r in result.records}) == len(result.records)
    assert result.provenance.parser_id == PARSER_ID
    assert result.provenance.parser_version == PARSER_VERSION
    assert result.provenance.schema_version == "1.0.0"
    assert result.provenance.raw.sha256 == entry["sha256"]
    assert result.provenance.retrieval_event_id == UUID(int=301)


def test_manifest_inventory_and_hashes(manifest, fixture_root):
    names = {entry["filename"] for entry in manifest}
    assert names == {path.name for path in fixture_root.iterdir()} - {"README.md", "manifest.json"}
    assert len(names) == len(manifest)
    for entry in manifest:
        content = (fixture_root / entry["filename"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        assert entry["fixture_type"] in {"original", "synthetic", "mutated"}
        if entry["fixture_type"] == "original":
            assert entry["acquisition_date"] == "2026-10-26"
            assert entry["source_url"].startswith("https://www.omie.es/en/file-download?")


@pytest.mark.parametrize(
    "price", ["+1.23", "-1.23", "0", "-0.00", "+0", "17", "1.2", "1.20", "228.59"]
)
def test_supported_decimal_lexemes(price, parse_report):
    content = (ROOT / "marginalpdbc_20261026.1").read_bytes().replace(b"228.59", price.encode(), 1)
    result = parse_report(content)
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.records[0].price.as_tuple() == Decimal(price).as_tuple()
    assert result.records[1].price == Decimal("228.59")
    assert result.records[0].price != result.records[1].price or price == "228.59"
    assert json.loads(result.records[0].model_dump_json())["price"] == str(Decimal(price))


@pytest.mark.parametrize(
    "price",
    [
        "NaN",
        "Infinity",
        "-inf",
        "1e2",
        "1E-2",
        "1,2",
        "1,000.00",
        "1 000",
        "",
        "1.234",
        "1.",
        ".1",
        "--1",
        "+-1",
        "+",
        " 1",
        "1 ",
        "−1",
    ],
)
def test_rejected_decimal_lexemes(price, parse_report):
    content = (ROOT / "marginalpdbc_20261026.1").read_bytes().replace(b"228.59", price.encode(), 1)
    result = parse_report(content)
    assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert result.records == ()


@pytest.mark.parametrize(
    "ending,final", [(b"\n", b""), (b"\n", b"\n"), (b"\r\n", b""), (b"\r\n", b"\r\n")]
)
def test_supported_line_endings(ending, final, parse_report):
    original = (ROOT / "marginalpdbc_20261026.1").read_bytes()
    content = ending.join(original.splitlines()) + final
    assert parse_report(content).provenance.outcome is ParseOutcome.SUCCESS


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows[1:],
        lambda rows: ["marginalpdbc;"] + rows[1:],
        lambda rows: rows[:2] + [""] + rows[2:],
        lambda rows: rows + ["*"],
        lambda rows: rows + ["", ""],
        lambda rows: rows[:-1] + [" *"],
        lambda rows: rows[:-1] + ["*;"],
        lambda rows: rows[:-2] + ["*"],
        lambda rows: rows[:1] + rows[1:25] + ["*"],
        lambda rows: [row.replace(";96;", ";97;") for row in rows],
        lambda rows: [row.replace(";1;228", ";0;228") for row in rows],
        lambda rows: [row.replace(";1;228", ";01;228") for row in rows],
        lambda rows: [row.replace(";1;228", ";+1;228") for row in rows],
        lambda rows: [row.replace("2026;10;26;", "2026;13;26;", 1) for row in rows],
        lambda rows: [row.replace("2026;10;26;", "2026;02;30;", 1) for row in rows],
        lambda rows: rows[:1] + [rows[1][:-1]] + rows[2:],
        lambda rows: rows[:1] + [rows[1].replace("228.59;228.59;", "228.59;")] + rows[2:],
        lambda rows: rows[:1] + [rows[1].replace("228.59;228.59;", ";228.59;")] + rows[2:],
        lambda rows: rows[:-2] + [rows[-2].rsplit(";", 2)[0] + ";NaN;"] + ["*"],
    ],
)
def test_reject_entire_day_on_structure_error(mutation, parse_report):
    rows = (ROOT / "marginalpdbc_20261026.1").read_text().splitlines()
    result = parse_report("\n".join(mutation(rows)).encode())
    assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert result.provenance.error_code is ErrorCode.CONTENT_INVALID
    assert not result.records and result.provenance.record_count == 0


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"\x00",
        b"\xff",
        b"\xfe\xff",
        b"\xff\xfe",
        b"+/v8-",
        b"<html>error</html>",
        b"MARGINALPDBC;\r1\r*",
    ],
)
def test_rejected_bodies(content, parse_report):
    assert parse_report(content).provenance.outcome is ParseOutcome.CONTENT_FAILURE


def test_original_unequal_columns_and_negative_prices(parse_report):
    result = parse_report((ROOT / "marginalpdbc_20250330.1").read_bytes(), date(2025, 3, 30))
    rows = (ROOT / "marginalpdbc_20250330.1").read_text().splitlines()[1:-1]
    unequal = 0
    for index, row in enumerate(rows):
        pt, es = row.split(";")[4:6]
        assert result.records[index * 2].price == Decimal(pt)
        assert result.records[index * 2 + 1].price == Decimal(es)
        unequal += pt != es
    assert unequal == 6
    assert any(record.price < 0 for record in result.records)


def test_request_date_mismatch(parse_report):
    result = parse_report((ROOT / "marginalpdbc_20261026.1").read_bytes(), date(2026, 10, 27))
    assert not result.records and result.provenance.error_code is ErrorCode.CONTENT_INVALID


@pytest.mark.parametrize("case", ["filename", "encoding", "linkage"])
def test_parser_preconditions(case):
    day = date(2026, 10, 26)
    source = resolved_source(
        SourceRequest(source_id="omie", report_id="marginalpdbc", delivery_date=day, revision=1), 1
    )
    content = (ROOT / "marginalpdbc_20261026.1").read_bytes()
    acquired = result_for(
        source, UUID(int=301), datetime(2026, 10, 26, tzinfo=UTC), content=content
    )
    updates = {}
    if case == "filename":
        source = type(source).model_validate(
            {**source.model_dump(), "filename": "marginalpdbc_20261027.1"}
        )
        updates["source"] = source
    elif case == "encoding":
        updates.update(http=HttpObservations(content_encoding="gzip, br"), http_status=200)
    else:
        updates["raw"] = result_for(
            source, UUID(int=303), datetime(2026, 10, 26, tzinfo=UTC), content=b"other"
        ).payload.reference
    retrieval = RetrievalProvenance.model_validate({**acquired.provenance.model_dump(), **updates})
    result = OmieParser().parse(
        acquired.payload,
        retrieval,
        parsed_at=datetime(2026, 10, 26, tzinfo=UTC),
        parse_event_id=UUID(int=302),
    )
    assert result.records == ()
    assert (
        result.provenance.error_code
        is {
            "filename": ErrorCode.CONTENT_INVALID,
            "encoding": ErrorCode.UNSUPPORTED_ENCODING,
            "linkage": ErrorCode.INTEGRITY_FAILURE,
        }[case]
    )
