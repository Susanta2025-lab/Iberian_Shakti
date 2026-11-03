# Phase 2 Stage 7 — Final pre-live engineering audit

Date: **2026-11-03**, Europe/Lisbon. Strictly offline engineering audit.
Phase 2 remains in progress. Stage 8 has neither started nor been authorized.

## 1. Executive verdict

**Phase 2 Stage 7 — PASS.** All required offline gates in §21 passed.
Two concrete production defects were
reproduced and fixed: reversible encoded active-credential echoes could reach
the archive, and direct OMIE parsing/replay lacked an independent body-size cap.
There is no change to accepted provider selections, business semantics, query
serialization/hashes, archive layout or provenance wire versions.

This report assesses local engineering, not real-provider compatibility or
Phase 2 final acceptance. Live-dependent requirements are explicitly pending.

## 2. Baseline and scope

The first commands were `git status --short` and
`git log --oneline --decorate -12`. Status was empty; existing branch **main**,
HEAD **c3476f1** (`test: complete Phase 2 cross-source integration hardening`).
The committed tree contains the accepted Stage 6 report and all four files in
`tests/integration/stage6/`; the report concludes **Phase 2 Stage 6 — PASS.**
Stage 5 checkpoint is **77ff8e2**. Local main is intentionally nine commits ahead
of locally recorded `origin/main`; no remote freshness claim or synchronization.

The original 59-section operator prompt was saved before audit changes at
[phase_2_stage_7_pre_live_engineering_audit.md](../prompts/phase_2/phase_2_stage_7_pre_live_engineering_audit.md).
The continuation authorizes work from c3476f1 while forbidding provider I/O,
credential probes and Git mutation. Earlier prompts/reports are untouched.

Scope: OMIE marginalpdbc; REN production breakdown 0.2.0; ESIOS 544;
ENTSO-E ES A65/A16 and PT/ES A69/A01; Open-Meteo ERA5 and explicit
**DWD ICON-EU / models=icon_eu**, including all six configured weather sites.
No source/model ranking, Stage 8 execution, Stage 9 closure or later platform work.

## 3. Audit methodology

Read AGENTS.md, README, architecture/ADR/runbook indexes, the sole
[readiness assessment](phase_2_readiness_assessment.md), Stage 1–6 reports,
the Stage 5 model-selection report, and ADRs 0001–0007. Historical blocked
REN/weather report sections were distinguished from their accepted completion
sections. ADR 0006 and the explicit ICON-EU decision remain binding.

Inspected actual contracts, identities/adapters, HTTP/private request/deadline/
retry code, JSON/XML/text boundaries, provider parsers, configuration, managed
logging, archive/replay/runner, fixtures, tests and CI. Targeted risk searches
are interpreted in §18. No external documentation was fetched: all provider
facts in this report refer to retained repository evidence, not new observations.

Existing regressions were reused. The additional permanent audit suite is
[`test_phase2_stage7_audit.py`](../../../tests/integration/test_phase2_stage7_audit.py).
It imports the existing synthetic Stage 6 case builder, injects transports and
clocks, and uses temporary local archives. It introduces no networking guard,
provider framework, dependency or fixture copies.

### Reproduced defects and minimal corrections

| Defect | Reproduction before correction | Correction / permanent regression |
| --- | --- | --- |
| S7-01: encoded credential echo publication | Eight cases showed that all/mixed percent escapes and JSON Unicode escapes of the active ESIOS/ENTSO-E synthetic token passed the original literal/default-quoting guard and were archived. A subsequent parser failure did not remove the credential-bearing raw evidence. | `ingestion/auth.py` recognizes single-pass percent escapes (including lowercase hex and escaped unreserved characters), JSON printable-ASCII Unicode/simple string escapes and mixed literal/escaped forms. The same guard protects response observations. Eight body and eight header cases verify no sensitive publication/metadata. Existing literal/quoted/JSON/XML cases remain green. |
| S7-02: OMIE direct-parser/replay size boundary | A hash-valid 4 MiB + 1 byte payload reached text parsing when acquired outside the default HTTP cap. Other provider parsers already enforced their own byte limits. | `ingestion/omie/parser.py` checks the existing 4 MiB constant before text decoding/row parsing; oversized input produces `content_failure/content_invalid`, zero records. The regression forbids entering `_records`. |

Initial focused reproduction: **9 failed**, exactly these eight echo cases and
the OMIE cap case. After correction, the affected Stage 7/private-request/OMIE
selection passed **311** cases. Later tests extend coverage beyond those nine.
Invalid XML surrogate/out-of-range references are kept inert during echo
inspection; three tests prevent Unicode encoding exceptions in the hardened guard.

The new retry test initially delivered 429 headers exactly at the deadline,
which correctly triggered deadline failure before status classification. Its
clock now delivers those headers one second before expiry; production retry
policy was not changed to accommodate a test.

## 4. Network and origin controls

The existing `tests/conftest.py` guard is installed in `pytest_configure`, before
collection/session fixtures. It blocks DNS helpers, socket connect/connect_ex,
send/sendall/sendto/sendmsg and real synchronous/asynchronous HTTPX transports.
It deliberately permits MockTransport, fake httpcore backends and local files.
No live-enabling marker, option or environment variable exists.

New tests exercise **all eight representative provider/product/domain default
transport paths**, including the custom DeadlineTransport, without an injected
HTTP transport. Each raises the guard before DNS/connect. Additional tests
exercise urllib, http.client and HTTPX convenience construction with loopback
literals, also denied before connection. Existing `test_offline_guard.py`
proves collection-time denial, direct socket methods, async transport denial and
fake-backend usability. `requests` is not installed or used; provider SDKs are
not dependencies. Ordinary requests/SDK Python socket networking would meet the
same guard. Native code, subprocess networking and malicious code that removes
the guard are outside its documented scope; no selected provider uses them.

| Provider | Fixed origin and path | Request controls |
| --- | --- | --- |
| OMIE | `https://www.omie.es/en/file-download`; discovery `/en/file-access-list` | Validated marginalpdbc date/revision filename and fixed parents; one listing, safe reconstructed download URL, never execute a discovered href. |
| REN | `https://servicebus.ren.pt/datahubapi/electricity/ElectricityProductionBreakdownDaily` | Fixed en-US culture, physical source-day identity, exactly selected series/profile. |
| ESIOS | `https://api.esios.ree.es/indicators/544` | Fixed indicator/peninsular query, bounded explicit UTC endpoints, private x-api-key. |
| ENTSO-E | `https://web-api.tp.entsoe.eu/api` | Exactly three product/domain selections, fixed document/process/domain selector, whole UTC minutes, private securityToken. |
| ERA5 | `https://archive-api.open-meteo.com/v1/archive` | Fixed era5, single configured site/UTC day, exact variables/output. |
| ICON-EU | `https://api.open-meteo.com/v1/forecast` | Fixed icon_eu, independent report/parser/output profile, single configured site/next UTC day. |

