"""Provider-neutral system/weather values; no parsing, conversion or inference."""

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, ValidationInfo, field_validator, model_validator

from iberian_shakti.contracts._base import (
    FrozenContract,
    Identifier,
    PositiveInt,
    UtcDatetime,
)
from iberian_shakti.contracts.geography import (
    Area,
    NativeIdentifier,
    ProfileVersion,
    SystemGeography,
    WeatherGrid,
    WeatherSite,
)


class SchemaFamily(StrEnum):
    MARKET_PRICE = "market_price"
    SYSTEM_MEASUREMENT = "system_measurement"
    WEATHER_MEASUREMENT = "weather_measurement"


class RecordSchema(FrozenContract):
    family: SchemaFamily
    version: Literal["1.0.0"] = "1.0.0"


class ValueKind(StrEnum):
    ACTUAL = "actual"
    FORECAST = "forecast"
    REANALYSIS = "reanalysis"


class ValidInstant(FrozenContract):
    kind: Literal["instant"] = "instant"
    at_utc: UtcDatetime


class SupportInterval(FrozenContract):
    """Half-open [start, end), independent of source label/cadence."""

    kind: Literal["interval"] = "interval"
    start_utc: UtcDatetime
    end_utc: UtcDatetime

    @model_validator(mode="after")
    def positive_interval(self) -> Self:
        if self.end_utc <= self.start_utc:
            raise ValueError("Support interval must have positive duration")
        return self


type MeasurementTime = Annotated[ValidInstant | SupportInterval, Field(discriminator="kind")]


class SourceTimes(FrozenContract):
    issue_time: UtcDatetime | None = None
    model_run_time: UtcDatetime | None = None
    published_at: UtcDatetime | None = None
    updated_at: UtcDatetime | None = None


class NativeSeries(FrozenContract):
    series_id: NativeIdentifier
    document_id: NativeIdentifier | None = None
    revision_id: NativeIdentifier | None = None
    profile_version: ProfileVersion


class Statistic(StrEnum):
    INSTANT = "instant"
    MEAN = "mean"
    SUM = "sum"
    # Source-period system power; precise aggregation unknown. Not a confirmed
    # interval mean and never sufficient to authorize MW -> MWh conversion.
    PROVIDER_PERIOD_VALUE = "provider_period_value"


