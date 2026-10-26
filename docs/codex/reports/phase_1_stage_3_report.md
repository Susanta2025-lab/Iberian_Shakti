# Phase 1 Stage 3 — Retrieval, immutable archive, provenance, and replay

Date: 2026-10-26. Working branch: existing `main`.

## A. Stage objective

Implemented the reusable synchronous execution/storage layer from
`ResolvedSource` to exact raw bytes, bounded retrieval outcomes, immutable local
content/events, and verified offline replay. The accepted
[Phase 1 assessment](phase_1_readiness_assessment.md),
[Stage 2 report](phase_1_stage_2_report.md), ADR 0001, and ADR 0002 remain the
baseline. No readiness/architecture reassessment or replacement acceptance
checklist was produced.

## B. Files changed

| Exact path | Purpose |
| --- | --- |
| `src/iberian_shakti/ingestion/errors.py` | Safe typed execution/archive/replay errors and closed failure reasons using existing contract error codes. |
| `src/iberian_shakti/ingestion/retry.py` | Validated finite retry, timeout, deadline, and backoff policy; explicit Stage 1 settings conversion. |
| `src/iberian_shakti/ingestion/retrieval.py` | Shared contract result assembly, exact local-file retrieval, safe path checks, encoding precondition, and controlled log context. |
| `src/iberian_shakti/ingestion/_http_transport.py` | HTTPX transport using public httpcore pool/backend interfaces to shrink socket timeouts against the monotonic deadline. |
| `src/iberian_shakti/ingestion/http.py` | HTTPS raw-stream acquisition, single retry loop, adapter-owned availability callback, allowlisted observations, byte/deadline limits. |
| `src/iberian_shakti/ingestion/archive.py` | Local immutable payload/event persistence, verified loads, and protocol-based acquisition persistence helper. |
| `src/iberian_shakti/ingestion/replay.py` | Offline replay through `RawArchive`, preserving original acquisition identity/time. |
| `src/iberian_shakti/contracts/ingestion.py` | One compatible widening of `HttpObservations.content_encoding` to preserve bounded ordered encoding lists; see J. |
| `src/iberian_shakti/common/logging.py` | Six additional closed event names required by Stage 3. No formatter/context/security behavior changed. |
| `tests/unit/ingestion/__init__.py` | Stage 3 unit test package. |
| `tests/unit/ingestion/conftest.py` | Synthetic contracts, advancing fake clock/sleeper, and network denial scoped only to these tests. |
| `tests/unit/ingestion/test_http.py` | Exact bytes, observations, HTTP/transport classifications, retry bounds, budgets, encoding contract regression tests. |
| `tests/unit/ingestion/test_transport.py` | Real HTTP framing over a mocked network backend; slow headers/body reads and shrinking socket budgets. |
| `tests/unit/ingestion/test_local_retry.py` | Local files, safe paths, failures, policy/settings validation, and no HTTP/archive side effects. |
| `tests/unit/ingestion/test_archive.py` | Publication, corruption, concurrency, immutable events, metadata failures, loading, and replay. |
| `tests/unit/ingestion/test_execution_logging.py` | Actual failure-path/event logging and synthetic secret non-disclosure. |
| `tests/integration/test_stage3_flow.py` | Generic mocked acquisition/archive/replay, test-only parser linkage, encoding/content failures, and local-file integration. |
| `docs/codex/reports/phase_1_stage_3_report.md` | This report. |

All other existing files, Stage 1 settings, dependency/tool configuration,
provider stubs, and existing tests are unchanged.

## C. Execution architecture

`HttpRetriever` and `LocalFileRetriever` implement the existing `Retriever`
boundary and return `RetrievalResult`. Each instance receives a caller-supplied
UUID representing its acquisition event; completion time is supplied by an
injected UTC clock or the default UTC clock. Callers use a new UUID for a new
acquisition. Construction performs no network request or archive creation.

The HTTP locator resolver maps the contract's opaque safe identifier to the
private transport URL. The URL is never persisted or logged. Provider-specific
404 interpretation is injected using the signature of
`SourceAdapter.classify_unavailable`; generic retrieval contains no source
filename, listing, publication, or HTML interpretation.

