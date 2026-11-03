"""Synthetic hourly arrays, support/grid semantics, strict JSON and finite bounds."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome, RawPayload, ResolvedSource
from iberian_shakti.contracts.measurements import (
    Statistic,
    SupportInterval,
    ValidInstant,
    ValueKind,
    WeatherMeasurement,
)
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, WeatherQuery
from iberian_shakti.ingestion.retrieval import result_for
from iberian_shakti.ingestion.weather import profile
from iberian_shakti.ingestion.weather.adapter import OpenMeteoAdapter, OpenMeteoForecastAdapter
from iberian_shakti.ingestion.weather.identity import forecast_request_for, historical_request_for

ROOT = Path(__file__).resolve().parents[3] / "data/open_meteo"
BODY = (ROOT / "synthetic_era5.json").read_bytes()
START = datetime(2026, 10, 25, tzinfo=UTC)
NOW = datetime(2026, 11, 3, tzinfo=UTC)
WINDOW = QueryWindow(start_utc=START, end_utc=START + timedelta(days=1))


def parse_body(body=None, site_id="PT.lisbon", source=None, *, forecast=False, **updates):
    adapter = OpenMeteoForecastAdapter() if forecast else OpenMeteoAdapter()
    builder = forecast_request_for if forecast else historical_request_for
    if body is None:
        body = (ROOT / "synthetic_icon_eu.json").read_bytes() if forecast else BODY
    acquired = result_for(
        source or adapter.resolve(builder(WINDOW, site_id)),
        UUID(int=1),
        START - timedelta(hours=12) if forecast else NOW,
        content=body,
    )
    retrieval = acquired.provenance.model_copy(update=updates)
    return adapter.parser.parse(
        acquired.payload,
        retrieval,
        parsed_at=NOW + timedelta(minutes=1),
        parse_event_id=UUID(int=2),
    )


@pytest.fixture(params=[False, True], ids=["historical_era5", "forecast_icon_eu"])
def forecast(request):
    return request.param


@pytest.fixture
def parse(forecast):
    def selected(*args, **kwargs):
        return parse_body(*args, forecast=forecast, **kwargs)

    return selected


def encode(data):
    return json.dumps(data, ensure_ascii=False).encode()


@pytest.mark.parametrize("site_id", [site.site_id for site in profile.SITES])
def test_weather_retains_every_value_unit_support_site_grid_and_linkage(site_id, parse, forecast):
    result = parse(site_id=site_id)
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.provenance.parser_version == result.provenance.catalogue_version == "0.1.0"
    assert result.provenance.schema_family.value == "weather_measurement"
    assert len(result.records) == 72
    original = json.loads(BODY)
    site = next(site for site in profile.SITES if site.site_id == site_id)
    for i in range(24):
        at = START + timedelta(hours=i)
        temperature, wind, radiation = result.records[i * 3 : i * 3 + 3]
        for record, name in zip((temperature, wind, radiation), profile.VARIABLES, strict=True):
            assert isinstance(record, WeatherMeasurement)
            assert record.kind is (
                ValueKind.FORECAST if forecast else ValueKind.REANALYSIS
            ) and record.model_id == ("icon_eu" if forecast else "era5")
            assert record.value == original["hourly"][name][i]
            assert record.unit == original["hourly_units"][name]
            assert record.site == site and record.site.requested != record.returned_grid.coordinates
            assert record.returned_grid.coordinates.latitude == 38.75
            assert record.returned_grid.coordinates.longitude == -9.25
            assert record.returned_grid.elevation_m == 123.5
            assert record.cadence_seconds == 3600
            assert record.native.series_id == name and record.native.profile_version == "0.1.0"
            assert record.source_times.model_dump() == {
                "issue_time": None,
                "model_run_time": None,
                "published_at": None,
                "updated_at": None,
            }
            assert record.retrieval_event_id == UUID(int=1) and record.parse_event_id == UUID(int=2)
            assert WeatherMeasurement.model_validate_json(record.model_dump_json()) == record
        assert temperature.height_m == 2 and wind.height_m == 10 and radiation.height_m is None
        assert temperature.variable.value == "temperature" and wind.variable.value == "wind_speed"
        assert temperature.timing == wind.timing == ValidInstant(at_utc=at)
        assert temperature.statistic is wind.statistic is Statistic.INSTANT
        assert radiation.variable.value == "shortwave_radiation"
        assert radiation.statistic is Statistic.MEAN
        assert radiation.timing == SupportInterval(start_utc=at - timedelta(hours=1), end_utc=at)
    assert result.records[2].timing.start_utc.date() < START.date()


def test_fixture_manifest():
    inventory = json.loads((ROOT / "manifest.json").read_bytes())
    assert set(inventory) == {p.name for p in ROOT.iterdir()} - {"README.md", "manifest.json"}
    for name, entry in inventory.items():
        content = (ROOT / name).read_bytes()
        assert hashlib.sha256(content).hexdigest() == entry["sha256"]
        assert len(content) == entry["bytes"] and entry["evidence"] == "synthetic"
        assert (
            entry["profile"] == "0.1.0"
            and len(parse_body(content, forecast=entry.get("model") == "icon_eu").records)
            == entry["record_count"]
        )


@pytest.mark.parametrize("variable", profile.VARIABLES)
@pytest.mark.parametrize(
    "value", [None, True, False, "12.3", [], {}, float("nan"), float("inf"), -float("inf"), 1e300]
)
def test_invalid_selected_value_rejects_complete_response(variable, value, parse):
    data = json.loads(BODY)
    data["hourly"][variable][-1] = value
    result = parse(encode(data))
    assert result.records == () and result.provenance.outcome is ParseOutcome.CONTENT_FAILURE


@pytest.mark.parametrize("variable", profile.VARIABLES)
@pytest.mark.parametrize("mutation", ["absent", "unit", "length", "empty"])
def test_variable_and_unit_completeness(variable, mutation, parse):
    data = json.loads(BODY)
    if mutation == "absent":
        del data["hourly"][variable]
    elif mutation == "unit":
        data["hourly_units"][variable] = {
            "temperature_2m": "°F",
            "wind_speed_10m": "km/h",
            "shortwave_radiation": "W/m2",
        }[variable]
    elif mutation == "length":
        data["hourly"][variable].pop()
    else:
        data["hourly"][variable] = []
    assert parse(encode(data)).records == ()


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "unordered",
        "missing",
        "outside",
        "off_hour",
        "iso",
        "float",
        "bool",
        "huge",
        "empty",
    ],
)
def test_timestamps_strict_utc_hourly_coverage(mutation, parse):
    data = json.loads(BODY)
    times = data["hourly"]["time"]
    if mutation == "duplicate":
        times[-1] = times[-2]
    elif mutation == "unordered":
        times[0], times[1] = times[1], times[0]
    elif mutation == "missing":
        for values in data["hourly"].values():
            values.pop(5)
    elif mutation == "outside":
        times[-1] += 3600
    elif mutation == "off_hour":
        times[5] += 1
    elif mutation == "iso":
        times[0] = "2026-10-25T00:00"
    elif mutation == "float":
        times[0] = float(times[0])
    elif mutation == "bool":
        times[0] = True
    elif mutation == "huge":
        times[0] = 10**100
    else:
        data["hourly"]["time"] = []
    assert parse(encode(data)).records == ()


@pytest.mark.parametrize(
    "field,value",
    [
        ("latitude", 91),
        ("longitude", -181),
        ("latitude", "38.75"),
        ("latitude", None),
        ("elevation", None),
        ("elevation", 10001),
        ("elevation", -501),
        ("utc_offset_seconds", 3600),
        ("utc_offset_seconds", False),
        ("utc_offset_seconds", 0.0),
        ("timezone", "Europe/Lisbon"),
        ("timezone_abbreviation", "CEST"),
        ("model", "best_match"),
        ("models", "era5_land"),
    ],
)
def test_invalid_grid_timezone_or_explicit_model_metadata(field, value, parse):
    data = json.loads(BODY)
    data[field] = value
    assert parse(encode(data)).records == ()


@pytest.mark.parametrize(
    "field",
    [
        "latitude",
        "longitude",
        "elevation",
        "utc_offset_seconds",
        "timezone",
        "hourly",
        "hourly_units",
    ],
)
def test_missing_required_metadata(field, parse):
    data = json.loads(BODY)
    del data[field]
    assert parse(encode(data)).records == ()


def test_presentation_metadata_optional_and_not_source_time(parse):
    data = json.loads(BODY)
    data["generationtime_ms"] = 12.34
    assert [r.model_dump() for r in parse(encode(data)).records] == [
        r.model_dump() for r in parse().records
    ]


@pytest.mark.parametrize(
    "variable,low,high",
    [("temperature_2m", -100, 70), ("wind_speed_10m", 0, 150), ("shortwave_radiation", 0, 2000)],
)
def test_existing_shared_scientific_bounds_without_clipping(variable, low, high, parse):
    data = json.loads(BODY)
    data["hourly"][variable][0:2] = [low, high]
    result = parse(encode(data))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    selected = [r.value for r in result.records if r.native.series_id == variable]
    assert selected[0:2] == [low, high]
    data["hourly"][variable][-1] = low - 0.01
    assert parse(encode(data)).records == ()


@pytest.mark.parametrize(
    "body",
    [
        b"[]",
        b"null",
        b"true",
        b"{}",
        b"<html>error</html>",
        b'{"hourly":',
        b"\xff",
        b'{"a":1,"a":2}',
        b'{"ignored":NaN}',
        b'{"ignored":1e999}',
        b'{"ignored":' + b"1" * 129 + b"}",
        b'{"ignored":"\\ud800"}',
        b'{"ignored":' + b"[" * 1000 + b"0" + b"]" * 1000 + b"}",
    ],
)
def test_malformed_and_unsupported_json(body, parse):
    result = parse(body)
    assert result.records == () and result.provenance.outcome is ParseOutcome.CONTENT_FAILURE


@pytest.mark.parametrize(
    "bound", ["bytes", "depth", "keys", "array", "string", "key_string", "nodes", "number"]
)
def test_explicit_json_work_bounds(bound, parse):
    data = json.loads(BODY)
    if bound == "bytes":
        body = BODY + b" " * profile.MAX_BYTES
    else:
        if bound == "depth":
            value = 0
            for _ in range(profile.MAX_DEPTH + 1):
                value = {"a": value}
            data["ignored"] = value
        elif bound == "keys":
            data.update({f"key{i}": i for i in range(profile.MAX_KEYS + 1)})
        elif bound == "array":
            data["ignored"] = [0] * (profile.MAX_POINTS + 1)
        elif bound == "string":
            data["ignored"] = "x" * (profile.MAX_STRING + 1)
        elif bound == "key_string":
            data["x" * (profile.MAX_STRING + 1)] = 0
        elif bound == "nodes":
            data["ignored"] = [[{str(i): i for i in range(48)} for _ in range(48)]]
        else:
            data["ignored"] = 10**128
        body = encode(data)
    result = parse(body)
    assert result.records == () and result.provenance.error_code is ErrorCode.CONTENT_INVALID


@pytest.mark.parametrize(
    "body,code,outcome",
    [
        (
            {"error": True, "reason": "unchecked provider reason"},
            ErrorCode.PROVIDER_REJECTED,
            ParseOutcome.PROVIDER_REJECTED,
        ),
        ({"error": True}, ErrorCode.SCHEMA_UNSUPPORTED, ParseOutcome.CONTENT_FAILURE),
        (
            {"error": False, "reason": "unknown shape"},
            ErrorCode.SCHEMA_UNSUPPORTED,
            ParseOutcome.CONTENT_FAILURE,
        ),
    ],
)
def test_controlled_provider_errors_are_never_no_data(body, code, outcome, caplog, parse):
    result = parse(encode(body))
    assert result.records == () and result.provenance.error_code is code
    assert result.provenance.outcome is outcome
    assert body.get("reason", "not in output") not in caplog.text + result.model_dump_json()


@pytest.mark.parametrize(
    "model,report",
    [
        ("best_match", "forecast.v0.1.0"),
        ("era5_land", profile.HISTORICAL_REPORT),
        ("era5", "historical.era5.v9.0.0"),
    ],
)
def test_parser_refuses_wrong_product_model_and_profile(model, report, parse):
    original = historical_request_for(WINDOW, "PT.lisbon")
    request = ApiSourceRequest(
        **{
            **original.model_dump(),
            "report_id": report,
            "query": WeatherQuery(
                site=original.query.site, model_id=model, variables=profile.VARIABLES
            ),
        }
    )
    result = parse(source=ResolvedSource.for_api(request))
    assert result.records == () and result.provenance.error_code is ErrorCode.SCHEMA_UNSUPPORTED


def test_raw_linkage_mismatch_fails_without_records(parse):
    result = parse(raw=None)
    assert result.records == () and result.provenance.error_code is ErrorCode.INTEGRITY_FAILURE
    adapter = OpenMeteoAdapter()
    acquired = result_for(
        adapter.resolve(historical_request_for(WINDOW, "PT.lisbon")), UUID(int=1), NOW, content=BODY
    )
    payload = RawPayload.model_construct(reference=acquired.payload.reference, content=BODY + b" ")
    result = adapter.parser.parse(
        payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=2)
    )
    assert result.records == () and result.provenance.error_code is ErrorCode.INTEGRITY_FAILURE
