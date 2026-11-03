# Runbook: Local OMIE ingestion and replay

Applies to the implemented Phase 1 local workflow. Phase 1 is CLOSED/PASS;
Phase 2 is in progress; REN acquisition and provisional empirical source-period
UTC normalization and ESIOS indicator 544 offline integration are implemented.
ENTSO-E and Open-Meteo remain pending.
There is no scheduler or deployed production service.
Last verified offline: 2026-11-03 (ESIOS Stage 3 and existing regressions). Live evidence is the historical
[Stage 6 report](../codex/reports/phase_1_stage_6_live_validation.md);
Stage 7 made no provider request.

## Prerequisites and settings

Run from the repository root in the existing pyenv environment `iberian_shakti`
(Python 3.12), with the declared dependencies installed and host IANA timezone
data providing `Europe/Madrid`. OMIE uses the public anonymous `marginalpdbc`
route and requires no ESIOS, ENTSO-E or Snowflake credentials.

`load_ingestion_settings()` reads only these exported environment variables
(or an explicitly injected mapping). It does **not** load `.env`; copying
`.env.example` does not configure a process. Invalid settings fail validation
before acquisition; no archive is created by settings construction.

| Variable | Default | Meaning |
| --- | --- | --- |
| `RAW_ARCHIVE_ROOT` | `data/raw` | Archive root, relative to the process working directory unless absolute. The live CLI's required `--archive-root` overrides it after settings validation. |
| `INGESTION_TIMEOUT_SECONDS` | `10` | Positive finite connect/read/write/pool phase timeout. |
| `INGESTION_MAX_ATTEMPTS` | `3` | Positive total attempt count, including the first attempt. |
| `INGESTION_BACKOFF_SECONDS` | `1` | Finite nonnegative initial exponential backoff. |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR or CRITICAL for explicit library logging setup. |

Library entry points may call `common.logging.configure_logging()` explicitly;
imports do not configure handlers. Use the managed JSON formatter and controlled
event fields. Never dump payloads, models, raw headers, rejected validation
inputs, unchecked exceptions or transport URLs into logs. The live CLI emits
an allowlisted JSON outcome summary; it does not configure this logging handler.

## Default offline validation

```bash
python -m pytest
```

The repository-wide guard denies DNS, outbound socket operations and real
HTTPX sync/async transports from pytest configuration through collection and
execution. MockTransport, fake backends and local fixtures remain usable.
There is no environment variable, marker or pytest option enabling live access.
The guard prevents accidental Python network use; it is not an OS sandbox for
independent subprocesses/native code.

Full local quality gates are `ruff check .`, `ruff format --check .`,
`mypy src`, `python -m pytest` and `git diff --check`. Run applicable cached
pre-commit hooks against changed paths. Neither pytest nor pre-commit should
run a live provider check.

## Deliberate live smoke

These are command templates for an operator-authorized acquisition, not a
recurring test gate. Replace date, revision and path placeholders explicitly.
No further live run is needed to reproduce Stage 7 acceptance.

Exact revision (no listing request):

```bash
python -m iberian_shakti.ingestion.omie.live_smoke \
  --live \
  --delivery-date YYYY-MM-DD \
  --revision REVISION \
  --archive-root /some/operator-controlled/path
```

Latest observed (omit revision):

```bash
python -m iberian_shakti.ingestion.omie.live_smoke \
  --live \
  --delivery-date YYYY-MM-DD \
  --archive-root /some/operator-controlled/path
```

`--live` is mandatory and intentionally authorizes bounded network use. Without
it the command refuses before constructing acquisition dependencies. Dates
must be canonical `YYYY-MM-DD`; revisions are canonical positive integers.
The archive root must be operator-controlled and excluded from Git. Use ignored
`data/raw/` or an external custom root. **Never use `tests/data/omie` as a live
archive**; the CLI rejects that directory and its descendants when run from
the repository root. Fixtures and their manifest must retain their exact bytes.

The command uses the actual adapter → retriever → archive → parser → parse-event
path. A pass includes byte hash, selected revision, period/area counts and UTC
coverage, after required persistence. `attempt_count` describes report
retrieval; it does not record listing physical attempts. Event UUIDs live in
the stored metadata, not in the CLI summary.

