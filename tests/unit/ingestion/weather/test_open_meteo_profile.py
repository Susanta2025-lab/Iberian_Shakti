"""Fixed six sites, ERA5 compatibility and explicit ICON-EU selection."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest

from iberian_shakti.contracts.geography import Coordinates, WeatherSite
from iberian_shakti.contracts.ingestion import ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, WeatherQuery
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.weather import profile
from iberian_shakti.ingestion.weather.adapter import OpenMeteoAdapter, OpenMeteoForecastAdapter
from iberian_shakti.ingestion.weather.identity import forecast_request_for, historical_request_for

START = datetime(2026, 10, 25, tzinfo=UTC)
WINDOW = QueryWindow(start_utc=START, end_utc=START + timedelta(days=1))
SITES = [
    ("PT.lisbon", "PT", 38.72, -9.14),
    ("PT.porto", "PT", 41.15, -8.61),
    ("PT.braganca", "PT", 41.81, -6.76),
    ("ES.madrid", "ES", 40.42, -3.70),
    ("ES.zaragoza", "ES", 41.65, -0.89),
    ("ES.seville", "ES", 37.39, -5.98),
]


@pytest.mark.parametrize("site_id,country,latitude,longitude", SITES)
def test_exact_site_and_historical_query(site_id, country, latitude, longitude):
    request = historical_request_for(WINDOW, site_id)
    site = request.query.site
    assert (site.site_id, site.country_code) == (site_id, country)
    assert (site.requested.latitude, site.requested.longitude) == (latitude, longitude)
    assert site.selection_version == "0.1.0"
    assert request.source_id == "open_meteo"
    assert request.report_id == "historical.era5.v0.1.0"
    assert request.query.model_id == "era5"
    assert set(request.query.variables) == set(profile.VARIABLES)
    assert request.revision is None and request.delivery_date == START.date()
    source = OpenMeteoAdapter.resolve(request)
    assert source == ResolvedSource.for_api(
        ApiSourceRequest.model_validate_json(request.model_dump_json())
    )
    url = httpx.URL(OpenMeteoAdapter.transport_url(source))
    assert str(url.copy_with(query=None)) == "https://archive-api.open-meteo.com/v1/archive"
    assert dict(url.params) == {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "start_date": "2026-10-25",
        "end_date": "2026-10-25",
        "models": "era5",
        "hourly": "temperature_2m,wind_speed_10m,shortwave_radiation",
        "timezone": "GMT",
        "timeformat": "unixtime",
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
    }
    assert "best_match" not in str(url)


def test_catalogue_is_exactly_six_and_one_site_per_query():
    assert [site.site_id for site in profile.SITES] == [site[0] for site in SITES]
    assert profile.MAX_SITES_PER_REQUEST == 1
    assert len({historical_request_for(WINDOW, site[0]).query_identity for site in SITES}) == 6
    later = QueryWindow(start_utc=START + timedelta(days=1), end_utc=START + timedelta(days=2))
    assert (
        historical_request_for(later, "PT.lisbon").query_identity
        != historical_request_for(WINDOW, "PT.lisbon").query_identity
    )


@pytest.mark.parametrize("site_id,country,latitude,longitude", SITES)
def test_forecast_pins_selected_product_for_every_site(site_id, country, latitude, longitude):
    request = forecast_request_for(WINDOW, site_id)
    assert request.report_id == "forecast.icon_eu.v0.1.0"
    assert request.query.model_id == "icon_eu"
    assert request.query.site.site_id == site_id
    assert request.query.site.country_code == country
    assert request.query.site.requested == Coordinates(latitude=latitude, longitude=longitude)
    assert request.query.site.selection_version == "0.1.0"
    assert request.query.output.profile_version == "0.1.0"
    assert ApiSourceRequest.model_validate_json(request.model_dump_json()) == request
    source = OpenMeteoForecastAdapter.resolve(request)
    url = httpx.URL(OpenMeteoForecastAdapter.transport_url(source))
    assert str(url.copy_with(query=None)) == profile.FORECAST_ENDPOINT
    assert dict(url.params) == {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "start_date": "2026-10-25",
        "end_date": "2026-10-25",
        "models": "icon_eu",
        "hourly": "temperature_2m,wind_speed_10m,shortwave_radiation",
        "timezone": "GMT",
        "timeformat": "unixtime",
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
    }
    assert request.query_identity != historical_request_for(WINDOW, site_id).query_identity


@pytest.mark.parametrize("site_id", ["PT.madrid", "ES.lisbon", "PT.Lisbon", "PT.faro", "", "auto"])
def test_unknown_site_rejected(site_id):
    with pytest.raises(ValueError):
        historical_request_for(WINDOW, site_id)


@pytest.mark.parametrize("offset,hours", [(0, 1), (0, 23), (0, 25), (1, 24), (0.01, 24)])
def test_only_complete_utc_day_supported(offset, hours):
    start = START + timedelta(hours=offset)
    with pytest.raises(ValueError):
        historical_request_for(
            QueryWindow(start_utc=start, end_utc=start + timedelta(hours=hours)), "PT.lisbon"
        )


@pytest.mark.parametrize("model", ["best_match", "era5_land", "era5_seamless", "arbitrary_model"])
def test_unapproved_models_cannot_reach_historical_transport(model):
    request = historical_request_for(WINDOW, "PT.lisbon")
    altered = ApiSourceRequest(
        **{
            **request.model_dump(),
            "query": WeatherQuery(
                site=request.query.site, model_id=model, variables=profile.VARIABLES
            ),
        }
    )
    with pytest.raises(ExecutionError):
        OpenMeteoAdapter.transport_url(ResolvedSource.for_api(altered))


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "other"),
        ("report_id", "forecast.v0.1.0"),
        ("report_id", "historical.era5.v9.0.0"),
        ("delivery_date", START.date() + timedelta(days=1)),
    ],
)
def test_wrong_product_profile_and_partition_rejected(field, value):
    request = historical_request_for(WINDOW, "PT.lisbon")
    altered = ApiSourceRequest(**{**request.model_dump(), field: value})
    with pytest.raises(ExecutionError):
        OpenMeteoAdapter.resolve(altered)


@pytest.mark.parametrize("change", ["coordinates", "country", "version", "variables"])
def test_site_or_variable_drift_rejected(change):
    request = historical_request_for(WINDOW, "PT.lisbon")
    site = request.query.site
    updates = {
        "coordinates": {"requested": Coordinates(latitude=38.75, longitude=-9.25)},
        "country": {"country_code": "ES"},
        "version": {"selection_version": "9.0.0"},
        "variables": {},
    }[change]
    query = WeatherQuery(
        site=WeatherSite(**{**site.model_dump(), **updates}),
        model_id="era5",
        variables=profile.VARIABLES if change != "variables" else ("temperature_2m",),
    )
    with pytest.raises(ExecutionError):
        OpenMeteoAdapter.resolve(ApiSourceRequest(**{**request.model_dump(), "query": query}))


def test_anonymous_default_transport_remains_under_offline_guard(monkeypatch):
    monkeypatch.delenv("OPEN_METEO_API_KEY", raising=False)
    adapter = OpenMeteoAdapter()
    with pytest.raises(AssertionError, match="Default pytest forbids network"):
        adapter.retriever(retrieval_event_id=UUID(int=1)).retrieve(
            adapter.resolve(historical_request_for(WINDOW, "PT.lisbon"))
        )
