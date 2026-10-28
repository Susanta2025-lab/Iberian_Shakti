"""Synthetic shared chain and committed Phase 1 wire history, entirely offline."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.geography import Area, AreaRole, Coordinates, WeatherSite
from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    MeasurementParseProvenance,
    ParseOutcome,
    ParseProvenance,
    ParseResult,
    ResolvedSource,
    RetrievalOutcome,
    RetrievalProvenance,
    SourceRequest,
    parse_event_from_json,
)
from iberian_shakti.contracts.market import MarketPrice
from iberian_shakti.contracts.measurements import (
    LoadMeasure,
    NativeSeries,
    RecordSchema,
    SchemaFamily,
    SourceTimes,
    Statistic,
    SystemMeasurement,
    ValidInstant,
    ValueKind,
    WeatherMeasurement,
    WeatherVariable,
)
from iberian_shakti.contracts.queries import (
    ApiSourceRequest,
    QueryWindow,
    SystemQuery,
    WeatherQuery,
)
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.auth import PrivateRequestPolicy
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.omie.parser import OmieParser
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.runner import ingest_resolved

NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)
FIXTURES = Path(__file__).resolve().parents[1] / "data"


def source_for(family="system"):
    area = Area(role=AreaRole.CONTROL_AREA, project_id="synthetic_area")
    query = SystemQuery(area=area, series_ids=("load",))
    if family == "weather":
        query = WeatherQuery(
            site=WeatherSite(
                site_id="site",
                selection_version="1.0.0",
                country_code="PT",
                requested=Coordinates(latitude=38.0, longitude=-9.0),
            ),
            model_id="synthetic_model",
            variables=("temperature",),
        )
    return ResolvedSource.for_api(
        ApiSourceRequest(
            source_id="synthetic",
            report_id=family,
            delivery_date=date(2026, 10, 26),
            window=QueryWindow(start_utc=NOW, end_utc=NOW + timedelta(hours=1)),
            query=query,
        )
    )


class SyntheticParser:
    """Capability double: fixed typed value, no provider grammar or network lookup."""

    def __init__(
        self, archive, outcome=ParseOutcome.SUCCESS, error=None, quantity=Decimal("1.2300")
    ):
        self.archive = archive
        self.outcome = outcome
        self.error = error
        self.quantity = quantity

    def parse(self, payload, retrieval, *, parsed_at, parse_event_id):
        # Assert acquisition persistence really happened before any semantic interpretation.
        assert (
            self.archive.load_retrieval(retrieval.archive, retrieval.retrieval_event_id)
            == retrieval
        )
        assert self.archive.load(retrieval.archive).content == payload.content
        query = retrieval.source.request.query
        weather = isinstance(query, WeatherQuery)
        family = SchemaFamily.WEATHER_MEASUREMENT if weather else SchemaFamily.SYSTEM_MEASUREMENT
        records = ()
        if self.outcome is ParseOutcome.SUCCESS:
            common = {
                "source_id": payload.reference.source_id,
                "report_id": payload.reference.report_id,
                "delivery_date": payload.reference.delivery_date,
                "kind": ValueKind.FORECAST,
                "timing": ValidInstant(at_utc=NOW),
                "statistic": Statistic.INSTANT,
                "source_times": SourceTimes(),
                "native": NativeSeries(series_id="synthetic_series", profile_version="1.0.0"),
                "retrieval_event_id": retrieval.retrieval_event_id,
                "parse_event_id": parse_event_id,
            }
            if weather:
                record = WeatherMeasurement(
                    **common,
                    model_id=query.model_id,
                    site=query.site,
                    variable=WeatherVariable.TEMPERATURE,
                    height_m=2.0,
                    unit="°C",
                    value=12.3,
                )
            else:
                record = SystemMeasurement(
                    **common,
                    measure=LoadMeasure(),
                    geography=query.area,
                    unit="MW",
                    value=self.quantity,
                )
            records = (record,)
        return ParseResult(
            provenance=MeasurementParseProvenance(
                retrieval_event_id=retrieval.retrieval_event_id,
                raw=payload.reference,
                archive=retrieval.archive,
                parser_id="synthetic",
                parser_version="1.0.0",
                record_schema=RecordSchema(family=family),
                catalogue_version="1.0.0",
                parsed_at=parsed_at,
                parse_event_id=parse_event_id,
                outcome=self.outcome,
                error_code=self.error,
                record_count=len(records),
            ),
            records=records,
        )


def execute(
    archive,
    *,
    family="system",
    body=b"synthetic original\r\n",
    event=1,
    outcome=ParseOutcome.SUCCESS,
    error=None,
    quantity=Decimal("1.2300"),
):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(body))

    service = HttpRetriever(
        lambda _: "https://shared.invalid/data",
        retrieval_event_id=UUID(int=event),
        transport=httpx.MockTransport(handler),
        now=lambda: NOW + timedelta(seconds=event),
        request_policy=PrivateRequestPolicy("https://shared.invalid"),
        sleeper=lambda _: pytest.fail("Unexpected retry"),
    )
    parser = SyntheticParser(archive, outcome, error, quantity)
    result = ingest_resolved(
        source_for(family),
        retriever=service,
        archive=archive,
        parser=parser,
        parse_event_id=UUID(int=event + 100),
        parsed_at=NOW,
    )
    return result, calls, parser


@pytest.mark.parametrize("family", ["system", "weather"])
def test_new_families_roundtrip_shared_archive_and_replay(tmp_path, monkeypatch, family):
    archive = LocalRawArchive(tmp_path)
    result, calls, parser = execute(archive, family=family)
    assert len(calls) == 1
    assert result.retrieval.contract_version == result.parse.provenance.contract_version == "2.0.0"
    assert result.retrieval.source.request.revision is None
    assert type(result).model_validate_json(result.model_dump_json()) == result
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    monkeypatch.setattr(HttpRetriever, "retrieve", lambda *_: pytest.fail("Replay must be offline"))
    acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
    repeated = parser.parse(
        acquired.payload,
        acquired.provenance,
        parsed_at=NOW + timedelta(days=1),
        parse_event_id=UUID(int=900),
    )
    archive.persist_parse(repeated.provenance)
    assert (
        repeated.provenance.normalized_content_identity
        == result.parse.provenance.normalized_content_identity
    )
    assert repeated.records[0].business_identity == result.parse.records[0].business_identity
    assert repeated.records[0].model_dump(exclude={"parse_event_id"}) == result.parse.records[
        0
    ].model_dump(exclude={"parse_event_id"})
    assert all(p.read_bytes() == b for p, b in before.items())
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2


SEMANTIC_CASES = [
    (ParseOutcome.SUCCESS, None),
    (ParseOutcome.SOURCE_UNAVAILABLE, ErrorCode.NO_DATA),
    (ParseOutcome.PROVIDER_REJECTED, ErrorCode.AUTHENTICATION_FAILURE),
    (ParseOutcome.PROVIDER_REJECTED, ErrorCode.AUTHORIZATION_FAILURE),
    (ParseOutcome.PROVIDER_REJECTED, ErrorCode.RATE_LIMITED),
    (ParseOutcome.PROVIDER_REJECTED, ErrorCode.PROVIDER_REJECTED),
    (ParseOutcome.PROVIDER_REJECTED, ErrorCode.UNSUPPORTED_DOMAIN),
    (ParseOutcome.CONTENT_FAILURE, ErrorCode.SCHEMA_UNSUPPORTED),
    (ParseOutcome.CONTENT_FAILURE, ErrorCode.TIME_SEMANTICS_UNKNOWN),
    (ParseOutcome.CONTENT_FAILURE, ErrorCode.CONTENT_INVALID),
]


@pytest.mark.parametrize("outcome,code", SEMANTIC_CASES)
def test_http_200_semantic_outcomes_archive_first_without_falsifying_status(
    tmp_path, outcome, code
):
    archive = LocalRawArchive(tmp_path)
    result, calls, parser = execute(archive, outcome=outcome, error=code)
    assert len(calls) == 1 and result.retrieval.http_status == 200
    assert result.retrieval.outcome is RetrievalOutcome.RETRIEVED
    assert result.parse.provenance.outcome is outcome and result.parse.provenance.error_code is code
    assert len(result.parse.records) == (1 if code is None else 0)
    assert archive.load(result.retrieval.archive).content == b"synthetic original\r\n"
    stored = next(tmp_path.rglob("parses/*.json"))
    assert parse_event_from_json(stored.read_bytes()) == result.parse.provenance
    if code is not None:
        acquired = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
        again = parser.parse(
            acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=UUID(int=999)
        )
        assert again.records == () and again.provenance.error_code is code


@pytest.mark.parametrize("changed", [False, True])
def test_snapshots_same_query_same_or_changed_content_are_immutable(tmp_path, changed):
    archive = LocalRawArchive(tmp_path)
    first, _, _ = execute(archive)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    second, _, _ = execute(
        archive,
        event=2,
        body=b"corrected synthetic bytes" if changed else b"synthetic original\r\n",
    )
    assert (
        first.retrieval.source.request.query_identity
        == second.retrieval.source.request.query_identity
    )
    assert (first.retrieval.raw == second.retrieval.raw) is (not changed)
    assert first.parse.records[0].business_identity != second.parse.records[0].business_identity
    assert len(list(tmp_path.rglob("payload.bin"))) == (2 if changed else 1)
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 2
    assert all(p.read_bytes() == b for p, b in before.items())
    archive.persist(archive.load(second.retrieval.archive), second.retrieval)
    archive.persist_parse(second.parse.provenance)
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 2
    assert len(list(tmp_path.rglob("parses/*.json"))) == 2


@pytest.mark.parametrize(
    "updates",
    [
        {"outcome": ParseOutcome.SUCCESS, "record_count": 0},
        {"outcome": ParseOutcome.SUCCESS, "error_code": ErrorCode.NO_DATA},
        {
            "outcome": ParseOutcome.SOURCE_UNAVAILABLE,
            "error_code": ErrorCode.CONTENT_INVALID,
            "record_count": 0,
        },
        {
            "outcome": ParseOutcome.PROVIDER_REJECTED,
            "error_code": ErrorCode.TIME_SEMANTICS_UNKNOWN,
            "record_count": 0,
        },
        {
            "outcome": ParseOutcome.CONTENT_FAILURE,
            "error_code": ErrorCode.NO_DATA,
            "record_count": 0,
        },
        {"record_count": True},
        {"contract_version": "1.0.0"},
        {"parsed_at": datetime(2026, 10, 26)},
        {"record_schema": RecordSchema(family=SchemaFamily.MARKET_PRICE)},
    ],
)
def test_invalid_new_semantic_states_fail_closed(tmp_path, updates):
    result, _, _ = execute(LocalRawArchive(tmp_path))
    with pytest.raises(ValidationError):
        MeasurementParseProvenance.model_validate(
            {**result.parse.provenance.model_dump(), **updates}
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"source_id": "other"},
        {"report_id": "other"},
        {"delivery_date": date(2026, 10, 27)},
        {"retrieval_event_id": UUID(int=99)},
        {"parse_event_id": UUID(int=99)},
    ],
)
def test_normalized_union_enforces_source_schema_and_event_linkage(tmp_path, updates):
    result, _, _ = execute(LocalRawArchive(tmp_path))
    record = result.parse.records[0]
    other = SystemMeasurement.model_validate({**record.model_dump(), **updates})
    with pytest.raises(ValidationError):
        ParseResult(provenance=result.parse.provenance, records=(other,))


def test_new_record_family_cannot_use_legacy_price_parse_provenance(tmp_path):
    result, _, _ = execute(LocalRawArchive(tmp_path))
    event = result.parse.provenance
    legacy = ParseProvenance(
        retrieval_event_id=event.retrieval_event_id,
        raw=event.raw,
        archive=event.archive,
        parser_id="synthetic",
        parser_version="1.0.0",
        parsed_at=NOW,
        parse_event_id=event.parse_event_id,
        outcome=ParseOutcome.SUCCESS,
        record_count=1,
    )
    with pytest.raises(ValidationError):
        ParseResult(provenance=legacy, records=result.parse.records)
    with pytest.raises(ValidationError):
        ParseProvenance.model_validate(
            {
                **legacy.model_dump(),
                "outcome": ParseOutcome.SOURCE_UNAVAILABLE,
                "record_count": 0,
                "error_code": ErrorCode.CONTENT_INVALID,
            }
        )


def test_original_phase1_wire_and_stored_events_replay_without_migration(tmp_path):
    history = json.loads((FIXTURES / "shared_contracts/phase_1_history.json").read_text())
    request = SourceRequest.model_validate_json(history["request_json"])
    retrieval = RetrievalProvenance.model_validate_json(history["retrieval_json"])
    parsed = ParseProvenance.model_validate_json(history["parse_json"])
    price = MarketPrice.model_validate_json(history["first_price_json"])
    for model, field in (
        (request, "request_json"),
        (retrieval, "retrieval_json"),
        (parsed, "parse_json"),
        (price, "first_price_json"),
    ):
        assert model.model_dump_json() == history[field]
    assert "schema_family" not in json.loads(parsed.model_dump_json())
    assert "query" not in json.loads(request.model_dump_json())
    assert parsed.schema_family is SchemaFamily.MARKET_PRICE
    # existing_payload_fixture is repository-relative, not tests-relative.
    payload = Path(__file__).resolve().parents[2] / history["existing_payload_fixture"]
    content = payload.read_bytes()
    assert hashlib.sha256(content).hexdigest() == retrieval.raw.sha256
    archived = tmp_path / retrieval.archive.relative_path
    archived.parent.mkdir(parents=True)
    archived.write_bytes(content)
    for category, event, field in (
        ("retrievals", retrieval.retrieval_event_id, "archive_retrieval_json"),
        ("parses", parsed.parse_event_id, "archive_parse_json"),
    ):
        target = archived.parent / category / f"{event}.json"
        target.parent.mkdir()
        target.write_text(history[field])
    original = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    archive = LocalRawArchive(tmp_path)
    loaded = replay(archive, retrieval.archive, retrieval.retrieval_event_id)
    assert loaded.provenance == retrieval
    repeated = OmieParser().parse(
        loaded.payload, loaded.provenance, parsed_at=NOW, parse_event_id=UUID(int=700)
    )
    assert len(repeated.records) == history["record_count"] == 192
    assert repeated.records[0].model_dump(exclude={"parse_event_id"}) == price.model_dump(
        exclude={"parse_event_id"}
    )
    assert repeated.provenance.normalized_content_identity == parsed.normalized_content_identity
    # Reusing an old event must compare byte-for-byte, not rewrite a new schema.
    archive.persist(loaded.payload, loaded.provenance)
    archive.persist_parse(parsed)
    assert all(p.read_bytes() == b for p, b in original.items())
    assert len(list(tmp_path.rglob("*.json"))) == 2


def test_shared_fixture_checksum_inventory():
    root = FIXTURES / "shared_contracts"
    manifest = json.loads((root / "manifest.json").read_text())
    assert set(manifest) == {p.name for p in root.iterdir()} - {"README.md", "manifest.json"}
    for name, sha in manifest.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha
