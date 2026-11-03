"""Synthetic-only tests of the explicit Stage 8 command and its real components."""

import argparse
import hashlib
import json
import os
import signal
import socket
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpcore
import httpx
import pytest
from pydantic import ValidationError
from stage6.support import TOKENS, cases_for

from iberian_shakti.ingestion import config
from iberian_shakti.ingestion import phase2_live as live
from iberian_shakti.ingestion._live_budget import (
    Budget,
    CountedTransport,
    Limits,
    RunBackend,
    RunStop,
    RunStream,
    hard_deadline,
)
from iberian_shakti.ingestion.auth import PrivateRequestPolicy
from iberian_shakti.ingestion.config import ConfigurationError, load_provider_auth
from iberian_shakti.ingestion.http import HttpRetriever

AT = datetime(2026, 11, 3, 12, tzinfo=UTC)


class Clock:
    def __init__(self):
        self.value = 0.0
        self.waits = []

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.value += seconds


@pytest.fixture
def fake_clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(live, "Budget", lambda: Budget(clock=clock, sleeper=clock.sleep))
    return clock


def args(root, *, enabled=True, replay=False):
    return argparse.Namespace(live=enabled, replay_only=replay, archive_root=root)


def forbidden(*args, **kwargs):
    raise AssertionError("Unexpected network/client/credential construction")


def bodies():
    result = {case.key: case.body for case in cases_for(date(2026, 10, 24)) if case.key != "omie"}
    result["era5"] = result.pop("era5:PT.lisbon")
    weather = json.loads(result.pop("icon_eu:PT.lisbon"))
    start = int(datetime(2026, 11, 4, tzinfo=UTC).timestamp())
    weather["hourly"]["time"] = [start + 3600 * i for i in range(24)]
    result["icon_eu"] = json.dumps(weather).encode()
    return result


def factory_for(*, statuses=None, mutations=None, calls=None):
    content = bodies()
    if mutations:
        content.update(mutations)
    selections = live.plan(AT)
    index = 0

    def factory(budget):
        nonlocal index
        key = selections[index].key
        index += 1
        attempts = iter((statuses or {}).get(key, [200]))

        def handler(request):
            status = next(attempts)
            if calls is not None:
                calls.append((key, status, budget.clock(), request))
            body = content[key] if status == 200 else b"unchecked-error-prose"
            return httpx.Response(
                status, stream=httpx.ByteStream(body), headers={"content-length": str(len(body))}
            )

        return httpx.MockTransport(handler)

    return factory


def load(root):
    return live.Manifest.model_validate_json((root / live.MANIFEST).read_bytes())


def run(root, **kwargs):
    return live.run(args(root), environment=TOKENS, now=lambda: AT, **kwargs)


def test_no_live_is_offline_before_credentials_or_client(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(live, "load_provider_auth", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    monkeypatch.setattr(HttpRetriever, "__init__", forbidden)
    assert live.main(["--archive-root", str(tmp_path / "live")]) == 2
    assert "live_authorization_required" in capsys.readouterr().out
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"ESIOS_API_TOKEN": TOKENS["ESIOS_API_TOKEN"]},
        {"ENTSOE_API_TOKEN": TOKENS["ENTSOE_API_TOKEN"]},
        {**TOKENS, "ENTSOE_API_TOKEN": "bad\nvalue"},
    ],
)
def test_credentials_fail_before_clients(monkeypatch, tmp_path, environment):
    monkeypatch.setattr(httpx, "Client", forbidden)
    assert live.run(args(tmp_path / "live"), environment=environment) == 2
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "path",
    [
        "tests/data/live",
        "fixtures/live",
        "data/raw/live",
        ".",
        "/tmp/fixtures/live",
        "/tmp/default",
    ],
)
def test_fixture_default_and_repository_roots_rejected(path):
    with pytest.raises(ConfigurationError):
        live.archive_root(Path(path).absolute() if path != "." else Path(path))


def test_symlink_and_nonempty_roots_rejected(tmp_path):
    target = tmp_path / "fixtures"
    target.mkdir()
    link = tmp_path / "live"
    link.symlink_to(target)
    with pytest.raises(ConfigurationError):
        live.archive_root(link)
    with pytest.raises(ConfigurationError):
        live.prepare_root(tmp_path)


