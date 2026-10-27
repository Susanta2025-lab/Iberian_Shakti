# Phase 1 Stage 7 — Final acceptance and closure

Verification date: 2026-10-27 (Europe/Lisbon). Existing branch: `main`.

## A. Purpose

Stage 7 performs final acceptance against the 22 criteria already established
in [the authoritative Phase 1 readiness assessment, §10](phase_1_readiness_assessment.md).
This is **not another readiness assessment** or architecture assessment.
**No new acceptance criteria were created.** Section D preserves every original
criterion verbatim and maps it to current implementation and verification.

**No live provider request was made during Stage 7.** No OMIE DNS lookup,
download, discovery, external-provider contact, dependency download, cloud
activation or paid-resource action occurred. The authoritative
[Stage 6 report](phase_1_stage_6_live_validation.md) supplies historical live
evidence; retained local objects were checked offline without modification.

## B. Baseline

```text
f15c9a2 feat: add explicit live OMIE smoke validation
```

Initial working tree and index were clean on existing `main`, eight commits
ahead of the locally stored `origin/main`. No fetch was performed; this is not
a claim about current remote state. Python 3.12.9 is selected by `.python-version`
in the named pyenv environment `iberian_shakti`. The existing source/test/tool
configuration, `.env.example`, accepted ADRs and Stage 1–6 evidence were inspected
before acceptance. Stage 7 makes documentation-only changes.

## C. Phase 1 implementation chronology

Exact messages verified from local Git history, oldest first:

| Commit | Exact message | Role |
| --- | --- | --- |
| `559077e` | docs: record Phase 1 readiness assessment | Original scope, decisions and acceptance criteria. |
| `1cab3c2` | feat: establish Phase 1 ingestion foundation | Stage 1 dependencies, ADRs, configuration and logging. |
| `b5092b5` | feat: add shared ingestion and market contracts | Stage 2 immutable contracts/protocols and generic calendar helper. |
| `e9bedab` | feat: add retrieval archive and replay foundation | Stage 3 reusable execution and storage. |
| `fdb7098` | feat: add OMIE resolution parsing and validation | Stage 4 concrete integration, fixtures and runner. |
| `09e4890` | test: harden Phase 1 ingestion and offline enforcement | Stage 5 network boundary and failure/revision/replay coverage. |
| `6290648` | test: complete pre-live OMIE engineering audit | Four corrections and default-transport regression coverage. |
| `f15c9a2` | feat: add explicit live OMIE smoke validation | Stage 6 CLI, offline CLI cases and successful live/replay evidence. |

ADRs were co-recorded with the Stage 1 foundation, before corresponding shared
contract/provider/execution implementations in Stages 2–4. Git establishes this
commit chronology, not an intra-commit editing timestamp. No history was changed.

## D. Acceptance traceability matrix

The criterion column below is copied directly from the original §10 checklist,
in order. Row numbers are traceability references only. Source paths are beneath
`src/iberian_shakti/`; unqualified test filenames refer to the existing modules
under `tests/unit/ingestion/` (OMIE-specific files under its `omie/` directory)
or the explicitly named contract/integration suites. All cited deterministic
tests ran in the full final suite. Reports supplement code/test/retained-object
verification rather than substituting for it.