Provider validators reconstruct and compare complete accepted requests. Caller
changes to series, geography, site coordinates/version, model or profile cannot
silently select another product. Private policies compare scheme/host/port,
reject userinfo/fragments/preinjected credential parameters and insert secrets
only after validation. Twelve new provider-specific injection cases exercise
host/port/scheme/userinfo/fragment/query rejection. Ten redirect cases cover
301/302/303/307/308 for both authenticated providers: one request to the fixed
origin, no redirect-body read, no forwarding to the attacker, no URL in output.
Existing OMIE discovery tests reject arbitrary origins, traversal-like/ambiguous
filenames, script links and extra query fields. TLS verification and
`trust_env=False` are retained; no proxy/environment credentials are inherited.

## 5. Authentication and secret handling

`load_provider_auth` reads only the selected provider's existing named setting
when explicitly constructing its retriever. Tests use injected synthetic maps;
tests of default environment loading first replace the selected value with a
synthetic token. No actual ESIOS_API_TOKEN or ENTSOE_API_TOKEN was inspected.
Missing/invalid selected credentials raise static ConfigurationError before
client construction. Anonymous factories and replay do not load credentials.
There is no dotenv read, refresh, account registration, probe or fallback auth.

Public queries, opaque locators, filenames, raw paths, acquisition/parse events
and normalized identities exclude private request values. SecretStr is omitted
from settings dumps/repr, and PrivateRequest omits URL/headers from repr.

| Echo/serialization case | Evidence / exact supported protection |
| --- | --- |
| Literal and quoted token | Existing private-request and provider-flow cases; active token substring is rejected before raw construction. |
| URL/query encoding | Existing standard quote/quote_plus cases plus new all/mixed percent escapes, uppercase/lowercase hex. One percent-decoding pass, no recursive encoding search. |
| JSON escapes | Existing standard quote/backslash cases plus new full/mixed `\uXXXX` printable-ASCII forms. One string-escape pass; no general Unicode normalization. |
| XML references | Existing ENTSO-E predefined/decimal/hex/zero-padded-reference tests; only its policy enables XML reference interpretation. No DTD/entity execution. Invalid references remain inert. |
| Header serialization / observations | Existing private header/query injection and literal ETag-echo checks plus eight new encoded ETag cases. All observations are omitted when an active echo is detected; safe body bytes remain unchanged. |
| Transport debug/error text | Managed DEBUG failure tests and existing execution/redaction/provider suites; controlled categories, no unchecked exception text/URL/header output. |
| Provider response echo | Terminal `sensitive_response`, no raw identity/payload/archive/parse and no retry. Bodies are never redacted and described as original bytes. |

This is a narrow active-credential guard. It does **not** detect arbitrary secrets,
base64, encryption, arbitrary multilayer transformations or credentials unknown
to that request. Anonymous content has no active credential to inspect.
Authenticated nonidentity Content-Encoding fails before publication rather than
attempting to inspect an ambiguous decoded representation.

## 6. Retry/time-budget audit

One retry engine: HttpRetriever. The httpcore pool has `retries=0` and no hidden
HTTPX retries. Default **3 total attempts**, phase timeout **10 s**, attempt
deadline **30 s**, operation deadline **93 s**; exponential waits **1 s, 2 s**,
cap **4 s**. Finite numeric settings and positive attempt counts are validated.

Arithmetic: `3 × 30 + 1 + 2 = 93 seconds`. More generally every attempt deadline
is `min(operation_deadline, now + attempt_timeout)`, and every underlying
connect/read/write/TLS timeout shrinks to remaining time. Responses/chunks and
body completion are checked against that deadline. A wait must be strictly less
than remaining operation time; equality/oversleep prevents another request.
Increasing configured attempts or phase timeout cannot remove the fixed operation
deadline. No new settings or timeout extension was added.

Forty new fake-clock cases exercise every representative provider selection:

| Scenario | Composed observed schedule |
| --- | --- |
| Every attempt times out | Starts at 0/31/63, waits 1/2, ends at 93; three failures and no payload. |
| Every body read times out after partial bytes | Same 0/31/63 and 93 bound; all streams closed and partial bytes discarded. |
| Final transport failure | Two 503 responses then a final connection failure; exactly three calls, 1/2 waits, end 93. |
| Near-limit Retry-After | First 429 at 29; minimum wait 63 ends at 92; next attempt gets only 1 s, ends at 93. ENTSO-E instead stops at 29 with one call/no sleep. |
| Operation shorter than attempts | 35 s operation: first attempt 30, wait 1, second gets 4, end 35; no third call. |

Existing tests cover equal/too-large Retry-After, enormous delta-seconds,
oversleep, slow headers, repeated small reads, timeout type translation, final
attempt exhaustion and phase clamping using the actual DeadlineStream/backend.

| Provider policy | Retryable / terminal |
| --- | --- |
| OMIE, REN, ESIOS, ERA5, ICON-EU | Selected connection/timeouts/incomplete transport and 500/502/503/504 retry within budgets. 429 uses supported delta-seconds Retry-After without shortening it. Unsupported/date Retry-After uses bounded fallback policy, not a claimed HTTP-date implementation. |
| ENTSO-E | Same transient policy, but **429 terminal**, reflecting the retained token-ban guidance. No global normalization of provider quota policy. |
| All | TLS verification, ordinary unclassified 4xx, private 401/403, unsupported encoding, size and sensitive-response failures terminal. Semantic no-data, provider rejection, schema/content failure and persistence failure occur outside retrieval retry loops. |

Budget scope is acquisition transport, not a claim that parsing/fsync or an
arbitrary injected backend can be preempted. Accepted host assumptions remain:
OS DNS/backend timeout compliance and cooperative scheduling/sleep. The suite
proves composed policy arithmetic and shrinking real transport calls, not an OS
hard real-time guarantee. No asynchronous cancellation framework is introduced.

There is no production multi-provider invocation planner. Stage 6's 18-case
plan is test-only. Stage 8 must separately define/enforce its authorized whole-run
query/attempt/byte/time caps (§20); no test plan is misrepresented as a live runner.

## 7. Transport/body/compression audit

HttpRetriever uses `client.stream` and `iter_raw`, not decoded `.read`, `.text`
or `iter_bytes`. Each incoming chunk is checked against the remaining byte cap
**before extending the accumulator**. Framing is handled by httpcore/h11; any
observable Content-Length mismatch fails. A preconsumed injected response is
rejected because original representation bytes can no longer be established.

| Boundary | Transport cap | Parser byte cap |
| --- | ---: | ---: |
| OMIE data | 4 MiB | 4 MiB, now independently enforced |
| OMIE discovery | 1 MiB | 1 MiB |
| REN | 1 MiB | 1 MiB |
| ESIOS | 2 MiB | 2 MiB |
| ENTSO-E | 4 MiB | 4 MiB |
| ERA5 / ICON-EU | 1 MiB each | 1 MiB each |

