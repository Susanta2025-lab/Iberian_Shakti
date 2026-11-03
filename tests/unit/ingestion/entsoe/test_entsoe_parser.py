"""Strict product/period/technology semantics through the real parser boundary."""

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from xml.etree import ElementTree as ET

import pytest

from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome, RawPayload
from iberian_shakti.contracts.measurements import Statistic, SupportInterval, SystemMeasurement
from iberian_shakti.contracts.queries import QueryWindow
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.entsoe.acknowledgement import AckCategory, validate_acknowledgement
from iberian_shakti.ingestion.entsoe.adapter import EntsoeAdapter
from iberian_shakti.ingestion.entsoe.identity import request_for
from iberian_shakti.ingestion.entsoe.schema import tag
from iberian_shakti.ingestion.entsoe.xml_boundary import parse_xml
from iberian_shakti.ingestion.retrieval import result_for

ROOT = Path(__file__).resolve().parents[3] / "data/entsoe"
BODY = (ROOT / "synthetic_es_load.xml").read_bytes()
PT = (ROOT / "synthetic_pt_forecast.xml").read_bytes()
ES = (ROOT / "synthetic_es_forecast.xml").read_bytes()
ACK = (ROOT / "synthetic_acknowledgement.xml").read_bytes()
START = datetime(2026, 10, 25, tzinfo=UTC)
NOW = datetime(2026, 11, 3, tzinfo=UTC)


def parse(body=BODY, product="actual_load", country="ES", start=START, end=None):
    source = EntsoeAdapter.resolve(
        request_for(
            product,
            country,
            QueryWindow(start_utc=start, end_utc=end or start + timedelta(hours=3)),
        )
    )
    acquired = result_for(source, UUID(int=1), NOW, content=body)
    return EntsoeAdapter.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=2)
    )


def mutate(body, path, value=None, *, remove=False):
    root = ET.fromstring(body)
    node = root.find("/".join(tag(part) for part in path.split("/")))
    assert node is not None
    if remove:
        parent = (
            root.find("/".join(tag(part) for part in path.split("/")[:-1])) if "/" in path else root
        )
        parent.remove(node)
    else:
        node.text = value
    return ET.tostring(root, encoding="utf-8")


def failed(result, code=None):
    assert result.provenance.outcome is not ParseOutcome.SUCCESS
    assert result.records == () and result.provenance.record_count == 0
    if code:
        assert result.provenance.error_code is code


def test_actual_load_exact_decimal_interval_support_native_identity_and_timing():
    result = parse()
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.provenance.parser_version == result.provenance.catalogue_version == "0.1.0"
    assert len(result.records) == 3
    assert [r.value for r in result.records] == [
        Decimal("23000.12300"),
        Decimal("23001"),
        Decimal("23002.50"),
    ]
    assert result.records[0].value.as_tuple().exponent == -5
    for record in result.records:
        assert isinstance(record, SystemMeasurement)
        assert record.measure.kind == "load" and record.kind.value == "actual"
        assert record.unit == "MW" and record.statistic is Statistic.PROVIDER_PERIOD_VALUE
        assert isinstance(record.timing, SupportInterval)
        assert record.timing.start_utc.tzinfo is UTC and record.timing.end_utc.tzinfo is UTC
        assert record.geography.native_id == "10YES-REE------0"
        assert record.geography.role.value == "bidding_zone"
        assert record.native.series_id == "synthetic-load"
        assert (
            record.native.document_id == "synthetic-load-document"
            and record.native.revision_id == "1"
        )
        assert record.native.profile_version == "0.1.0"
        assert all(value is None for value in record.source_times.model_dump().values())
        assert record.retrieval_event_id == UUID(int=1) and record.parse_event_id == UUID(int=2)
        assert SystemMeasurement.model_validate_json(record.model_dump_json()) == record
    assert [r.cadence_seconds for r in result.records] == [1800, 1800, 3600]
    assert result.records[0].timing.start_utc == START
    assert result.records[1].timing.end_utc == START + timedelta(hours=1)
    assert result.records[2].timing.start_utc == START + timedelta(hours=2)


