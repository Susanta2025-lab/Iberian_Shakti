# Phase 1 — Ingestion Foundation & OMIE Integration: Readiness Assessment

Assessment date: 2026-10-26 (Europe/Lisbon). Repository baseline: `main`, commit `399fc912bc2eea7fa465f76c61c92b27c7156cd4` (`docs: add Codex repository instructions`).

This is the single assessment for the entire Phase 1. It covers retrieval through deterministic typed normalization, including historical and modern OMIE periods, revisions, provenance, replay, configuration, logging, documentation, and verification. It authorizes no implementation by itself. After acceptance, the decisions and acceptance checklist below are the baseline for every Phase 1 implementation stage.

## 1. Final readiness verdict

**PASS WITH GAPS**

Implementation can begin safely after this assessment is accepted. The repository layout, Python version, quality configuration, and architecture guardrails support the requested scope. There is no existing ingestion implementation or incompatible schema to migrate. Public OMIE documentation and actual downloaded reports establish a usable source and demonstrate modern quarter-hourly and legacy hourly records.

The gaps are implementation work: contracts, retrieval, archive, parser, fixtures, tests, configuration, operational documentation, and ADRs are absent. The CSV ignore rule needs a narrow fixture exception if CSV fixtures are used. Runtime dependencies have not been declared or installed. Remaining external uncertainties are bounded below and do not prevent building the verified report integration. They must not be replaced with invented publication guarantees or encoding assumptions.

This verdict means ready to implement the whole phase; it does not mean any ingestion capability is operational today.

## 2. Verified current repository state

### Implemented today

- A Python package skeleton and development foundation only. All 14 tracked Python files under `src/iberian_shakti/` are zero-byte `__init__.py` files, including `common/`, `contracts/`, `ingestion/`, and `ingestion/omie/`.
- Repository instructions and architecture/development documentation exist. They require immutable raw data, provenance, bounded retries, finite timeouts, typed code, offline default tests, and explicit live validation.
- No functioning source adapter, parser, archive, configuration loader, logging setup, normalized record, or application workflow exists.

### Configured today

- `pyproject.toml`: setuptools build, Python `>=3.12,<3.13`, no runtime dependencies. The `dev` extra declares pytest, pytest-cov, Ruff, mypy, and pre-commit.
- Pytest searches `tests/`, adds `src` to its import path, and uses `-ra`. There are no live markers, live exclusions, or network guards.
- Ruff targets Python 3.12 with E/F/I/B/UP checks and a 100-character line length. Mypy is strict over `iberian_shakti`.
- `.pre-commit-config.yaml` pins Ruff hooks at `v0.13.2` and pre-commit-hooks at `v6.0.0`; it includes whitespace, YAML/TOML, large-file, and private-key checks. Installed Ruff differs from the hook pin; avoid unrelated toolchain changes in Phase 1.
- `.env.example` contains `APP_ENV`, `LOG_LEVEL`, ESIOS/ENTSO-E token placeholders, and Snowflake placeholders. It has no ingestion timeout/retry/archive settings. A template does not imply automatic `.env` loading.
- `.gitignore` excludes root `/data/`, `raw_data/`, secrets, caches, and various artifact extensions. `*.csv` applies even inside `tests/data/`; the earlier `/data/` correction preserves that directory but does not unignore CSV fixtures. Original extensionless OMIE files and JSON fixture manifests are not ignored.
- `.python-version` names the existing `iberian_shakti` pyenv environment; selected Python is 3.12.9. No new virtual environment is needed.

### Skeleton/placeholders

- All five source adapter packages (`omie`, `ren`, `esios`, `entsoe`, `weather`) are empty.
- `tests/unit/`, `tests/contracts/`, `tests/integration/`, `tests/data/`, and `tests/e2e/` contain only `.gitkeep`.
- `.github/workflows/`, `apps/`, Snowflake, dbt, Docker, and Terraform areas are placeholders. There is no CI workflow implementing the quality gates.
- `docs/adr/` has the catalog/template and no individual ADRs. Architecture and runbook READMEs describe intent and operating rules, not running services.

### Planned only

Snowflake RAW/CURATED/FEATURES/SERVING, transformation, features, models, training, inference, monitoring pipelines, API/dashboard, infrastructure, and all provider integrations. Local inspection cannot establish external cloud account/resource state; no cloud discovery or changes were performed.

### Absent

Actual tests and fixtures; ingestion interfaces; shared schemas; HTTP client dependency; raw archive; replay command; parser/version contract; structured events/redaction; source availability handling; live smoke command; dependency lockfile; individual implementation ADRs; ingestion runbook.

### Inspection and baseline evidence

Read root `AGENTS.md` before other repository inspection, then `README.md`, `pyproject.toml`, `.gitignore`, `.env.example`, `.pre-commit-config.yaml`, all four `.cursor/rules/*.mdc` files, and the architecture, ADR, and runbook READMEs. Inspected the actual source/test/docs trees, file sizes, tracked files, ignore behavior, Git status, and recent history. No nested `AGENTS.md` was found in the repository search.

Initial Git status was clean on `main...origin/main`. Recent local history: `399fc91` instructions, `1be5904` architecture guardrails, `72493a4` preservation of the test data directory, followed by foundation/environment commits. The remote was not fetched, so this does not certify remote freshness.

Read-only baseline checks:

| Check | Observed result |
| --- | --- |
| `ruff check . --no-cache` | Passed |
| `ruff format --check . --no-cache` | Passed; 19 files already formatted |
| `mypy src --cache-dir /tmp/iberian-shakti-phase1-mypy` | Passed over 14 source files |
| `python -m pytest --collect-only -q -p no:cacheprovider` | No tests collected; no behavior is validated |
| `git check-ignore -v --no-index ...` | `/data/` and fixture CSVs ignored; original OMIE filenames and fixture JSON permitted |

Selected Python has pytest 9.1.1, Ruff 0.16.9, mypy 2.3.1, and pre-commit 4.6.2 installed. HTTPX, Pydantic, and pytest-cov are not installed in that environment. These are observations, not dependency pins. No packages were installed during this assessment.

### Verified OMIE evidence and limits

