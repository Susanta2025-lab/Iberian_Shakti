# Phase 1 Stage 6 — Pre-live engineering audit

Audit date: 2026-10-26. Scope: current Stage 1–5 code and the prerequisites
for the future explicit OMIE smoke command. No live command was implemented
or executed. No external request, DNS lookup, browser, provider probe,
dependency download, or cloud action was performed.

## A. Objective

**This audit does not claim that local success guarantees live success.**
Its purpose is to eliminate detectable engineering defects before external
validation. Passing local tests, including this audit, does not prove provider
availability or compatibility with its current responses.

The existing [Phase 1 assessment](phase_1_readiness_assessment.md) remains
authoritative. This is a code-level defect audit, not another readiness or
architecture assessment. Read root `AGENTS.md`, README, architecture/ADR/runbook
catalogs, the assessment, Stage 2–5 reports, ADRs 0001/0002, implementation,
all Stage 3–5 integration tests, transport/boundary/redaction tests, the root
pytest network guard and `.pre-commit-config.yaml`. Inspected Git history and
the working tree before changes.

Four passes completed:

1. Static inspection of imports, concrete functions and their control flow.
2. Contract/runtime wiring and installed dependency API verification.
3. Adversarial offline execution, including real HTTP framing and real backend
   exception translation, beyond HTTPX MockTransport.
4. Operational simulation of acquisition, immutable persistence, parsing,
   repeated acquisition, replay, filesystem prerequisites and safe diagnostics.

## B. Repository state

| Item | Observation |
| --- | --- |
| Branch | Existing `main`; no branch created. |
| HEAD | `09e4890d83a560d1c0451aedc18a5cb21d8ec9ae`, `test: harden Phase 1 ingestion and offline enforcement`. |
| Initial working tree/index | Clean. |
| Reviewed history | Stage 5 `09e4890`, Stage 4 `fdb7098`, Stage 3 `e9bedab`, Stage 2 `b5092b5`, Stage 1 `1cab3c2`, assessment `559077e`. No fetch. |
| Final scope | Four modified production files, one new audit integration test module, this report; unstaged/uncommitted. |
| Python | Named pyenv environment `iberian_shakti`, Python **3.12.9**. |
| Actual interpreter | `/home/home/.pyenv/versions/iberian_shakti/bin/python`. |
| `which python` | `/home/home/.pyenv/shims/python`. |
| `which pytest` | `/home/home/.local/bin/pytest`; shebang `/usr/bin/python3`, Python 3.12.3. All reported pytest runs use `python -m pytest`. |
| HTTPX / httpcore | **0.28.1 / 1.0.9**. |
| Pydantic / pytest | **2.14.1 / 9.1.1** in the named environment. |
| Installation | Editable `iberian-shakti` 0.1.0 points to this repository's `src` package. |
| Dependency consistency | `python -m pip check`: no broken requirements. Versions satisfy `pyproject.toml`; Python `>=3.12,<3.13`, HTTPX `>=0.28,<1`, Pydantic `>=2,<3`, pytest `>=8.0`. |
| Lock state | No project dependency lockfile; this is the accepted environment model, not an introduced change. No upgrade/install performed. |
| Effective settings | Safely validated current settings: 3 attempts, 10-second phases, 1-second initial backoff, INFO. No environment contents or credentials printed. |

The four production paths changed are `contracts/ingestion.py`,
`common/logging.py`, `ingestion/http.py`, and `ingestion/runner.py`, beneath
`src/iberian_shakti/`. The new tests are
`tests/integration/test_pre_live_engineering_audit.py`. Fixture bytes, manifest,
ADRs, prior reports, dependency declarations and hook configuration are unchanged.

## C. Actual planned live execution path

`ingestion/omie/live_smoke.py` does **not yet exist**. The following distinguishes
the required future wrapper from the actual callable production components
verified here; it does not claim an existing CLI has been validated.

```text
future main(): parse/validate date, revision and archive-root arguments
  -> require --live
  -> load/validate IngestionSettings, request and calendar preflight
  -> configure_logging; create fresh retrieval/parse UUIDs
  -> RetryPolicy.from_settings; OmieAdapter; LocalRawArchive
  -> HttpRetriever(download_url, resolve_listing_url=listing_url,
       classify_unavailable=adapter.classify_unavailable, retrieval_event_id=...)
  -> ingest(..., listing_retriever=retriever, retriever=retriever,
       parser=adapter.parser, archive=archive, parse_event_id=...)
     [omit parsed_at to capture actual parse-start time]
  -> OmieAdapter.resolve
     exact: resolved_source, no listing acquisition
     latest: HttpRetriever.retrieve_listing -> bounded listing interpretation
  -> HttpRetriever.retrieve -> _url -> _acquire
  -> DeadlineTransport -> httpcore.ConnectionPool -> DeadlineBackend
  -> installed SyncBackend / SyncStream -> external socket/TLS boundary
  -> HTTP response classification and iter_raw complete-body acquisition
  -> result_for: SHA-256 / RawPayload / RetrievalProvenance
  -> persist_retrieval -> LocalRawArchive.persist: payload, retrieval event
  -> OmieParser.parse -> intervals_for -> market_day_intervals
  -> ParseResult -> LocalRawArchive.persist_parse
  -> IngestionResult (or an explicit unresolved ResolutionResult)
  -> future CLI allowlisted summary and distinct outcome/exit handling
```