@pytest.mark.parametrize(
    "country,body,technologies",
    [
        ("PT", PT, {"solar", "wind_onshore"}),
        ("ES", ES, {"solar", "wind_onshore", "wind_offshore"}),
    ],
    ids=["pt-solar-onshore", "es-three-technologies"],
)
def test_forecast_psr_identity_separate_and_absent_never_zero(country, body, technologies):
    result = parse(body, "wind_solar_forecast", country)
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert len(result.records) == 4 * len(technologies)
    assert {r.measure.technology for r in result.records} == technologies
    inverse = {v: k for k, v in profile.TECHNOLOGIES.items()}
    for record in result.records:
        assert record.kind.value == "forecast" and record.measure.kind == "generation"
        assert record.native.series_id == f"synthetic-{inverse[record.measure.technology]}"
        assert record.geography.country_code == country
        assert record.geography.native_id == profile.DOMAINS[country]
        assert record.value != 0 and record.unit == "MW"
        assert record.source_times.issue_time is None and record.source_times.model_run_time is None
    assert [r.value for r in result.records[:4]] == [
        Decimal("1000.12300"),
        Decimal("1000.12300"),
        Decimal("1001"),
        Decimal("1001"),
    ]


def test_fixture_manifest_synthetic_checksums_and_counts():
    manifest = json.loads((ROOT / "manifest.json").read_bytes())
    assert set(manifest) == {p.name for p in ROOT.iterdir()} - {"README.md", "manifest.json"}
    for name, entry in manifest.items():
        content = (ROOT / name).read_bytes()
        assert (
            len(content) == entry["bytes"]
            and hashlib.sha256(content).hexdigest() == entry["sha256"]
        )
        assert entry["evidence"] == "synthetic" and entry["profile"] == "0.1.0"
        product = "wind_solar_forecast" if "forecast" in name else "actual_load"
        assert (
            len(parse(content, product, "PT" if "_pt_" in name else "ES").records)
            == entry["record_count"]
        )


@pytest.mark.parametrize(
    "path,value",
    [
        ("type", "A69"),
        ("type", "A75"),
        ("process.processType", "A01"),
        ("mRID", ""),
        ("createdDateTime", "yesterday"),
        ("createdDateTime", "2026-10-24T12:00"),
        ("createdDateTime", "2026-10-24T12:00+01:00"),
        ("revisionNumber", "0"),
        ("TimeSeries/businessType", "A01"),
        ("TimeSeries/objectAggregation", "A08"),
        ("TimeSeries/quantity_Measure_Unit.name", "MWH"),
        ("TimeSeries/quantity_Measure_Unit.name", "MW"),
        ("TimeSeries/curveType", "A02"),
        ("TimeSeries/outBiddingZone_Domain.mRID", "10YPT-REN------W"),
        ("TimeSeries/Period/resolution", "PT5M"),
        ("TimeSeries/Period/resolution", "PT1H"),
        ("TimeSeries/Period/resolution", "P1D"),
        ("TimeSeries/Period/resolution", "PT0M"),
        ("TimeSeries/Period/timeInterval/end", "2026-10-25T00:00Z"),
        ("TimeSeries/Period/timeInterval/end", "2026-10-25T00:45Z"),
        ("TimeSeries/Period/timeInterval/start", "2026-10-24T23:00Z"),
        ("TimeSeries/Period/Point/position", "0"),
        ("TimeSeries/Period/Point/position", "3"),
        ("TimeSeries/Period/Point/position", "1.0"),
        ("TimeSeries/Period/Point/position", "-1"),
        ("TimeSeries/Period/Point/quantity", "NaN"),
        ("TimeSeries/Period/Point/quantity", "Infinity"),
        ("TimeSeries/Period/Point/quantity", "1e3"),
        ("TimeSeries/Period/Point/quantity", "1,000"),
        ("TimeSeries/Period/Point/quantity", ""),
        ("TimeSeries/Period/Point/quantity", "1" * 129),
    ],
)
def test_incompatible_metadata_periods_positions_quantities_fail_atomically(path, value):
    failed(parse(mutate(BODY, path, value)))


