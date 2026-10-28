"""Stage 1 private requests and credential echoes, with injected offline transport."""

import gzip
import io
import json
import logging
from collections.abc import Mapping
from urllib.parse import quote
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from iberian_shakti.common.logging import configure_logging
from iberian_shakti.contracts.ingestion import ErrorCode, ResolvedSource, RetrievalOutcome
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow, SystemQuery
from iberian_shakti.ingestion.archive import LocalRawArchive, persist_retrieval
from iberian_shakti.ingestion.auth import (
    HeaderAuthentication,
    PrivateRequestPolicy,
    QueryAuthentication,
)
from iberian_shakti.ingestion.config import (
    ConfigurationError,
    ProviderSecretSettings,
    load_provider_auth,
)
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.http import HttpRetriever

from .conftest import ACQUIRED_AT

SECRET = "synthetic-stage1-secret/+="


@pytest.fixture
def safe_output():
    root = logging.getLogger()
    names = {"httpx", "httpcore"} | {
        name for name in root.manager.loggerDict if name.startswith(("httpx.", "httpcore."))
    }
    loggers = [root, *(logging.getLogger(name) for name in names)]
    saved = [(log, log.handlers[:], log.level, log.propagate) for log in loggers]
    output = io.StringIO()
    configure_logging("DEBUG", stream=output)
    try:
        yield output
    finally:
        for log, handlers, level, propagate in saved:
            log.handlers[:] = handlers
            log.setLevel(level)
            log.propagate = propagate


@pytest.fixture
def api_source():
    from iberian_shakti.contracts.geography import Area, AreaRole

    request = ApiSourceRequest(
        source_id="synthetic",
        report_id="system",
        delivery_date=ACQUIRED_AT.date(),
        window=QueryWindow(start_utc=ACQUIRED_AT, end_utc=ACQUIRED_AT.replace(hour=13)),
        query=SystemQuery(
            area=Area(role=AreaRole.CONTROL_AREA, project_id="test"), series_ids=("load",)
        ),
    )
    return ResolvedSource.for_api(request)


def service(source, handler, clock, *, auth=None, url="https://provider.invalid/data", **kwargs):
    return HttpRetriever(
        lambda _: url,
        retrieval_event_id=UUID(int=1),
        now=lambda: ACQUIRED_AT,
        transport=httpx.MockTransport(handler),
        clock=clock,
        sleeper=clock.sleep,
        request_policy=PrivateRequestPolicy("https://provider.invalid", auth),
        **kwargs,
    )


def response(body=b"synthetic public bytes", status=200, headers=None):
    return httpx.Response(status, stream=httpx.ByteStream(body), headers=headers)


@pytest.mark.parametrize(
    "auth_type,name", [(HeaderAuthentication, "x-api-key"), (QueryAuthentication, "securityToken")]
)
def test_private_injection_and_secret_free_archive(
    api_source, clock, tmp_path, safe_output, auth_type, name
):
    auth = auth_type(SecretStr(SECRET))
    requests = []

    def handler(request):
        requests.append(request)
        assert request.method == "GET" and request.headers["accept-encoding"] == "identity"
        if auth_type is HeaderAuthentication:
            assert request.headers[name] == SECRET and SECRET not in str(request.url)
        else:
            assert request.url.params[name] == SECRET and name not in request.headers
        assert request.extensions["timeout"] == dict.fromkeys(
            ["connect", "read", "write", "pool"], 10.0
        )
        return response(headers={"ETag": '"' + SECRET + '"'})

    retriever = service(api_source, handler, clock, auth=auth)
    result = persist_retrieval(retriever.retrieve(api_source), LocalRawArchive(tmp_path))
    assert result.payload.content == b"synthetic public bytes"
    assert result.provenance.contract_version == "2.0.0" and result.provenance.http is None
    assert len(requests) == 1 and clock.sleeps == []
    assert SECRET not in result.model_dump_json() + repr(auth) + repr(retriever.request_policy)
    for path in tmp_path.rglob("*.json"):
        assert SECRET not in path.read_text() and quote(SECRET, safe="") not in path.read_text()
    assert SECRET not in safe_output.getvalue() and "securityToken=" not in safe_output.getvalue()