Boundary audit (types are the existing contracts, not invented CLI DTOs):

| Caller → callee | Input → output | Error boundary | Retry / persistence / network ownership |
| --- | --- | --- | --- |
| Future CLI → settings/request/calendar | Parsed scalars → `IngestionSettings`, `SourceRequest`, intervals | `ConfigurationError`, sanitized `ValidationError`, configuration `ExecutionError` | No retries/network; settings and constructors do not create archives. |
| `ingest` → `OmieAdapter.resolve` | `SourceRequest`, `ListingRetriever` → `ResolutionResult` | Typed absence/coverage/schema/acquisition codes; invalid caller request can raise validation/execution error | Adapter selects only; no archive. Network only via listing capability. |
| Adapter → `HttpRetriever.retrieve_listing` | `ListingRequest` → `ListingResult` | Stable acquisition codes or `ExecutionError` | One bounded acquisition; no report identity or persistence fabricated. |
| `ingest` → `HttpRetriever.retrieve` | `ResolvedSource` → `RetrievalResult` | Stable outcome/error codes; invalid locator raises `ExecutionError` | Retriever alone owns application retries; no persistence. Network possible. |
| Retriever → `DeadlineTransport.handle_request` | `httpx.Request` → streamed `httpx.Response` | httpcore errors translated to HTTPX errors, then safe execution codes | Pool retries zero; no redirects, no archive. External I/O boundary. |
| Retriever → `result_for` | Complete bytes, status, observations, UTC time → validated raw/retrieval models | Model invariants, SHA/length verification | No retry/network/archive; original bytes preserved. |
| Runner → `persist_retrieval` → archive | Payload/provenance → archive-linked `RetrievalResult` | `ArchiveError`, stable archive/integrity/path reason | Owns raw and retrieval-event writes; outside retry loop; no network. |
| Runner → `OmieParser.parse` | Archived `RawPayload`, retrieval, parse UUID/time → `ParseResult` | Typed content/encoding/integrity failure with zero records; missing timezone is a configuration exception | No retries or I/O; parser validates date/filename and whole report. |
| Parser → calendar/helper | Delivery date → tuple of UTC `MarketInterval` | Missing IANA data translated to configuration `ExecutionError`; invalid calendar partition is visible | Generic policy; no network/persistence. |
| Runner → `persist_parse` | `ParseProvenance` → `None` only after persistence | `ArchiveError` | Separate immutable event; verifies raw and original retrieval; no network/retry. |
| Runner → result / future summary | Archived retrieval and parse → `IngestionResult` | Contract linkage validation; unresolved selection stays a `ResolutionResult` | Success returns only after required writes. Future CLI must summarize enums/scalars, not dump models/causes. |

### Imports, environment, packaging and state

All package `__init__.py` files are empty. Module-level code defines models,
regular expressions, constants, logger handles, TypeAdapters and a ContextVar.
A fresh `python -B` process imported **all 32 production modules** under an
audit hook denying filesystem mutations, environment mutations and socket
events, with DNS APIs and HTTPX client constructors replaced by rejection
functions. All imports and settings/retriever/archive construction succeeded;
environment contents were unchanged. Ordinary import/dependency file reads
are allowed; no archive, client, handler or network connection is created by
application imports.

`HttpRetriever.__init__` only validates/stores arguments. The default transport
and client are created inside `_acquire`, after execution begins. Explicit
`DeadlineTransport()` creates a verified SSL context and pool; this reads local
trust material but does not connect, resolve DNS or create an archive. No
production private HTTPX/httpcore attribute or import is used.

`load_ingestion_settings` reads exactly five named ingestion/log settings from
an explicit mapping or `os.environ`. It never loads `.env` or reads ESIOS,
ENTSO-E, Snowflake, Azure/AWS/GCP or OMIE credentials. Existing Stage 5 tests
also run ingestion beside an invalid `.env` without provider variables. The
public OMIE path has no credential dependency.

Editable package discovery includes `ingestion/omie`. The future module will
resolve once its file is implemented; this audit did not run that module or
add a skeleton. A fresh application process imported no test conftest.
`tests/conftest.py` installs denial in `pytest_configure`, before collection,
and undoes it in `pytest_unconfigure`. No production module imports tests or
installs a persistent network monkeypatch. Existing guard tests remain active.
The new harness replaces denied socket creation with an entirely in-memory
function during individual tests; DNS remains denied and no real descriptor
is created.

