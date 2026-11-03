"""Pinned, secret-free native indicator queries; synthetic credentials only."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, SystemQuery
from iberian_shakti.ingestion.config import ConfigurationError
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.esios import profile
from iberian_shakti.ingestion.esios.adapter import EsiosAdapter
from iberian_shakti.ingestion.esios.identity import request_for

START = datetime(2026, 10, 25, tzinfo=UTC)
WINDOW = QueryWindow(start_utc=START, end_utc=START + timedelta(hours=3))
TOKEN = 'synthetic-ESIOS-only-token-"+/?='


def test_fixed_product_query_transport_and_identity():
    first = request_for(WINDOW)
    second = ApiSourceRequest.model_validate_json(first.model_dump_json())
    assert first == second and first.query_identity == second.query_identity
    assert first.source_id == "esios" and first.report_id == "indicator544.v0.1.0"
    assert first.query.series_ids == ("544",) and first.query.area == profile.AREA
    assert first.delivery_date == START.date() and first.revision is None
    source = EsiosAdapter().resolve(first)
    assert source == ResolvedSource.for_api(second)
    url = httpx.URL(EsiosAdapter().transport_url(source))
    assert str(url.copy_with(query=None)) == "https://api.esios.ree.es/indicators/544"
    assert dict(url.params) == {
        "start_date": START.isoformat(),
        "end_date": WINDOW.end_utc.isoformat(),
    }
    assert "544" in source.safe_locator
    assert TOKEN not in first.model_dump_json() + source.model_dump_json() + str(url)
    assert (
        request_for(QueryWindow(start_utc=START, end_utc=START + timedelta(hours=2))).query_identity
        != first.query_identity
    )


@pytest.mark.parametrize("hours", [0, -1, 25.01, 48])
def test_invalid_query_window_is_rejected(hours):
    with pytest.raises(ValidationError):
        request_for(QueryWindow(start_utc=START, end_utc=START + timedelta(hours=hours)))


def test_shared_25_hour_ceiling_and_utc_requirement():
    assert request_for(QueryWindow(start_utc=START, end_utc=START + timedelta(hours=25)))
    with pytest.raises(ValidationError):
        QueryWindow(start_utc=datetime(2026, 10, 25), end_utc=WINDOW.end_utc)


@pytest.mark.parametrize("indicator", ["460", "545", "1293", "544.other"])
def test_other_products_cannot_reach_transport(indicator):
    selected = request_for(WINDOW)
    altered = ApiSourceRequest(
        **selected.model_dump(exclude={"query"}),
        query=SystemQuery(area=profile.AREA, series_ids=(indicator,)),
    )
    with pytest.raises(ExecutionError):
        EsiosAdapter().transport_url(ResolvedSource.for_api(altered))


@pytest.mark.parametrize(
    "field,value", [("source_id", "other"), ("report_id", "indicator544.v9.0.0")]
)
def test_other_source_or_profile_is_rejected(field, value):
    selected = request_for(WINDOW)
    changed = ApiSourceRequest(**{**selected.model_dump(), field: value})
    with pytest.raises(ExecutionError):
        EsiosAdapter().resolve(changed)


def test_key_is_injected_only_into_private_header():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["x-api-key"] == TOKEN
        assert "authorization" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        assert TOKEN not in str(request.url)
        return httpx.Response(401, stream=httpx.ByteStream(b"unauthorized"))

    retriever = EsiosAdapter().retriever(
        retrieval_event_id=UUID(int=1),
        environ={"ESIOS_API_TOKEN": TOKEN},
        transport=httpx.MockTransport(handler),
    )
    assert TOKEN not in repr(retriever.request_policy)
    result = retriever.retrieve(EsiosAdapter().resolve(request_for(WINDOW)))
    assert len(calls) == 1
    assert TOKEN not in result.model_dump_json()


@pytest.mark.parametrize("value", [None, "", "short", "embedded space", "new\nline-token", "é" * 8])
def test_missing_or_invalid_credential_fails_before_request_construction(monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail("External request constructed before credential validation")

    monkeypatch.setattr(httpx, "Client", forbidden)
    environment = {} if value is None else {"ESIOS_API_TOKEN": value}
    with pytest.raises(
        ConfigurationError, match="Missing or invalid selected-provider credential"
    ) as caught:
        EsiosAdapter().retriever(retrieval_event_id=UUID(int=1), environ=environment)
    assert str(caught.value) == "Missing or invalid selected-provider credential"
    if value:
        assert value not in str(caught.value) + repr(caught.value)


def test_default_transport_stays_under_offline_network_guard():
    adapter = EsiosAdapter()
    with pytest.raises(AssertionError, match="Default pytest forbids network"):
        adapter.retriever(
            retrieval_event_id=UUID(int=1), environ={"ESIOS_API_TOKEN": TOKEN}
        ).retrieve(adapter.resolve(request_for(WINDOW)))