@pytest.mark.parametrize("form", [SECRET, quote(SECRET, safe=""), json.dumps(SECRET)[1:-1]])
@pytest.mark.parametrize("auth_type", [HeaderAuthentication, QueryAuthentication])
def test_response_echo_rejected_before_payload_or_archive(
    api_source, clock, tmp_path, safe_output, form, auth_type
):
    calls = []

    def handler(_):
        calls.append(1)
        return response(b"provider echoed: " + form.encode())

    result = service(api_source, handler, clock, auth=auth_type(SecretStr(SECRET))).retrieve(
        api_source
    )
    result = persist_retrieval(result, LocalRawArchive(tmp_path))
    assert result.provenance.outcome is RetrievalOutcome.PERMANENT_FAILURE
    assert result.provenance.error_code is ErrorCode.SENSITIVE_RESPONSE
    assert result.provenance.http_status == 200 and result.provenance.attempt_count == 1
    assert result.payload is result.provenance.raw is result.provenance.archive is None
    assert not list(tmp_path.rglob("*")) and calls == [1] and not clock.sleeps
    assert SECRET not in result.model_dump_json() + safe_output.getvalue()


@pytest.mark.parametrize("status", [400, 401, 403, 429, 503])
def test_error_response_echo_is_never_archived_or_logged(
    api_source, clock, tmp_path, safe_output, status
):
    result = service(
        api_source,
        lambda _: response(SECRET.encode(), status),
        clock,
        auth=QueryAuthentication(SecretStr(SECRET)),
    ).retrieve(api_source)
    persist_retrieval(result, LocalRawArchive(tmp_path))
    assert result.payload is None and not list(tmp_path.rglob("*"))
    assert SECRET not in result.model_dump_json() + safe_output.getvalue()
    if status in (401, 403):
        expected = (
            ErrorCode.AUTHENTICATION_FAILURE if status == 401 else ErrorCode.AUTHORIZATION_FAILURE
        )
        assert result.provenance.error_code is expected and not clock.sleeps
        assert result.provenance.attempt_count == 1
    if status in (429, 503):
        assert result.provenance.attempt_count == 3 and clock.sleeps == [1.0, 2.0]


@pytest.mark.parametrize(
    "url",
    [
        "http://provider.invalid/data",
        "https://other.invalid/data",
        "https://provider.invalid:444/data",
        "https://user:password@provider.invalid/data",
        "https://provider.invalid/data#fragment",
        "https://provider.invalid/data?securityToken=bad",
        "https://provider.invalid/data?TOKEN=bad",
    ],
)
def test_fixed_origin_and_duplicate_auth_rejected_before_io(api_source, clock, safe_output, url):
    calls = []
    retriever = service(
        api_source,
        lambda _: calls.append(1),
        clock,
        auth=QueryAuthentication(SecretStr(SECRET)),
        url=url,
    )
    with pytest.raises(ExecutionError) as caught:
        retriever.retrieve(api_source)
    assert not calls and not clock.sleeps
    logging.getLogger(__name__).exception("ingestion_failed", exc_info=caught.value)
    assert SECRET not in str(caught.value) + repr(caught.value) + safe_output.getvalue()


@pytest.mark.parametrize(
    "origin",
    [
        "http://provider.invalid",
        "https://provider.invalid/path",
        "https://provider.invalid?token=" + SECRET,
        "https://user:" + SECRET + "@provider.invalid",
    ],
)
def test_invalid_origin_uses_safe_exception(origin):
    with pytest.raises(ExecutionError) as caught:
        PrivateRequestPolicy(origin)
    assert SECRET not in str(caught.value) + repr(caught.value)


def test_api_requires_explicit_origin_and_default_transport_still_denied(api_source, monkeypatch):
    with pytest.raises(ExecutionError):
        HttpRetriever(
            lambda _: "https://provider.invalid/data", retrieval_event_id=UUID(int=1)
        ).retrieve(api_source)
    # Exercise the actual default construction; no provider/DNS operation can occur.
    with pytest.raises(AssertionError, match="Default pytest forbids network access"):
        HttpRetriever(
            lambda _: "https://provider.invalid/data",
            retrieval_event_id=UUID(int=1),
            request_policy=PrivateRequestPolicy(
                "https://provider.invalid", QueryAuthentication(SecretStr(SECRET))
            ),
        ).retrieve(api_source)


@pytest.mark.parametrize("encoding", ["gzip", "br", "unknown"])
def test_authenticated_encoding_is_not_published_without_echo_inspection(
    api_source, clock, tmp_path, encoding
):
    content = gzip.compress(SECRET.encode())
    with pytest.raises(ExecutionError) as caught:
        service(
            api_source,
            lambda _: response(content, headers={"Content-Encoding": encoding}),
            clock,
            auth=HeaderAuthentication(SecretStr(SECRET)),
        ).retrieve(api_source)
    assert caught.value.code is ErrorCode.UNSUPPORTED_ENCODING
    assert not list(tmp_path.rglob("*")) and not clock.sleeps


