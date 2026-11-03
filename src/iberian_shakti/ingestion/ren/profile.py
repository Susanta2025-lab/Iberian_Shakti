"""REN 0.2.0: provisional empirical source periods, never inferred mean MW.

Profile 0.1.0 authorized no normalization (ADR 0005). ADR 0006 accepts the
ordered Lisbon interpretation for forecasting, without provider-authority claims.
"""

from datetime import date
from types import MappingProxyType
from typing import Final
from zoneinfo import ZoneInfo

from iberian_shakti.contracts.geography import Area, AreaRole, ExternalBoundary
from iberian_shakti.contracts.market import MarketInterval
from iberian_shakti.contracts.measurements import (
    GenerationMeasure,
    InterchangeMeasure,
    LoadMeasure,
    Statistic,
    ValueKind,
)
from iberian_shakti.contracts.periods import market_day_intervals

SOURCE_ID: Final = "ren"
PRODUCT: Final = "ElectricityProductionBreakdownDaily"
ORIGIN: Final = "https://servicebus.ren.pt"
ENDPOINT_PATH: Final = "/datahubapi/electricity/ElectricityProductionBreakdownDaily"
CULTURE: Final = "en-US"
PROFILE_VERSION: Final = "0.2.0"
REPORT_ID: Final = f"{PRODUCT}.{CULTURE}.v{PROFILE_VERSION}"
PARSER_ID: Final = "ren-production-breakdown"
PARSER_VERSION: Final = "0.2.0"
UNIT: Final = "MW"
VALUE_KIND: Final = ValueKind.ACTUAL
PUBLICATION_STATUS: Final = "provisional"
TIMEZONE: Final = "Europe/Lisbon"
PERIOD_MINUTES: Final = 15
TIMESTAMP_MEANING: Final = "interval_start"
TIME_SEMANTICS_STATUS: Final = "provisional_empirical"
STATISTIC: Final = Statistic.PROVIDER_PERIOD_VALUE
MAX_BYTES: Final = 1024 * 1024
MAX_SERIES: Final = 32
MAX_VALUES: Final = 10_000


def day_intervals(source_day: date) -> tuple[MarketInterval, ...]:
    """Physical Lisbon civil day; no naive wall-clock stepping or fixed offset."""
    intervals = market_day_intervals(
        source_day, timezone=ZoneInfo(TIMEZONE), duration_minutes=PERIOD_MINUTES
    )
    if len(intervals) not in {92, 96, 100}:
        raise ValueError("Unsupported REN physical day length")
    return intervals


AREA: Final = Area(
    role=AreaRole.SYSTEM,
    project_id="ren_portuguese_system",
    country_code="PT",
    perimeter="provider_defined",
)
EXTERNAL_BOUNDARY: Final = ExternalBoundary(area=AREA)

# These are the Stage 1 measure variants, not a parallel technology vocabulary.
SELECTED: Final[MappingProxyType[str, LoadMeasure | GenerationMeasure | InterchangeMeasure]] = (
    MappingProxyType(
        {
            "Consumption": LoadMeasure(),
            "Wind": GenerationMeasure(technology="wind"),
            "Solar": GenerationMeasure(technology="solar"),
            "Hydro": GenerationMeasure(technology="hydro"),
            "Natural Gas": GenerationMeasure(technology="natural_gas"),
            "Biomass": GenerationMeasure(technology="biomass"),
            "Other Thermal": GenerationMeasure(technology="other_thermal"),
            "Coal": GenerationMeasure(technology="coal"),
            "Wave": GenerationMeasure(technology="wave"),
            "Import": InterchangeMeasure(direction="import"),
            "Export": InterchangeMeasure(direction="export"),
        }
    )
)
UNSELECTED: Final = frozenset(
    {"Pumping", "Consumption + Storage", "Consumption of Batteries", "Battery Injection"}
)