The HTTPX client uses an injected synchronous transport or the default
deadline-aware transport. The default transport uses public APIs from HTTPX's
existing required httpcore 1.x dependency; no dependency was added, and no
private pool/client fields are patched. It owns verified TLS and zero transport
retries. A supplied transport is closed with the acquisition client and must
honor finite timeouts, avoid internal retries, and expose an unconsumed raw
stream. A preconsumed response is rejected rather than trusting potentially
decoded `response.content`.

Local files use safe relative locators beneath an explicit input root and
binary reads. URL locators, traversal, absolute paths, and symlinks below that
root are rejected. Local results have null HTTP status/observations. Retrieval
does not create an archive.

`LocalRawArchive` implements `RawArchive`. `persist_retrieval(result, archive)`
uses that protocol to add validated archive linkage only after both the raw
object and acquisition event have persisted. It does not parse or claim full
ingestion success. Unavailable/failed acquisitions have no payload to archive.
`replay(archive, reference, event_id)` uses only `RawArchive`, returning the
existing `RetrievalResult` contract rather than defining a replay DTO.

Settings remain explicit: callers can pass
`RetryPolicy.from_settings(settings)` into `HttpRetriever` and create an archive
with `LocalRawArchive.from_settings(settings)`. No environment or `.env` is
implicitly loaded.

## D. Retry/error semantics

Default policy: **three total attempts**, including the first, with **1 second
then 2 seconds** backoff. Exponential backoff saturates at **4 seconds** when a
caller explicitly increases the attempt limit. There is one retry loop, no
tenacity, hidden transport retries, publication polling, or rediscovery loop.

| Condition | Exact behavior |
| --- | --- |
| Connection failure | Retry with `transport_failure`. |
| Connect/read/write/pool timeout | Retry with `timeout`; typed internal reason distinguishes phases. |
| Read error / remote protocol interruption | Retry with `incomplete_body`; discard all bytes from that attempt. |
| HTTP 500/502/503/504 | Retry with `http_failure`; exhaustion returns `retry_exhausted`. |
| HTTP 429 | Retry with `rate_limited` only within attempts and remaining operation budget. |
| Provider-classified 404 | Return `unavailable` with `not_found`/`not_listed`, full original source/request context, no retry, and no payload. |
| Unclassified 404, permanent/unclassified 4xx | Return `permanent_failure` / `http_failure` after one attempt. |
| Other statuses, including unselected 5xx and redirects | Fail closed as permanent HTTP failure. Only 200 is a successful report. |
| TLS failure | Recognize chained SSL errors; permanent `tls_failure`, never retry or disable verification. |
| Invalid configuration/source/locator/scheme | Raise safe `ExecutionError` before request I/O. Closed `reason` distinguishes configuration, invalid source, scheme, and locator under the existing `invalid_locator` contract category. |
| Oversized body | Permanent `size_limit`; no retry or successful payload. |
| Deadline/budget exhaustion | Controlled `budget_exceeded`; another attempt is possible only if the operation budget and backoff permit it. No attempt starts after exhaustion. |
| Empty/HTML/malformed complete 200 body | Retrieve and archive unchanged; content validation belongs after archival, outside HTTP retries. |
| Unsupported encoding | Preserve valid encoding observations and raw bytes. `require_identity_encoding` raises `unsupported_encoding` at the later parser precondition. Invalid/unrepresentable encoding observations fail closed without retry. |
| Local missing/unreadable file | Raise `ExecutionError(local_failure)` with distinct missing/unreadable reasons; no HTTP loop. |
| Archive permissions/I/O/metadata failure | Raise `ArchiveError(archive_failure)`; no successful persistence result or HTTP retry. |
| Existing payload/event corruption/conflict | Raise `ArchiveError(integrity_failure)`; never replace it. |
| Invalid archive path | Raise `ArchiveError(invalid_locator)` with `path_validation` reason. |
| Replay corruption/missing history | Raise `ReplayError`, preserving the stable integrity/archive category and a replay-specific reason. No fallback acquisition. |

Exception messages contain only enum values. Library causes remain chained for
debugging and are never supplied to the logger. Failures represented by contract
results expose only their stable error category, not exception text.

## E. Timeout/deadline/size behavior