| Exit | Outcome | Operator interpretation |
| --- | --- | --- |
| `0` | Pass | Archived complete report and successful persisted parse. |
| `2` | Missing `--live` or invalid arguments | No authorized acquisition; correct explicit inputs. |
| `3` | Unavailable | `not_found` or `not_listed`; no zero-record ingestion success. |
| `4` | Discovery failure/unknown coverage | Inspect safe outcome; an independently known exact revision bypasses the listing. |
| `5` | Retrieval/execution failure | Inspect stable error code; distinguish transport, status, encoding and budget failures. |
| `6` | Content failure | Complete raw report and failed parse retained; inspect/replay offline. |
| `7` | Archive failure | No ingestion success; preserve existing objects and investigate local storage. |
| `8` | Configuration/validation failure | Correct settings/inputs before another authorized run. |
| `70` | Unexpected internal failure | Static safe diagnostic; investigate locally without logging raw exception text. |

Passing local tests does not guarantee successful live validation.
A successful live observation does not guarantee permanent provider compatibility.

## Bounds and supported content

Default policy is three total attempts, with 1 then 2 seconds backoff (4-second
cap), 10-second phases, 30 seconds per attempt and 93 seconds per logical
acquisition including waits. Exact mode has at most three report attempts;
discovery has at most three listing plus three report attempts. An explicit
attempt-setting override changes these ceilings to N and 2N, subject to the
finite acquisition budgets. Listing and report have separate budgets, at most
186 seconds combined by default; local parsing/archive work is outside them.
Deadlines cooperate with host resolver/backend timeout behavior and do not
provide hard real-time preemption of a stalled OS call.

HTTP sends `Accept-Encoding: identity`, reads raw streams, uses verified TLS,
disables environment proxies/credentials and transport retries, and follows
zero redirects. Report limit is 4 MiB; discovery is one page, 1 MiB and 10,000
anchor candidates. There is no revision probing, polling or rediscovery loop.
Selected transient failures retry; permanent statuses/TLS failures do not.
Valid integer delta-seconds Retry-After must fit the remaining budget;
HTTP-date Retry-After uses bounded backoff instead.

Discovery selects the highest numeric revision observed for the date within
recognized coverage. Pagination/unrecognized or uncovered listings are explicit
coverage/schema outcomes, not evidence of historical absence. `.1` is not
assumed. Publication time/SLA, retention and complete revision history are not
guaranteed. A selected report's 404 ends that run without rediscovery.

Only the tested ASCII numeric `MARGINALPDBC;` grammar is supported: six fields
(year, month, day, sequential period, PT price, ES price), trailing semicolons,
LF/CRLF and a terminal `*`. Signed Decimal prices accept integers or one/two
fractional digits; negatives are valid. The complete day must match request,
filename and calendar. Both bidding areas use `Europe/Madrid`, not Lisbon
midnight or a fixed CET offset:

| Delivery date | Resolution | Ordinary / spring / autumn periods |
| --- | --- | --- |
| Before 2025-10-01 | 60 minutes | 24 / 23 / 25 |
| From 2025-10-01 | 15 minutes | 96 / 92 / 100 |

Each period yields PT then ES EUR/MWh records with UTC intervals. Unsupported
encoding, malformed rows or incomplete days produce zero normalized records,
without silently dropping rows or using an hourly fallback. Synthetic legacy
autumn/transition fixtures test those profiles; they do not establish original
provider bytes for those dates or compatibility with every historical grammar.

## Immutable archive and recovery

```text
<root>/omie/marginalpdbc/<delivery-date>/sha256/<sha256>/
  payload.bin
  retrievals/<retrieval-event-id>.json
  parses/<parse-event-id>.json
```

SHA-256 identifies unchanged complete response bytes, before decoding/newline
conversion. Retrieval events record safe source/date/filename/revision, UTC
completion, attempts/status, hash/length and archive linkage; parse events add
parser/schema versions, original retrieval ID, outcome and count. Publication
time remains null when unknown. Only allowlisted HTTP observations are retained.

