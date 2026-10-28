# Phase 2 Stage 1 — Shared multi-source foundation

Verification date: 2026-10-28 (Europe/Lisbon).

## A. Objective

Implement shared multi-source queries, normalized system/weather measurements,
versioned semantic outcomes and a private authentication/request boundary.
Preserve accepted Phase 1 serialization, original-byte archive, replay, OMIE
behavior, logging, retries and offline tests. No provider implementation or live
source verification is included. Phase 2 remains **in progress**.

## B. Baseline

- Existing branch: `main`; initial HEAD `70f4204` (`docs: record Phase 2 readiness assessment`).
- Locally recorded `origin/main`: `a4191a3`; local main one commit ahead.
- Initial working tree and index: clean. No fetch, branch creation, staging,
  commit or push was performed.
- Python 3.12.9 in the existing named pyenv environment `iberian_shakti`.

`git status` and the last 12 decorated commits were inspected before any change.
The committed assessment was read completely before implementation. The prompt
folder/README and complete operator Stage 1 prompt were saved first. ADRs 0003
and 0004 were written before their corresponding code; they record accepted
assessment decisions, not another readiness assessment.

## C. Authoritative inputs

- [Phase 2 readiness assessment](phase_2_readiness_assessment.md), especially
  §§J–R/U–X and the unchanged 44-criterion checklist.
- [ADR 0001](../../adr/0001-omie-day-ahead-source-and-market-price-contract.md)
  and [ADR 0002](../../adr/0002-local-ingestion-immutable-archive-and-replay.md).
- [Phase 1 closure](phase_1_stage_7_final_acceptance.md), repository instructions,
  README, architecture and ingestion runbook.
- Actual contracts, HTTP/retry/transport, archive/provenance, parser, logging,
  settings, tests and fixture behavior; `pyproject.toml` and `.env.example`.

The requested `src/iberian_shakti/config.py` does not exist. The actual shared
configuration is `src/iberian_shakti/ingestion/config.py`; no second root-level
configuration module was invented. No dependency was added or installed.

## D. ADR decisions

Two focused accepted ADRs were added to the index; ADRs 0001/0002 are unchanged:

- [0003: Multi-source query and measurement contracts](../../adr/0003-multi-source-query-and-measurement-contracts.md):
  canonical daily API snapshot identity; typed geography, instant/interval/source
  times; system Decimal and scientific weather values; schema families; separate
  version-2 metadata; closed normalized-record union; shared archive/runner/replay.
- [0004: Private authentication and semantic provider outcomes](../../adr/0004-private-authentication-and-semantic-outcomes.md):
  private fixed-origin GET policy; selected-provider header/query credentials;
  no secret persistence; active-credential echo rejection; safe semantic outcomes
  after raw archival; retained retry/transport/logging invariants.

## E. Query/snapshot contracts

`ApiSourceRequest` is separate from unchanged `SourceRequest`. It has explicit
version `2.0.0`, `api_snapshot` selection, source/report identity, archive query
partition day, a positive half-open UTC requested window bounded to 25 hours,
and a discriminated `SystemQuery` or `WeatherQuery`.

System selections carry typed area/border/boundary and bounded unique native
series IDs; weather selections carry a versioned project site, requested WGS84
coordinates, model and bounded unique variables. Selection tuples are immutable
and sorted canonically. No arbitrary parameter dictionaries, URL, headers,
credential fields or numeric API revision are accepted.

Canonical sorted-key JSON yields a deterministic SHA-256 query identity;
`ResolvedSource.for_api()` derives an opaque locator and filename from it and
rejects mismatches/fake observed numeric revisions. Requested window and query
partition are explicit; neither claims every returned support interval is inside
that day. Native revision/document observations belong to the normalized source
metadata, not a fabricated query revision.

Identical bodies retain existing `(source, report, partition day, SHA-256)` raw
identity and independent acquisition events. Changed bytes preserve both versions.
Different queries can reuse identical raw bytes while their distinct query
identity remains in immutable acquisition provenance; no archive path migration.

## F. Normalized record model

- `MarketPrice` code and wire shape are unchanged. The shared closed union is
  `MarketPrice | SystemMeasurement | WeatherMeasurement`.
- System measurements have a discriminated load/generation/interchange measure,
  technology/direction where applicable, explicit geography, instant/support
  interval/statistic/cadence, finite Decimal MW/MWh, publication status, nullable
  source times, native series/document/revision/profile and retrieval/parse IDs.
  Python float/int/string coercion into system Decimal values is rejected; JSON
  requires decimal strings. MWh requires interval sum; MW permits instant/mean.