@pytest.mark.parametrize(
    "path",
    [
        "type",
        "process.processType",
        "mRID",
        "createdDateTime",
        "time_Period.timeInterval",
        "TimeSeries/mRID",
        "TimeSeries/businessType",
        "TimeSeries/objectAggregation",
        "TimeSeries/outBiddingZone_Domain.mRID",
        "TimeSeries/quantity_Measure_Unit.name",
        "TimeSeries/curveType",
        "TimeSeries/Period/resolution",
        "TimeSeries/Period/timeInterval/start",
        "TimeSeries/Period/Point/position",
        "TimeSeries/Period/Point/quantity",
    ],
)
def test_required_metadata_cannot_be_missing(path):
    failed(parse(mutate(BODY, path, remove=True)))


@pytest.mark.parametrize("quantity", ["0", "-2", "+3.0", ".125", "1.23000000000000000000000000001"])
def test_signed_decimal_precision_preserved_without_invented_sign_or_rounding(quantity):
    result = parse(mutate(BODY, "TimeSeries/Period/Point/quantity", quantity))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.records[0].value.as_tuple() == Decimal(quantity).as_tuple()


@pytest.mark.parametrize(
    "path,value",
    [
        ("type", "A65"),
        ("process.processType", "A16"),
        ("TimeSeries/MktPSRType/psrType", "B01"),
        ("TimeSeries/MktPSRType/psrType", "B20"),
        ("TimeSeries/MktPSRType/psrType", "other"),
        ("TimeSeries/businessType", "A93"),
        ("TimeSeries/objectAggregation", "A01"),
        ("TimeSeries/inBiddingZone_Domain.mRID", "10YES-REE------0"),
    ],
)
def test_forecast_cannot_change_product_technology_business_or_domain(path, value):
    failed(parse(mutate(PT, path, value), "wind_solar_forecast", "PT"))


@pytest.mark.parametrize("path", ["TimeSeries/MktPSRType", "TimeSeries/MktPSRType/psrType"])
def test_forecast_without_psr_is_unsupported(path):
    failed(parse(mutate(PT, path, remove=True), "wind_solar_forecast", "PT"))


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "reversed", "outside"])
@pytest.mark.parametrize("curve", ["A01", "A03"])
def test_position_errors_do_not_get_sorted_or_filled(curve, mutation):
    root = ET.fromstring(BODY)
    ts = root.find(tag("TimeSeries"))
    ts.find(tag("curveType")).text = curve
    period = ts.find(tag("Period"))
    points = period.findall(tag("Point"))
    if mutation == "duplicate":
        period.append(deepcopy(points[-1]))
    elif mutation == "missing":
        period.remove(points[0])
    elif mutation == "reversed":
        period.remove(points[0])
        period.append(points[0])
    else:
        points[-1].find(tag("position")).text = "3"
    failed(parse(ET.tostring(root)))


def test_missing_a01_later_position_fails_but_a03_constant_extends_to_period_end():
    # Keep position 1 and omit position 2 instead.
    root = ET.fromstring(BODY)
    period = root.find(f"{tag('TimeSeries')}/{tag('Period')}")
    period.remove(period.findall(tag("Point"))[1])
    failed(parse(ET.tostring(root)))
    root.find(f"{tag('TimeSeries')}/{tag('curveType')}").text = "A03"
    result = parse(ET.tostring(root))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.records[0].value == result.records[1].value == Decimal("23000.12300")
    assert result.records[1].timing.end_utc == START + timedelta(hours=1)


