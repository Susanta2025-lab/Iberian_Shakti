# Phase 1 Stage 5 — Offline enforcement and failure-path hardening

Date: 2026-10-26. Branch: existing `main`. Baseline: `fdb7098`
(`feat: add OMIE resolution parsing and validation`), clean working tree,
700 passing tests in the named `iberian_shakti` Python 3.12.9 environment.

## A. Stage objective

Hardened the implemented request → resolution/discovery → bounded acquisition
→ immutable raw/archive provenance → strict OMIE parsing → parse provenance
→ offline replay path. Added 203 deterministic regression cases and a shared
pytest network boundary. Existing production components and identities remain
unchanged. The accepted [Phase 1 baseline](phase_1_readiness_assessment.md),
Stages 2–4 evidence, ADR 0001 and ADR 0002 remain authoritative. No readiness or
architecture reassessment or replacement acceptance checklist was created.

## B. Files changed

Twelve paths: eight additions (including this report), four modifications.

| Exact path | Purpose |
| --- | --- |
| `tests/conftest.py` | Install session-wide offline enforcement before test collection; undo at pytest shutdown. |
| `tests/unit/test_offline_guard.py` | Collection-time denial, DNS/socket/HTTPX denial, and mock compatibility proofs. |
| `tests/unit/ingestion/test_stage5_archive.py` | Low-level publication faults, explicit recovery, staging isolation, corruption, replay linkage and concurrent parse/content events. |
| `tests/unit/ingestion/test_stage5_http.py` | Exact retry ceilings, remaining-budget boundaries, streamed deadlines, duplicate Content-Length and redirect handling. |
| `tests/unit/ingestion/test_stage5_redaction.py` | Synthetic secrets across configuration/locator/transport/header/exception/archive/replay paths; raw identity invariants. |
| `tests/unit/ingestion/omie/test_stage5_boundaries.py` | Additional strict grammar, precision, calendar, listing limits and encoded/adversarial link cases. |
| `tests/integration/test_stage5_flow.py` | Real-component exact/latest/retry/unavailable/content/revision/replay/persistence/recovery/environment scenarios. |
| `tests/unit/ingestion/conftest.py` | Remove the redundant narrower Stage 3 network guard. Existing synthetic fixtures retained. |
| `tests/unit/ingestion/omie/conftest.py` | Correct the fixture module description to reference repository-wide denial. |
| `tests/integration/test_stage3_flow.py` | Remove the redundant module-local network guard; preserve every test/assertion. |
| `tests/integration/test_stage4_omie_flow.py` | Remove the redundant module-local network guard; preserve every test/assertion. |
| `docs/codex/reports/phase_1_stage_5_report.md` | This implementation and validation evidence. |

## C. Repository-wide offline enforcement

Root `tests/conftest.py` uses `pytest_configure` and a session-owned
`pytest.MonkeyPatch`, retained in pytest's configuration stash. Unlike a
test-scoped autouse fixture, this applies during collection and session fixture
execution as well as every unit, contract and integration test. Pytest shutdown
restores the patched APIs with `pytest_unconfigure`.

Blocked APIs:

- `socket.create_connection`, `getaddrinfo`, `gethostbyname`,
  `gethostbyname_ex`, `gethostbyaddr`, `getnameinfo`, and `getfqdn`.
- Socket `connect`, `connect_ex`, `send`, `sendall`, `sendto`, and `sendmsg`
  where supported, covering connected and unconnected outbound use.
- `httpx.HTTPTransport.handle_request` and
  `httpx.AsyncHTTPTransport.handle_async_request` fail before real backend work.
  Custom transports still encounter the shared socket/DNS boundary.

Denial raises an immediate assertion with a static safe diagnostic, without
including the attempted target. There is no environment switch, marker or
pytest option enabling live access. A collection-time assertion and 16 guard
tests verify denial without opening a real socket or depending on internet
availability. Direct patched socket methods are called without a live descriptor.
HTTPX MockTransport, httpcore MockBackend/fake streams, local files, parsing,
archive/replay, synthetic clocks and sleepers remain functional throughout the
suite. This is protection against accidental Python test network use, not an
OS sandbox for malicious native code or independently launched processes.

