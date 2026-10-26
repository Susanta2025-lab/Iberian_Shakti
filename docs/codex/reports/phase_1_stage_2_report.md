# Phase 1 Stage 2 — Shared contracts and protocol boundaries

Date: 2026-10-26. Branch: existing `main`. Stage 1 baseline: local commit
`1cab3c2` (`feat: establish Phase 1 ingestion foundation`).

## A. Stage objective

Implemented the shared immutable typed contracts and synchronous protocol
boundaries consumed by later Phase 1 stages. This implementation follows the
accepted [Phase 1 assessment](phase_1_readiness_assessment.md),
[ADR 0001](../../adr/0001-omie-day-ahead-source-and-market-price-contract.md), and
[ADR 0002](../../adr/0002-local-ingestion-immutable-archive-and-replay.md).
No additional readiness assessment or architecture decision was performed.

## B. Files changed

All nine paths are additions; existing tracked files are unchanged.

| Exact path | Purpose |
| --- | --- |
| `src/iberian_shakti/contracts/_base.py` | Internal strict/frozen configuration, safe scalar types, UTC validation, central version identifiers/types. |
| `src/iberian_shakti/contracts/ingestion.py` | Request/resolution, content/archive, acquisition/parse provenance, outcomes/results, and four protocol boundaries. |
| `src/iberian_shakti/contracts/market.py` | Shared interval and normalized price models and reusable interval validation. |
| `src/iberian_shakti/contracts/periods.py` | Pure caller-configured market-day partitioning between separately converted local midnight boundaries. |
| `tests/contracts/conftest.py` | Synthetic reusable contract examples; no downloaded fixtures. |
| `tests/contracts/test_ingestion.py` | Request, locator, identity, provenance, result, immutability, serialization, and no-I/O tests. |
| `tests/contracts/test_market.py` | Shared interval/price, strict Decimal, identity, serialization, and validation tests. |
| `tests/unit/test_market_periods.py` | Accepted legacy/modern calendar examples and generic helper invariants. |
| `docs/codex/reports/phase_1_stage_2_report.md` | This implementation and validation report. |

No package exports or files under `ingestion/` needed changes.

## C. Contract architecture

`contracts/ingestion.py` owns the acquisition and parsing contracts, including
all reusable protocols. `contracts/market.py` owns the single normalized price
schema and interval validation. Ingestion contracts import the normalized record;
the market module does not import ingestion, avoiding a dependency cycle.

`_base.py` holds internal validation primitives and centrally named ingestion,
parse-provenance, and market-schema version constants and literal types, all
initially `1.0.0`. Parser implementation versions are explicit three-component
numeric versions supplied by future parsers; no OMIE parser version is invented.

`periods.py` consumes the shared `MarketInterval`; it does not duplicate its
validation. All protocols are defined once in `contracts/ingestion.py`. There
is no additional interface module, registry, orchestration class, async layer,
or dependency injection framework.

HTTP execution, retry decisions/execution, archive publication/event storage,
replay execution, and OMIE resolution/discovery/parser policy are deferred.

## D. Models introduced

Every model inherits strict, frozen Pydantic v2 behavior with unexpected fields
forbidden, defaults validated, and rejected inputs hidden in validation error
text. Nested models are frozen; record collections are tuples; payloads are
immutable bytes. Python validation requires correctly typed inputs. JSON uses
explicit standard representations for dates, aware timestamps, UUIDs, enums,
and Decimal strings. Declared field order gives deterministic serialization
for fixed values; identity properties do not add redundant serialized fields.

