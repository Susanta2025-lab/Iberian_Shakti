"""Exactly three secret-free product/domain queries, private synthetic auth."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.geography import AreaRole
from iberian_shakti.contracts.ingestion import ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, SystemQuery
from iberian_shakti.ingestion.config import ConfigurationError
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.entsoe.adapter import EntsoeAdapter
from iberian_shakti.ingestion.entsoe.identity import request_for
from iberian_shakti.ingestion.errors import ExecutionError

START = datetime(2026, 10, 25, tzinfo=UTC)
WINDOW = QueryWindow(start_utc=START, end_utc=START + timedelta(hours=3))
TOKEN = 'synthetic-ENTSOE-only-token-"+/?='


@pytest.mark.parametrize("selected", profile.PROFILES)
def test_query_and_transport_preserve_product_domain_role_and_window(selected):
    request = request_for(selected.product, selected.country, WINDOW)
    restored = ApiSourceRequest.model_validate_json(request.model_dump_json())
    assert request == restored and request.query_identity == restored.query_identity
    assert request.source_id == "entsoe" and request.report_id == selected.report_id
    assert request.query.series_ids == (f"{selected.document_type}.{selected.process_type}",)
    assert request.query.area.role is AreaRole.BIDDING_ZONE
    assert request.query.area.native_id == profile.DOMAINS[selected.country]
    assert request.revision is None and request.delivery_date == START.date()
    source = EntsoeAdapter.resolve(request)
    url = httpx.URL(EntsoeAdapter.transport_url(source))
    assert str(url.copy_with(query=None)) == "https://web-api.tp.entsoe.eu/api"
    assert dict(url.params) == {
        "documentType": selected.document_type,
        "processType": selected.process_type,
        selected.domain_parameter: profile.DOMAINS[selected.country],
        "periodStart": "202610250000",
        "periodEnd": "202610250300",
    }
    assert TOKEN not in request.model_dump_json() + source.model_dump_json() + str(url)


def test_all_selections_and_different_windows_have_distinct_canonical_identities():
    queries = [request_for(s.product, s.country, WINDOW) for s in profile.PROFILES]
    queries.append(
        request_for(
            "actual_load", "ES", QueryWindow(start_utc=START, end_utc=START + timedelta(hours=2))
        )
    )
    assert len({r.query_identity for r in queries}) == 4


@pytest.mark.parametrize(
    "product,country",
    [
        ("actual_load", "PT"),
        ("load_forecast", "ES"),
        ("actual_generation", "ES"),
        ("wind_solar_forecast", "FR"),
        ("price", "PT"),
    ],
)
def test_unselected_products_never_resolve(product, country):
    with pytest.raises(ValueError, match="Unsupported Stage 4"):
        request_for(product, country, WINDOW)


@pytest.mark.parametrize("hours", [0, -1, 25.01, 48])
def test_request_windows_are_bounded(hours):
    with pytest.raises(ValidationError):
        request_for(
            "actual_load",
            "ES",
            QueryWindow(start_utc=START, end_utc=START + timedelta(hours=hours)),
        )


@pytest.mark.parametrize("shift", [timedelta(seconds=1), timedelta(microseconds=1)])
def test_request_does_not_silently_truncate_seconds(shift):
    with pytest.raises(ValueError, match="whole UTC minutes"):
        request_for(
            "actual_load", "ES", QueryWindow(start_utc=START + shift, end_utc=WINDOW.end_utc)
        )


def test_shared_utc_contract_and_25_hour_window():
    assert request_for(
        "actual_load", "ES", QueryWindow(start_utc=START, end_utc=START + timedelta(hours=25))
    )
    with pytest.raises(ValidationError):
        QueryWindow(start_utc=START.replace(tzinfo=None), end_utc=WINDOW.end_utc)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "other"),
        ("report_id", "actual_load.A65.A01.v0.1.0"),
        ("report_id", "actual_load.A65.A16.v9.0.0"),
    ],
)
def test_profile_tampering_cannot_reach_transport(field, value):
    request = request_for("actual_load", "ES", WINDOW)
    altered = ApiSourceRequest(**{**request.model_dump(), field: value})
    with pytest.raises(ExecutionError):
        EntsoeAdapter.transport_url(ResolvedSource.for_api(altered))


@pytest.mark.parametrize("series", ["A65.A01", "A69.A16", "A75.A16"])
def test_wrong_document_process_selector_cannot_reach_transport(series):
    request = request_for("actual_load", "ES", WINDOW)
    altered = ApiSourceRequest(
        **request.model_dump(exclude={"query"}),
        query=SystemQuery(area=request.query.area, series_ids=(series,)),
    )
    with pytest.raises(ExecutionError):
        EntsoeAdapter.resolve(altered)


@pytest.mark.parametrize("value", [None, "", "short", "embedded space", "new\nline-token", "é" * 8])
def test_missing_invalid_authentication_fails_before_client_construction(monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail("Client construction before credential validation")

    monkeypatch.setattr(httpx, "Client", forbidden)
    with pytest.raises(ConfigurationError) as caught:
        EntsoeAdapter().retriever(
            retrieval_event_id=UUID(int=1),
            environ={} if value is None else {"ENTSOE_API_TOKEN": value},
        )
    assert str(caught.value) == "Missing or invalid selected-provider credential"
    if value:
        assert value not in str(caught.value) + repr(caught.value)


def test_synthetic_token_is_injected_only_into_private_query():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.params["securityToken"] == TOKEN
        assert "authorization" not in request.headers and "x-api-key" not in request.headers
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(401, stream=httpx.ByteStream(b"unauthorized"))

    retriever = EntsoeAdapter().retriever(
        retrieval_event_id=UUID(int=1),
        environ={"ENTSOE_API_TOKEN": TOKEN},
        transport=httpx.MockTransport(handler),
    )
    assert TOKEN not in repr(retriever.request_policy)
    result = retriever.retrieve(EntsoeAdapter.resolve(request_for("actual_load", "ES", WINDOW)))
    assert len(calls) == 1 and TOKEN not in result.model_dump_json()


def test_default_network_guard_remains_active():
    adapter = EntsoeAdapter()
    with pytest.raises(AssertionError, match="Default pytest forbids network"):
        adapter.retriever(
            retrieval_event_id=UUID(int=1), environ={"ENTSOE_API_TOKEN": TOKEN}
        ).retrieve(adapter.resolve(request_for("actual_load", "ES", WINDOW)))
