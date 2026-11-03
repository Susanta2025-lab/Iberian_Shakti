"""Bounded, inert chart grammar; ordered calendar validation belongs to the parser."""

import json
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, ValidationError, model_validator

from iberian_shakti.contracts._base import FrozenContract
from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.ren import profile

MAX_DEPTH = 12
MAX_NODES = 30_000
MAX_STRING = 4096
MAX_LABELS = 10_000  # Work bound; parser separately checks the complete physical day.
MAX_NUMBER_TOKEN = 128


class ProfileFailure(Exception):
    """No source strings or unchecked exception details cross this boundary."""

    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _decimal(value: object) -> Decimal:
    if type(value) is int:
        return Decimal(value)
    if isinstance(value, Decimal) and value.is_finite():
        return value
    raise ValueError("Expected a finite JSON number")


def _tuple(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


type Text = Annotated[str, Field(max_length=MAX_STRING)]
type Quantity = Annotated[Decimal, BeforeValidator(_decimal)]
type Values = Annotated[
    tuple[Quantity, ...], Field(max_length=profile.MAX_VALUES), BeforeValidator(_tuple)
]


class _Title(FrozenContract):
    text: Text


class _Style(FrozenContract):
    color: Text


class _Tooltip(FrozenContract):
    style: _Style


class _Marker(FrozenContract):
    lineColor: Text


class _XAxis(FrozenContract):
    title: _Title
    categories: Annotated[
        tuple[Annotated[str, Field(pattern=r"^(?:[01][0-9]|2[0-3]):(?:00|15|30|45)$")], ...],
        Field(min_length=1, max_length=MAX_LABELS),
        BeforeValidator(_tuple),
    ]
    max: Annotated[int, Field(gt=0, le=MAX_LABELS)]
    tickInterval: Annotated[int, Field(gt=0, le=MAX_LABELS)]


class _YAxis(FrozenContract):
    title: _Title


class Series(FrozenContract):
    type: Literal["line"]
    name: Annotated[str, Field(min_length=1, max_length=128)]
    data: Values
    # Only these observed presentation keys are irrelevant to measurement meaning.
    color: Text | None = None
    zIndex: int | None = None
    tooltipOptions: _Tooltip | None = None
    marker: _Marker | None = None
    lineWidth: Annotated[int, Field(ge=0, le=100)] | None = None


class Chart(FrozenContract):
    xAxis: _XAxis
    yAxis: _YAxis
    series: Annotated[
        tuple[Series, ...],
        Field(min_length=1, max_length=profile.MAX_SERIES),
        BeforeValidator(_tuple),
    ]

    @model_validator(mode="after")
    def complete_selection(self) -> "Chart":
        if self.xAxis.title.text != "Hour" or self.yAxis.title.text != profile.UNIT:
            raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
        names = [series.name for series in self.series]
        if len(set(names)) != len(names) or set(names) - (
            profile.SELECTED.keys() | profile.UNSELECTED
        ):
            raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
        if not profile.SELECTED.keys() <= set(names):
            raise ProfileFailure(ErrorCode.CONTENT_INVALID)
        count = len(self.xAxis.categories)
        if (
            self.xAxis.max != count
            or sum(len(series.data) for series in self.series) > profile.MAX_VALUES
            or any(len(series.data) != count for series in self.series)
        ):
            raise ProfileFailure(ErrorCode.CONTENT_INVALID)
        return self


def _number(token: str) -> Decimal:
    if len(token) > MAX_NUMBER_TOKEN:
        raise ValueError("Numeric token bound")
    value = Decimal(token)
    if not value.is_finite():
        raise ValueError("Nonfinite number")
    return value


def _integer(token: str) -> int:
    if len(token) > MAX_NUMBER_TOKEN:
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


def _depth(text: str) -> None:
    """Bound nesting before json.loads allocates/recurses; strings stay inert."""
    level = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            level += 1
            if level > MAX_DEPTH:
                raise ValueError("JSON depth bound")
        elif char in "]}":
            level -= 1


def _work(value: object) -> None:
    pending = [value]
    nodes = 0
    while pending:
        item = pending.pop()
        nodes += 1
        if nodes > MAX_NODES:
            raise ValueError("JSON node bound")
        if isinstance(item, str):
            if len(item) > MAX_STRING or any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise ValueError("JSON string bound or surrogate")
        elif isinstance(item, dict):
            if len(item) > 64:
                raise ValueError("JSON object bound")
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            if len(item) > profile.MAX_VALUES:
                raise ValueError("JSON array bound")
            pending.extend(item)


def validate_chart(content: bytes) -> Chart:
    """Validate all arrays including unselected ones; never discard malformed values."""
    if len(content) > profile.MAX_BYTES:
        raise ProfileFailure(ErrorCode.CONTENT_INVALID)
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ProfileFailure(ErrorCode.UNSUPPORTED_ENCODING) from None
    try:
        _depth(text)
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
        return Chart.model_validate(data)
    except ValidationError:
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED) from None
