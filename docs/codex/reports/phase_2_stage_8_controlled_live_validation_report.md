# Phase 2 Stage 8 — Controlled live validation and replay

## 1. Executive verdict

**Phase 2 Stage 8 — PASS.** The targeted ESIOS continuation in §24 resolved
its required-product gap with a versioned provider-specific request, 288 valid
real samples and successful denied replay. All regression/quality gates pass.

**Original seven-request execution verdict: PASS WITH GAPS.** The following
paragraphs and §§2–23 retain the original execution history; §24 records the
separate authorized resolution.

The authorized seven logical data acquisitions completed safely: seven HTTP 200
responses, seven attempts, no retries, **159,742 attempted body bytes**, all
archived unchanged. Six products parsed successfully into **1,560 records**.
All seven archived acquisitions replayed with network/client/retriever and
credential access explicitly denied; this includes reproduction of ESIOS's
failed parse, which is not successful product validation.

**Remaining required-product gap: ESIOS 544 UTC coverage.** Its 301 ordered
five-minute samples extend through **2026-10-25T01:00:00Z**, although the exact
accepted request ends at **2026-10-25T00:00:00Z**. Twelve samples lie after that
inclusive upper bound. The accepted parser correctly returns
`content_failure/content_invalid` and zero records. No response was clipped,
no bound relaxed and no replacement request issued.

## 2. Baseline and authorization

Initial checkpoint: **main**, clean working tree and index, HEAD
`17d1e19630d5c353b22d3820091e19e24aaf51f2` —
`test: complete Phase 2 pre-live engineering audit`. The committed Stage 7 report
concludes **Phase 2 Stage 7 — PASS.** Local main remains intentionally ten commits
ahead of the locally recorded origin; no synchronization occurred.

The exact original prompt was saved before implementation/network access at
`docs/codex/prompts/phase_2/phase_2_stage_8_controlled_live_validation_replay.md`.
The original pre-network BLOCKED report is superseded by this actual execution.
On continuation, the operator explicitly authorized loading only the two selected
credentials from repository-local `.env`. The existing operator `.gitignore`
change is preserved; `.env` remains ignored, untracked and unchanged by this task.

Repository instructions, architecture/ADRs/runbooks, readiness, provider reports
including REN's revised acceptance and the accepted ICON-EU completion/model
selection, Stage 6/7 evidence, and actual adapters/query builders/parsers,
archive/runner/replay/credential and Stage 7 security code informed this work.
Source/model selection was not reopened. Stage 9 has not started.

## 3. Live safety plan and entry point

New explicit command: `python -m iberian_shakti.ingestion.phase2_live`.
It refuses without `--live` before credential/client/retriever construction.
`--replay-only` is an independent offline path. No live command was added to
pytest, pre-commit or CI.

All local preflight precedes HTTP construction: explicit external archive
validation, credential validation, all seven canonical queries, main-thread
POSIX deadline availability, empty destination and local hard-link/fsync checks.
Relative/default/repository/fixture/test/symlink archive destinations are refused.
A nonempty destination cannot be reused for another live run.

One synchronous loop calls the existing production provider factories and
`HttpRetriever` → `ingest_resolved` → `LocalRawArchive` → accepted parser →
immutable parse-event path. No provider retry policy, parser/profile semantics,
query wire format, contract, archive layout or dependency changed.

Readiness §Q supplies the finite request plan but no exact numeric delay;
its §M/provider context uses a conservative one-request-per-second ceiling.
Stage 8 chooses a fixed **1.1-second minimum between all HTTP attempt starts**,
including retries, across providers. Longer production backoff/Retry-After waits
remain binding. ENTSO-E 429 remains terminal for that logical acquisition.

## 4. Whole-run budgets

Hard ceilings: **8 logical requests**, **1 conditional metadata request**,
**24 HTTP attempts**, **32 MiB attempted response bodies**, **900 seconds**.
This command exposes only the required seven-product plan; it does not implement
an optional metadata endpoint or a product/date/model override.

The controller counts streamed raw body chunks from successes, non-200 errors,
interrupted responses and retries, not just archived successes. Error bodies are
drained boundedly without decoding/persisting their prose; a failed drain retains
the known status and cannot turn a terminal auth/ENTSO-E quota response into a
transport retry. A separate conservative **32 MiB inbound socket-read cap**
counts headers/framing as well, including bytes buffered before rejection.
Read sizes shrink before each socket read. Thus buffering/rejected bodies cannot
bypass the body cap. The manifest distinguishes actual streamed body bytes from
this conservative transport counter.

Shrinking socket timeouts plus a POSIX alarm bound the live acquisition/replay
phase, including DNS, parsing and filesystem work. Budget checks precede request
admission, waits and reads. Safety/integrity failures stop further network access.
Default provider retry budgets remain 3 attempts and 10/30/93-second phase/attempt/
operation limits. No limit was increased or exhausted in this run.

## 5. Exact request plan and results

Historical source day: **2026-10-24**. ESIOS/ENTSO-E/weather historical query window:
`[2026-10-24T00:00Z, 2026-10-25T00:00Z)`; ESIOS permits an inclusive end sample.
REN's accepted Lisbon source day has physical UTC bounds
`[2026-10-23T23:00Z, 2026-10-24T23:00Z)`.

Actual execution clock selected **2026-11-04 UTC** for ICON-EU, without clock
manipulation. Both weather requests used only **PT.lisbon (38.72, -9.14)**,
all three selected variables, explicit temperature/wind units, GMT and Unix time.
Forecast explicitly used `models=icon_eu`; history explicitly used `models=era5`.
No OMIE, IFS, other site, product, date, account or catalogue request occurred.

