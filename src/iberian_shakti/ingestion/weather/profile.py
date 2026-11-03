"""Stage 5 ERA5 and operator-selected DWD ICON-EU; independent product versions."""

from iberian_shakti.contracts.geography import Coordinates, WeatherSite

SOURCE_ID = "open_meteo"
PROFILE_VERSION = "0.1.0"
PARSER_ID = "open_meteo.era5.hourly"
PARSER_VERSION = "0.1.0"
HISTORICAL_REPORT = "historical.era5.v0.1.0"
HISTORICAL_MODEL = "era5"
HISTORICAL_ORIGIN = "https://archive-api.open-meteo.com"
HISTORICAL_PATH = "/v1/archive"
FORECAST_ORIGIN = "https://api.open-meteo.com"
FORECAST_PATH = "/v1/forecast"
FORECAST_ENDPOINT = f"{FORECAST_ORIGIN}{FORECAST_PATH}"
FORECAST_MODEL = "icon_eu"
FORECAST_REPORT = "forecast.icon_eu.v0.1.0"
FORECAST_PROFILE_VERSION = "0.1.0"
FORECAST_PARSER_ID = "open_meteo.icon_eu.hourly"
FORECAST_PARSER_VERSION = "0.1.0"
# Main cycles: native hourly through 78 h. Side cycles may be shorter. Only
# next-UTC-day snapshots are supported; complete coverage still must validate.
# Returned grid/elevation can change (announced transition after 2026-11-30).
VARIABLES = ("temperature_2m", "wind_speed_10m", "shortwave_radiation")
CADENCE_SECONDS = 3600
MAX_BYTES = 1024 * 1024
MAX_POINTS = 48
MAX_SITES_PER_REQUEST = 1
MAX_DEPTH = 16
MAX_KEYS = 64
MAX_STRING = 4096
MAX_NUMBER = 128
MAX_NODES = 4096

# Stable logical site identity is independent of the provider's chosen grid.
SITES = tuple(
    WeatherSite(
        site_id=site_id,
        selection_version=PROFILE_VERSION,
        country_code=country,
        requested=Coordinates(latitude=latitude, longitude=longitude),
    )
    for site_id, country, latitude, longitude in (
        ("PT.lisbon", "PT", 38.72, -9.14),
        ("PT.porto", "PT", 41.15, -8.61),
        ("PT.braganca", "PT", 41.81, -6.76),
        ("ES.madrid", "ES", 40.42, -3.70),
        ("ES.zaragoza", "ES", 41.65, -0.89),
        ("ES.seville", "ES", 37.39, -5.98),
    )
)
