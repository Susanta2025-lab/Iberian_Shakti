"""Final offline audit regressions over the accepted provider components."""

import io
import json
import logging
from dataclasses import dataclass, field
from http.client import HTTPSConnection
from urllib.request import ProxyHandler, build_opener
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from stage6.support import PARSED_AT, TOKENS, cases_for, deny_reacquisition, execute

from iberian_shakti.common.logging import configure_logging
from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome, RetrievalOutcome
from iberian_shakti.ingestion._http_transport import deadline_context
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.auth import PrivateRequestPolicy, QueryAuthentication
from iberian_shakti.ingestion.errors import ExecutionError, ReplayError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.omie.identity import download_url
from iberian_shakti.ingestion.omie.parser import OmieParser
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import DEFAULT_MAX_BYTES, result_for
from iberian_shakti.ingestion.retry import RetryPolicy

CASES = cases_for()
KEYS = tuple(case.key for case in CASES)


def retriever_for(case, **kwargs):
    if case.adapter is None:
        return HttpRetriever(download_url, **kwargs)
    if case.source.request.source_id in {"esios", "entsoe"}:
        kwargs["environ"] = TOKENS
    return case.adapter.retriever(**kwargs)


@pytest.fixture
def managed_output():
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


def encoded_echo(secret, form):
    if form == "percent-all":
        return "".join(f"%{ord(char):02x}" for char in secret)
    if form == "percent-mixed":
        return "".join(f"%{ord(char):02X}" if i % 2 else char for i, char in enumerate(secret))
    if form == "json-unicode":
        return "".join(f"\\u{ord(char):04x}" for char in secret)
    if form == "json-mixed":
        return "".join(f"\\u{ord(char):04X}" if i % 2 else char for i, char in enumerate(secret))
    raise AssertionError("Unknown synthetic encoding")


@pytest.mark.parametrize("key", ["esios", "entsoe_load"])
@pytest.mark.parametrize("form", ["percent-all", "percent-mixed", "json-unicode", "json-mixed"])
def test_encoded_active_credentials_cannot_publish(key, form, tmp_path, managed_output):
    case = next(case for case in cases_for() if case.key == key)
    token_key = "ESIOS_API_TOKEN" if key == "esios" else "ENTSOE_API_TOKEN"
    secret = TOKENS[token_key]
    echo = encoded_echo(secret, form)
    # A JSON presentation field or an XML comment is sufficient to leak a
    # reversible secret into an otherwise normal raw archive. No parser runs.
    body = json.dumps({"description": "placeholder"}).replace("placeholder", echo).encode()
    if key == "entsoe_load":
        body = f"<!-- {echo} -->".encode() + case.body
    archive = LocalRawArchive(tmp_path)
    result = execute(archive, case, 701, body=body)
    assert result.retrieval.outcome is RetrievalOutcome.PERMANENT_FAILURE
    assert result.retrieval.error_code is ErrorCode.SENSITIVE_RESPONSE
    assert result.retrieval.raw is result.retrieval.archive is result.parse is None
    assert list(tmp_path.iterdir()) == []
    diagnostics = result.model_dump_json() + managed_output.getvalue()
    assert secret not in diagnostics and echo not in diagnostics


def test_omie_replay_body_cap_precedes_text_parsing(monkeypatch):
    case = cases_for()[0]
    acquired = result_for(
        case.source, UUID(int=701), case.completed_at, content=b"x" * (DEFAULT_MAX_BYTES + 1)
    )

    def forbidden(*args):
        pytest.fail("Oversized replay bytes reached OMIE text parsing")

    monkeypatch.setattr(OmieParser, "_records", forbidden)
    parsed = case.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=PARSED_AT, parse_event_id=UUID(int=702)
    )
    assert parsed.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert parsed.provenance.error_code is ErrorCode.CONTENT_INVALID
    assert parsed.records == ()


@pytest.mark.parametrize("key", KEYS)
def test_every_default_provider_transport_is_network_denied(key):
    case = next(case for case in CASES if case.key == key)
    retriever = retriever_for(case, retrieval_event_id=UUID(int=701), now=lambda: case.completed_at)
    with pytest.raises(AssertionError, match="Default pytest forbids network access"):
        retriever.retrieve(case.source)


@pytest.mark.parametrize("path", ["urllib", "http.client", "httpx-convenience"])
def test_alternate_python_http_paths_remain_denied(path):
    # Loopback literals never require provider or DNS observations. The guard
    # raises before any connection, including alternate library constructors.
    with pytest.raises(AssertionError, match="Default pytest forbids network access"):
        if path == "urllib":
            build_opener(ProxyHandler({})).open("https://127.0.0.1:1", timeout=1)
        elif path == "http.client":
            connection = HTTPSConnection("127.0.0.1", port=1, timeout=1)
            try:
                connection.request("GET", "/")
            finally:
                connection.close()
        else:
            httpx.get("https://127.0.0.1:1", timeout=1, trust_env=False)