| Provider/product | Target date | Logical # | Attempts | HTTP outcome | Bytes | Raw SHA-256 | Normalized records | Parse | Replay | Deviation |
| --- | --- | ---: | ---: | --- | ---: | --- | ---: | --- | --- | --- |
| REN production breakdown | 2026-10-24 | 1 | 1 | HTTP 200 | 28,420 | `65145ea67ba42da8e30a54bff8d262eb11acf18998d8dca4393983134add30db` | 1,056 | PASS | PASS | None blocking |
| ESIOS 544 | 2026-10-24 | 2 | 1 | HTTP 200 | 75,197 | `4b356d9e2a6f0d8c96f762c7f214834eff41e5c9f8c219839a1a81d2e9e3c926` | 0 | content_invalid | Equal failed parse | 12 samples beyond requested end |
| ENTSO-E ES load | 2026-10-24 | 3 | 1 | HTTP 200 | 12,945 | `a7bac5cb29dbf3e53008e5243cd6ed9a16dddbe56b807d90d2b518a35826173f` | 96 | PASS | PASS | None blocking |
| ENTSO-E PT renewables | 2026-10-24 | 4 | 1 | HTTP 200 | 11,895 | `a6cf213879c6622783811cb941be366b2a6d51015b3801aca1b6c61d3661faaf` | 72 | PASS | PASS | None blocking |
| ENTSO-E ES renewables | 2026-10-24 | 5 | 1 | HTTP 200 | 29,333 | `55e0238a1da82640fc73445d26f7e63c18e59360f98d50e578f793e37daf698b` | 192 | PASS | PASS | None blocking |
| ERA5, PT.lisbon | 2026-10-24 | 6 | 1 | HTTP 200 | 975 | `625cbf92d592967ce609c4c3dd8dbbb07263d8858a7534d6fd7fdd5455878257` | 72 | PASS | PASS | None blocking |
| ICON-EU, PT.lisbon | 2026-11-04 | 7 | 1 | HTTP 200 | 977 | `8bdad6043e7284eee80c8cfe2df24548f9744853cd12a394e437b3d103c33fd9` | 72 | PASS | PASS | None blocking |

## 6. Credential preflight and diagnostics

The agent's inherited environment initially lacked both names despite the
operator's terminal exports. The operator then authorized repository-local
`.env` access. Only assignments for `ESIOS_API_TOKEN` and `ENTSOE_API_TOKEN`
were parsed locally into the execution subprocess environment; no shell code,
other setting, credential store or unrelated key was loaded. Values were not
printed, logged, copied to another file, persisted or semantically inspected.
Both passed the existing application loader's local validation before any HTTP
operation. REN and Open-Meteo requests remained anonymous.

Normal required ESIOS and all three ENTSO-E responses returned HTTP 200, providing
successful real authentication/authorization evidence for those requests. There
was no separate credential probe, invalid-key test or alternate auth format.

The managed diagnostic boundary captured allowlisted logs in memory and checked
for both active credentials before output. The safe manifest was checked before
each publication. No private request headers, credential-bearing URLs, raw
provider bodies or unchecked provider error prose were published in diagnostics
or this report. The original Stage 7 encoded active-credential guard and OMIE
independent 4 MiB direct-parser/replay cap remain unchanged.

A final local active-credential exclusion scan passed across every live archive
file (including payloads/sidecars/manifest), the saved prompt/report, runbook and
new code/tests, using the existing literal/encoded echo guard. Only a static
pass/fail result was printed; no credential value or matching content was shown.

## 7. REN result — PASS

HTTP 200; **28,420 original bytes**, profile/parser **0.2.0**; **1,056 records**.
The strict chart validated all eleven selected concepts: Consumption, Hydro,
Solar, Import, Export, Wind, Natural Gas, Other Thermal, Biomass, Coal and Wave.
All four ancillary arrays were present and validated: Consumption + Storage,
Pumping, Consumption of Batteries and Battery Injection. Axes returned Hour/MW;
96 exact ordered quarter-hour labels span 00:00–23:45 and match the accepted
ordinary Lisbon source-day sequence. Every selected native Decimal MW value and
its interval support survived replay.

Returned root metadata contains chart axes/series, not an authoritative timezone,
label-placement, fold or MW-statistic definition. Compatibility with
`provisional_empirical`, Europe/Lisbon, `interval_start`, `provider_period_value`
is confirmed for this response; those assumptions are not promoted to new
provider-authoritative claims. No mean/instant reinterpretation, MW-to-MWh
conversion or ADR 0006 change occurred.

## 8. ESIOS result — required validation GAP

HTTP 200; **75,197 original bytes**. Indicator 544 returned the exact name
**Demanda prevista Peninsular**, magnitude **Potencia (20)**, cadence
**Cinco minutos (219)** and geography **Península (8741)**. Numeric IDs here are
observed metadata, not new guessed catalogue mappings. There is no explicit
`unit` field; MW remains the accepted documented product unit, not a newly
observed native unit string. The response carries enough metadata to assess
name/magnitude/geography/sampling against the pinned product; an extra metadata
request would not resolve the coverage violation and was not made.

Local offline validation of the entire retained body established:

- 301 values, strictly increasing UTC timestamps, all successive deltas exactly
  300 seconds; no gaps or duplicates in that returned sequence.
- All supplied local timestamps agree with explicit UTC and Europe/Madrid offset
  rules, including the transition at the returned tail.
- First UTC sample 2026-10-24T00:00:00Z; last 2026-10-25T01:00:00Z.
- Zero samples before the requested start; **12 after the accepted requested end**.
- `values_updated_at` validates as 2026-10-25T22:53:55Z and remains indicator
  snapshot update context, never per-value forecast issue time.

The accepted request encodes explicit UTC endpoints through the existing URL
builder. This observation does not establish why the provider returned an extra
hour; DST/end-date handling is a possible explanation, not a proven cause.
The parser's strict requested-window rule is deliberate, so no local defect
warranting a safe correction was demonstrated. Broadening the window, discarding
12 rows, changing dates or accepting a different interpretation would violate
this task. The failed parse and its zero-record outcome are preserved and replay
equally. **ESIOS is not counted as successful live product validation.**

