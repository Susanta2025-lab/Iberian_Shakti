"""Bounded indicator/values grammar; optional presentation metadata stays optional.

The accepted product pins MW and five minutes. If the response supplies unit,
magnitude or cadence metadata it must agree. Numeric catalogue IDs for those
concepts are deliberately not guessed. All source metadata remains in raw bytes.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.esios import profile


class ProfileFailure(Exception):
    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _quantity(value: object) -> Decimal:
    if type(value) is int:
        return Decimal(value)
    if isinstance(value, Decimal) and value.is_finite():
        return value
    raise ValueError("Expected a finite JSON number")


def _tuple(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


type Text = Annotated[str, Field(min_length=1, max_length=4096)]
type GeoId = Annotated[int, Field(gt=0)]


class _SourceModel(BaseModel):
    # ESIOS includes descriptions, short names and display metadata. They are
    # inert original bytes, not mandatory fields in the normalized contract.
    model_config = ConfigDict(strict=True, frozen=True, extra="ignore", hide_input_in_errors=True)


class Geo(_SourceModel):
    geo_id: GeoId
    geo_name: Literal["Península"]


class Value(_SourceModel):
    value: Annotated[Decimal, BeforeValidator(_quantity)]
    datetime_utc: Text
    datetime: Text | None = None
    geo_id: GeoId
    geo_name: Literal["Península"] | None = None


class _Magnitude(_SourceModel):
    name: Literal["Potencia"]


class _Cadence(_SourceModel):
    name: Literal["Cinco minutos"]


class Indicator(_SourceModel):
    id: Literal[544]
    name: Literal["Demanda prevista Peninsular"] | None = None
    unit: Literal["MW"] | None = None
    magnitud: (
        Annotated[
            tuple[_Magnitude, ...], BeforeValidator(_tuple), Field(min_length=1, max_length=1)
        ]
        | None
    ) = None
    tiempo: (
        Annotated[tuple[_Cadence, ...], BeforeValidator(_tuple), Field(min_length=1, max_length=1)]
        | None
    ) = None
    geos: (
        Annotated[
            tuple[Geo, ...],
            BeforeValidator(_tuple),
            Field(min_length=1, max_length=profile.MAX_GEOS),
        ]
        | None
    ) = None
    values_updated_at: Text | None = None
    values: Annotated[
        tuple[Value, ...],
        BeforeValidator(_tuple),
        Field(min_length=1, max_length=profile.MAX_VALUES),
    ]


class _Document(_SourceModel):
    indicator: Indicator


def timestamp(text: str, *, utc: bool = False) -> datetime:
    # No dates, naive times, basic ISO dates or Python's permissive separators.
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})",
        text,
    ):
        raise ValueError("Expected an offset-aware ISO timestamp")
    result = datetime.fromisoformat(text)
    if utc and result.utcoffset() != timedelta(0):
        raise ValueError("Expected explicit provider UTC")
    return result.astimezone(UTC)


def value_time(value: Value) -> datetime:
    result = timestamp(value.datetime_utc, utc=True)
    if result.second or result.microsecond or result.minute % 5:
        raise ValueError("Observation outside the five-minute grid")
    if value.datetime is not None:
        if timestamp(value.datetime) != result:
            raise ValueError("Local and UTC timestamps disagree")
        local = datetime.fromisoformat(value.datetime)
        if local.utcoffset() != result.astimezone(ZoneInfo("Europe/Madrid")).utcoffset():
            raise ValueError("Local timestamp offset disagrees with peninsular time")
    return result


def _number(token: str) -> Decimal:
    if len(token) > 128:
        raise ValueError("Numeric token bound")
    value = Decimal(token)
    if not value.is_finite():
        raise ValueError("Nonfinite number")
    return value


def _integer(token: str) -> int:
    if len(token) > 128:
        raise ValueError("Numeric token bound")
    return int(token)


def _constant(token: str) -> None:
    raise ValueError("Nonfinite number")


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
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
        if depth > 16 or nodes > 50_000:
            raise ValueError("JSON work bound")
        if isinstance(value, str):
            if len(value) > 4096 or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
                raise ValueError("Invalid or oversized JSON string")
        elif isinstance(value, dict):
            pending.extend((v, depth + 1) for v in value.values())
            pending.extend((k, depth + 1) for k in value)
        elif isinstance(value, list):
            if len(value) > profile.MAX_VALUES:
                raise ValueError("JSON array bound")
            pending.extend((v, depth + 1) for v in value)


def validate_indicator(content: bytes) -> Indicator:
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
    try:
        indicator = _Document.model_validate(data).indicator
        # Literal equality alone would accept 544.0 in Pydantic.
        if type(data["indicator"]["id"]) is not int:
            raise ValueError("Expected integer indicator identity")
        geos = {geo.geo_id: geo.geo_name for geo in indicator.geos or ()}
        if indicator.geos is not None and len(geos) != len(indicator.geos):
            raise ValueError("Duplicate geography metadata")
        # One peninsular series only; never silently select or discard other areas.
        if len({value.geo_id for value in indicator.values}) != 1:
            raise ValueError("Unexpected geographic selection")
        for value in indicator.values:
            if indicator.geos is not None and value.geo_id not in geos:
                raise ValueError("Value geography absent from metadata")
            if value.geo_name is None and value.geo_id not in geos:
                raise ValueError("Missing peninsular geographic identity")
        return indicator
    except (ValidationError, ValueError):
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED) from None
