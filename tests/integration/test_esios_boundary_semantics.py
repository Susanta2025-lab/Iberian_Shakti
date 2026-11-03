"""Generated native samples; candidate endpoint semantics never require network."""

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest

from iberian_shakti.contracts.ingestion import ParseOutcome
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow
from iberian_shakti.ingestion import phase2_live as live
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.esios.adapter import BoundedEsiosAdapter, EsiosAdapter
from iberian_shakti.ingestion.esios.identity import request_for
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import result_for

MADRID = ZoneInfo("Europe/Madrid")
STEP = timedelta(minutes=5)
NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)
TARGET = QueryWindow(
    start_utc=datetime(2026, 10, 24, tzinfo=UTC), end_utc=datetime(2026, 10, 25, tzinfo=UTC)
)
WINDOWS = [
    QueryWindow(start_utc=start, end_utc=start + timedelta(days=1))
    for start in (
        datetime(2026, 10, 20, tzinfo=UTC),  # ordinary
        TARGET.start_utc,  # original ambiguous logical end, unambiguous wire end
        datetime(2026, 10, 24, 23, tzinfo=UTC),  # autumn fold inside support
        datetime(2026, 3, 29, tzinfo=UTC),  # spring jump inside support
    )
]


def body_for(window, *, count=None):
    size = int((window.end_utc - window.start_utc) / STEP) if count is None else count
    times = [window.start_utc + i * STEP for i in range(size)]
    return json.dumps(
        {
            "indicator": {
                "id": 544,
                "name": "Demanda prevista Peninsular",
                "magnitud": [{"name": "Potencia"}],
                "tiempo": [{"name": "Cinco minutos"}],
                "geos": [{"geo_id": 999001, "geo_name": "Península"}],
                "values": [
                    {
                        "datetime_utc": t.isoformat(),
                        "datetime": t.astimezone(MADRID).isoformat(),
                        "geo_id": 999001,
                        "value": 12345.5,
                    }
                    for t in times
                ],
            }
        }
    ).encode()


def parse(body, window=TARGET, *, bounded=True):
    adapter = BoundedEsiosAdapter() if bounded else EsiosAdapter()
    source = adapter.resolve(request_for(window, bounded=bounded))
    acquired = result_for(source, uuid4(), NOW, content=body)
    return adapter.parser.parse(
        acquired.payload, acquired.provenance, parsed_at=NOW, parse_event_id=uuid4()
    )


@pytest.mark.parametrize("window", WINDOWS)
def test_grid_wire_identity_and_full_half_open_support(window):
    request = request_for(window, bounded=True)
    adapter = BoundedEsiosAdapter()
    params = httpx.URL(adapter.transport_url(adapter.resolve(request))).params
    assert dict(params) == {
        "start_date": window.start_utc.isoformat(),
        "end_date": (window.end_utc - STEP).isoformat(),
    }
    assert request.window == window
    assert request.report_id == "indicator544.v0.2.0"
    restored = ApiSourceRequest.model_validate_json(request.model_dump_json())
    assert restored == request and restored.query_identity == request.query_identity
    legacy = request_for(window)
    assert legacy.window == request.window and legacy.query == request.query
    assert legacy.query_identity != request.query_identity
    assert (
        httpx.URL(EsiosAdapter.transport_url(EsiosAdapter.resolve(legacy))).params["end_date"]
        == window.end_utc.isoformat()
    )
    parsed = parse(body_for(window), window)
    assert parsed.provenance.outcome is ParseOutcome.SUCCESS
    assert parsed.provenance.catalogue_version == parsed.provenance.parser_version == "0.2.0"
    times = [r.timing.at_utc for r in parsed.records]
    assert len(times) == 288  # only these four 24-hour/five-minute test windows
    assert times[0] == window.start_utc and times[-1] == window.end_utc - STEP
    assert all(window.start_utc <= t < window.end_utc for t in times)
    assert all(b - a == STEP for a, b in pairwise(times))
    assert all(r.cadence_seconds == 300 for r in parsed.records)


