"""Strict bounded UTF-8 JSON and selected hourly grammar; no network or conversion."""

import json
import math
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from iberian_shakti.contracts.geography import Coordinates, WeatherGrid
from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.weather import profile


class ProfileFailure(Exception):
    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _finite(value: object) -> float:
    if not isinstance(value, (float, int)) or isinstance(value, bool):
        raise ValueError("Expected JSON number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Expected finite JSON number")
    return result


def _tuple(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


type Number = Annotated[float, BeforeValidator(_finite)]
type Values = Annotated[
    tuple[Number, ...], BeforeValidator(_tuple), Field(min_length=1, max_length=profile.MAX_POINTS)
]


class _Selected(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)


class Hourly(_Selected):
    time: Annotated[
        tuple[int, ...], BeforeValidator(_tuple), Field(min_length=1, max_length=profile.MAX_POINTS)
    ]
    temperature_2m: Values
    wind_speed_10m: Values
    shortwave_radiation: Values


class Units(_Selected):
    time: Literal["unixtime"]
    temperature_2m: Literal["°C"]
    wind_speed_10m: Literal["m/s"]
    shortwave_radiation: Literal["W/m²"]


class WeatherDocument(BaseModel):
    # Presentation/performance metadata is inert and remains in original bytes.
    model_config = ConfigDict(strict=True, frozen=True, extra="ignore", hide_input_in_errors=True)
    latitude: Number
    longitude: Number
    elevation: Number
    utc_offset_seconds: Literal[0]
    timezone: Literal["GMT", "UTC", "Etc/GMT", "Etc/UTC"]
    timezone_abbreviation: Literal["GMT", "UTC"] | None = None
    hourly_units: Units
    hourly: Hourly
    # Model identity is query-selected, not normally returned. If supplied, it
    # must agree; never use optional response text to select a different model.
    model: str | None = None
    models: str | None = None

    def grid(self) -> WeatherGrid:
        return WeatherGrid(
            coordinates=Coordinates(latitude=self.latitude, longitude=self.longitude),
            elevation_m=self.elevation,
        )


def _number(token: str) -> float:
    if len(token) > profile.MAX_NUMBER:
        raise ValueError("Numeric token bound")
    return _finite(float(token))


def _integer(token: str) -> int:
    if len(token) > profile.MAX_NUMBER:
        raise ValueError("Numeric token bound")
    return int(token)


def _constant(token: str) -> None:
    raise ValueError("Nonfinite number")


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    if len(pairs) > profile.MAX_KEYS:
        raise ValueError("Object key bound")
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _work(data: object) -> None:
    pending = [(data, 0)]
    nodes = 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        if depth > profile.MAX_DEPTH or nodes > profile.MAX_NODES:
            raise ValueError("JSON work bound")
        if isinstance(value, str):
            if len(value) > profile.MAX_STRING or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
                raise ValueError("Invalid or oversized JSON string")
        elif isinstance(value, dict):
            pending.extend((v, depth + 1) for v in value.values())
            pending.extend((k, depth + 1) for k in value)
        elif isinstance(value, list):
            if len(value) > profile.MAX_POINTS:
                raise ValueError("JSON array bound")
            pending.extend((v, depth + 1) for v in value)


def validate_document(
    content: bytes, *, model_id: str = profile.HISTORICAL_MODEL
) -> WeatherDocument:
    if len(content) > profile.MAX_BYTES:
        raise ProfileFailure(ErrorCode.CONTENT_INVALID)
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ProfileFailure(ErrorCode.UNSUPPORTED_ENCODING) from None
    try:
        data = json.loads(
            text,
            parse_float=_number,
            parse_int=_integer,
            parse_constant=_constant,
            object_pairs_hook=_object,
        )
        _work(data)
    except (ValueError, ArithmeticError, RecursionError):
        raise ProfileFailure(ErrorCode.CONTENT_INVALID) from None
    if isinstance(data, dict) and "error" in data:
        if data["error"] is True and isinstance(data.get("reason"), str):
            # Only a controlled category crosses the boundary, never reason text.
            raise ProfileFailure(ErrorCode.PROVIDER_REJECTED)
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    try:
        document = WeatherDocument.model_validate(data)
        if any(
            value is not None and value != model_id for value in (document.model, document.models)
        ):
            raise ValueError("Response model contradicts selected product")
        if type(data["utc_offset_seconds"]) is not int:
            raise ValueError("Expected integer UTC offset")
        document.grid()
        size = len(document.hourly.time)
        if any(len(getattr(document.hourly, name)) != size for name in profile.VARIABLES):
            raise ValueError("Mismatched hourly arrays")
        return document
    except (ValidationError, ValueError):
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED) from None
