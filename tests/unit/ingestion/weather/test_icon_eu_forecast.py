"""ICON-EU identity, bounded next-day snapshots and historical compatibility."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.geography import Coordinates
from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome, ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.retrieval import result_for
from iberian_shakti.ingestion.weather import profile
from iberian_shakti.ingestion.weather.adapter import OpenMeteoAdapter, OpenMeteoForecastAdapter
from iberian_shakti.ingestion.weather.identity import forecast_request_for, historical_request_for

BODY = (Path(__file__).resolve().parents[3] / "data/open_meteo/synthetic_icon_eu.json").read_bytes()
START = datetime(2026, 10, 25, tzinfo=UTC)
ACQUIRED = START - timedelta(hours=12)
WINDOW = QueryWindow(start_utc=START, end_utc=START + timedelta(days=1))


def changed_request(change):
    original = forecast_request_for(WINDOW, "PT.lisbon")
    data = json.loads(original.model_dump_json())
    if change.startswith("model:"):
        data["query"]["model_id"] = change.split(":", 1)[1]
    elif change == "missing_model":
        del data["query"]["model_id"]
    elif change == "profile":
        data["report_id"] = "forecast.icon_eu.v9.0.0"
    elif change == "historical_profile":
        data["report_id"] = profile.HISTORICAL_REPORT
    elif change == "output_profile":
        data["query"]["output"]["profile_version"] = "9.0.0"
    elif change == "missing_output":
        del data["query"]["output"]
    elif change == "country":
        data["query"]["site"]["country_code"] = "ES"
    elif change == "site_version":
        data["query"]["site"]["selection_version"] = "9.0.0"
    elif change == "coordinates":
        data["query"]["site"]["requested"]["latitude"] = 38.75
    elif change == "site":
        data["query"]["site"]["site_id"] = "PT.porto"
    elif change == "variables":
        data["query"]["variables"] = ["temperature_2m"]
    elif change == "extra_variable":
        data["query"]["variables"].append("humidity")
    elif change == "source":
        data["source_id"] = "other"
    elif change == "partition":
        data["delivery_date"] = "2026-10-26"
    else:
        data["query"]["output"][change] = {
            "timezone": "Europe/Lisbon",
            "timeformat": "iso8601",
            "wind_speed_unit": "kmh",
            "temperature_unit": "fahrenheit",
        }[change]
    return ApiSourceRequest.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "change",
    [
        "model:best_match",
        "model:icon_seamless",
        "model:icon_global",
        "model:icon_d2",
        "model:dwd_aicon_global_native",
        "model:ecmwf_ifs",
        "model:era5",
        "model:icon_eu,ecmwf_ifs",
        "missing_model",
        "profile",
        "historical_profile",
        "output_profile",
        "missing_output",
        "site",
        "country",
        "site_version",
        "coordinates",
        "variables",
        "extra_variable",
        "source",
        "partition",
        "timezone",
        "timeformat",
        "wind_speed_unit",
        "temperature_unit",
    ],
)
def test_forecast_identity_drift_fails_before_http_and_parse_success(change, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Rejected forecast identity reached client construction")

    monkeypatch.setattr(httpx, "Client", forbidden)
    try:
        request = changed_request(change)
    except ValidationError:
        return  # Missing required identity or unsupported literal: fails at construction.
    source = ResolvedSource.for_api(request)
    adapter = OpenMeteoForecastAdapter()
    with pytest.raises(ExecutionError):
        adapter.resolve(request)
    with pytest.raises(ExecutionError):
        adapter.retriever(retrieval_event_id=UUID(int=1), now=lambda: ACQUIRED).retrieve(source)
    acquired = result_for(source, UUID(int=1), ACQUIRED, content=BODY)
    parsed = adapter.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=START, parse_event_id=UUID(int=2)
    )
    assert parsed.records == ()
    assert parsed.provenance.error_code is ErrorCode.SCHEMA_UNSUPPORTED


def test_forecast_query_retains_explicit_output_policy_and_separate_parser_identity():
    request = forecast_request_for(WINDOW, "PT.lisbon")
    data = json.loads(request.model_dump_json())
    assert data["query"]["output"] == {
        "profile_version": "0.1.0",
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
        "timezone": "GMT",
        "timeformat": "unixtime",
    }
    assert data["query"]["model_id"] == "icon_eu"
    assert data["report_id"] == "forecast.icon_eu.v0.1.0"
    adapter = OpenMeteoForecastAdapter()
    assert adapter.parser.parser_id == "open_meteo.icon_eu.hourly"
    assert adapter.parser.parser_version == adapter.parser.profile_version == "0.1.0"
    acquired = result_for(adapter.resolve(request), UUID(int=1), ACQUIRED, content=BODY)
    result = adapter.parser.parse(
        acquired.payload,
        acquired.provenance,
        parsed_at=START + timedelta(days=365),
        parse_event_id=UUID(int=2),
    )
    assert result.provenance.parser_id == "open_meteo.icon_eu.hourly"
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert {record.report_id for record in result.records} == {request.report_id}
    assert acquired.provenance.source.request.query_identity == request.query_identity
    with pytest.raises(ExecutionError):
        OpenMeteoAdapter.resolve(request)
    with pytest.raises(ExecutionError):
        adapter.resolve(historical_request_for(WINDOW, "PT.lisbon"))
    assert (
        OpenMeteoAdapter()
        .parser.parse(
            acquired.payload, acquired.provenance, parsed_at=START, parse_event_id=UUID(int=3)
        )
        .records
        == ()
    )


def test_forecast_addition_preserves_legacy_weather_query_serialization_and_hash():
    request = historical_request_for(WINDOW, "PT.lisbon")
    legacy = {
        "contract_version": "2.0.0",
        "source_id": "open_meteo",
        "report_id": "historical.era5.v0.1.0",
        "delivery_date": "2026-10-25",
        "window": {"start_utc": "2026-10-25T00:00:00Z", "end_utc": "2026-10-26T00:00:00Z"},
        "selection_mode": "api_snapshot",
        "query": {
            "kind": "weather",
            "model_id": "era5",
            "variables": ["shortwave_radiation", "temperature_2m", "wind_speed_10m"],
            "site": {
                "site_id": "PT.lisbon",
                "selection_version": "0.1.0",
                "country_code": "PT",
                "requested": {"latitude": 38.72, "longitude": -9.14},
            },
        },
    }
    assert json.loads(request.model_dump_json()) == legacy
    assert request.model_dump(mode="json")["query"] == legacy["query"]
    assert "output" not in request.model_dump()["query"]
    assert ApiSourceRequest.model_validate_json(json.dumps(legacy)) == request
    assert (
        request.query_identity
        == hashlib.sha256(
            json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


@pytest.mark.parametrize("offset", [-5, -1, 0, 2, 3, 7, 16])
def test_forecast_unsupported_target_day_fails_before_http(offset, monkeypatch):
    start = datetime(2026, 10, 24, tzinfo=UTC) + timedelta(days=offset)
    request = forecast_request_for(
        QueryWindow(start_utc=start, end_utc=start + timedelta(days=1)), "PT.lisbon"
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Unsupported forecast day reached HTTP")

    monkeypatch.setattr(httpx, "Client", forbidden)
    adapter = OpenMeteoForecastAdapter()
    with pytest.raises(ExecutionError):
        adapter.retriever(retrieval_event_id=UUID(int=1), now=lambda: ACQUIRED).retrieve(
            adapter.resolve(request)
        )
    # Parser also enforces the bound against original acquisition, even if a
    # forged/local input provides otherwise complete hourly coverage.
    data = json.loads(BODY)
    data["hourly"]["time"] = [int(start.timestamp()) + i * 3600 for i in range(24)]
    acquired = result_for(
        adapter.resolve(request), UUID(int=1), ACQUIRED, content=json.dumps(data).encode()
    )
    parsed = adapter.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=START, parse_event_id=UUID(int=2)
    )
    assert parsed.records == ()


@pytest.mark.parametrize("offset,hours", [(0, 1), (0, 23), (0, 25), (1, 24), (0.01, 24)])
def test_forecast_requires_exact_midnight_utc_day(offset, hours):
    start = START + timedelta(hours=offset)
    with pytest.raises(ValueError):
        forecast_request_for(
            QueryWindow(start_utc=start, end_utc=start + timedelta(hours=hours)), "PT.lisbon"
        )


@pytest.mark.parametrize("date", ["2026-03-29", "2026-10-25", "2028-02-29", "2026-12-01"])
def test_forecast_utc_calendar_remains_24_hours_across_dst_leap_and_grid_transition(date):
    start = datetime.fromisoformat(date).replace(tzinfo=UTC)
    adapter = OpenMeteoForecastAdapter()
    request = forecast_request_for(
        QueryWindow(start_utc=start, end_utc=start + timedelta(days=1)), "PT.lisbon"
    )
    data = json.loads(BODY)
    data["hourly"]["time"] = [int(start.timestamp()) + i * 3600 for i in range(24)]
    data.update(latitude=38.71, longitude=-9.13, elevation=151.25)
    acquired = result_for(
        adapter.resolve(request),
        UUID(int=1),
        start - timedelta(hours=12),
        content=json.dumps(data).encode(),
    )
    result = adapter.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=start, parse_event_id=UUID(int=2)
    )
    assert result.provenance.outcome is ParseOutcome.SUCCESS and len(result.records) == 72
    assert result.records[0].site.requested == Coordinates(latitude=38.72, longitude=-9.14)
    assert result.records[0].returned_grid.coordinates == Coordinates(
        latitude=38.71, longitude=-9.13
    )
    assert result.records[0].returned_grid.elevation_m == 151.25
    assert {r.model_id for r in result.records} == {"icon_eu"}


@pytest.mark.parametrize(
    "response_model", ["era5", "ecmwf_ifs", "best_match", "icon_global", "icon_seamless"]
)
@pytest.mark.parametrize("field", ["model", "models"])
def test_forecast_explicit_response_model_must_agree_with_query(field, response_model):
    data = json.loads(BODY)
    data[field] = response_model
    adapter = OpenMeteoForecastAdapter()
    acquired = result_for(
        adapter.resolve(forecast_request_for(WINDOW, "PT.lisbon")),
        UUID(int=1),
        ACQUIRED,
        content=json.dumps(data).encode(),
    )
    result = adapter.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=START, parse_event_id=UUID(int=2)
    )
    assert result.records == () and result.provenance.outcome is ParseOutcome.CONTENT_FAILURE


def test_forecast_extra_hour_rejected_atomically():
    data = json.loads(BODY)
    for values in data["hourly"].values():
        values.append(values[-1])
    data["hourly"]["time"][-1] += 3600
    adapter = OpenMeteoForecastAdapter()
    acquired = result_for(
        adapter.resolve(forecast_request_for(WINDOW, "PT.lisbon")),
        UUID(int=1),
        ACQUIRED,
        content=json.dumps(data).encode(),
    )
    result = adapter.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=START, parse_event_id=UUID(int=2)
    )
    assert result.records == () and result.provenance.outcome is ParseOutcome.CONTENT_FAILURE
