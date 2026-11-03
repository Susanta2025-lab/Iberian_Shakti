"""Synthetic Stage 1 contracts; no provider mappings, fixtures or network."""

import json
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from iberian_shakti.contracts.geography import (
    Area,
    AreaRole,
    Coordinates,
    DirectedBorder,
    ExternalBoundary,
    WeatherGrid,
    WeatherSite,
)
from iberian_shakti.contracts.ingestion import NormalizedRecord, ResolvedSource
from iberian_shakti.contracts.measurements import (
    GenerationMeasure,
    InterchangeMeasure,
    LoadMeasure,
    NativeSeries,
    RecordSchema,
    SchemaFamily,
    SourceTimes,
    Statistic,
    SupportInterval,
    SystemMeasurement,
    ValidInstant,
    ValueKind,
    WeatherMeasurement,
    WeatherVariable,
)
from iberian_shakti.contracts.queries import (
    ApiSelectionMode,
    ApiSourceRequest,
    QueryWindow,
    SystemQuery,
    WeatherQuery,
)

NOW = datetime(2026, 10, 25, tzinfo=UTC)
DAY = date(2026, 10, 25)
AREA = Area(role=AreaRole.SYSTEM, project_id="PT-mainland", country_code="PT", perimeter="mainland")
SITE = WeatherSite(
    site_id="test_site",
    selection_version="1.0.0",
    country_code="PT",
    requested=Coordinates(latitude=38.0, longitude=-9.0),
)


def api_request(**updates):
    return ApiSourceRequest.model_validate(
        {
            "source_id": "synthetic",
            "report_id": "system",
            "delivery_date": DAY,
            "window": QueryWindow(start_utc=NOW, end_utc=NOW + timedelta(hours=25)),
            "query": SystemQuery(area=AREA, series_ids=("load", "wind")),
            **updates,
        }
    )


def system_record(**updates):
    return SystemMeasurement.model_validate(
        {
            "source_id": "synthetic",
            "report_id": "system",
            "delivery_date": DAY,
            "kind": ValueKind.ACTUAL,
            "timing": ValidInstant(at_utc=NOW),
            "statistic": Statistic.INSTANT,
            "cadence_seconds": 900,
            "native": NativeSeries(series_id="load", profile_version="1.0.0"),
            "retrieval_event_id": UUID(int=1),
            "parse_event_id": UUID(int=2),
            "measure": LoadMeasure(),
            "geography": AREA,
            "unit": "MW",
            "value": Decimal("12.3400"),
            **updates,
        }
    )


def weather_record(**updates):
    return WeatherMeasurement.model_validate(
        {
            "source_id": "synthetic",
            "report_id": "weather",
            "delivery_date": DAY,
            "kind": ValueKind.REANALYSIS,
            "timing": ValidInstant(at_utc=NOW),
            "statistic": Statistic.INSTANT,
            "cadence_seconds": 3600,
            "native": NativeSeries(series_id="temperature", profile_version="1.0.0"),
            "retrieval_event_id": UUID(int=1),
            "parse_event_id": UUID(int=2),
            "model_id": "model",
            "site": SITE,
            "variable": WeatherVariable.TEMPERATURE,
            "height_m": 2.0,
            "unit": "°C",
            "value": 12.3,
            **updates,
        }
    )


def test_provider_period_power_is_exact_mw_with_interval_and_no_energy_semantics():
    support = SupportInterval(start_utc=NOW, end_utc=NOW + timedelta(minutes=15))
    record = system_record(timing=support, statistic=Statistic.PROVIDER_PERIOD_VALUE)
    assert record.value.as_tuple() == Decimal("12.3400").as_tuple()
    assert record.unit == "MW"
    assert record.statistic is not Statistic.MEAN
    assert SystemMeasurement.model_validate_json(record.model_dump_json()) == record
    with pytest.raises(ValidationError):
        system_record(timing=support, statistic=Statistic.PROVIDER_PERIOD_VALUE, unit="MWh")
    with pytest.raises(ValidationError):
        system_record(statistic=Statistic.PROVIDER_PERIOD_VALUE)  # Instant has no source period.
    with pytest.raises(ValidationError):
        weather_record(
            timing=support,
            statistic=Statistic.PROVIDER_PERIOD_VALUE,
            variable=WeatherVariable.SHORTWAVE_RADIATION,
            unit="W/m²",
            height_m=None,
        )


