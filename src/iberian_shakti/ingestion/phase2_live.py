"""Explicit, finite Stage 8 operator command. Default execution is offline.

The seven selections are fixed; no dates/products/models can be overridden.
Credentials come only from an explicitly supplied environment. Replay uses only
the existing immutable archive and denies acquisition/credential/network access.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import signal
import socket
import threading
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Literal, NoReturn
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from iberian_shakti.common.logging import configure_logging
from iberian_shakti.contracts.ingestion import (
    ArchiveReference,
    ErrorCode,
    IngestionResult,
    ParseOutcome,
    ParseResult,
    ResolvedSource,
    parse_event_from_json,
)
from iberian_shakti.contracts.queries import ApiSourceRequest, QueryWindow
from iberian_shakti.ingestion._http_transport import DeadlineTransport
from iberian_shakti.ingestion._live_budget import (
    Budget,
    CountedTransport,
    Limits,
    RunBackend,
    RunStop,
    hard_deadline,
)
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.auth import PrivateRequestPolicy
from iberian_shakti.ingestion.config import ConfigurationError, load_provider_auth
from iberian_shakti.ingestion.entsoe.adapter import EntsoeAdapter
from iberian_shakti.ingestion.entsoe.identity import request_for as entsoe_request
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.esios.adapter import BoundedEsiosAdapter, EsiosAdapter
from iberian_shakti.ingestion.esios.identity import request_for as esios_request
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.ren.adapter import RenAdapter
from iberian_shakti.ingestion.ren.identity import request_for as ren_request
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import utc_now
from iberian_shakti.ingestion.runner import ingest_resolved
from iberian_shakti.ingestion.weather.adapter import OpenMeteoAdapter, OpenMeteoForecastAdapter
from iberian_shakti.ingestion.weather.identity import forecast_request_for, historical_request_for

HISTORICAL_DAY = date(2026, 10, 24)
MANIFEST = "stage8-manifest.json"
type Product = Literal["ren", "esios", "entsoe_load", "entsoe_pt", "entsoe_es", "era5", "icon_eu"]
type Adapter = RenAdapter | EsiosAdapter | EntsoeAdapter | OpenMeteoAdapter


@dataclass(frozen=True)
class Selection:
    key: Product
    adapter: Adapter
    source: ResolvedSource

    @property
    def request(self) -> ApiSourceRequest:
        request = self.source.request
        assert isinstance(request, ApiSourceRequest)
        return request


def daily(day: date) -> QueryWindow:
    start = datetime.combine(day, time.min, UTC)
    return QueryWindow(start_utc=start, end_utc=start + timedelta(days=1))


def plan(at: datetime) -> tuple[Selection, ...]:
    window = daily(HISTORICAL_DAY)
    forecast = daily(at.astimezone(UTC).date() + timedelta(days=1))
    requests: tuple[tuple[Product, Adapter, ApiSourceRequest], ...] = (
        ("ren", RenAdapter(), ren_request(HISTORICAL_DAY)),
        ("esios", EsiosAdapter(), esios_request(window)),
        ("entsoe_load", EntsoeAdapter(), entsoe_request("actual_load", "ES", window)),
        ("entsoe_pt", EntsoeAdapter(), entsoe_request("wind_solar_forecast", "PT", window)),
        ("entsoe_es", EntsoeAdapter(), entsoe_request("wind_solar_forecast", "ES", window)),
        ("era5", OpenMeteoAdapter(), historical_request_for(window, "PT.lisbon")),
        ("icon_eu", OpenMeteoForecastAdapter(), forecast_request_for(forecast, "PT.lisbon")),
    )
    return tuple(
        Selection(key, adapter, adapter.resolve(request)) for key, adapter, request in requests
    )


def esios_boundary_plan() -> tuple[Selection, ...]:
    """Only the separately authorized continuation, same logical business window."""
    adapter = BoundedEsiosAdapter()
    request = esios_request(daily(HISTORICAL_DAY), bounded=True)
    return (Selection("esios", adapter, adapter.resolve(request)),)


class SafeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class Entry(SafeModel):
    product: Product
    logical_number: int = Field(ge=1, le=7)
    request: ApiSourceRequest
    query_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempts: int = Field(default=0, ge=0, le=3)
    statuses: list[int | None] = Field(default_factory=list, max_length=3)
    attempted_body_bytes: int = Field(default=0, ge=0)
    error_body_read_failures: int = Field(default=0, ge=0, le=3)
    archive: ArchiveReference | None = None
    retrieval_uuid: UUID | None = None
    parse_uuid: UUID | None = None
    record_count: int = Field(default=0, ge=0)
    outcome: Literal["not_executed", "success", "retrieval_failure", "parse_failure", "stopped"] = (
        "not_executed"
    )
    error_code: ErrorCode | None = None
    content_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    parse_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    replay: Literal["not_run", "equal", "failed"] = "not_run"
    replay_parse_uuid: UUID | None = None
    cumulative: dict[str, int | float] = Field(default_factory=dict)


type StopCategory = Literal[
    "wall_clock_budget_exhausted",
    "logical_request_budget_exhausted",
    "metadata_request_budget_exhausted",
    "http_attempt_budget_exhausted",
    "attempted_byte_budget_exhausted",
    "transport_accounting_failure",
    "request_outside_authorized_plan",
    "unsafe_redirect",
    "unsafe_transport",
    "sensitive_response",
    "entsoe_rate_limited",
    "archive_integrity_failure",
    "attempt_accounting_failure",
    "internal_safety_failure",
]


class Manifest(SafeModel):
    run_id: UUID
    started_utc: datetime
    ended_utc: datetime | None = None
    scope: Literal["original", "esios_boundary"] = "original"
    icon_target: date | None
    logical_planned: Literal[1, 7] = 7
    logical_limit: Literal[1, 8] = 8
    attempt_limit: Literal[3, 24] = 24
    byte_limit: Literal[6291456, 33554432] = 33554432
    seconds_limit: Literal[120, 900] = 900
    entries: list[Entry]
    accounting: dict[str, int | float] = Field(default_factory=dict)
    remaining_budget: dict[str, int | float] = Field(default_factory=dict)
    archived_bytes: int = 0
    logical_successful: int = 0
    retries_by_provider: dict[str, int] = Field(default_factory=dict)
    stop_category: StopCategory | None = None


def archive_root(path: Path) -> Path:
    root = path.expanduser().resolve()
    repository = Path(__file__).resolve().parents[3]
    if (
        not path.is_absolute()
        or root == repository
        or repository in root.parents
        or "live" not in root.name.lower()
        or any(
            "fixture" in part.lower() or part.lower() in {"tests", "test"} for part in root.parts
        )
        or root == Path(root.anchor)
        or any(p.is_symlink() for p in (path, *path.parents))
    ):
        raise ConfigurationError("An explicit external live archive root is required")
    return root


def prepare_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(root.iterdir()):
        raise ConfigurationError("A new empty live archive root is required")
    # Test the archive's actual no-replace primitive before network construction.
    first, second = root / ".preflight", root / ".preflight-link"
    try:
        with first.open("xb") as stream:
            stream.write(b"stage8-local-preflight")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(first, second)
        if second.read_bytes() != b"stage8-local-preflight":
            raise ConfigurationError("Archive preflight failed")
    finally:
        second.unlink(missing_ok=True)
        first.unlink(missing_ok=True)


def _digest(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def content_digest(parsed: ParseResult) -> str:
    return _digest(
        [record.model_dump(mode="json", exclude={"parse_event_id"}) for record in parsed.records]
    )


def parse_digest(parsed: ParseResult) -> str:
    return _digest(
        parsed.provenance.model_dump(mode="json", exclude={"parse_event_id", "parsed_at"})
    )


def save_manifest(
    root: Path, manifest: Manifest, guards: Sequence[PrivateRequestPolicy] = ()
) -> None:
    # Revalidate a closed schema. No arbitrary dict/provider message is serialized.
    content = (
        Manifest.model_validate_json(manifest.model_dump_json()).model_dump_json(indent=2).encode()
        + b"\n"
    )
    if any(guard.contains_credential(content) for guard in guards):
        raise RunStop("sensitive_response")
    temporary = root / ".manifest-pending"
    with temporary.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(root / MANIFEST)


def _denied(*args: object, **kwargs: object) -> NoReturn:
    raise RunStop("Replay attempted acquisition, credentials or network")


@contextmanager
def network_denied() -> Iterator[None]:
    """Same explicit injection/denial technique as the Stage 6/7 regressions."""
    with ExitStack() as stack:
        for name in (
            "create_connection",
            "getaddrinfo",
            "gethostbyname",
            "gethostbyname_ex",
            "gethostbyaddr",
            "getnameinfo",
            "getfqdn",
            "socket",
        ):
            stack.enter_context(patch.object(socket, name, _denied))
        for name in ("Client", "AsyncClient", "HTTPTransport", "AsyncHTTPTransport"):
            stack.enter_context(patch.object(httpx, name, _denied))
        stack.enter_context(patch.object(HttpRetriever, "__init__", _denied))
        stack.enter_context(patch.object(HttpRetriever, "retrieve", _denied))
        for adapter in (RenAdapter, EsiosAdapter, EntsoeAdapter, OpenMeteoAdapter):
            stack.enter_context(patch.object(adapter, "retriever", _denied))
        for module in ("config", "esios.adapter", "entsoe.adapter", "phase2_live"):
            stack.enter_context(
                patch(f"iberian_shakti.ingestion.{module}.load_provider_auth", _denied)
            )
        stack.enter_context(patch.dict(os.environ, {}, clear=True))
        yield


def replays(root: Path, manifest: Manifest) -> None:
    archive = LocalRawArchive(root)
    # Rebuild only pinned local parsers. Never construct a retriever here.
    selections = (
        esios_boundary_plan() if manifest.scope == "esios_boundary" else plan(manifest.started_utc)
    )
    selected = {item.key: item for item in selections}
    with network_denied():
        for entry in manifest.entries:
            if entry.archive is None or entry.retrieval_uuid is None:
                continue
            try:
                acquired = replay(archive, entry.archive, entry.retrieval_uuid)
                if (
                    acquired.payload is None
                    or acquired.provenance.source != selected[entry.product].source
                    or acquired.provenance.source.request != entry.request
                    or entry.request.query_identity != entry.query_sha256
                ):
                    raise RunStop("Replay linkage mismatch")
                parsed = selected[entry.product].adapter.parser.parse(
                    acquired.payload,
                    acquired.provenance,
                    parsed_at=utc_now(),
                    parse_event_id=uuid4(),
                )
                if (
                    content_digest(parsed) != entry.content_digest
                    or parse_digest(parsed) != entry.parse_digest
                ):
                    raise RunStop("Replay content mismatch")
                archive.persist_parse(parsed.provenance)
                entry.replay = "equal"
                entry.replay_parse_uuid = parsed.provenance.parse_event_id
            except Exception:
                entry.replay = "failed"


def _record(entry: Entry, result: IngestionResult, archive: LocalRawArchive) -> None:
    retrieval, parsed = result.retrieval, result.parse
    entry.retrieval_uuid = retrieval.retrieval_event_id
    entry.archive = retrieval.archive
    entry.error_code = retrieval.error_code
    entry.outcome = "retrieval_failure"
    if retrieval.archive is not None:
        archive.load(retrieval.archive)
        if archive.load_retrieval(retrieval.archive, retrieval.retrieval_event_id) != retrieval:
            raise RunStop("archive_integrity_failure")
    if parsed is not None:
        entry.parse_uuid = parsed.provenance.parse_event_id
        entry.record_count = len(parsed.records)
        entry.error_code = parsed.provenance.error_code
        entry.outcome = (
            "success" if parsed.provenance.outcome is ParseOutcome.SUCCESS else "parse_failure"
        )
        entry.content_digest, entry.parse_digest = content_digest(parsed), parse_digest(parsed)
        assert retrieval.archive is not None
        sidecar = (
            archive.root
            / Path(retrieval.archive.relative_path).parent
            / "parses"
            / f"{entry.parse_uuid}.json"
        )
        if parse_event_from_json(sidecar.read_bytes()) != parsed.provenance:
            raise RunStop("archive_integrity_failure")


def execute(
    root: Path,
    selections: tuple[Selection, ...],
    manifest: Manifest,
    budget: Budget,
    environment: Mapping[str, str],
    guards: Sequence[PrivateRequestPolicy],
    *,
    now: Callable[[], datetime] = utc_now,
    transport_factory: Callable[[Budget], httpx.BaseTransport] | None = None,
) -> None:
    archive = LocalRawArchive(root)
    # One sequential loop, one production logical acquisition per fixed selection.
    for selection, entry in zip(selections, manifest.entries, strict=True):
        transport: CountedTransport | None = None
        before_bytes = budget.body_bytes
        try:
            budget.begin()
            entry.outcome = "stopped"
            expected_url = selection.adapter.transport_url(selection.source)
            inner = (
                transport_factory(budget)
                if transport_factory
                else DeadlineTransport(backend=RunBackend(budget))
            )
            # Use the production provider factory (and its unchanged retry policy).
            kwargs = (
                {"environ": environment}
                if isinstance(selection.adapter, (EsiosAdapter, EntsoeAdapter))
                else {}
            )
            retriever = selection.adapter.retriever(
                retrieval_event_id=uuid4(), transport=inner, now=now, sleeper=budget.wait, **kwargs
            )
            transport = CountedTransport(inner, budget, expected_url, retriever.max_bytes)
            retriever.transport, retriever.clock = transport, budget.clock
            result = ingest_resolved(
                selection.source,
                retriever=retriever,
                archive=archive,
                parser=selection.adapter.parser,
                parse_event_id=uuid4(),
            )
            if result.retrieval.attempt_count != budget.current_attempts:
                raise RunStop("attempt_accounting_failure")
            _record(entry, result, archive)
            if entry.error_code is ErrorCode.SENSITIVE_RESPONSE:
                raise RunStop("sensitive_response")
            if (
                selection.request.source_id == "entsoe"
                and entry.error_code is ErrorCode.RATE_LIMITED
            ):
                # A token ban affects every later selection in this invocation.
                raise RunStop("entsoe_rate_limited")
        except RunStop as error:
            manifest.stop_category = TypeAdapter(StopCategory).validate_python(str(error))
        except ExecutionError as error:
            entry.error_code = error.code
            if error.code is ErrorCode.UNSUPPORTED_ENCODING:
                entry.outcome = "retrieval_failure"
            else:
                manifest.stop_category = "archive_integrity_failure"
        except Exception:
            manifest.stop_category = "internal_safety_failure"
        finally:
            if transport is not None:
                entry.attempts = len(transport.statuses)
                entry.statuses = transport.statuses
                entry.error_body_read_failures = transport.error_body_read_failures
            entry.attempted_body_bytes = budget.body_bytes - before_bytes
            entry.cumulative = budget.counters()
            manifest.accounting = budget.counters()
            manifest.remaining_budget = budget.remaining()
            manifest.archived_bytes = sum(
                e.archive.raw.byte_length for e in manifest.entries if e.archive
            )
            manifest.logical_successful = sum(e.outcome == "success" for e in manifest.entries)
            manifest.retries_by_provider = {
                provider: sum(
                    max(0, e.attempts - 1)
                    for e in manifest.entries
                    if e.request.source_id == provider
                )
                for provider in ("ren", "esios", "entsoe", "open_meteo")
            }
            save_manifest(root, manifest, guards)
        if manifest.stop_category is not None:
            break


def run(
    args: argparse.Namespace,
    *,
    environment: Mapping[str, str] | None = None,
    now: Callable[[], datetime] = utc_now,
    transport_factory: Callable[[Budget], httpx.BaseTransport] | None = None,
) -> int:
    if not args.live and not args.replay_only:
        print('{"outcome":"live_authorization_required"}')
        return 2
    diagnostics = io.StringIO()
    configure_logging(stream=diagnostics)
    try:
        root = archive_root(args.archive_root)
        if args.replay_only:
            manifest = Manifest.model_validate_json((root / MANIFEST).read_bytes())
            replays(root, manifest)
            save_manifest(root, manifest)
            return 0 if all(e.replay == "equal" for e in manifest.entries if e.archive) else 3
        environment = os.environ if environment is None else environment
        targeted = getattr(args, "esios_boundary_only", False)
        providers = ("esios",) if targeted else ("esios", "entsoe")
        auths = [load_provider_auth(source, environment) for source in providers]
        guards = [
            PrivateRequestPolicy("https://localhost", auth, xml_character_references=True)
            for auth in auths
        ]
        if threading.current_thread() is not threading.main_thread() or signal.getitimer(
            signal.ITIMER_REAL
        ) != (0.0, 0.0):
            raise ConfigurationError("A free main-thread deadline timer is required")
        started = now()
        selections = esios_boundary_plan() if targeted else plan(started)
        for item in selections:
            item.adapter.transport_url(item.source)  # complete local query validation
        prepare_root(root)
        manifest = Manifest(
            run_id=uuid4(),
            started_utc=started,
            scope="esios_boundary" if targeted else "original",
            icon_target=None if targeted else selections[-1].source.request.delivery_date,
            logical_planned=1 if targeted else 7,
            logical_limit=1 if targeted else 8,
            attempt_limit=3 if targeted else 24,
            byte_limit=6291456 if targeted else 33554432,
            seconds_limit=120 if targeted else 900,
            entries=[
                Entry(
                    product=s.key,
                    logical_number=i,
                    request=s.request,
                    query_sha256=s.request.query_identity,
                )
                for i, s in enumerate(selections, 1)
            ],
        )
        save_manifest(root, manifest, guards)
        budget = (
            Budget(limits=Limits(logical=1, attempts=3, body_bytes=6291456, seconds=120))
            if targeted
            else Budget()
        )
        try:
            with hard_deadline(budget):
                execute(
                    root,
                    selections,
                    manifest,
                    budget,
                    environment,
                    guards,
                    now=now,
                    transport_factory=transport_factory,
                )
                if manifest.stop_category is None:
                    replays(root, manifest)
        except RunStop:
            manifest.stop_category = "wall_clock_budget_exhausted"
        manifest.ended_utc = now()
        manifest.accounting = budget.counters()
        manifest.remaining_budget = budget.remaining()
        save_manifest(root, manifest, guards)
        if any(guard.contains_credential(diagnostics.getvalue().encode()) for guard in guards):
            raise RunStop("sensitive_response")
        # Only this closed manifest summary is printed; managed logs stay in memory.
        print(
            json.dumps(
                {
                    "run_id": str(manifest.run_id),
                    "accounting": manifest.accounting,
                    "successful": manifest.logical_successful,
                    "stop": manifest.stop_category,
                    "results": {e.product: [e.outcome, e.replay] for e in manifest.entries},
                },
                sort_keys=True,
            )
        )
        return (
            0
            if manifest.logical_successful == len(selections)
            and all(e.replay == "equal" for e in manifest.entries)
            else 3
        )
    except ConfigurationError:
        print('{"outcome":"local_preflight_blocked"}')
        return 2
    except Exception:
        print('{"outcome":"controlled_safety_failure"}')
        return 3


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--replay-only", action="store_true")
    parser.add_argument("--esios-boundary-only", action="store_true")
    parser.add_argument("--archive-root", type=Path, required=True)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
