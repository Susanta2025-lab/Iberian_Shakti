"""One archive, independent immutable evidence, failure isolation and offline replay."""

import hashlib
import io
import json
import logging
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

import httpx
import pytest

from iberian_shakti.common.logging import configure_logging
from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ParseOutcome,
    SourceRequest,
    parse_event_from_json,
)
from iberian_shakti.contracts.market import MarketPrice
from iberian_shakti.contracts.measurements import SupportInterval, ValidInstant, ValueKind
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.config import ConfigurationError
from iberian_shakti.ingestion.errors import ArchiveError, FailureReason, ReplayError
from iberian_shakti.ingestion.omie.identity import resolved_source
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import result_for

from .support import (
    DATA,
    TOKENS,
    assert_preserved,
    cases_for,
    deny_reacquisition,
    execute,
    forbidden,
    reparse,
    seed,
    snapshot,
)

KEYS = tuple(c.key for c in cases_for())


def test_combined_replay_and_full_raw_provenance_without_credentials_or_acquisition(
    tmp_path, monkeypatch
):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for(all_sites=True)
    results = seed(archive, cases)
    assert len(cases) == len(results) == 18
    before = snapshot(tmp_path)
    retrieval_paths = set(tmp_path.rglob("retrievals/*.json"))
    # Identical weather bytes can share content within their product partition;
    # distinct sites remain distinct immutable queries/acquisitions, not fake
    # site-specific hashes. Provider/report always remain part of raw identity.
    assert len({r.retrieval.raw.content_identity for r in results.values()}) == 8
    assert len({r.retrieval.source.safe_locator for r in results.values()}) == 18
    deny_reacquisition(monkeypatch)
    for i, case in enumerate(cases, 1):
        result = results[case.key]
        event = result.parse.provenance
        path = tmp_path / event.archive.relative_path
        stored_parse = parse_event_from_json(
            (path.parent / "parses" / f"{event.parse_event_id}.json").read_bytes()
        )
        assert stored_parse == event
        retrieval = archive.load_retrieval(event.archive, event.retrieval_event_id)
        assert retrieval == result.retrieval and retrieval.source.request == case.source.request
        assert retrieval.raw == event.raw == event.archive.raw
        assert hashlib.sha256(path.read_bytes()).hexdigest() == event.raw.sha256
        assert path.read_bytes() == case.body
        for record in result.parse.records:
            assert record.parse_event_id == stored_parse.parse_event_id
            assert (
                record.source_id == event.raw.source_id and record.report_id == event.raw.report_id
            )
            if not isinstance(record, MarketPrice):
                assert record.retrieval_event_id == retrieval.retrieval_event_id
        repeated = reparse(archive, case, result, 20_000 + i)
        assert repeated.provenance.raw == event.raw
        assert repeated.provenance.parsed_at != event.parsed_at
    assert_preserved(before)
    assert set(tmp_path.rglob("retrievals/*.json")) == retrieval_paths
    assert len(list(tmp_path.rglob("parses/*.json"))) == 36


@pytest.mark.parametrize("key", KEYS)
def test_one_corrupt_payload_fails_replay_without_fallback_or_damage_to_other_sources(
    tmp_path, monkeypatch, key
):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    results = seed(archive, cases)
    bad = results[key].retrieval
    path = tmp_path / bad.archive.relative_path
    other_files = {p: b for p, b in snapshot(tmp_path).items() if p != path}
    path.chmod(0o600)
    path.write_bytes(b"corrupted synthetic evidence")
    retrieval_paths = set(tmp_path.rglob("retrievals/*.json"))
    deny_reacquisition(monkeypatch)
    with pytest.raises(ReplayError) as caught:
        replay(archive, bad.archive, bad.retrieval_event_id)
    assert caught.value.reason is FailureReason.REPLAY
    for i, case in enumerate(cases):
        if case.key != key:
            reparse(archive, case, results[case.key], 30_000 + i)
    assert_preserved(other_files)
    assert path.read_bytes() == b"corrupted synthetic evidence"
    assert set(tmp_path.rglob("retrievals/*.json")) == retrieval_paths