def test_original_endpoint_later_fold_hypothesis_and_corrected_endpoint():
    earlier = TARGET.end_utc.astimezone(MADRID)
    later = (TARGET.end_utc + timedelta(hours=1)).astimezone(MADRID)
    assert earlier.isoformat() == "2026-10-25T02:00:00+02:00" and earlier.fold == 0
    assert later.isoformat() == "2026-10-25T02:00:00+01:00" and later.fold == 1
    assert earlier.replace(tzinfo=None) == later.replace(tzinfo=None)
    last = (TARGET.end_utc - STEP).astimezone(MADRID)
    assert last.isoformat() == "2026-10-25T01:55:00+02:00"
    assert last.replace(fold=0).utcoffset() == last.replace(fold=1).utcoffset()
    # This models a possible provider rule, not a claim about its internals.
    assert earlier.replace(fold=1).astimezone(UTC) == TARGET.end_utc + timedelta(hours=1)


@pytest.mark.parametrize("minutes", [5, 10, 60, 1500])
def test_native_grid_not_a_universal_288_record_assumption(minutes):
    start = WINDOWS[0].start_utc
    window = QueryWindow(start_utc=start, end_utc=start + timedelta(minutes=minutes))
    parsed = parse(body_for(window), window)
    assert parsed.provenance.outcome is ParseOutcome.SUCCESS
    assert len(parsed.records) == minutes // 5
    assert parsed.records[0].timing.at_utc == start
    assert parsed.records[-1].timing.at_utc == window.end_utc - STEP
    params = httpx.URL(
        BoundedEsiosAdapter.transport_url(
            BoundedEsiosAdapter.resolve(request_for(window, bounded=True))
        )
    ).params
    assert params["end_date"] == (window.end_utc - STEP).isoformat()


@pytest.mark.parametrize("window", [WINDOWS[2], WINDOWS[3]])
def test_real_utc_stepping_preserves_autumn_folds_and_spring_jump(window):
    document = json.loads(body_for(window))
    values = document["indicator"]["values"]
    before = next(v for v in values if v["datetime_utc"].endswith("00:55:00+00:00"))
    after = next(v for v in values if v["datetime_utc"].endswith("01:00:00+00:00"))
    if window == WINDOWS[2]:
        assert before["datetime"].endswith("02:55:00+02:00")
        assert after["datetime"].endswith("02:00:00+01:00")
        assert {
            datetime.fromisoformat(v["datetime_utc"]).astimezone(MADRID).fold for v in values
        } == {
            0,
            1,
        }
    else:
        assert before["datetime"].endswith("01:55:00+01:00")
        assert after["datetime"].endswith("03:00:00+02:00")
        assert not any("T02:" in v["datetime"] for v in values)
    assert parse(json.dumps(document).encode(), window).provenance.outcome is ParseOutcome.SUCCESS


@pytest.mark.parametrize("mutation", ["before", "end", "after", "malformed", "wrong_offset"])
def test_bad_late_or_boundary_value_is_atomic_without_clipping(mutation):
    document = json.loads(body_for(TARGET))
    values = document["indicator"]["values"]
    if mutation in {"before", "end", "after"}:
        instant = {
            "before": TARGET.start_utc - STEP,
            "end": TARGET.end_utc,
            "after": TARGET.end_utc + STEP,
        }[mutation]
        value = values[0] if mutation == "before" else values[-1]
        value.update(
            datetime_utc=instant.isoformat(), datetime=instant.astimezone(MADRID).isoformat()
        )
    elif mutation == "malformed":
        values[-1]["value"] = True
    else:
        values[-1]["datetime"] = "2026-10-25T00:55:00+01:00"
    parsed = parse(json.dumps(document).encode())
    assert parsed.records == () and parsed.provenance.record_count == 0
    assert parsed.provenance.outcome is ParseOutcome.CONTENT_FAILURE