| Model | Purpose, key fields, and invariants |
| --- | --- |
| `SourceRequest` | Source/report IDs, delivery date, optional positive integer revision, and serialized selection mode. Omitted revision selects `latest_observed`; a revision selects `exact_revision`. An explicitly contradictory mode is rejected. IDs are bounded, nonempty safe identifiers. Python date strings, numeric coercion, and boolean revisions are rejected. |
| `ResolvedSource` | Original request, safe filename, optional positive observed revision, and opaque safe locator. Exact selection must preserve its requested revision. Source/report/date/selection remain accessible through the immutable request. |
| `ResolutionResult` | Request, resolution outcome, optional resolved source, and stable error code. Resolved requires a matching source and no error; unresolved outcomes have no source. Explicit absence, unknown/incomplete coverage, and failures remain distinguishable. |
| `RawContentReference` | Source/report/date, lowercase 64-hex SHA-256, and nonnegative byte length. `content_identity` is `(source_id, report_id, delivery_date, sha256)`, excluding revisions and acquisition times. |
| `RawPayload` | Raw reference and original immutable bytes. A small pure validator recomputes SHA-256 and checks length against these exact bytes, including line endings. Bytes are excluded from repr and metadata serialization. This runtime byte carrier is intentionally not reconstructible from a metadata-only dump; persisted references/events are round-trippable. |
| `ArchiveReference` | Raw reference and safe relative path. Requires exactly `source/report/YYYY-MM-DD/sha256/<hash>/payload.bin`. No absolute paths, traversal, path resolution, file reads, or writes. |
| `HttpObservations` | Only bounded MIME type, content-encoding token, HTTP opaque ETag, and parsed UTC Last-Modified. No raw header mapping or arbitrary metadata. Last-Modified is not asserted to be publication time. |
| `RetrievalProvenance` | Version, resolved source/request, UTC completion time, caller-supplied UUID event ID, acquisition outcome, positive attempt count, optional status/HTTP observations, raw/archive references, stable error code, and optional source publication time. Successful HTTP acquisition requires 200; local acquisition has null status. Raw source linkage and archive identity must agree. Failed/unavailable acquisition cannot claim a payload/archive. Content/discovery/archive errors cannot masquerade as retry exhaustion. Unknown publication time defaults to null. |
| `RetrievalResult` | Retrieval provenance and optional payload. Retrieved requires the matching raw payload; unsuccessful retrieval forbids payloads. Payload bytes remain excluded from nested metadata dumps. |
| `ParseProvenance` | Separate contract version, original retrieval UUID/raw/archive references, parser ID/version, market schema version, UTC parse time, distinct parse UUID, parse outcome, stable error code, and record count. Success requires positive count and no error. Content/integrity failure requires a recognized code and zero count. Archive/raw references must agree. |
| `ParseResult` | Parse provenance and immutable tuple of normalized prices. Count, parse-event UUID, schema version, and source/report/date linkage must agree. A failed parse cannot return partial records. |
| `IngestionResult` | Original retrieval provenance and optional parse result. Unsuccessful/unavailable acquisition has no parse. Completed acquisition-to-parse results require archive linkage and matching original acquisition UUID/content/archive. Both parse success and explicit content failure retain archived acquisition history. |
| `MarketInterval` | Positive strict period index/duration and aware UTC start/end. Requires a positive interval of exactly the stated whole-minute duration, with no fixed period ceiling or resolution. |
| `MarketPrice` | Shared interval plus schema version, source/report/market/area/date, finite Decimal price, currency, MWh unit, and parse-event UUID. Allows signed/zero prices and safely serializes Decimal as strings. Business identity excludes acquisition time and parse-event UUID. |

Strict JSON round trips are tested for persisted metadata and normalized records.
Malformed JSON decimal strings and JSON numbers for prices are rejected.

## E. Protocols introduced

All methods are synchronous and implementation-independent:

| Protocol | Method boundaries and responsibility |
| --- | --- |
| `SourceAdapter` | `resolve(request, retriever) -> ResolutionResult` resolves selection using injected acquisition when discovery is required. `classify_unavailable(source, http_status) -> ErrorCode | None` owns provider-specific absence interpretation. It owns no reusable retry or archive execution. |
| `Retriever` | `retrieve(source) -> RetrievalResult` acquires exact bytes and reports retrieval provenance. Future implementations own finite transport budgets/retries; there is no implementation in this stage. |
| `RawArchive` | `persist(payload, provenance) -> ArchiveReference` preserves original payload/acquisition history; `load(reference) -> RawPayload` loads verified bytes; `load_retrieval(reference, retrieval_event_id) -> RetrievalProvenance` retrieves original history; `persist_parse(provenance) -> None` stores a separate immutable parse event. |
| `Parser` | `parse(payload, retrieval, *, parsed_at, parse_event_id) -> ParseResult` validates complete content and returns normalized records with an explicitly versioned parse event. Time/event identity are supplied, not generated by contract construction. |