def test_seven_exact_products_dates_sites_and_models():
    selected = live.plan(AT)
    assert [s.key for s in selected] == [
        "ren",
        "esios",
        "entsoe_load",
        "entsoe_pt",
        "entsoe_es",
        "era5",
        "icon_eu",
    ]
    assert all(s.request.delivery_date == date(2026, 10, 24) for s in selected[:-1])
    assert selected[-1].request.delivery_date == date(2026, 11, 4)
    assert live.plan(AT + timedelta(days=2))[-1].request.delivery_date == date(2026, 11, 6)
    for s in selected[-2:]:
        query = httpx.URL(s.adapter.transport_url(s.source)).params
        assert query["models"] == s.key
        assert query["latitude"] == "38.72" and query["longitude"] == "-9.14"
        assert query["temperature_unit"] == "celsius" and query["wind_speed_unit"] == "ms"
        assert query["timezone"] == "GMT" and query["timeformat"] == "unixtime"
    assert selected[2].request.query.area.native_id == "10YES-REE------0"
    assert selected[3].request.query.area.native_id == "10YPT-REN------W"
    assert selected[4].request.query.area.native_id == "10YES-REE------0"


def test_logical_and_optional_metadata_limits():
    budget = Budget()
    for _ in range(7):
        budget.begin()
    budget.begin(optional=True)
    with pytest.raises(RunStop, match="logical_request_budget"):
        budget.begin()
    separate = Budget()
    separate.begin(optional=True)
    with pytest.raises(RunStop, match="metadata_request_budget"):
        separate.begin(optional=True)
    assert separate.logical == 1 and separate.optional == 1


@pytest.mark.parametrize(
    "limits",
    [
        {"logical": 9},
        {"attempts": 25},
        {"body_bytes": 33554433},
        {"seconds": 901},
        {"seconds": float("nan")},
    ],
)
def test_limits_cannot_be_increased(limits):
    with pytest.raises(ValueError):
        Limits(**limits)


def test_24_attempts_and_three_per_acquisition():
    clock = Clock()
    budget = Budget(clock=clock, sleeper=clock.sleep)
    with pytest.raises(RunStop, match="outside_authorized"):
        budget.attempt()
    for _ in range(8):
        budget.begin()
        for _ in range(3):
            budget.attempt()
        with pytest.raises(RunStop, match="attempt_budget"):
            budget.attempt()
    assert budget.attempts == 24
    assert clock.value >= 23 * 1.1 - 1e-6


class SyntheticStream(httpcore.NetworkStream):
    def __init__(self):
        self.calls = []

    def read(self, max_bytes, timeout=None):
        self.calls.append(max_bytes)
        return b"x" * max_bytes


def test_inbound_cap_limits_read_before_network_operation():
    budget = Budget(limits=Limits(body_bytes=10))
    inner = SyntheticStream()
    stream = RunStream(inner, budget)
    assert len(stream.read(8)) == 8
    assert len(stream.read(8)) == 2
    with pytest.raises(RunStop, match="byte_budget"):
        stream.read(1)
    assert inner.calls == [8, 2] and budget.inbound_bytes == 10
    budget.begin()
    with pytest.raises(RunStop, match="byte_budget"):
        budget.attempt()
    assert budget.attempts == 0


def test_body_counter_counts_failed_attempts_and_stops_before_overrun():
    budget = Budget(limits=Limits(body_bytes=10))
    budget.body(6)
    budget.body(4)
    with pytest.raises(RunStop, match="byte_budget"):
        budget.body(1)
    assert budget.body_bytes == 10


def test_wall_clock_and_wait_admission():
    clock = Clock()
    budget = Budget(clock=clock, sleeper=clock.sleep)
    with pytest.raises(RunStop, match="wall_clock"):
        budget.wait(900)
    clock.value = 900
    with pytest.raises(RunStop, match="wall_clock"):
        budget.begin()
    assert budget.logical == budget.attempts == 0 and not clock.waits


def test_host_deadline_interrupts_blocked_local_work():
    previous = signal.getsignal(signal.SIGALRM)
    with pytest.raises(RunStop, match="wall_clock"):
        with hard_deadline(Budget(limits=Limits(seconds=0.02))):
            time.sleep(0.2)
    assert signal.getsignal(signal.SIGALRM) == previous
    assert signal.getitimer(signal.ITIMER_REAL) == (0, 0)