- Weather measurements use generic temperature, wind-speed and shortwave-radiation
  variables, explicit unit/height/statistic, finite float with assessed bounds,
  model/site/requested/returned-grid/elevation metadata and provenance. Missing
  values require null plus explicit status/reason; they are not zero. Reanalysis
  is distinct from actual observations and forecasts. No Open-Meteo parser or
  provider variable catalogue is embedded in the generic models.
- Geographic area roles distinguish country, system/perimeter, bidding zone,
  control area and provider-native area; EIC/provider scheme is separate native
  metadata. Directed border endpoints and aggregate external boundaries are
  separate types. No entire provider catalogue was hard-coded.
- All times are UTC-aware. Instants and positive half-open intervals are separate
  variants; source cadence does not declare averaging support. Source issue,
  model-run, publication and update times are nullable and distinct from retrieval
  completion. No provider timezone, issue time or forecasting cutoff is guessed.
- Business identity excludes values, archive partition/schema version,
  provisional/final correction metadata and new parse IDs. Known forecast issue/
  run times distinguish editions. Unknown forecast editions include original
  retrieval-event identity, retaining separate acquisition snapshots. Replay
  keeps that original retrieval identity; its new parse event does not alter it.

The new contracts do no I/O, conversions, filling, resampling, aggregation or
feature engineering. Scientific plausibility bounds are project validation
policy, not claims about provider guarantees.

## G. Schema/version strategy

Legacy SourceRequest, MarketPrice and ParseProvenance continue to emit the same
JSON fields/values. Legacy parse schema family is available in memory as
`market_price`; no new field is inserted into old serialized metadata.

RetrievalProvenance accepts version 1 only for legacy requests and version 2
only for ApiSourceRequest. New `MeasurementParseProvenance` is a separate
version-2 wire shape with explicit `RecordSchema` family/version and optional
local catalogue version. Record schemas are initially version `1.0.0` in each
family. Version-1 readers still reject an unsupported version rather than
quietly interpreting it as old data.

`ParseResult` accepts the closed record/event unions and checks schema family,
version, source/report/day, record count and original retrieval/parse linkage.
An event cannot mix record families or claim zero-record success. Version-2
normalized content identity includes family/version/catalogue plus raw/parser
identity. Legacy normalized-content identity remains unchanged.

## H. Authentication/request boundary

`PrivateRequestPolicy` is an execution object pinned to a supplied fixed HTTPS
origin; API acquisitions require this policy. It builds an opaque private GET
request with identity encoding, injecting either `HeaderAuthentication`
(`x-api-key`) or `QueryAuthentication` (`securityToken`). It rejects changed
origin/port, userinfo, fragments, preinjected token parameters and active secrets
smuggled into safe source/query identity before I/O. Provider origins themselves
remain future provider configuration; no source connection is made here.

Private URL/headers and credentials have no persisted-contract fields; repr omits
private material. `load_provider_auth()` reads only the selected existing
ESIOS_API_TOKEN or ENTSOE_API_TOKEN. Anonymous paths return without reading the
environment. No import-time read, .env loader, login, refresh or registration.
SecretStr settings exclude the token from dumps/repr; loader errors are static.
The documented initial credential bound is 8–4096 printable non-whitespace ASCII
characters, an application policy rather than a verified provider token grammar.

Tests exercise private header/query injection through MockTransport and scan
returned/provenance/archive JSON plus managed output for synthetic secrets.
Normal successful original body bytes remain unchanged; authentication material
is not reconstructed from a redacted URL or persisted alongside the safe query.
TLS, trust_env=False, zero redirects, raw streams and underlying transport retry
policy remain the same as Phase 1.

## I. Semantic outcomes

Error vocabulary adds no-data, authentication/authorization failure, provider
rejection, unsupported domain/schema, unknown time semantics and sensitive
response. Existing rate-limited/content/transport/archive codes remain.

New measurement parse outcomes represent:

| Outcome | Allowed meaning |
| --- | --- |
| success | Positive records, no error |
| source_unavailable | No data, zero records |
| provider_rejected | Auth, authorization, quota, domain or request rejection; zero records |
| content_failure | Content/encoding/integrity/schema/time-profile failure; zero records |