## 9. ENTSO-E ES actual load — PASS

HTTP 200; **12,945 bytes**, **96 records**, full requested UTC day with one
TimeSeries `1`, type/process **A65/A16**, business **A04**, aggregation **A01**,
ES outgoing bidding-zone EIC **10YES-REE------0**, coding scheme A01,
**MAW → MW**, **PT15M**, curve **A03**. Its single Period spans exactly the
requested midnight-to-midnight day; 96 ordered points have positions 1–96.
No missing support or technology fabrication. Parsed/replayed as actual load,
interval-supported provider-period values.

## 10. ENTSO-E PT day-ahead renewables — PASS

HTTP 200; **11,895 bytes**, **72 records**. Type/process **A69/A01**,
aggregation **A08**, PT incoming bidding-zone EIC **10YPT-REN------W** with A01
coding, MAW, **PT60M**, **A03**. All three technologies were actually present:

| TimeSeries | PSR | Business | Encoded points | Last position | Expanded hourly records |
| --- | --- | --- | ---: | ---: | ---: |
| 1 | B16 solar | A94 | 16 | 21 | 24 |
| 2 | B18 offshore wind | A93 | 23 | 24 | 24 |
| 3 | B19 onshore wind | A93 | 24 | 24 | 24 |

Each has one Period covering the full requested day, starting at position 1.
A03 constant-block decoding explains omitted intermediate positions and the last
solar block through Period end; it is not gap filling. No technologies are absent
and no gaps exist in the decoded supports. Independent forecast series and
native identities survive replay; none was aggregated.

## 11. ENTSO-E ES day-ahead renewables — PASS

HTTP 200; **29,333 bytes**, **192 records**. Type/process **A69/A01**, aggregation
**A08**, ES incoming bidding-zone EIC **10YES-REE------0**, A01 coding,
MAW, **PT15M**, **A03**. TimeSeries `1` is B16/A94 solar (94 encoded points,
positions 1–96); TimeSeries `2` is B19/A93 onshore wind (96 encoded points,
positions 1–96). Each single Period covers the exact requested UTC day and
expands to 96 records under accepted A03 semantics. No decoded support gaps.
**B18 offshore wind is absent** and stays absent; no zero series was invented.

All three ENTSO-E documents use the supported namespace/version
`urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0` and root
`GL_MarketDocument`. Document/series identities and Period bounds, business,
aggregation, domain, PSR, units, resolution, curve and ordered positions passed
strict existing validation. `createdDateTime` was present at
15:41:26Z / 15:41:32Z / 15:41:39Z respectively on 2026-11-03. It remains
request/document creation context in raw XML, not an inferred forecast issue,
publication, update or model-run time. No acknowledgement occurred, and none
was deliberately provoked.

## 12. ERA5 historical/reanalysis — PASS

HTTP 200; **975 bytes**, **24 exact UTC hourly timestamps**, **72 records**;
kind=reanalysis, explicit canonical/request model `era5`. Returned grid is
**38.75, -9.25**, elevation **64.0 m**; requested coordinates remain
38.72, -9.14. Returned timezone/abbreviation **GMT**, UTC offset **0**, time
unit **unixtime**, temperature **°C**, wind **m/s**, shortwave **W/m²**.
Every selected array has 24 entries and strict daily coverage passes.
No explicit response model/run field is supplied; identity is established by the
pinned explicit query under the accepted Stage 5 policy, not an invented echo.

Temperature and wind are instants; shortwave is preceding-hour mean `[t-1h,t)`,
including midnight support in the previous day. Original grid/units/values/support
and raw/retrieval linkage replay equally. ERA5 is not a historical forecast vintage.

## 13. ICON-EU next-day forecast — PASS

HTTP 200; **977 bytes**, target **2026-11-04 UTC**, **24 exact hourly timestamps**,
**72 records**, explicit query `models=icon_eu`; kind=forecast. Returned grid is
**38.75, -9.125**, elevation **64.0 m**, independently retained from the logical
site. Same validated GMT/zero offset/Unix and three measurement units as ERA5;
all arrays have 24 entries. Temperature/10 m wind remain instants; shortwave
remains preceding-hour mean. No model/run metadata echo was supplied, so source
issue/model-run/publication times remain null.

The returned grid is recorded as observed, not compared with synthetic or
pre-transition coordinates. The announced post-30-November transition remains
provider context, not an observed event or model-identity change here. No configured
site coordinate changed and no alternative model was requested. This snapshot
establishes forecast availability at this acquisition, not before a past auction.

## 14. Provider deviations and incompatibilities

Only the ESIOS returned-window overrun blocks a required product. Unit absence
and missing weather model/run echoes are reported conservatively under existing
profiles. All seven responses had no Content-Encoding header and were read as
original identity representation bytes; no decoding policy changed. REN used
text/plain for valid JSON, already supported by byte-based parsing. PT offshore
wind was returned, ES offshore wind was absent, and differing native resolutions
were retained. There was no provider outage, no-data, auth rejection, natural
HTTP error, quota response, compression incompatibility or fallback attempt.

## 15. Real archive and provenance

Exact dedicated archive: **`/tmp/iberian-shakti-phase2-stage8-live-20261103`**.
Run manifest: `/tmp/iberian-shakti-phase2-stage8-live-20261103/stage8-manifest.json`.
Run ID: **`682c7b5a-ed3f-4e7e-b1ed-de164a63a46d`**.

`LocalRawArchive` retained **7 immutable payloads**, **7 retrieval events** and
**21 parse events**: initial parsing, automatic denied replay, and a separate
replay-only proof. ESIOS's failed events remain failures. Each raw hash/length,
archive path, original acquisition completion time, canonical request and UUID
linkage was loaded and verified locally. Full safe query descriptions are in
the manifest and retrieval events. No real body entered Git or test fixtures.
The shared retriever checked declared Content-Length whenever present; archived
byte lengths and SHA-256 values were independently reloaded and checked.