## D. Redaction/security hardening

Reviewed configuration, HTTP/listing acquisition, adapter/parser, archive,
replay, runner and the managed JSON logging boundary. Added regression tests
using synthetic URL userinfo, query tokens, signed URLs, Authorization/bearer
text, cookies, API keys, passwords, rejected locator/environment values,
transport/OS exception messages and malformed HTTP observations.

Tests actively log failures with exception/stack information and structured
validation-error objects. Managed output excludes unchecked exception causes,
tracebacks, rejected input, arbitrary fields, raw rows and listing bodies.
Internal chained causes may remain available; application output stays within
the existing event/context allowlist. No event was added.

Persisted retrieval JSON excludes transport query strings, arbitrary response
headers, cookies and authorization. MIME parameters are discarded; invalid
optional ETag/Last-Modified observations are omitted. Invalid encoding metadata
fails safely instead of pretending the body has identity encoding. The safe
public locator remains intact. The existing four HTTP observation fields retain
their documented semantics; they are not arbitrary metadata containers.
Raw diagnostic payload bytes remain deliberately preserved, independently of
the safe metadata/logging boundary. No secret leakage was found in tested paths;
no production redaction correction was required.

## E. Archive/provenance hardening

Added a 24-case fault matrix: payload, retrieval-event and parse-event
publication each encounter directory creation, staging creation, partial write,
flush, file fsync, chmod, atomic link and directory fsync failures. Each raises
the existing safe `archive_failure` category with the appropriate archive-I/O
or metadata reason. Existing permission/missing/unreadable tests remain active.

Directory fsync failure can occur after a complete object is linked. The call
still fails; callers receive no ingestion success. A later explicit persistence
attempt verifies and reuses completed objects without replacing bytes/inodes.
Retrieval metadata failure can leave an orphan payload, which is insufficient
for replay until original acquisition provenance is explicitly persisted.

Abandoned partial staging files cannot satisfy payload loads or parse-event
preconditions and do not affect verified loads. Interrupted staging cannot
damage an existing payload. Failed writes clean their own staging files; no
background cleanup or automatic corruption repair was introduced.

Existing and new tests cover corrupt payloads, retrieval/parse JSON corruption,
conflicting event content, missing/unreadable content and verified orphan reuse.
Prior object bytes/inodes are checked after faults and recovery. Corrupt
immutable events remain untouched and raise `integrity_failure`.

Existing concurrent identical payload/acquisition and conflicting acquisition
tests remain. New barrier-synchronized races cover identical, independently
identified and conflicting parse events, plus simultaneous changed-content
versions. Results retain one object per content identity, independently valid
events, one winner for a conflicting event path/UUID, no overwrite and no shared
mutable manifest.

## F. Retrieval/discovery hardening

The existing retry engine is unchanged. Added explicit first/second/third
success and exhaustion matrices for 503, timeout and interrupted-stream failures,
with exactly 1/2-second waits and zero fourth attempt. Added Retry-After less
than/equal to/greater than the actual remaining budget, fallback backoff at or
beyond that remainder, and a streamed attempt deadline followed by successful
recovery. Existing invalid Retry-After, operation oversleep, size-boundary,
misleading length, encoding and phase-timeout coverage remains active.

Only complete HTTP 200 succeeds, including an empty body subsequently subject
to parsing. Additional success-like/unclassified statuses fail permanently.
Redirects neither follow secret-bearing locations nor iterate redirect bodies.
MockTransport duplicate Content-Length declarations fail closed; real h11
framing over MockBackend accepts identical declarations after protocol
validation and rejects conflicting declarations. No retry classification widened.