Defaults are **10 seconds per connect/read/write/pool phase**, **30 seconds per
attempt**, and **93 seconds for the complete operation**, including backoff.
The last value accommodates three 30-second attempts plus 1/2-second waits;
it remains an independent finite ceiling for custom attempt counts. Stage 1
`INGESTION_TIMEOUT_SECONDS`, `INGESTION_MAX_ATTEMPTS`, and
`INGESTION_BACKOFF_SECONDS` are used by `RetryPolicy.from_settings`.

At each attempt, phase timeouts are clamped to the attempt/operation remainder.
The default network backend further recomputes the remaining timeout before
each socket connect, TLS, read, and write. This covers repeated short reads
inside response headers/protocol events, in addition to checks before/after raw
body chunks. The same injected monotonic clock controls operation and attempt
accounting. Tests use advancing clocks and fake sleepers, never actual sleep.

As with synchronous HTTPX itself, OS name resolution must honor the host's
resolver behavior; Python socket timeouts cannot forcibly preempt a stalled OS
resolver. Arbitrary injected transports/backends must honor their timeout
contract. This is application deadline accounting, not hard real-time process
preemption. No background acquisition worker is left running after a deadline.

The generic HTTP/local default is **4 MiB (4,194,304 bytes)**, an injectable code
policy rather than another environment setting. It is deliberately conservative
for report acquisition; future discovery/download adapters can select an
explicit smaller/larger finite bound. HTTP memory is bounded by that payload
limit plus transport chunks and temporary immutable byte copies; no decoded
expansion occurs. Actual streamed bytes determine the limit even when
Content-Length is absent or misleading. A present Content-Length must also
match the complete observed byte count. Archive metadata loads are capped at
64 KiB; archive payload loads read in bounded chunks through expected length
plus one and verify length/hash.

Redirect bound is **zero**: all redirects fail closed without following or
reading their bodies. This also avoids HTTPX's automatic redirect-body reads.

Retry-After supports trimmed nonnegative integer delta-seconds. Enormous valid
numbers saturate before conversion and fail the finite operation-budget check;
they never trigger a giant sleep or an early fallback retry. Invalid,
fractional, negative, and HTTP-date values use the finite exponential fallback;
HTTP-date interpretation is not implemented. A valid delay is at least the backoff delay and must be strictly
less than the remaining operation budget. If it cannot fit, return controlled
rate-limit exhaustion immediately, without sleeping or retrying earlier than
the requested delay. A sleeper that overshoots cannot cause another attempt.

## F. Exact-byte handling

HTTP requests explicitly send `Accept-Encoding: identity`. Retrieval exclusively
uses `Response.iter_raw()`, bypassing HTTPX content decompression. HTTP transfer
framing is removed by the protocol layer; encoded body representation bytes
remain unchanged. No charset decoding, text property, newline normalization,
automatic compression handling, or parser transformation occurs.

SHA-256 and byte length describe these exact bytes. Tests cover LF, CRLF,
non-ASCII/binary bytes, empty content, invalid compressed bytes, real gzip, and
stacked encoding observations. Valid non-identity bodies remain archivable;
the supplied encoding precondition makes unsupported plain-byte parsing explicit.
Content-Type parameters are reduced to the MIME token allowed by Stage 2;
this changes metadata only, never payload bytes. Optional malformed MIME/ETag/
Last-Modified observations are omitted independently. Invalid encoding metadata
fails closed rather than masquerading as identity encoding.

Interrupted, oversized, length-inconsistent, or preconsumed responses never
become successful raw reports. Archive publication is separate from acquisition
and cannot accidentally persist partial attempt bytes.

## G. Archive design

Default root remains `data/raw`; custom roots must also be excluded from Git.
The existing ignored data directory is unchanged. Layout:

```text
<root>/<source>/<report>/<YYYY-MM-DD>/sha256/<64-hex-sha256>/
  payload.bin
  retrievals/<retrieval-event-uuid>.json
  parses/<parse-event-uuid>.json
```

Content identity remains `(source_id, report_id, delivery_date, sha256)`.
Revision, acquisition timestamp, ETag, and Last-Modified do not enter it.
Same bytes under a different revision reuse the payload; changed bytes under
the same filename/revision get another hash directory.