@pytest.mark.parametrize("bounded", [False, True])
def test_301_sample_original_overrun_remains_rejected(bounded):
    parsed = parse(body_for(TARGET, count=301), bounded=bounded)
    assert parsed.records == () and parsed.provenance.error_code.value == "content_invalid"
    if not bounded:
        assert request_for(TARGET).query_identity == (
            "6b01d414cdc160d2445f33015ce6d25ff7751b07215a8cd73c20f2279e0b92bd"
        )
        # Keep the old accepted inclusive-end interpretation untouched.
        assert parse(body_for(TARGET, count=289), bounded=False).provenance.outcome is (
            ParseOutcome.SUCCESS
        )


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-10-25T00:00:00Z", "2026-10-25T03:00:00Z"),  # ambiguous start
        ("2026-10-24T23:00:00Z", "2026-10-25T01:00:00Z"),  # ambiguous last sample
        ("2026-10-24T00:01:00Z", "2026-10-25T00:00:00Z"),  # not on grid
        ("2026-10-24T00:00:00Z", "2026-10-24T00:04:00Z"),
    ],
)
def test_unsupported_wire_boundaries_fail_locally(start, end):
    with pytest.raises(ValueError):
        request_for(
            QueryWindow(
                start_utc=datetime.fromisoformat(start), end_utc=datetime.fromisoformat(end)
            ),
            bounded=True,
        )


@pytest.mark.parametrize("count,expected", [(288, "success"), (301, "parse_failure")])
def test_targeted_controller_only_esios_and_denied_replay(tmp_path, monkeypatch, count, expected):
    body = body_for(TARGET, count=count)
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.host == "api.esios.ree.es" and request.url.path == "/indicators/544"
        assert dict(request.url.params) == {
            "start_date": "2026-10-24T00:00:00+00:00",
            "end_date": "2026-10-24T23:55:00+00:00",
        }
        assert request.headers["x-api-key"] == "synthetic-esios-boundary-only"
        return httpx.Response(200, stream=httpx.ByteStream(body))

    root = tmp_path / "live"
    args = argparse.Namespace(
        live=True, replay_only=False, esios_boundary_only=True, archive_root=root
    )
    code = live.run(
        args,
        environment={"ESIOS_API_TOKEN": "synthetic-esios-boundary-only"},
        now=lambda: NOW,
        transport_factory=lambda _: httpx.MockTransport(handler),
    )
    assert code == (0 if count == 288 else 3)
    assert len(calls) == 1
    manifest = live.Manifest.model_validate_json((root / live.MANIFEST).read_bytes())
    assert manifest.scope == "esios_boundary" and len(manifest.entries) == 1
    assert manifest.logical_planned == manifest.logical_limit == 1 and manifest.attempt_limit == 3
    assert manifest.accounting["logical_requests"] == manifest.accounting["http_attempts"] == 1
    entry = manifest.entries[0]
    assert entry.outcome == expected and entry.replay == "equal"
    assert entry.record_count == (288 if count == 288 else 0)
    assert entry.archive.raw.sha256 == hashlib.sha256(body).hexdigest()
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    archive = LocalRawArchive(root)
    with live.network_denied():
        acquired = replay(archive, entry.archive, entry.retrieval_uuid)
        assert acquired.provenance.source.request == entry.request
        assert acquired.provenance.source.request.query_identity == entry.query_sha256
        assert acquired.payload.content == body
    args.live, args.replay_only = False, True

    def denied(*args, **kwargs):
        pytest.fail("Replay attempted credentials or acquisition")

    monkeypatch.setattr(live, "load_provider_auth", denied)
    monkeypatch.setattr(BoundedEsiosAdapter, "retriever", denied)
    assert live.run(args, environment={}) == 0
    assert all(p.read_bytes() == value for p, value in before.items() if p.name != live.MANIFEST)
    assert len(list(root.rglob("retrievals/*.json"))) == 1
    assert len(list(root.rglob("parses/*.json"))) == 3
    assert len(list(root.rglob("payload.bin"))) == 1


def test_targeted_default_command_remains_offline(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("No live authorization")

    monkeypatch.setattr(live, "load_provider_auth", denied)
    monkeypatch.setattr(httpx, "Client", denied)
    assert live.main(["--esios-boundary-only", "--archive-root", str(tmp_path / "live")]) == 2
    assert not list(tmp_path.iterdir())