| Criterion | Implementation evidence | Test/report evidence | Status |
| --- | --- | --- | --- |
| 1. ADRs 0001/0002 record the accepted source, market-period contract, execution/archive/provenance/replay, dependency, and test-isolation choices before corresponding implementation. | ADRs 0001/0002; Git records both in Stage 1 `1cab3c2`, before the Stage 2 contracts and Stage 3 execution/archive code. Source/calendar, HTTPX/Pydantic, local execution and isolation decisions remain consistent. | Read both accepted ADRs, Stage 1 tree/stat and subsequent commit history; no factual correction needed. ADR index already links both. | PASS |
| 2. One shared typed contract set lives in `contracts/`; common execution lives in `ingestion/`; OMIE-specific locator/parser/calendar rules live in `ingestion/omie/`. Future provider stubs remain untouched. | `contracts/{_base,ingestion,market,periods}.py`; reusable execution in `ingestion/`; provider identity/adapter/parser/calendar in `ingestion/omie/`. | `tests/contracts/`, calendar and actual-component integration tests; history diff confirms future provider/domain stubs untouched. | PASS |
| 3. Valid source requests support exact OMIE revisions and bounded latest-observed discovery. No hard-coded assumption that `.1` exists or that the index proves complete history. | `OmieAdapter.resolve`, `identity.resolved_source`, one-page `_Listing`; 1 MiB, 10,000 anchors, numeric maximum, explicit coverage/pagination outcomes; no probing. | `test_discovery.py` exact bypass, `.2` without `.1`, `.9`/`.10`, absent/uncovered/paginated cases; `test_stage5_boundaries.py` byte/candidate/adversarial cases. Latest observed is not complete remote history (§L). | PASS — DOCUMENTED EXTERNAL LIMITATION |
| 4. Anonymous public download mechanism works through an injectable synchronous client; local file retrieval and archive replay work offline. | Injectable synchronous `HttpRetriever`; `LocalFileRetriever`; `replay()` has only archive/reference/original-event dependencies. | Stage 6 exact/discovery observation plus read-only retained-archive reproduction (§F); local-file and no-client replay tests in Stages 3–5. Future public availability/access is not guaranteed (§L). | PASS — DOCUMENTED EXTERNAL LIMITATION |
| 5. All external calls have explicit finite phase timeouts, bounded attempt/operation duration, size limits, and bounded discovery. Selected transient failures use at most three total attempts with exponential backoff; permanent failures do not retry. | `RetryPolicy`, `HttpRetriever._acquire/_read`, `DeadlineTransport/Backend/Stream`; explicit finite phases, shrinking deadlines, size bounds, zero redirects/retries below the application loop. | `test_http.py`, `test_transport.py`, `test_stage5_http.py`, discovery tests and default-stack audit: default three total attempts, 1/2-second waits, budget/Retry-After boundaries. Accepted configurable attempt setting remains explicit; synchronous host resolver/backend preemption limitation retained (§L). | PASS — DOCUMENTED EXTERNAL LIMITATION |
| 6. Source-unavailable/not-yet-published behavior is explicit, preserves context, and produces neither zero-record success nor retry/polling storms. Missing historical revisions and unknown listing coverage are not misrepresented. | Provider-owned 404 classification; `ResolutionOutcome`/`RetrievalOutcome` distinguish not-found/not-listed, unknown coverage and failures. Runner returns without parsing unsuccessful acquisitions. | Discovery and Stage 4/5 integration cases assert no poll/rediscovery, no payload/parse, explicit request/revision context and no zero-record success; CLI unavailable exit 3. | PASS |
| 7. Raw archive preserves original body bytes unchanged under ignored `data/raw/` (or a documented external custom root), uses SHA-256 identity, and never replaces an archived payload or metadata event. | `iter_raw()` with identity request header; binary local reads; `RawPayload` hash/length; `LocalRawArchive._publish` stages/fsyncs then uses atomic no-replace `os.link` for payloads and events. | Raw gzip/CRLF/binary preservation, existing-object verification and concurrent writers in HTTP/archive/transport tests; ignored `data/raw/` confirmed; custom external root documented in runbook. Stage 6 retained body equals fixture. | PASS |
| 8. Identical replay/acquisition reuses content; differing content, including same-filename republishing, is separately retained. Concurrent writes, corruption, partial writes, and metadata failures have tested controlled behavior. | Content-addressed path excludes revision/event time. Independent immutable retrieval/parse events; changed same-filename bytes get new hashes; conflicting existing objects fail. | `test_archive.py`, 24-case publication fault matrix and concurrent parse/content tests in `test_stage5_archive.py`; four revision/content combinations and explicit recovery in `test_stage5_flow.py`. | PASS |
| 9. Retrieval provenance captures source/report/date, safe locator/filename, retrieval UTC time, status/attempts, byte length/hash/archive reference, and observed revision; parse provenance adds parser/schema versions and references the original raw acquisition. | Strict `RetrievalProvenance`, `HttpObservations`, `ParseProvenance`, linkage validators; persistence adds archive reference only after payload/event writes; parser/schema versions separate from acquisition. | Contract JSON/linkage/UTC tests; archive load/persistence tests; retained two acquisition and three parse events validate and reproduce exactly (§F). Unknown publication time stays null. | PASS |
| 10. Offline replay verifies content hash, makes no network call, retains original acquisition history, and produces deterministic normalized values/identities for a fixed parser/schema version. | `replay()` calls verified archive loads only and returns the original retrieval result; parser and new parse persistence are separate calls. | Stage 4/5 integration forbids client/retriever during replay and compares values/identities; wrong-link/hash/missing/oversized metadata cases; Stage 7 read-only reproduction with socket audit denial (§F). | PASS |
| 11. Parser validates the complete selected grammar and day, emits explicit typed content errors, and never drops bad rows or returns partial days. Complete malformed payloads remain archived for diagnostics. | `OmieParser.parse/_records`: strict ASCII, exact header, six fields plus trailing delimiter, matching valid date and sequence, terminal `*`, whole-day validation before record construction. Runner archives first. | Manifest-driven valid/malformed fixtures, final-row/precision/structure tests; complete empty/HTML/encoded/malformed body integration retains acquisition plus zero-record typed failed parse, without content retry. | PASS |
| 12. Both PT and ES records are emitted with correct column order, finite signed Decimal prices in EUR/MWh, and exact supported precision; no float intermediates or nonnegative-price restriction. | Direct `Decimal(pt)`/`Decimal(es)`; PT then ES mapping; shared `MarketPrice` finite Decimal validation and string JSON; EUR/MWh. | Original unequal-column legacy spring fixture checks all prices and six differing rows; signed/zero/precision lexical tests; contract rejection of floats/nonfinite values; no price caps. | PASS |
| 13. Normalized periods include delivery date, source period index, resolution, and UTC interval; no legacy hourly-only field or 24-period ceiling. Modern 96/92/100 and legacy 24/23/25 profiles, transition boundary, full-day coverage, and DST ambiguity are tested. | `MarketInterval`, `MarketPrice`, generic `market_day_intervals`; OMIE `profile_for/intervals_for` chooses Europe/Madrid and 2025-10-01 transition; independently converted midnights then UTC stepping. | All six profiles (24/23/25 and 96/92/100), transition, UTC bounds, both autumn folds, skipped spring hour, full-day coverage and modern-24-row rejection; clearly labelled complete synthetic legacy autumn fixture is present. | PASS |
| 14. Environment settings are minimal, documented, validated, and require no unrelated provider credentials; bad settings fail before I/O. No unnecessary runtime/test dependency is introduced. | `IngestionSettings` and explicit five-key `load_ingestion_settings`; `.env.example`; HTTPX/Pydantic v2 only new runtime dependencies, existing dev set retained. | 83 original configuration/logging cases remain; config tests prove no dotenv/I/O/unrelated key reads, invalid finite/range settings and frozen settings; full local integration beside invalid `.env` with credentials absent. | PASS |
| 15. Structured logging identifies report/attempt/outcome/content/parser with useful safe fields. Secret-bearing URLs, headers, exceptions, configuration, and validation input are redacted in every tested path, including metadata. | `SafeJsonFormatter`, closed events/scalar context, explicit `configure_logging`; controlled failure reasons and safe listing locator; allowlisted HTTP observations only. | `test_logging.py`, execution/OMIE logging tests, 31 Stage 5 redaction cases and default-stack diagnostic tests exercise synthetic secret-bearing URL/header/config/exception/validation/archive paths, no raw bodies or tracebacks. | PASS |
| 16. Small versioned fixture files/manifest are committed intentionally under `tests/data/omie/`; ignore rules permit them while excluding raw datasets and secrets. Synthetic/mutated fixtures are labelled. | 25 small byte/HTML fixtures plus README and manifest in `tests/data/omie/`; originals retain CRLF, synthetic/mutated purpose and parent labels; `/data/` ignored. | `test_manifest_inventory_and_hashes` checks full inventory and exact hashes; fixture paths tracked; source/manifest/fixture/hook bytes unchanged at Stage 7; EOF-fixer fixture exclusion preserved. | PASS |
| 17. Unit, contract, and mocked integration tests cover every behavior in §8, including revision preservation, retry limits, unavailability, provenance, logging, malformed content, DST, and replay. | Existing unit, contract and actual-component mocked integrations cover assessment §8 behavior, with injected clocks/sleepers, temporary roots, MockTransport and fake core/socket backends. | Full 968-case suite (§J), including revision/republication, failures, faults/concurrency, no partial parse, security, calendar, replay and environment independence. Default-stack audit covers real installed framing and exception mapping offline. | PASS |
| 18. Normal `pytest` succeeds with network disabled, uses no secrets/live source, and never invokes the live module. No meaningful test is weakened to make checks pass. | `tests/conftest.py` installs DNS/socket/HTTPX denial at `pytest_configure`, before collection, with no enable switch; shutdown restores it. | `test_offline_guard.py` collection assertion plus 16 denial/mock-compatibility cases; `python -m pytest` passes all 968 with no skips. CLI cases inject offline doubles; pytest never starts a real live acquisition. No test changes in Stage 7. | PASS |
| 19. Optional live module requires explicit `--live`, has a documented invocation/outcomes, uses no credentials for the verified route, and is excluded from pytest/pre-commit/automatic CI. A live run result or an explicit not-run/environment limitation is documented separately. | `live_smoke.run` refuses without `--live` before acquisition dependency construction; scalar summaries and explicit exits; fixture-root rejection. Separate module, absent from hooks/automatic CI. | 16 offline CLI cases; authoritative Stage 6 exact/discovery exits 0 and local replay; retained evidence independently verified (§F). Invocation/outcomes now documented in runbook; no new live request. | PASS |
| 20. README/architecture status, ADR index, and ingestion runbook describe actual implemented behavior, support limits, settings, raw paths, revision recovery, and replay. | Updated root/architecture/runbook catalog, new `docs/runbooks/ingestion.md`; existing ADR index correctly lists both accepted decisions. | Documentation checked against implementation, settings and exit codes; covers bounds, archive assumptions/paths, deliberate live use, unavailable/revision recovery and actual two-step replay/parse API. Links checked locally (§K). | PASS |
| 21. Final `ruff check .`, `ruff format --check .`, `mypy src`, `pytest`, and `git diff --check` pass in the intended Python 3.12 environment; complete diff/status reviewed. | Named `iberian_shakti` environment, Python 3.12.9; unchanged code/tests; repository-wide quality commands and complete staged/unstaged/new-file review. | Exact final results in §J; all applicable hooks pass on every changed path; diff/status and explicit new-file review accounted for; no temporary repository artifacts. | PASS |
| 22. No Snowflake/dbt/ML/serving/dashboard/cloud/infrastructure implementation, other provider implementation, paid-resource action, unsolicited commit, or push is included. | Stage 7 changes only five documentation paths; historical implementation history remains inside Phase 1 local scope. Future provider and platform stubs unchanged. | History/diff/status inspection; no external network/cloud operation, branch/index mutation, commit or push. Future phase work only listed (§M). | PASS |