@pytest.mark.parametrize("key", ["esios", "entsoe_load"])
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_private_redirects_cannot_forward_credentials(key, status, tmp_path, managed_output):
    case = next(case for case in CASES if case.key == key)
    calls = []

    class ForbiddenBody(httpx.SyncByteStream):
        def __iter__(self):
            pytest.fail("Redirect body was consumed")

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            headers={"Location": "https://attacker.invalid/collect"},
            stream=ForbiddenBody(),
        )

    acquired = retriever_for(
        case,
        retrieval_event_id=UUID(int=701),
        transport=httpx.MockTransport(handler),
        now=lambda: case.completed_at,
    ).retrieve(case.source)
    assert len(calls) == 1 and calls[0].url.host != "attacker.invalid"
    assert acquired.payload is None and acquired.provenance.error_code is ErrorCode.HTTP_FAILURE
    assert not list(tmp_path.iterdir())
    diagnostics = acquired.model_dump_json() + managed_output.getvalue()
    assert "attacker.invalid" not in diagnostics
    assert all(token not in diagnostics for token in TOKENS.values())


@pytest.mark.parametrize("key", ["esios", "entsoe_load"])
@pytest.mark.parametrize("escape", ["host", "port", "scheme", "userinfo", "fragment", "query"])
def test_private_policy_refuses_origin_or_credential_injection(key, escape):
    case = next(case for case in CASES if case.key == key)
    retriever = retriever_for(case, retrieval_event_id=UUID(int=701))
    url = httpx.URL(retriever.resolve_url(case.source))
    altered = {
        "host": lambda: url.copy_with(host="attacker.invalid"),
        "port": lambda: url.copy_with(port=444),
        "scheme": lambda: url.copy_with(scheme="http"),
        "userinfo": lambda: url.copy_with(username="attacker"),
        "fragment": lambda: url.copy_with(fragment="unsafe"),
        "query": lambda: url.copy_add_param("securityToken", "preinjected"),
    }[escape]()
    with pytest.raises(ExecutionError) as caught:
        retriever.request_policy.prepare(altered)
    assert caught.value.code is ErrorCode.INVALID_LOCATOR
    assert caught.value.__cause__ is None
    assert all(token not in repr(caught.value) for token in TOKENS.values())


