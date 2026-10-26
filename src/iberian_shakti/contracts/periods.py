"""Pure reusable market-day partitioning, with caller-owned calendar policy.

No default timezone, resolution, transition date, provider profile, or startup
checks belong here. Missing IANA data surfaces as ZoneInfoNotFoundError for the
future execution/configuration layer to translate at startup.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pydantic import TypeAdapter

from iberian_shakti.contracts._base import PositiveInt
from iberian_shakti.contracts.market import MarketInterval

_DATE = TypeAdapter(date, config={"strict": True})
_DURATION = TypeAdapter(PositiveInt, config={"strict": True})


def market_day_intervals(
    delivery_date: date, *, timezone: ZoneInfo, duration_minutes: int
) -> tuple[MarketInterval, ...]:
    """Partition elapsed UTC time between independently converted local midnights.

    A duration must divide the elapsed day exactly; no partial final interval,
    filling or resampling. Step only in UTC across skipped/repeated local hours.
    """
    day = _DATE.validate_python(delivery_date)
    duration = _DURATION.validate_python(duration_minutes)
    if not isinstance(timezone, ZoneInfo):
        raise ValueError("Market calendar requires an IANA timezone")
    start = datetime.combine(day, time.min, timezone).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, timezone).astimezone(UTC)
    minutes, subminute = divmod(end - start, timedelta(minutes=1))
    count, remainder = divmod(minutes, duration)
    if subminute or remainder or count <= 0:
        raise ValueError("Duration must partition a positive complete market day")
    step = timedelta(minutes=duration)
    return tuple(
        MarketInterval(
            period_index=index + 1,
            duration_minutes=duration,
            interval_start_utc=start + index * step,
            interval_end_utc=start + (index + 1) * step,
        )
        for index in range(count)
    )