Result: **22/22 satisfied** — 19 PASS and 3 PASS — DOCUMENTED EXTERNAL
LIMITATION (rows 3–5). No FAIL and no NOT APPLICABLE. These limitations already
fit the accepted bounded discovery/public observation/cooperative deadline
scope; none waives a missing implementation requirement.

## E. Stage-by-stage verification

| Stage | Current verification |
| --- | --- |
| Stage 1 (`1cab3c2`) | HTTPX and Pydantic v2 declarations remain. Explicit validated settings read only five ingestion/log keys, never dotenv or unrelated credentials. Managed structured logs omit unchecked messages, exceptions, raw payloads and rejected inputs. Original 83 settings/logging cases remain green. ADRs 0001/0002 and their index remain correct and unchanged. |
| [Stage 2](phase_1_stage_2_report.md) | One strict/frozen contract set covers request/resolution/listing/retrieval/archive/provenance/parser/ingestion results, normalized MarketPrice and synchronous protocols. UTC-aware timestamps, immutable tuples/bytes, Decimal prices and provider-neutral interval partitioning remain coherent. Listing refinements do not leak OMIE grammar into shared contracts. |
| [Stage 3](phase_1_stage_3_report.md) | Exact raw-byte streaming with identity request encoding, bounded single retry engine, finite phases/deadlines/size, zero redirects, explicit unavailable semantics; local-file retrieval, immutable SHA-256 payload/events, hash verification and offline replay. Atomic publication/concurrency/corruption/fault tests support ADR 0002. Runner persists raw and retrieval metadata before parsing, and parse metadata before returning. |
| [Stage 4](phase_1_stage_4_report.md) | Exact `marginalpdbc_YYYYMMDD.v` bypasses discovery; latest-observed reads one bounded page and compares numeric revisions without probing. Strict ASCII/header/six-field/terminal-marker/day validation emits all PT/ES records or none. Both use Europe/Madrid: before 2025-10-01, 60-minute 24/23/25 profiles; from that date, 15-minute 96/92/100 profiles. No fixed CET, float conversion, price nonnegativity rule or partial-day fallback. Malformed complete reports survive archival. |
| [Stage 5](phase_1_stage_5_report.md) | Repository-wide pytest DNS/socket/real-HTTPX denial is active from configuration/collection. MockTransport/fake backends still work. Fault matrix, concurrent events/versions, redaction, retries/deadlines, adversarial discovery, parser/calendar boundaries, four revision/republishing combinations, replay integrity and environment independence remain green. |
| [Pre-live audit](phase_1_stage_6_pre_live_engineering_audit.md) | All four corrections remain with regression coverage, detailed below. Default transport construction, installed core/h11 framing and exception translation execute over fake socket/TLS boundaries, not live providers. The historical GO verdict did not guarantee provider success. |
| [Stage 6](phase_1_stage_6_live_validation.md) | Separate `--live` CLI composes the production path; 16 offline cases retain its opt-in/configuration/summary/failure checks. Successful exact/discovery observations are supported by retained raw/provenance, fixture equality and all three reproduced parse results (§F). |