@pytest.mark.parametrize("resolution,positions", [("PT15M", 4), ("PT30M", 2), ("PT60M", 1)])
@pytest.mark.parametrize("curve", ["A01", "A03"])
def test_all_supported_resolutions_per_period(resolution, positions, curve):
    root = ET.fromstring(BODY)
    ts = root.find(tag("TimeSeries"))
    ts.find(tag("curveType")).text = curve
    period = ts.find(tag("Period"))
    period.find(tag("resolution")).text = resolution
    for point in period.findall(tag("Point")):
        period.remove(point)
    for position in range(1, positions + 1) if curve == "A01" else [1]:
        point = ET.SubElement(period, tag("Point"))
        ET.SubElement(point, tag("position")).text = str(position)
        ET.SubElement(point, tag("quantity")).text = "12.50"
    result = parse(ET.tostring(root))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert len(result.records) == positions + 1
    assert result.records[positions - 1].timing.end_utc == START + timedelta(hours=1)


@pytest.mark.parametrize(
    "mutation",
    [
        "period_equal",
        "period_conflict",
        "period_partial",
        "period_reversed",
        "series_equal",
        "series_conflict",
        "same_mrid",
    ],
)
def test_overlaps_identical_duplicates_and_conflicts_are_never_overwritten(mutation):
    root = ET.fromstring(BODY)
    ts = root.find(tag("TimeSeries"))
    if mutation.startswith("period"):
        period = deepcopy(ts.find(tag("Period")))
        if mutation == "period_conflict":
            period.find(f"{tag('Point')}/{tag('quantity')}").text = "9"
        if mutation == "period_partial":
            period.find(f"{tag('timeInterval')}/{tag('start')}").text = "2026-10-25T00:30Z"
            period.find(f"{tag('timeInterval')}/{tag('end')}").text = "2026-10-25T01:30Z"
        if mutation == "period_reversed":
            original = ts.find(tag("Period"))
            ts.remove(original)
            ts.append(original)
        else:
            ts.append(period)
    else:
        copied = deepcopy(ts)
        if mutation != "same_mrid":
            copied.find(tag("mRID")).text = "different-source-series"
        if mutation == "series_conflict":
            copied.find(f"{tag('Period')}/{tag('Point')}/{tag('quantity')}").text = "9"
        root.append(copied)
    failed(parse(ET.tostring(root)), ErrorCode.CONTENT_INVALID)


def test_absent_technology_and_period_gaps_preserved_without_filling():
    root = ET.fromstring(PT)
    root.remove(root.findall(tag("TimeSeries"))[1])
    result = parse(ET.tostring(root), "wind_solar_forecast", "PT")
    assert len(result.records) == 4 and {r.measure.technology for r in result.records} == {"solar"}
    result = parse()
    assert len(result.records) == 3
    assert not any(r.timing.start_utc == START + timedelta(hours=1) for r in result.records)


def test_document_creation_is_validated_but_not_claimed_as_issue_or_update_time():
    changed = mutate(PT, "createdDateTime", "2026-10-24T13:00:00Z")
    before = parse(PT, "wind_solar_forecast", "PT")
    after = parse(changed, "wind_solar_forecast", "PT")
    assert before.records == after.records
    assert before.provenance.raw.sha256 != after.provenance.raw.sha256


def test_revision_optional_and_never_fabricated():
    result = parse(mutate(BODY, "revisionNumber", remove=True))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert all(record.native.revision_id is None for record in result.records)


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"not XML",
        b"<broken>",
        b"<root/>",
        BODY.replace(b"generationloaddocument:3:0", b"generationloaddocument:4:0"),
        BODY.replace(b"quantity_Measure_Unit.name", b"quantity_Measurement_Unit.name"),
        ACK.replace(b"acknowledgementdocument:7:0", b"acknowledgementdocument:8:0"),
    ],
    ids=lambda value: f"synthetic-{len(value)}-bytes",
)
def test_unknown_empty_malformed_namespace_or_schema_never_means_no_data(body):
    failed(parse(body))
    assert parse(body).provenance.error_code is not ErrorCode.NO_DATA


