"""Synthetic REN source periods normalize only under the pinned empirical profile."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome, RawPayload
from iberian_shakti.contracts.measurements import Statistic, SupportInterval, SystemMeasurement
from iberian_shakti.ingestion.ren import profile
from iberian_shakti.ingestion.ren.adapter import RenAdapter
from iberian_shakti.ingestion.ren.identity import request_for
from iberian_shakti.ingestion.ren.parser import RenParser
from iberian_shakti.ingestion.ren.schema import ProfileFailure, validate_chart
from iberian_shakti.ingestion.retrieval import result_for

ROOT = Path(__file__).resolve().parents[3] / "data/ren"
INVENTORY = json.loads((ROOT / "manifest.json").read_bytes())
NOW = datetime(2026, 10, 28, tzinfo=UTC)


def parse(body, day=date(2026, 10, 24), **kwargs):
    acquired = result_for(RenAdapter().resolve(request_for(day)), UUID(int=1), NOW, content=body)
    return RenParser().parse(
        acquired.payload,
        acquired.provenance,
        parsed_at=NOW,
        parse_event_id=UUID(int=2),
        **kwargs,
    )


@pytest.mark.parametrize("name,entry", sorted(INVENTORY.items()))
def test_synthetic_fixture_outcomes(name, entry):
    result = parse((ROOT / name).read_bytes(), date.fromisoformat(entry["source_day"]))
    assert len(result.records) == result.provenance.record_count == entry["record_count"]
    assert result.provenance.outcome.value == entry["outcome"]
    assert result.provenance.error_code == entry["error_code"]
    assert result.provenance.catalogue_version == entry["profile"] == "0.2.0"
    assert result.provenance.record_schema.family.value == "system_measurement"


@pytest.mark.parametrize(
    "name,count,hour_count",
    [
        ("ordinary", 96, 4),
        ("spring", 92, 0),
        ("autumn", 100, 8),
        ("leap", 96, 4),
        ("year_boundary", 96, 4),
    ],
)
def test_physical_days_normalize_without_claiming_averaging(name, count, hour_count):
    body = (ROOT / f"synthetic_{name}.json").read_bytes()
    chart = validate_chart(body)
    assert len(chart.xAxis.categories) == count
    assert sum(label.startswith("01:") for label in chart.xAxis.categories) == hour_count
    assert all(len(s.data) == count for s in chart.series)
    assert chart.series[0].data[0] == Decimal("1.2300")
    assert chart.series[0].data[0].as_tuple().exponent == -4
    result = parse(body, date.fromisoformat(INVENTORY[f"synthetic_{name}.json"]["source_day"]))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert len(result.records) == 11 * count
    consumption = [r for r in result.records if r.native.series_id == "Consumption"]
    assert len(consumption) == count
    day = date.fromisoformat(INVENTORY[f"synthetic_{name}.json"]["source_day"])
    zone = ZoneInfo("Europe/Lisbon")
    start = datetime(day.year, day.month, day.day, tzinfo=zone).astimezone(UTC)
    expected_starts = [start + timedelta(minutes=15 * i) for i in range(count)]
    assert [r.timing.start_utc for r in consumption] == expected_starts
    assert len(set(expected_starts)) == count
    for i, record in enumerate(consumption):
        assert isinstance(record, SystemMeasurement)
        assert isinstance(record.timing, SupportInterval)
        assert record.timing.end_utc - record.timing.start_utc == timedelta(minutes=15)
        assert (
            record.timing.start_utc.astimezone(zone).strftime("%H:%M") == chart.xAxis.categories[i]
        )
        assert record.statistic is Statistic.PROVIDER_PERIOD_VALUE
        assert record.unit == "MW" and record.cadence_seconds == 900
        assert record.value.as_tuple() == chart.series[0].data[i].as_tuple()
        assert record.native.profile_version == "0.2.0"
        assert record.parse_event_id == result.provenance.parse_event_id
        assert record.retrieval_event_id == result.provenance.retrieval_event_id
        assert SystemMeasurement.model_validate_json(record.model_dump_json()) == record
    if name == "autumn":
        assert [r.timing.start_utc.astimezone(zone).fold for r in consumption[4:12]] == [0] * 4 + [
            1
        ] * 4
        assert [r.value for r in consumption[4:12]] == list(chart.series[0].data[4:12])
    assert {r.native.series_id for r in result.records} == set(profile.SELECTED)
    for record in result.records:
        assert record.measure == profile.SELECTED[record.native.series_id]
        assert record.geography == (
            profile.EXTERNAL_BOUNDARY
            if record.native.series_id in {"Import", "Export"}
            else profile.AREA
        )


def test_checksum_inventory_and_synthetic_rights_policy():
    assert set(INVENTORY) == {p.name for p in ROOT.iterdir()} - {"README.md", "manifest.json"}
    for name, entry in INVENTORY.items():
        body = (ROOT / name).read_bytes()
        assert len(body) == entry["bytes"]
        assert hashlib.sha256(body).hexdigest() == entry["sha256"]
        assert entry["evidence"] == "synthetic"
        assert name.startswith("synthetic_")


@pytest.mark.parametrize(
    "token", [b"true", b"false", b"null", b'"1.2"', b"[]", b"{}", b"NaN", b"Infinity", b"-Infinity"]
)
def test_invalid_numeric_values_never_become_zero_or_success(token):
    body = (ROOT / "synthetic_ordinary.json").read_bytes().replace(b"1.2300", token, 1)
    result = parse(body)
    assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert result.records == ()


@pytest.mark.parametrize("token", [b"0", b"-2", b"1.23000000000000000000000000001", b"1e-20"])
def test_numeric_lexemes_preserve_decimal_without_float(token):
    body = (ROOT / "synthetic_ordinary.json").read_bytes().replace(b"1.2300", token, 1)
    value = validate_chart(body).series[0].data[0]
    assert isinstance(value, Decimal)
    assert value.as_tuple() == Decimal(token.decode()).as_tuple()
    result = parse(body)
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.records[0].value.as_tuple() == value.as_tuple()
    assert result.records[0].unit == "MW"  # No multiplication by 0.25 or energy field.


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"null",
        b"[]",
        b"{}",
        b'{"x":1,"x":2}',
        b"[" * 1000 + b"]" * 1000,
        b'{"x":"' + b"x" * 5000 + b'"}',
        b'{"x":' + b"1" * 129 + b"}",
        b'{"x":1e9999999999999999999999999}',
        b'{"x":"\\ud800"}',
        b"\xff",
        b" " * (1024 * 1024 + 1),
    ],
)
def test_hostile_json_is_bounded_and_controlled(body):
    result = parse(body)
    assert result.records == ()
    assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE


def test_presentation_strings_are_data_never_executed(tmp_path):
    target = tmp_path / "must-not-exist"
    text = f"__import__('pathlib').Path({str(target)!r}).write_text('executed')"
    data = json.loads((ROOT / "synthetic_ordinary.json").read_bytes())
    data["series"][0]["tooltipOptions"]["style"]["color"] = text + ' { [ \\"'
    result = parse(json.dumps(data).encode())
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert not target.exists()


@pytest.mark.parametrize("where", ["root", "series", "axis", "title", "marker", "tooltip"])
def test_undeclared_presentation_and_semantic_keys_are_not_silently_ignored(where):
    data = json.loads((ROOT / "synthetic_ordinary.json").read_bytes())
    destination = {
        "root": data,
        "series": data["series"][0],
        "axis": data["xAxis"],
        "title": data["yAxis"]["title"],
        "marker": data["series"][0]["marker"],
        "tooltip": data["series"][0]["tooltipOptions"],
    }[where]
    destination["newField"] = "unknown semantics"
    assert parse(json.dumps(data).encode()).provenance.error_code is ErrorCode.SCHEMA_UNSUPPORTED


def test_bad_unselected_values_are_not_silently_discarded():
    data = json.loads((ROOT / "synthetic_ordinary.json").read_bytes())
    data["series"][-1]["data"][0] = None
    with pytest.raises(ProfileFailure):
        validate_chart(json.dumps(data).encode())


def test_incomplete_day_fails_even_when_all_arrays_align():
    data = json.loads((ROOT / "synthetic_ordinary.json").read_bytes())
    data["xAxis"]["categories"].pop()
    data["xAxis"]["max"] -= 1
    for series in data["series"]:
        series["data"].pop()
    result = parse(json.dumps(data).encode())
    assert result.provenance.error_code is ErrorCode.CONTENT_INVALID
    assert result.records == ()


@pytest.mark.parametrize(
    "mutation", ["reorder", "duplicate", "fold_removed", "fold_interleaved", "wrong_day"]
)
def test_unexpected_order_or_fold_sequence_fails_without_partial_records(mutation):
    autumn = mutation.startswith("fold")
    name = "synthetic_autumn.json" if autumn else "synthetic_ordinary.json"
    data = json.loads((ROOT / name).read_bytes())
    day = date.fromisoformat(INVENTORY[name]["source_day"])
    labels = data["xAxis"]["categories"]
    if mutation == "reorder":
        labels[2], labels[3] = labels[3], labels[2]
    elif mutation == "duplicate":
        labels[40] = labels[39]
    elif mutation == "fold_removed":
        del labels[8:12]
        data["xAxis"]["max"] -= 4
        for series in data["series"]:
            del series["data"][8:12]
    elif mutation == "fold_interleaved":
        labels[4:12] = ["01:00", "01:00", "01:15", "01:15", "01:30", "01:30", "01:45", "01:45"]
    else:
        day = date(2026, 3, 29)  # 96 valid labels cannot satisfy a 92-period source day.
    result = parse(json.dumps(data).encode(), day)
    assert result.provenance.error_code is ErrorCode.CONTENT_INVALID
    assert result.records == ()


def test_payload_hash_is_revalidated_at_parser_boundary():
    original = (ROOT / "synthetic_ordinary.json").read_bytes()
    acquired = result_for(
        RenAdapter().resolve(request_for(date(2026, 10, 24))), UUID(int=1), NOW, content=original
    )
    bypassed = RawPayload.model_construct(reference=acquired.payload.reference, content=b"changed")
    result = RenParser().parse(
        bypassed, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=2)
    )
    assert result.provenance.error_code is ErrorCode.INTEGRITY_FAILURE
    assert result.records == ()
