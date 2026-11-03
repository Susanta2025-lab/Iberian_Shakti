"""Small test-only evidence plan using real provider parsers and the shared runner.

All input is synthetic. Existing fixtures supply the grammars; date changes and
OMIE rows are generated in memory. This is not an acquisition planner or a join.
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
import pytest

from iberian_shakti.contracts.ingestion import (
    IngestionResult,
    Parser,
    ParseResult,
    ResolvedSource,
    SourceRequest,
)
from iberian_shakti.contracts.queries import QueryWindow
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.entsoe.adapter import EntsoeAdapter
from iberian_shakti.ingestion.entsoe.identity import request_for as entsoe_request
from iberian_shakti.ingestion.esios.adapter import EsiosAdapter
from iberian_shakti.ingestion.esios.identity import request_for as esios_request
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.omie.calendar import intervals_for
from iberian_shakti.ingestion.omie.identity import download_url, resolved_source
from iberian_shakti.ingestion.omie.parser import OmieParser
from iberian_shakti.ingestion.ren.adapter import RenAdapter
from iberian_shakti.ingestion.ren.identity import request_for as ren_request
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.runner import ingest_resolved
from iberian_shakti.ingestion.weather import profile as weather
from iberian_shakti.ingestion.weather.adapter import OpenMeteoAdapter, OpenMeteoForecastAdapter
from iberian_shakti.ingestion.weather.identity import forecast_request_for, historical_request_for

DATA = Path(__file__).resolve().parents[2] / "data"
DAY = date(2026, 10, 25)
PARSED_AT = datetime(2026, 11, 3, 12, tzinfo=UTC)
TOKENS = {
    "ESIOS_API_TOKEN": "synthetic-stage6-esios-only",
    "ENTSOE_API_TOKEN": "synthetic-stage6-entsoe-only",
}


def forbidden(*args, **kwargs):
    pytest.fail("Offline integration attempted acquisition, credentials, or network")


@dataclass(frozen=True)
class Case:
    key: str
    source: ResolvedSource
    parser: Parser
    body: bytes
    completed_at: datetime
    adapter: RenAdapter | EsiosAdapter | EntsoeAdapter | OpenMeteoAdapter | None = None


def cases_for(day: date = DAY, *, all_sites: bool = False) -> tuple[Case, ...]:
    start = datetime.combine(day, time.min, UTC)
    window = QueryWindow(start_utc=start, end_utc=start + timedelta(hours=3))
    daily = QueryWindow(start_utc=start, end_utc=start + timedelta(days=1))
    acquired = PARSED_AT - timedelta(hours=1)
    # Same deliberately uncorrelated value in both market areas. Counts follow
    # the accepted source calendar; tests assert independent expected boundaries.
    rows = [
        f"{day.year};{day.month};{day.day};{i.period_index};42.00;42.00;"
        for i in intervals_for(day)
    ]
    omie = ("MARGINALPDBC;\n" + "\n".join(rows) + "\n*\n").encode()
    cases = [
        Case(
            "omie",
            resolved_source(
                SourceRequest(
                    source_id="omie", report_id="marginalpdbc", delivery_date=day, revision=1
                ),
                1,
            ),
            OmieParser(),
            omie,
            acquired,
        )
    ]
    fixture = {date(2026, 10, 24): "ordinary", date(2026, 3, 29): "spring", DAY: "autumn"}[day]
    ren = RenAdapter()
    cases.append(
        Case(
            "ren",
            ren.resolve(ren_request(day)),
            ren.parser,
            (DATA / f"ren/synthetic_{fixture}.json").read_bytes(),
            acquired,
            ren,
        )
    )
    esios = EsiosAdapter()
    data = json.loads((DATA / "esios/synthetic_forecast.json").read_bytes())
    # Preserve lexical Decimal tokens; only replace timestamp strings.
    esios_body = (DATA / "esios/synthetic_forecast.json").read_bytes()
    for item, minutes in zip(data["indicator"]["values"], (55, 60, 65), strict=True):
        at = start + timedelta(minutes=minutes)
        esios_body = esios_body.replace(
            item["datetime_utc"].encode(), at.isoformat().replace("+00:00", "Z").encode()
        )
        esios_body = esios_body.replace(
            item["datetime"].encode(), at.astimezone(ZoneInfo("Europe/Madrid")).isoformat().encode()
        )
    cases.append(
        Case(
            "esios", esios.resolve(esios_request(window)), esios.parser, esios_body, acquired, esios
        )
    )
    entsoe = EntsoeAdapter()
    for key, product, country, filename in (
        ("entsoe_load", "actual_load", "ES", "synthetic_es_load.xml"),
        ("entsoe_pt", "wind_solar_forecast", "PT", "synthetic_pt_forecast.xml"),
        ("entsoe_es", "wind_solar_forecast", "ES", "synthetic_es_forecast.xml"),
    ):
        body = (
            (DATA / "entsoe" / filename)
            .read_bytes()
            .replace(b"2026-10-25", day.isoformat().encode())
        )
        cases.append(
            Case(
                key,
                entsoe.resolve(entsoe_request(product, country, window)),
                entsoe.parser,
                body,
                acquired,
                entsoe,
            )
        )
    for model, adapter, builder in (
        ("era5", OpenMeteoAdapter(), historical_request_for),
        ("icon_eu", OpenMeteoForecastAdapter(), forecast_request_for),
    ):
        body = json.loads((DATA / f"open_meteo/synthetic_{model}.json").read_bytes())
        body["hourly"]["time"] = [int(start.timestamp()) + i * 3600 for i in range(24)]
        for site in weather.SITES if all_sites else weather.SITES[:1]:
            cases.append(
                Case(
                    f"{model}:{site.site_id}",
                    adapter.resolve(builder(daily, site.site_id)),
                    adapter.parser,
                    json.dumps(body, ensure_ascii=False).encode(),
                    start - timedelta(hours=12) if model == "icon_eu" else acquired,
                    adapter,
                )
            )
    return tuple(cases)


def execute(
    archive: LocalRawArchive,
    case: Case,
    event: int,
    *,
    body: bytes | None = None,
    status: int = 200,
    timeout: bool = False,
) -> IngestionResult:
    calls = []

    def handler(request):
        calls.append(request)
        source = case.source.request.source_id
        if source == "esios":
            assert request.headers["x-api-key"] == TOKENS["ESIOS_API_TOKEN"]
            assert "securityToken" not in request.url.params
        elif source == "entsoe":
            assert request.url.params["securityToken"] == TOKENS["ENTSOE_API_TOKEN"]
            assert "x-api-key" not in request.headers
        else:
            assert "x-api-key" not in request.headers and "authorization" not in request.headers
            assert "securityToken" not in request.url.params
        if source == "open_meteo":
            assert request.url.params["models"] == case.source.request.query.model_id
        if timeout:
            raise httpx.ReadTimeout("unrestricted synthetic transport prose", request=request)
        return httpx.Response(status, stream=httpx.ByteStream(case.body if body is None else body))

    kwargs = dict(
        retrieval_event_id=UUID(int=event),
        transport=httpx.MockTransport(handler),
        now=lambda: case.completed_at,
    )
    if case.adapter is None:
        retriever = HttpRetriever(download_url, **kwargs, sleeper=forbidden)
    elif isinstance(case.adapter, (EsiosAdapter, EntsoeAdapter)):
        retriever = case.adapter.retriever(**kwargs, environ=TOKENS, sleeper=lambda _: None)
    else:
        retriever = case.adapter.retriever(**kwargs, sleeper=forbidden)
    result = ingest_resolved(
        case.source,
        retriever=retriever,
        archive=archive,
        parser=case.parser,
        parse_event_id=UUID(int=10_000 + event),
        parsed_at=PARSED_AT,
    )
    assert len(calls) == (3 if timeout else 1)
    return result


def seed(archive: LocalRawArchive, cases: tuple[Case, ...]) -> dict[str, IngestionResult]:
    results = {case.key: execute(archive, case, i) for i, case in enumerate(cases, 1)}
    assert all(
        r.parse is not None and r.parse.provenance.outcome.value == "success"
        for r in results.values()
    )
    return results


def reparse(
    archive: LocalRawArchive, case: Case, result: IngestionResult, event: int
) -> ParseResult:
    loaded = replay(archive, result.retrieval.archive, result.retrieval.retrieval_event_id)
    assert loaded.payload.content == case.body
    assert loaded.provenance == result.retrieval
    parsed = case.parser.parse(
        loaded.payload,
        loaded.provenance,
        parsed_at=PARSED_AT + timedelta(days=100),
        parse_event_id=UUID(int=event),
    )
    archive.persist_parse(parsed.provenance)
    assert (
        parsed.provenance.normalized_content_identity
        == result.parse.provenance.normalized_content_identity
    )
    for original, reproduced in zip(result.parse.records, parsed.records, strict=True):
        assert original.model_dump(exclude={"parse_event_id"}) == reproduced.model_dump(
            exclude={"parse_event_id"}
        )
        assert original.business_identity == reproduced.business_identity
    return parsed


def snapshot(root: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def assert_preserved(before: dict[Path, bytes]) -> None:
    assert all(p.read_bytes() == body for p, body in before.items())


def deny_reacquisition(monkeypatch):
    monkeypatch.setattr(HttpRetriever, "retrieve", forbidden)
    monkeypatch.setattr(HttpRetriever, "__init__", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    for module in ("config", "esios.adapter", "entsoe.adapter"):
        monkeypatch.setattr(f"iberian_shakti.ingestion.{module}.load_provider_auth", forbidden)