External evidence was inspected on 2026-10-26. Use the primary sources linked here, rather than the legacy word “hourly” in a page title, to interpret the data.

| Evidence | Finding and implication |
| --- | --- |
| [OMIE launch release, 1 October 2025](https://www.omie.es/sites/default/files/2025-10/2501001_go_live_mtu15_md_en_vf.pdf) | Day-ahead clearing on 30 September produced 96 quarter-hourly prices for delivery 1 October 2025. This fixes the modern granularity transition for this adapter. |
| [OMIE public file format v1.37, dated 30 September 2025](https://www.omie.es/sites/default/files/2025-09/formato_ficheros_inf_pub_137.pdf), §5.1.1.1, p.13 | `marginalpdbc_YYYYMMDD.v`, `MARGINALPDBC;` header, year/month/day/integer period/PT price/ES price, semicolon separation, dot-decimal examples, and final `*`. The report includes both areas. Periods may reach 100. §3 identifies prices as EUR/MWh and distinguishes graphical exports. This is the newest format specification located, not proof that no newer document exists. |
| [OMIE previous format v1.36](https://www.omie.es/sites/default/files/2025-03/formato_ficheros_inf_pub_136.pdf), §6.18, p.67 | Same report family and price-column order; legacy period range includes 1–25, and signed prices are described. Historical compatibility needs explicit format/calendar tests rather than generic CSV guessing. |
| [Current OMIE file index](https://www.omie.es/en/file-access-list?realdir=marginalpdbc) | The inspected Spain-family listing includes `marginalpdbc_20261026.1`, published/changed 25 October at 13:27:36, and `marginalpdbc_20251127.2`. Other dates have later D-1 or D timestamps. Revision `.1` is not universal; listing change time is not a guaranteed first-publication timestamp. |
| [OMIE day-ahead results description](https://www.omie.es/en/market-results/daily/daily-market/day-ahead-price) | Describes period 1 as H1Q1, 00:00–00:15 CET, for both electrical systems. This presentation label must not replace the selected file's numeric period identity. |
| [OMIE-hosted market rules, Annex 1, p.225](https://www.omie.es/sites/default/files/2025-03/resolucion_dcoor-de-009-24.pdf) | Describes sequential 96-period delivery days and 92/100 on clock changes. A fixed UTC+1 offset cannot represent this calendar correctly. |
| [OMIE market information](https://www.omie.es/en/market-information) | Includes a May 2026 notice about a negative SDAC minimum clearing price. Do not impose a nonnegative-price validator or treat old documentary ranges as current market caps. |

Direct anonymous HTTPS GETs also succeeded, without credentials, using the following download mechanism: [public download example](https://www.omie.es/en/file-download?parents=marginalpdbc&filename=marginalpdbc_20261026.1). Query parameters are `parents=marginalpdbc` and the exact `filename`. Files were inspected only in `/tmp`; none was added as a repository fixture during this task. The sandbox initially blocked DNS; an approved network read then succeeded. The browser tool could inspect documentation/listings but could not render the binary download.

| Downloaded filename | HTTP | Bytes | Data rows / period range | Other observation |
| --- | --- | --- | --- | --- |
| `marginalpdbc_20261026.1` | 200 | 2,637 | 96 / 1–96 | Ordinary modern delivery day |
| `marginalpdbc_20261025.1` | 200 | 2,734 | 100 / 1–100 | Autumn DST; negative price observed |
| `marginalpdbc_20260329.1` | 200 | 2,279 | 92 / 1–92 | Spring DST; negative price observed |
| `marginalpdbc_20250930.1` | 200 | 633 | 24 / 1–24 | Legacy day immediately before transition |
| `marginalpdbc_20250330.1` | 200 | 599 | 23 / 1–23 | Legacy spring DST; six rows have unequal PT/ES prices; negative price observed |
| `marginalpdbc_20251027.1` | 200 | 2,675 | 96 / 1–96 | Additional modern sample |
| `marginalpdbc_20251127.2` | 200 | 2,613 | 96 / 1–96 | Actual revision-2 file is accessible |
| `marginalpdbc_20990101.1` | 404 | Not archived | Not applicable | Far-future missing report returns an HTML error response |

Successful samples were ASCII-compatible bytes, with CRLF, trailing row semicolons, dot decimals, and the final `*`. The ordinary modern sample's SHA-256 is `5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e`; autumn modern is `763aebcdccc9ed1b94aba4be4de4d73ac76376a2c8660f87424b1dee1dd0f79e`; spring modern is `9159169cd6b18c158ee7c3a0cc1c9c588dc42282617ce697dc9f3c670c1b8f95`. Responses used `application/octet-stream`, without a charset or Content-Encoding. ASCII-compatible samples cannot establish whether OMIE globally promises UTF-8, Latin-1, or another superset.

**UNVERIFIED external details:** a guaranteed publication minute/SLA; every possible not-yet-published HTTP/body variant; a contractual charset guarantee; whether content can change under the same filename/revision; complete revision history and historical retention/pagination guarantees; every older format and legacy autumn file's exact bytes. No evidence establishes a stable “latest revision” API. These do not block the verified report family: use bounded discovery, exact-revision requests, explicit unavailable states, content hashes, strict decoding, and a documented historical support envelope. Resolving a specific fixture or response detail during implementation is normal source verification, not another readiness assessment.

## 3. Whole-Phase-1 readiness matrix

Statuses describe readiness to undertake implementation, not completed functionality. GAP means required work is missing but can be implemented within this phase; BLOCKER means work cannot safely begin.

| Area | Status | Assessment / locked direction |
| --- | --- | --- |
| Ingestion abstraction | READY WITH IMPLEMENTATION DECISION | Empty layout supports a synchronous typed adapter protocol and injectable retriever/archive/parser orchestration. See §5. |
| OMIE retrieval | READY WITH IMPLEMENTATION DECISION | Public GET verified; support exact revision plus bounded listing-based selection, not an assumed `.1`. |
| OMIE parsing | GAP | No parser. Implement the verified numeric-period family with strict whole-report validation. |
| Normalized contract | READY WITH IMPLEMENTATION DECISION | One shared immutable schema, Decimal prices, separate PT/ES rows, provenance reference. |
| Market-period handling | READY WITH IMPLEMENTATION DECISION | Delivery date + sequential period + duration + UTC interval; modern 15-minute and legacy 60-minute profiles. |
| Raw archive | GAP | No archive exists; use ignored local content-addressed paths. |
| Immutability | READY WITH IMPLEMENTATION DECISION | Atomic no-replace publication and verified existing-content reuse; never write through an existing object. |
| Revisions | READY WITH IMPLEMENTATION DECISION | Preserve each new content hash, even under an unchanged revision label; retain revision observations separately. |
| Provenance | GAP | Define retrieval and parsing provenance once in contracts; immutable sidecars reference archived bytes. |
| Replay/idempotency | READY WITH IMPLEMENTATION DECISION | Content identity and parser/schema version define replay; a new retrieval event is not new raw content. |
| Errors/retries | READY WITH IMPLEMENTATION DECISION | Typed categories, three total attempts, bounded exponential backoff; unavailable is a terminal result for this run. |
| Configuration | GAP | Add a small validated environment reader; no automatic dotenv or provider credential expansion. |
| Logging | GAP | Standard logging with structured JSON events and an allowlist; redact locators/exceptions. |
| Dependencies | READY WITH IMPLEMENTATION DECISION | HTTPX + Pydantic v2 only as new runtime dependencies; no new test library. |
| Fixtures | GAP | None exist; retain small byte fixtures/manifest and narrowly unignore CSV if used. |
| Deterministic tests | GAP | No test modules; default must work without network, credentials, or installed secrets. |
| Mocked integration | GAP | Exercise real component chain with HTTPX MockTransport and temporary archive. |
| Live validation | READY WITH IMPLEMENTATION DECISION | Separate explicit module command outside pytest collection; no automatic CI invocation. |
| Publication/encoding/history guarantees | UNVERIFIED EXTERNAL DETAIL | Explicit limits above; fail visibly rather than invent guarantees. |
| ADR/documentation | GAP | Record two cohesive ADRs before their code, plus one ingestion runbook and developer usage. |
| Repository / Python baseline | READY | Clean Git state, Python 3.12.9, compatible configured quality gates. |

No matrix area is a BLOCKER.

## 4. Blocking issues

None found that prevent implementation from beginning safely.

Missing code, tests, dependency installation, fixture exceptions, ADRs, and settings are ordinary implementation tasks. External availability is not a prerequisite for writing and verifying deterministic components. Actual source behavior contradicting the verified format/calendar or an instruction conflict that cannot be reconciled would be a genuine blocking contradiction; it should be identified specifically, not used to reopen all of Phase 1.

## 5. Decisions to lock for Phase 1

### 5.1 Scope and ingestion boundary

Implement only: source request → resolve locator → retrieve bytes → immutable raw archive and retrieval provenance → parse/validate → typed normalized records and parsing provenance. Validate configuration/request/HTTP outcome before accepting a payload; archive complete downloaded bodies before parsing so malformed reports remain diagnosable. This refines the high-level architecture's validation step without changing its downstream boundaries.

Use synchronous execution. A small adapter protocol builds/resolves source requests and parses raw payloads. The reusable runner owns transport calls, retries, archiving, and result assembly; source-specific response interpretation belongs to the adapter. Inject HTTP client/transport, clock, sleeper, and archive root. Support local file bytes for offline retrieval/replay with the same raw/provenance contracts; do not implement a plugin registry, scheduler, async framework, or any future provider.

### 5.2 OMIE report selection, discovery, and parsing

Select the `marginalpdbc` day-ahead marginal-price file family as the one concrete integration. It already carries Portugal and Spain prices together; fetching a second Portuguese family is unnecessary. Exclude intraday, retail tariffs, chart exports, and aggregation reports.

Requests identify source `omie`, report `marginalpdbc`, delivery date, and an optional positive numeric source revision. An explicit revision resolves deterministically to the verified public download query. With no revision, inspect the public family listing and select the highest numeric revision listed for the requested date. Parse only matching filenames and validated same-origin download links with standard-library HTML/URL tools; compare revisions numerically. Never probe an unbounded series of revision numbers or silently fall back to `.1`.

Bound listing retrieval size and page traversal. Start with the verified family listing; if its coverage cannot establish the requested date, return an explicit discovery/coverage outcome and allow an exact-revision request. Do not interpret an unrecognized HTML page or an incomplete/paginated index as proof of nonpublication. Preserve the chosen locator/revision; selection means latest observed in that listing, not a guarantee that all historical versions were found. A discovered file disappearing before download yields controlled unavailability, not an unbounded rediscovery loop.

Parse an independent byte copy using strict ASCII for the selected numeric report grammar. ASCII is the verified subset, not an asserted global encoding guarantee. Do not use replacement decoding, automatic encoding guessing, or a Latin-1 fallback that masks corruption. CRLF and LF are supported without changing the archive. Reject unsupported BOM/non-ASCII bytes explicitly unless a future concrete supported sample justifies a versioned decoder change.

Require the exact header, six nonempty data fields and the expected trailing delimiter, consistent valid dates matching the request/filename, integer periods in source order, and exactly one terminal `*`. Permit a final line ending; do not silently skip interior blanks, extra columns, data after the terminator, duplicates, missing periods, or malformed rows. Numeric parsing uses signed finite Decimal values with the supported report precision, accepting lexical integers and one/two decimal digits. Reject NaN, infinity, exponents, grouped/comma decimals, missing values, or precision outside the supported grammar. Negative prices are valid; do not encode mutable regulatory price caps in the domain schema.

Validate the entire day before returning any normalized records. Unknown schema, truncated body, empty payload, inconsistent date, and invalid period sequence are typed failures with safe row/field context. Never return a partially accepted day.

### 5.3 Normalized market-period and price contract

Use one record per bidding area and delivery interval. Shared fields include source/report identity, `market="day_ahead"`, `market_area` (`PT` or `ES` for this adapter), `delivery_date`, positive sequential `period_index`, positive `duration_minutes`, timezone-aware `interval_start_utc` and `interval_end_utc`, finite Decimal price, `currency="EUR"`, `price_unit="MWh"`, and a provenance reference. The price is EUR per MWh, not an energy quantity. Preserve precision through JSON using decimal strings; do not route prices through binary floats.

Keep the shared duration field extensible; the OMIE profile accepts 60 or 15 minutes according to the verified transition. Do not constrain every future provider to OMIE's maximum period count or areas. Retain the numeric source period in provenance/record identity; H1Q1 is a presentation label, not a required alternative schema.

For OMIE, the market delivery day uses the DST-aware European market clock, represented by `Europe/Madrid`, for both areas. `PT` is the bidding area, not an instruction to shift the report's delivery date to Lisbon midnight. Derive the two local-midnight boundaries separately and convert them to UTC. Add period offsets in UTC, never by stepping naive/local wall-clock datetimes through DST.

- Delivery dates before 2025-10-01 use 60-minute periods: normally 24, spring 23, autumn 25.
- Delivery dates from 2025-10-01 use 15-minute periods: normally 96, spring 92, autumn 100.
- Expected count is elapsed UTC minutes between successive market-local midnights divided by resolution. The received periods must equal the ordered sequence `1..N`; a modern file with only 24 rows is truncated/invalid, not an hourly fallback.
- Enforce interval contiguity, full-day coverage, and exactly two area records per source period. No resampling, filling, hourly averaging, or timezone-dependent date rewriting.

Calendar rules and observed DST counts support this mapping. Local `zoneinfo` checks confirmed 1,380/1,500-minute market days for the downloaded spring/autumn dates. The provider's shorthand “CET” must not become a permanent fixed offset. Host IANA timezone data is an explicit prerequisite, checked at startup; absent data produces a clear configuration error.

Historical support means the explicitly tested legacy numeric `marginalpdbc` profile and the modern profile, not all OMIE historical products or unlimited remote backfill. The legacy autumn case requires a fixture before final acceptance; it was not downloaded in this assessment.

### 5.4 Immutable archive, revisions, and replay

Default root: repository-local `data/raw/`, configurable by environment and resolved consistently from the documented working directory. Example layout:

```text
data/raw/omie/marginalpdbc/2026-10-26/sha256/<64-hex-sha256>/
  payload.bin
  retrievals/<retrieval-event-id>.json
  parses/<parse-event-id>.json
```

The SHA-256 is computed over the original response body bytes, before charset decoding, newline changes, or parser transformation. Request identity transfer encoding. HTTPX's automatic content decoding must not accidentally change the archived bytes: retrieve the raw body stream; record Content-Encoding and reject unsupported encodings at parsing, preserving the original body. Transport framing is not file content. Local file retrieval reads bytes unchanged.

The content identity is `(source_id, report_id, delivery_date, sha256)`; the hash directory contains one payload even if the same bytes arrive under different filenames/revision labels. A different hash is a separate immutable version, including republishing under an unchanged `.v`. Revision labels, ETags, and Last-Modified are observations, never substitutes for content identity. No mutable `latest` payload or overwritten manifest is required.

Publish complete objects with atomic no-replace semantics on the same filesystem, using private staging plus a no-clobber publish operation. Do not use an overwrite-capable rename as the sole immutability guarantee. Existing destination content must be checked for expected hash/length; a collision, corruption, or inconsistent metadata is an archive-integrity error. Test concurrent identical writes and crash/interruption behavior. File modes alone do not establish immutability. This is application-enforced local immutability, not WORM infrastructure.

Metadata is immutable too. Retrieval events retain their timestamps/locators without rewriting an earlier sidecar. An event ID can be a hash of canonical, versioned event metadata. Replaying the same event must not duplicate it; a genuinely new acquisition may add a small observation referencing the existing payload. This is controlled provenance growth, not another raw copy. Never append by rewriting a shared JSON manifest. A failed metadata write must not report ingestion success; orphan payloads remain recoverable without changing their bytes.

Archive complete 200-response bodies even when empty, HTML, or malformed, then record content failure. An interrupted/oversized transport body is not a complete report and must not be published as one. Unavailable/permanent HTTP error pages are diagnostics, not successful raw reports.

Replay reads an archive reference, verifies its hash, and parses offline with explicit parser/schema versions. It does not make a network request or fabricate a new retrieval timestamp. A parse event is distinct from a retrieval event. Stable normalized content identity includes the content identity plus parser and normalized-schema versions. Business identity is `(source, report, market_area, delivery_date, period_index, duration_minutes)`; revisions remain distinguishable by content/version provenance. Retrieval time must not enter business or normalized-content identity.

`/data/` already protects the default archive from Git. Document that custom archive roots must also be outside tracked content. Preserve that ignore rule; never force-add bulk downloaded data. Only small intentional test fixtures under `tests/data/omie/` belong in Git.

### 5.5 Contract ownership and provenance

| Layer | Owns | Must not duplicate |
| --- | --- | --- |
| `contracts/ingestion.py` | Shared immutable SourceRequest, resolved locator, raw-payload/archive-reference, retrieval provenance, parse provenance, result/availability types, and adapter/retriever/archive protocol signatures | No HTTP client, filesystem writes, source-layout parsing, or second copy of normalized schemas |
| `contracts/market.py` | Shared normalized market-price record and reusable field/cross-field invariants | No OMIE filename grammar or date-dependent source-format selection |
| `ingestion/` | Protocol implementations, HTTP/file retrieval, archive, retry/error mapping, orchestration, replay, and local configuration | Import shared schemas; do not redeclare equivalent DTOs |
| `ingestion/omie/` | Family identifier, request restrictions, locator/discovery rules, source availability interpretation, parser/version identifier, column mapping, and market-calendar profile | No duplicate price/provenance contracts or private retry engine |
| `common/` | Only truly shared logging/redaction utilities | Do not turn it into a second ingestion package |

Module names may be adjusted for cohesion without another architecture assessment. Public schema ownership and behavior remain fixed. Frozen Pydantic models must use immutable nested collections where applicable; `frozen=True` alone does not freeze nested dictionaries/lists.

Required provenance fields:

| Information | Required representation / semantics |
| --- | --- |
| Source/report | Stable `source_id`, `report_id`; selected market/product |
| Requested report | Delivery date, requested revision if any, request/selection mode |
| Locator | Exact nonsecret public URL or file locator, resolved filename, observed revision; sanitize secret-bearing components for future providers |
| Retrieval | UTC-aware retrieval-completion timestamp, retrieval event ID, outcome, attempt count, HTTP status for HTTP (null for file) |
| Raw object | SHA-256, byte length, stable relative archive reference; hash verified on replay |
| HTTP observations | Allowlisted Content-Type/Content-Encoding, ETag/Last-Modified if present; not authoritative revision/publication proof |
| Parsing | Parser ID + explicit version, contract/schema version, raw/retrieval references, parse timestamp and success/failure code |
| Normalized linkage | Each record references parse provenance, which resolves to the archived payload and original retrieval |
| Unknown facts | Nullable source publication timestamp/revision only when genuinely unknown; never substitute retrieval time for publication time |

Record filename revision when determinable even if bytes match a prior acquisition. Keep parser identity in parsing provenance rather than pretending it existed at retrieval. Persist safe provenance only: credentials, cookies, authorization headers, signed query values, and arbitrary response/request headers must not enter logs or manifests. A future authenticated provider supplies a stable nonsecret locator and credential reference, not a secret-bearing URL.

### 5.6 Explicit error, retry, and unavailable semantics

Use typed application exceptions/results with stable error codes. Translate library exceptions at the boundary; retain safe diagnostic context and chained causes without logging raw exception strings or rejected input values.

| Condition | Behavior |
| --- | --- |
| Invalid date/revision, unsupported report, malformed environment/configuration | Fail before I/O; typed request/configuration error; no retry |
| Connection failure or connect/read/write timeout | Retry safe GET within one bounded retry policy; reset incomplete attempt bytes |
| HTTP 500, 502, 503, 504 | Retry under that same policy; exhausted attempts raise typed retrieval-exhausted error |
| HTTP 429 | Respect valid Retry-After only within the remaining bounded budget; otherwise return/raise controlled rate-limited failure without long polling |
| Clearly permanent 400, 401, 403, 405, 410, 422; other unclassified 4xx | Permanent retrieval error; no retry; 403 is not presumed “not published” |
| Valid OMIE filename returning 404 | Explicit unavailable result with `not_found` reason; no retry in this run. Preserve date/revision context; an old revision missing is not proof of future publication |
| Requested date absent from a valid, covering listing | Explicit unavailable/not-listed result; future-day context may indicate not-yet-published, without promising a publication time |
| Unrecognized/incomplete listing or uncovered historical date | Typed discovery/schema/coverage outcome, not an empty success and not a claim that the report does not exist |
| 200 empty, HTML, malformed, invalid numeric/schema/date/period, missing terminator | Archive complete bytes; typed content/parse/validation error; no automatic content retries or silent record dropping |
| Local file missing/unreadable; archive permission/disk failure; integrity mismatch | Typed local retrieval/archive error; no HTTP retry loop |
| TLS verification failure or invalid URL | Permanent transport/configuration failure; do not retry or disable TLS verification |

Selected transport-level incomplete-read/protocol failures can be retryable when the safe GET was interrupted; a complete body that fails the parser is a content failure. Other status codes are explicitly classified or fail closed; do not blanket-retry every exception or 5xx.

Default policy: **three total attempts**, including the first; backoff 1 second then 2 seconds, with a 4-second cap. Expose a small typed policy and inject sleeper/clock so tests never sleep. Disable underlying transport auto-retries to avoid multiplying attempts. Validate all numeric settings as finite and positive/nonnegative as appropriate; reject unlimited attempts/timeouts.

Use explicit connect/read/write/pool timeout values, initially 10 seconds each, plus an overall bounded attempt deadline (initially 30 seconds) and finite response-size limits appropriate to the adapter. HTTPX phase/inactivity timeouts are not a total response deadline; account for slow streaming using monotonic remaining-budget checks. Bound discovery and payload downloads independently and document the maximum request count of an ingestion run. Backoff and any Retry-After must respect the operation budget. No polling until publication and no hidden scheduler.

The exact prepublication response taxonomy beyond the tested 404 is UNVERIFIED. Do not implement undocumented 200-message signatures as availability rules; unknown 200 bodies remain content failures. Unavailable is distinguishable from success with zero records, validation failure, and retry exhaustion. A later explicit run may try again.

### 5.7 Configuration and logging

Read settings explicitly at startup from an injectable environment mapping with standard-library `os`, then validate them. No import-time network/filesystem work and no implicit `.env` loader. Document exported environment variables or a trusted shell setup; existing ESIOS/ENTSO-E/Snowflake placeholders are not required to run OMIE.

Minimum environment surface:

| Setting | Default / purpose |
| --- | --- |
| `RAW_ARCHIVE_ROOT` | `data/raw`; local archive destination |
| `INGESTION_TIMEOUT_SECONDS` | `10`; finite HTTP phase timeout |
| `INGESTION_MAX_ATTEMPTS` | `3`; includes initial attempt |
| `INGESTION_BACKOFF_SECONDS` | `1`; initial exponential delay |
| `LOG_LEVEL` | Existing `INFO`; validate level |

Keep deadline/backoff caps and per-adapter size bounds as documented typed policy defaults, not additional environment knobs unless actual operation requires them. `APP_ENV` can remain existing context; it need not select infrastructure. OMIE uses a fixed verified HTTPS origin, injectable in construction for testing; no user-facing `OMIE_BASE_URL` knob is necessary for Phase 1. No API token setting is needed for the verified public access path.

Use standard-library logging and a small JSON formatter/allowlisted event context: source/report/date, safe filename/revision, attempt, status, elapsed time, bytes/hash/archive reference, record count, parser version, outcome/error code. Configure handlers at the entry point, not library import. Include unavailable, reused-content, revision, validation-failure, and exhausted-retry outcomes. Never log payloads, whole configuration objects, raw headers, userinfo, query tokens, Pydantic rejected values, or unchecked exception strings. Test sanitization with synthetic authenticated-provider locators, including failure paths. Keep HTTPX/httpcore debug logging from bypassing the application's redaction policy.

## 6. Minimal dependency plan

### Runtime

| Proposed dependency | Purpose | Why standard library alone is insufficient for the chosen design / Phase 1 justification |
| --- | --- | --- |
| `httpx>=0.28,<1` | Synchronous pooled HTTPS, explicit timeout phases, typed transport failures, injectable transport | `urllib` can fetch bytes, but reproducing the desired client/transport seam, timeout categories, and deterministic mock transport would add custom plumbing. HTTPX supplies those capabilities in one dependency. Its built-in [MockTransport](https://www.python-httpx.org/advanced/transports/) also removes the need for an HTTP mocking library. [Timeout documentation](https://www.python-httpx.org/advanced/timeouts/) distinguishes phase timeouts from the application deadline. |
| `pydantic>=2,<3` | Immutable typed contracts, declarative validation, safe serialization, structured error information | Dataclass annotations do not enforce runtime fields/cross-field invariants or provide equivalent structured validation/serialization. Reimplementing those across requests, provenance, and normalized records would duplicate schema logic. Use deliberate strict validation and explicit parser conversion, as supported by [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/); sanitize errors before logging. |

These are proposed compatibility ranges, not claims about the latest package releases or resolved transitive versions. Resolve/install only during authorized implementation and verify Python 3.12 compatibility then. No dependency was installed in this assessment.

Standard library is sufficient for SHA-256, bytes/file access, no-replace local publication, dates/Decimal/zoneinfo, HTML/URL parsing, environment reads, sleep/deadline logic, JSON, logging, and redaction. System IANA tzdata is available here; document that prerequisite. A `tzdata` fallback dependency is unnecessary for this verified environment and can be justified later if required portability includes hosts without a timezone database.

### Dev/test

**No new test dependency.** Use existing pytest with `tmp_path`, `monkeypatch`, `caplog`, and standard-library mocks; use runtime HTTPX's MockTransport. Keep existing dev declarations: pytest (test runner/fixtures), pytest-cov (optional coverage support), Ruff (lint/format), mypy (static typing), pre-commit (existing hooks). The standard library does not replace those existing repository toolchain roles; do not remove or broaden them in this phase. The missing local pytest-cov installation is an environment gap, not a reason to add another package to `pyproject.toml`.

Do not add pandas, tenacity, structlog, python-dotenv, pydantic-settings, respx/pytest-httpx, FastAPI, Snowflake libraries, or orchestration frameworks. Phase 1 has no demonstrated need for them. Keep dependency changes in `pyproject.toml`; do not introduce an unrelated package-manager/lockfile migration.

## 7. Final Phase 1 file/change boundaries

This assessment task changes only `docs/codex/reports/phase_1_readiness_assessment.md`. The following is the future implementation boundary after acceptance, not permission to change it now.

| Allowed future path | Intended change |
| --- | --- |
| `src/iberian_shakti/contracts/` | Shared ingestion/provenance/market contracts and protocol definitions |
| `src/iberian_shakti/common/` | Shared logging/redaction only as required |
| `src/iberian_shakti/ingestion/` | Configuration, errors, HTTP/file retrieval, archive, orchestration, replay; focused public entry point if useful |
| `src/iberian_shakti/ingestion/omie/` | Adapter, locator/discovery, parser/calendar profile, optional explicit live smoke module |
| `tests/unit/`, `tests/contracts/`, `tests/integration/`, `tests/data/omie/` | Deterministic tests, small bytes/HTML fixtures, fixture metadata |
| `tests/conftest.py` | Network guard/shared fixtures if needed |
| `pyproject.toml` | Two runtime dependencies, narrowly required quality/test configuration |
| `.env.example` | Minimum local ingestion settings and comments; no secrets |
| `.gitignore` | Narrow `tests/data/omie/` CSV exception if CSVs are introduced; retain archive/secret exclusions |
| `docs/adr/0001-*.md`, `0002-*.md`, `docs/adr/README.md` | Two decisions and index links |
| `docs/architecture/README.md` | Brief implemented ingestion boundary and links |
| `docs/runbooks/ingestion.md`, `docs/runbooks/README.md`, `README.md` | Usage, replay, failure handling, live isolation, actual phase status |

Keep untouched: future-provider package stubs (`ren`, `esios`, `entsoe`, `weather`), `features/`, `models/`, `training/`, `inference/`, `monitoring/`, `apps/`, `snowflake/`, `dbt/`, `infra/`, `docker/`, `.github/workflows/`, `tests/e2e/`, root instructions, `.cursor/rules/`, and unrelated configuration. Do not add cloud/paid resources or serving, ML, streaming, Kafka, Kubernetes, or Terraform implementation. No automatic commits/pushes. Existing pre-commit configuration remains unchanged unless an actual Phase 1 incompatibility requires a narrowly explained correction.

Minimum ADR set, written before their corresponding implementation:

1. **ADR 0001: OMIE day-ahead source and market-price contract.** Report/endpoint selection, evidence/limits, numeric period semantics, transition date, DST/UTC mapping, Decimal/area representation, validation and historical envelope.
2. **ADR 0002: Local ingestion execution, immutable archive, and replay.** Interface ownership, retrieval/parse separation, content identity, atomic publication/revisions, provenance, retry/unavailable behavior, dependency choices, and offline/live isolation.

These two capture cohesive durable choices without separate ADRs for every setting or library. Writing them records accepted decisions; it is not a new architecture assessment or stage gate.

Minimum developer/runbook documentation: environment/prerequisites and quality commands; one-day ingestion and typed output; exact-revision versus latest-observed selection; raw layout and custom-root Git exclusion; offline hash-verified replay; error/outcome table and bounded retry behavior; revision recovery and archive-integrity handling; fixture maintenance with attribution/checksums; timezone/format support envelope; live invocation and interpretation. Correct the catalog's future “missing hours” terminology when documenting this ingestion path so it refers to market periods.

## 8. Complete Phase 1 test plan

Default `pytest` must require no network, credentials, paid resources, shell `.env`, or live source. All integration and contract tests are deterministic. Assert behavior/invariants, not merely that implementation methods were called.

### Deterministic units and contracts

| Location / subject | Required coverage |
| --- | --- |
| `tests/contracts/` | Valid requests, payload/archive references, retrieval/parse metadata, market records; invalid areas/currency/units where restricted, naive timestamps, invalid dates/revisions, bad SHA length/characters, inconsistent byte lengths/intervals, nonfinite Decimal, extra fields and unwanted coercion. Decimal serialization and immutable nested structures. |
| `tests/unit/` — OMIE parser | Header/footer, exact field layout, date agreement, PT/ES ordering using unequal prices, signed and zero prices, supported lexical precision, CRLF/LF, legacy/modern profiles, empty/HTML/non-ASCII/BOM payloads, bad numbers, unexpected columns, extra trailing data, truncation, missing/duplicate/reordered/out-of-range periods. Full report rejected on any bad row. |
| `tests/unit/` — market calendar | Legacy ordinary/spring/autumn counts 24/23/25; modern 96/92/100; 2025-09-30/2025-10-01 boundary; leap day and invalid calendar dates; exact UTC boundaries, duration, monotonicity, contiguity, repeated autumn hour and skipped spring hour. PT/ES share the source calendar. Reject modern 24-row files and wrong-day DST counts. |
| `tests/unit/` — hash/archive | Hash exact bytes including line endings; no newline/encoding normalization; immutable first write; identical content reuses payload; new hash preserves prior bytes; changed bytes under unchanged filename/revision; same bytes under different revision labels; repeated event idempotency; metadata failure and corruption; path traversal rejection; no replacement on concurrent write; interrupted/staged write never appears as a complete payload. |
| `tests/unit/` — retrieval/retry | Success; connection/timeouts/selected 5xx; exact three-attempt ceiling and injected 1/2-second sleeps; no nested retries; exhaustion; permanent 4xx; 404 unavailable with no backoff; bounded 429/Retry-After; unsupported schemes/TLS failures; stream interruption; deadline, response-size, redirect bounds; local file unchanged/missing/unreadable. Assert explicit finite HTTP timeout configuration. |
| `tests/unit/` — discovery | Exact revision bypasses listing; numeric latest selection including `.9` versus `.10`; `.2` without `.1`; invalid links/origin/filenames; absent date; unrecognized/partial/paginated listing coverage; disappearance after discovery; finite request/page bounds. |
| `tests/unit/` — config/logging | Defaults, environment overrides, invalid finite/range settings, no credential requirement for OMIE; structured outcomes and useful context; unavailable/reuse/content failure; secrets in URL userinfo/query/header/config/exception/validation input never logged or archived in metadata. No raw payload logging. |

### Fixtures under `tests/data/omie/`

Commit only small intentional report-byte and discovery HTML examples. Prefer original `marginalpdbc_YYYYMMDD.v` filenames or `.omie`/`.txt` to retain source shape; if CSV fixtures are used, narrowly unignore them under this fixture directory. Do not unignore root `/data/` or all repository CSVs.

Provide ordinary legacy/modern, legacy spring/autumn, modern spring/autumn, boundary dates, unequal PT/ES and negative prices, genuine revision-labelled content plus a controlled revised pair, and deliberately malformed/truncated examples. Parameterized synthetic complete days may cover large combinations; label synthetic files clearly. Include the observed 92/100-period cases as representative byte fixtures when implementing. A checksum manifest records source URL, filename/revision, delivery date, acquisition date, SHA-256, expected rows/resolution, and whether each sample is original, synthetic, or deliberately mutated. Tests never download fixtures at runtime. Do not pass a shortened excerpt off as a valid full-day fixture.

### Mocked integration under `tests/integration/`

Run the actual adapter → HTTP retriever → temporary immutable archive/provenance → parser → normalized-record chain through HTTPX MockTransport. Assert original bytes/hash, safe metadata linkage, both area prices, output types, parser version, and expected counts (192 ordinary modern records, 184 spring, 200 autumn).

Run again with identical bytes: one payload, stable normalized content identity, original provenance intact. Then supply revised bytes: two hashes/payloads with independently traceable records. Include unchanged revision labels. Replay from the archive with network disabled and compare deterministic values/identities; only parse-event timestamps may differ. Test retry-to-success/exhaustion, unavailable with zero retries/no successful raw report, malformed content archived but no normalized success, and archive/provenance persistence failure.

Use a default network-denial guard so an accidental real HTTP transport/socket connection fails tests. Pass mock transport explicitly; no environment-variable toggle may silently enable live access in pytest. Fake clocks/sleepers keep tests fast and repeatable; temporary roots isolate filesystem writes.

### Optional live smoke validation

Prefer a **separate module command**, not a pytest marker. It is easier to keep completely outside default collection and CI and avoids a marker being accidentally selected by broad pytest invocations. Intended explicit invocation after implementation:

```bash
python -m iberian_shakti.ingestion.omie.live_smoke --live --delivery-date 2026-10-26 --revision 1 --archive-root /tmp/iberian-shakti-omie-smoke
```

The command must require `--live` before any network I/O; module import performs no I/O. Date/revision are operator inputs, not a date tied to the test suite. The illustrated date is a verified sample, not a permanently available fixture service. It uses the real retrieval/archive/parser path, checks hash and calendar/area counts, and emits a safe summary. An omitted revision can exercise bounded latest-observed discovery.

Document success, explicit unavailable, transport failure, and content failure as distinct outcomes/exit statuses; unavailability is never a green ingestion result. Do not schedule it, call it from pytest, put it in pre-commit, or run it automatically in CI. Anonymous downloads were verified; no credentials are required for this selected route. Live observations supplement deterministic tests and are not a recurring readiness gate. If live execution is unavailable, record that fact; do not weaken deterministic acceptance or invent a live pass.

## 9. Phase 1 implementation sequence

Each stage proceeds directly from this report. No stage includes a readiness or architectural reassessment. Add meaningful tests with the behavior they validate, rather than deferring every test to the end.

1. Record ADRs 0001/0002 from the accepted decisions, declare the two runtime dependencies, and add the minimal validated settings/logging foundation. Preserve existing environment/toolchain conventions.
2. Implement shared contracts and protocol boundaries with contract tests, including period/Decimal/provenance invariants and version identifiers.
3. Implement byte retrieval and bounded retry/availability semantics with mocked unit tests; implement local file retrieval, immutable archive, event metadata, and hash-verified replay with filesystem tests.
4. Implement OMIE exact-revision/bounded discovery adapter and parser/calendar profiles. Add representative source/malformed fixtures and parser/calendar tests together; protect the current and legacy format boundary.
5. Complete retry/redaction/archive edge cases and offline network guard. Run mocked end-to-end ingestion/revision/replay integration across the real components.
6. Add the explicitly opted-in live smoke command and run it if the environment permits; record the actual result separately from deterministic tests. Resolve only concrete source details needed for implementation, without reopening the baseline.
7. Finish README, architecture links, ADR index, and the ingestion runbook; run final quality gates and the single acceptance checklist below. Review the complete diff and verify no out-of-scope work or raw dataset entered Git.

Stages may be split across prompts for reviewability. Verification of a stage's implementation is normal engineering work; it must not become another Phase 1 assessment gate.

## 10. Complete Phase 1 acceptance criteria

Reuse this checklist through final Phase 1 verification. Partial stages may leave entries pending; they must not create conflicting replacement criteria.

- [ ] ADRs 0001/0002 record the accepted source, market-period contract, execution/archive/provenance/replay, dependency, and test-isolation choices before corresponding implementation.
- [ ] One shared typed contract set lives in `contracts/`; common execution lives in `ingestion/`; OMIE-specific locator/parser/calendar rules live in `ingestion/omie/`. Future provider stubs remain untouched.
- [ ] Valid source requests support exact OMIE revisions and bounded latest-observed discovery. No hard-coded assumption that `.1` exists or that the index proves complete history.
- [ ] Anonymous public download mechanism works through an injectable synchronous client; local file retrieval and archive replay work offline.
- [ ] All external calls have explicit finite phase timeouts, bounded attempt/operation duration, size limits, and bounded discovery. Selected transient failures use at most three total attempts with exponential backoff; permanent failures do not retry.
- [ ] Source-unavailable/not-yet-published behavior is explicit, preserves context, and produces neither zero-record success nor retry/polling storms. Missing historical revisions and unknown listing coverage are not misrepresented.
- [ ] Raw archive preserves original body bytes unchanged under ignored `data/raw/` (or a documented external custom root), uses SHA-256 identity, and never replaces an archived payload or metadata event.
- [ ] Identical replay/acquisition reuses content; differing content, including same-filename republishing, is separately retained. Concurrent writes, corruption, partial writes, and metadata failures have tested controlled behavior.
- [ ] Retrieval provenance captures source/report/date, safe locator/filename, retrieval UTC time, status/attempts, byte length/hash/archive reference, and observed revision; parse provenance adds parser/schema versions and references the original raw acquisition.
- [ ] Offline replay verifies content hash, makes no network call, retains original acquisition history, and produces deterministic normalized values/identities for a fixed parser/schema version.
- [ ] Parser validates the complete selected grammar and day, emits explicit typed content errors, and never drops bad rows or returns partial days. Complete malformed payloads remain archived for diagnostics.
- [ ] Both PT and ES records are emitted with correct column order, finite signed Decimal prices in EUR/MWh, and exact supported precision; no float intermediates or nonnegative-price restriction.
- [ ] Normalized periods include delivery date, source period index, resolution, and UTC interval; no legacy hourly-only field or 24-period ceiling. Modern 96/92/100 and legacy 24/23/25 profiles, transition boundary, full-day coverage, and DST ambiguity are tested.
- [ ] Environment settings are minimal, documented, validated, and require no unrelated provider credentials; bad settings fail before I/O. No unnecessary runtime/test dependency is introduced.
- [ ] Structured logging identifies report/attempt/outcome/content/parser with useful safe fields. Secret-bearing URLs, headers, exceptions, configuration, and validation input are redacted in every tested path, including metadata.
- [ ] Small versioned fixture files/manifest are committed intentionally under `tests/data/omie/`; ignore rules permit them while excluding raw datasets and secrets. Synthetic/mutated fixtures are labelled.
- [ ] Unit, contract, and mocked integration tests cover every behavior in §8, including revision preservation, retry limits, unavailability, provenance, logging, malformed content, DST, and replay.
- [ ] Normal `pytest` succeeds with network disabled, uses no secrets/live source, and never invokes the live module. No meaningful test is weakened to make checks pass.
- [ ] Optional live module requires explicit `--live`, has a documented invocation/outcomes, uses no credentials for the verified route, and is excluded from pytest/pre-commit/automatic CI. A live run result or an explicit not-run/environment limitation is documented separately.
- [ ] README/architecture status, ADR index, and ingestion runbook describe actual implemented behavior, support limits, settings, raw paths, revision recovery, and replay.
- [ ] Final `ruff check .`, `ruff format --check .`, `mypy src`, `pytest`, and `git diff --check` pass in the intended Python 3.12 environment; complete diff/status reviewed.
- [ ] No Snowflake/dbt/ML/serving/dashboard/cloud/infrastructure implementation, other provider implementation, paid-resource action, unsolicited commit, or push is included.

## 11. Recommended first implementation slice

After this assessment is accepted, implement **the shared market-price and provenance contract foundation**: record ADRs 0001/0002, declare the agreed HTTPX/Pydantic runtime dependencies, then add the shared request, normalized interval-price, and retrieval/parse provenance models with focused contract/calendar tests. This is the smallest coherent basis for the complete pipeline: it fixes the meaning of source periods, immutable content identity, and traceability before retrieval/archive/parser code consumes them.

Include only the settings needed by those contracts if necessary; leave HTTP execution, file writes, OMIE parsing, and other packages for subsequent direct implementation slices. This sequencing is implementation against the accepted baseline, not permission for another readiness assessment.

Assessment-task delivery validation: run `git diff --check`, inspect `git status --short` and all untracked paths, and confirm this report is the only added/modified repository file. No implementation, dependency installation, commit, push, or paid-resource action is part of this task.

## Phase 1 Assessment Lock

> This assessment covers the complete Phase 1 scope. Once accepted, no additional Phase 1 readiness or architecture assessment is required between implementation stages. Subsequent work should proceed directly through implementation, testing, and verification against this report unless a genuine blocking contradiction is discovered.