Interrupted streams, body timeouts, short Content-Length, malformed/truncated
chunk framing and read/protocol exceptions cannot publish a complete acquisition.
Each failed attempt discards its accumulated bytes. No application can detect
truncation of an otherwise valid close-delimited body beyond observable framing;
the strict complete-report/calendar/array grammar remains the semantic defense.

Complete safe malformed/empty/HTML 200 bodies remain archived before parsing and
receive failed parse events with zero records. Non-200 diagnostic bodies are not
read into successful raw history. Tests distinguish this from incomplete transport.

No provider parser supports compression. Anonymous complete nonidentity bodies
are bounded and archived **in original encoded form**, with Content-Encoding
observed, then fail `unsupported_encoding` at parsing/discovery. Authenticated
nonidentity bodies fail before publication because echo inspection is unsafe.
Unrepresentable encoding headers fail visibly. Gzip/deflate/br/unknown/list
regressions exercise raw preservation; no decoder or ZIP fallback exists.
The SHA-256 and payload.bin cover HTTP entity representation bytes after framing,
before content decoding; framing bytes themselves are not the payload.
Actual provider identity/compression negotiation remains a Stage 8 observation.

## 8. Parser-security audit

### JSON

Strict UTF-8 decoding and provider byte limits bound allocation before parsing.
Duplicate keys, invalid constants/NaN/Infinity, excessive numeric tokens,
nonfinite weather floats, malformed JSON/UTF-8, lone Unicode surrogates and
wrong shapes are rejected. Quantity validators reject bool/null/string coercion.
System JSON quantities become Decimal directly; no float intermediate. Weather
numbers become finite scientific floats and must pass their physical bounds.

| Parser | Structural work limits and handling |
| --- | --- |
| REN | Pre-decode-tree nesting scan depth 12; 30,000 visited nodes; 64 keys/object; strings 4,096; numeric tokens 128; at most 32 series/10,000 total values; all unselected arrays also validated. |
| ESIOS | Depth 16/50,000 visited nodes; strings 4,096; numeric tokens 128; arrays/selected values 2,000; geos 32. Object/key work is bounded by the node and 2 MiB byte limits, not an invented separate 64-key limit. |
| ERA5 / ICON-EU | Depth 16/4,096 nodes; 64 keys/object; strings/keys 4,096; numeric tokens 128; 48 items/array; exact success requires 24 hours/72 measurements. |

ESIOS/weather perform structural traversal after stdlib JSON allocation; the
raw byte limit bounds that allocation and RecursionError is caught. REN checks
depth first as well. No parser claims an unbounded streaming JSON capability.
Decimal exponents outside implementation range fail safely; finite large
system Decimals preserve accepted semantics rather than arbitrary clipping.

Existing provider parser suites cover the hostile matrix; additional Stage 7
late failures prove zero output after final invalid values for all products.
Pydantic constructs the tuple only after successful completion; a failed tuple
comprehension does not assign partial records. Parsing does not acquire data.

### XML

ENTSO-E uses only the bounded namespace-aware Expat callback boundary, with
Expat >=2.6.0 checked at runtime. XML 1.0 and UTF-8 are the supported profile;
UTF-8 BOM/absent declaration are accepted. Other declarations/versions,
invalid UTF-8, UTF-16/32 confusion and NUL fail. Full expanded namespaces are
checked, never stripped: Generation/Load v3 and acknowledgement v7 only.

DOCTYPE is refused before DTD processing. Entity declarations, external and
parameter entities, skipped/unparsed entities, notations and processing
instructions are refused; parameter parsing is disabled. No resolver, remote
schema, XInclude, stylesheet or weaker parser fallback exists. Predefined/XML
character references remain ordinary bounded text.

Limits during tree construction: depth 32, 100,000 elements, 2 MiB cumulative
text, 4,096 characters/node across fragmented callbacks, 16 attributes/element,
256 characters per expanded name/attribute name/value and 4 MiB input. Semantic
limits: 100 series, 64 Periods/series, 20,000 records, 25-hour document/Period,
128-character decimal tokens. Existing real-boundary tests exercise all these,
file/network entity attempts, old Expat refusal and A01/A03 expansion. No upgrade.

### OMIE text/discovery

One listing page, 1 MiB, 10,000 anchor candidates. HTMLParser treats scripts and
presentation text as inert; only supported fixed-origin download grammar inside
complete tables supplies date/revision observations. Pagination is detected but
never followed; unknown coverage cannot assert absence. Revisions are positive
numeric values under the 128-character filename bound, selected numerically.

Data now has a parser-level 4 MiB bound as well as transport protection. Rows
and line lengths are consequently finite; the exact day requires calendar rows
plus header/terminator, at most 100 rows/200 prices under contemporary profiles.
ASCII grammar accepts only the established date/period and signed integer or
one/two-decimal prices. No HTML execution, CSV guessing or hourly fallback.
Existing grammar/calendar/discovery boundary cases remain unchanged.

## 9. Time, DST and temporal support

Shared QueryWindow is positive UTC and at most 25 elapsed hours. REN matches its
physical Lisbon day, OMIE its Madrid day, ENTSO-E whole UTC minutes, weather
exactly midnight-to-midnight UTC. ESIOS preserves explicit requested UTC bounds
and five-minute response samples, with a possible inclusive endpoint retained
under its accepted profile; no complete-day coverage claim is fabricated.
Partition-date consistency is checked by each reconstructed provider identity.

Independently specified ordinary/spring/autumn Stage 6 cases coexist. OMIE uses
Madrid for **both** price areas: legacy 24/23/25 hourly periods and modern
96/92/100 quarters. REN uses Lisbon 96/92/100 quarters. Midnights are converted
independently then stepped in UTC; autumn fold 0 and fold 1 survive without
deduplication, spring missing local hours are not filled. Leap/year boundaries,
UTC/local midnight crossings and host timezone independence are covered by the
existing period/calendar/provider tests. ESIOS cross-checks supplied local Madrid
offset timestamps against provider UTC. ENTSO-E stays on explicit UTC Periods;
weather always has 24 UTC hours even on local 23/25-hour days.

`instant` requires ValidInstant; mean/sum/provider-period statistics require a
positive SupportInterval. Temperature/wind remain instantaneous at 2/10 m;
shortwave is mean `[t−1h,t)`, including midnight support in the previous day.
REN/ENTSO-E use interval-supported `provider_period_value`, not asserted mean
or energy. ESIOS uses forecast ValidInstant. Invalid combinations fail contracts.

## 10. Units, statistics, decimals and geography

Five distinct unit families remain: Decimal EUR/MWh prices, Decimal MW power,
finite float °C, m/s and W/m² weather. MWh requires interval sum and cannot
relabel provider-period power; no conversion service or implicit scaling exists.
OMIE lexical decimals, REN/ESIOS direct Decimal JSON parsing and ENTSO-E decimal
text retain sign/scale/precision without binary intermediates, rounding or clipping.
The explicit ENTSO-E MAW-to-MW code mapping changes the unit code, not the value.