def test_namespace_prefixes_supported_but_foreign_nested_namespace_rejected():
    assert parse(ET.tostring(ET.fromstring(BODY))).provenance.outcome is ParseOutcome.SUCCESS
    changed = BODY.replace(b"<quantity>", b'<quantity xmlns="urn:unknown">', 1)
    failed(parse(changed), ErrorCode.SCHEMA_UNSUPPORTED)


def test_domain_coding_scheme_and_wrong_direction_fail():
    failed(parse(BODY.replace(b'codingScheme="A01">10YES', b'codingScheme="A02">10YES')))
    failed(parse(BODY.replace(b"outBiddingZone_Domain", b"inBiddingZone_Domain")))
    failed(
        parse(
            PT.replace(b"inBiddingZone_Domain", b"outBiddingZone_Domain"),
            "wind_solar_forecast",
            "PT",
        )
    )


@pytest.mark.parametrize(
    "path", ["mRID", "type", "TimeSeries/businessType", "TimeSeries/Period/resolution"]
)
def test_duplicate_metadata_nodes_not_accepted(path):
    root = ET.fromstring(BODY)
    parts = path.split("/")
    parent = root.find("/".join(map(tag, parts[:-1]))) if len(parts) > 1 else root
    parent.append(deepcopy(parent.find(tag(parts[-1]))))
    failed(parse(ET.tostring(root)))


def test_query_context_is_not_support_clipping_or_source_publication():
    result = parse(start=START + timedelta(minutes=15), end=START + timedelta(minutes=45))
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    assert result.records[0].timing.start_utc == START
    assert result.records[-1].timing.end_utc == START + timedelta(hours=3)
    failed(parse(start=START + timedelta(days=1)))


@pytest.mark.parametrize(
    "code,context,category,error",
    [
        ("999", "No matching data found", AckCategory.NO_DATA, ErrorCode.NO_DATA),
        (
            "999",
            "Invalid query attributes or parameters",
            AckCategory.INVALID_REQUEST,
            ErrorCode.PROVIDER_REJECTED,
        ),
        (
            "999",
            "More than 100 matching documents",
            AckCategory.TECHNICAL,
            ErrorCode.PROVIDER_REJECTED,
        ),
        (
            "999",
            "Unauthorized. Missing or invalid security token",
            AckCategory.AUTHENTICATION,
            ErrorCode.AUTHENTICATION_FAILURE,
        ),
        (
            "A05",
            "Sender without valid contract",
            AckCategory.AUTHORIZATION,
            ErrorCode.AUTHORIZATION_FAILURE,
        ),
        ("A94", "Document cannot be processed", AckCategory.TECHNICAL, ErrorCode.PROVIDER_REJECTED),
        ("B18", "Failure", AckCategory.TECHNICAL, ErrorCode.PROVIDER_REJECTED),
        ("A23", "Area invalid", AckCategory.DOMAIN, ErrorCode.UNSUPPORTED_DOMAIN),
        (
            "A04",
            "Time interval incorrect",
            AckCategory.INVALID_REQUEST,
            ErrorCode.PROVIDER_REJECTED,
        ),
        (
            "999",
            "No matching data found but request is invalid",
            AckCategory.UNSUPPORTED,
            ErrorCode.PROVIDER_REJECTED,
        ),
        ("999", "unrecognized reason", AckCategory.UNSUPPORTED, ErrorCode.PROVIDER_REJECTED),
        ("999", None, AckCategory.UNSUPPORTED, ErrorCode.PROVIDER_REJECTED),
        ("A01", "Message accepted", AckCategory.UNSUPPORTED, ErrorCode.PROVIDER_REJECTED),
    ],
)
def test_acknowledgements_use_code_and_documented_context_never_999_alone(
    code, context, category, error
):
    root = ET.fromstring(ACK)
    reason = root.find(tag("Reason", profile.ACK_NAMESPACE))
    reason.find(tag("code", profile.ACK_NAMESPACE)).text = code
    if context is None:
        reason.remove(reason.find(tag("text", profile.ACK_NAMESPACE)))
    else:
        reason.find(tag("text", profile.ACK_NAMESPACE)).text = context
    body = ET.tostring(root)
    assert validate_acknowledgement(parse_xml(body)).category is category
    result = parse(body)
    failed(result, error)
    assert result.provenance.outcome is (
        ParseOutcome.SOURCE_UNAVAILABLE
        if category is AckCategory.NO_DATA
        else ParseOutcome.PROVIDER_REJECTED
    )


