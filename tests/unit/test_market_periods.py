"""Accepted profile examples passed explicitly to the provider-neutral helper.

The transition policy remains test data here; no OMIE profile is implemented.
These dates/assertions are calendar invariants, not downloaded report fixtures.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.periods import market_day_intervals


@pytest.mark.parametrize(
    ("day", "duration", "count", "utc_hour"),
    [
        (date(2025, 1, 15), 60, 24, 23),
        (date(2025, 3, 30), 60, 23, 23),
        (date(2024, 10, 27), 60, 25, 22),
        (date(2026, 1, 15), 15, 96, 23),
        (date(2026, 3, 29), 15, 92, 23),
        (date(2026, 10, 25), 15, 100, 22),
        (date(2025, 9, 30), 60, 24, 22),
        (date(2025, 10, 1), 15, 96, 22),
        (date(2024, 2, 29), 60, 24, 23),
    ],
)
def test_accepted_profile_invariants(day: date, duration: int, count: int, utc_hour: int) -> None:
    timezone = ZoneInfo("Europe/Madrid")
    periods = market_day_intervals(day, timezone=timezone, duration_minutes=duration)
    assert isinstance(periods, tuple)
    assert len(periods) == count
    assert tuple(period.period_index for period in periods) == tuple(range(1, count + 1))
    assert periods[0].interval_start_utc.date() == day - timedelta(days=1)
    assert periods[0].interval_start_utc.hour == utc_hour
    assert periods[0].interval_start_utc.astimezone(timezone).date() == day
    assert periods[-1].interval_end_utc.astimezone(timezone).date() == day + timedelta(days=1)
    assert periods[-1].interval_end_utc.astimezone(timezone).hour == 0
    assert periods[-1].interval_end_utc - periods[0].interval_start_utc == timedelta(
        minutes=count * duration
    )
    for period in periods:
        assert period.interval_start_utc.tzinfo is UTC
        assert period.interval_end_utc.tzinfo is UTC
        assert period.interval_end_utc - period.interval_start_utc == timedelta(minutes=duration)
        assert period.duration_minutes == duration
    for previous, current in zip(periods, periods[1:], strict=False):
        assert previous.interval_end_utc == current.interval_start_utc
    with pytest.raises(ValidationError):
        periods[0].period_index = 0


def test_utc_boundaries_span_spring_offset_change() -> None:
    periods = market_day_intervals(
        date(2026, 3, 29), timezone=ZoneInfo("Europe/Madrid"), duration_minutes=15
    )
    assert periods[0].interval_start_utc == datetime(2026, 3, 28, 23, tzinfo=UTC)
    assert periods[-1].interval_end_utc == datetime(2026, 3, 29, 22, tzinfo=UTC)
    local_starts = [p.interval_start_utc.astimezone(ZoneInfo("Europe/Madrid")) for p in periods]
    assert not any(start.hour == 2 for start in local_starts)


def test_autumn_repeated_hour_has_distinct_utc_intervals() -> None:
    timezone = ZoneInfo("Europe/Madrid")
    periods = market_day_intervals(date(2026, 10, 25), timezone=timezone, duration_minutes=15)
    repeated = [
        p.interval_start_utc.astimezone(timezone)
        for p in periods
        if p.interval_start_utc.astimezone(timezone).hour == 2
    ]
    assert len(repeated) == 8
    assert {start.fold for start in repeated} == {0, 1}
    assert {start.utcoffset() for start in repeated} == {timedelta(hours=1), timedelta(hours=2)}
    assert periods[0].interval_start_utc == datetime(2026, 10, 24, 22, tzinfo=UTC)
    assert periods[-1].interval_end_utc == datetime(2026, 10, 25, 23, tzinfo=UTC)


@pytest.mark.parametrize("duration", [0, -1, True, 15.0, "15", 7, 1500])
def test_invalid_resolution_or_incomplete_partition(duration: object) -> None:
    with pytest.raises((ValidationError, ValueError)):
        market_day_intervals(
            date(2026, 1, 15), timezone=ZoneInfo("Europe/Madrid"), duration_minutes=duration
        )


def test_no_provider_defaults_or_transition_policy() -> None:
    periods = market_day_intervals(
        date(2026, 10, 25), timezone=ZoneInfo("UTC"), duration_minutes=30
    )
    assert len(periods) == 48
    assert periods[0].interval_start_utc == datetime(2026, 10, 25, tzinfo=UTC)
    assert (
        len(
            market_day_intervals(
                date(2026, 10, 25), timezone=ZoneInfo("Europe/Madrid"), duration_minutes=60
            )
        )
        == 25
    )


@pytest.mark.parametrize("day", ["2026-10-25", datetime(2026, 10, 25)])
def test_day_requires_date_object(day: object) -> None:
    with pytest.raises(ValidationError):
        market_day_intervals(day, timezone=ZoneInfo("Europe/Madrid"), duration_minutes=15)


def test_huge_resolution_is_invalid_without_overflow() -> None:
    with pytest.raises(ValueError):
        market_day_intervals(
            date(2026, 10, 25), timezone=ZoneInfo("Europe/Madrid"), duration_minutes=10**30
        )


def test_fixed_offset_does_not_replace_iana_calendar() -> None:
    with pytest.raises(ValueError, match="IANA timezone"):
        market_day_intervals(date(2026, 10, 25), timezone=UTC, duration_minutes=15)