Identical bytes reuse the payload while independent acquisitions add events.
Changed content, even under the same filename/revision, gets another hash
directory; prior bytes/events remain untouched. Never edit an archived payload,
event or mutable latest pointer to recover a revision. An operator can request
an independently known exact revision deliberately; neither listing coverage
failure nor 404 justifies brute-force probing or treating absence as success.

Complete malformed/empty/HTML 200 bodies are archived before failed parsing.
Interrupted/oversized bodies and HTTP error pages are not successful raw reports.
Archive or event-persistence failure prevents ingestion success. An orphan
complete payload may remain after a metadata failure; it is not replayable
acquisition history without the actual original provenance. If the caller
retains that acquisition result, explicit persistence can verify/reuse it.
Never fabricate missing retrieval history. Investigate disk/permission/fsync
faults and checksum/event conflicts without replacing immutable objects.

The archive requires a trusted local directory tree, same-filesystem hard
links and directory fsync. It does not protect against hostile owner changes,
directory-swap attacks or promise network-filesystem/WORM guarantees. A killed
process can leave private staging files; these are not published payloads.

## Offline replay

```text
previously archived raw payload + original retrieval provenance
  → replay(archive, archive_reference, original_retrieval_event_id)
  → same verified raw content + original retrieval provenance
  → parser.parse(..., parsed_at=<UTC>, parse_event_id=<new UUID>)
  → archive.persist_parse(parsed.provenance)
```

Use `LocalRawArchive`, `ingestion.replay.replay()` and `OmieAdapter().parser`.
Choose the archive reference and original acquisition UUID from that operator's
retained retrieval metadata, validated as `RetrievalProvenance`; do not copy
temporary Stage 6 UUIDs into permanent procedures. `replay()` itself only loads
and verifies content and original acquisition linkage. It performs no new
acquisition, creates no retrieval event or payload, and never falls back to HTTP
on corruption/missing history. Parsing and persisting a new parse event are
separate explicit calls, using a new UUID and aware UTC parse time.

For fixed raw bytes and parser/schema versions, normalized values, business
identities and normalized-content identity reproduce. Parse time/UUID can
differ. A parser-version change can change normalized-content identity without
changing the original raw object or acquisition history. Replay supports
parser upgrades, reprocessing, reproducibility and auditing, including repeat
diagnosis of malformed reports.

## Phase 2 shared contracts and selected credentials

Stage 1 adds pure API snapshot queries and system/weather records. API
`delivery_date` is the archive query partition; requested UTC window and actual
measurement support are separate. Legacy SourceRequest/MarketPrice/version-1
metadata remain unchanged; new API retrieval and measurement-parse events use
version 2. Reuse the same archive/replay functions; never migrate or edit old
sidecars. `ingest_resolved` shares persistence-before-parsing with OMIE.

`load_provider_auth(source_id, environ=...)` explicitly reads only the selected
ESIOS_API_TOKEN or ENTSOE_API_TOKEN. It does not load .env; anonymous sources
need neither. Secret settings dumps/repr exclude values. `PrivateRequestPolicy`
pins the HTTPS origin and supplies x-api-key or securityToken only privately.
No provider adapter/authentication success is implied by these shared utilities.

A safe complete HTTP-200 body can receive a separate version-2 no-data/provider
rejection/profile failure event after archival. Such a result is not successful
normalized data and retains its real HTTP status. An active credential echo is
rejected before normal payload publication, without redaction or a retry. Only
safe failure status/attempt/code metadata is returned. Authenticated nonidentity
coding fails before publication because the narrow echo guard does not decode
arbitrary encodings. Provider-specific commands and recovery instructions await
those provider stages; Stage 1 adds no live invocation.

## REN production and provisional empirical source periods

Stage 2 implements only `ElectricityProductionBreakdownDaily`, anonymous GET at
`https://servicebus.ren.pt/datahubapi/electricity/ElectricityProductionBreakdownDaily`,
`culture=en-US`, canonical date. No credential or unrelated environment is read.
No second aggregate request, discovery, scraping or polling occurs.

Library composition: `ren.identity.request_for(source_day)` →
`RenAdapter().resolve(request)` → `RenAdapter().retriever(retrieval_event_id=...)`
→ shared `ingest_resolved`, passing the adapter's parser and LocalRawArchive.
Offline tests inject MockTransport through the adapter's retriever factory.
There is no new REN live command; source-profile observations are not Stage 8
acceptance. Default pytest remains network-denied.