Pre-live corrections inspected in current code and
`tests/integration/test_pre_live_engineering_audit.py`:

1. Safe failure diagnostics: `_acquire` retains status, attempts, elapsed time,
   controlled reason and safe listing locator; formatter allows those bounded
   fields. Status, real-exception, discovery-failure and unsafe-field cases
   cover this correction, alongside the retained redaction suite.
2. Exposed `httpx.WriteError` maps to bounded retryable
   `transport_failure/connection_failure`. `test_httpx_write_error_is_connection_failure`
   remains. Installed core may suppress a GET write error while seeking a server
   response; this mapping test does not claim that every default GET exposes it.
3. Runner default parse time is captured after acquisition persistence;
   `test_default_parse_time_is_captured_after_acquisition_persistence` verifies
   stored retrieval exists before the clock is read. Explicit deterministic
   callers may still supply `parsed_at`.
4. `HttpObservations.content_encoding` accepts valid whitespace around commas
   while retaining bounds. `test_default_encoding_raw_preservation` includes
   `GZIP ,\tBR`, preserves body bytes and fails parsing explicitly afterward.

The complete requested Phase 1 chain is present: configuration/logging →
shared contracts → bounded HTTP/local retrieval and error/retry policy →
immutable raw/provenance → offline replay → OMIE identity/exact/discovery →
strict parser/Europe-Madrid normalization/PT-ES prices → ingestion runner and
malformed-report preservation → default offline boundary and failure/security/
archive hardening → explicit live smoke → recorded real success → offline
replay of live-acquired content. No required Phase 1 implementation remains.