@dataclass
class AuditClock:
    elapsed: float = 0.0
    sleeps: list[float] = field(default_factory=list)

    def __call__(self):
        return self.elapsed

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.elapsed += seconds


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize(
    "scenario", ["timeout-every", "body-timeout", "final-transport", "retry-after", "short-budget"]
)
def test_composed_retry_budget_on_every_provider(key, scenario):
    case = next(case for case in CASES if case.key == key)
    clock = AuditClock()
    calls = []
    streams = []

    class TimedBody(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield b"partial"
            deadline, _ = deadline_context.get()
            clock.elapsed = deadline
            raise httpx.ReadTimeout("synthetic private transport detail")

        def close(self):
            self.closed = True

    def handler(request):
        deadline, active_clock = deadline_context.get()
        assert active_clock is clock
        calls.append(clock.elapsed)
        remaining = deadline - clock.elapsed
        assert remaining > 0
        assert all(0 < t <= min(10, remaining) for t in request.extensions["timeout"].values())
        if scenario == "body-timeout":
            stream = TimedBody()
            streams.append(stream)
            return httpx.Response(200, stream=stream)
        clock.elapsed = deadline
        if scenario == "retry-after" and len(calls) == 1:
            # Headers arrive just before the attempt expires; a response at
            # the deadline is correctly a budget failure before status policy.
            clock.elapsed -= 1
            return httpx.Response(429, headers={"Retry-After": "63"}, stream=httpx.ByteStream(b""))
        if scenario == "final-transport":
            if len(calls) < 3:
                return httpx.Response(503, stream=httpx.ByteStream(b""))
            raise httpx.ConnectError("synthetic final-attempt failure")
        raise httpx.ReadTimeout("synthetic timeout")

    retriever = retriever_for(
        case,
        retrieval_event_id=UUID(int=701),
        transport=httpx.MockTransport(handler),
        now=lambda: case.completed_at,
    )
    retriever.clock = clock
    retriever.sleeper = clock.sleep
    retriever.policy = RetryPolicy(
        operation_timeout_seconds=35 if scenario == "short-budget" else 93
    )
    result = retriever.retrieve(case.source)
    if scenario == "retry-after":
        terminal = key.startswith("entsoe")
        assert calls == ([0] if terminal else [0, 92])
        assert clock.sleeps == ([] if terminal else [63])
        assert clock.elapsed == (29 if terminal else 93)
    elif scenario == "short-budget":
        assert calls == [0, 31] and clock.sleeps == [1] and clock.elapsed == 35
    else:
        assert calls == [0, 31, 63] and clock.sleeps == [1, 2] and clock.elapsed == 93
    assert clock.elapsed <= retriever.policy.operation_timeout_seconds
    assert result.provenance.attempt_count == len(calls) and result.payload is None
    assert all(stream.closed for stream in streams)


@pytest.mark.parametrize("key", KEYS)
def test_late_parser_failure_is_atomic_and_never_retried(key, tmp_path):
    case = next(case for case in CASES if case.key == key)
    if key == "omie":
        lines = case.body.splitlines()
        lines[-2] += b"late-invalid-field;"
        body = b"\n".join(lines)
    elif key == "ren":
        data = json.loads(case.body)
        data["series"][-1]["data"][-1] = None
        body = json.dumps(data).encode()
    elif key == "esios":
        data = json.loads(case.body)
        data["indicator"]["values"][-1]["value"] = True
        body = json.dumps(data).encode()
    elif key.startswith("entsoe"):
        start = case.body.rindex(b"<quantity>") + len(b"<quantity>")
        end = case.body.index(b"</quantity>", start)
        body = case.body[:start] + b"NaN" + case.body[end:]
    else:
        data = json.loads(case.body)
        data["hourly"]["shortwave_radiation"][-1] = 2001
        body = json.dumps(data).encode()
    result = execute(LocalRawArchive(tmp_path), case, 701, body=body)
    assert result.retrieval.attempt_count == 1
    assert result.parse.records == () and result.parse.provenance.record_count == 0
    assert result.parse.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert (tmp_path / result.retrieval.archive.relative_path).read_bytes() == body


@pytest.mark.parametrize("reference", [b"&#55296;", b"&#xDFFF;", b"&#1114112;"])
def test_invalid_xml_character_reference_stays_inert(reference):
    policy = PrivateRequestPolicy(
        "https://provider.invalid",
        QueryAuthentication(SecretStr("synthetic-stage7-only")),
        xml_character_references=True,
    )
    assert not policy.contains_credential(reference)


@pytest.mark.parametrize("key", ["esios", "entsoe_load"])
@pytest.mark.parametrize("form", ["percent-all", "percent-mixed", "json-unicode", "json-mixed"])
def test_encoded_header_echo_cannot_enter_provenance(key, form, tmp_path, managed_output):
    case = next(case for case in CASES if case.key == key)
    secret = TOKENS["ESIOS_API_TOKEN" if key == "esios" else "ENTSOE_API_TOKEN"]
    echo = encoded_echo(secret, form)

    def handler(_):
        return httpx.Response(
            200, headers={"ETag": f'"{echo}"'}, stream=httpx.ByteStream(case.body)
        )

    retriever = retriever_for(
        case,
        retrieval_event_id=UUID(int=701),
        transport=httpx.MockTransport(handler),
        now=lambda: case.completed_at,
    )
    acquired = retriever.retrieve(case.source)
    assert acquired.payload.content == case.body and acquired.provenance.http is None
    archive = LocalRawArchive(tmp_path)
    archive.persist(acquired.payload, acquired.provenance)
    diagnostics = acquired.model_dump_json() + managed_output.getvalue()
    diagnostics += "".join(path.read_text() for path in tmp_path.rglob("*.json"))
    assert secret not in diagnostics and echo not in diagnostics


@pytest.mark.parametrize("key", [key for key in KEYS if key != "omie"])
@pytest.mark.parametrize("field", ["query", "profile"])
def test_replay_rejects_changed_query_or_profile_linkage(key, field, tmp_path, monkeypatch):
    case = next(case for case in CASES if case.key == key)
    archive = LocalRawArchive(tmp_path)
    result = execute(archive, case, 701)
    reference = result.retrieval.archive
    event = (
        (tmp_path / reference.relative_path).parent
        / "retrievals"
        / f"{result.retrieval.retrieval_event_id}.json"
    )
    data = json.loads(event.read_bytes())
    request = data["source"]["request"]
    if field == "profile":
        request["report_id"] = "unsupported.v9.0.0"
    elif request["query"]["kind"] == "system":
        request["query"]["series_ids"] = ["wrong_series"]
    else:
        request["query"]["site"]["selection_version"] = "9.0.0"
    event.chmod(0o600)
    event.write_text(json.dumps(data))
    deny_reacquisition(monkeypatch)
    with pytest.raises(ReplayError) as caught:
        replay(archive, reference, result.retrieval.retrieval_event_id)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE
    assert event.read_text() == json.dumps(data)  # No repair or history rewrite.