OMIE market areas, REN provider-defined Portuguese system/aggregate boundary,
ESIOS ES.peninsular mainland system, ENTSO-E role-qualified EIC bidding zones,
logical weather sites and independently returned cells remain separate types
and business dimensions. Coincident country, coordinate, time, value or concept
cannot establish equality/deduplication. Stage 6's six-site serialization and
2,190-record autumn matrix prove coexistence without aligning source counts.

## 11. Query and raw identity

Canonical API SHA-256 covers the complete nonsecret request JSON, sorted keys
and unique sorted series/variables: source, report/profile, partition/window,
area/role/native ID or model/site/coordinates/selection version/output selection.
Existing tests distinguish material changes and normalize key order. Provider
validators also reject unsupported alternatives before transport. ICON-EU's
typed output selection is explicit; the omitted historical output field preserves
the accepted ERA5 canonical bytes/hash. No wire/hash migration is introduced.

Raw identity is `(source_id, report_id, partition_date, sha256)`, **not SHA-256
alone**. Different providers/reports never overwrite one another. Identical bytes
for distinct site queries within one source/report/day may share one raw object;
their independent query/acquisition events preserve the site selections. The
combined Stage 6 replay has 18 distinct acquisitions backed by eight composite
raw identities, with all business/query identities preserved.

## 12. Archive and persistence

Paths derive only from validated identifiers/date/hash and UUID event filenames.
ArchiveReference checks the exact content-addressed path. contained_path rejects
absolute/traversing/empty/backslash/colon/NUL components and symlinks beneath the
configured root. The root is trusted operator configuration; protection against
a hostile process swapping writable parent directories is not claimed.

Private same-directory mkstemp staging writes/flushed/fsyncs complete bytes,
sets 0444 and publishes via atomic hard link with no replacement. Existing files
are verified, never opened for replacement. Parent-directory fsync completes
publication durability; finally cleanup removes staged files. Hard-link/fsync
support is an explicit local filesystem prerequisite, not WORM protection.

Existing tests exercise same/changed content, duplicate/independent/conflicting
events, concurrent identical/conflicting writers, interruption, permission/write/
flush/fsync/link failure, abandoned staging, corrupt history and symlinks. No new
concurrency mechanism was added. Previously persisted evidence remains intact.

Stage 6 separately injects raw/retrieval/parse publication failures for all eight
selections (24 cases). Raw/retrieval failure prevents parsing; parse publication
failure prevents returning successful records. An orphan payload or acquisition
can remain recoverable but is not successful ingestion; explicit retry verifies
and reuses complete history rather than silently repairing corrupt objects.

## 13. Replay integrity and determinism

Replay depends only on RawArchive, a raw reference and original retrieval UUID.
It verifies bytes/length/hash, bounded metadata and raw/archive/event/query linkage.
Missing/changed raw data, missing/corrupt/wrong events and inconsistent linkage
fail with ReplayError; there is no client, credential loader, retriever or refetch.
Fourteen new API-query/profile tampering cases prove that changing embedded
selection/report while retaining its original locator/hash cannot replay.

Stage 6 replays every product/domain and both weather models at all six sites,
with credential loading and HTTP/retriever construction explicitly forbidden.
Business values/identities, native semantics, original query/retrieval and raw
identity reproduce; only new parse-event UUID/time changes. All prior files are
byte-identical. Existing raw-missing/hash/length/event-corruption tests are reused.

Provider parsers validate supported query/profile identity; a weather model or
another product cannot be reinterpreted as the selected product by a fallback.
Replay intentionally does not require a prior successful parse or lock to an old
parser version: explicit new parser versions may add new interpretations, as
accepted REN 0.1.0-to-0.2.0 replay demonstrates. Old parse history is never edited.
Retrieval sidecars are schema/linkage-checked, not cryptographically signed;
the trusted local archive is not an adversarial metadata-authentication system.

## 14. Error taxonomy and diagnostics

ConfigurationError is separate and precedes I/O. Controlled acquisition
transport/timeout/TLS/HTTP/rate/auth/authorization outcomes remain distinct from
semantic no-data/rejection/schema/content, archive I/O/integrity and replay failure.
Only complete safe 200 bodies become parse candidates. Unknown provider errors
never become zero-record success. ENTSO-E acknowledgement classification uses
exact code/context mappings, not keyword matching; other providers retain their
accepted, deliberately narrower error grammars.

Managed DEBUG tests cover success and failure, private headers/queries, encoded
echoes, unchecked provider prose, invalid configuration, transport debug and
nested exceptions. SafeJsonFormatter emits fixed events and allowlisted scalar
context, omitting arbitrary messages, headers, URLs, bodies and traceback/cause
formatting. HTTPX/httpcore handlers/verbosity cannot bypass this managed setup.
ExecutionError str/repr exposes controlled code/reason only; transport exceptions
with attached private requests are consumed into safe outcomes, not returned.
Local OS/locator causes may remain diagnostic objects internally; callers must
use the documented managed boundary, which never renders those causes. This
does not promise safety for arbitrary unmanaged third-party logging handlers.

## 15. Provider-specific findings

| Provider | Preserved semantics / remaining observational boundary |
| --- | --- |
| OMIE | Exact/latest-observed marginalpdbc, numeric revisions, both price areas and resolution transition retained. Discovery coverage is bounded, not a global latest/history guarantee. New parser cap closes direct/replay overrun path. |
| REN | Profile/parser 0.2.0 remains **provisional_empirical**, Europe/Lisbon, interval_start, ordered 92/96/100 sequence and Decimal MW provider_period_value. All eleven selected concepts from one chart; four ancillary concepts validated but unselected. No authoritative mean/instant/fold claim or MW-to-MWh conversion. Provider-authoritative refinements remain Stage 8/future clarification. |
| ESIOS | Indicator 544, ES.peninsular, five-minute forecast instant samples. values_updated_at stays indicator update context, never per-value issuance. No invented numeric geography catalogue ID. Actual authentication/catalogue/end-boundary/coverage remains unobserved. |
| ENTSO-E | ES actual load and PT/ES renewable forecasts preserve process/domain/PSR/native IDs, explicit UTC resolutions, A01 exact cells and A03 constant blocks; gaps stay gaps and absent technologies stay absent. Known 999+exact-context no-data/auth/rejection and A05/A23/etc. codes remain distinct; unknown/mixed reasons are unsupported provider rejection even if prose contains auth/domain/no-data words. 429 terminal. |
| ERA5 | Explicit era5, reanalysis, six fixed versioned sites, complete UTC weather day, independent returned grid/elevation, no historical forecast substitution. |
| ICON-EU | Explicit icon_eu only. Target is next UTC day at preflight, rechecked against original acquisition completion; midnight-crossing acquisitions may fail closed. Replay uses original completion, never current parse time. Issue/run time remains null. Grid changes are retained; actual cycle/coverage/transition behavior remains live-only. **IFS HRES is documentation-only; no automatic fallback, best_match, seamless model, repair or mixing path exists.** |