Synthetic parsers prove HTTP-200 acknowledgements can be archived as successful
retrievals, followed by unsuccessful semantic parse events without falsifying
status 404, creating data success or retrying parsing. Actual provider body
classification remains later. Legacy price parsing retains its original success/
content-failure rules. Private-policy HTTP 401/403 have terminal safe codes;
no provider-specific retry override was introduced. Three-attempt defaults,
backoff and finite transport budgets remain unchanged.

## J. Archive/replay compatibility

Raw path construction, SHA-256 content identity, no-replace publication, hash
verification, metadata atomicity and `replay()` code are unchanged. The archive
parse-event reader accepts explicit legacy/new versions and verifies event
version/linkage before publication. No old object is edited or migrated.

`ingest_resolved()` shares persistence-before-parsing for API/OMIE acquisitions;
the existing OMIE resolver delegates to the same chain. The OMIE identity change
only widens a validation argument annotation; its existing SourceRequest
validation still rejects API requests. The live summary adds a type guard for
the expanded record union; valid OMIE behavior and authorization are unchanged.

A small synthetic compatibility fixture was generated offline with the committed
pre-Stage-1 source at `70f4204` in `/tmp`, not the modified model implementation.
It stores baseline JSON/canonical sidecars and references an already committed
unchanged OMIE payload fixture. Tests read those bytes as existing archive
history, reproduce 192 prices, compare original JSON and normalized values and
reuse existing retrieval/parse events byte-for-byte without migration.

Synthetic system and weather integrations use actual shared HTTP/archive/runner
components with capability-double parsers. They verify original bytes, query
identity, typed provenance, changed/unchanged snapshot bodies and network-denied
replay. Fixed-version values/identities reproduce; only new parse identity/time
changes. No live metadata, geocoding, schema or catalogue lookup exists.

## K. Security/redaction

Synthetic tests cover header and query credentials, environment configuration,
secret-bearing URL parameters, unchecked transport/other exception text,
Pydantic validation errors, safe query abuse, allowlisted response-header echoes
and literal/quoted/escaped body echoes. Existing managed logging and transport
debug suppression remain unchanged and their original tests still pass.

An active credential echoed by a complete 200 body causes terminal
`sensitive_response` before RawPayload/hash/archive creation. Only safe status,
attempt/outcome/error metadata is returned; neither redacted nor original secret
bytes are published. Non-200 bodies are not archived/logged. Allowlisted HTTP
observations containing the active credential are omitted.

Authenticated nonidentity encoding is rejected before publication because the
narrow echo guard cannot safely inspect arbitrary encoded bodies. Anonymous
Phase 1 raw-byte behavior remains unchanged. This is not a general DLP detector
and does not claim to detect arbitrary transformed or unrelated secrets.

The original pytest network-denial guard is unchanged. A new test exercises
private default transport construction and proves that the guard rejects network
use before an actual synthetic-host connection. Other request tests use injected
MockTransport. No provider request/DNS lookup, schema download, credential
presence inspection or live validation occurred. Only synthetic secrets were used.

## L. Tests added

| New test module | Passing cases | Evidence |
| --- | ---: | --- |
| `tests/contracts/test_multisource.py` | 94 | Strict/frozen/canonical queries; secret-field rejection; bounded collections/window; geography; Decimal/finite values; weather units/missing/support; UTC/source times; editions/business identity; closed schemas/record union. |
| `tests/unit/ingestion/test_private_requests.py` | 55 | Private header/query injection; origin pinning; terminal auth; inherited retries/timeouts; selective credentials; repr/dumps/validation/logging; response echoes; encoded-body rejection; offline guard. |
| `tests/integration/test_multisource_foundation.py` | 31 | New-family shared chain/replay; ten semantic cases; immutable duplicate/correction snapshots; invalid states/linkage; baseline Phase 1 wire/storage replay; fixture checksums. |
| Total | **180** | All focused cases pass; no real provider fixture or credential required. |

The existing 968 cases remain unchanged and pass in the full suite. The new
fixture and checksum inventory under `tests/data/shared_contracts/` contain
synthetic metadata only; no readiness-assessment /tmp responses were copied.

## M. Full validation

All commands run offline in the existing Python 3.12.9 environment. Final exact
results are recorded below; no live test or dependency/hook download is used.