Immutable models/constants have no cross-run revision/archive state. The
adapter's class-level `OmieParser` instance has no mutable operational fields;
parser versions are constant strings, not cached results. Retrievers and event
UUIDs are per acquisition. Deadline ContextVar tokens reset in `finally`.
Clients/pools are per logical acquisition; no global cached HTTP client exists.
Repeated exact/discovery/replay tests show no cross-run contamination.

### Future CLI inputs and authorization ordering

The four proposed arguments are sufficient: `--live`, required ISO delivery
date, optional positive integer revision, and archive root. No token, base URL,
cloud configuration or additional switch is needed. UUIDs, UTC completion and
parse clocks, parser and retry defaults are internal runtime dependencies.
Validate source/calendar compatibility before network execution, including
availability of `Europe/Madrid`; do not substitute the current day.

Required ordering is parse arguments → validate their syntax/ranges → require
`--live` → validate effective settings/request/calendar and configure safe
logging → construct dependencies → invoke runner. Reject missing authorization
before the first possible acquisition; no DNS/client/archive work belongs in
argument parsing. Constructors are safe, but placing them after the gate keeps
the boundary explicit. CLI archive-root input must override the corresponding
validated setting. The CLI must omit `parsed_at` so the corrected runner captures
it after persistence. No future CLI exit-code numbers are implemented here.

## D. HTTP transport review

Inspected installed HTTPX/httpcore source and signatures locally, including
`Client`, `Request`, `URL`, `Response`, `ConnectionPool`, `NetworkBackend`,
`NetworkStream`, `SyncBackend.connect_tcp`, and `SyncStream.start_tls`.
`httpcore.URL(scheme, host, port, target)` uses keyword arguments matching 1.0.9;
`Request` receives method, raw URL target, raw headers, iterable request stream
and timeout extensions. Both positional backend/stream delegations match the
installed signatures. Real default construction is valid for HTTPX 0.28.1.

`DeadlineTransport` uses public exported interfaces. `_http_transport.py` is
our private module name, not use of a library's private API. The tests inspect
installed implementation behavior but production does not patch it. httpcore
is the installed required HTTPX dependency; no dependency upgrade was needed.
Compatibility must be rechecked after future upgrades; the broad accepted
ranges are not a claim about every future release.

TLS uses `ssl.create_default_context()`, hostname checking and `CERT_REQUIRED`.
No proxy/environment credentials are passed: HTTPX has `trust_env=False`.
Redirect following is false with zero redirect allowance. The pool uses
`retries=0`, defaults to HTTP/1.1 and has no second retry layer. Only GET is sent.

`client.stream` keeps responses unconsumed. `ResponseStream` delegates the
httpcore body iterator and close method, translating core exceptions both
while acquiring headers and while iterating/closing. `Response.iter_raw()`
removes transfer framing through h11 but never decompresses content codings
or decodes text. No `.text`, `.content`, `read()` or `iter_bytes()` is used for
raw acquisition. Preconsumed mock responses fail closed, rather than trusting
possibly decompressed bytes.

The new harness executes default `HttpRetriever` construction without injecting
a transport. Only `socket.create_connection` and `SSLContext.wrap_socket` are
replaced; actual SyncBackend, SyncStream, httpcore, h11 and HTTPX execute.
It verifies TLS-context flags/SNI, canonical GET target and headers, timeout
arguments, complete framing, closed sockets and full runner persistence.
Neither real TLS negotiation nor socket/network success is established.

HTTPX client and response context managers close on success, status failure,
stream error, deadline and encoding exception. Each attempt's partial bytearray
is discarded. Archive/parser errors happen after client closure. Pools close
with their client. Files and staging descriptors use context managers, directory
fds close in `finally`, staging paths are removed on ordinary failure. The
focused suite also ran with resource warnings promoted to errors. This is
local cleanup evidence, not a guarantee against process kill or OS failure.

## E. OMIE exact URL review

For delivery date **2026-10-26**, revision **1**, actual `resolved_source` and
`download_url` produce, without sending anything:

```text
filename:     marginalpdbc_20261026.1
safe locator: omie/marginalpdbc/marginalpdbc_20261026.1
URL:          https://www.omie.es/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.1
raw target:   /en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.1
```

Scheme HTTPS; hostname `www.omie.es`; effective port 443; path
`/en/file-download`; exactly one `parents=marginalpdbc` and one `filename`.
`urlencode` encodes query values once. The selected filename contains only
safe ASCII and its dot remains canonical. No userinfo, fragment, additional
slash, duplicate parameter or secret exists. Identity validation checks
request/source/report/date/revision/filename/locator agreement before mapping.
Generic `_url` independently rejects non-HTTPS, missing hosts, userinfo and
fragments. The real local HTTP framing tests assert the exact request line.
This corresponds to accepted ADR 0001, not newly observed provider behavior.

## F. OMIE discovery route review

```text
safe locator: omie/marginalpdbc/listing
URL:          https://www.omie.es/en/file-access-list?realdir=marginalpdbc
raw target:   /en/file-access-list?realdir=marginalpdbc
```

