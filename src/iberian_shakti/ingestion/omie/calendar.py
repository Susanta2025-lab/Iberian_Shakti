"""OMIE delivery-day policy; all interval stepping remains in the shared helper."""

from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.contracts.market import MarketInterval
from iberian_shakti.contracts.periods import market_day_intervals
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason

TRANSITION_DATE = date(2025, 10, 1)
MARKET_TIMEZONE = "Europe/Madrid"


@dataclass(frozen=True)
class MarketProfile:
    name: str
    duration_minutes: int


LEGACY = MarketProfile("legacy", 60)
MODERN = MarketProfile("modern", 15)


def profile_for(delivery_date: date) -> MarketProfile:
    return LEGACY if delivery_date < TRANSITION_DATE else MODERN


def intervals_for(delivery_date: date) -> tuple[MarketInterval, ...]:
    try:
        timezone = ZoneInfo(MARKET_TIMEZONE)
    except ZoneInfoNotFoundError as error:
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION) from error
    return market_day_intervals(
        delivery_date,
        timezone=timezone,
        duration_minutes=profile_for(delivery_date).duration_minutes,
    )