| Command | Result |
| --- | --- |
| Focused three-module pytest invocation | 180 passed in 1.19s. |
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 93 files already formatted. |
| `mypy src` | Success: no issues found in 37 source files. |
| `python -m pytest` | 1148 passed in 9.46s; 1148 collected, zero failed/skipped, no warnings. |
| `git diff --check` | Passed, no output; new-file whitespace also checked explicitly. |
| `pre-commit run --files <every changed/new path>` | Passed on all 30 changed/new paths: Ruff check/format, whitespace, EOF, large-file and private-key hooks; YAML/TOML skipped (no applicable changed paths). |

The pinned hook Ruff initially rejected an imported fixture alias; the new test
module now owns its logging fixture, preserving the existing tests and rules.
The affected 55 cases and the final full suite pass; final hooks did not mutate
files. No warnings, skips, resource errors or weakened assertions are accepted as a
substitute for passing evidence. Complete tracked/untracked and cached diffs are
reviewed; ignored generated caches are cleaned after validation. The sole
readiness report, Phase 1 ADRs/history, existing tests/fixtures/hashes, provider
stubs, network guard, retry/transport backend and dependency declarations remain
unchanged. No branch/index/history mutation or commit/push occurs.

## N. Phase 2 acceptance traceability

The following criterion text is copied verbatim from authoritative §V. Status
means evidence established by this Stage 1 scope; it does not close Phase 2 or
mark any provider/live criterion complete. Provider-dependent portions remain
explicitly pending. No criterion is replaced or weakened.