| Product | Canonical query SHA-256 | Retrieval UUID | Original parse UUID | Latest replay parse UUID |
| --- | --- | --- | --- | --- |
| REN production breakdown | `87bd21fac28661bc9817e2c9d3dcb82edd515cc49c071726b32d6dfd8ab690ee` | `f6150c10-6c67-4bde-a8c7-52f816a55ae2` | `615bc6de-4ce2-4518-a6a8-27abd3370acb` | `6f058031-57d4-497c-91b3-5fd9fe4e9443` |
| ESIOS 544 | `6b01d414cdc160d2445f33015ce6d25ff7751b07215a8cd73c20f2279e0b92bd` | `a51706e2-7380-47d9-afb2-2f058e3799c7` | `746bd779-023e-474d-ab5d-5e1898c6cf34` | `65171749-0097-4272-92ab-9b71a222c50e` |
| ENTSO-E ES load | `c70fe23eadfabe433d6dd2527abe09e00bb232cb27e2cc06231323d16ebbcade` | `a6a62a20-d92e-406c-90b9-66298fb7cf28` | `c8e920d8-429d-445c-a8a9-ed736f3b315d` | `ea4c5124-c261-4267-b598-a0133e611d69` |
| ENTSO-E PT renewables | `53e352bee2709db2bcbbe08f9390886d6e1497e482d9173dfae8f4f7bff85c8e` | `65df9e03-8bba-401f-a68f-a50b7bb7b1af` | `419d6088-d6be-4712-b782-bf18c2560c5e` | `4f0066c0-0d36-4256-a693-f2de845f7e9e` |
| ENTSO-E ES renewables | `2ff2b9fe0a3c402c36bc6fa8a0d58c9d8c656cae64096e648130ded67a8b399e` | `2c3cfcc0-7f5f-4206-9132-29bf0fdf2409` | `35928c3e-971c-4378-a22c-fa965f605903` | `ae5f0d60-a17d-466b-a619-234c8a1dc2cf` |
| ERA5, PT.lisbon | `f98b12d8a69f22ccc41648b2900f9babe488689814c4dadf78541c074d79a033` | `1fdfb344-29f6-48c7-9c96-69db27449cfd` | `5338c381-7a42-4311-b794-49c34a4c5784` | `05343703-1881-45e1-aa5f-affcf62c9e0a` |
| ICON-EU, PT.lisbon | `2288ee62f40e99d149eecd30a33f1895ab62d4f1be674a9ff10f0036edbb8a69` | `2d4f4184-9d7b-4b1b-a4c7-42fb98feacb0` | `41ef5ad6-c3c2-43e9-9576-db5e6cef79fe` | `8dfc228e-4d57-455f-a842-390a8a03d128` |

Raw references relative to the archive root:

- ren: `ren/ElectricityProductionBreakdownDaily.en-US.v0.2.0/2026-10-24/sha256/65145ea67ba42da8e30a54bff8d262eb11acf18998d8dca4393983134add30db/payload.bin`
- esios: `esios/indicator544.v0.1.0/2026-10-24/sha256/4b356d9e2a6f0d8c96f762c7f214834eff41e5c9f8c219839a1a81d2e9e3c926/payload.bin`
- entsoe_load: `entsoe/actual_load.A65.A16.v0.1.0/2026-10-24/sha256/a7bac5cb29dbf3e53008e5243cd6ed9a16dddbe56b807d90d2b518a35826173f/payload.bin`
- entsoe_pt: `entsoe/wind_solar_forecast.A69.A01.v0.1.0/2026-10-24/sha256/a6cf213879c6622783811cb941be366b2a6d51015b3801aca1b6c61d3661faaf/payload.bin`
- entsoe_es: `entsoe/wind_solar_forecast.A69.A01.v0.1.0/2026-10-24/sha256/55e0238a1da82640fc73445d26f7e63c18e59360f98d50e578f793e37daf698b/payload.bin`
- era5: `open_meteo/historical.era5.v0.1.0/2026-10-24/sha256/625cbf92d592967ce609c4c3dd8dbbb07263d8858a7534d6fd7fdd5455878257/payload.bin`
- icon_eu: `open_meteo/forecast.icon_eu.v0.1.0/2026-11-04/sha256/8bdad6043e7284eee80c8cfe2df24548f9744853cd12a394e437b3d103c33fd9/payload.bin`

## 16. Network-denied replay

The automatic replay ran after all seven acquisitions. A separate
`python -m iberian_shakti.ingestion.phase2_live --replay-only --archive-root ...`
also exited **0**, without loading `.env` or any credential. Within replay,
HTTPX clients/transports, every provider retriever factory, HttpRetriever
construction/retrieval, selected-provider credential loader seams, socket
construction and DNS helpers explicitly raise if called. The process environment
is temporarily empty. Synthetic tests directly exercise these denials.

All seven archive payloads/hash and original retrieval linkages load; all six
successful products reproduce complete record-content digests covering values,
units, support/valid times, kind, requested/returned geography, native identities,
product/model and retrieval identity. Full canonical query identity and raw/parse
provenance digests also match. Only the new parse UUID/time is excluded.
ESIOS independently reproduces its zero-record content failure, not successful
forecast data. Original retrieval/parse events remain retained as separate
immutable files; no new retrieval or body is created by replay.

## 17. Request, attempt, byte and time accounting

The following counters come directly from the controller manifest, not manually
inferred transport logs:

| Measure | Result |
| --- | ---: |
| Required logical requests planned | 7 |
| Logical requests executed | 7 |
| Successful required product parses | 6 |
| Optional ESIOS metadata requests used | 0 |
| HTTP attempts | 7 |
| Retries, every provider | 0 |
| Attempted raw response-body bytes | 159,742 |
| Archived original response-body bytes | 159,742 |
| Conservative inbound transport bytes | 163,127 |
| Acquisition + automatic replay budget duration | 24.102013 s |
| Recorded start/end UTC span, including local setup | 24.121818 s |
| Unexecuted planned required requests | 0 |
| Safety stop / exhausted budget | None |
| Remaining logical/attempt admission slots | 1 / 17 |
| Remaining body/inbound byte budgets | 33,394,690 / 33,391,305 |
| Remaining timed budget | 875.897972 s |

Start UTC: **2026-11-03T15:41:16.891241+00:00**.
End UTC: **2026-11-03T15:41:41.013059+00:00**.
Unused admission capacity is not permission for additional requests. The logical
plan is complete; ESIOS's outstanding criterion is not hidden as an unexecuted call.
All seven attempt/error-body accounting checks were consistent; no error-body
read failed. The command returned exit **3** for six successful parses and one
live gap, rather than claiming seven-product PASS.

## 18. Live evidence, local defects and corrections

No accepted provider parser/contract defect was demonstrated and no provider
semantics/version was changed. ESIOS's deliberate coverage rejection is retained.
A permanent **generated synthetic 301-sample regression** proves atomic rejection
of the one-hour overrun, original-byte preservation and equal failed replay.
It uses synthetic values/native identity and copies no live payload into fixtures.

New controller implementation was tested before live use. Pre-live engineering
checks also ensure partial/error/retry bytes count, terminal statuses survive
error-body read failures, and limits cannot be increased. Replay additionally
checks manifest-to-original canonical query identity. There was no refetch to
validate a parser fix, no dropped row and no semantic expansion.

## 19. Regression validation

Python **3.12.9**. All tests use synthetic transports/fixtures with the default
collection-time network denial unchanged. No test reads the real archive or
credentials. No old assertion, fixture, source parser or security control changed.

| Executed gate | Result |
| --- | --- |
| New Stage 8 offline suite | **49 passed in 6.13 s** |
| Pre-live Stage 8 + Stage 7 audit selection | **162 passed in 6.38 s** (before the final two added Stage 8 regressions) |
| Stage 7 + guard/private HTTP/retry/transport/archive/XML security selection | **457 passed in 6.61 s** |
| `python -m pytest tests/integration/stage6 -q` | **119 passed in 40.65 s** |
| Provider-focused unit/integration selection | **1,164 passed in 16.45 s** |
| `python -m pytest` | **2,295 passed in 69.00 s**; zero failures/skips/warnings |
| `ruff check .` | **PASS** |
| `ruff format --check .` | **PASS**, 164 files formatted |
| `mypy src` | **PASS**, 61 source files |
| `pre-commit run --all-files` | **PASS**, all eight hooks |
| Explicit pre-commit on unstaged/untracked Stage 8 paths | **PASS**, all six applicable hooks; YAML/TOML inapplicable |
| `git diff --check`, new-file whitespace and final diff review | **PASS**; tracked diff and complete new source/tests/docs reviewed; index unchanged |

Provider selection matches Stage 7: OMIE/REN/ESIOS/ENTSO-E/weather unit suites plus
Stage 3/4/5 OMIE and REN/ESIOS/ENTSO-E/Open-Meteo integration flows. The security
selection includes the 115-case Stage 7 audit plus offline guard, private requests,
HTTP, Stage 5 HTTP, transport, archive, Stage 5 archive and XML security.

## 20. Remaining live / Stage 9 boundary

Resolve ESIOS 544's returned coverage semantics/provider behavior before its live
product criterion can PASS. Further live requests, changed dates/windows or new
profile semantics are not authorized by this report. Preserve and reuse this
archived response for any later reviewed interpretation.

REN's authoritative statistic/label/fold refinements, unknown forecast run/issue
metadata, historical availability/vintages/cutoff and licensing/operational
clearance are not solved by these snapshots. They are retained limitations,
not invented blockers for the six accepted live products. Stage 9 final Phase 2
acceptance/reconciliation remains separately authorized and has not started.
No Snowflake, dbt, features, training, model registry, inference, API/dashboard,
scheduler, deployment, monitoring or cloud component was implemented.

## 21. Files changed

- `src/iberian_shakti/ingestion/phase2_live.py`: fixed explicit operator plan,
  preflight, safe manifest, production composition and denied replay.
- `src/iberian_shakti/ingestion/_live_budget.py`: whole-run counters, admission,
  bounded socket reads, pacing, deadline and counted production transport.
- `tests/integration/test_phase2_stage8_live.py`: 49 synthetic controller,
  accounting, boundary, security, preservation and replay regressions.
- `docs/runbooks/ingestion.md`: narrow explicit Stage 8 operation/replay guidance.
- Saved original Stage 8 prompt and this updated report.
- `.gitignore`: pre-existing operator addition of `.env`, preserved unchanged.

No dependency, existing fixture/parser/security module, CI or architecture change.

## 22. Final Git status

```text
 M .gitignore
 M docs/runbooks/ingestion.md
?? docs/codex/prompts/phase_2/phase_2_stage_8_controlled_live_validation_replay.md
?? docs/codex/reports/phase_2_stage_8_controlled_live_validation_report.md
?? src/iberian_shakti/ingestion/_live_budget.py
?? src/iberian_shakti/ingestion/phase2_live.py
?? tests/integration/test_phase2_stage8_live.py
```

All changes remain unstaged; the index is unchanged. No new branch, staging,
commit, push, fetch, pull, rebase, reset, restore or stash occurred. No unauthorized
provider request, quota/auth probing, date search, model fallback, bulk download,
paid/cloud action or Stage 9 work occurred. `.env` and live bytes remain outside Git.

## 23. Final verdict

Phase 2 Stage 8 — PASS WITH GAPS.

