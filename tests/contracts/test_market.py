"""Shared interval/price validation without OMIE lexical or calendar policy."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.market import MarketInterval, MarketPrice


@pytest.mark.parametrize("area", ["PT", "ES"])
@pytest.mark.parametrize("price", [Decimal("+12.34"), Decimal("-12.34"), Decimal("0.00")])
def test_areas_and_signed_prices(market_price: MarketPrice, area: str, price: Decimal) -> None:
    record = MarketPrice.model_validate(
        {**market_price.model_dump(), "market_area": area, "price": price}
    )
    assert record.price == price
    assert record.market_area == area


@pytest.mark.parametrize("duration", [15, 60, 5, 30])
def test_generic_durations(market_price: MarketPrice, duration: int) -> None:
    record = MarketPrice.model_validate(
        {
            **market_price.model_dump(),
            "duration_minutes": duration,
            "interval_end_utc": market_price.interval_start_utc + timedelta(minutes=duration),
        }
    )
    assert record.duration_minutes == duration


def test_decimal_precision_and_json_round_trip(market_price: MarketPrice) -> None:
    price = Decimal("-12345678901234567890.123456789012345678900")
    record = MarketPrice.model_validate({**market_price.model_dump(), "price": price})
    encoded = record.model_dump_json()
    assert json.loads(encoded)["price"] == str(price)
    restored = MarketPrice.model_validate_json(encoded)
    assert restored == record
    assert restored.price.as_tuple() == price.as_tuple()
    assert record.model_dump()["price"] is price


@pytest.mark.parametrize("value", [12.34, 0.0, -1.0, 12, True, "12.34"])
def test_python_price_requires_decimal(market_price: MarketPrice, value: object) -> None:
    with pytest.raises(ValidationError):
        MarketPrice.model_validate({**market_price.model_dump(), "price": value})


@pytest.mark.parametrize("value", [12.34, 0, True, None])
def test_json_price_requires_decimal_string(market_price: MarketPrice, value: object) -> None:
    values = json.loads(market_price.model_dump_json())
    values["price"] = value
    with pytest.raises(ValidationError):
        MarketPrice.model_validate_json(json.dumps(values))


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_prices_must_be_finite(market_price: MarketPrice, value: str) -> None:
    with pytest.raises(ValidationError):
        MarketPrice.model_validate({**market_price.model_dump(), "price": Decimal(value)})
    values = json.loads(market_price.model_dump_json())
    values["price"] = value
    with pytest.raises(ValidationError):
        MarketPrice.model_validate_json(json.dumps(values))


@pytest.mark.parametrize("field", ["interval_start_utc", "interval_end_utc"])
@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2026, 10, 25, 23),
        datetime(2026, 10, 25, 23, tzinfo=timezone(timedelta(hours=1))),
        "2026-10-25T23:00:00Z",
    ],
)
def test_timestamps_require_aware_utc_objects(
    market_price: MarketPrice, field: str, timestamp: object
) -> None:
    with pytest.raises(ValidationError):
        MarketPrice.model_validate({**market_price.model_dump(), field: timestamp})


@pytest.mark.parametrize("minutes", [0, -15, 14, 16, 60])
def test_invalid_interval_end(market_price: MarketPrice, minutes: int) -> None:
    with pytest.raises(ValidationError):
        MarketPrice.model_validate(
            {
                **market_price.model_dump(),
                "interval_end_utc": market_price.interval_start_utc + timedelta(minutes=minutes),
            }
        )


def test_subminute_mismatch_rejected(market_price: MarketPrice) -> None:
    with pytest.raises(ValidationError):
        MarketPrice.model_validate(
            {
                **market_price.model_dump(),
                "interval_end_utc": market_price.interval_end_utc + timedelta(microseconds=1),
            }
        )


@pytest.mark.parametrize("field", ["period_index", "duration_minutes"])
@pytest.mark.parametrize("value", [0, -1, True, 1.0, "1"])
def test_positive_strict_period_and_duration(
    market_price: MarketPrice, field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        MarketPrice.model_validate({**market_price.model_dump(), field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("market_area", ""),
        ("market_area", "pt"),
        ("market_area", "PT?token=x"),
        ("currency", "eur"),
        ("currency", "EURO"),
        ("price_unit", "kWh"),
        ("market", ""),
        ("parse_event_id", "not-a-uuid"),
        ("schema_version", "2.0.0"),
    ],
)
def test_invalid_codes_and_versions(market_price: MarketPrice, field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        MarketPrice.model_validate({**market_price.model_dump(), field: value})


def test_extensible_area_currency_and_period_count(market_price: MarketPrice) -> None:
    record = MarketPrice.model_validate(
        {
            **market_price.model_dump(),
            "source_id": "future_provider",
            "market_area": "FR",
            "currency": "USD",
            "period_index": 300,
        }
    )
    assert record.period_index == 300
    assert record.market_area == "FR"


def test_record_is_closed_frozen_and_identity_is_event_independent(
    market_price: MarketPrice,
) -> None:
    with pytest.raises(ValidationError):
        market_price.price = Decimal("0")
    with pytest.raises(ValidationError):
        MarketPrice.model_validate({**market_price.model_dump(), "unexpected": "value"})
    new_event = MarketPrice.model_validate(
        {**market_price.model_dump(), "parse_event_id": UUID(int=99)}
    )
    assert new_event.business_identity == market_price.business_identity
    assert market_price.business_identity == (
        market_price.source_id,
        market_price.report_id,
        market_price.market_area,
        market_price.delivery_date,
        market_price.period_index,
        market_price.duration_minutes,
    )


def test_shared_interval_enforces_same_validation(market_price: MarketPrice) -> None:
    fields = {field: getattr(market_price, field) for field in MarketInterval.model_fields}
    assert MarketInterval.model_validate(fields).duration_minutes == 15
    with pytest.raises(ValidationError):
        MarketInterval.model_validate(
            {**fields, "interval_end_utc": market_price.interval_start_utc}
        )


@pytest.mark.parametrize("value", ["", "not-a-price"])
def test_invalid_json_decimal_text(market_price: MarketPrice, value: str) -> None:
    values = json.loads(market_price.model_dump_json())
    values["price"] = value
    with pytest.raises(ValidationError):
        MarketPrice.model_validate_json(json.dumps(values))


def test_impossible_duration_rejected_without_arithmetic_overflow(
    market_price: MarketPrice,
) -> None:
    with pytest.raises(ValidationError):
        MarketPrice.model_validate({**market_price.model_dump(), "duration_minutes": 10**30})