| Criterion (unchanged original wording) | Stage 1 status | Evidence / outstanding work |
| --- | --- | --- |
| 1. Accepted Phase 2 query/measurement/auth/semantic-outcome decisions are recorded in focused ADR(s) before corresponding implementation; Phase 1 ADR history is retained and this report remains the sole readiness assessment. | SATISFIED | ADRs 0003/0004 written before code, accepted assessment retained. |
| 9. Query contracts carry validated nonsecret product/window/domain/variables/location/model identity and explicit selection semantics; API snapshots do not fabricate numeric OMIE revisions or guaranteed latest versions. | SATISFIED | Canonical typed API queries, explicit snapshot mode, safe query fingerprint and bounds. |
| 10. New system/weather record families and parse schema-family versions are strict, frozen and typed; MarketPrice and Phase 1 serialized archive/provenance remain readable and behaviorally compatible. | SATISFIED | Closed record/event unions and baseline wire/canonical-sidecar compatibility test. |
| 11. Geographic roles distinguish country, mainland/system perimeter, bidding zone, control area, EIC and coordinate; native IDs remain available and directed/aggregate interchange are not conflated. | SATISFIED | Area roles/perimeter/native scheme/site and directed/aggregate boundary contracts. |
| 12. MW, MWh and EUR/MWh remain distinct; system/market decimals have no binary-float intermediate and financial serialization preserves exact decimal values. | SATISFIED | Strict system Decimal/string JSON and unchanged MarketPrice tests; MW/MWh invariants. |
| 13. Scientific weather values are finite floats with explicit verified units, height/statistic and versioned plausibility/missing policy; no clipping or implicit unit conversion occurs. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Scientific contract bounds/units tested; source output units require provider verification. |
| 14. Every normalized time is UTC-aware; instant samples, positive half-open intervals, source cadence and weather preceding-hour support remain distinct and query boundary handling is tested. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Shared UTC/instant/interval/preceding-hour support tested; provider timezone/end-boundary profiles remain later. |
| 16. Actual, forecast and reanalysis kind is explicit; issue/publication/update/acquisition times remain distinct and unknown source times/horizons stay null. | SATISFIED | Explicit value kinds and nullable separate source times; no inferred acquisition-as-issue time. |
| 17. Multiple known forecast editions and unknown-edition acquisition snapshots for the same target survive distinctly; historical refetches are never declared known at an earlier market cutoff without evidence. | SATISFIED | Known editions and unknown acquisition snapshots remain distinct; revision/replay tests. |
| 18. Source-selected credentials use ESIOS_API_TOKEN and ENTSOE_API_TOKEN, validated before I/O and injected privately using the verified mechanism; anonymous providers and OMIE need neither credential. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Selected configuration/private injection complete with synthetic tokens; real provider authentication remains later. |
| 19. Authentication/authorization failures are terminal, safely diagnosed and tested; there is no pasted-secret workflow, implicit dotenv load, auto-registration or token-refresh/probing loop. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Shared HTTP 401/403 and semantic codes are terminal/tested; actual provider body classification remains later. |
| 20. Every external call uses finite phase/attempt/operation budgets, response caps, verified TLS, zero redirects and no hidden transport retries; whole-invocation query/attempt/byte/time caps are enforced. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Shared finite transport/deadline/size/retry rules retained/tested; provider invocation-wide caps remain later. |
| 24. Original complete safe provider body bytes are archived unchanged before transformation/semantic parsing using reused SHA-256 content addressing and atomic no-replace publication. | SATISFIED | Existing raw byte/hash/no-replace archive reused; shared real-component synthetic tests. |
| 25. Independent identical acquisitions reuse content while retaining immutable events; changed bytes under unchanged provider/query/revision keys retain both versions and repeated event IDs remain idempotent. | SATISFIED | Identical/changed query snapshots, independent immutable events and idempotent reuse tested. |
| 26. Retrieval provenance retains safe query/locator, acquisition UTC/status/attempts, native revision observations when known, byte/hash/archive linkage; no private request data is persisted. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Safe query/acquisition/status/hash linkage verified; provider-native observations require actual provider stages. |
| 27. Separate parse provenance records parser/schema/catalogue versions and original raw/retrieval linkage; every normalized record links back to that chain and persistence failure prevents success. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Versioned schema/catalogue/parser/raw/event linkage enforced; concrete provider catalogue/version evidence remains later. |
| 30. Provider-specific auth/quota/domain/semantic/schema errors map to controlled typed categories, including ENTSO-E acknowledgement context rather than reason 999 alone; raw error text is never logged. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Shared typed outcomes/context rules tested synthetically; actual acknowledgement grammar/classification remains later. |
| 31. Safe logging/CLI/exception/config/metadata boundaries are tested with synthetic secret-bearing URLs, headers, rejected validation inputs and credential echoes; sensitive raw-body publication is rejected without pretending redaction preserves original bytes. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Shared synthetic-secret/echo boundaries tested; each later provider integration must retain this protection. |
| 32. Each selected product replays entirely offline from archived bytes/history plus pinned catalogue metadata, with no name/geo/schema/weather/model network lookup and no fallback acquisition. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Old and synthetic new families replay entirely offline; mandatory product replay remains later. |
| 33. Replay verifies hash/linkage and reproduces fixed-version normalized values and identities; only new parse event identity/time may differ and original retrieval history remains unchanged. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Baseline/synthetic replay identities reproduce; actual future provider acquisitions still need replay evidence. |
| 36. Existing OMIE fixtures and meaningful tests are preserved; shared changes pass Phase 1 regression and old-provenance/replay compatibility tests without weakening assertions. | SATISFIED | All original tests/fixtures retained plus explicit baseline JSON/canonical archive reproduction. |
| 37. Repository-wide python -m pytest succeeds with the existing network-denied guard active from collection, without credentials, real providers, subprocess networking or a live-enabling test switch. | SATISFIED | Full suite passes with unchanged repository network denial and no credentials. |
| 42. Final Python 3.12 ruff check ., ruff format --check ., mypy src, python -m pytest, git diff --check and applicable pre-commit checks pass; full new/staged/unstaged diff and Git status are reviewed. | SATISFIED | Full offline quality gates, applicable hooks and complete diff review. |
| 43. No Snowflake/dbt/features/ML/registry/inference/API/dashboard/deployment/Kafka/Kubernetes implementation, paid-resource change, bulk download or unnecessary runtime dependency enters Phase 2. | SATISFIED | No new dependency/provider/paid resource or Phase 3+ implementation. |

The other Phase 2 criteria remain for their provider, hardening, live and closure
stages; no new readiness assessment is recommended. None of the 24 selected
criteria is NOT YET APPLICABLE: each has at least shared-foundation evidence.

## O. Files changed

Every path is accounted for below. All changes are left unstaged.