class _Measurement(FrozenContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    source_id: Identifier
    report_id: Identifier
    # Query/archive partition; support may cross its midnight boundary.
    delivery_date: date
    kind: ValueKind
    timing: MeasurementTime
    statistic: Statistic
    cadence_seconds: PositiveInt | None = None
    source_times: SourceTimes = SourceTimes()
    native: NativeSeries
    retrieval_event_id: UUID
    parse_event_id: UUID

    @model_validator(mode="after")
    def consistent_time_statistic(self) -> Self:
        if (self.statistic is Statistic.INSTANT) != isinstance(self.timing, ValidInstant):
            raise ValueError("Instant statistics need an instant; period values need an interval")
        if self.kind is ValueKind.ACTUAL and (
            self.source_times.issue_time is not None or self.source_times.model_run_time is not None
        ):
            raise ValueError("Actual measurements cannot claim a forecast issue/model run")
        return self

    @property
    def business_identity(self) -> str:
        """Unknown forecast editions retain original acquisition snapshot identity.

        Replay keeps retrieval_event_id, so a new parse event does not change it.
        Actual corrections are separate through raw/parse provenance, not latest overwrite.
        """
        data = json.loads(self.model_dump_json())
        for key in (
            "value",
            "status",
            "missing_reason",
            "publication_status",
            "parse_event_id",
            "retrieval_event_id",
            "delivery_date",
            "schema_version",
        ):
            data.pop(key, None)
        data["native"] = {"series_id": self.native.series_id}
        times = self.source_times
        data["source_times"] = {
            "issue_time": times.issue_time.isoformat() if times.issue_time else None,
            "model_run_time": times.model_run_time.isoformat() if times.model_run_time else None,
        }
        if self.kind is ValueKind.FORECAST and not (times.issue_time or times.model_run_time):
            data["unknown_edition_acquisition"] = str(self.retrieval_event_id)
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class LoadMeasure(FrozenContract):
    kind: Literal["load"] = "load"


class GenerationMeasure(FrozenContract):
    kind: Literal["generation"] = "generation"
    technology: Identifier


class InterchangeMeasure(FrozenContract):
    kind: Literal["interchange"] = "interchange"
    direction: Literal["import", "export"]
    exchange_kind: Literal["physical", "scheduled", "unspecified"] = "unspecified"


class SystemMeasurement(_Measurement):
    schema_family: Literal[SchemaFamily.SYSTEM_MEASUREMENT] = SchemaFamily.SYSTEM_MEASUREMENT
    measure: Annotated[
        LoadMeasure | GenerationMeasure | InterchangeMeasure, Field(discriminator="kind")
    ]
    geography: SystemGeography
    unit: Literal["MW", "MWh"]
    value: Annotated[Decimal, Field(allow_inf_nan=False)]
    publication_status: Literal["provisional", "final", "unknown"] = "unknown"

    @field_validator("value", mode="before")
    @classmethod
    def decimal_without_float(cls, value: object, info: ValidationInfo) -> object:
        if isinstance(value, Decimal):
            return value
        if info.mode == "json" and isinstance(value, str):
            try:
                return Decimal(value)
            except InvalidOperation:
                raise ValueError("Invalid system decimal string") from None
        raise ValueError("System quantity requires Decimal or a JSON decimal string")

    @model_validator(mode="after")
    def consistent_quantity(self) -> Self:
        if self.kind is ValueKind.REANALYSIS:
            raise ValueError("System measurements support actual or forecast values")
        if isinstance(self.measure, InterchangeMeasure) == isinstance(self.geography, Area):
            raise ValueError("Interchange needs a border/boundary; load/generation need an area")
        if (self.unit == "MWh") != (self.statistic is Statistic.SUM):
            raise ValueError("MWh requires sum; MW supports instant, mean or provider-period power")
        return self


class WeatherVariable(StrEnum):
    TEMPERATURE = "temperature"
    WIND_SPEED = "wind_speed"
    SHORTWAVE_RADIATION = "shortwave_radiation"


class WeatherMeasurement(_Measurement):
    schema_family: Literal[SchemaFamily.WEATHER_MEASUREMENT] = SchemaFamily.WEATHER_MEASUREMENT
    model_id: Identifier
    site: WeatherSite
    returned_grid: WeatherGrid | None = None
    variable: WeatherVariable
    height_m: Annotated[float, Field(ge=0, le=1000, allow_inf_nan=False)] | None = None
    unit: Literal["°C", "m/s", "W/m²"]
    status: Literal["present", "missing"] = "present"
    value: Annotated[float, Field(allow_inf_nan=False)] | None
    missing_reason: Literal["not_reported", "provider_missing"] | None = None

    @model_validator(mode="after")
    def consistent_weather(self) -> Self:
        if self.statistic is Statistic.PROVIDER_PERIOD_VALUE:
            raise ValueError("Provider-period values are supported only for system power")
        if self.status == "missing":
            if self.value is not None or self.missing_reason is None:
                raise ValueError("Missing weather needs null value and an explicit reason")
        elif self.value is None or self.missing_reason is not None:
            raise ValueError("Present weather needs a finite value and no missing reason")
        unit, low, high = {
            WeatherVariable.TEMPERATURE: ("°C", -100.0, 70.0),
            WeatherVariable.WIND_SPEED: ("m/s", 0.0, 150.0),
            WeatherVariable.SHORTWAVE_RADIATION: ("W/m²", 0.0, 2000.0),
        }[self.variable]
        if self.unit != unit or (self.value is not None and not low <= self.value <= high):
            raise ValueError("Weather unit/value is outside the declared scientific profile")
        if self.variable in {WeatherVariable.TEMPERATURE, WeatherVariable.WIND_SPEED}:
            if self.height_m is None or self.statistic is not Statistic.INSTANT:
                raise ValueError("Temperature/wind require explicit height and instant statistic")
        elif self.height_m is not None or self.statistic is Statistic.SUM:
            raise ValueError("Radiation has no measurement height and cannot be an energy sum")
        return self