## F. Live validation evidence

Historical observations come from Stage 6; they were **not repeated live**.

```text
exact live mode: PASS
discovery live mode: PASS
live-vs-fixture hash: identical
offline replay: PASS
```

| Observation | Exact revision | Latest observed |
| --- | --- | --- |
| Delivery date / revision | 2026-10-26 / 1 | 2026-10-26 / 1 |
| Selected filename | marginalpdbc_20261026.1 | marginalpdbc_20261026.1 |
| HTTP / report attempt / exit | 200 / 1 / 0 | 200 / 1 / 0 |
| Original bytes | 2637 | 2637 |
| Source periods / PT / ES / total | 96 / 96 / 96 / 192 | 96 / 96 / 96 / 192 |
| UTC coverage | 2026-10-25 23:00 → 2026-10-26 23:00 | Same |
| Parser / schema | omie.marginalpdbc 1.0.0 / 1.0.0 | Same |

Exact/discovery/replay content SHA-256:

```text
5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e
```

Stage 6 directly compared the acquired body with the committed fixture at
validation time; the 2,637 bytes were identical. Stage 7 confirms retained
payload/fixture equality again locally; fixtures have no change against HEAD.
The live listing structure was compatible at the recorded discovery observation,
selecting the same revision/filename/content and normalized output. Listing HTML
was ephemeral and not retained. **Listing physical-attempt count was not
independently recorded**; report attempt 1 must not be attributed to listing.