The listing mapper accepts only the defined safe listing locator. Route/origin
and query match the accepted family listing. One logical page acquisition only;
no second page, crawler, revision probing or `.1` fallback exists. Limits are
**1 MiB** listing bytes and **10,000** anchor candidates, with independent
adapter checks. Report limit is **4 MiB**. Redirect bound is zero.

Only closed download tables and validated same-origin `/en/file-download`
anchors with exactly the two required query fields can select reports.
Rejected origins, userinfo, fragments, duplicate query fields, malformed dates,
unsafe paths and wrong families cannot select a revision. Revisions are compared
numerically; `.10` beats `.9`. Pagination/partial/unrecognized content produces
coverage/schema outcomes, never historical absence or another page request.
The synthetic listing proves our bounded grammar/wiring only; live DOM and
coverage remain external uncertainties.

## G. Contract/wiring audit

`SourceAdapter.resolve(request, ListingRetriever)` is coherent. One real
`HttpRetriever` implements both `retrieve_listing(ListingRequest)` and
`retrieve(ResolvedSource)`. The runner accepts both capabilities explicitly;
the same object was passed for both in the default-transport simulations.
Listing construction needs no resolved report, so there is no circular
resolution/retrieval dependency. Exact resolution never invokes listing.
Only the selected report gets raw/acquisition identity; listing HTML remains
ephemeral, excluded from repr/metadata and never archived as a report.

`LocalRawArchive` implements persist/load/load_retrieval/persist_parse;
`OmieParser` satisfies the shared parser signature. Mypy checks concrete runtime
composition in production. Runtime tests exercise real objects rather than
using Protocol runtime introspection (the protocols are structural, not marked
`runtime_checkable`). No test-only resolver, alternate parser or archive is
needed for a live run.

Fixture-to-live equivalence is now exercised through the actual **default**
transport as well as existing MockTransport integration. The original fixture
`tests/data/omie/marginalpdbc_20261026.1` becomes a raw HTTP response body,
then follows production hashing, metadata, immutable archival, parser and
calendar code. Its 2,637 bytes and SHA-256
`5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e`
are preserved. Filename/date/revision come from the actual resolver, never the
fixture path. Real transport creates an unconsumed stream; content observations
and archive linkage reach the same parser preconditions as live acquisition.

The calendar selects modern policy generically for dates from 2025-10-01:
15-minute MTU, **96 periods / 192 records / 96 PT / 96 ES** on 2026-10-26.
Europe/Madrid local midnights separately convert to 2026-10-25 23:00 UTC and
2026-10-26 23:00 UTC. No special case for this date exists. Synthetic machine
TZ tests (UTC/New York/Kolkata), existing ordinary/DST/profile-transition tests
and real parser integration confirm the CLI delivery date remains authoritative.
Source dates must match the report; retrieval/parse clocks are UTC-aware.
Naive/non-UTC provenance timestamps are rejected by the contracts.

## H. Mock-vs-real risk review

| Fake/controlled input | Live replacement / what it cannot prove | Local real implementation exercised |
| --- | --- | --- |
| In-memory socket creation, receive/send/close | OS resolver/TCP socket; cannot prove routing, DNS, certificate exchange, real stalls or connectivity | Actual default DeadlineTransport, SyncBackend, SyncStream, core/h11/HTTPX framing and exception mapping. |
| TLS wrap returning a fake stream, or raising an SSL verification error | Real SSL handshake; context flags alone do not prove provider trust/negotiation | Actual verified context construction, hostname parameter, TLS failure chain and closure. |
| Synthetic HTTP/listing/status bytes | Current provider responses and HTML structure | Actual response parser, listing adapter, resolver, retry, archive and OMIE parser. |
| Controlled monotonic clock/sleeper and UTC clocks | OS clock, scheduling and sleep behavior | Real deadline/retry arithmetic, shrinking timeout propagation and oversleep checks. |
| MockTransport for the isolated exposed `httpx.WriteError` regression | Any supplied HTTPX transport that surfaces that public exception | Classification boundary; default GET core behavior is separately inspected/tested. |
| Temporary archive root and injected link permission fault | Operator filesystem and actual disk faults | Actual archive writes/fsync/link/hash checks and error translation. |

No fake archive, parser, runner, contracts, identity or calendar is used in the
new full-path tests. Existing spies wrap real components. The socket double
could accept a call a real socket rejects; running actual installed backend
methods, canonical request assertions and TLS-context checks reduces this risk
without pretending to test actual TLS. No live result was inferred from it.

## I. Retry/request-count analysis

The default and currently validated effective policy is **three total attempts**.
Backoff is exactly **1 then 2 seconds**, capped at 4 for explicitly configured
larger attempt limits. No fourth default attempt, HTTPX/httpcore retry,
automatic redirect, rediscovery loop, retry around parsing, or publication
polling exists.

| Mode | Successful first-attempt logical acquisitions | Maximum physical HTTP request attempts under current/default policy |
| --- | --- | ---: |
| Exact | One report, zero listings | **3** |
| Latest observed | One listing plus one selected report | **6** |

