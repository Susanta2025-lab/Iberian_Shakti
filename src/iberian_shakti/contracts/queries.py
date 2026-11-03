"""Nonsecret bounded API query identity, separate from private HTTP requests."""

import hashlib
import json
from datetime import date, timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, SerializerFunctionWrapHandler, model_serializer, model_validator

from iberian_shakti.contracts._base import FrozenContract, Identifier, UtcDatetime
from iberian_shakti.contracts.geography import (
    NativeIdentifier,
    ProfileVersion,
    SystemGeography,
    WeatherSite,
)


class QueryWindow(FrozenContract):
    """Requested UTC half-open window, not a declaration of returned support."""

    start_utc: UtcDatetime
    end_utc: UtcDatetime

    @model_validator(mode="after")
    def bounded_daily_window(self) -> Self:
        if not timedelta(0) < self.end_utc - self.start_utc <= timedelta(hours=25):
            raise ValueError("Daily API query window must be positive and at most 25 hours")
        return self


class SystemQuery(FrozenContract):
    kind: Literal["system"] = "system"
    area: SystemGeography
    series_ids: Annotated[tuple[NativeIdentifier, ...], Field(min_length=1, max_length=32)]

    @model_validator(mode="after")
    def canonical_series(self) -> Self:
        if len(set(self.series_ids)) != len(self.series_ids):
            raise ValueError("Series selection must be unique")
        object.__setattr__(self, "series_ids", tuple(sorted(self.series_ids)))
        return self


class WeatherOutputSelection(FrozenContract):
    profile_version: ProfileVersion
    temperature_unit: Literal["celsius"] = "celsius"
    wind_speed_unit: Literal["ms"] = "ms"
    timezone: Literal["GMT"] = "GMT"
    timeformat: Literal["unixtime"] = "unixtime"


class WeatherQuery(FrozenContract):
    kind: Literal["weather"] = "weather"
    site: WeatherSite
    model_id: Identifier
    variables: Annotated[tuple[Identifier, ...], Field(min_length=1, max_length=16)]
    output: WeatherOutputSelection | None = None

    @model_serializer(mode="wrap")
    def preserve_legacy_shape(self, handler: SerializerFunctionWrapHandler) -> dict[str, object]:
        data: dict[str, object] = handler(self)
        if self.output is None:
            data.pop("output", None)
        return data

    @model_validator(mode="after")
    def canonical_variables(self) -> Self:
        if len(set(self.variables)) != len(self.variables):
            raise ValueError("Weather variables must be unique")
        object.__setattr__(self, "variables", tuple(sorted(self.variables)))
        return self


class ApiSelectionMode(StrEnum):
    SNAPSHOT = "api_snapshot"


class ApiSourceRequest(FrozenContract):
    contract_version: Literal["2.0.0"] = "2.0.0"
    source_id: Identifier
    report_id: Identifier
    # Compatibility with the immutable raw layout: explicitly a query partition.
    delivery_date: date
    window: QueryWindow
    query: Annotated[SystemQuery | WeatherQuery, Field(discriminator="kind")]
    selection_mode: ApiSelectionMode = ApiSelectionMode.SNAPSHOT

    @property
    def revision(self) -> None:
        """API snapshots have no fabricated numeric provider revision."""
        return None

    @property
    def query_identity(self) -> str:
        canonical = json.dumps(
            json.loads(self.model_dump_json()), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