## 16. Stage 6 integration regression

Fresh dedicated run: **119 passed in 35.83 s**. No Stage 6 files changed.
Identity/geography isolation, temporal support coexistence, unit/statistic/kind
safety, complete combined replay, failures/revisions/persistence isolation,
per-source bounds, ordinary/DST calendars and managed diagnostics remain green.
Provider-focused regression: **1,164 passed in 13.11 s**. These are fresh runs,
not counts copied from the Stage 6 report.

## 17. Dependency/runtime findings

Locally executed in the existing named `iberian_shakti` environment:

| Runtime/dependency | Exact used version |
| --- | --- |
| Python | 3.12.9, GCC 13.3.0 build |
| Expat | expat_2.6.4 |
| HTTPX | 0.28.1 |
| httpcore | 1.0.9 |
| Pydantic | 2.14.1 |
| pytest | 9.1.1 |
| Ruff command | 0.16.9 |
| mypy | 2.3.1 |
| pre-commit | 4.6.2 |

The pinned pre-commit Ruff revision is v0.13.2, distinct from the CLI version;
both must pass. Expat exceeds the parser's >=2.6.0 safety prerequisite. HTTPX's
installed httpcore 1.x public pool/backend interfaces match DeadlineTransport;
the actual backend/framing regression exercises that assumption. Required Madrid
and Lisbon IANA zones work in this environment. No compatibility defect justifies
a dependency upgrade. No dependency/install/network action was performed.

## 18. Risk-pattern, TODO and dead-path audit

Targeted `rg` searches covered ingestion/contracts/common and relevant tests/CI
for TODO/FIXME/HACK/XXX/pass/NotImplemented/temporary and verify=False,
timeout=None, requests.get/httpx.get, eval/exec, pickle.load, yaml.load,
shell=True, subprocess, os.system, open and except Exception. Contextual findings:

| Occurrence | Classification and result |
| --- | --- |
| `http.py` optional Last-Modified parsing `pass` | Safe intentional: invalid optional metadata is omitted; raw body/required encoding validation is not skipped. |
| `omie/live_smoke.py` temporary archive help and verdict `pass` | Safe intentional operator-controlled local archive/success label; no temporary production implementation. |
| `contracts/periods.py` future configuration-layer note | Future-phase host-startup concern; concrete source/calendar calls require installed zones and fail rather than guess. Current zone/DST tests pass. |
| `_http_transport.translate_errors` broad except | Safe intentional closed httpcore-to-HTTPX mapping, static message, unknown exceptions re-raised. No blanket success/retry or raw managed logging. |
| `omie/live_smoke.run` broad except | Safe intentional final CLI boundary returns static unexpected_internal_failure; opt-in gate precedes construction. |
| archive/local retriever `Path.open`, archive `os.open`/fdopen | Safe intentional bounded binary reads and same-filesystem atomic publication; containment/UUID/hash checks and failure regressions reviewed. |
| Fake socket `setsockopt` / fake stream close `pass` | Safe intentional test doubles; no production I/O implementation is missing. |
| Backend/stream optional-timeout interface defaults and test `timeout=None` signatures | Safe intentional httpcore-compatible interfaces; every actual operation is clamped by DeadlineStream/DeadlineBackend, with finite HTTPX phase timeouts. |
| New HTTPX convenience call | Safe intentional network-denial regression under the existing guard; loopback literal, finite timeout, trust_env=False. |
| Docstring/comment matches for pass | Ordinary English, no executable placeholder. |

No TODO/FIXME/HACK/XXX/NotImplemented placeholder in the accepted ingestion path;
no production verify=False, unlimited explicit timeout, eval/exec, pickle/yaml
deserialization, shell/subprocess/os.system networking. No production requests
client or SDK. Existing transport interface methods that forbid Unix sockets or
backend retry sleeps intentionally fail closed. No unreachable retry/fallback
branch creates another provider/model path. No broad cleanup/refactoring was done.

## 19. Authoritative 44-criterion reconciliation

Original wording and numbering below come from readiness §V, unchanged. A row
classified OFFLINE SATISFIED is local implementation evidence only, not proof
of live compatibility or full Phase 2 closure. Mixed requirements are conservatively
assigned to their remaining live/final stage. The stronger original REN criterion
4 is not silently marked provider-authoritative by the accepted empirical policy.

