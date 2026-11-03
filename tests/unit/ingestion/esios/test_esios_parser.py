"""Exact native forecast values, strict source validation and honest edition times."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome, RawPayload
from iberian_shakti.contracts.measurements import (
    Statistic,
    SystemMeasurement,
    ValidInstant,
    ValueKind,
)
from iberian_shakti.contracts.queries import QueryWindow
from iberian_shakti.ingestion.esios.adapter import EsiosAdapter
from iberian_shakti.ingestion.esios.identity import request_for
from iberian_shakti.ingestion.esios.parser import EsiosParser
from iberian_shakti.ingestion.retrieval import result_for

ROOT = Path(__file__).resolve().parents[3] / "data/esios"
BODY = (ROOT / "synthetic_forecast.json").read_bytes()
START = datetime(2026, 10, 25, tzinfo=UTC)
NOW = datetime(2026, 11, 3, tzinfo=UTC)


def parse(body=BODY, start=START, **kwargs):
    source = EsiosAdapter().resolve(
        request_for(QueryWindow(start_utc=start, end_utc=start + timedelta(hours=3)))
    )
    acquired = result_for(source, UUID(int=1), NOW, content=body)
    return EsiosParser().parse(
        acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=2), **kwargs
    )


def test_forecast_samples_keep_exact_values_times_geography_and_unknown_vintage():
    result = parse()
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.provenance.parser_version == result.provenance.catalogue_version == "0.1.0"
    assert len(result.records) == 3
    assert [record.value for record in result.records] == [
        Decimal("23000.12300"),
        Decimal("23001"),
        Decimal("23002.5"),
    ]
    assert result.records[0].value.as_tuple().exponent == -5
    for i, record in enumerate(result.records):
        assert isinstance(record, SystemMeasurement)
        assert record.measure.kind == "load" and record.kind is ValueKind.FORECAST
        assert record.unit == "MW" and record.statistic is Statistic.INSTANT
        assert isinstance(record.timing, ValidInstant)
        assert record.timing.at_utc == START + timedelta(minutes=55 + 5 * i)
        assert record.cadence_seconds == 300
        assert record.geography.project_id == "ES.peninsular"
        assert record.geography.role.value == "system" and record.geography.country_code == "ES"
        assert record.geography.perimeter == "mainland"
        assert (
            record.geography.native_id == "999001" and record.geography.native_scheme == "provider"
        )
        assert record.native.series_id == "544" and record.native.profile_version == "0.1.0"
        assert record.source_times.updated_at == datetime(2026, 10, 25, 2, 10, tzinfo=UTC)
        assert record.source_times.issue_time is None and record.source_times.model_run_time is None
        assert record.source_times.published_at is None and record.publication_status == "unknown"
        assert record.retrieval_event_id == UUID(int=1) and record.parse_event_id == UUID(int=2)
        assert SystemMeasurement.model_validate_json(record.model_dump_json()) == record


def test_fixture_inventory_is_synthetic_and_checksum_verified():
    inventory = json.loads((ROOT / "manifest.json").read_bytes())
    assert set(inventory) == {p.name for p in ROOT.iterdir()} - {"README.md", "manifest.json"}
    for name, entry in inventory.items():
        content = (ROOT / name).read_bytes()
        assert len(content) == entry["bytes"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        assert entry["evidence"] == "synthetic" and entry["profile"] == "0.1.0"
        assert len(parse(content).records) == entry["record_count"]


@pytest.mark.parametrize(
    "token",
    [b"true", b"false", b"null", b'"12.3"', b"[]", b"{}", b"NaN", b"Infinity", b"-Infinity"],
)
def test_invalid_quantities_fail_without_any_partial_records(token):
    result = parse(BODY.replace(b"23000.12300", token, 1))
    assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE and result.records == ()


@pytest.mark.parametrize("token", [b"0", b"-2", b"1.23000000000000000000000000001", b"1e-20"])
def test_source_decimal_precision_is_preserved_without_resampling(token):
    result = parse(BODY.replace(b"23000.12300", token, 1))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.records[0].value.as_tuple() == Decimal(token.decode()).as_tuple()


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", 545),
        ("id", 460),
        ("id", 1293),
        ("id", "544"),
        ("id", 544.0),
        ("name", "Demanda real"),
        ("unit", "MWh"),
        ("magnitud", [{"name": "Energía"}]),
        ("tiempo", [{"name": "Hora"}]),
        ("values", None),
        ("values", []),
        ("geos", [{"geo_id": 999001, "geo_name": "España"}]),
        ("values_updated_at", "yesterday"),
    ],
)
def test_wrong_product_unit_cadence_schema_and_update_time_fail(field, value):
    data = json.loads(BODY)
    data["indicator"][field] = value
    result = parse(json.dumps(data).encode())
    assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE and result.records == ()


@pytest.mark.parametrize("field", ["id", "values"])
def test_required_indicator_fields_cannot_be_missing(field):
    data = json.loads(BODY)
    del data["indicator"][field]
    assert parse(json.dumps(data).encode()).records == ()


@pytest.mark.parametrize("field", ["value", "datetime_utc", "geo_id"])
def test_required_value_fields_cannot_be_missing(field):
    data = json.loads(BODY)
    del data["indicator"]["values"][0][field]
    assert parse(json.dumps(data).encode()).provenance.outcome is ParseOutcome.CONTENT_FAILURE


@pytest.mark.parametrize(
    "field,value",
    [
        ("datetime_utc", "2026-10-25T00:55:00"),
        ("datetime_utc", "bad"),
        ("datetime_utc", "2026-10-25T00:55:00+01:00"),
        ("datetime_utc", "2026-10-25T00:56:00Z"),
        ("datetime_utc", "2026-10-25T00:55:01Z"),
        ("datetime_utc", "2026-10-25T00:55:00.001Z"),
        ("datetime", "2026-10-25T02:55:00+01:00"),
        ("datetime", "2026-10-25T00:55:00+00:00"),
        ("datetime", "2026-10-25T02:55:00"),
        ("geo_id", 123456),
        ("geo_id", True),
        ("geo_name", "Baleares"),
    ],
)
def test_invalid_value_timestamp_or_geography_is_controlled(field, value):
    data = json.loads(BODY)
    data["indicator"]["values"][0][field] = value
    result = parse(json.dumps(data).encode())
    assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE and result.records == ()


@pytest.mark.parametrize(
    "mutation", ["reorder", "duplicate", "conflict", "missing_geo", "mixed_geo", "duplicate_geo"]
)
def test_order_duplicates_and_ambiguous_geography_never_normalize(mutation):
    data = json.loads(BODY)
    indicator = data["indicator"]
    values = indicator["values"]
    if mutation == "reorder":
        values.reverse()
    elif mutation in {"duplicate", "conflict"}:
        values[1] = dict(values[0])
        if mutation == "conflict":
            values[1]["value"] += 1
    elif mutation == "missing_geo":
        del indicator["geos"]
        for value in values:
            del value["geo_name"]
    elif mutation == "mixed_geo":
        values[1]["geo_id"] = 999002
        indicator["geos"].append({"geo_id": 999002, "geo_name": "Península"})
    else:
        indicator["geos"].append(dict(indicator["geos"][0]))
    assert parse(json.dumps(data).encode()).provenance.outcome is ParseOutcome.CONTENT_FAILURE


def test_optional_metadata_is_optional_and_original_bytes_retain_native_time():
    data = json.loads(BODY)
    indicator = data["indicator"]
    for key in ["name", "magnitud", "tiempo", "values_updated_at", "geos"]:
        del indicator[key]
    for value in indicator["values"]:
        del value["datetime"]
    result = parse(json.dumps(data).encode())
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert all(record.source_times.updated_at is None for record in result.records)
    assert result.records[0].timing.at_utc == START + timedelta(minutes=55)
    # geo_name can instead be inherited from matching indicator geos metadata.
    data = json.loads(BODY)
    for value in data["indicator"]["values"]:
        del value["geo_name"]
    assert parse(json.dumps(data).encode()).provenance.outcome is ParseOutcome.SUCCESS


def test_gap_is_retained_without_filling_or_inferred_intervals():
    data = json.loads(BODY)
    del data["indicator"]["values"][1]
    records = parse(json.dumps(data).encode()).records
    assert len(records) == 2
    assert records[1].timing.at_utc - records[0].timing.at_utc == timedelta(minutes=10)
    assert all(record.cadence_seconds == 300 for record in records)


@pytest.mark.parametrize(
    "utc,local",
    [
        ("2026-03-29T00:55:00Z", "2026-03-29T01:55:00+01:00"),
        ("2026-03-29T01:00:00+00:00", "2026-03-29T03:00:00+02:00"),
    ],
)
def test_spring_dst_provider_timestamps_are_used_directly(utc, local):
    data = json.loads(BODY)
    value = data["indicator"]["values"][0]
    value.update(datetime_utc=utc, datetime=local)
    data["indicator"]["values"] = [value]
    result = parse(json.dumps(data).encode(), start=datetime(2026, 3, 29, tzinfo=UTC))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.records[0].timing.at_utc == datetime.fromisoformat(utc)


def test_possible_inclusive_end_is_preserved_and_outside_window_is_rejected():
    data = json.loads(BODY)
    data["indicator"]["values"] = [data["indicator"]["values"][0]]
    value = data["indicator"]["values"][0]
    value.update(datetime_utc="2026-10-25T03:00:00Z", datetime="2026-10-25T04:00:00+01:00")
    assert parse(json.dumps(data).encode()).provenance.outcome is ParseOutcome.SUCCESS
    value.update(datetime_utc="2026-10-25T03:05:00Z", datetime="2026-10-25T04:05:00+01:00")
    assert parse(json.dumps(data).encode()).records == ()


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"null",
        b"[]",
        b"{}",
        b'{"indicator":',
        b'{"id":544,"id":545}',
        b"[" * 2000 + b"]" * 2000,
        b'{"x":1e9999999999999999999999999}',
        b'{"x":"\\ud800"}',
        b"\xff",
        b'{"x":' + b"1" * 129 + b"}",
    ],
)
def test_malformed_or_hostile_json_has_controlled_failure(body):
    result = parse(body)
    assert result.provenance.outcome is ParseOutcome.CONTENT_FAILURE and result.records == ()


def test_payload_integrity_is_checked_before_semantic_parsing():
    source = EsiosAdapter().resolve(
        request_for(QueryWindow(start_utc=START, end_utc=START + timedelta(hours=3)))
    )
    acquired = result_for(source, UUID(int=1), NOW, content=BODY)
    payload = RawPayload.model_construct(reference=acquired.payload.reference, content=b"changed")
    result = EsiosParser().parse(
        payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=2)
    )
    assert result.provenance.error_code is ErrorCode.INTEGRITY_FAILURE and result.records == ()