Exact required-product gap: **ESIOS 544** returned twelve samples beyond the
requested UTC endpoint. Its immutable real response and failed parse/replay chain
are retained, but normalization and successful product replay remain unsatisfied.
REN, all three independent ENTSO-E paths, ERA5 and ICON-EU passed live validation
and denied replay. Phase 2 is not closed; Stage 9 has not started or been authorized.


## 24. Targeted ESIOS 544 semantics-resolution continuation

This section preserves §§1–23 as the original PASS WITH GAPS execution history.
Continuation baseline remains **17d1e19**, existing **main**, with all original
unstaged Stage 8 files and `.gitignore` preserved. The exact continuation prompt
was saved at
[phase_2_stage_8_esios_544_boundary_semantics_resolution.md](../prompts/phase_2/phase_2_stage_8_esios_544_boundary_semantics_resolution.md).
No Stage 9 or final Phase 2 closure is authorized.

### Offline evidence and original contract

All analysis preceded the additional data request. No credential was needed.
Original query identity:
`6b01d414cdc160d2445f33015ce6d25ff7751b07215a8cd73c20f2279e0b92bd`.
Its safe wire parameters were exactly:
`start_date=2026-10-24T00:00:00+00:00`,
`end_date=2026-10-25T00:00:00+00:00`, encoded using `urlencode`
(including `%2B00%3A00`). No aggregation, timezone or geographic filter was sent.
Shared QueryWindow is half-open; Stage 3 profile/parser 0.1.0 explicitly retained
an inclusive end sample as an unresolved provider convention. Stage 7 §9 audited
that same policy, without settling provider endpoint behavior.

The original 75,197-byte payload was read from the archive, never refetched.
Its SHA-256 remains
`4b356d9e2a6f0d8c96f762c7f214834eff41e5c9f8c219839a1a81d2e9e3c926`.
All 301 UTC/local pairs agree as instants and Madrid offsets. UTC cadence is
uniformly 300 seconds, with zero duplicates/gaps or samples before start.
There is **one sample exactly at end plus twelve strictly after end**: thirteen
samples outside a strict half-open window. The old parser's twelve-later-sample
failure was correct under its historical inclusive endpoint allowance.

A full timestamp-only table (zero-based sequence position, UTC, provider local,
offset, fold and seconds relative to end) is retained locally at
`/tmp/iberian-shakti-esios544-boundary-analysis-20261103/original-timestamps.json`.
Representative rows:

| Position | UTC | Provider Madrid time | Fold | Seconds from logical end |
| ---: | --- | --- | ---: | ---: |
| 276 | 2026-10-24 23:00 | 2026-10-25 01:00 +02:00 | 0 | -3600 |
| 287 | 2026-10-24 23:55 | 2026-10-25 01:55 +02:00 | 0 | -300 |
| 288 | 2026-10-25 00:00 | 2026-10-25 02:00 +02:00 | 0 | 0 |
| 289 | 2026-10-25 00:05 | 2026-10-25 02:05 +02:00 | 0 | 300 |
| 299 | 2026-10-25 00:55 | 2026-10-25 02:55 +02:00 | 0 | 3300 |
| 300 | 2026-10-25 01:00 | 2026-10-25 02:00 +01:00 | 1 | 3600 |

The twelve later samples are eleven first-fold 02:05–02:55 samples and one
second-fold 02:00 sample. They are **not** twelve samples of a complete second
02:00–02:55 hour. The last returned wall-clock label equals the requested
endpoint's Madrid label in the later fold. This fits an inclusive endpoint
resolved to the later fold; it does not establish the provider's internal
algorithm or prove that all filtering uses local wall time.

### Official documentation versus inference