| Original criterion (unchanged) | Stage 7 classification | Evidence / reason deferred |
| --- | --- | --- |
| 1. Accepted Phase 2 query/measurement/auth/semantic-outcome decisions are recorded in focused ADR(s) before corresponding implementation; Phase 1 ADR history is retained and this report remains the sole readiness assessment. | OFFLINE SATISFIED | ADRs 0003/0004/0006/0007, Stage 1 report and later completion records; historical ADRs/readiness retained. |
| 2. All four mandatory providers and exactly the minimum products in §C are implemented; any scope change is explicitly approved and traced, never silently removed to obtain acceptance. | OFFLINE SATISFIED | All provider adapters/profiles and Stage 5 completion; Stage 6 source matrix. Explicit REN/ICON-EU operator decisions retained; no minimum product removed. |
| 3. REN's documented daily production endpoint supplies all selected load/generation/import/export series from one acquisition; ancillary series/presentation fields have explicit selection policy, with no double-counted totals. | OFFLINE SATISFIED | ren/profile.py, schema.py, parser.py; REN unit/integration and Stage 6 matrix. Eleven selected/four ancillary concepts, one chart, no totals. |
| 4. REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly. | LIVE VALIDATION REQUIRED | ADR 0006 and revised Stage 2 report accept provisional empirical 0.2.0; REN/Stage 6 DST tests pass. Stronger original provider-authoritative evidence is not established; reserve refinements for provider clarification and final policy reconciliation. |
| 5. ESIOS 544 is verified against official authenticated name/unit/geography/sampling metadata, retained in a versioned catalogue; the peninsular forecast curve is not mislabelled as a complete D-1 forecast or actual load. | LIVE VALIDATION REQUIRED | ESIOS profile/schema/parser and Stage 3 report support the pinned offline contract. Actual authenticated catalogue/name/unit/geo/cadence evidence remains Stage 8; synthetic geo IDs are not authority. |
| 6. ENTSO-E implements ES A65/A16 actual total load and PT plus ES A69/A01 renewable forecasts, retaining document/series/process/domain/PSR identity and distinguishing absent technologies from zero output. | OFFLINE SATISFIED | entsoe/profile.py, identity.py, schema.py, parser.py; test_entsoe_parser.py and test_entsoe_flow.py exercise ES load and both renewable domains/absent PSRs. |
| 7. ENTSO-E namespace/version, Period resolution/position and A01/A03 curve handling are explicitly supported and tested, including multiple periods, constant blocks, missing sections and conflicting overlaps. | OFFLINE SATISFIED | ENTSO-E schema.py and test_entsoe_parser.py: A01/A03, multiple Periods, gaps, overlaps, variable resolutions and bounds. |
| 8. Open-Meteo archive ERA5 and selected-model forecast ingestion support exactly the three initial variables at six versioned sites, preserving requested/returned coordinates, grid/elevation and model identity. | OFFLINE SATISFIED | weather/profile.py, identity.py, adapter.py, parser.py; weather unit/integration suites and Stage 6 all-sites matrix, ERA5 and explicit icon_eu. |
| 9. Query contracts carry validated nonsecret product/window/domain/variables/location/model identity and explicit selection semantics; API snapshots do not fabricate numeric OMIE revisions or guaranteed latest versions. | OFFLINE SATISFIED | contracts/queries.py and all identity validators; test_multisource.py, Stage 6 test_semantics.py and ICON-EU output/legacy hash regressions. |
| 10. New system/weather record families and parse schema-family versions are strict, frozen and typed; MarketPrice and Phase 1 serialized archive/provenance remain readable and behaviorally compatible. | OFFLINE SATISFIED | FrozenContract/closed unions/versioned provenance; contract suites and test_multisource_foundation.py baseline Phase 1 wire/replay fixture. |
| 11. Geographic roles distinguish country, mainland/system perimeter, bidding zone, control area, EIC and coordinate; native IDs remain available and directed/aggregate interchange are not conflated. | OFFLINE SATISFIED | contracts/geography.py, provider profiles; Stage 6 geography/source matrix and six-site separation tests. |
| 12. MW, MWh and EUR/MWh remain distinct; system/market decimals have no binary-float intermediate and financial serialization preserves exact decimal values. | OFFLINE SATISFIED | contracts/market.py and measurements.py; direct lexical/JSON Decimal provider parsers, precision/unit contract and Stage 6 tests. |
| 13. Scientific weather values are finite floats with explicit verified units, height/statistic and versioned plausibility/missing policy; no clipping or implicit unit conversion occurs. | OFFLINE SATISFIED | Weather schema.py/parser.py plus WeatherMeasurement; retained Stage 5 unit/support evidence, finite/plausibility/boolean/null/unit/missing tests. No claim of new real response verification. |
| 14. Every normalized time is UTC-aware; instant samples, positive half-open intervals, source cadence and weather preceding-hour support remain distinct and query boundary handling is tested. | OFFLINE SATISFIED | Measurement timing contracts, provider identity/parser tests and Stage 6 support coexistence/midnight tests. |
| 15. Ordinary/leap/year boundaries, spring/autumn DST, duplicate local labels and UTC/local-day crossings are covered where applicable; GMT weather days are not forced to local 23/25-hour counts. | OFFLINE SATISFIED | test_market_periods.py, OMIE calendar/boundary tests, REN profile/parser tests, ESIOS timestamp tests, weather forecast/calendar and Stage 6 DST tests. |
| 16. Actual, forecast and reanalysis kind is explicit; issue/publication/update/acquisition times remain distinct and unknown source times/horizons stay null. | OFFLINE SATISFIED | ValueKind/SourceTimes and provider parsers; Stage 6 kind/source-time tests. No issuance from values_updated_at, createdDateTime or acquisition. |
| 17. Multiple known forecast editions and unknown-edition acquisition snapshots for the same target survive distinctly; historical refetches are never declared known at an earlier market cutoff without evidence. | OFFLINE SATISFIED | test_multisource.py forecast editions; provider correction/replay suites and Stage 6 repeated unknown-edition snapshots. |
| 18. Source-selected credentials use ESIOS_API_TOKEN and ENTSOE_API_TOKEN, validated before I/O and injected privately using the verified mechanism; anonymous providers and OMIE need neither credential. | LIVE VALIDATION REQUIRED | config.py/auth.py and private/provider tests prove selected loading, missing-before-I/O, private insertion and anonymous independence. Actual provider acceptance of credentials/mechanism remains live-only. |
| 19. Authentication/authorization failures are terminal, safely diagnosed and tested; there is no pasted-secret workflow, implicit dotenv load, auto-registration or token-refresh/probing loop. | OFFLINE SATISFIED | test_private_requests.py and provider flows: 401/403 terminal and safe; explicit injected settings, no dotenv/refresh/account workflow. |
| 20. Every external call uses finite phase/attempt/operation budgets, response caps, verified TLS, zero redirects and no hidden transport retries; whole-invocation query/attempt/byte/time caps are enforced. | LIVE VALIDATION REQUIRED | http.py, retry.py, _http_transport.py and 40 new composed-budget cases prove per-acquisition caps. No production multi-provider planner exists; the separately authorized Stage 8 execution mechanism must enforce its whole-invocation caps before I/O. |
| 21. Retry policy has at most three attempts by default with bounded backoff, permanent/content/no-data failures do not retry, Retry-After is never shortened and ENTSO-E token bans end the invocation. | OFFLINE SATISFIED | Shared HTTP/retry/transport suites plus new composed-budget tests; ENTSO-E retry_rate_limits=False, exact waits, no semantic retry. |
| 22. Selected query/record/JSON/XML bounds are implemented and documented; unexpected pagination/truncation/ZIP/content coding gives explicit coverage or unsupported failure rather than partial success. | OFFLINE SATISFIED | Provider byte/shape/collection limits and actual security/parser suites; new OMIE direct/replay cap. Unsupported compression/pagination/ZIP never produces partial success. |
| 23. XML cannot resolve external resources or expand DTD/entities; encoding-aware element/depth/text/work safeguards and hostile-payload tests exercise the actual parser boundary, with any added security dependency justified. | OFFLINE SATISFIED | entsoe/xml_boundary.py and test_entsoe_xml_security.py: actual callbacks refuse declarations/entities/resources and enforce runtime/complexity bounds. |
| 24. Original complete safe provider body bytes are archived unchanged before transformation/semantic parsing using reused SHA-256 content addressing and atomic no-replace publication. | OFFLINE SATISFIED | runner.py, archive.py, raw-stream tests and all provider flows; safe complete bodies persist before parsing. S7-01 blocks encoded secret bodies without rewriting originals. |
| 25. Independent identical acquisitions reuse content while retaining immutable events; changed bytes under unchanged provider/query/revision keys retain both versions and repeated event IDs remain idempotent. | OFFLINE SATISFIED | Archive/Stage 5 archive concurrency/idempotence tests, provider correction tests and Stage 6 revision/isolation cases. |
| 26. Retrieval provenance retains safe query/locator, acquisition UTC/status/attempts, native revision observations when known, byte/hash/archive linkage; no private request data is persisted. | OFFLINE SATISFIED | RetrievalProvenance, result_for, archive.py; private/provider/Stage 6 persisted-chain checks plus new encoded-header exclusion. |
| 27. Separate parse provenance records parser/schema/catalogue versions and original raw/retrieval linkage; every normalized record links back to that chain and persistence failure prevents success. | OFFLINE SATISFIED | MeasurementParseProvenance/ParseResult, archive.persist_parse and runner; Stage 6 24 persistence-fault cases and contract/schema/linkage tests. |
| 28. Complete malformed safe 200 responses and semantic no-data/error documents are preserved with explicit parse/semantic outcomes and zero normalized success; interrupted/oversized responses never masquerade as complete acquisitions. | OFFLINE SATISFIED | HTTP/framing/provider flows and Stage 6 failure cases; eight new late failures retain original safe raw bytes but zero records; body timeouts never publish. |
| 29. Empty/null/missing/unsupported/future/provider-error results are distinguished from successful selected coverage; no bad rows are silently dropped, absent data converted to zero or undeclared partial dataset emitted. | LIVE VALIDATION REQUIRED | All supported offline missing/error shapes fail or classify safely; no silent rows/zero filling. Actual future/no-data/provider error variants still require Stage 8 observation, without guessing new schemas. |
| 30. Provider-specific auth/quota/domain/semantic/schema errors map to controlled typed categories, including ENTSO-E acknowledgement context rather than reason 999 alone; raw error text is never logged. | OFFLINE SATISFIED | ErrorCode/outcomes, entsoe/acknowledgement.py exact mappings; provider parser/flow and Stage 6 error-taxonomy/unknown-prose tests. |
| 31. Safe logging/CLI/exception/config/metadata boundaries are tested with synthetic secret-bearing URLs, headers, rejected validation inputs and credential echoes; sensitive raw-body publication is rejected without pretending redaction preserves original bytes. | OFFLINE SATISFIED | Managed logging/config/private transport/redaction/provider/Stage 6 suites and new Stage 7 encoded body/header/origin/redirect DEBUG cases. S7-01 fixed. |
| 32. Each selected product replays entirely offline from archived bytes/history plus pinned catalogue metadata, with no name/geo/schema/weather/model network lookup and no fallback acquisition. | OFFLINE SATISFIED | replay.py has no acquisition dependency; all provider and combined Stage 6 replay tests prohibit HTTP/client/retriever/credential loading. |
| 33. Replay verifies hash/linkage and reproduces fixed-version normalized values and identities; only new parse event identity/time may differ and original retrieval history remains unchanged. | OFFLINE SATISFIED | Archive/replay corruption/linkage tests, provider deterministic replay and Stage 6 combined replay; fourteen new API query/profile tampering cases. |
| 34. Actual-component mocked integration covers each mandatory product's successful chain, failure chain, correction/duplicate handling and replay through the shared archive/runner. | OFFLINE SATISFIED | test_ren_flow.py, test_esios_flow.py, test_entsoe_flow.py, test_open_meteo_flow.py and Stage 6 actual-component success/failure/correction/replay. |
| 35. Small versioned fixtures cover §P's valid/missing/malformed/boundary/time/revision/provider-error cases; manifests protect hashes/inventory, label original/synthetic/mutated evidence and record rights/attribution. | OFFLINE SATISFIED | tests/data/{omie,ren,esios,entsoe,open_meteo,shared_contracts} manifests/READMEs, provider inventory/hash tests and in-memory hostile mutations. No real response fixture added. |
| 36. Existing OMIE fixtures and meaningful tests are preserved; shared changes pass Phase 1 regression and old-provenance/replay compatibility tests without weakening assertions. | OFFLINE SATISFIED | All original OMIE fixtures/tests untouched; full Phase 1/regression suite and baseline wire/replay compatibility tests pass. |
| 37. Repository-wide python -m pytest succeeds with the existing network-denied guard active from collection, without credentials, real providers, subprocess networking or a live-enabling test switch. | OFFLINE SATISFIED | tests/conftest.py, test_offline_guard.py and new every-provider/urllib/http.client/HTTPX construction denials; full pytest runs with no live switch or real credentials. |
| 38. Live commands are separate and explicit --live opt-in, refuse before network construction without it, reject fixture archive roots and are absent from pytest/pre-commit/automatic CI execution. | LIVE VALIDATION REQUIRED | Existing OMIE CLI opt-in/root/CI tests pass. No Phase 2 live command exists yet; Stage 8 must supply a separately reviewed bounded opt-in mechanism, not execute directly from ordinary pytest. |
| 39. Controlled live validation records successful data through implemented retrieval/archive/parser paths for REN, ESIOS 544, ENTSO-E ES actual plus PT/ES forecasts, and Open-Meteo archive plus forecast; unavailability/auth failure is never counted as success. | LIVE VALIDATION REQUIRED | No Stage 7 provider requests. Seven required successful real product/domain paths must be observed under separately authorized Stage 8; prior source studies/synthetic tests do not satisfy this. |
| 40. The actual live acquisitions in criterion 39 have retained safe checksums/query/provenance/outcomes and successful subsequent network-denied replay; request/attempt totals and deviations from §Q are explained. | LIVE VALIDATION REQUIRED | No criterion-39 real acquisitions exist from Stage 7. Stage 8 must retain their safe provenance and demonstrate subsequent network-denied replay and run totals. |
| 41. Source catalogues/runbooks/README/architecture status describe implemented scope, limits, units/time/forecast semantics, credentials, errors, revisions, replay, live opt-in and attribution/licensing boundaries without claiming production clearance or complete history. | FINAL ACCEPTANCE / STAGE 9 | Current source profiles/runbook/README/architecture and this report describe engineering limits. Final operational/live outcome documentation and licensing/access boundaries belong to Stage 9 after Stage 8. |
| 42. Final Python 3.12 ruff check ., ruff format --check ., mypy src, python -m pytest, git diff --check and applicable pre-commit checks pass; full new/staged/unstaged diff and Git status are reviewed. | FINAL ACCEPTANCE / STAGE 9 | Fresh Stage 7 gates in section 21 and diff/status review provide present evidence. Final Phase 2 gates must be rerun against its actual final accepted tree in Stage 9. |
| 43. No Snowflake/dbt/features/ML/registry/inference/API/dashboard/deployment/Kafka/Kubernetes implementation, paid-resource change, bulk download or unnecessary runtime dependency enters Phase 2. | OFFLINE SATISFIED | Five-path Stage 7 scope; unchanged dependencies/architecture and no external action. No Snowflake/dbt/features/ML/serving/deployment/infrastructure work. |
| 44. Final acceptance traces every numbered criterion to concrete code/test/document/live evidence, reports external limitations honestly and leaves commit/push decisions to explicit operator authorization. | FINAL ACCEPTANCE / STAGE 9 | This table traces all 44 without closing Phase 2; final live/final evidence reconciliation and acceptance remain Stage 9. All Git decisions stay with the operator. |