A connection failure may prevent transmission of an HTTP request, so these are
upper bounds. Actual default-transport simulations hit all six allowed attempts
(two failed listing attempts, listing success, two failed report attempts,
report success) with sleeps `[1, 2, 1, 2]`. Exact mode reached three failures or
success within three. A listed report's 404 ends that run without rediscovery.
Parser/archive/replay contain no transport dependency that can add requests.

`INGESTION_MAX_ATTEMPTS` is an accepted operator override, not an immutable
hard cap of three for every possible configuration. If changed to N, the
attempt ceilings become N and 2N, subject to each operation budget. The future
CLI must use/identify the validated effective policy; no new switch is needed.

## J. Timeout/budget analysis

Defaults: **10 seconds** each connect/read/write/pool phase, **30 seconds** per
attempt, **93 seconds per logical acquisition**, including backoff/Retry-After.
Discovery and report use separate budgets, giving at most **186 seconds of
acquisition budget**; there is no 93-second whole-ingestion deadline. Local
parsing/archive operations are outside that acquisition budget.

`_acquire` records a monotonic operation deadline before transport construction.
Before every attempt it checks the remainder; attempt deadline is the minimum
of operation deadline and now + 30. HTTPX phase timeouts clamp to the attempt
remainder. The ContextVar passes this deadline/clock into `DeadlineBackend` and
`DeadlineStream`, which recompute remaining time before connect/TLS/read/write
backend operations. `_read` checks after each raw chunk and after EOF. Bytes
received after the deadline never become an acquired report.

Backoff consumes the operation budget. A required delay must be strictly less
than the remainder; equality/excess ends the operation. A sleeper overshoot
cannot start another request. Supported Retry-After is a nonnegative integer
number of seconds; use at least the exponential wait, and never truncate a
provider's minimum to fit. Enormous integers saturate before float conversion.
HTTP-date Retry-After is an accepted documented unsupported subset and uses
bounded fallback; no date parsing or long polling was added.

Existing fake-clock tests execute phase clamping, slow body chunks, repeated
short header/body reads inside core, deadline exhaustion before first attempt,
retry recovery, backoff/Retry-After equal/above/below remaining budget and
oversleep. New default-path tests verify finite socket timeouts and real
exception translation. No wall-clock sleeps are needed in those tests.

**Documented limitation:** synchronous deadlines are cooperative accounting,
not process-level preemption. Host DNS resolution, OS calls and work internal
to a backend/TLS/socket operation can exceed a requested timeout. An injected
backend must honor its timeout contract; the wrapper checks each delegated
operation and later body boundary, not every internal instruction. No claim
of hard real-time cancellation is made. The existing host/backend limitation
remains; no worker or new infrastructure was introduced.

## K. Archive/persistence audit

Success ordering in `runner.ingest` is:

```text
complete acquisition and verified raw contract
→ publish immutable payload and verify it
→ publish acquisition JSON with ArchiveReference
→ return archive-linked retrieval
→ capture parse-start time / invoke actual parser
→ verify acquisition and persist separate parse JSON
→ assemble and return IngestionResult
```

A malformed complete 200 follows the same ordering, producing an archived
payload, successful retrieval event, separate failed parse event and **zero
records**, without HTTP retry. A truncated file with otherwise complete HTTP
framing is archived and fails content validation. An interrupted HTTP body is
discarded and may retry; no partial raw object is published. Archive errors
cannot return success or reenter acquisition. Failure after raw publication
may leave a recoverable complete orphan, never a fabricated successful history.

Absolute roots are supported: only paths *beneath* the trusted configured root
are required to be safe relative references. `/tmp/iberian-shakti-omie-smoke`
was created locally, with a temporary synthetic archive beneath it. Two
acquisitions reused one payload and retained two retrieval/two parse events.
Temporary probe directories were removed, including the audit-created smoke
root. No fixture storage or repository object was modified by the probe.

Safe local probes under both the repository filesystem and `/tmp` verified
hard links with matching inodes, FileExistsError on duplicate publication,
file and directory fsync, and 0444 mode setting. Both reported device **2096**;
no relevant difference was observed on this WSL workspace. Staging is on the
destination filesystem. Publication uses `os.link` with no replacement;
existing objects are compared and hash/length verified. Existing concurrency,
fault/recovery and staging tests also pass. Assumptions remain a trusted local
tree and hard-link/fsync support, not hostile-user/WORM/network-storage safety.
Process kill can leave private staging files; ordinary exceptions clean them.

Replay requires archive reference and original retrieval UUID only. It verifies
SHA/length, reads original provenance including filename/date/encoding, and
needs no live URL, DNS or retriever. A new parse event may be persisted;
original raw/acquisition bytes remain unchanged. A replay test forbids HTTP
client construction. Repeat acquisitions retain deterministic normalized
values/content identities while using fresh acquisition/parse UUIDs.

Same filename/revision is never assumed to mean same bytes. Stage 5's four-way
revision/content matrix still executes; differing content gets a new hash
object, with prior payload/inode/events preserved. The future summary can
report hash, count, profile and parse outcome; fixture comparison is a local
structural observation, not a reason to rewrite fixture bytes. The live module
must never update the fixture or its manifest.