def test_query_identity_is_canonical_and_snapshot_only():
    query = api_request()
    reverse = api_request(query=SystemQuery(area=AREA, series_ids=("wind", "load")))
    assert query.model_dump_json() == reverse.model_dump_json()
    assert query.query_identity == reverse.query_identity
    assert query.revision is None and query.selection_mode is ApiSelectionMode.SNAPSHOT
    assert "revision" not in json.loads(query.model_dump_json())
    resolved = ResolvedSource.for_api(query)
    assert resolved.observed_revision is None and query.query_identity in resolved.safe_locator
    assert ResolvedSource.model_validate_json(resolved.model_dump_json()) == resolved
    changed = api_request(window=QueryWindow(start_utc=NOW, end_utc=NOW + timedelta(hours=24)))
    assert changed.query_identity != query.query_identity
    with pytest.raises(ValidationError):
        ResolvedSource.model_validate({**resolved.model_dump(), "observed_revision": 1})
    with pytest.raises(ValidationError):
        ResolvedSource.model_validate({**resolved.model_dump(), "safe_locator": "wrong/query"})


@pytest.mark.parametrize(
    "field", ["token", "securityToken", "Authorization", "headers", "url", "revision"]
)
def test_safe_query_has_no_secret_slots(field):
    with pytest.raises(ValidationError) as caught:
        api_request(**{field: "synthetic-stage1-secret"})
    assert "synthetic-stage1-secret" not in str(caught.value)
    assert "synthetic-stage1-secret" not in repr(caught.value)


@pytest.mark.parametrize(
    "updates",
    [
        {"source_id": "https://example.invalid/?token=secret"},
        {"source_id": "x" * 65},
        {"delivery_date": "2026-10-25"},
        {"selection_mode": "latest"},
        {"selection_mode": "api_snapshot"},
        {"contract_version": "1.0.0"},
    ],
)
def test_query_strict_types_and_versions(updates):
    with pytest.raises(ValidationError):
        api_request(**updates)


@pytest.mark.parametrize(
    "bad_time",
    [
        datetime(2026, 10, 25),
        datetime(2026, 10, 25, tzinfo=timezone(timedelta(hours=1))),
        "2026-10-25",
    ],
)
@pytest.mark.parametrize(
    "model,field",
    [
        (ValidInstant, "at_utc"),
        (SourceTimes, "issue_time"),
        (SourceTimes, "model_run_time"),
        (SourceTimes, "published_at"),
        (SourceTimes, "updated_at"),
    ],
)
def test_all_source_times_require_aware_utc(model, field, bad_time):
    with pytest.raises(ValidationError):
        model(**{field: bad_time})


@pytest.mark.parametrize("hours", [0, -1, 26])
def test_query_daily_window_bound(hours):
    with pytest.raises(ValidationError):
        QueryWindow(start_utc=NOW, end_utc=NOW + timedelta(hours=hours))


@pytest.mark.parametrize("kind", ["system", "weather"])
@pytest.mark.parametrize("values", [(), ("x", "x"), tuple(str(i) for i in range(40)), ["x"]])
def test_selections_are_immutable_bounded_unique(kind, values):
    with pytest.raises(ValidationError):
        if kind == "system":
            SystemQuery(area=AREA, series_ids=values)
        else:
            WeatherQuery(site=SITE, model_id="model", variables=values)


def test_weather_query_uses_site_model_variables_not_area_bag():
    query = api_request(query=WeatherQuery(site=SITE, model_id="model", variables=("wind", "temp")))
    assert query.query.variables == ("temp", "wind")
    assert ApiSourceRequest.model_validate_json(query.model_dump_json()) == query
    with pytest.raises(ValidationError):
        WeatherQuery(site=SITE, model_id="model", variables=("temperature",), token="secret-value")


@pytest.mark.parametrize(
    "model",
    [
        api_request(),
        AREA,
        SITE,
        Coordinates(latitude=1.0, longitude=2.0),
        SourceTimes(),
        system_record(),
        weather_record(),
        RecordSchema(family=SchemaFamily.SYSTEM_MEASUREMENT),
    ],
)
def test_new_contracts_are_frozen_closed_roundtrippable(model):
    assert type(model).model_validate_json(model.model_dump_json()) == model
    key = next(iter(type(model).model_fields))
    with pytest.raises(ValidationError):
        setattr(model, key, getattr(model, key))
    with pytest.raises(ValidationError):
        type(model).model_validate({**model.model_dump(), "unrecognized": 1})