Writers create private `mkstemp` staging files in the destination directory,
write/flush/fsync the complete bytes, set a read-only mode, then atomically
publish using `os.link(..., follow_symlinks=False)`. There is no overwrite-capable
rename or existing-object write. The destination directory is fsynced after a
new link. Existing destinations are compared with the intended bytes; payloads
are additionally loaded and hash/length verified before metadata success.

Concurrent identical writers have one immutable payload winner; losers verify
and reuse it. Distinct acquisition events can then be added independently.
Identical concurrent event writes are idempotent; conflicting concurrent event
writes yield one immutable winner and one integrity failure. Exceptions and
interruptions clean their staging files. A process killed before cleanup can
leave a private staging file, but never a partially published complete object.

Absolute/traversing paths and symlinks below the configured root are rejected.
The configured root/tree must be trusted and not writable by hostile local
users; directory-swap attacks, external owner modifications, WORM guarantees,
and network-filesystem semantics are outside this local storage boundary.
The filesystem must support same-filesystem hard links and directory fsync;
unsupported primitives fail explicitly instead of falling back to overwrites.

## H. Provenance persistence

Acquisition metadata is validated and enriched only with its correct archive
reference. The original completion timestamp/event UUID/source context remain
unchanged. Each acquisition has its own UTF-8 JSON file, using sorted keys,
compact separators, deterministic contract representations, and no arbitrary
metadata/header mapping. Only allowlisted HTTP observations are persisted.

Parse events use the same immutable publication mechanism in a separate
directory. Their raw/archive linkage and existing acquisition event are checked
before publication; parse IDs cannot equal their acquisition ID. Parse writes
never alter acquisition metadata.

Repeated identical event bytes reuse the event; conflicting bytes under the
same path/UUID raise integrity failure. There is no shared mutable manifest or
latest pointer. Metadata failure prevents persistence success, even when a
complete orphan payload has already been safely published. A subsequent explicit
retry can recover by verifying/reusing that payload.

Stage 1 logging changed only to allow six required event names: retry scheduled,
retry exhausted, archive integrity error, retrieval provenance persisted, replay
started, and replay integrity failure. Existing retrieval/archive/reuse/replay
completion events remain in use. Context contains only controlled identifiers,
attempts, error codes, and content references; no URLs, headers, payloads, models,
configuration objects, or raw exception strings are logged.

## I. Replay

Replay accepts an `ArchiveReference` and original acquisition UUID, loads exact
bytes, recomputes SHA-256, checks length, and loads acquisition JSON through
`RetrievalProvenance.model_validate_json`. It verifies archive/raw/event linkage
and successful original acquisition. Missing/corrupt bytes or metadata fail
explicitly, without fallback network work. No `model_construct` is used.

The returned `RetrievalResult` retains the original acquisition UUID and UTC
completion time. Replay has no network client, retriever, clock, or UUID factory.
It does not write any raw or acquisition file. A future Stage 4 parser consumes
this payload/provenance with explicit `parsed_at` and a new `parse_event_id`,
then persists its separate event with `RawArchive.persist_parse`.

Integration tests use only a synthetic parser to demonstrate the existing
`Parser` signature, stable normalized values/business identities, and separate
new parse events without changing acquisition history. No source parser ships
in production code in this stage.

## J. Contract adjustments

Exactly one compatible Stage 2 adjustment:

- `HttpObservations.content_encoding` now accepts a comma-separated ordered
  list of the already permitted coding tokens, up to 128 total characters;
  individual tokens retain the 32-character bound. The scalar string field,
  nullability, previous valid single-token inputs, and JSON representation stay
  unchanged. No protocol, error enum, identity, or other schema changed.
- Required because a valid response such as `Content-Encoding: gzip, br` could
  not previously be represented while preserving both raw bytes and its encoding
  observation for later parser rejection. Rejecting that valid complete response
  before archiving would contradict the accepted exact-byte/content boundary.
- This is bounded validation widening, not a new DTO/field or encoding decoder.
  Contract regression tests cover existing singles, ordered lists, JSON round
  trips, malformed delimiters/newlines, per-token limits, and the total limit.
  HTTP/integration tests prove stacked encoding bytes survive archival/replay
  and produce an explicit later encoding failure without transport retries.

## K. Tests

Focused Stage 3 command:

```bash
python -m pytest tests/unit/ingestion tests/integration/test_stage3_flow.py -q
```

**215 passed**, including parameterized cases:

| File | Count | Categories |
| --- | ---: | --- |
| `tests/unit/ingestion/test_http.py` | 107 | Exact bytes, metadata, all required transport/HTTP classifications, three-attempt ceiling, 1/2-second waits, rate limits, sizes, deadlines, and contract encoding regression. |
| `tests/unit/ingestion/test_archive.py` | 47 | Content/revision preservation, corruption/length/hash/missing/unreadable/path failures, staging/interruption, concurrent writes, metadata/idempotency/conflicts, and replay history. |
| `tests/unit/ingestion/test_local_retry.py` | 35 | Exact local bytes/null HTTP, missing/unreadable/unsafe paths, limits, policy/settings validation, and no HTTP/archive side effects. |
| `tests/unit/ingestion/test_transport.py` | 10 | Raw HTTP framing, incomplete wire responses, slow headers/body, socket budget shrinking, verified TLS context, and no construction I/O. |
| `tests/unit/ingestion/test_execution_logging.py` | 5 | Actual failure paths, safe event visibility, chained causes, and synthetic secret non-disclosure. |
| `tests/integration/test_stage3_flow.py` | 11 | Generic acquisition/storage/replay/synthetic parse events, complete content failures, encoding boundaries, interrupted/oversized reports, archive failure isolation, and local acquisition. |
| **Stage 3 focused** | **215** | Fully mocked/offline. |
| Existing Stage 1/2 suite | 297 | Retained unchanged and passing. |
| **Full suite** | **512** | No failures, skips, or live tests. |

Network-denial fixtures are scoped to the new Stage 3 unit/integration tests,
blocking socket connect, connection creation, and DNS lookup. HTTPX
MockTransport and httpcore MockBackend/fake streams are used exclusively.
Filesystem roots are pytest temporary directories; downloaded datasets and
real provider fixtures were not added. Repository-wide denial remains Stage 5.

## L. Validation evidence

Named environment: `iberian_shakti`, Python 3.12.9;
`/home/home/.pyenv/versions/iberian_shakti/bin/python`.
Installed HTTPX 0.28.1, httpcore 1.0.9, Pydantic 2.14.1. No installation or
dependency/tool configuration change was required.

| Command | Result |
| --- | --- |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `51 files already formatted` |
| `mypy src` | `Success: no issues found in 27 source files` |
| `python -m pytest` | `512 passed` |
| Focused command in K | `215 passed` |
| `git diff --check` | Exit 0, no output. |

Reviewed `git status --short`, `git diff --stat`, and `git diff`; also inspected
untracked additions explicitly because ordinary Git diffs omit them. Added-file
diff/whitespace checks were run separately. Changes are restricted to the paths
in B. No network request or external resource operation was performed.

## M. Scope confirmation

Stage 3 only. No OMIE URL construction, discovery, filename/calendar policy,
report parsing, provider fixture/live validation, or other Stage 4+ production
implementation was introduced. The normalized example is solely a synthetic
test parser. No scheduler, async execution, future provider implementation,
Snowflake, dbt, features, ML, API/dashboard, Terraform, cloud, Kafka, or
Kubernetes work was added.

No credentials or real secrets were used, exposed, or committed. No raw dataset
was added to Git. No branch, commit, push, cloud discovery, or external/paid
resource modification was performed. Work remains uncommitted on `main`.

## N. Remaining Phase 1 work

- Stage 4: OMIE resolution/bounded discovery, parser/calendar profiles,
  representative fixtures, and complete-report validation.
- Stage 5: remaining edge cases/redaction and generic end-to-end integration,
  plus the repository-wide default offline network guard.
- Stage 6: explicitly opted-in live smoke command and separately recorded result.
- Stage 7: operational/developer documentation and final verification against
  the existing accepted Phase 1 criteria.

## O. Stage verdict

**PASS**

Applies only to Phase 1 Stage 3. Stages 4–7 remain pending. Operational limits
are the documented HTTPS-only/zero-redirect policy, numeric Retry-After subset,
trusted local hard-link filesystem, host resolver/backend timeout behavior,
and absence of live-provider validation in this stage.