## L. Logging/diagnostic sufficiency

A concrete deficiency was corrected: response failures did not log status,
phase reason or elapsed time, and listing acquisition had no target context.
Discovery then returned only an aggregate error code, losing the distinctions
needed to diagnose the first listing failure.

Acquisition success/unavailability/failure/retry events now include applicable
attempt, HTTP status, monotonic elapsed seconds, byte count, stable error code
and controlled `FailureReason` value. Listing events identify their opaque safe
locator. Report events carry source/report/date/filename/revision. Archive events
supply SHA-256, byte count and safe relative archive reference; parser events
supply parser version, outcome and record count. SHA is available only for a
complete body, never claimed for an interrupted attempt.

The formatter adds only bounded safe `reason` and relative `safe_locator` fields
to its existing scalar allowlist. Call sites supply enums and validated opaque
locators, never upstream exception strings. HTTPX/httpcore logging remains
restricted and formatted by the explicitly configured application handler.
No raw payload, listing HTML, arbitrary headers, rejected input, query URL,
userinfo, token, traceback or unchecked library/OS error text is emitted.
Existing secret/redaction tests and new realistic failure tests pass.

### First-call error/evidence matrix

For rows marked retry, at most three attempts apply and budgets may stop sooner.
No HTTP-error page or incomplete body is archived as a successful report.

| Failure | Stable category / safe reason or outcome | Retry | Archive/evidence and future operator outcome |
| --- | --- | --- | --- |
| DNS failure | `transport_failure` / `connection_failure` | Yes | No raw object; attempt/time/category logs; acquisition failure. DNS and TCP intentionally share the safe connection category. |
| TCP connection failure | `transport_failure` / `connection_failure` | Yes | Same; separate from bad locator/TLS/content. |
| Connect timeout | `timeout` / `connect_timeout` | Yes | No raw; phase/attempt/time visible. |
| Read timeout | `timeout` / `read_timeout` | Yes | Attempt bytes discarded; phase/attempt/time visible. |
| Write/pool timeout | `timeout` / `write_timeout` or `pool_timeout` | Yes | No successful payload; existing timeout tests retained. |
| Exposed HTTPX WriteError | `transport_failure` / `connection_failure` | Yes | Corrected generic transport mapping; safe GET bounded retry. See N for core GET suppression behavior. |
| TLS validation failure | `tls_failure` / `tls_verification_failure` | No | Actual core/HTTPX SSL cause chain exercised; one attempt; no raw. |
| HTTP 404 on report | `unavailable` / `not_found` | No | No raw/parse; date/revision/status retained; explicit unavailable, not success. |
| HTTP 403 / other permanent 4xx | `http_failure` / `http_failure` | No | Status/target/attempt logged; explicit acquisition failure. |
| HTTP 429 | `rate_limited` / `rate_limited` | Bounded | Status and attempts; valid delta wait respected or explicit exhaustion. |
| HTTP 500/502/503/504 | `http_failure` / `http_failure` | Yes | Final status, attempts and exhausted outcome visible. |
| Redirect | `http_failure` / `http_failure` | No | Status visible; no follow or body iteration, no leaked Location URL. |
| HTML or empty complete 200 | `content_failure` / `content_invalid` | No | Exact complete body, retrieval event and zero-record parse event preserved. |
| Truncated report, complete HTTP | `content_failure` / `content_invalid` | No | Full received bytes archived; strict grammar/terminator/day checks reject it. |
| Premature HTTP EOF / bad framing | `incomplete_body` / `incomplete_transport` | Yes | No partial payload; real h11 rejects incomplete/conflicting framing. |
| Unsupported valid content coding | `content_failure` / `unsupported_encoding` | No | Encoded raw bytes/observation and failed parse preserved, including valid coding-list whitespace. |
| Invalid/unrepresentable encoding metadata | `unsupported_encoding` exception | No | No claimed successful raw report; safe encoding/status/attempt log. Existing bounded metadata policy remains. |
| Parser schema/date/period mismatch | `content_failure` / `content_invalid` | No | Complete raw/acquisition and failed parse persist, zero records; safe outcome distinguishes content from acquisition. |
| Oversized body | `size_limit` | No | No successful payload; size reason and status when available. |
| Archive/persistence fault | `ArchiveError`, `archive_failure` or `integrity_failure`, closed reason | No | No ingestion success; completed earlier objects remain; future CLI must log enum code/reason and fail. |
| Listing schema/pagination/coverage mismatch | `discovery_schema` or `coverage_unknown` | No content retry | No report request/parse; explicit resolution outcome, safe listing context; no raw HTML dump. |