Archive states:

| Point | Payloads | Retrieval events | Parse events | Evidence |
| --- | ---: | ---: | ---: | --- |
| After two live acquisitions | 1 | 2 | 2 | Stage 6 operator observation and retained acquisition/parse pairs. |
| After offline replay | 1 | 2 | 3 | Stage 6 observation and current independently verified retained files. |

Stage 7 used a temporary read-only verifier outside the repository against
`/tmp/iberian-shakti-omie-smoke`. A Python socket audit hook and replaced DNS
helpers denied network use. No HttpRetriever was constructed. It validated both
retrieval JSON objects and all three parse JSON objects through current strict
contracts, verified the raw hash/length, invoked `replay()` and the same parser
with each stored event's ID/time, reproduced all stored parse provenance and
compared every normalized value excluding only parse UUID. All reproduced
96 periods, 96 PT, 96 ES and 192 records. Exact acquisition has one parse;
discovery acquisition has its original parse plus the separate replay parse.
Original retrieval identity/time/linkage was preserved. Before/after hashes
of every archive file were identical; no fourth parse event or new acquisition
was written. The historical exit codes and intermediate counts remain attributed
to Stage 6 rather than reconstructed shell executions.

## G. Final architecture state

Implemented locally:

```text
OMIE public source → SourceRequest
  → exact revision OR bounded latest-observed discovery
  → bounded HTTP retrieval → immutable raw archive → retrieval provenance
  → strict OMIE parsing → Europe/Madrid calendar normalization
  → PT / ES MarketPrice records → parse provenance

immutable archive + original retrieval provenance
  → verified offline replay → same parser → new parse event
```

Local-file retrieval shares the raw/provenance path without HTTP. Contracts,
common execution and provider rules retain separate ownership. No architecture
replacement or accepted ADR rewrite was necessary. The updated architecture
README distinguishes this implemented slice from the planned Snowflake
RAW → CURATED → FEATURES → training/registry/batch inference → SERVING →
API/dashboard platform. No scheduler, deployment or production service is implied.

## H. Security and safety controls

- Validated opaque safe locators exclude executable URLs, userinfo, query
  values, fragments and traversal; private transport URLs are not persisted.
- Explicit managed structured logging allows only known events and safe scalar
  context; no raw payload/HTML, whole configuration, unchecked exceptions,
  validation inputs, arbitrary headers or tracebacks. CLI summaries are separately
  allowlisted; the current CLI does not configure library logging handlers.
- HTTP metadata retains only bounded MIME/encoding, valid ETag and UTC
  Last-Modified observations. Optional invalid observations are omitted;
  unrepresentable encoding fails closed. Observations are not publication facts.
- TLS verification, identity raw streaming, finite budgets/size, zero redirects,
  no environment proxy credentials and zero underlying transport retries remain.
- Immutable no-replace payload/events and SHA-256 verification guard reproducibility;
  failed persistence never becomes ingestion success. Archive roots require a
  trusted local filesystem as documented in §L.
- Default pytest denies DNS/socket/real HTTPX use with no live escape switch.
  The separate module requires explicit `--live`, rejects fixture-root archival
  from repository-root invocation, and remains outside automatic hooks/CI.