Discovery tests now hit exactly 1 MiB / one byte over and exactly 10,000 anchor
candidates / one over, with a single logical listing acquisition. Candidate
tests use short irrelevant links so the byte limit does not mask the candidate
limit. A 128-character valid filename exercises a large numeric revision.
Encoded paths, double encoding, injected/duplicate query parameters, invalid
dates and external/unexpected origins cannot select the decoy revision. Valid
query escaping is decoded then reconstructed into the canonical safe locator.
Existing numeric .9/.10, deduplication, invalid revision, malformed/irrelevant
HTML, pagination/partial coverage, absence/range and transport exhaustion tests
remain active. No revision probing, extra page traversal or rediscovery loop.

## G. Parser/calendar hardening

Added header-only/terminator-only bodies, header/row whitespace, duplicate final
and extra periods, data after marker, repeated markers, negative/boolean/quoted
periods, quoted/boolean prices, unsupported precision and a bounded 10,000-digit
malformed price. Signed zero and exact decimal representations are preserved.
CR-only, BOM and non-ASCII EOF input fail. Mixed LF/CRLF is already supported
as unambiguous occurrences of the two accepted separators; no grammar change.

Synthetic complete reports reject modern 24-period, legacy 96-period, wrong
transition-day and wrong DST counts. Calendar checks cover the day before/on/
after resolution transition and spring/autumn DST, winter/summer and leap days.
They verify full local-midnight coverage, UTC duration/continuity, both autumn
folds and the absent spring hour. Existing missing Europe/Madrid timezone tests
remain active. No fixed CET offset or timezone dependency was introduced.

## H. Revision/republication behavior

The full runner and subsequent replay verify all four combinations:

| Acquisition pair | Raw storage | Provenance/normalization |
| --- | --- | --- |
| Same revision, same bytes | Reuse one SHA object. | Independent acquisitions/parses; deterministic normalized values. |
| Different revision, same bytes | Reuse one SHA object. | Distinct observed revision, unchanged normalized content identity. |
| Higher revision, changed bytes | Retain two SHA objects. | Separate acquisition/parse history and traceable normalized versions. |
| Same revision, changed bytes | Retain two SHA objects. | Republishing does not overwrite or collapse either version. |

Retrieval time, event UUID, revision, ETag, Last-Modified and HTTP/local status
metadata do not change raw identity. Replay time and parse UUID do not change
business values/identity. A changed explicit parser version changes normalized
content identity without changing raw or business identity; the existing
normalized identity explicitly includes the fixed supported schema `1.0.0`.
No identity or schema-version definition changed.

## I. Replay hardening

New tests reject wrong source/report/date/archive linkage without modifying
history. Existing missing/modified payload, length/SHA mismatch, missing event,
corrupt/oversized JSON and mismatched event/archive cases remain active.
Both valid and malformed/unsupported-encoding bodies replay through the actual
OMIE parser, retaining original retrieval provenance. Independent failed parse
attempts persist separate zero-record failure events. Integration tests forbid
HTTP client/retriever use while replaying revised content and recovering
already-acquired content.

A replay parse-event persistence failure raises an archive error and leaves
original raw/acquisition/parse files intact. Retrying persistence explicitly
adds the new event. Replay never replaces raw objects, rewrites acquisitions or
fabricates missing retrieval history.

## J. End-to-end integration

The new integration module contains 26 cases across the actual existing
adapter/retriever/archive/parser/runner components:

- Exact revision and latest-observed highest numeric selection, with success on
  each possible attempt and controlled exhaustion; successful acquisition invokes
  archive/parser once.
- Exact/discovered 404 unavailability; listing schema failure/exhaustion never
  executes report parsing or creates successful raw history.
- Empty/malformed/unsupported/stacked-encoding complete reports preserve successful
  acquisition and raw bytes while persisting zero-record parse failures.
- All four revision/republishing combinations, followed by offline replay of
  each independent acquisition with deterministic normalized output.
- Payload publication failure, retrieval metadata failure before parsing, and
  parse metadata failure after parsing; none returns ingestion success or retries
  HTTP. Explicit offline recovery reuses verified acquired bytes.
- Replay parse-event persistence failure and later explicit persistence recovery.
- Parser version identity separation, and complete local ingestion with provider
  and ingestion environment settings absent and an ignored invalid `.env`.

Mocks wrap real components to observe failure ordering and invocation counts;
they do not substitute an alternate parser, archive or retry engine.