def test_private_transport_exception_is_secret_safe(api_source, clock, safe_output):
    def handler(_):
        raise httpx.ReadTimeout("private url securityToken=" + SECRET)

    result = service(
        api_source, handler, clock, auth=QueryAuthentication(SecretStr(SECRET))
    ).retrieve(api_source)
    assert (
        result.provenance.attempt_count == 3 and result.provenance.error_code is ErrorCode.TIMEOUT
    )
    assert SECRET not in result.model_dump_json() + safe_output.getvalue()
    logging.getLogger(__name__).exception("ingestion_failed", exc_info=ValueError(SECRET))
    assert SECRET not in safe_output.getvalue()


@pytest.mark.parametrize(
    "source_id,environment_key,auth_type",
    [
        ("esios", "ESIOS_API_TOKEN", HeaderAuthentication),
        ("entsoe", "ENTSOE_API_TOKEN", QueryAuthentication),
    ],
)
def test_selected_environment_only_no_dotenv(
    source_id, environment_key, auth_type, tmp_path, monkeypatch
):
    class SelectedOnly(Mapping):
        def __getitem__(self, key):
            assert key == environment_key
            return SECRET

        def __iter__(self):
            pytest.fail("Do not enumerate environment")

        def __len__(self):
            pytest.fail("Do not inspect unrelated settings")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(environment_key + "=" + SECRET)
    with pytest.raises(ConfigurationError):
        load_provider_auth(source_id, {})
    assert isinstance(load_provider_auth(source_id, SelectedOnly()), auth_type)
    monkeypatch.setenv(environment_key, SECRET)
    assert isinstance(load_provider_auth(source_id), auth_type)


@pytest.mark.parametrize("source_id", ["omie", "ren", "open_meteo", "weather", "synthetic"])
def test_anonymous_paths_require_no_secrets_or_environment_read(source_id):
    class NoRead(dict):
        def get(self, *args):
            pytest.fail("Anonymous source read credential environment")

    assert load_provider_auth(source_id, NoRead()) is None


@pytest.mark.parametrize(
    "value", ["", "short", "x" * 4097, SECRET + "\n", SECRET + "\x00", SECRET + "é", None, 123]
)
@pytest.mark.parametrize("source_id", ["esios", "entsoe"])
def test_invalid_config_and_validation_are_secret_safe(source_id, value, safe_output):
    key = "ESIOS_API_TOKEN" if source_id == "esios" else "ENTSOE_API_TOKEN"
    with pytest.raises(ConfigurationError) as caught:
        load_provider_auth(source_id, {key: value})
    assert SECRET not in str(caught.value) + repr(caught.value)
    logging.getLogger(__name__).exception("ingestion_failed", exc_info=caught.value)
    assert SECRET not in safe_output.getvalue()


def test_secret_settings_are_excluded_frozen_and_validation_safe(safe_output):
    settings = ProviderSecretSettings(token=SecretStr(SECRET))
    assert settings.model_dump() == {} and settings.model_dump_json() == "{}"
    assert SECRET not in repr(settings)
    with pytest.raises(ValidationError):
        settings.token = SecretStr("different-synthetic-secret")
    with pytest.raises(ValidationError) as caught:
        ProviderSecretSettings(token=SecretStr(SECRET + "\n"))
    assert SECRET not in str(caught.value) + repr(caught.value)
    logging.getLogger(__name__).exception("ingestion_failed", exc_info=caught.value)
    assert SECRET not in safe_output.getvalue()


def test_active_secret_cannot_be_smuggled_in_safe_series_identity(api_source, clock):
    # Even a syntactically legal native identifier cannot carry the active credential.
    secret = "synthetic-alphanumeric-credential"
    request = ApiSourceRequest.model_validate(
        {
            **api_source.request.model_dump(),
            "query": SystemQuery(area=api_source.request.query.area, series_ids=(secret,)),
        }
    )
    source = ResolvedSource.for_api(request)
    calls = []
    with pytest.raises(ExecutionError) as caught:
        service(
            source, lambda _: calls.append(1), clock, auth=HeaderAuthentication(SecretStr(secret))
        ).retrieve(source)
    assert caught.value.code is ErrorCode.INVALID_LOCATOR and calls == []
    assert secret not in str(caught.value) + repr(caught.value)


def test_private_material_repr_is_opaque():
    policy = PrivateRequestPolicy(
        "https://provider.invalid", QueryAuthentication(SecretStr(SECRET))
    )
    private = policy.prepare(httpx.URL("https://provider.invalid/data"))
    assert SECRET not in repr(private)
    assert "securityToken" not in repr(private) and "headers" not in repr(private)