**Classification totals: 33 OFFLINE SATISFIED; 8 LIVE VALIDATION REQUIRED;
3 FINAL ACCEPTANCE / STAGE 9; 0 NOT APPLICABLE.** No mandatory criterion is
removed. Mixed live/final rows retain their existing offline evidence without
being declared fully complete.

## 20. Stage 8 entry gate

The engineering entry gate requires all of the following, with fresh results
recorded in §21:

- [x] All local provider, contract and cross-source regressions green.
- [x] JSON/XML/OMIE parser bounds and atomic failure regressions green.
- [x] Credential publication, private-origin and managed-diagnostic protections green.
- [x] Retry/timeout composition finite, including short-operation and near-limit waits.
- [x] Immutable archive, persistence failure and replay integrity/determinism green.
- [x] Default full-suite network denial effective for every provider transport.
- [x] No unresolved locally detectable correctness defect in the audited paths.
- [ ] Separate operator authorization for Stage 8; **not granted by this report**.

Before any Stage 8 execution, its concrete opt-in mechanism must refuse before
network construction without authorization, reject fixture archive roots and
enforce the authorized whole-run limits. There is no Phase 2 live CLI in this
Stage 7 patch. Preserve readiness §Q's minimal seven-data-request plan (REN 1,
ESIOS 1, ENTSO-E 3, ERA5 1, ICON-EU 1), at most one necessary ESIOS metadata
request, 15-minute/32-MiB run cap, finite per-request attempts and caller pacing.
Do not assume a raw per-request cap enforces a total run cap: attempted bytes
across retries must count too. No date searching/polling, invalid-key/quota probes,
unbounded retry, bulk history or all-site smoke is authorized here.

