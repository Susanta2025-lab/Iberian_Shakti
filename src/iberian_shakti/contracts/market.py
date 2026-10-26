"""Shared normalized prices, independent of provider grammar and calendars."""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, ValidationInfo, field_validator, model_validator

from iberian_shakti.contracts._base import (
    MARKET_SCHEMA_VERSION,
    FrozenContract,
    Identifier,
    MarketSchemaVersion,
    PositiveInt,
    UtcDatetime,
)


class MarketInterval(FrozenContract):
    """Generic positive source period and internally consistent UTC interval."""

    period_index: PositiveInt
    duration_minutes: PositiveInt
    interval_start_utc: UtcDatetime
    interval_end_utc: UtcDatetime

    @model_validator(mode="after")
    def consistent_interval(self) -> Self:
        duration = self.interval_end_utc - self.interval_start_utc
        minutes, remainder = divmod(duration, timedelta(minutes=1))
        if minutes != self.duration_minutes or remainder:
            raise ValueError("Interval must be positive and match duration_minutes")
        return self


class MarketPrice(MarketInterval):
    """One bidding area/interval; parse_event_id links to acquisition history.

    Area and currency use bounded codes rather than OMIE-only enums so other
    providers can extend them. The adapter validates its supported code set.
    This contract expresses prices per MWh.
    Python inputs require Decimal; JSON inputs require decimal strings.
    """

    schema_version: MarketSchemaVersion = MARKET_SCHEMA_VERSION
    source_id: Identifier
    report_id: Identifier
    market: Identifier
    market_area: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_-]{1,15}$")]
    delivery_date: date
    price: Annotated[Decimal, Field(allow_inf_nan=False)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    price_unit: Literal["MWh"]
    parse_event_id: UUID

    @field_validator("price", mode="before")
    @classmethod
    def decimal_without_float(cls, value: object, info: ValidationInfo) -> object:
        if isinstance(value, Decimal):
            return value
        if info.mode == "json" and isinstance(value, str):
            try:
                return Decimal(value)
            except InvalidOperation:
                raise ValueError("Invalid decimal string") from None
        raise ValueError("Price requires Decimal or a JSON decimal string")

    @property
    def business_identity(self) -> tuple[str, str, str, date, int, int]:
        """Acquisition times and revisions do not enter business identity."""
        return (
            self.source_id,
            self.report_id,
            self.market_area,
            self.delivery_date,
            self.period_index,
            self.duration_minutes,
        )
