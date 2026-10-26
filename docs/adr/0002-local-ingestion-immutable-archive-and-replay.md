# ADR 0002: Local ingestion execution, immutable archive, and replay

- Status: Accepted
- Date: 2026-10-26

## Context

Phase 1 requires reproducible local ingestion with original source bytes and
traceable revisions, without additional infrastructure. This records the
already accepted [Phase 1 assessment](../codex/reports/phase_1_readiness_assessment.md),
especially §§5.1 and 5.4–5.7. It is not another architecture assessment.

## Decision

### Execution and responsibility boundaries

Use synchronous execution with a small source-adapter boundary for resolving
requests/locators, source-specific availability interpretation, and parsing.
The reusable runner owns retrieval, bounded retries, archive, and result
assembly. Retrievers acquire bytes; archives preserve bytes/provenance;
parsers validate an independent copy and produce normalized records.
Inject client/transport, clock, sleeper, and archive root. Support offline
local-file retrieval and replay in later stages, without an async framework,
plugin registry, scheduler, or future provider implementation.

Shared immutable request, payload, provenance, result, and protocol contracts
belong in `contracts/ingestion.py`; normalized prices belong in
`contracts/market.py`. Common execution/configuration belongs in `ingestion/`,
OMIE-specific rules in `ingestion/omie/`, and shared logging in `common/`.
Frozen models must also use immutable nested collections where applicable.

### Original bytes, content identity, and immutable local archive

Default archive root is `data/raw`, relative to the documented working
directory, overridable with `RAW_ARCHIVE_ROOT`. Custom roots must also remain
outside tracked content. Preserve original complete body bytes unchanged,
before decoding/newline/parser transformations. Request identity encoding and
read the raw HTTP body stream so automatic content decoding cannot change the
archive; record Content-Encoding and reject unsupported encodings at parsing.
Local retrieval reads unchanged bytes too. Transport framing is not file content.

Compute SHA-256 over those bytes. Content identity is
`(source_id, report_id, delivery_date, sha256)`; the content-addressed layout is:

```text
data/raw/omie/marginalpdbc/2026-10-26/sha256/<64-hex-sha256>/
  payload.bin
  retrievals/<retrieval-event-id>.json
  parses/<parse-event-id>.json
```

Identical content reuses the payload even under different revision labels.
Different content is separately retained, including a possible same-filename
republishing. Revision/ETag/Last-Modified observations never replace the hash.
Do not overwrite archived bytes, metadata events, or a mutable latest manifest.

Publish complete objects atomically with no-replace semantics using private
same-filesystem staging. An overwrite-capable rename or file permissions alone
does not establish immutability. Check existing content hash/length, and report
collision/corruption/inconsistent metadata as integrity errors. Test concurrency
and interruption in the archive stage. This is application-enforced local
immutability, not WORM infrastructure.

Retrieval and parse events are separate immutable objects with stable event
identity (for example, hashes of canonical versioned metadata). Reusing an
event must not duplicate it; a new acquisition may add an observation without
copying the payload. Metadata failures cannot report ingestion success; an
orphan payload remains recoverable. Archive complete 200 bodies before parsing,
including empty/malformed/HTML bodies, so content failures remain diagnosable.
Interrupted/oversized bodies and HTTP error pages are not successful reports.

### Provenance and replay

Retrieval provenance records source/report/date, selection mode/requested and
observed revision, safe locator/filename, UTC completion time/event ID, outcome,
attempt count, HTTP status (null for local file), byte count, hash, and archive
reference. Only allowlisted HTTP observations may be retained. Unknown source
publication time stays unknown; retrieval time is not publication time.

Parse provenance adds parser identity/version, normalized-schema version,
original retrieval/raw references, parse timestamp, and success/failure code.
It must not pretend the parser was part of acquisition. Each normalized record
links through parse provenance to original raw content and acquisition history.

Replay verifies the archived hash, performs no network request, retains original
retrieval history, and creates a distinct parse event with explicit versions.
For fixed content/parser/schema, normalized values and identities are deterministic.
Normalized content identity includes raw content identity plus parser/schema
versions. Business identity is
`(source, report, market_area, delivery_date, period_index, duration_minutes)`.
Revisions remain distinguishable through content/version provenance; retrieval
timestamps do not enter either normalized-content or business identity.