def test_mixed_ack_reasons_cannot_be_misclassified_as_no_data():
    root = ET.fromstring(ACK)
    reason = deepcopy(root.find(tag("Reason", profile.ACK_NAMESPACE)))
    reason.find(tag("text", profile.ACK_NAMESPACE)).text = "Unknown refusal"
    root.append(reason)
    failed(parse(ET.tostring(root)), ErrorCode.PROVIDER_REJECTED)


@pytest.mark.parametrize("name", ["mRID", "createdDateTime", "Reason"])
def test_incomplete_ack_fails_schema_not_no_data(name):
    root = ET.fromstring(ACK)
    root.remove(root.find(tag(name, profile.ACK_NAMESPACE)))
    failed(parse(ET.tostring(root)), ErrorCode.SCHEMA_UNSUPPORTED)


def test_payload_hash_linkage_checked_before_xml():
    source = EntsoeAdapter.resolve(
        request_for(
            "actual_load", "ES", QueryWindow(start_utc=START, end_utc=START + timedelta(hours=3))
        )
    )
    acquired = result_for(source, UUID(int=1), NOW, content=BODY)
    corrupt = acquired.payload.model_copy(update={"content": b"corrupt"})
    assert isinstance(corrupt, RawPayload)
    failed(
        EntsoeAdapter.parser.parse(
            corrupt, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=2)
        ),
        ErrorCode.INTEGRITY_FAILURE,
    )


@pytest.mark.parametrize("absent", ["B16", "B19"])
def test_each_absent_forecast_technology_remains_absent(absent):
    root = ET.fromstring(PT)
    for series in root.findall(tag("TimeSeries")):
        if series.find(f"{tag('MktPSRType')}/{tag('psrType')}").text == absent:
            root.remove(series)
    result = parse(ET.tostring(root), "wind_solar_forecast", "PT")
    assert result.provenance.outcome is ParseOutcome.SUCCESS
    expected = {"solar", "wind_onshore"} - {profile.TECHNOLOGIES[absent]}
    assert {record.measure.technology for record in result.records} == expected
    assert len(result.records) == 4


def test_empty_series_selection_is_not_provider_no_data_or_zero():
    root = ET.fromstring(BODY)
    root.remove(root.find(tag("TimeSeries")))
    failed(parse(ET.tostring(root)), ErrorCode.SCHEMA_UNSUPPORTED)


def test_actual_load_cannot_acquire_fabricated_psr_semantics():
    root = ET.fromstring(BODY)
    source_psr = ET.fromstring(PT).find(f"{tag('TimeSeries')}/{tag('MktPSRType')}")
    root.find(tag("TimeSeries")).append(source_psr)
    failed(parse(ET.tostring(root)), ErrorCode.SCHEMA_UNSUPPORTED)


@pytest.mark.parametrize("name", ["cancelledTS", "registeredResource.mRID", "Reason"])
def test_unsupported_series_semantics_fail_instead_of_silently_discarding(name):
    root = ET.fromstring(BODY)
    ET.SubElement(root.find(tag("TimeSeries")), tag(name)).text = "unsupported"
    failed(parse(ET.tostring(root)), ErrorCode.SCHEMA_UNSUPPORTED)