## K. Production code corrections

None. Comprehensive regression tests did not demonstrate a production defect
requiring a change. No source, contract, dependency, event allowlist, identity,
parser grammar, retry classification or architecture change was made. The missing
repository-wide pytest guarantee was implemented entirely in test configuration.

## L. Tests

Focused Stage 5 command, including broader ingestion regressions and guard tests:

```bash
python -m pytest tests/unit/ingestion tests/integration tests/unit/test_offline_guard.py -q
```

**606 passed**, zero skipped/failed. Stage 5 adds 203 cases:

| New test module | Cases |
| --- | ---: |
| `tests/unit/test_offline_guard.py` | 16 |
| `tests/unit/ingestion/test_stage5_archive.py` | 37 |
| `tests/unit/ingestion/test_stage5_http.py` | 33 |
| `tests/unit/ingestion/test_stage5_redaction.py` | 31 |
| `tests/unit/ingestion/omie/test_stage5_boundaries.py` | 60 |
| `tests/integration/test_stage5_flow.py` | 26 |
| **New Stage 5 cases** | **203** |
| **Full suite, including all 700 prior cases** | **903** |

Full command: `python -m pytest` → **903 passed**, zero skipped/failed,
**zero live tests executed**. Environment: named `iberian_shakti`, Python 3.12.9.

## M. Validation evidence

| Exact command | Result |
| --- | --- |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `72 files already formatted` |
| `mypy src` | `Success: no issues found in 32 source files` |
| `python -m pytest` | `903 passed` |
| Focused command in L | `606 passed` |
| `git diff --check` | Exit 0, no output. |
| `pre-commit run` | Exit 0; all hooks skipped because the index contains no staged files. |
| `pre-commit run --files <all 12 paths in B>` | All applicable hooks passed; YAML/TOML hooks have no matching changed files. |
| `pre-commit run end-of-file-fixer --files <all 25 OMIE data fixtures>` | Skipped all protected fixtures as configured. |

Initial sandboxed `pre-commit run` failed because Git index-lock and hook-cache
paths are read-only there. The requested command was rerun successfully with
approved escalation; this did not commit, stage or push anything. Explicit
`--files` validation covers the unstaged and untracked work without staging it.
Hook results and working-tree content were checked for unnoticed mutations.

Reviewed `git status --short`, `git diff --stat`, `git diff`,
`git diff --cached --stat` and `git diff --cached`, together with every untracked
addition (ordinary diffs omit untracked content). Four existing test files have
unstaged changes; eight additions remain untracked. Both cached diffs are empty.
No existing assertion was removed or weakened. No hook-generated changes remain
unaccounted for.

## N. Fixture integrity

All 25 fixture checksums match the authoritative manifest and all data-fixture
bytes match `HEAD`, including original CRLF and intentional malformed EOF state.
The inventory/checksum test passes in the full suite. Neither fixture bytes,
manifest, fixture documentation nor `.pre-commit-config.yaml` changed.
The exact `^tests/data/omie/` end-of-file-fixer exclusion is preserved and verified
with the actual hook. Protected fixtures were not normalized or rehashed.

## O. Remaining Phase 1 work

- Stage 6: explicitly opted-in live smoke validation and actual provider evidence.
- Stage 7: documentation and final acceptance against the existing Phase 1 criteria.

Existing support limits remain: one observed listing page cannot establish full
remote history; live DOM/availability/retention and unverified historical grammar
remain external uncertainties. Local archive guarantees assume the documented
trusted filesystem with hard-link/fsync support; OS resolver and injected backend
timeouts retain their Stage 3 limits. These were not expanded into new features.

## P. Scope confirmation

Stage 5 only. No live provider request, Stage 6 CLI/test, scheduler, provider
expansion, Snowflake/dbt/features/ML/inference/API/dashboard, deployment,
infrastructure or paid-resource action. No branch, commit or push. Work remains
on the original `main` working tree, uncommitted and unstaged for user review.

## Q. Stage verdict

**PASS**

Applies only to Phase 1 Stage 5.