def test_all_production_paths_sequential_accounted_and_replayed(tmp_path, fake_clock, capsys):
    root = tmp_path / "live"
    calls = []
    assert run(root, transport_factory=factory_for(calls=calls)) == 0
    manifest = load(root)
    assert manifest.logical_successful == 7
    assert manifest.accounting["logical_requests"] == manifest.accounting["http_attempts"] == 7
    assert manifest.accounting["optional_metadata_requests"] == 0
    assert [c[0] for c in calls] == [s.key for s in live.plan(AT)]
    assert all(b[2] - a[2] >= 1.1 - 1e-6 for a, b in zip(calls, calls[1:], strict=False))
    assert all(
        e.replay == "equal" and e.replay_parse_uuid != e.parse_uuid for e in manifest.entries
    )
    assert [e.record_count for e in manifest.entries] == [1056, 3, 3, 8, 12, 72, 72]
    assert manifest.accounting["attempted_body_bytes"] == manifest.archived_bytes
    assert manifest.archived_bytes == sum(len(b) for b in bodies().values())
    evidence = "".join(p.read_text() for p in root.rglob("*.json")) + capsys.readouterr().out
    for secret in TOKENS.values():
        assert secret not in evidence
    assert "securityToken" not in evidence and "x-api-key" not in evidence
    assert not list(root.rglob(".preflight*"))


def test_error_bodies_and_retries_count_and_auth_failure_does_not_retry(tmp_path, fake_clock):
    calls = []
    root = tmp_path / "live"
    assert (
        run(
            root,
            transport_factory=factory_for(
                statuses={"ren": [500, 503, 200], "esios": [401]}, calls=calls
            ),
        )
        == 3
    )
    manifest = load(root)
    assert manifest.accounting["http_attempts"] == 9
    assert manifest.entries[0].attempts == 3 and manifest.entries[1].attempts == 1
    assert manifest.entries[1].error_code.value == "authentication_failure"
    assert manifest.entries[-1].outcome == "success"
    assert manifest.accounting["attempted_body_bytes"] == manifest.archived_bytes + 3 * len(
        b"unchecked-error-prose"
    )
    assert manifest.retries_by_provider["ren"] == 2
    assert len(list(root.rglob("payload.bin"))) == 6


def test_entsoe_429_is_terminal_and_other_planned_domains_continue(tmp_path, fake_clock):
    root = tmp_path / "live"
    assert run(root, transport_factory=factory_for(statuses={"entsoe_load": [429]})) == 3
    manifest = load(root)
    assert manifest.entries[2].attempts == 1
    assert manifest.entries[2].error_code.value == "rate_limited"
    assert manifest.entries[3].outcome == manifest.entries[4].outcome == "success"
    assert manifest.accounting["http_attempts"] == 7


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_redirect_stops_all_further_network(tmp_path, fake_clock, status):
    root = tmp_path / "live"
    assert run(root, transport_factory=factory_for(statuses={"ren": [status]})) == 3
    manifest = load(root)
    assert manifest.stop_category == "unsafe_redirect"
    assert manifest.accounting["logical_requests"] == manifest.accounting["http_attempts"] == 1
    assert all(e.outcome == "not_executed" for e in manifest.entries[1:])


def test_credential_echo_stops_run_without_raw_publication(tmp_path, fake_clock):
    root = tmp_path / "live"
    assert (
        run(
            root,
            transport_factory=factory_for(mutations={"esios": TOKENS["ESIOS_API_TOKEN"].encode()}),
        )
        == 3
    )
    manifest = load(root)
    assert manifest.stop_category == "sensitive_response"
    assert manifest.entries[1].archive is None
    assert manifest.accounting["http_attempts"] == 2
    assert len(list(root.rglob("payload.bin"))) == 1


def test_failed_semantic_parse_is_retained_and_replayed(tmp_path, fake_clock):
    root = tmp_path / "live"
    assert run(root, transport_factory=factory_for(mutations={"ren": b"{bad json}"})) == 3
    manifest = load(root)
    assert manifest.entries[0].outcome == "parse_failure"
    assert manifest.entries[0].archive is not None and manifest.entries[0].replay == "equal"
    assert manifest.logical_successful == 6
    assert manifest.accounting["http_attempts"] == 7


