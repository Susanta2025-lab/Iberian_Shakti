"""Stage 4 Generation/Load v3 grammar and explicit A01/A03 period semantics.

This validates the supported product subset, not the entire ENTSO-E XSD.
Unknown fields/versions fail; optional metadata remains in the immutable XML.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from xml.etree.ElementTree import Element

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.contracts.queries import QueryWindow
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.entsoe.xml_boundary import ProfileFailure


@dataclass(frozen=True)
class Sample:
    start: datetime
    end: datetime
    resolution: int
    value: Decimal


@dataclass(frozen=True)
class Series:
    mrid: str
    psr: str | None
    samples: tuple[Sample, ...]


@dataclass(frozen=True)
class Document:
    mrid: str
    revision: str | None
    created: datetime
    series: tuple[Series, ...]


def tag(name: str, namespace: str = profile.GL_NAMESPACE) -> str:
    return f"{{{namespace}}}{name}"


def shape(
    node: Element,
    singles: set[str],
    repeated: frozenset[str] = frozenset(),
    *,
    namespace: str = profile.GL_NAMESPACE,
) -> None:
    allowed = {tag(name, namespace) for name in singles | repeated}
    seen: set[str] = set()
    if node.attrib or (node.text and node.text.strip()):
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    for child in node:
        if (
            child.tag not in allowed
            or (child.tag in seen and child.tag not in {tag(n, namespace) for n in repeated})
            or (child.tail and child.tail.strip())
        ):
            raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
        seen.add(child.tag)


def one(node: Element, name: str, namespace: str = profile.GL_NAMESPACE) -> Element:
    children = node.findall(tag(name, namespace))
    if len(children) != 1:
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    return children[0]


def text(node: Element, *, coding_scheme: bool = False) -> str:
    if len(node) or node.text is None or not node.text.strip():
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    expected = {"codingScheme": "A01"} if coding_scheme else {}
    if node.attrib != expected:
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    return node.text.strip()


def field(node: Element, name: str, namespace: str = profile.GL_NAMESPACE) -> str:
    return text(one(node, name, namespace))


def identifier(value: str) -> str:
    # The shared NativeSeries contract's deliberately bounded native ID grammar.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,127}", value):
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    return value


def timestamp(value: str) -> datetime:
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}"
        r"(?::[0-9]{2}(?:\.[0-9]{1,6})?)?(?:Z|\+00:00)",
        value,
    ):
        raise ProfileFailure()
    return datetime.fromisoformat(value).astimezone(UTC)


def interval(node: Element) -> tuple[datetime, datetime]:
    shape(node, {"start", "end"})
    start, end = timestamp(field(node, "start")), timestamp(field(node, "end"))
    if not timedelta(0) < end - start <= profile.MAX_DOCUMENT_DURATION:
        raise ProfileFailure()
    return start, end


def _points(period: Element, count: int) -> tuple[tuple[int, Decimal], ...]:
    result: list[tuple[int, Decimal]] = []
    for point in period.findall(tag("Point")):
        shape(point, {"position", "quantity"})
        position, quantity = field(point, "position"), field(point, "quantity")
        if not re.fullmatch(r"[1-9][0-9]{0,5}", position):
            raise ProfileFailure()
        at = int(position)
        if at > count or (result and at <= result[-1][0]):
            raise ProfileFailure()
        if len(quantity) > 128 or not re.fullmatch(
            r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", quantity
        ):
            raise ProfileFailure()
        result.append((at, Decimal(quantity)))
    if not result or result[0][0] != 1:
        raise ProfileFailure()
    return tuple(result)


def _fixed_blocks(points: tuple[tuple[int, Decimal], ...], count: int) -> tuple[Decimal, ...]:
    # Strictly increasing points are validated first: A01 must cover every cell.
    if tuple(position for position, _ in points) != tuple(range(1, count + 1)):
        raise ProfileFailure()
    return tuple(value for _, value in points)


def _variable_blocks(points: tuple[tuple[int, Decimal], ...], count: int) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for i, (start, value) in enumerate(points):
        end = points[i + 1][0] if i + 1 < len(points) else count + 1
        if end <= start:
            raise ProfileFailure()
        # This is expansion of an explicitly encoded constant block, never
        # interpolation/filling of absent observations or across Period gaps.
        values.extend([value] * (end - start))
    return tuple(values)


def _period(period: Element, curve: str) -> tuple[Sample, ...]:
    shape(period, {"timeInterval", "resolution"}, frozenset({"Point"}))
    start, end = interval(one(period, "timeInterval"))
    resolution = field(period, "resolution")
    if resolution not in profile.RESOLUTIONS:
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    seconds = profile.RESOLUTIONS[resolution]
    step = timedelta(seconds=seconds)
    count, remainder = divmod(end - start, step)
    if remainder or not 0 < count <= profile.MAX_RECORDS:
        raise ProfileFailure()
    points = _points(period, count)
    values = _fixed_blocks(points, count) if curve == "A01" else _variable_blocks(points, count)
    return tuple(
        Sample(start + i * step, start + (i + 1) * step, seconds, value)
        for i, value in enumerate(values)
    )


_PARTICIPANTS = {
    "sender_MarketParticipant.mRID",
    "sender_MarketParticipant.marketRole.type",
    "receiver_MarketParticipant.mRID",
    "receiver_MarketParticipant.marketRole.type",
}


def participants(node: Element, namespace: str = profile.GL_NAMESPACE) -> None:
    for name in _PARTICIPANTS:
        child = node.find(tag(name, namespace))
        if child is not None:
            value = text(child, coding_scheme=name.endswith("mRID"))
            identifier(value)


def validate_document(
    root: Element, selected: profile.ProductProfile, window: QueryWindow
) -> Document:
    shape(
        root,
        {
            "mRID",
            "revisionNumber",
            "type",
            "process.processType",
            "createdDateTime",
            "time_Period.timeInterval",
        }
        | _PARTICIPANTS,
        frozenset({"TimeSeries"}),
    )
    if (field(root, "type"), field(root, "process.processType")) != (
        selected.document_type,
        selected.process_type,
    ):
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    mrid = identifier(field(root, "mRID"))
    created = timestamp(field(root, "createdDateTime"))
    participants(root)
    revision_node = root.find(tag("revisionNumber"))
    revision = text(revision_node) if revision_node is not None else None
    if revision is not None and not re.fullmatch(r"[1-9][0-9]{0,8}", revision):
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    doc_start, doc_end = interval(one(root, "time_Period.timeInterval"))
    # Preserve full declared MTUs that intersect a partial request. No clipping
    # or claim of request completeness; bound the whole document independently.
    if doc_end <= window.start_utc or doc_start >= window.end_utc:
        raise ProfileFailure()
    nodes = root.findall(tag("TimeSeries"))
    if not 0 < len(nodes) <= profile.MAX_SERIES:
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    series = tuple(_series(node, selected, doc_start, doc_end) for node in nodes)
    if len({s.mrid for s in series}) != len(series):
        raise ProfileFailure()
    count = sum(len(s.samples) for s in series)
    if count > profile.MAX_RECORDS:
        raise ProfileFailure()
    # Series mRIDs are observations, not independent business dimensions. Reject
    # even identical duplicates, as the existing ESIOS deterministic policy does.
    # Cross-series order has no meaning; sorting here only detects collisions.
    for psr in {s.psr for s in series}:
        samples = sorted(
            (sample for s in series if s.psr == psr for sample in s.samples),
            key=lambda sample: sample.start,
        )
        if any(b.start < a.end for a, b in pairwise(samples)):
            raise ProfileFailure()
    return Document(mrid, revision, created, series)


def _series(
    node: Element, selected: profile.ProductProfile, doc_start: datetime, doc_end: datetime
) -> Series:
    shape(
        node,
        {
            "mRID",
            "businessType",
            "objectAggregation",
            "inBiddingZone_Domain.mRID",
            "outBiddingZone_Domain.mRID",
            "quantity_Measure_Unit.name",
            "curveType",
            "MktPSRType",
        },
        frozenset({"Period"}),
    )
    mrid = identifier(field(node, "mRID"))
    load = selected.product == "actual_load"
    domain_name = "outBiddingZone_Domain.mRID" if load else "inBiddingZone_Domain.mRID"
    forbidden = "inBiddingZone_Domain.mRID" if load else "outBiddingZone_Domain.mRID"
    if node.find(tag(forbidden)) is not None:
        raise ProfileFailure(ErrorCode.UNSUPPORTED_DOMAIN)
    domain = text(one(node, domain_name), coding_scheme=True)
    if domain != selected.area.native_id:
        raise ProfileFailure(ErrorCode.UNSUPPORTED_DOMAIN)
    if field(node, "quantity_Measure_Unit.name") != "MAW":
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    psr_node = node.find(tag("MktPSRType"))
    psr = None
    if load:
        if psr_node is not None:
            raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
        expected_business, expected_aggregation = "A04", "A01"
    else:
        if psr_node is None:
            raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
        shape(psr_node, {"psrType"})
        psr = field(psr_node, "psrType")
        if psr not in profile.TECHNOLOGIES:
            raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
        expected_business = "A94" if psr == "B16" else "A93"
        expected_aggregation = "A08"
    if (field(node, "businessType"), field(node, "objectAggregation")) != (
        expected_business,
        expected_aggregation,
    ):
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    curve = field(node, "curveType")
    if curve not in {"A01", "A03"}:
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    periods = node.findall(tag("Period"))
    if not 0 < len(periods) <= profile.MAX_PERIODS:
        raise ProfileFailure()
    samples: list[Sample] = []
    for period in periods:
        current = _period(period, curve)
        if (
            current[0].start < doc_start
            or current[-1].end > doc_end
            or (samples and current[0].start < samples[-1].end)
        ):
            raise ProfileFailure()
        samples.extend(current)
    return Series(mrid, psr, tuple(samples))