| Path | Change |
| --- | --- |
| `.env.example` | Comment-only selected-loader guidance; existing token names/empty values retained. |
| `README.md` | Actual Stage 1 status/capabilities and authoritative report links; provider integrations pending. |
| `docs/adr/0003-multi-source-query-and-measurement-contracts.md` | Accepted query/measurement/versioning/compatibility decisions before code. |
| `docs/adr/0004-private-authentication-and-semantic-outcomes.md` | Accepted private request/security/semantic decisions before code. |
| `docs/adr/README.md` | Index new accepted ADRs. |
| `docs/architecture/README.md` | Current shared foundation, compatibility/security boundary and pending providers. |
| `docs/codex/prompts/phase_2/README.md` | Permanent prompt history policy and naming convention. |
| `docs/codex/prompts/phase_2/phase_2_stage_1_shared_extensions.md` | Full operator Stage 1 prompt stored before implementation; not a summary. |
| `docs/codex/reports/phase_2_stage_1_report.md` | This scoped implementation/validation/traceability report. |
| `docs/runbooks/README.md` | Phase 2 in-progress status; no production claim. |
| `docs/runbooks/ingestion.md` | Shared query/metadata/auth/semantic operation notes; existing OMIE instructions retained. |
| `src/iberian_shakti/contracts/geography.py` | Typed areas/native schemes/borders/sites/coordinates. |
| `src/iberian_shakti/contracts/ingestion.py` | Closed request/record/event extensions and strict version/semantic/linkage rules. |
| `src/iberian_shakti/contracts/measurements.py` | Typed system/weather/time/schema/source metadata and edition identity. |
| `src/iberian_shakti/contracts/queries.py` | Canonical bounded API snapshot/query contracts. |
| `src/iberian_shakti/ingestion/archive.py` | Versioned parse-event reader; existing byte storage/publication/retrieval readers retained. |
| `src/iberian_shakti/ingestion/auth.py` | Private fixed-origin request/auth objects and narrow active-credential detection. |
| `src/iberian_shakti/ingestion/config.py` | Selected-provider secret loader/settings; existing ingestion loader unchanged. |
| `src/iberian_shakti/ingestion/errors.py` | Closed auth/authorization/sensitive-response failure reasons. |
| `src/iberian_shakti/ingestion/http.py` | Optional private request policy; terminal private 401/403; pre-publication secret guard. |
| `src/iberian_shakti/ingestion/omie/identity.py` | Type annotation/import only for shared request union; same validation behavior. |
| `src/iberian_shakti/ingestion/omie/live_smoke.py` | Narrow union to MarketPrice or fail closed; same valid OMIE summary/opt-in behavior. |
| `src/iberian_shakti/ingestion/retrieval.py` | Version selected from request type when assembling provenance. |
| `src/iberian_shakti/ingestion/runner.py` | Extract shared resolved-source persist-before-parse composition. |
| `tests/contracts/test_multisource.py` | 94 synthetic contract/identity/validation cases. |
| `tests/data/shared_contracts/README.md` | Synthetic baseline fixture purpose/origin and maintenance policy. |
| `tests/data/shared_contracts/manifest.json` | Exact-byte synthetic fixture checksum inventory. |
| `tests/data/shared_contracts/phase_1_history.json` | Small synthetic compatibility metadata generated with baseline committed source. |
| `tests/integration/test_multisource_foundation.py` | 31 shared-chain/semantic/compatibility/replay cases. |
| `tests/unit/ingestion/test_private_requests.py` | 55 synthetic request/config/security/offline cases. |

## P. Remaining Stage 1 limitations

- No provider integration, source grammar, live authentication/coverage,
  catalogue, invocation-wide provider cap or provider-specific semantic/retry
  classification is implemented. These are later stages, not a Stage 1 defect.
- Query windows are bounded daily acquisitions (at most 25 elapsed hours);
  pagination, ZIP/XML handling, backfill/scheduling and feature computations are
  outside this shared stage. Schema families initially support version 1.0.0.
- Unknown forecast editions retain original retrieval-event identity; they do not
  reconstruct unobserved provider publication/issue history or a known-at cutoff.
- Echo protection covers active literal/URL-quoted/JSON-escaped UTF-8 credentials;
  it is deliberately narrow. Authenticated nonidentity bodies fail before
  publication until a concrete provider stage justifies bounded safe handling.
- Local filesystem trust, hard-link/fsync availability and cooperative host
  deadline limitations remain those already accepted in Phase 1.

No unresolved requirement within the authorized Stage 1 scope remains. No new
runtime dependency, provider-specific fixture/live artifact or Phase 3+ component
was introduced. Provider access/legal/time uncertainties remain as recorded in
the authoritative assessment, without being recast as Stage 1 success evidence.

## Q. Stage verdict

**PASS**

Stage 1 contracts, ADRs, private request/auth boundary, semantic outcomes,
compatibility evidence and offline validation are complete. Phase 0/1 remain
CLOSED/PASS; Phase 2 remains in progress. The full phase is not accepted here.
No commit, push or branch was created. Stage 2 was not started.

## R. Next stage

Phase 2 Stage 2 — REN integration