def test_manifest_closed_schema_and_secret_exclusion(tmp_path):
    manifest = live.Manifest(
        run_id=uuid4(), started_utc=AT, icon_target=date(2026, 11, 4), entries=[]
    )
    guard = PrivateRequestPolicy(
        "https://localhost", load_provider_auth("esios", {"ESIOS_API_TOKEN": str(manifest.run_id)})
    )
    with pytest.raises(RunStop, match="sensitive_response"):
        live.save_manifest(tmp_path, manifest, [guard])
    assert not list(tmp_path.iterdir())
    with pytest.raises(ValidationError):
        live.Manifest.model_validate({**manifest.model_dump(), "private_headers": "untrusted"})
    with pytest.raises(ValidationError):
        live.Manifest.model_validate(
            {**manifest.model_dump(), "stop_category": "unchecked provider prose"}
        )


def test_replay_denials_are_enforced():
    operations = [
        lambda: httpx.Client(),
        lambda: HttpRetriever(None, retrieval_event_id=uuid4()),
        lambda: config.load_provider_auth("esios"),
        lambda: config.load_provider_auth("entsoe"),
        lambda: socket.socket(),
        lambda: socket.getaddrinfo("localhost", 443),
        lambda: live.EsiosAdapter().retriever(retrieval_event_id=uuid4()),
        lambda: live.EntsoeAdapter().retriever(retrieval_event_id=uuid4()),
    ]
    with live.network_denied():
        assert not os.environ
        for operation in operations:
            with pytest.raises(RunStop, match="Replay attempted"):
                operation()


def test_replay_only_loads_no_credentials_or_clients_and_preserves_history(
    tmp_path, fake_clock, monkeypatch
):
    root = tmp_path / "live"
    assert run(root, transport_factory=factory_for()) == 0
    before = {
        p: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file() and p.name != live.MANIFEST
    }
    monkeypatch.setattr(live, "load_provider_auth", forbidden)
    monkeypatch.setattr(httpx, "Client", forbidden)
    assert live.run(args(root, enabled=False, replay=True), environment={}) == 0
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in before.items())
    assert len(list(root.rglob("payload.bin"))) == 7
    assert len(list(root.rglob("parses/*.json"))) == 21


def test_corrupt_real_path_fails_replay_without_refetch(tmp_path, fake_clock):
    root = tmp_path / "live"
    assert run(root, transport_factory=factory_for()) == 0
    manifest = load(root)
    payload = root / manifest.entries[0].archive.relative_path
    payload.chmod(0o600)
    payload.write_bytes(b"corrupt synthetic bytes")
    assert live.run(args(root, enabled=False, replay=True), environment={}) == 3
    assert load(root).entries[0].replay == "failed"


def test_transport_refuses_unplanned_url_before_attempt():
    budget = Budget()
    budget.begin()
    counted = CountedTransport(
        httpx.MockTransport(forbidden), budget, "https://example.test/selected", 100
    )
    with pytest.raises(RunStop, match="outside_authorized"):
        counted.handle_request(httpx.Request("GET", "https://example.test/other"))
    assert budget.attempts == 0


@pytest.mark.parametrize("limit", ["logical", "attempts", "bytes", "time"])
def test_exhaustion_preserves_evidence_and_stops_before_next_call(
    tmp_path, monkeypatch, fake_clock, limit
):
    root = tmp_path / "live"
    limits = {
        "logical": Limits(logical=1),
        "attempts": Limits(attempts=1),
        "bytes": Limits(body_bytes=len(bodies()["ren"])),
        "time": Limits(seconds=1.0),
    }[limit]
    monkeypatch.setattr(
        live, "Budget", lambda: Budget(limits=limits, clock=fake_clock, sleeper=fake_clock.sleep)
    )
    calls = []
    assert run(root, transport_factory=factory_for(calls=calls)) == 3
    manifest = load(root)
    assert len(calls) == 1 and manifest.entries[0].archive is not None
    assert manifest.entries[0].record_count == 1056
    assert manifest.stop_category is not None
    assert manifest.accounting["http_attempts"] == 1
    assert all(e.outcome == "not_executed" for e in manifest.entries[2:])


