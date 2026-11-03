"""REN request identity and selection policy; no source connectivity."""

from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.geography import AreaRole, ExternalBoundary
from iberian_shakti.contracts.ingestion import ResolvedSource
from iberian_shakti.contracts.measurements import (
    GenerationMeasure,
    InterchangeMeasure,
    LoadMeasure,
    Statistic,
    ValueKind,
)
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, SystemQuery
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.ren import profile
from iberian_shakti.ingestion.ren.adapter import RenAdapter
from iberian_shakti.ingestion.ren.identity import request_for

DAY = date(2026, 10, 24)


@pytest.mark.parametrize(
    "name,measure",
    [
        ("Consumption", LoadMeasure()),
        ("Wind", GenerationMeasure(technology="wind")),
        ("Solar", GenerationMeasure(technology="solar")),
        ("Hydro", GenerationMeasure(technology="hydro")),
        ("Natural Gas", GenerationMeasure(technology="natural_gas")),
        ("Biomass", GenerationMeasure(technology="biomass")),
        ("Other Thermal", GenerationMeasure(technology="other_thermal")),
        ("Coal", GenerationMeasure(technology="coal")),
        ("Wave", GenerationMeasure(technology="wave")),
        ("Import", InterchangeMeasure(direction="import")),
        ("Export", InterchangeMeasure(direction="export")),
    ],
)
def test_explicit_stage1_measure_mapping(name, measure):
    assert profile.SELECTED[name] == measure
    assert len(profile.SELECTED) == 11


def test_unselected_is_explicit_and_immutable():
    assert profile.UNSELECTED == {
        "Pumping",
        "Consumption + Storage",
        "Consumption of Batteries",
        "Battery Injection",
    }
    assert not profile.SELECTED.keys() & profile.UNSELECTED
    with pytest.raises(TypeError):
        profile.SELECTED["New concept"] = LoadMeasure()
    assert "Batteries" not in profile.UNSELECTED  # No guessed source-name alias.


def test_geography_does_not_invent_country_zone_equivalence_or_counterparty():
    assert profile.AREA.role is AreaRole.SYSTEM
    assert profile.AREA.country_code == "PT"
    assert profile.AREA.perimeter == "provider_defined"
    assert profile.AREA.native_id is profile.AREA.native_scheme is None
    assert profile.VALUE_KIND is ValueKind.ACTUAL
    assert profile.PUBLICATION_STATUS == "provisional"
    assert isinstance(profile.EXTERNAL_BOUNDARY, ExternalBoundary)
    assert profile.EXTERNAL_BOUNDARY.area == profile.AREA
    assert "ES" not in profile.EXTERNAL_BOUNDARY.model_dump_json()


def test_safe_versioned_query_roundtrip_without_transport_material(monkeypatch):
    class NoEnvironment:
        def __getattribute__(self, name):
            pytest.fail("REN must not read credentials or environment")

    with monkeypatch.context() as patch:
        patch.setattr("os.environ", NoEnvironment())
        adapter = RenAdapter()
        request = request_for(DAY)
        resolved = adapter.resolve(request)
        transport_url = adapter.transport_url(resolved)
    assert (
        adapter.resolve(ApiSourceRequest.model_validate_json(request.model_dump_json())) == resolved
    )
    url = httpx.URL(transport_url)
    assert str(url).startswith(profile.ORIGIN + profile.ENDPOINT_PATH)
    assert dict(url.params) == {"date": str(DAY), "culture": "en-US"}
    assert request.query.series_ids == tuple(sorted(profile.SELECTED))
    assert request.window.start_utc == datetime(2026, 10, 23, 23, tzinfo=UTC)
    assert request.window.end_utc - request.window.start_utc == timedelta(days=1)
    wire = resolved.model_dump_json()
    assert all(x in wire for x in (profile.PRODUCT, profile.CULTURE, profile.PROFILE_VERSION))
    assert "https" not in wire and "servicebus" not in wire
    assert request.revision is None and resolved.observed_revision is None
    assert resolved.safe_locator.endswith(request.query_identity)
    assert request_for(DAY).query_identity == request.query_identity
    assert request_for(DAY + timedelta(days=1)).query_identity != request.query_identity


@pytest.mark.parametrize("change", ["source_id", "report_id", "window", "query"])
def test_reject_nonprofile_query_before_transport(change):
    request = request_for(DAY)
    values = request.model_dump()
    values[change] = {
        "source_id": "other",
        "report_id": "ElectricityConsumptionSupplyDaily",
        "window": QueryWindow(
            start_utc=request.window.start_utc + timedelta(hours=1),
            end_utc=request.window.end_utc,
        ),
        "query": SystemQuery(area=profile.AREA, series_ids=("Consumption",)),
    }[change]
    altered = ApiSourceRequest.model_validate(values)
    with pytest.raises(ExecutionError):
        RenAdapter().resolve(altered)
    with pytest.raises(ExecutionError):
        RenAdapter().transport_url(ResolvedSource.for_api(altered))


@pytest.mark.parametrize("day", ["2026-10-24", datetime(2026, 10, 24), True, None])
def test_source_day_is_strict(day):
    with pytest.raises(ValidationError):
        request_for(day)


def test_provisional_profile_has_no_runtime_timezone_or_statistic_override():
    assert profile.PROFILE_VERSION == profile.PARSER_VERSION == "0.2.0"
    assert profile.TIMEZONE == "Europe/Lisbon"
    assert profile.TIMESTAMP_MEANING == "interval_start"
    assert profile.PERIOD_MINUTES == 15
    assert profile.TIME_SEMANTICS_STATUS == "provisional_empirical"
    assert profile.STATISTIC is Statistic.PROVIDER_PERIOD_VALUE
    with pytest.raises(TypeError):
        RenAdapter(timezone="Europe/Lisbon")


@pytest.mark.parametrize(
    "day,start,end",
    [
        (
            date(2026, 3, 29),
            datetime(2026, 3, 29, tzinfo=UTC),
            datetime(2026, 3, 29, 23, tzinfo=UTC),
        ),
        (
            date(2026, 10, 25),
            datetime(2026, 10, 24, 23, tzinfo=UTC),
            datetime(2026, 10, 26, tzinfo=UTC),
        ),
    ],
)
def test_query_window_covers_physical_civil_day(day, start, end):
    request = request_for(day)
    assert request.window == QueryWindow(start_utc=start, end_utc=end)