The safe report ID is `ElectricityProductionBreakdownDaily.en-US.v0.2.0`, so
culture and pinned profile participate in existing canonical query identity.
The query window spans the physical Europe/Lisbon civil day, converted to UTC
under the explicitly provisional empirical profile: 23, 24 or 25 elapsed hours.

Profile 0.2.0 requires all eleven selected source concepts. Consumption maps to
load; Wind/Solar/Hydro/Natural Gas/Biomass/Other Thermal/Coal/Wave map to generation
with explicit technology; Import/Export map to aggregate external interchange,
with no Spanish counterparty or asserted physical-versus-commercial statistic.
REN's native perimeter is retained as provider-defined Portuguese system data.
Pumping, Consumption + Storage, Consumption of Batteries and Battery Injection
are explicitly unselected. Unknown/duplicate names, fields, units or malformed
values fail visibly. Presentation strings are bounded inert data. No derived
share, total, energy or filling is performed.

Original safe complete 200 bytes are archived before strict UTF-8 JSON validation,
regardless of MIME. Limits: 1 MiB, 32 series, 10,000 values, depth 12, 30,000 JSON
nodes, strings 4,096 characters, numeric tokens 128 characters, object keys 64.
Every selected and unselected array must be numeric, finite, non-null and aligned.
Decimals have no float intermediate or rounding. MW must be explicit. Duplicate
JSON keys/nonfinite values/unknown schema and content coding fail safely.

The parser generates the physical Europe/Lisbon quarter-hour sequence by UTC
stepping between independently converted local midnights. All source labels must
match it in exact order: 96 ordinary, 92 spring (01h absent), 100 autumn (two 01h
blocks assigned fold 0 then fold 1 by position). Unexpected counts, duplicates
or ordering fail `content_invalid` with zero records; no sorting/deduplication.
Valid days emit eleven SystemMeasurement records per period, with source Decimal
MW unchanged, interval support and `provider_period_value`. No MW-to-MWh
conversion, instantaneous claim or arithmetic-mean claim exists. Status is
`provisional_empirical` in the versioned profile, separate from the provider's
provisional publication status. Authoritative MW statistic, label placement and
autumn fold contract remain unresolved; they no longer block forecasting inputs.

The shared three-attempt, 1/2-second backoff and 10/30/93-second phase/attempt/
operation budgets apply. Permanent failures terminate; 404 has no REN-specific
no-data interpretation. Future/missing/error forms remain unverified. Keep
successive deliberate calls sequential and at least one second apart.

Replay uses the existing `replay()` function and REN parser, then explicitly
persists the new parse event. It verifies original hash/retrieval linkage and
reproduces the same values/identities or failure, never refetches or downloads
metadata. Same-query identical bytes reuse content with distinct retrieval events; corrections retain
both hashes/histories. Do not overwrite failed payloads to repair semantics.
Fixtures are synthetic/checksummed; real observations stay outside Git pending
rights approval. Exact legacy 0.1.0 acquisitions are also accepted by the parser
under 0.2.0; new fetches accept only 0.2.0 identity. Legacy report/query/raw/events
stay unchanged, with interpretation identified by native/parse profile 0.2.0.
Each record's day, series and physical interval recover its zero-based array
position and label from original bytes through retrieval/parse/raw-hash linkage.
Future authoritative clarification requires a new version and new replay parse
events, preserving all old events. See the original
[ADR 0005](../adr/0005-ren-source-profile-and-time-gate.md),
[ADR 0006](../adr/0006-ren-provisional-period-semantics.md)
and the [Stage 2 report](../codex/reports/phase_2_stage_2_ren_report.md).

## ESIOS indicator 544 (offline engineering integration)

Only `Demanda prevista Peninsular` is selected: Spanish peninsular demand
forecast, MW, native five-minute timestamped samples. Publication description:
00:00 covers D; 13:30 adds the first three hours of D+1. This does not establish
a complete D+1 or historical auction-cutoff forecast vintage.