@pytest.mark.parametrize(
    "role", [AreaRole.COUNTRY, AreaRole.BIDDING_ZONE, AreaRole.CONTROL_AREA, AreaRole.PROVIDER_AREA]
)
def test_area_roles_are_distinct_from_native_scheme(role):
    area = Area(
        role=role,
        project_id="PT",
        country_code="PT",
        native_id="synthetic-domain",
        native_scheme="eic",
    )
    assert area != AREA and area.role is role and area.native_scheme == "eic"


@pytest.mark.parametrize(
    "updates",
    [
        {"native_id": "eic"},
        {"native_scheme": "eic"},
        {"perimeter": None},
        {"role": AreaRole.BIDDING_ZONE},
        {"country_code": "Portugal"},
        {"native_id": "https://host/", "native_scheme": "provider"},
    ],
)
def test_invalid_area_combinations(updates):
    with pytest.raises(ValidationError):
        Area.model_validate({**AREA.model_dump(), **updates})


@pytest.mark.parametrize(
    "updates",
    [{"latitude": 91.0}, {"longitude": -181.0}, {"latitude": float("nan")}, {"longitude": True}],
)
def test_coordinate_boundaries(updates):
    with pytest.raises(ValidationError):
        Coordinates(latitude=updates.get("latitude", 0.0), longitude=updates.get("longitude", 0.0))


def test_interchange_endpoints_and_technology_contracts():
    other = Area(role=AreaRole.CONTROL_AREA, project_id="other")
    border = DirectedBorder(from_area=AREA, to_area=other)
    for geography in (border, ExternalBoundary(area=AREA)):
        record = system_record(measure=InterchangeMeasure(direction="import"), geography=geography)
        assert record.measure.direction == "import"
    assert system_record(measure=GenerationMeasure(technology="wind")).measure.technology == "wind"
    with pytest.raises(ValidationError):
        DirectedBorder(from_area=AREA, to_area=AREA)
    with pytest.raises(ValidationError):
        system_record(measure=InterchangeMeasure(direction="export"))
    with pytest.raises(ValidationError):
        system_record(geography=border)
    with pytest.raises(ValidationError):
        LoadMeasure(technology="wind")


@pytest.mark.parametrize("value", [1.2, 1, True, "1.20", Decimal("NaN"), Decimal("Infinity")])
def test_system_quantities_reject_float_coercion_and_nonfinite(value):
    with pytest.raises(ValidationError):
        system_record(value=value)


def test_system_precision_and_power_energy_distinction():
    power = system_record()
    assert json.loads(power.model_dump_json())["value"] == "12.3400"
    assert (
        SystemMeasurement.model_validate_json(power.model_dump_json()).value.as_tuple()
        == power.value.as_tuple()
    )
    interval = SupportInterval(start_utc=NOW, end_utc=NOW + timedelta(minutes=15))
    energy = system_record(unit="MWh", timing=interval, statistic=Statistic.SUM)
    assert energy.unit != power.unit
    assert system_record(timing=interval, statistic=Statistic.MEAN).value == power.value
    for updates in ({"unit": "MWh"}, {"statistic": Statistic.SUM}, {"unit": "EUR/MWh"}):
        with pytest.raises(ValidationError):
            system_record(**updates)
    payload = json.loads(power.model_dump_json())
    payload["value"] = 12.34
    with pytest.raises(ValidationError):
        SystemMeasurement.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize("kind", list(ValueKind))
def test_value_kind_and_unknown_source_times(kind):
    assert weather_record(kind=kind).source_times == SourceTimes()
    if kind is ValueKind.REANALYSIS:
        with pytest.raises(ValidationError):
            system_record(kind=kind)
    else:
        assert system_record(kind=kind).kind is kind


