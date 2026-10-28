"""Typed project geography and separate native identifiers; no provider catalogue."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from iberian_shakti.contracts._base import FrozenContract, Identifier, Version

NativeIdentifier = Annotated[
    str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_. -]{0,127}\z", max_length=128)
]
CountryCode = Annotated[str, Field(pattern=r"^[A-Z]{2}\z")]
ProfileVersion = Annotated[Version, Field(max_length=32)]


class AreaRole(StrEnum):
    COUNTRY = "country"
    SYSTEM = "system"
    BIDDING_ZONE = "bidding_zone"
    CONTROL_AREA = "control_area"
    PROVIDER_AREA = "provider_area"


class Area(FrozenContract):
    kind: Literal["area"] = "area"
    role: AreaRole
    project_id: Identifier
    country_code: CountryCode | None = None
    perimeter: Literal["mainland", "whole_country", "provider_defined"] | None = None
    native_id: NativeIdentifier | None = None
    native_scheme: Literal["eic", "provider"] | None = None

    @model_validator(mode="after")
    def consistent_area(self) -> Self:
        if (self.native_id is None) != (self.native_scheme is None):
            raise ValueError("Native area identifier and scheme must be supplied together")
        if self.role is AreaRole.COUNTRY:
            if self.country_code is None or self.project_id != self.country_code:
                raise ValueError("Country area must identify its country explicitly")
        if (self.role is AreaRole.SYSTEM) != (self.perimeter is not None):
            raise ValueError("Only a system area requires an explicit perimeter")
        return self


class DirectedBorder(FrozenContract):
    kind: Literal["directed_border"] = "directed_border"
    from_area: Area
    to_area: Area

    @model_validator(mode="after")
    def distinct_endpoints(self) -> Self:
        if self.from_area == self.to_area:
            raise ValueError("Directed border endpoints must differ")
        return self


class ExternalBoundary(FrozenContract):
    kind: Literal["external_boundary"] = "external_boundary"
    area: Area


type SystemGeography = Annotated[
    Area | DirectedBorder | ExternalBoundary, Field(discriminator="kind")
]


class Coordinates(FrozenContract):
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]


class WeatherSite(FrozenContract):
    site_id: Identifier
    selection_version: ProfileVersion
    country_code: CountryCode
    requested: Coordinates


class WeatherGrid(FrozenContract):
    coordinates: Coordinates
    elevation_m: Annotated[float, Field(ge=-500, le=10_000, allow_inf_nan=False)] | None = None