Archive failures have stable error categories but cannot be claimed as ingestion
success. Later execution must translate exceptions safely and ensure metadata
was actually persisted before assembling success; these pure contracts do not
verify filesystem existence or event persistence.

## F. Market-period design

`MarketInterval` owns generic per-record interval validation, reused by
`MarketPrice` and the pure calendar helper. Prices require Python `Decimal`;
JSON requires decimal strings, converted directly to `Decimal` without float
intermediates. Nonfinite values are invalid; negative and zero prices are valid.
Trailing decimal precision survives serialization and deserialization.

Timestamps must have timezone information and zero UTC offset. Naive and
nonzero-offset timestamps are rejected rather than silently normalized.
`period_index` and `duration_minutes` are strict positive integers; neither has
an OMIE period-count ceiling. Interval duration is checked without imposing
regulatory price caps or fixed 15/60-minute resolution.

Area and currency are bounded code strings, allowing PT/ES/EUR and future
provider codes; the shared record does not impose OMIE-only area restrictions.
Malformed codes are rejected. The unit is explicitly MWh. OMIE's allowed
area/currency/market set remains adapter policy.

`market_day_intervals(day, timezone=..., duration_minutes=...)` accepts an
explicit IANA `ZoneInfo` and explicit resolution. It separately converts each
market-local midnight to UTC and partitions elapsed UTC time, returning a tuple.
It rejects nonpositive/coerced durations, incomplete partitions, and fixed-offset
calendar substitutes. It never steps naive wall-clock times through DST.

Tests pass Europe/Madrid and the accepted profiles explicitly: legacy 24/23/25
hourly periods and modern 96/92/100 quarter-hour periods, including 2025-09-30
and 2025-10-01. Tests also assert exact spring/autumn UTC boundaries, skipped and
repeated hours, full-day duration, contiguity, leap day, generic resolutions,
and another timezone. The transition date is test input, not production policy.

OMIE profile selection, filename/date agreement, whole-report sequence and
two-area completeness checks, historical fixture verification, supported
lexical price precision, and timezone startup/configuration checks remain
Stage 4 or later work. IANA data must be supplied by the host; this stage adds
no timezone dependency or startup machinery.

## G. Provenance design

The linkage is:

```text
SourceRequest -> ResolvedSource -> RetrievalProvenance
                                      | raw + optional archive
                                      v
                         RawContentReference / ArchiveReference
                                      ^
                                      | original acquisition UUID + raw/archive
                               ParseProvenance
                                      ^
                                      | parse-event UUID
                                  MarketPrice
```

Acquisition and parse event UUIDs are explicit caller-supplied stable identities,
never generated during model construction. Reusing an acquisition does not
change it. A later replay can use a new parse UUID/time while retaining the
original acquisition UUID and raw/archive identity. Tests construct these
relationships without implementing replay execution.

`ParseProvenance.normalized_content_identity` combines raw content identity,
parser ID/version, and normalized schema version. `MarketPrice.business_identity`
is `(source, report, market_area, delivery_date, period_index, duration_minutes)`.
Neither includes retrieval time. Different revision labels can refer to the
same raw content; different hashes remain distinct under the same filename.
The models do not substitute ETag, revision, or Last-Modified for content hash.

Safe locators deliberately use opaque public relative identifiers rather than
URLs. They cannot contain schemes, URL userinfo, query strings, fragments,
percent escapes, or traversal. Actual transport URLs and future authentication
remain execution-owned and must never be copied into these fields. No OMIE
URL is built. Identifier/HTTP-observation fields must be populated according to
their documented meaning, not repurposed to carry credentials.

No model permits raw headers, cookies, Authorization, or arbitrary metadata
maps. Construction and validation produce no logs. Error text hides rejected
inputs; callers must not log `ValidationError.errors()` or whole models.
Pydantic's validation-bypass APIs (`model_construct`, `model_copy(update=...)`)
are not supported ingestion boundaries; changed external data must be validated.

## H. Tests

Focused Stage 2 command:

```bash
python -m pytest tests/contracts tests/unit/test_market_periods.py -q
```

**214 passed**. The directly requested `pytest` executable also passed all 214
focused tests. Counts include parametrized cases:

| File | Count | Coverage |
| --- | ---: | --- |
| `tests/contracts/test_ingestion.py` | 129 | Requests/modes/revisions, strict identifiers/dates, safe locators/filenames, hashes/lengths/exact bytes, archive path/content linkage, UTC acquisition/parse history, HTTP observations, availability/coverage/failure distinctions, results, immutable nesting, version/identity/replay relationships, error text, and no-I/O construction. |
| `tests/contracts/test_market.py` | 62 | PT/ES, positive/negative/zero prices, Decimal precision and strict Python/JSON inputs, finite values, UTC intervals/duration/order, period/duration validation, code/version/extra-field rejection, immutable records, and extensible periods/areas/currencies. |
| `tests/unit/test_market_periods.py` | 23 | Six accepted ordinary/DST profiles, transition boundaries, leap day, UTC boundaries/contiguity/day coverage, skipped/repeated local hours, generic timezone/resolution, invalid partition/type/range, and no fixed-offset substitution. |
| **Stage 2 total** | **214** | Offline synthetic contracts and calendar inputs only. |
| Existing Stage 1 configuration/logging tests | 83 | Unchanged and all passing. |
| **Full suite** | **297** | No skipped, failed, or live tests. |

No source fixture downloads, credentials, filesystem archive writes, live HTTP
calls, sleeps, or paid resources are required. The no-I/O construction test
explicitly blocks file access and sockets. A repository-wide default network
guard remains deferred to Stage 5 as specified by the accepted sequence.

## I. Validation evidence

All commands completed with exit status 0:

| Command | Exact result |
| --- | --- |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `35 files already formatted` |
| `mypy src` | `Success: no issues found in 20 source files` |
| `pytest` | `297 passed` |
| `git diff --check` | Passed; no output. |
| `pytest tests/contracts tests/unit/test_market_periods.py -q` | `214 passed` |
| `python -m pytest tests/contracts tests/unit/test_market_periods.py -q` | `214 passed` |
| `python -m pytest -q` | `297 passed` |

The named repository environment is `iberian_shakti`, Python 3.12.9,
Pydantic 2.14.1. The shell's standalone `pytest` selects another Python 3.12
installation (3.12.3); both that requested command and `python -m pytest` in the
named environment pass. No dependency or tool configuration was changed.

Reviewed `git status --short`, `git diff --stat`, and `git diff`. All additions
are initially untracked, so ordinary Git diff/stat do not display their content.
Also reviewed each added file through `git diff --no-index /dev/null <path>`
and checked added-file whitespace separately. No existing tracked file changed.

## J. Scope confirmation

Stage 2 only. No Stage 3+ execution was introduced: no concrete HTTPX transport,
retry loop, archive writer/publication/sidecar handling, replay execution,
OMIE download URL, listing parser/discovery, report parser, downloaded fixture,
live smoke command, end-to-end ingestion runner, or infrastructure behavior.
The pure exact-byte hash check and generic UTC interval helper are the small
contract-level helpers explicitly permitted in this stage.

Stage 1 configuration/logging/tests, ADRs, project/dependency configuration,
environment template, instructions, provider stubs, apps, Snowflake/dbt, ML,
monitoring, Terraform, Docker, and workflows are unchanged. No cloud/resource
operation, commit, push, or branch creation occurred.

## K. Remaining Phase 1 work

The accepted sequence remains authoritative:

- Stage 3: byte retrieval, bounded retry/availability, local files, immutable
  archive/events, and verified replay with mocked/filesystem tests.
- Stage 4: OMIE exact selection/bounded discovery, parser/calendar profiles,
  representative fixtures, and complete-report validation.
- Stage 5: edge cases, redaction/archive failures, default offline network guard,
  and mocked end-to-end revision/replay integration.
- Stage 6: explicitly opted-in live smoke command and separately recorded result.
- Stage 7: operational/developer documentation and final Phase 1 verification
  against the existing accepted criteria.

No unresolved Stage 2 implementation issue was found. Execution/storage
assurances, OMIE fixture coverage, and live observations remain unimplemented
later-stage responsibilities, not claims made by these contracts.

## L. Stage verdict

**PASS**

Applies to Phase 1 Stage 2 only; Stages 3–7 remain pending.