- No secrets were used or exposed; no `.env`, private key or downloaded bulk
  dataset was added. No external or paid resource was contacted or modified.

## I. Reproducibility and provenance

Raw content identity is `(source_id, report_id, delivery_date, sha256)` over
unchanged original body bytes. New acquisitions have independent UUID/time/
revision/status observations; identical content reuses the payload. Different
bytes under either a new revision or an unchanged filename/revision are retained
separately. Revision labels, ETag, Last-Modified and retrieval time do not replace
content identity or prove provider immutability.

Parse events link original acquisition/raw/archive, explicit parser/schema
versions, a distinct UUID/time and outcome/count. Each MarketPrice references
its parse event. Normalized-content identity adds parser ID/version and schema
version to raw identity; business identity retains source/report/area/day/period/
duration. Replay retains the original acquisition, verifies raw content and
reproduces fixed-version values/identities. Explicit parsing can add a new parse
event without a new payload or retrieval event, supporting upgrades, reprocessing
and auditing. Corrupt/missing history fails without fallback network retrieval.

## J. Test and quality evidence

All checks ran offline in the named `iberian_shakti` Python 3.12.9 environment.
No dependencies, code, tests, fixtures, hook settings or accepted criteria changed.

| Command | Exact final result |
| --- | --- |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `78 files already formatted` |
| `mypy src` | `Success: no issues found in 33 source files` |
| `python -m pytest` | `968 passed in 7.11s`; 968 collected, zero failed/skipped. |
| `git diff --check` | Exit 0; no output after documentation whitespace correction. |
| `pre-commit run --files <all five Stage 7 paths>` | Exit 0: trailing whitespace, EOF, large-file and private-key hooks Passed; Ruff check/format and YAML/TOML hooks Skipped (no applicable changed files). |
| Retained live archive verification | Pass: exact fixture equality, typed history, three reproduced parses, network denied, archive unchanged. |

The full suite retains all original 968 cases. Historical Stage 1–6 reports keep
their historical counts. No tests were added just to validate reversible prose
changes, and no assertion was removed or weakened. Pinned hook repositories
and installed environments were checked in the existing local cache before
execution; no remote initialization/download was needed.

Final review includes `git status --short`, `git diff --stat`, `git diff`,
`git diff --cached --stat` and `git diff --cached`, plus explicit no-index content
and whitespace inspection of the two new Markdown files because ordinary diffs
omit untracked content. There are exactly three unstaged modifications and two
untracked additions (§K); nothing is staged. The Stage 6 archive remains outside
Git. Temporary verifier/generator scripts remain under `/tmp`, not the repository.

## K. Documentation changes

| Exact path | Change |
| --- | --- |
| `README.md` | Replace pre-implementation skeleton/zero-test status with actual Phase 1 capabilities, 968 offline tests, phase status, support limits, no dotenv loading, runbook and closure links. |
| `docs/architecture/README.md` | Document implemented local ingestion/replay and ownership, archival-before-parse, profiles/bounds; clearly label future end-to-end platform flow. |
| `docs/runbooks/README.md` | Link implemented ingestion runbook; preserve future catalog and correct offline/current-test/settings status. |
| `docs/runbooks/ingestion.md` | New focused operator/developer procedure: settings, default offline tests, mandatory deliberate live opt-in, safe archive roots, exits/bounds, revision/failure recovery, conceptual actual replay API and limitations. |
| `docs/codex/reports/phase_1_stage_7_final_acceptance.md` | This authoritative closure document and original-criterion traceability. |

The existing ADR index already links both accepted ADRs; it needs no change.
ADRs 0001/0002 and historical reports are unchanged. Repository searches checked
stale foundation/zero-test descriptions, pending live-validation statements,
old counts, implementation status and pytest-network instructions. Historical
statements remain historical; only current-facing stale documentation changed.
Local relative Markdown links in all five changed paths were checked, without
opening external URLs. All working-tree changes are explained above.

## L. External limitations

An **accepted external limitation** is uncertainty already outside the original
Phase 1 support envelope, with controlled behavior and explicit documentation.
An **engineering blocker** is a missing required capability or unresolved
implementation defect preventing acceptance. No engineering blocker remains.