Inspected the official
[unaggregated range-filter documentation](https://api.esios.ree.es/doc/indicator/getting_a_specific_indicator_filtering_values_by_a_date_range.html),
[five-minute grouping example](https://api.esios.ree.es/doc/indicator/getting_a_specific_indicator_filtering_values_by_a_date_range_grouped_by_five_minutes_intervals.html)
and [official API information page](https://www.esios.ree.es/es/pagina/api).
These describe ISO-8601 start/end filtering. No explicit inclusive/exclusive,
UTC-versus-local comparison or DST-fold policy was found. Illustrative response
local endpoints resemble inclusive selection, but their UTC timestamps do not
consistently honor the example UTC request bounds; the site calls the requests
examples. They cannot prove UTC boundary semantics. Grouping was not requested
in our acquisition; native five-minute cadence comes from the real payload.

The precise candidate hypothesis was: use the last desired native timestamp as
an inclusive provider end filter. Subtract 300 elapsed UTC seconds, retaining
the logical start/end. For this window that selects 23:55 UTC / Madrid 01:55+02,
which is unambiguous, instead of the ambiguous 02:00 endpoint. Inclusive behavior
and fold selection remain empirical hypotheses until targeted confirmation.

Deterministic ordinary/autumn/spring tests step in UTC. Ordinary boundaries
remain unambiguous; autumn interior folds retain both offsets; spring crosses
from 01:55+01 to 03:00+02 without inventing a 02:xx local sample. The product's
24 elapsed UTC hours still contain 288 native timestamps in each such test,
independent of local civil-day duration. Other tested durations are not forced
to 288. These tests establish our transformation and validation policy, not
unobserved live-provider results for the synthetic dates.

### Candidate implementation and version decision

[ADR 0008](../../adr/0008-esios-bounded-five-minute-request.md) was recorded before
implementation, conditional on controlled confirmation. `BoundedEsiosAdapter`
and `BoundedEsiosParser` use explicit profile/parser **0.2.0**, report
`indicator544.v0.2.0`. The original adapter/parser and default request constructor
remain 0.1.0 for historical reproduction. The new path accepts only five-minute
grid-aligned windows and conservatively refuses ambiguous Madrid wire boundaries
before acquisition; it does not guess unsupported fold policy.

This is not silently classified as a wire-only patch: enforcing exclusive
response support changes the accepted Stage 3 inclusive-end meaning. Therefore
the report/profile/parser are versioned. The exact logical QueryWindow, indicator,
geography and measurements are unchanged, while the explicit version produces
new canonical query identity
`346e02f84124188197200349025b27c6e64124f433f34738d91fbb986c7c4f5e`.
Shared QueryWindow/serialization, other providers, values_updated_at, units,
metadata checks and provenance contracts are unchanged. Every response value is
validated; any sample at/after end or before start causes atomic failure.
There is no selection, clipping, widening, sorting or inferred forecast issuance.

The existing Stage 8 controller has a separate fixed `--esios-boundary-only`
selection and a new external archive, preserving its seven-product original plan.
This mode loads only ESIOS authentication and admits one logical request,
three total attempts, 6 MiB total body/inbound budget and 120 seconds overall;
the existing 2 MiB response cap, retry/deadline/pacing/credential controls remain.
Replay reconstructs the versioned local parser under the existing explicit
network/client/retriever/credential denials and empty process environment.

The original acquisition was also replayed offline under its original query and
parser. It reproduced content_failure/content_invalid with zero records and
identical content/provenance digests. New failed parse event
`3a7abc98-da01-45d4-aa72-3287dce3f777` was appended; no old event or manifest was
modified. Pre-continuation file hashes were recorded for preservation checks.


### Targeted real request and independent timestamp validation

Offline analysis, versioned implementation, **186 focused ESIOS/Stage 8 tests**,
Ruff/format/mypy and **457 Stage 7/security cases** passed before the single
additional ESIOS request. The request was necessary: neither the retained body
nor the documentation alone establishes whether the corrected range is honored.
No exploratory call, authentication probe or second diagnostic request occurred.

The sandbox required network execution approval; the approved command used only
`ESIOS_API_TOKEN`, loading only that selected assignment from the already
operator-authorized `.env` mechanism when absent from the process environment.
No shell sourcing, ENTSO-E credential read, credential inspection/output/persistence,
.env modification or separate authentication request occurred.

| Evidence | Targeted result |
| --- | --- |
| Logical UTC window | [2026-10-24T00:00:00Z, 2026-10-25T00:00:00Z) |
| Provider-wire start_date | `2026-10-24T00:00:00+00:00` |
| Provider-wire end_date | `2026-10-24T23:55:00+00:00` |
| Profile/parser/report | 0.2.0 / 0.2.0 / indicator544.v0.2.0 |
| Run UUID | `e94f2e96-7734-4974-9910-23be24cbd906` |
| Started / ended UTC | 2026-11-03T20:07:17.003809Z / 20:07:17.635342Z |
| Logical requests / HTTP attempts / retries | **1 / 1 / 0** |
| HTTP status | **200** |
| Original body bytes / attempted body bytes | **71,973 / 71,973** |
| Conservative inbound transport bytes | **73,312** |
| Body SHA-256 | `476aecfc4b13b6ada038aabbd6cfce792d2c1804d62a1b87b08b96eb6f3de7ae` |
| Retrieval UUID | `9ebff94f-5955-44e9-bbfc-88306fdd713d` |
| Acquisition parse UUID | `b54bc228-6072-49aa-8b17-8263d06c0824` |
| Automatic denied replay parse UUID | `90a20de9-54dc-4cb0-a5d1-3cb5d9614652` |
| Returned samples / normalized records | **288 / 288** |
| First / last UTC | **2026-10-24T00:00:00Z / 2026-10-24T23:55:00Z** |
| Cadence / duplicates / gaps | **300 seconds / 0 / 0** |
| Before start / at-or-after end | **0 / 0** |
| UTC/local/Europe-Madrid offset conflicts | **0** |
| Parse / automatic denied replay | **success / equal** |
| Stop / safety-budget exhaustion | **None / None** |
| Additional metadata/auth/quota/other-provider calls | **0** |

Archive root:
`/tmp/iberian-shakti-phase2-stage8-esios-boundary-live-20261103`.
Raw reference:
`esios/indicator544.v0.2.0/2026-10-24/sha256/476aecfc4b13b6ada038aabbd6cfce792d2c1804d62a1b87b08b96eb6f3de7ae/payload.bin`.
The separate root uses the existing immutable archive/runner and manifest; it
neither replaces the original body nor rewrites its manifest/history.

All targeted local timestamps have offset +02:00 and fold 0, ranging from
2026-10-24 02:00+02 to 2026-10-25 01:55+02. This is correct: the strict target
window excludes the ambiguous 02:00 hour entirely, so a fallback inside this
corrected response would be conflicting evidence. The retained original response
still supplies the observed +02 to +01 transition; synthetic crossing tests
retain both folds and the spring jump without fabricating new live observations.

Metadata again confirms indicator **544**, **Demanda prevista Peninsular**,
**Potencia (20)**, **Cinco minutos (219)** and **Península (8741)**. There is
still no explicit native unit field; the pinned MW profile is unchanged.
`values_updated_at` remains indicator update context, never forecast issue time.
No measurement values were needed for timestamp analysis; the parser and replay
retain and compare every normalized Decimal value and business/provenance field.

### Root-cause classification and limits

**A. Request-semantics defect resolved.** For this controlled product/window,
passing the logical exclusive end directly is not a safe provider representation.
Using the last desired native sample as end filter yields exactly the requested
half-open coverage without accepting or removing any outside value. The real
result empirically supports the inclusive-last-sample request convention.

The exact original one-hour expansion remains consistent with later-fold
handling of the ambiguous endpoint. Neither two acquisitions nor the official
examples prove the provider's internal timezone/fold algorithm. No claim that
ESIOS universally uses local time is made. Ambiguous provider-wire endpoints
remain deliberately unsupported in 0.2.0, pending clarification; ordinary/spring
provider behavior is covered by deterministic policy tests, not additional live
calls. Returned gaps remain visible and are not filled; this particular live
24-hour result was independently checked for full coverage before acceptance.

The parser was not relaxed to accept the original overrun. The explicit version
only tightens support to half-open and separates the corrected request contract
from Stage 3 history. Classification B (reinterpret old raw data) was not used;
no filtering, clipping, logical widening or semantic relaxation was introduced.

### Denied replay and preservation

Automatic replay matched normalized business-content digest
`68f40a71c1eeaf1f30ea0fc8e010bba611aae0aa2399acf05338c2df84547345`
and parse-provenance digest
`e95a106e45e872ee00bc55e955df9d1b8b9ed444af31f250197617bdacfb07e9`.
The equality includes the canonical query, all normalized record fields except
the new parse UUID, raw hash/reference and original retrieval linkage; parse time
and parse UUID are the only parse-event exclusions. The explicit replay-only
command also exited **0**, without loading .env or any credential, constructing
clients/retrievers or enabling network. It appended another immutable parse
event; there was no acquisition or body publication. Both success and failure
replay paths are covered by the new synthetic tests.

All **36 pre-continuation archive files**, including the original manifest,
payloads and retrieval/parse/replay events for every provider, matched their
recorded SHA-256 hashes. Original ESIOS retrieval
`a51706e2-7380-47d9-afb2-2f058e3799c7`, failed parse
`746bd779-023e-474d-ab5d-5e1898c6cf34` and failed replay events remain unchanged.
The additional old-body replay only appended the failed event noted above.
REN, the three ENTSO-E paths, ERA5 and ICON-EU retain their accepted results;
none was refetched or reopened. Original body hashes are not fixture copies.

### Permanent regressions and files

New `tests/integration/test_esios_boundary_semantics.py`: **25** synthetic cases.
They cover ordinary/target-autumn/crossing-autumn/spring 24-hour UTC windows,
first/last samples, exclusive bounds, 300-second cadence, both folds/spring jump,
wire serialization, canonical version/round-trip identity, original legacy hash,
legacy inclusive-end compatibility, unchanged 301-sample atomic rejection,
malformed/local-conflict failures, unsupported ambiguous/non-grid boundaries,
5/10/60/1500-minute durations, one-provider controller admission and successful/
failed denied replay with immutable archive/query/provenance linkage. Tests load
no credentials or real archive and perform no live calls. The original Stage 8
301-sample regression and all previous tests remain unchanged.

Changed production code is confined to four ESIOS modules and the existing
Stage 8 controller. Added ADR 0008/index entry and this continuation prompt,
report section and runbook guidance. No dependencies, shared contracts, other
provider semantics, infrastructure, CI, fixture payloads or architecture flow
changed. Existing dirty Stage 8 work remains unstaged for review.


### Final continuation validation

Python **3.12.9**. All pytest runs retain collection-time network denial and
synthetic transports; no tests repeat live requests or load real credentials.

| Executed gate | Continuation result |
| --- | --- |
| ESIOS unit/integration + new boundary suite + Stage 8 controller | **186 passed in 6.86 s** (25 new boundary cases; 49 existing Stage 8 cases retained) |
| Stage 7 audit + offline guard/private HTTP/HTTP/deadline/transport/archive/XML security selection | **457 passed in 4.98 s** |
| `python -m pytest tests/integration/stage6 -q` | **119 passed in 34.29 s** |
| Full `python -m pytest` | **2,320 passed in 58.52 s**, no failures/skips/warnings |
| `ruff check .` | **PASS** |
| `ruff format --check .` | **PASS**, 167 files formatted |
| `mypy src` | **PASS**, 61 source files |
| `pre-commit run --all-files` | **PASS**, all eight hooks |
| Explicit pre-commit on all new unstaged/untracked paths | **PASS**, all six applicable hooks; YAML/TOML inapplicable |
| `git diff --check` and complete changed/new file review | **PASS** |

Only one additional logical ESIOS request was executed (one HTTP attempt,
no retry). The original ESIOS failure remains real and preserved; it has not
been replaced with a synthetic success. Existing six-product acceptance is
unchanged and required no new provider calls. No stage, commit, branch, push,
fetch, pull, rebase, reset, restore or stash occurred. The index is unchanged;
`.env` remains ignored/untracked and was never written.

Exact final `git status --short`:

```text
 M .gitignore
 M docs/adr/README.md
 M docs/runbooks/ingestion.md
 M src/iberian_shakti/ingestion/esios/adapter.py
 M src/iberian_shakti/ingestion/esios/identity.py
 M src/iberian_shakti/ingestion/esios/parser.py
 M src/iberian_shakti/ingestion/esios/profile.py
?? docs/adr/0008-esios-bounded-five-minute-request.md
?? docs/codex/prompts/phase_2/phase_2_stage_8_controlled_live_validation_replay.md
?? docs/codex/prompts/phase_2/phase_2_stage_8_esios_544_boundary_semantics_resolution.md
?? docs/codex/reports/phase_2_stage_8_controlled_live_validation_report.md
?? src/iberian_shakti/ingestion/_live_budget.py
?? src/iberian_shakti/ingestion/phase2_live.py
?? tests/integration/test_esios_boundary_semantics.py
?? tests/integration/test_phase2_stage8_live.py
```

### Final continuation verdict

**Phase 2 Stage 8 — PASS.** The ESIOS 544 required-product boundary-semantics
validation gap is resolved for the explicit bounded profile and controlled UTC
window. Accepted successful normalized records across the six original products
and corrected ESIOS total **1,848**; the original ESIOS failed acquisition stays
separate and is not counted as successful data. Provider-wide DST/filtering
internals, ambiguous wire boundaries, historical forecast vintage and future
compatibility are not claimed resolved. These limits do not reinterpret any raw
sample or conceal out-of-window data.

Phase 2 Stage 9 has not been started or authorized. No 44-criterion Phase 2
closure, paid cloud operation or later-phase implementation was performed.