@pytest.mark.parametrize(
    "key,body,status,outcome,code",
    [
        (
            "omie",
            b"MARGINALPDBC;\ninvalid final row\n*\n",
            200,
            ParseOutcome.CONTENT_FAILURE,
            ErrorCode.CONTENT_INVALID,
        ),
        (
            "ren",
            (DATA / "ren/synthetic_invalid_json.json").read_bytes(),
            200,
            ParseOutcome.CONTENT_FAILURE,
            ErrorCode.CONTENT_INVALID,
        ),
        ("esios", b"unchecked private auth error", 401, None, ErrorCode.AUTHENTICATION_FAILURE),
        (
            "esios",
            b'{"indicator":{"id":544,"values":[null]}}',
            200,
            ParseOutcome.CONTENT_FAILURE,
            ErrorCode.SCHEMA_UNSUPPORTED,
        ),
        (
            "esios",
            b"unchecked private permission error",
            403,
            None,
            ErrorCode.AUTHORIZATION_FAILURE,
        ),
        (
            "entsoe_load",
            (DATA / "entsoe/synthetic_acknowledgement.xml")
            .read_bytes()
            .replace(b"No matching data found", b"Unknown authentication issue; no data available"),
            200,
            ParseOutcome.PROVIDER_REJECTED,
            ErrorCode.PROVIDER_REJECTED,
        ),
        (
            "entsoe_pt",
            (DATA / "entsoe/synthetic_acknowledgement.xml").read_bytes(),
            200,
            ParseOutcome.SOURCE_UNAVAILABLE,
            ErrorCode.NO_DATA,
        ),
        (
            "era5:PT.lisbon",
            b"not JSON",
            200,
            ParseOutcome.CONTENT_FAILURE,
            ErrorCode.CONTENT_INVALID,
        ),
        (
            "icon_eu:PT.lisbon",
            b"not JSON",
            200,
            ParseOutcome.CONTENT_FAILURE,
            ErrorCode.CONTENT_INVALID,
        ),
    ],
)
def test_failed_source_preserves_all_prior_evidence_and_other_sources_still_replay(
    tmp_path, monkeypatch, key, body, status, outcome, code
):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    results = seed(archive, cases)
    before = snapshot(tmp_path)
    case = next(c for c in cases if c.key == key)
    failed = execute(archive, case, 100, body=body, status=status)
    if status == 200:
        assert failed.retrieval.http_status == 200
        assert archive.load(failed.retrieval.archive).content == body
        assert failed.parse.records == () and failed.parse.provenance.outcome is outcome
        assert failed.parse.provenance.error_code is code
    else:
        assert failed.parse is None and failed.retrieval.raw is None
        assert failed.retrieval.error_code is code
    assert_preserved(before)
    deny_reacquisition(monkeypatch)
    # Even this source's previously successful acquisition remains usable.
    for i, original_case in enumerate(cases):
        reparse(archive, original_case, results[original_case.key], 40_000 + i)
    assert_preserved(before)


@pytest.mark.parametrize("key", ["esios", "entsoe_load"])
def test_missing_selected_credentials_do_not_read_real_environment_or_damage_anonymous_history(
    tmp_path, monkeypatch, key
):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    results = seed(archive, cases)
    before = snapshot(tmp_path)
    monkeypatch.setattr(httpx, "Client", forbidden)
    case = next(c for c in cases if c.key == key)
    with pytest.raises(ConfigurationError, match="Missing or invalid selected-provider credential"):
        case.adapter.retriever(retrieval_event_id=UUID(int=100), environ={})
    assert_preserved(before)
    for c in cases:
        assert archive.load(results[c.key].retrieval.archive).content == c.body