This evidence distinguishes acquisition, provider status, content rejection,
configuration and local storage failures without unsafe raw dumps. DNS vs TCP
root causes and precise parser row diagnostics are intentionally not free-text
logs. Archived complete bodies allow local parser investigation/replay. A
future CLI can map typed results and `ExecutionError`/`ArchiveError`, plus
sanitized settings/request validation, without parsing exception messages.
Unexpected programming exceptions must yield a static safe failure summary;
chained internal request objects must not be printed. CLI handling is Stage 6
implementation work, not an existing feature claimed here.

## M. Offline full-path simulation

New test module: **49 passing cases**, with actual default transport and real
production components as described in H. The following required manual-style
scenarios execute there as deterministic tests:

| Scenario | Observed result / acquisition attempts |
| --- | --- |
| 200 valid original report | 192 records; raw/retrieval/parse persisted; 1. |
| 404 exact report | Explicit not_found unavailable; no raw/parse; 1. |
| 503 then valid report | Success; one 1-second fake wait; 2. |
| Three 503 responses | Retry exhausted; no raw/parse; 3, waits 1/2, no fourth. |
| Read timeout then valid report | Real SyncStream/core/HTTPX translation, then success; 2. |
| HTML 200 | Archived; content_invalid, zero records; 1. |
| Complete HTTP carrying truncated report | Archived; content_invalid, zero records; 1. |
| Unsupported Content-Encoding | Exact encoded bytes archived; unsupported_encoding parse; 1. |
| Archive link permission failure | Typed ArchiveError; no ingestion success, no retry/staging leak; 1. |
| Parser schema failure | Actual parser rejects changed header after archival; zero-record parse event; 1. |
| Compatible listing then report | Actual shared retriever resolves numeric revision 10 over 9; 192 records; 2. |
| Incompatible listing | discovery_schema; zero report requests; 1. |
| Compatible listing then report 404 | Selected revision retained; not_found, no rediscovery; 2. |

Additional cases cover empty 200, wire EOF, DNS/connection/connect/read/TLS
failure translation, 403/429/500/502/503/504/redirect logging, identity/case and
stacked encoding, absent/exact/duplicate-equal Content-Length, chunked framing,
repeat acquisition/replay, six-attempt discovery ceiling, host timezone changes,
parse-time capture, safe-field rejection and transport construction/closure.
Conflicting lengths, incomplete chunks, slow reads, fake-clock boundary cases,
metadata faults, revisions/mutations and independent parse persistence remain
covered by the retained Stage 3–5 suites.

## N. Test-overfitting findings

- Stage 3–5 core tests inject MockBackend or NetworkBackend doubles; their
  previous full OMIE integrations injected MockTransport. This left default
  backend construction/real exception translation outside the full provider
  stack. The new socket-boundary harness closes that concrete local coverage
  gap. No invalid constructor or private-API dependency was found.
- MockTransport can construct preconsumed `Response(content=...)` objects;
  production retrieval explicitly rejects them. Realistic retriever tests use
  streams. A separate guard test's preconsumed response tests MockTransport
  itself, not ingestion success.
- Duplicate Content-Length is different at the two seams: HTTPX mocks expose
  a combined string and fail closed, whereas h11 normalizes equal lengths and
  rejects conflicting ones. Real framing coverage confirms correct behavior;
  mock behavior was not mistaken for provider behavior.
- Real SyncBackend maps OS and SSL errors into core exceptions; new tests inject
  errors beneath that boundary rather than only raising hand-picked HTTPX types.
  Chained SSL validation errors remain permanent.
- The exposed public HTTPX WriteError mapping was incomplete. **Nuance:** installed
  core HTTP/1.1 deliberately suppresses a write error while sending a GET and
  attempts to read a possible server response. Thus a MockTransport WriteError
  alone does not prove that the default live GET will expose that exact error.
  The small mapping correction is a generic boundary defect, classified
  non-blocking below; it is not evidence of invalid default construction.
- Valid `Content-Encoding: GZIP , BR` survived real h11 framing but failed our
  metadata regex before raw archival. This was a real contract defect hidden
  by narrower existing header examples; regression now verifies archival and
  explicit later parser rejection.
- Existing fixtures/listings remain labelled original or synthetic. Synthetic
  listing compatibility cannot verify today's live DOM. Default-path tests
  use canonical production URL mapping and resolver-supplied filenames.

## O. Defects found

Severity describes the finding **before correction**. All listed fixes were
re-audited offline; no known blocker remains.