Library composition: `esios.identity.request_for(QueryWindow(...))` →
`EsiosAdapter().resolve(request)` → the adapter's retriever → shared
`ingest_resolved`, `LocalRawArchive` and adapter parser. No live command is added;
provider calls remain reserved for separately authorized controlled validation.
Offline tests inject `httpx.MockTransport` and a synthetic environment mapping.

The request profile is `indicator544.v0.1.0`; parser/profile version is 0.1.0.
Queries contain only ISO-8601 UTC `start_date` and `end_date` at
`https://api.esios.ree.es/indicators/544`. Windows must be positive and at most
25 hours. The UTC start date supplies archive partition context. No aggregation,
pagination, backfill loop or geographic-ID guess is made. Keep separate deliberate
calls sequential and at least one second apart. Shared three-attempt bounded
retry/backoff/time budgets apply; delta-seconds Retry-After is respected.

`ESIOS_API_TOKEN` is loaded only when constructing the selected retriever and
injected privately as `x-api-key`. Missing/invalid credentials raise the shared
static `ConfigurationError` before request construction or network I/O. No .env
loading, authentication fallback, refresh, token logging or CI secret is needed.
401/403 are terminal authentication/authorization failures. Unverified 404 bodies
remain permanent HTTP failures, without invented no-data semantics. Timeouts,
429 and supported 5xx use shared retries. Oversized bodies and active-credential
echoes are rejected before raw publication; authenticated nonidentity encoding
also fails before publication under the existing private policy.

The strict parser requires indicator ID 544 and finite, non-null numeric values,
explicit provider UTC timestamps and native geo IDs with peninsular name evidence
(`Península` in the value or matching `geos`). Optional name/unit/magnitude/time
metadata must agree when supplied; descriptions and display fields are optional
inert bytes. No live numeric magnitude/cadence/geography ID is asserted. Raw cap
is 2 MiB; at most 2,000 values and 32 geos, depth 16, 50,000 JSON nodes, strings
4,096 characters and numeric tokens 128 characters. Unknown/error documents,
duplicate JSON keys, conflicting or repeated timestamps and incompatible
metadata produce a failed parse event with zero normalized records, without retry.

Use `datetime_utc` directly. If offset-aware `datetime` is present, its instant
and Europe/Madrid offset must agree, including DST. Strict UTC order and
five-minute grid membership retain gaps without filling. A possible inclusive
end sample is retained; samples outside the requested endpoints are rejected.
Real end-date inclusivity remains unverified. No whole-window completeness,
resampling, averaging or interval-energy claim is made.

Each observation is an existing `SystemMeasurement` forecast/load/MW instant
sample with cadence 300 seconds, canonical `ES.peninsular` system/mainland area,
returned provider-native geo ID, native series 544 and profile version.
`Statistic.INSTANT` represents a timestamped forecast sample, not actual demand
or a confirmed arithmetic mean. `values_updated_at`, if supplied, is indicator
update context in `SourceTimes.updated_at` on the snapshot's records; it does
not establish a per-value issue time. Issue/run/publication times remain null;
publication status is unknown. Acquisition and parse times remain separate events.

Complete safe successful response bytes archive before parsing. Identical bytes
reuse raw content with separate retrieval events; changed bytes retain both
hashes and immutable histories. Replay uses shared `replay()` with original
retrieval identity, then `EsiosParser.parse()` and `archive.persist_parse()`.
It requires no token or network and reproduces values, business identities,
UTC times and raw linkage. Only the new parse event ID/time changes.

Run `python -m pytest tests/unit/ingestion/esios tests/integration/test_esios_flow.py`
for the focused offline suite. Exact live metadata spelling/catalogue mapping,
authentication/identity-encoding compatibility, missing/error shapes, retention,
revisions, quotas and returned coverage remain controlled-live checks; see the
[Stage 3 report](../codex/reports/phase_2_stage_3_esios_report.md).

## Deferred scope

Other ESIOS products, ENTSO-E, Open-Meteo and
MIBGAS remain unimplemented. Snowflake, dbt, feature engineering,
ML training, model registry, batch forecasts, FastAPI, dashboard, production
scheduler and infrastructure deployment remain future work. No paid-resource
action is part of this local workflow. See the
[closure report](../codex/reports/phase_1_stage_7_final_acceptance.md) for the
accepted limitations and future phase sequence.