Accepted limitations preserved from the assessment, ADRs and stage evidence:

- Future endpoint availability, future anonymous access, routing/DNS, TLS
  negotiation/trust behavior and certificate/provider policy can change.
- Future OMIE HTML/DOM changes may fail bounded discovery. One page cannot
  establish complete pagination, provider retention, complete historical
  revision coverage or a guaranteed latest-revision API. Exact revisions bypass
  listing uncertainty but do not guarantee a remote object exists.
- Publication time/minute/SLA and every prepublication status/body variant are
  unverified. Retrieval/Last-Modified times are not promised publication times.
- Same-filename mutation and changes between listing and retrieval remain
  possible; content addressing retains observed changed bytes without claiming
  remote filename immutability.
- Supported grammar is the tested strict ASCII numeric legacy/modern family,
  not every historical grammar or a contractual global charset. Original bytes
  for legacy autumn/transition dates remain unverified; labelled complete
  synthetic fixtures exercise those accepted profiles. Unknown future provider
  formats/codings/undocumented changes fail visibly rather than being guessed.
- Listing physical-attempt count and original listing HTML were not retained
  during Stage 6; successful discovery does not invent that missing evidence.
- Synchronous finite deadlines are cooperative with OS resolver/backend/socket
  behavior, not hard real-time process cancellation. Injected transports must
  honor their timeout/raw-stream/no-retry contract. Integer-only Retry-After
  support, zero redirects and finite separate listing/report budgets remain.
- Local archive immutability assumes a trusted tree and same-filesystem hard
  links/directory fsync, not hostile-user/WORM/network-storage guarantees.
  An interruption can leave private staging or a recoverable complete orphan;
  missing acquisition history is never fabricated. Host IANA data is required.
- Broad dependency ranges and no lockfile remain the accepted project model;
  future upgrades require compatibility revalidation against installed APIs.

These boundaries do not waive any original criterion or promise permanent
provider compatibility. Explicitly:

```text
Passing local tests does not guarantee successful live validation.
A successful live observation does not guarantee permanent provider compatibility.
```

## M. Deferred future work

No later phase was started or implemented:

| Phase | Deferred work |
| --- | --- |
| Phase 2 — Multi-Source Ingestion Expansion | REN, ESIOS, ENTSO-E, Open-Meteo and MIBGAS integration work, subject to its accepted scope. |
| Phase 3 — Snowflake Data Platform | Central data-platform objects, access and storage. |
| Phase 4 — dbt Transformation Layer | Transformations and data-quality models. |
| Phase 5 — Feature Engineering | Feature definitions and pipelines. |
| Phase 6 — Model Training & Evaluation | Baselines, training and evaluation. |
| Phase 7 — Model Registry & Batch Inference | Registry/governance and scheduled precomputed batch forecasts. |
| Phase 8 — API & Dashboard | FastAPI and presentation of persisted results. |
| Phase 9 — Monitoring & Observability | Future platform/data/model operational monitoring. |
| Phase 10 — CI/CD & Infrastructure Hardening | Deployment, scheduler/automation and infrastructure controls as explicitly scoped. |

Existing provider/domain/platform placeholders do not imply implementation.
No Kafka, Kubernetes, streaming or additional infrastructure was introduced.

## N. Phase 1 closure decision

**PHASE 1 CLOSED — PASS**

Every one of the 22 original criteria is satisfied: 19 PASS and three PASS
with documented accepted external limitations, all within the original scope.
There is no unresolved engineering blocker. The full offline 968-test suite
and quality gates pass, retained Stage 6 live/replay evidence is valid, current
documentation matches actual behavior, and every changed path is accounted for.
Phase 0 remains CLOSED/PASS; Phase 2 is not started.

## O. Push readiness

The accumulated eight local Phase 1 commits through `f15c9a2` are technically
ready to push based on current local verification. Stage 7's five documentation
paths remain unstaged/uncommitted for user review and the user's Stage 7 commit;
they are not yet part of that commit series. Remote freshness was not checked.
The user owns the commit/push decision. No branch was created, nothing was
staged or committed, and nothing was pushed.