Engineering readiness permits consideration of a separately bounded live task;
it is not permission to execute it or a claim that all 44 final criteria close.

## 21. Validation results

All commands run with the repository's network-denied pytest configuration and
synthetic private credentials. Required commands are recorded only after actual
execution. Final counts/results:

| Executed gate | Result |
| --- | --- |
| Focused Stage 7 suite | **115 passed in 1.59 s**; all are newly added Stage 7 cases |
| Stage 7 plus existing guard/private HTTP/retry/transport/archive/XML security selection | **457 passed in 4.25 s** |
| Provider-focused unit/integration selection | **1,164 passed in 13.11 s** |
| `python -m pytest tests/integration/stage6 -q` | **119 passed in 35.83 s** |
| `python -m pytest` | **2,246 passed in 55.71 s**; zero failures/skips/warnings |
| `ruff check .` | **Passed**: All checks passed |
| `ruff format --check .` | **Passed**: 159 files already formatted |
| `mypy src` | **Passed**: no issues in 59 source files |
| `pre-commit run --all-files` | **Passed**: all eight hooks |
| Explicit pre-commit on all five new/changed paths without staging | **Passed**: all six applicable hooks; YAML/TOML inapplicable, no files changed |
| `git diff --check` plus explicit new-file whitespace review | **Passed**: no whitespace errors; full tracked/new contents reviewed |

Provider selection: `tests/unit/ingestion/{omie,ren,esios,entsoe,weather}` plus
`tests/integration/test_{stage3_flow,stage4_omie_flow,stage5_flow,ren_flow,esios_flow,entsoe_flow,open_meteo_flow}.py`.
The 457-case security selection includes the new Stage 7 module, offline guard,
private requests, HTTP, Stage 5 HTTP, transport, archive, Stage 5 archive and
ENTSO-E XML security modules. Full pytest includes all existing Phase 1 and
Stages 1–6 cases unchanged. No assertion/fixture was weakened or test skipped.

## 22. Files changed and Git review

Exactly five Stage 7 paths, all unstaged:

| Path | Purpose |
| --- | --- |
| `docs/codex/prompts/phase_2/phase_2_stage_7_pre_live_engineering_audit.md` | Exact original operator prompt. |
| `docs/codex/reports/phase_2_stage_7_pre_live_engineering_audit_report.md` | This engineering audit, reconciliation and live boundary. |
| `src/iberian_shakti/ingestion/auth.py` | Narrow encoded active-credential echo hardening. |
| `src/iberian_shakti/ingestion/omie/parser.py` | Independent existing 4 MiB parser/replay cap. |
| `tests/integration/test_phase2_stage7_audit.py` | Permanent reproductions and missing cross-provider audit cases. |

Tracked production diff and complete new prompt/report/test contents are reviewed
separately because ordinary git diff omits untracked files. The index remains
unchanged. No previous prompt/report, dependency, fixture, provider semantics,
CI/workflow or Stage 6 file changed. No branch, staging, commit, push, fetch,
pull, rebase, reset, restore or stash operation occurred.

Final exact status is recorded after validation:

```text
 M src/iberian_shakti/ingestion/auth.py
 M src/iberian_shakti/ingestion/omie/parser.py
?? docs/codex/prompts/phase_2/phase_2_stage_7_pre_live_engineering_audit.md
?? docs/codex/reports/phase_2_stage_7_pre_live_engineering_audit_report.md
?? tests/integration/test_phase2_stage7_audit.py
```

## 23. Remaining Stage 8 controlled-live validation items

No live result is simulated or inferred from a synthetic fixture. Questions:

1. Do the operator-provided ESIOS/ENTSO-E credentials actually authenticate and
   authorize the selected products? No credentials were probed here.
2. Do real REN payloads match all selected/ancillary arrays and accepted Lisbon
   source-period sequencing? Provider-authoritative statistic/label/fold refinements
   remain clarification items; empirical acceptance is not new official evidence.
3. Does ESIOS 544 return the accepted exact name/unit/geography/cadence metadata,
   UTC/local timestamps, update context and actual bounded coverage/end inclusivity?
   Which native IDs are authoritative? No offline-discovered ID is promoted.
4. Do all three independent ENTSO-E product/domain paths return the supported
   namespace/version, business/aggregation/domain/PSR identity, curve/resolution,
   Period spans and technology coverage? What are actual acknowledgements?
5. Do explicit ERA5 and icon_eu requests return all selected units/24 UTC hours,
   requested-versus-returned grid/elevation and required shortwave support?
6. What ICON-EU cycles compose the latest snapshot, when is complete next-day
   coverage available relative to a chosen market cutoff, and what changes at the
   announced grid transition? No issue/run availability is guessed.
7. What are real safe error/no-data responses, rate policy, availability timing,
   response sizes/Content-Encoding and identity-negotiation behavior? Observe
   encountered failures within the authorized plan; do not provoke quota/auth errors.
8. What corrections/revisions/history retention and actual publication/update
   metadata are available? Historical forecast availability/cutoff correctness
   needs separate real evidence; latest API and ERA5 cannot establish it.
9. Are evaluation/service access, provider licensing/owner eligibility and required
   attribution confirmed by the operator? Retained documentation grants no new
   commercial clearance, subscription or cloud authorization.
10. Do the exact real acquisitions replay with matching values/identities and
    unchanged original evidence under network denial? Count all requests, retries,
    bytes and deviations from the authorized finite plan.

## 24. Final verdict

Phase 2 Stage 7 — PASS.

The complete Phase 2 ingestion system has passed the final
offline pre-live engineering audit.

All locally detectable correctness, boundedness, security,
identity, provenance, persistence and replay requirements
required before controlled provider validation are satisfied.

Remaining questions require real provider observations and
are reserved for Phase 2 Stage 8.

Phase 2 Stage 8 has not been started or authorized.
