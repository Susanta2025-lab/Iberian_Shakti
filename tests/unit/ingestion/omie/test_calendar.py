"""OMIE profile selection and provider coverage around DST and the transition."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest

from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.omie import calendar
from iberian_shakti.ingestion.omie.calendar import intervals_for, profile_for


@pytest.mark.parametrize(
    "day,count,resolution,start,end",
    [
        ("2025-02-01", 24, 60, "2025-01-31T23:00", "2025-02-01T23:00"),
        ("2025-03-30", 23, 60, "2025-03-29T23:00", "2025-03-30T22:00"),
        ("2024-10-27", 25, 60, "2024-10-26T22:00", "2024-10-27T23:00"),
        ("2026-10-26", 96, 15, "2026-10-25T23:00", "2026-10-26T23:00"),
        ("2026-03-29", 92, 15, "2026-03-28T23:00", "2026-03-29T22:00"),
        ("2026-10-25", 100, 15, "2026-10-24T22:00", "2026-10-25T23:00"),
        ("2025-09-30", 24, 60, "2025-09-29T22:00", "2025-09-30T22:00"),
        ("2025-10-01", 96, 15, "2025-09-30T22:00", "2025-10-01T22:00"),
    ],
)
def test_provider_profile(day, count, resolution, start, end):
    day = date.fromisoformat(day)
    intervals = intervals_for(day)
    profile = profile_for(day)
    assert profile.duration_minutes == resolution
    assert profile.name == ("legacy" if resolution == 60 else "modern")
    assert len(intervals) == count
    assert [item.period_index for item in intervals] == list(range(1, count + 1))
    assert {item.duration_minutes for item in intervals} == {resolution}
    assert intervals[0].interval_start_utc == datetime.fromisoformat(start).replace(tzinfo=UTC)
    assert intervals[-1].interval_end_utc == datetime.fromisoformat(end).replace(tzinfo=UTC)
    assert all(
        a.interval_end_utc == b.interval_start_utc
        for a, b in zip(intervals, intervals[1:], strict=False)
    )
    assert intervals[-1].interval_end_utc - intervals[0].interval_start_utc == timedelta(
        minutes=count * resolution
    )


@pytest.mark.parametrize(
    "day,occurrences",
    [
        (date(2025, 3, 30), 0),
        (date(2024, 10, 27), 2),
        (date(2026, 3, 29), 0),
        (date(2026, 10, 25), 8),
    ],
)
def test_skipped_repeated_hour(day, occurrences):
    local = [i.interval_start_utc.astimezone(ZoneInfo("Europe/Madrid")) for i in intervals_for(day)]
    repeated = [instant for instant in local if instant.hour == 2]
    assert len(repeated) == occurrences
    if occurrences:
        assert {instant.fold for instant in repeated} == {0, 1}
        assert {instant.utcoffset() for instant in repeated} == {
            timedelta(hours=1),
            timedelta(hours=2),
        }


def test_missing_timezone_is_safe_configuration_error(monkeypatch):
    def missing(_):
        raise ZoneInfoNotFoundError("synthetic-secret")

    monkeypatch.setattr(calendar, "ZoneInfo", missing)
    with pytest.raises(ExecutionError) as caught:
        intervals_for(date(2026, 10, 26))
    assert caught.value.reason is FailureReason.CONFIGURATION
    assert "synthetic-secret" not in str(caught.value)