def test_forecast_editions_and_acquisition_snapshot_identity():
    unknown = system_record(kind=ValueKind.FORECAST)
    assert unknown.source_times.issue_time is None
    later = system_record(kind=ValueKind.FORECAST, retrieval_event_id=UUID(int=9))
    assert unknown.business_identity != later.business_identity
    assert (
        system_record(kind=ValueKind.FORECAST, parse_event_id=UUID(int=9)).business_identity
        == unknown.business_identity
    )
    issued = SourceTimes(issue_time=NOW - timedelta(days=1))
    known = system_record(kind=ValueKind.FORECAST, source_times=issued)
    assert (
        known.business_identity
        == system_record(
            kind=ValueKind.FORECAST, source_times=issued, retrieval_event_id=UUID(int=9)
        ).business_identity
    )
    assert known.business_identity != unknown.business_identity
    assert (
        known.business_identity
        != system_record(
            kind=ValueKind.FORECAST, source_times=SourceTimes(issue_time=NOW)
        ).business_identity
    )
    with pytest.raises(ValidationError):
        system_record(source_times=issued)


@pytest.mark.parametrize(
    "updates",
    [
        {"value": float("nan")},
        {"value": float("inf")},
        {"value": -101.0},
        {"value": 71.0},
        {"unit": "MW"},
        {"unit": "m/s"},
        {"height_m": None},
        {"height_m": True},
        {"status": "missing"},
        {"value": None},
        {"missing_reason": "provider_missing"},
    ],
)
def test_weather_profile_and_missing_policy(updates):
    with pytest.raises(ValidationError):
        weather_record(**updates)


def test_weather_grid_and_preceding_hour_radiation_support():
    support = SupportInterval(start_utc=NOW - timedelta(hours=1), end_utc=NOW)
    radiation = weather_record(
        variable=WeatherVariable.SHORTWAVE_RADIATION,
        height_m=None,
        unit="W/m²",
        value=0.0,
        timing=support,
        statistic=Statistic.MEAN,
        returned_grid=WeatherGrid(
            coordinates=Coordinates(latitude=38.1, longitude=-9.2), elevation_m=10.0
        ),
    )
    assert radiation.timing.start_utc.date() < radiation.delivery_date
    assert radiation.returned_grid.coordinates != radiation.site.requested
    assert isinstance(radiation.value, float)
    assert (
        weather_record(value=None, status="missing", missing_reason="provider_missing").value
        is None
    )
    assert (
        weather_record(variable=WeatherVariable.WIND_SPEED, unit="m/s", height_m=10.0).value == 12.3
    )
    with pytest.raises(ValidationError):
        SupportInterval(start_utc=NOW, end_utc=NOW)


@pytest.mark.parametrize("record_factory", [system_record, weather_record])
def test_closed_record_union_and_schema_identity(record_factory):
    record = record_factory()
    adapter = TypeAdapter(NormalizedRecord)
    assert adapter.validate_json(record.model_dump_json()) == record
    assert RecordSchema(family=record.schema_family).version == record.schema_version
    with pytest.raises(ValidationError):
        adapter.validate_json('{"arbitrary":"object"}')
    for field, value in (("schema_version", "2.0.0"), ("schema_family", "market_price")):
        with pytest.raises(ValidationError):
            type(record).model_validate({**record.model_dump(), field: value})


@pytest.mark.parametrize("field", ["start_utc", "end_utc"])
@pytest.mark.parametrize(
    "bad_time", [NOW.replace(tzinfo=None), NOW.astimezone(timezone(timedelta(hours=1)))]
)
def test_query_window_requires_utc_for_both_bounds(field, bad_time):
    valid = {"start_utc": NOW, "end_utc": NOW + timedelta(hours=1)}
    with pytest.raises(ValidationError):
        QueryWindow.model_validate({**valid, field: bad_time})


def test_business_identity_excludes_partition_and_provisional_revision_metadata():
    original = system_record()
    revised = system_record(
        value=Decimal("99.9900"),
        delivery_date=DAY + timedelta(days=1),
        publication_status="final",
        native=NativeSeries(
            series_id="load", document_id="document", revision_id="2", profile_version="1.0.0"
        ),
        source_times=SourceTimes(published_at=NOW, updated_at=NOW + timedelta(days=1)),
    )
    assert original.business_identity == revised.business_identity


def test_new_profile_versions_have_finite_string_bounds():
    oversized = "9" * 40 + ".0.0"
    with pytest.raises(ValidationError):
        NativeSeries(series_id="series", profile_version=oversized)
    with pytest.raises(ValidationError):
        WeatherSite.model_validate({**SITE.model_dump(), "selection_version": oversized})