### Bounded retrieval and availability

All external calls use finite connect/read/write/pool timeouts (initially
10 seconds each), a bounded attempt deadline (initially 30 seconds), operation
budget, finite response-size limits, and bounded discovery traversal. Keep
deadline, backoff-cap, and adapter size limits as typed code defaults unless
operation demonstrates a need for more environment settings.

Default retry policy is three total attempts including the initial attempt,
with 1-second then 2-second exponential backoff and a 4-second cap. Disable
transport auto-retries. Selected connection/timeouts/incomplete transport and
500/502/503/504 outcomes may retry under that single policy. Retry-After on
429 must fit the remaining budget; otherwise fail explicitly. TLS verification
and invalid URLs are permanent; never disable verification. Permanent/unclassified
4xx, local/archive failures, and complete content-validation failures do not
enter a blanket retry loop. Translate errors to stable typed codes without
logging unchecked library exception strings.

A valid OMIE filename returning 404 yields explicit `not_found` unavailability,
with date/revision context and no retry in that run. Absence from a valid covering
listing yields `not_listed`; unrecognized/incomplete/uncovered listings yield
explicit discovery/schema/coverage outcomes. Do not claim historical absence or
future publication from insufficient evidence. Unavailable differs from empty
success, content failure, and retry exhaustion. No polling until publication;
a later explicit run may try again. Other prepublication body variants remain
unverified, so unknown 200 bodies are content failures.

### Dependencies, configuration, and logging

Use runtime `httpx>=0.28,<1` for synchronous HTTPS, phase timeouts, injectable
transport, and MockTransport; use `pydantic>=2,<3` for validated typed contracts.
No new test dependency or package-manager/lockfile system is required.

Read the minimal environment explicitly using the standard library and an
injectable mapping: `RAW_ARCHIVE_ROOT=data/raw`,
`INGESTION_TIMEOUT_SECONDS=10`, `INGESTION_MAX_ATTEMPTS=3`,
`INGESTION_BACKOFF_SECONDS=1`, and `LOG_LEVEL=INFO`. Validate before I/O;
numeric settings must be finite with positive timeout/attempts and nonnegative
backoff. No automatic `.env` loading, import-time I/O/handler setup, archive
creation during settings construction, or unrelated provider credentials.

Use standard-library logging with an explicitly configured JSON handler and
allowlisted event context: source/report/date, safe filename/revision, attempt,
status, elapsed time, bytes/hash/archive reference, records, parser version,
outcome/error code. Omit arbitrary messages, rejected validation inputs, raw
payloads, full configuration, unchecked exception text, arbitrary headers,
authorization/cookies/passwords/tokens, URL userinfo, and signed query values.
Keep HTTPX/httpcore debug output from bypassing this policy. This must remain
safe for later authenticated adapters, not just public OMIE access.

### Testing and resource controls

Normal pytest is deterministic and offline, using fixtures, temporary paths,
injected clocks/sleepers, and MockTransport. Explicit live validation belongs
in a separate opt-in command outside normal pytest/pre-commit/automatic CI;
record its result separately. Do not automatically activate, provision, resize,
modify, or delete Snowflake or any paid cloud resource. This local decision
authorizes no external infrastructure action.

## Alternatives considered

Async execution, orchestration frameworks, cloud storage, and extra retry or
logging libraries add no required Phase 1 capability. Mutable filename-based
storage loses revision history. Retrieval-only metadata cannot identify parser
changes, and refetching during replay defeats reproducibility. Standard-library
HTTP plumbing would duplicate HTTPX's chosen transport/timeout testing seam.

## Consequences

Later stages must test atomic no-replace publication, corruption, metadata
failures, revisions, bounded retry/availability, and hash-verified replay.
Stage 1 installs dependencies and supplies only validated configuration and
logging; retrieval, archive, protocols, normalized models, and replay remain
pending. No cloud, serving, or future provider code is introduced.

## Follow-up

See [ADR 0001](0001-omie-day-ahead-source-and-market-price-contract.md) for
the source/price/calendar contract and the accepted assessment's Stages 2–7
and single Phase 1 acceptance checklist for implementation and validation.