@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize("boundary", ["payload", "retrieval", "parse"])
def test_required_persistence_failure_prevents_success_for_every_path(
    tmp_path, monkeypatch, key, boundary
):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    results = seed(archive, cases)
    before = snapshot(tmp_path)
    case = next(c for c in cases if c.key == key)
    original_publish = archive._publish
    original_parse = case.parser.parse
    parsed_events = []

    def publish(path, data, *, metadata):
        category = (
            "payload"
            if not metadata
            else ("parse" if path.parent.name == "parses" else "retrieval")
        )
        if category == boundary:
            raise ArchiveError(
                ErrorCode.ARCHIVE_FAILURE,
                FailureReason.METADATA if metadata else FailureReason.ARCHIVE_IO,
            )
        return original_publish(path, data, metadata=metadata)

    def parse(*args, **kwargs):
        parsed_events.append(kwargs["parse_event_id"])
        # The real parser cannot run before original bytes and retrieval exist.
        retrieval = args[1]
        assert archive.load_retrieval(retrieval.archive, retrieval.retrieval_event_id) == retrieval
        return original_parse(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(archive, "_publish", publish)
        patch.setattr(case.parser, "parse", parse)
        with pytest.raises(ArchiveError) as caught:
            execute(archive, case, 100)
        assert caught.value.code is ErrorCode.ARCHIVE_FAILURE
    assert parsed_events == ([UUID(int=10_100)] if boundary == "parse" else [])
    assert not list(tmp_path.rglob(f"parses/{UUID(int=10_100)}.json"))
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == len(cases) + (boundary == "parse")
    assert_preserved(before)
    deny_reacquisition(monkeypatch)
    for i, c in enumerate(cases):
        reparse(archive, c, results[c.key], 50_000 + i)
    assert_preserved(before)


@pytest.mark.parametrize("key", KEYS)
def test_identical_and_revised_acquisitions_are_provider_local_and_immutable(
    tmp_path, monkeypatch, key
):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    results = seed(archive, cases)
    before = snapshot(tmp_path)
    case = next(c for c in cases if c.key == key)
    original = results[key]
    identical = execute(archive, case, 100)
    old, new = (
        (b"42.00", b"43.00")
        if key == "omie"
        else (b"1.2300", b"2.2300")
        if key == "ren"
        else (b"23000.12300", b"24000.12300")
        if key in {"esios", "entsoe_load"}
        else (b"1000.12300", b"1100.12300")
        if key.startswith("entsoe_")
        else (b"12.25", b"13.25")
    )
    revised = replace(case, body=case.body.replace(old, new, 1))
    if key == "omie":
        request = SourceRequest(
            source_id="omie",
            report_id="marginalpdbc",
            delivery_date=case.source.request.delivery_date,
            revision=2,
        )
        revised = replace(revised, source=resolved_source(request, 2))
    corrected = execute(archive, revised, 101)
    assert original.retrieval.raw == identical.retrieval.raw != corrected.retrieval.raw
    assert original.parse.records[0] != corrected.parse.records[0]
    original_value = (
        original.parse.records[0].price if key == "omie" else original.parse.records[0].value
    )
    changed_value = (
        corrected.parse.records[0].price if key == "omie" else corrected.parse.records[0].value
    )
    assert original_value != changed_value
    if key != "omie":
        assert (
            original.retrieval.source.request.query_identity
            == corrected.retrieval.source.request.query_identity
        )
    is_forecast = key != "omie" and original.parse.records[0].kind is ValueKind.FORECAST
    identities = {r.parse.records[0].business_identity for r in (original, identical, corrected)}
    assert len(identities) == (3 if is_forecast else 1)
    assert len(list(tmp_path.rglob("payload.bin"))) == len(cases) + 1
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == len(cases) + 2
    assert_preserved(before)
    deny_reacquisition(monkeypatch)
    for i, c in enumerate(cases):
        reparse(archive, c, results[c.key], 60_000 + i)
    reparse(archive, case, identical, 61_000)
    reparse(archive, revised, corrected, 61_001)
    assert_preserved(before)


def test_same_timestamp_value_country_and_concept_do_not_deduplicate_sources(tmp_path):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    changed = []
    start = next(c for c in cases if c.key == "entsoe_load").source.request.window.start_utc
    for case in cases:
        body = case.body
        if case.key == "ren":
            # Local midnight is 23Z; the fourth subsequent quarter starts at
            # UTC midnight. Set that source array value without moving it.
            data = json.loads(body)
            data["series"][0]["data"][4] = 42
            body = json.dumps(data).encode()
        elif case.key == "entsoe_load":
            body = body.replace(b"23000.12300", b"42", 1)
        elif case.key == "esios":
            data = json.loads(body)
            item = data["indicator"]["values"][0]
            item.update(
                value=42, datetime_utc="2026-10-25T00:00:00Z", datetime="2026-10-25T02:00:00+02:00"
            )
            body = json.dumps(data).encode()
        changed.append(replace(case, body=body))
    results = seed(archive, tuple(changed))
    entsoe_record = results["entsoe_load"].parse.records[0]
    esios_record = results["esios"].parse.records[0]
    ren_record = next(
        r
        for r in results["ren"].parse.records
        if r.measure.kind == "load" and r.timing.start_utc == start
    )
    selected = [ren_record, entsoe_record, esios_record]
    assert {r.value for r in selected} == {42}
    assert {r.measure.kind for r in selected} == {"load"}
    assert {
        r.timing.start_utc if isinstance(r.timing, SupportInterval) else r.timing.at_utc
        for r in selected
    } == {start}
    assert entsoe_record.geography.country_code == esios_record.geography.country_code == "ES"
    assert len({r.business_identity for r in selected}) == 3
    market = next(
        r
        for r in results["omie"].parse.records
        if r.market_area == "ES" and r.interval_start_utc == start
    )
    assert market.price == 42 and market.business_identity not in {
        r.business_identity for r in selected
    }


@pytest.fixture
def managed_output():
    loggers = [logging.getLogger(name) for name in ("", "httpx", "httpcore")]
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


def test_mixed_private_and_anonymous_diagnostics_never_leak_credentials_or_provider_prose(
    tmp_path, managed_output
):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    results = seed(archive, cases)
    diagnostics = "".join(r.model_dump_json() for r in results.values())
    for i, case in enumerate(cases):
        if case.key in {"esios", "entsoe_load"}:
            token = TOKENS["ESIOS_API_TOKEN" if case.key == "esios" else "ENTSOE_API_TOKEN"]
            result = execute(archive, case, 100 + i, body=token.encode())
            assert (
                result.parse is None and result.retrieval.error_code is ErrorCode.SENSITIVE_RESPONSE
            )
            assert result.retrieval.raw is None
            timeout = execute(archive, case, 200 + i, timeout=True)
            assert timeout.parse is None and timeout.retrieval.error_code is ErrorCode.TIMEOUT
            diagnostics += timeout.model_dump_json()
        elif case.key.startswith(("era5:", "icon_eu:")):
            result = execute(
                archive,
                case,
                100 + i,
                body=b'{"error":true,"reason":"unrestricted synthetic provider prose"}',
            )
            assert result.parse.provenance.outcome is ParseOutcome.PROVIDER_REJECTED
        else:
            result = execute(archive, case, 100 + i, body=b"unrestricted synthetic provider prose")
            assert result.parse.records == ()
        diagnostics += result.model_dump_json()
    diagnostics += managed_output.getvalue() + "".join(
        p.read_text() for p in tmp_path.rglob("*.json")
    )
    assert "unrestricted synthetic provider prose" not in diagnostics
    assert "unrestricted synthetic transport prose" not in diagnostics
    for token in TOKENS.values():
        assert token not in diagnostics
        assert all(token.encode() not in p.read_bytes() for p in tmp_path.rglob("payload.bin"))
    assert "https://" not in managed_output.getvalue()
    assert "securityToken" not in diagnostics and "x-api-key" not in diagnostics


@pytest.mark.parametrize("key", KEYS)
def test_per_source_response_limit_cannot_invalidate_other_evidence(tmp_path, monkeypatch, key):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    results = seed(archive, cases)
    before = snapshot(tmp_path)
    case = next(c for c in cases if c.key == key)
    caps = {"omie": 4, "ren": 1, "esios": 2, "entsoe": 4, "open_meteo": 1}
    result = execute(
        archive, case, 100, body=b"x" * (caps[case.source.request.source_id] * 1024 * 1024 + 1)
    )
    assert result.parse is None and result.retrieval.error_code is ErrorCode.SIZE_LIMIT
    assert snapshot(tmp_path) == before
    deny_reacquisition(monkeypatch)
    for i, c in enumerate(cases):
        reparse(archive, c, results[c.key], 70_000 + i)


def test_old_weather_forecast_target_cannot_be_relabelled_as_latest_acquisition(tmp_path):
    archive = LocalRawArchive(tmp_path)
    cases = cases_for()
    results = seed(archive, cases)
    case = next(c for c in cases if c.key == "icon_eu:PT.lisbon")
    loaded = replay(
        archive, results[case.key].retrieval.archive, results[case.key].retrieval.retrieval_event_id
    )
    # Correct bytes and query, but a later acquisition cannot pretend they are
    # the supported next-day forecast. No reconstructed run or fallback exists.
    later = result_for(
        case.source,
        UUID(int=100),
        case.completed_at + timedelta(days=30),
        content=loaded.payload.content,
    )
    parsed = case.parser.parse(
        later.payload,
        later.provenance,
        parsed_at=case.completed_at + timedelta(days=31),
        parse_event_id=UUID(int=101),
    )
    assert parsed.records == () and parsed.provenance.outcome is ParseOutcome.CONTENT_FAILURE
    assert all(r.source_times.issue_time is None for r in results[case.key].parse.records)
    assert isinstance(results[case.key].parse.records[0].timing, ValidInstant)