| Severity | Finding | Root cause | Fix | Regression test |
| --- | --- | --- | --- | --- |
| BLOCKER | Discovery HTTP failures lost status/target and timeout-phase evidence needed to diagnose a first call. | `_acquire` failure/retry logs omitted status/reason/elapsed/attempt in several branches; listing passed empty context and resolution retained only the aggregate code. | Add safe listing locator, controlled reason and applicable status/attempt/elapsed to existing events; extend formatter only for those two safe fields. No raw diagnostics. | `test_default_status_outcome_and_safe_diagnostics`, `test_real_sync_exception_translation`, `test_discovery_failure_keeps_diagnostic_status`, safe-field rejection and retained redaction suite. |
| NON-BLOCKING DEFECT | An exposed `httpx.WriteError` was reported as invalid locator. | Public transport classification lacked WriteError despite translating core WriteError. | Map to bounded retryable transport_failure/connection_failure; SSL-chain detection remains first. | `test_httpx_write_error_is_connection_failure`; default core nuance documented in N. |
| BLOCKER | Planned direct runner call had to capture a purported parse time before acquisition. | Required `parsed_at: datetime` evaluated at CLI call time, preceding potentially long retrieval; no default just-in-time parse clock. | Compatible optional `parsed_at` default captures UTC immediately after raw/retrieval persistence and before parser. Explicit deterministic callers unchanged. | `test_default_parse_time_is_captured_after_acquisition_persistence`: delayed acquisition, persisted retrieval present when clock is read, parse time after completion. |
| BLOCKER | A valid coding list with whitespace before comma lost complete-body archive evidence. | `HttpObservations` regex accepted OWS only after a comma, although real framing preserves legal pre-comma whitespace. | Widen whitespace placement only; retain token/total length bounds, ordered raw metadata, no decompression and unsupported-encoding parser outcome. | `test_default_encoding_raw_preservation[GZIP ,\tBR]` through real default transport/framing/archive/parser. |

Before the first corrections, the new harness had **14 demonstrated assertion
failures / 33 passing cases** after correcting a harness binding mistake.
The new default parse-time test separately failed on the missing required
argument, and the whitespace-encoding test failed at the real metadata boundary
(1 failed / 6 encoding cases passed). These were not failures of OMIE service.
After correction all **49** new cases and the full existing suite pass. Existing
tests were neither deleted nor weakened. Contract widening is backward compatible;
no persisted field, version, identity, parser grammar or archive layout changed.

## P. External uncertainties remaining

Only actual external observation can establish:

- Current OMIE endpoint availability, network routing/DNS, real TLS negotiation
  and provider certificate/trust behavior on the operator host.
- Current listing HTML, pagination/coverage and retention compatibility with
  the intentionally bounded one-page grammar.
- Actual report status, body/schema, date/revision availability and response
  headers/content coding, including intermediary-added encoding.
- Whether a remote filename/revision now has bytes different from the retained
  fixture or changes between listing and acquisition.
- Undocumented provider-side access/format changes and response behavior.

Previously accepted limitations remain: strict supported ASCII/numeric grammar,
two market profiles, incomplete historical/revision coverage, no publication
SLA inference, integer-only Retry-After, cooperative deadlines and trusted
hard-link/fsync filesystem semantics. Unverified legacy-format history is not
a blocker for this modern exact-day attempt. These are documented limitations,
not newly invented engineering failures or guarantees.

## Q. Validation evidence

All validation is offline in the named Python 3.12.9 environment.

| Command / inspection | Result |
| --- | --- |
| `python -m pytest tests/integration/test_pre_live_engineering_audit.py -q -W error::ResourceWarning` | **49 passed**, no skips/failures/resource warnings. |
| `python -m pytest tests/unit/ingestion tests/integration tests/unit/test_offline_guard.py -q -W error::ResourceWarning` | **655 passed**, no skips/failures/resource warnings. |
| `python -m pytest` | **952 passed**, no skips/failures; all 903 baseline cases retained plus 49 audit cases. |
| `ruff check .` | All checks passed. |
| `ruff format --check .` | 74 files already formatted. |
| `mypy src` | Success: no issues found in 32 source files. |
| `git diff --check` | Clean. |
| `pre-commit run --files <six changed paths>` | All applicable hooks passed: Ruff check/format, whitespace, EOF, large-file and private-key checks; YAML/TOML skipped because no changed matching paths. Cached environments used, no download or escalation needed. |
| Fresh-process import audit | 32 production modules; no application import-time network/DNS, filesystem writes, environment mutation, archive creation or HTTPX client construction. |
| Local filesystem/archive probe | Both filesystems: hardlink/no-replace, file/directory fsync, chmod; temporary absolute-root archive reuse/events verified and removed. |
| Fixture integrity | Manifest/inventory test passes; data fixture/manifest/hook configuration diff against HEAD is empty. |

No dependency was downloaded. Cached pre-commit environments are already present;
no hook initialization or remote lookup is authorized. Final diff review includes
the new untracked test/report because ordinary Git diff omits them. Nothing is
staged, committed or pushed. No Stage 6 CLI, Stage 7, provider expansion or
infrastructure work is included.

## R. Live-call readiness verdict

**GO — NO DETECTABLE ENGINEERING BLOCKER**

The exact and bounded discovery prerequisites are coherent; real installed
transport construction, URL mapping, retry ceilings, persistence ordering,
parser/calendar behavior and safe diagnostic boundaries have been exercised
locally. The four detected defects are corrected, all quality checks/tests pass,
and default pytest remains offline. Stage 6 still must implement its small,
explicitly authorized CLI according to the ordering in C; no external execution
is authorized by this report alone.

This verdict means the locally detectable engineering path is ready for a live
attempt. It does not predict or guarantee provider-side success.