def test_partial_failed_stream_bytes_count_across_production_retries(tmp_path, fake_clock):
    root = tmp_path / "live"
    original = factory_for()
    first = True

    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield b"incomplete-body"
            raise httpx.ReadError("synthetic unchecked diagnostic")

    def factory(budget):
        nonlocal first
        if not first:
            return original(budget)
        first = False
        # Advance the same exact seven-selection factory without a request.
        original(budget)
        count = 0

        def handler(request):
            nonlocal count
            count += 1
            return httpx.Response(
                200, stream=Interrupted() if count == 1 else httpx.ByteStream(bodies()["ren"])
            )

        return httpx.MockTransport(handler)

    assert run(root, transport_factory=factory) == 0
    manifest = load(root)
    assert manifest.accounting["http_attempts"] == 8
    assert manifest.accounting["attempted_body_bytes"] == manifest.archived_bytes + len(
        b"incomplete-body"
    )
    assert manifest.entries[0].attempts == 2


def test_actual_transport_backend_counts_failed_wire_reads_and_bodies():
    clock = Clock()
    budget = Budget(clock=clock, sleeper=clock.sleep)
    budget.begin()
    wire = b"HTTP/1.1 500 Error\r\nContent-Length: 5\r\nConnection: close\r\n\r\nerror"
    selection = live.plan(AT)[0]
    inner = live.DeadlineTransport(backend=RunBackend(budget, httpcore.MockBackend([wire])))
    counted = CountedTransport(
        inner, budget, selection.adapter.transport_url(selection.source), 1024
    )
    retriever = selection.adapter.retriever(
        retrieval_event_id=uuid4(), transport=counted, now=lambda: AT, sleeper=budget.wait
    )
    retriever.clock = clock
    result = retriever.retrieve(selection.source)
    assert result.payload is None and result.provenance.attempt_count == 3
    assert budget.body_bytes == 15 and budget.inbound_bytes == 3 * len(wire)
    assert counted.statuses == [500, 500, 500]


@pytest.mark.parametrize("product,status", [("esios", 401), ("esios", 403), ("entsoe_load", 429)])
def test_error_body_read_failure_cannot_change_terminal_status(product, status):
    clock = Clock()
    budget = Budget(clock=clock, sleeper=clock.sleep)
    budget.begin()
    selection = next(s for s in live.plan(AT) if s.key == product)

    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield b"failed error body prefix"
            raise httpx.ReadTimeout("synthetic unchecked diagnostic")

    counted = CountedTransport(
        httpx.MockTransport(lambda _: httpx.Response(status, stream=Interrupted())),
        budget,
        selection.adapter.transport_url(selection.source),
        1024,
    )
    retriever = selection.adapter.retriever(
        retrieval_event_id=uuid4(),
        environ=TOKENS,
        transport=counted,
        now=lambda: AT,
        sleeper=budget.wait,
    )
    retriever.clock = clock
    result = retriever.retrieve(selection.source)
    assert result.provenance.http_status == status
    assert result.provenance.attempt_count == budget.attempts == 1
    assert counted.error_body_read_failures == 1
    assert budget.body_bytes == len(b"failed error body prefix")


def test_esios_301_samples_overrun_the_utc_day_fail_atomically_and_replay(tmp_path, fake_clock):
    # Generated synthetic content, never copied live bytes/native IDs/values.
    document = json.loads(bodies()["esios"])
    indicator = document["indicator"]
    template = indicator["values"][0]
    start = datetime(2026, 10, 24, tzinfo=UTC)
    indicator["values"] = [
        {
            **template,
            "value": 12345.5,
            "datetime_utc": (start + timedelta(minutes=5 * i)).isoformat(),
            "datetime": (start + timedelta(minutes=5 * i))
            .astimezone(ZoneInfo("Europe/Madrid"))
            .isoformat(),
        }
        for i in range(301)
    ]
    body = json.dumps(document).encode()
    root = tmp_path / "live"
    assert run(root, transport_factory=factory_for(mutations={"esios": body})) == 3
    entry = load(root).entries[1]
    assert entry.attempts == 1 and entry.statuses == [200]
    assert entry.outcome == "parse_failure" and entry.error_code.value == "content_invalid"
    assert entry.record_count == 0 and entry.replay == "equal"
    assert (root / entry.archive.relative_path).read_bytes() == body
    assert entry.archive.raw.sha256 == hashlib.sha256(body).hexdigest()


def test_manifest_query_linkage_mismatch_fails_replay(tmp_path, fake_clock):
    root = tmp_path / "live"
    assert run(root, transport_factory=factory_for()) == 0
    manifest = load(root)
    manifest.entries[0].query_sha256 = "0" * 64
    live.save_manifest(root, manifest)
    assert live.run(args(root, enabled=False, replay=True), environment={}) == 3
    assert load(root).entries[0].replay == "failed"
