> **Current final acceptance — 2026-11-03:** operator policy accepts REN criterion 4
> as SATISFIED WITH DOCUMENTED LIMITATION under ADR 0009. Current totals are
> **42 SATISFIED, 2 SATISFIED WITH DOCUMENTED LIMITATION, 0 NOT SATISFIED**.
> **Phase 2 Stage 9 — PASS. Phase 2 — Multi-Source Ingestion Expansion — CLOSED.**
>
> The complete pre-policy Stage 9 record below—including its original checklist,
> PASS WITH GAPS verdict and targeted REN investigation—is preserved verbatim as
> history. The [operator-policy resolution and current authoritative checklist](#operator-acceptance-policy-resolution-for-ren-criterion-4)
> at the end supersede those earlier acceptance statuses without strengthening
> provider evidence or changing implementation semantics.

---

# Phase 2 Stage 9 — Final acceptance and closure review

Execution date: **2026-11-03**, Europe/Lisbon. Python **3.12.9**.

## 1. Executive verdict

**Phase 2 Stage 9 — PASS WITH GAPS. Phase 2 remains open.**
The final checklist reconciles **44/44** original criteria: **42 SATISFIED**,
**1 SATISFIED WITH DOCUMENTED LIMITATION** (#5), **1 NOT SATISFIED** (#4).
All seven required Stage 8 products and their denied replay are accepted.
The remaining gap is the stronger final REN timestamp/fold evidence requirement,
not a missing live product or failed local engineering check.

One locally determinable production defect was reproduced and corrected: an
ENTSO-E 429 previously stopped its acquisition but allowed later selections.
The whole invocation now stops, satisfying #21; three strengthened permanent
regressions prove every ENTSO-E position, preserved prior bytes and denied replay.
No provider semantics, product/version, query identity or dependency changed.
Fresh gates and exact commands are in §12. No additional live validation occurred.

## 2. Baseline and scope

Mandatory first verification: `git status --short` (empty),
`git log --oneline --decorate -15`, `git diff --check` (empty).
Existing branch **main**; authoritative clean HEAD
**e3753ca34dbb8670138d74887af17a1a5e4f79f1** (`e3753ca`,
`feat: complete Phase 2 controlled live validation`). Working tree/index were
clean. Local main is intentionally **11 commits ahead** of locally recorded
`origin/main` at `a4191a3`; no fetch or remote freshness claim.

`git show HEAD:docs/codex/reports/phase_2_stage_8_controlled_live_validation_report.md`
confirmed the committed executive/final continuation verdict **Stage 8 — PASS**
and its §24 bounded ESIOS success. Earlier §23 PASS WITH GAPS is preserved history.
The exact operator prompt was saved before code/document changes at
[phase_2_stage_9_final_acceptance_closure.md](../prompts/phase_2/phase_2_stage_9_final_acceptance_closure.md)
and byte-compared with the received user message before adding the repository-standard
terminal LF (prompt wording unchanged). Earlier prompts/reports and
ADRs are unchanged.

Read AGENTS.md, complete required Stage 1–8 history/readiness/model-selection,
README, architecture, all ADRs and runbooks. Inspected provider profiles,
query/parser/schema contracts, live controller/budget, runner/archive/replay,
network guard, CI and specific test evidence. This is acceptance of the fixed
scope, not another readiness/source-selection study or new live experiment.

## 3. Phase 2 development history

| Stage | Engineering result and durable evidence |
| --- | --- |
| 1 shared foundation | [Stage 1][s1], ADRs 0003/0004: canonical API snapshot queries, frozen system/weather records, explicit semantic outcomes and private selected authentication; Phase 1 wire compatibility. |
| 2 REN | [Stage 2][s2]: original 0.1.0 time gate/PASS WITH GAPS preserved; explicit operator policy and ADR 0006 accept provisional 0.2.0 periods/unaltered MW for Stage 2 engineering. Stronger final criterion 4 was not replaced for full Phase 2. |
| 3 ESIOS | [Stage 3][s3]: indicator 544, private x-api-key, strict Decimal/UTC/peninsular forecast normalization and acquisition snapshots; live evidence reserved. |
| 4 ENTSO-E | [Stage 4][s4]: ES A65/A16 and PT/ES A69/A01; strict namespace-aware bounded XML, A01/A03, native identity, no-data/rejection and denied replay. |
| 5 Open-Meteo | [Stage 5][s5]: ERA5 then explicitly approved ICON-EU, independent profiles/parsers, six sites, exact hourly UTC-day arrays, ADR 0007 explicit output identity. [Model selection][selection] is retained, not reopened; IFS remains documentation only. |
| 6 cross-source | [Stage 6][s6]: all products/domains/sites coexist through actual shared components; no geography/unit/time/kind conflation, correction loss or replay fallback; 119-case compatibility proof. |
| 7 pre-live audit | [Stage 7][s7]: encoded credential echo and OMIE direct-parser cap corrections; 44 provisional classifications, security/timeout/parser audit. Live and final classifications resolved individually below. |
| 8 controlled live | [Stage 8][s8]: original seven HTTP-200 acquisitions, six successful products plus preserved ESIOS overrun failure. Separately authorized §24/ADR 0008 accepts bounded ESIOS 0.2.0 with 288 valid samples and denied replay. Overall Stage 8 PASS. |
| 9 final review | This report: exact reconciliation, current documentation, fresh gates and narrow #21 controller fix; #4 remains an external semantic/final-policy gap. |

## 4. Final implemented provider/product matrix

Live/replay columns report retained evidence, not new Stage 9 execution.

| Provider/product | Final version | Geography | Kind | Native cadence/support | Units | Live validated | Replay validated |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OMIE marginalpdbc — Phase 1 prerequisite | parser 1.0.0; market schema 1.0.0 | PT/ES market areas, both Madrid delivery day | day-ahead price | 60 min before 2025-10-01; 15 min from then; 23/24/25 h physical days | Decimal EUR/MWh | Phase 1 Stage 6 | Phase 1 + fresh compatibility regressions |
| REN ElectricityProductionBreakdownDaily | profile/parser 0.2.0 | provider-defined PT system; aggregate external boundary | actual, provisional | 15 min Lisbon interval_start, 92/96/100; provider_period_value | Decimal MW | Stage 8, 1,056 records | Stage 8 equal denied replay |
| ESIOS 544 Demanda prevista Peninsular | bounded profile/parser 0.2.0 | ES.peninsular, native geo 8741 observed | forecast | 300 s ValidInstant; logical half-open UTC, no fill | Decimal MW (documented, no native unit field) | Stage 8 §24, 288 records | §24 equal denied replay |
| ENTSO-E ES actual load A65/A16 | profile/parser 0.1.0 | ES bidding zone 10YES-REE------0 | actual | PT15M observed; PT15M/PT30M/PT60M supported, provider_period_value | MAW → Decimal MW | Stage 8, 96 records | Stage 8 equal denied replay |
| ENTSO-E PT renewables A69/A01 | profile/parser 0.1.0 | PT bidding zone 10YPT-REN------W | forecast | PT60M observed; A03 blocks; B16/B18/B19 returned | MAW → Decimal MW | Stage 8, 72 records | Stage 8 equal denied replay |
| ENTSO-E ES renewables A69/A01 | profile/parser 0.1.0 | ES bidding zone 10YES-REE------0 | forecast | PT15M observed; A03 blocks; B16/B19, no invented B18 | MAW → Decimal MW | Stage 8, 192 records | Stage 8 equal denied replay |
| Open-Meteo ERA5 Historical Weather | profile/parser 0.1.0 | six versioned PT/ES sites, independent returned grids | reanalysis | 24 UTC hourly samples; temperature/wind instants, radiation preceding-hour mean | finite float °C, m/s, W/m² | Stage 8 Lisbon, 72 records | Stage 8 equal denied replay |
| Open-Meteo DWD ICON-EU, models=icon_eu | profile/parser 0.1.0 | same six sites; independent returned grids | forecast | next UTC-day snapshot, 24 hourly samples; same variable support | finite float °C, m/s, W/m² | Stage 8 Lisbon, 72 records | Stage 8 equal denied replay |

All-site weather support is deterministic/offline; readiness §Q deliberately
requires only one-site live validation for each weather product. REN's live
product acceptance under the operational empirical profile is distinct from
final #4 authority. No source was removed because its semantics are limited.

## 5. Final profile/parser/version inventory

Read directly from committed profiles/contracts/parser classes, unchanged by
Stage 9. These independent version axes are not the package release version.

| Contract/product | Exact accepted version/identity | Implementation |
| --- | --- | --- |
| API query / selection | ApiSourceRequest 2.0.0; api_snapshot | [queries.py][queries] |
| QueryWindow/SystemQuery/WeatherQuery/geography/source-time values | No independent wire-version field; carried in API 2.0.0 / measurement 1.0.0; typed bounded/frozen | [queries][queries], [geography][geography], [measurements][measurements] |
| Private auth / semantic outcomes | No standalone version field; ADR 0004, controlled ErrorCode/ParseOutcome and measurement parse-event 2.0.0 | [auth][auth], [contracts][contracts] |
| Shared legacy request/raw/retrieval | Base ingestion contract 1.0.0; RetrievalProvenance 1.0.0 for OMIE, 2.0.0 for API | [_base.py][base], [ingestion.py][contracts] |
| Legacy market record/parse | MarketPrice schema 1.0.0; ParseProvenance 1.0.0 | [market.py][market], [contracts][contracts] |
| System/weather records / schema families | SystemMeasurement 1.0.0 / system_measurement; WeatherMeasurement 1.0.0 / weather_measurement; RecordSchema 1.0.0 | [measurements.py][measurements] |
| Measurement parse provenance | 2.0.0; explicit parser/catalogue/record-schema family/version, original retrieval/raw link | [MeasurementParseProvenance][contracts] |
| REN | profile/catalogue 0.2.0; ren-production-breakdown / 0.2.0; ElectricityProductionBreakdownDaily.en-US.v0.2.0 | [profile][ren-profile], [parser][ren-parser] |
| ESIOS accepted | bounded profile/catalogue 0.2.0; esios.indicator544 / 0.2.0; indicator544.v0.2.0 | [profile][esios-profile], [BoundedEsiosParser][esios-parser] |
| ESIOS historical | profile/parser 0.1.0; indicator544.v0.1.0 retained for legacy inclusive-end reproduction | same modules; legacy adapter/default request constructor unchanged |
| ENTSO-E | profile/catalogue 0.1.0; entsoe.generation-load / 0.1.0; actual_load.A65.A16.v0.1.0 and wind_solar_forecast.A69.A01.v0.1.0 | [profile][entsoe-profile], [parser][entsoe-parser] |
| ERA5 | profile/catalogue 0.1.0; open_meteo.era5.hourly / 0.1.0; historical.era5.v0.1.0; model era5 | [profile][weather-profile], [parser][weather-parser] |
| ICON-EU | independent profile/catalogue 0.1.0; open_meteo.icon_eu.hourly / 0.1.0; forecast.icon_eu.v0.1.0; model icon_eu | same weather modules |
| Weather site/output selection | six sites selection_version 0.1.0; ICON-EU WeatherOutputSelection.profile_version 0.1.0; absent ERA5 output field preserves legacy identity | [profile][weather-profile], [identity][weather-identity], ADR 0007 |
| OMIE prerequisite | omie.marginalpdbc / 1.0.0, marginalpdbc report | [identity][omie-identity] |

Raw archive layout/content addressing has no new Stage 9 schema or migration.
REN historical 0.1.0 query/failure evidence remains retained; the 0.2.0 parser
can explicitly reinterpret supported legacy acquisitions with new parse events.
ESIOS historical 0.1.0 and accepted bounded 0.2.0 remain separate behaviors.

## 6. Shared architecture and invariants

```text
external provider → typed query → bounded fixed-origin retrieval
  → immutable original raw bytes → retrieval provenance
  → strict provider parser → normalized typed record → parse provenance
  → network-free checksum/linkage-verified replay
```

[runner.py][runner] persists raw/retrieval before parsing and parse provenance
before returning success. [archive.py][archive] uses same-directory staging,
fsync and hard-link no-replace publication. Identical raw content is reused;
changed bytes and independent acquisitions retain immutable histories. Raw
identity includes source/report/partition/hash; query identity and native provider
revision are separate. Immutability assumes a trusted hard-link/fsync filesystem,
not WORM or signed adversarial metadata.

Strict whole-parse validation has no silent bad-row dropping, invented zeros,
clipping, sorting, filling, resampling, derived totals or MW-to-MWh conversion.
ENTSO-E A03 block expansion is declared encoding. Gaps/absent technologies remain
visible. Decimal system/price values and finite scientific weather values stay
distinct, as do system perimeters, EIC roles, logical sites and returned grids.

## 7. Live evidence summary

Authoritative evidence is the committed [Stage 8 report][s8], not a fresh archive
inspection/request. The original run made **7 logical requests / 7 attempts /
0 retries**, **159,742 body bytes**, **163,127 conservative inbound bytes**,
**24.102013 seconds** acquisition/automatic-replay duration. All were HTTP 200;
6 successful products emitted 1,560 records. Original ESIOS 0.1.0 failed for
301 samples extending through 2026-10-25 01:00Z; its failure is not data success.

The separately authorized ESIOS continuation made **1 logical request / 1
attempt / 0 retries**, **71,973 body bytes**, **73,312 inbound bytes**, HTTP 200.
It returned **288 samples**, every delta 300 seconds, no gaps/duplicates/outside
values, 00:00Z through 23:55Z for `[2026-10-24,2026-10-25)`. Final successful
seven-product acceptance is **1,848 records**. Across both acquisitions there
were **8 logical requests / 8 attempts / 0 retries / 0 metadata requests** and
**231,715 original body bytes**. These are two separately bounded runs, not one
run exceeding its request plan. The targeted correction is the explained §Q
deviation; no failed acquisition was erased or counted as success.

| Accepted product | Body SHA-256 (from Stage 8) | Records |
| --- | --- | ---: |
| REN | 65145ea67ba42da8e30a54bff8d262eb11acf18998d8dca4393983134add30db | 1,056 |
| ESIOS bounded 0.2.0 | 476aecfc4b13b6ada038aabbd6cfce792d2c1804d62a1b87b08b96eb6f3de7ae | 288 |
| ENTSO-E ES load | a7bac5cb29dbf3e53008e5243cd6ed9a16dddbe56b807d90d2b518a35826173f | 96 |
| ENTSO-E PT renewables | a6cf213879c6622783811cb941be366b2a6d51015b3801aca1b6c61d3661faaf | 72 |
| ENTSO-E ES renewables | 55e0238a1da82640fc73445d26f7e63c18e59360f98d50e578f793e37daf698b | 192 |
| ERA5 | 625cbf92d592967ce609c4c3dd8dbbb07263d8858a7534d6fd7fdd5455878257 | 72 |
| ICON-EU | 8bdad6043e7284eee80c8cfe2df24548f9744853cd12a394e437b3d103c33fd9 | 72 |

Historical failed ESIOS body SHA-256 remains
`4b356d9e2a6f0d8c96f762c7f214834eff41e5c9f8c219839a1a81d2e9e3c926`.
Stage 8 §§15/24 retain safe canonical query hashes, original retrieval/parse/replay
UUIDs, raw references and accounting. For corrected ESIOS the query SHA-256 is
`346e02f84124188197200349025b27c6e64124f433f34738d91fbb986c7c4f5e`, retrieval
`9ebff94f-5955-44e9-bbfc-88306fdd713d`, acquisition parse
`b54bc228-6072-49aa-8b17-8263d06c0824`, automatic replay
`90a20de9-54dc-4cb0-a5d1-3cb5d9614652`.

External local evidence roots:
`/tmp/iberian-shakti-phase2-stage8-live-20261103` and
`/tmp/iberian-shakti-phase2-stage8-esios-boundary-live-20261103`.
They are **outside Git, not repository fixtures, not required by ordinary tests**.
Stage 9 did not open/modify live payloads, manifests or events. Preservation
verification of all 36 pre-continuation files belongs to Stage 8 §24; it is not
misreported as a new Stage 9 archive audit. No native unit field, error response,
fold algorithm, future compatibility or historical vintage is invented.

## 8. Replay/provenance summary

Stage 8 denied network/client/retriever/credential access with empty process
environment and matched full record content plus parse/query/raw/retrieval
linkage, excluding only new parse UUID/time. All seven accepted successful
products reproduce, including corrected ESIOS; the old ESIOS failure also
reproduces its zero-record failure separately. Explicit replay-only proofs
succeeded without credentials or new acquisitions. Stage 9 deliberately does
not rerun replay on real archives because it would append new parse events.

Fresh offline regressions use synthetic temporary archives, actual provider
parsers and shared components. They test original acquisition identity, byte/hash
and event consistency, complete values/business identities, correction survival,
failed parse reproduction, corrupt/missing linkage without refetch and preserved
prior files. No Stage 8 /tmp path is a test input.

## 9. Security/boundedness summary and local correction

Every request retains fixed HTTPS origin, verified TLS, trust_env=False,
zero redirects/hidden transport retries, phase/attempt/operation deadlines
10/30/93 s, default 3 attempts and 1/2 s bounded backoff. Supported Retry-After
is not shortened; semantic/content/permanent/auth failures do not retry.
Per-product response/parser caps are OMIE 4 MiB (discovery 1 MiB), REN 1 MiB,
ESIOS 2 MiB, ENTSO-E 4 MiB, each weather product 1 MiB. JSON/XML structural and
expanded-record limits remain those in profiles, Stage 7 §§7–8 and runbook.

[_live_budget.py][budget] and [phase2_live.py][live] enforce production whole-run
controls: original fixed plan 7 logical requests with ceiling 8 (optional metadata
slot unused/unimplemented), 24 total attempts, 32 MiB attempted-body and separate
conservative inbound cap, 900 s deadline, sequential 1.1 s attempt-start pacing.
Targeted ESIOS mode: 1 logical/3 attempts/6 MiB body+inbound/120 s. Failed,
interrupted/retried/error bodies count; read admission shrinks before socket reads.
POSIX main-thread alarm extends the finite bound to DNS/parsing/local work under
the documented host assumptions. Stage 6 limits are test-only, not production caps.

**S9-01 / criterion 21:** source inspection found
`test_entsoe_429_is_terminal_and_other_planned_domains_continue` deliberately
expected continuation after 429. That contradicted the original whole-invocation
requirement. Before correction, the strengthened parameterized regression failed
**3/3** at the absent stop category (all selected ENTSO-E positions). The controller
now records the failed acquisition and raises static `entsoe_rate_limited`,
persists its counters/safe manifest and stops all subsequent network selections.
Earlier immutable objects remain available to explicit offline replay. Three
cases pass after correction and verify exact request/attempt counts, no retries,
untouched later entries, byte accounting and byte-identical earlier evidence
through replay. Existing per-acquisition retry/error-drain controls remain intact.
This strengthens the old continuation assertion; no test is weakened or skipped.
No provider observation is needed to validate this local admission policy.
No 429 occurred in retained Stage 8 runs; their evidence is unaffected.

Secret-safe logging/private request/echo tests retain literal/percent/JSON/XML
protections without redacting and mislabelling raw bytes. Active-token protection
is intentionally narrow, not general DLP. `.env` was checked only for Git
ignore/tracking presence; it was never read. No credential value was inspected.

## 10. Final 44-criterion reconciliation

Original text below is copied verbatim from readiness §V, programmatically
checked for exact equality and sequential numbering. Original reports remain
immutable. Final classifications concern each exact requirement, not nearby
successes. Evidence links identify concrete code/test/document/live sources.

| # | Original criterion | Final status | Primary evidence | Supporting evidence | Residual limitation |
| --- | --- | --- | --- | --- | --- |
| 1 | Accepted Phase 2 query/measurement/auth/semantic-outcome decisions are recorded in focused ADR(s) before corresponding implementation; Phase 1 ADR history is retained and this report remains the sole readiness assessment. | SATISFIED | [ADRs 0003–0008][adrs]; [Stage 1 §D][s1] | [Stage 2 §U][s2]; [Stage 5 completion][s5]; [Stage 8 §24][s8] | ADRs 0001/0002 and sole readiness unchanged; no new Stage 9 architectural decision. |
| 2 | All four mandatory providers and exactly the minimum products in §C are implemented; any scope change is explicitly approved and traced, never silently removed to obtain acceptance. | SATISFIED | [REN][ren-profile], [ESIOS][esios-profile], [ENTSO-E][entsoe-profile], [weather profiles][weather-profile] | [Stage 6 source matrix][s6]; [Stage 8 §§7–13,24][s8] | Exactly selected products; explicit ICON-EU operator selection, no IFS implementation. |
| 3 | REN's documented daily production endpoint supplies all selected load/generation/import/export series from one acquisition; ancillary series/presentation fields have explicit selection policy, with no double-counted totals. | SATISFIED | [ren/profile.py][ren-profile], [ren/parser.py][ren-parser], [ren/schema.py][ren-schema] | [REN parser tests][ren-tests]; [Stage 8 §7][s8] | Eleven selected/four ancillary series, all arrays validated; time evidence separately assessed in #4. |
| 4 | REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly. | NOT SATISFIED | [ADR 0006][adr6]; [Stage 2 §U, Revised acceptance and limits][s2] | [REN period tests][ren-tests]; [Stage 7 §19 row 4][s7]; [Stage 8 §7][s8] | NOT SATISFIED: explicit provisional profile cannot prove label placement or value-to-fold ownership. Stage 2-only replacement does not replace final criterion; see §10 reasoning. |
| 5 | ESIOS 544 is verified against official authenticated name/unit/geography/sampling metadata, retained in a versioned catalogue; the peninsular forecast curve is not mislabelled as a complete D-1 forecast or actual load. | SATISFIED WITH DOCUMENTED LIMITATION | [ESIOS profile/schema][esios-profile]; [Stage 8 §§8,24 metadata][s8] | [Readiness §F][ready]; [ESIOS parser][esios-parser]; [boundary regressions][boundary-tests] | No native unit field in either live response. Official selected-product MW plus authenticated Potencia/name/geo/cadence supports pinned MW; 0.2.0 bounded success; see §10. |
| 6 | ENTSO-E implements ES A65/A16 actual total load and PT plus ES A69/A01 renewable forecasts, retaining document/series/process/domain/PSR identity and distinguishing absent technologies from zero output. | SATISFIED | [ENTSO-E profile][entsoe-profile], [schema][entsoe-schema], [parser][entsoe-parser] | [ENTSO-E parser tests][entsoe-tests]; [Stage 8 §§9–11][s8] | Only returned PSRs; ES offshore absent, PT offshore present in captured response. No completeness guarantee. |
| 7 | ENTSO-E namespace/version, Period resolution/position and A01/A03 curve handling are explicitly supported and tested, including multiple periods, constant blocks, missing sections and conflicting overlaps. | SATISFIED | [entsoe/schema.py][entsoe-schema], [xml_boundary.py][xml] | [test_entsoe_parser.py][entsoe-tests] A01/A03, multiple Periods, gaps/overlaps | Strict GL v3/ACK v7 subset, PT15M/PT30M/PT60M; unknown versions fail. |
| 8 | Open-Meteo archive ERA5 and selected-model forecast ingestion support exactly the three initial variables at six versioned sites, preserving requested/returned coordinates, grid/elevation and model identity. | SATISFIED | [Weather profile][weather-profile], [identity][weather-identity], [parser][weather-parser] | [ICON-EU tests][icon-tests]; [Stage 6 six-site matrix][s6]; [Stage 8 §§12–13][s8] | Six sites offline; minimal authorized live smoke uses Lisbon only. Model pinned by query; no required response model echo. |
| 9 | Query contracts carry validated nonsecret product/window/domain/variables/location/model identity and explicit selection semantics; API snapshots do not fabricate numeric OMIE revisions or guaranteed latest versions. | SATISFIED | [contracts/queries.py][queries]; provider identity validators | [test_multisource.py][contracts-tests]; [Stage 6 query tests][s6-semantics]; [boundary-tests][boundary-tests] | API snapshots have no numeric revision/latest-history guarantee. ERA5 legacy bytes retained. |
| 10 | New system/weather record families and parse schema-family versions are strict, frozen and typed; MarketPrice and Phase 1 serialized archive/provenance remain readable and behaviorally compatible. | SATISFIED | [contracts/measurements.py][measurements], [ingestion.py][contracts], [_base.py][base] | [Contract tests][contracts-tests]; [test_multisource_foundation.py][foundation] original_phase1_wire_and_stored_events_replay_without_migration | Explicit versions; old wire events are read without migration. |
| 11 | Geographic roles distinguish country, mainland/system perimeter, bidding zone, control area, EIC and coordinate; native IDs remain available and directed/aggregate interchange are not conflated. | SATISFIED | [contracts/geography.py][geography]; provider profiles | [Stage 6 geography tests][s6-semantics]; [REN profile tests][ren-profile-tests] | Country/system/bidding-zone/coordinate coincidence never implies equivalence; no invented import/export counterparty. |
| 12 | MW, MWh and EUR/MWh remain distinct; system/market decimals have no binary-float intermediate and financial serialization preserves exact decimal values. | SATISFIED | [measurements.py][measurements], [market.py][market]; direct Decimal JSON/XML parsers | [Contract precision/unit tests][contracts-tests]; [Stage 6 unit tests][s6-semantics] | MW provider_period_value cannot become MWh; no binary float intermediate for system/market values. |
| 13 | Scientific weather values are finite floats with explicit verified units, height/statistic and versioned plausibility/missing policy; no clipping or implicit unit conversion occurs. | SATISFIED | [weather/schema.py][weather-schema], [parser.py][weather-parser]; [measurements.py][measurements] | [Weather parser tests][weather-tests]; [Stage 8 §§12–13][s8] | Schema 1.0.0 broad plausibility bounds; null/out-of-profile values fail the selected product atomically, no clipping. |
| 14 | Every normalized time is UTC-aware; instant samples, positive half-open intervals, source cadence and weather preceding-hour support remain distinct and query boundary handling is tested. | SATISFIED | [Measurement timing][measurements], [queries][queries]; provider parsers | [Stage 6 support tests][s6-semantics]; [ESIOS exclusive-boundary tests][boundary-tests] | REN empirical support is qualified by #4. Radiation at midnight retains preceding-day interval. |
| 15 | Ordinary/leap/year boundaries, spring/autumn DST, duplicate local labels and UTC/local-day crossings are covered where applicable; GMT weather days are not forced to local 23/25-hour counts. | SATISFIED | [REN period tests][ren-tests]; [OMIE calendar tests][omie-calendar-tests]; [boundary tests][boundary-tests] | [ICON-EU calendar tests][icon-tests]; [Stage 6 independent_calendars_coexist_at_dst_and_midnight][s6-semantics] | DST synthetic tests establish implementation policy, not unseen provider observations; weather always 24 UTC samples. |
| 16 | Actual, forecast and reanalysis kind is explicit; issue/publication/update/acquisition times remain distinct and unknown source times/horizons stay null. | SATISFIED | [ValueKind/SourceTimes][measurements]; provider parsers | [Stage 6 unknown_source_times_and_native_update_metadata_remain_separate][s6-semantics]; [Stage 8 §§8–13,24][s8] | Unknown issue/run/publication/horizon remains null as required; update/document creation is not issuance. |
| 17 | Multiple known forecast editions and unknown-edition acquisition snapshots for the same target survive distinctly; historical refetches are never declared known at an earlier market cutoff without evidence. | SATISFIED | [Measurement business_identity][measurements]; [immutable archive][archive] | [Contract edition tests][contracts-tests]; [Stage 6 latest_forecast_cannot_establish_an_old_market_cutoff][s6-semantics]; provider correction tests | Requirement explicitly preserves unknown editions and forbids old-cutoff claims; historical reconstruction is not required or implemented. |
| 18 | Source-selected credentials use ESIOS_API_TOKEN and ENTSOE_API_TOKEN, validated before I/O and injected privately using the verified mechanism; anonymous providers and OMIE need neither credential. | SATISFIED | [Selected credential loader][config], [private auth][auth]; provider adapters | [Private request tests][private-tests]; [Stage 8 §6,24 real authenticated HTTP 200][s8] | ESIOS x-api-key; ENTSO-E securityToken privately. No Stage 9 probe or credential access. |
| 19 | Authentication/authorization failures are terminal, safely diagnosed and tested; there is no pasted-secret workflow, implicit dotenv load, auto-registration or token-refresh/probing loop. | SATISFIED | [config.py][config], [auth.py][auth], [http.py][http] | [Private request tests][private-tests]; [Stage 7 §5][s7]; [runbook][runbook] | Terminal synthetic 401/403; no implicit dotenv, registration, refresh or secret-pasting workflow. |
| 20 | Every external call uses finite phase/attempt/operation budgets, response caps, verified TLS, zero redirects and no hidden transport retries; whole-invocation query/attempt/byte/time caps are enforced. | SATISFIED | [http.py][http], [_http_transport.py][transport], [_live_budget.py][budget], [phase2_live.py][live] | [Stage 7 §6][s7]; [Stage 8 controller tests][live-tests]; [Stage 8 §17,24 accounting][s8] | Production Stage 8 caps include failed/retried body and conservative inbound bytes; Stage 6 plan remains test-only. |
| 21 | Retry policy has at most three attempts by default with bounded backoff, permanent/content/no-data failures do not retry, Retry-After is never shortened and ENTSO-E token bans end the invocation. | SATISFIED | [retry.py][retry], [http.py][http], [Stage 9 controller correction][live] | [Stage 7 composed budgets][audit-tests]; [three ENTSO-E 429 invocation regressions][live-tests]; §9 below | Stage 9 fixed continuing after ENTSO-E 429. All later selections now remain not_executed; prior evidence replayable. No live 429 claimed. |
| 22 | Selected query/record/JSON/XML bounds are implemented and documented; unexpected pagination/truncation/ZIP/content coding gives explicit coverage or unsupported failure rather than partial success. | SATISFIED | [Provider profiles][ren-profile], [ENTSO-E XML][xml], [weather schema][weather-schema]; [OMIE parser][omie-parser] | [Stage 7 §§7–8][s7]; [provider parser tests][entsoe-tests]; [controller budget tests][live-tests] | Strict supported envelope, no ZIP/pagination/implicit decoding/partial success; parser caps apply in replay too. |
| 23 | XML cannot resolve external resources or expand DTD/entities; encoding-aware element/depth/text/work safeguards and hostile-payload tests exercise the actual parser boundary, with any added security dependency justified. | SATISFIED | [entsoe/xml_boundary.py][xml] | [test_entsoe_xml_security.py][xml-tests]; [Stage 7 §8][s7] | Expat >=2.6.0; DTD/entity/external access rejected; actual callback work limits; no added dependency. |
| 24 | Original complete safe provider body bytes are archived unchanged before transformation/semantic parsing using reused SHA-256 content addressing and atomic no-replace publication. | SATISFIED | [runner.ingest_resolved][runner]; [archive._publish/persist][archive] | [Stage 6 raw provenance tests][s6-evidence]; all provider flows; [Stage 8 §15,24][s8] | Safe complete representation bytes before transformation; framing not payload; sensitive/interrupted bodies not published. |
| 25 | Independent identical acquisitions reuse content while retaining immutable events; changed bytes under unchanged provider/query/revision keys retain both versions and repeated event IDs remain idempotent. | SATISFIED | [archive.py][archive] | [test_stage5_archive.py][archive-tests]; [Stage 6 identical_and_revised_acquisitions_are_provider_local_and_immutable][s6-evidence] | Content reuse plus immutable independent events; no mutable latest overwrite or fabricated provider revision. |
| 26 | Retrieval provenance retains safe query/locator, acquisition UTC/status/attempts, native revision observations when known, byte/hash/archive linkage; no private request data is persisted. | SATISFIED | [RetrievalProvenance][contracts], [retrieval.py][retrieval], [archive.py][archive] | [Private request tests][private-tests]; [Stage 6 persisted-chain checks][s6-evidence]; [Stage 8 §15,24][s8] | Only safe locators/query and allowlisted observations; unknown native revisions/publication times stay unknown. |
| 27 | Separate parse provenance records parser/schema/catalogue versions and original raw/retrieval linkage; every normalized record links back to that chain and persistence failure prevents success. | SATISFIED | [MeasurementParseProvenance/ParseResult][contracts]; [runner][runner] | [Stage 6 required_persistence_failure_prevents_success_for_every_path][s6-evidence]; [contracts tests][contracts-tests] | Per-record parse/retrieval linkage, explicit parser/catalogue/schema; parse persistence failure prevents return of success. |
| 28 | Complete malformed safe 200 responses and semantic no-data/error documents are preserved with explicit parse/semantic outcomes and zero normalized success; interrupted/oversized responses never masquerade as complete acquisitions. | SATISFIED | [Shared HTTP][http], [runner][runner], provider parsers | [Stage 6 failure chains][s6-evidence]; [ENTSO-E acknowledgement flow tests][entsoe-flow]; [Stage 8 original ESIOS failure][s8] | Safe malformed 200/ACK retained with zero records; incomplete or oversized bodies not complete acquisitions. |
| 29 | Empty/null/missing/unsupported/future/provider-error results are distinguished from successful selected coverage; no bad rows are silently dropped, absent data converted to zero or undeclared partial dataset emitted. | SATISFIED | [REN schema][ren-schema], [ESIOS schema][esios-schema], [ENTSO-E acknowledgements][ack], [weather schema][weather-schema] | [ENTSO-E parser error/no-data tests][entsoe-tests]; [weather error flow tests][weather-flow]; [Stage 6 taxonomy][s6] | Implemented safe distinction required, not deliberate real failures. No natural live errors/no-data observed; unknown shapes fail, never success. See §10. |
| 30 | Provider-specific auth/quota/domain/semantic/schema errors map to controlled typed categories, including ENTSO-E acknowledgement context rather than reason 999 alone; raw error text is never logged. | SATISFIED | [ErrorCode/ParseOutcome][contracts]; [entsoe/acknowledgement.py][ack]; provider parsers | [ENTSO-E exact-context tests][entsoe-tests]; [Stage 7 §14][s7]; [Stage 6 failure isolation][s6-evidence] | Reason 999 alone is insufficient; unknown/mixed text remains controlled rejection, never raw prose logging. |
| 31 | Safe logging/CLI/exception/config/metadata boundaries are tested with synthetic secret-bearing URLs, headers, rejected validation inputs and credential echoes; sensitive raw-body publication is rejected without pretending redaction preserves original bytes. | SATISFIED | [auth.py][auth], [common/logging.py][logging], [config.py][config] | [Stage 7 encoded echo/origin/redirect tests][audit-tests]; [private tests][private-tests]; [Stage 8 safe manifest tests][live-tests] | Narrow active-credential guard with specified reversible encodings; no general DLP/unmanaged-handler guarantee required. |
| 32 | Each selected product replays entirely offline from archived bytes/history plus pinned catalogue metadata, with no name/geo/schema/weather/model network lookup and no fallback acquisition. | SATISFIED | [replay.py][replay]; provider pinned parsers/profiles | [Stage 6 combined_replay_and_full_raw_provenance_without_credentials_or_acquisition][s6-evidence]; [Stage 8 §16,24][s8] | No HTTP/name/geo/schema/model lookup, credentials or fallback; external real archives are not ordinary test dependencies. |
| 33 | Replay verifies hash/linkage and reproduces fixed-version normalized values and identities; only new parse event identity/time may differ and original retrieval history remains unchanged. | SATISFIED | [replay.py][replay], [archive.load/load_retrieval][archive] | [Stage 6 corruption/replay tests][s6-evidence]; [Stage 7 query tampering tests][audit-tests]; [Stage 8 replay digests][s8] | New parse ID/time excluded; raw, original retrieval, query and business fields compared; trusted local metadata, no signature guarantee. |
| 34 | Actual-component mocked integration covers each mandatory product's successful chain, failure chain, correction/duplicate handling and replay through the shared archive/runner. | SATISFIED | [Stage 6 actual-component evidence suite][s6-evidence] | [REN][ren-flow], [ESIOS][esios-flow], [ENTSO-E][entsoe-flow], [weather flow tests][weather-flow] | Synthetic transports, actual shared runner/archive/provider parsers; every selected product/domain and six weather sites. |
| 35 | Small versioned fixtures cover §P's valid/missing/malformed/boundary/time/revision/provider-error cases; manifests protect hashes/inventory, label original/synthetic/mutated evidence and record rights/attribution. | SATISFIED | tests/data/{omie,ren,esios,entsoe,open_meteo,shared_contracts}/manifest.json and README.md | [Provider fixture inventory tests][ren-tests]; [ENTSO-E fixtures][entsoe-tests]; [foundation checksum tests][foundation] | Synthetic/mutated cases clearly labelled; original OMIE inventory preserved; zero Stage 8 payload copies. |
| 36 | Existing OMIE fixtures and meaningful tests are preserved; shared changes pass Phase 1 regression and old-provenance/replay compatibility tests without weakening assertions. | SATISFIED | [OMIE parser/calendar tests][omie-calendar-tests]; [Phase 1 compatibility fixture/test][foundation] | [Stage 6 OMIE coexistence][s6]; §12 provider/full gates | Original OMIE fixture bytes/assertions preserved; Stage 7 independent cap retained. |
| 37 | Repository-wide python -m pytest succeeds with the existing network-denied guard active from collection, without credentials, real providers, subprocess networking or a live-enabling test switch. | SATISFIED | [tests/conftest.py][guard]; [test_offline_guard.py][guard-tests] | §12 fresh full pytest and security selection; [Stage 7 all-provider default-transport denials][audit-tests] | Guard active before collection; synthetic credentials only; no live switch, archive dependency or subprocess network. |
| 38 | Live commands are separate and explicit --live opt-in, refuse before network construction without it, reject fixture archive roots and are absent from pytest/pre-commit/automatic CI execution. | SATISFIED | [phase2_live.run/main/archive_root][live]; [OMIE live_smoke][omie-live] | [Stage 8 no-live/root/denied-replay tests][live-tests]; [boundary default-command test][boundary-tests]; [CI][ci] | Default offline, explicit --live; external archive required; no live invocation in pytest/pre-commit/CI. See runbook original-vs-bounded distinction. |
| 39 | Controlled live validation records successful data through implemented retrieval/archive/parser paths for REN, ESIOS 544, ENTSO-E ES actual plus PT/ES forecasts, and Open-Meteo archive plus forecast; unavailability/auth failure is never counted as success. | SATISFIED | [Stage 8 §§5,7–13,24 successful real acquisitions][s8] | §7 below; [production composition][runner]; [versioned parsers/profiles][esios-parser] | Seven required successful products total 1,848 records; original ESIOS failure is separate; REN operational acceptance does not satisfy #4 authority. |
| 40 | The actual live acquisitions in criterion 39 have retained safe checksums/query/provenance/outcomes and successful subsequent network-denied replay; request/attempt totals and deviations from §Q are explained. | SATISFIED | [Stage 8 §§15–17,24 safe provenance and denied replay][s8] | §§7–8 below; [controller replay tests][live-tests]; [boundary replay tests][boundary-tests] | Original 7 requests + separately authorized corrected ESIOS 1; 8 total attempts, zero retries/metadata calls; external evidence unchanged by Stage 9. |
| 41 | Source catalogues/runbooks/README/architecture status describe implemented scope, limits, units/time/forecast semantics, credentials, errors, revisions, replay, live opt-in and attribution/licensing boundaries without claiming production clearance or complete history. | SATISFIED | [README][readme], [architecture][architecture], [runbook][runbook], [ADR index][adrs] | §11 current-document acceptance; §4 matrix, §5 exact inventory, §13 limitations; versioned provider code profiles | Documents keep Phase 2 open for #4 and retain historical reports; no production/commercial/history guarantee. |
| 42 | Final Python 3.12 ruff check ., ruff format --check ., mypy src, python -m pytest, git diff --check and applicable pre-commit checks pass; full new/staged/unstaged diff and Git status are reviewed. | SATISFIED | §12 fresh Python 3.12.9 gates on Stage 9 tree | §§16–17 tracked/untracked/index review and hygiene | No staging/commit/push; gate results recorded only after execution. |
| 43 | No Snowflake/dbt/features/ML/registry/inference/API/dashboard/deployment/Kafka/Kubernetes implementation, paid-resource change, bulk download or unnecessary runtime dependency enters Phase 2. | SATISFIED | §14 scope review; baseline-to-HEAD path diff a4191a3..e3753ca | Unchanged pyproject.toml runtime dependencies; empty future-package __init__.py and .gitkeep trees | Future skeletons predate Phase 2; CI quality workflow is not deployment; Stage 9 changes only documented scope and narrow controller correction. |
| 44 | Final acceptance traces every numbered criterion to concrete code/test/document/live evidence, reports external limitations honestly and leaves commit/push decisions to explicit operator authorization. | SATISFIED | This report §10 exact 44-row reconciliation | Readiness §V unchanged; Stage 1–8 history; §12 fresh evidence; §17 Git restrictions | A complete trace reports failure honestly; it does not require or authorize a closure commit. One mandatory gap remains. |

Totals: **42 SATISFIED; 1 SATISFIED WITH DOCUMENTED LIMITATION; 1 NOT SATISFIED**.
No provisional Stage 7 status remains in this table.

### Criterion 4 — mandatory gap, not an inferred waiver

Exact original requirement:

> REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly.

The official 15-minute-period/MW evidence, empirical 92/96/100 label sequence,
blackout chronology, explicit operator decision and ADR 0006 justify the current
**Stage 2 engineering** product. Exact-value/calendar/failure/replay tests and
Stage 8 ordinary-day compatibility are positive evidence. They do not establish
physical value-to-fold ownership or a provider-authoritative label definition.
The experiment explicitly remained INCONCLUSIVE, and Stage 2 §U states that
matching labels cannot prove which repeated block's values own a fold.

The original wording includes **official/profile evidence**, so official written
confirmation is not the only possible route. But a profile recording the selected
provisional interpretation is not independent evidence that its fold ownership
is correct. Synthetic UTC stepping proves faithful execution of that rule; it
cannot settle the external ambiguity. Nor does an ordinary-day live response
exercise either autumn fold. No averaging interval is claimed, and using
provider_period_value honestly resolves the statistic problem; it does not by
itself resolve timestamp placement/fold ownership.

ADR 0006 expressly supersedes ADR 0005's operational normalization gate, calls
these future refinements rather than ingestion blockers, and permits Stage 2
PASS. The saved operator prompt §26 removes authoritative REN DST/fold/written
confirmation from **Stage 2 PASS** requirements. Critically, the accepted Stage 2
report explicitly says this supersedes the gate **for Stage 2 engineering
acceptance**, and does not assert full Phase 2 closure. Stage 7 retains stronger
criterion 4 for final policy reconciliation; Stage 8 repeats the same unresolved
limits. There is no recorded full-phase replacement of the exact final criterion.

Accordingly **NOT SATISFIED** is required under Stage 9's no-criterion-replacement
rule. The provisional profile remains validly accepted for its declared ingestion
purpose; Stage 9 does not revoke it or strengthen it into official evidence.
**Missing evidence:** source-specific authoritative clarification or sufficiently
independent timestamped official/profile evidence establishing label support and
value ownership across the repeated hour. This is an **external semantic evidence
blocker**, not locally fixable from the retained evidence. A future explicit
full-phase acceptance-policy replacement would be an operator decision; Stage 9
does not invent, request or implement one. No new request is made to obtain it.

### Criterion 5 — accepted with documented unit-field limitation

Stage 3 pinned the official analysis-544 MW/five-minute peninsular forecast
product, with optional unit checks and no guessed numeric catalogue IDs. The
first authenticated response and bounded §24 response both observe indicator
544, Demanda prevista Peninsular, Potencia (20), Cinco minutos (219), Península
(8741). The corrected 0.2.0 profile adds successful bounded normalization and
replay. Safe metadata is retained here with exact code profile/report identity
and linked immutable hashes/history in Stage 8. Synthetic geo 999001 is unchanged.

Neither response supplies a native `unit` field. The authenticated power
magnitude is compatible with the **official product's documented MW unit**
(readiness §F / Stage 3), not new proof of an echoed MW string or a new numeric
unit code. Under the already accepted Stage 3/8 profile, the mandatory intent—
correct identified product, magnitude, unit, geography, native cadence and
forecast meaning—is satisfied through this combined evidence. Missing the
redundant native unit field does not cause ambiguity between selected products
or alter values, and the parser rejects incompatible supplied unit metadata.
Thus **SATISFIED WITH DOCUMENTED LIMITATION**, with no fabricated field claim.
The native-field absence is not used to erase any authentication/coverage failure.

### Criteria 18, 20, 29, 38–40 — remaining special reasoning

- **18:** normal real ESIOS and all three ENTSO-E data requests authenticated
  successfully. Synthetic selected-loading/private-injection/anonymous-independence
  tests plus those HTTP-200 results satisfy verified mechanism; no extra probe.
- **20:** Stage 8 added actual invocation controls, exercised by synthetic
  controller/backend tests and real counters. Stage 6's harness is not promoted
  to production infrastructure. The #21 continuation defect is fixed separately.
- **29:** exact wording requires implemented distinction from successful selected
  coverage, with no bad-row dropping/zero fabrication/undeclared partial output.
  It does **not** demand natural live examples of every error or intentional
  failures. REN/ESIOS unknown or empty shapes fail; ENTSO-E supported exact
  acknowledgements classify no-data/rejection; weather supported error documents
  reject; future targets outside ICON-EU policy fail locally. Offline tests
  establish those distinctions; Stage 8 establishes successful live behavior.
  No live outage/no-data/auth/quota/error was observed or deliberately provoked.
  Unknown future variants remain strict failures, so this limit does not defeat
  the requirement. **SATISFIED**, without claiming universal error recognition.
- **38:** default offline; explicit --live before credential/network construction;
  --replay-only independent; external/fixture/repository root checks; required
  selected credentials, budgets and no CI/pre-commit/pytest live execution.
  Original seven-product command deliberately retains historical ESIOS 0.1.0;
  the separate targeted mode and explicit BoundedEsiosAdapter select 0.2.0.
- **39/40:** seven required products successfully acquired and replayed using final
  accepted profiles across the original run plus authorized corrected ESIOS run.
  The original ESIOS failed parse is retained, not counted as success. These rows
  establish live compatibility, not REN authoritative semantics in #4.

## 11. Documentation acceptance

Current README, architecture and runbook now describe actual implementations,
Stage 8 acceptance, bounded ESIOS 0.2.0 versus historical 0.1.0, whole-run bounds,
private process-environment credentials, exact units/statistics/geographies/time
support, immutable correction/snapshot provenance, safe errors/retry, offline
replay and separate live opt-in. Runbook includes original versus targeted command
semantics, external archive requirements, credential-free replay and operator-local
.env handling without automatic dotenv loading. It preserves original ESIOS history
and marks REN #4 unresolved while retaining Stage 2 engineering acceptance.

Source profiles in §5 and fixture documentation distinguish synthetic IDs from
observed metadata. ESIOS/ENTSO-E fixture README text was corrected for historical
versus completed live evidence; payloads/manifests/hashes remain unchanged.
The ADR index already includes accepted 0006/0007/0008 and needs no change.
No new ADR is warranted by a bug fix enforcing an existing requirement.

No current status text claims complete provider history, guaranteed future
compatibility, production SLA, licensing/commercial clearance or historical
cutoff-safe forecasts. Stage reports retain all PASS WITH GAPS/blocked/failure
history. README remains OPEN/PASS WITH GAPS; no closure date/status is asserted.

## 12. Final regression/quality gates

Fresh executions on the actual Stage 9 tree, using Python 3.12.9 and existing
collection-time network denial. Tests use synthetic credentials/transports and
temporary archives, never real environment files/provider calls/Stage 8 archives.
No skips introduced; no existing test removed or weakened. The strengthened
429 regression adds two parameterized cases to the former 2,320-case full suite.

| Executed gate | Fresh result |
| --- | --- |
| Stage 6 dedicated compatibility regression | **119 passed in 34.20 s** |
| Stage 7 audit/security selection, exact command below | **457 passed in 7.54 s** |
| Complete Stage 8 controller + ESIOS boundary selection | **76 passed in 7.81 s** (51 controller, 25 boundary) |
| All provider-focused unit/integration + bounded ESIOS | **1,189 passed in 14.32 s** |
| Full `python -m pytest` | **2,322 passed in 57.12 s**; zero failures/skips/warnings |
| `ruff check .` | **PASS**, all checks passed |
| `ruff format --check .` | **PASS**, 169 files already formatted |
| `mypy src` | **PASS**, no issues in 61 source files |
| `pre-commit run --all-files` | **PASS**, all eight hooks |
| Explicit pre-commit on all ten changed/new Stage 9 paths | **PASS**, all six applicable hooks; YAML/TOML inapplicable |
| `git diff --check` and explicit new-file whitespace/content review | **PASS** |
| Exact original-criterion/link/prompt checks | **PASS**, 44 verbatim sequential rows, local evidence links resolve, saved prompt wording unchanged |

The full suite was executed as
`env -u ESIOS_API_TOKEN -u ENTSOE_API_TOKEN python -m pytest`, removing both named
credential settings for that process without reading their values. The guard
and test code are unchanged except for the strengthened controller regression.
All gates include the Stage 9 production/test change; final report-only edits
record results and receive the final hooks/diff checks.

Exact focused commands (selections overlap; counts must not be summed):

```bash
python -m pytest tests/integration/stage6 -q
python -m pytest tests/integration/test_phase2_stage7_audit.py tests/unit/test_offline_guard.py tests/unit/ingestion/test_private_requests.py tests/unit/ingestion/test_http.py tests/unit/ingestion/test_stage5_http.py tests/unit/ingestion/test_transport.py tests/unit/ingestion/test_archive.py tests/unit/ingestion/test_stage5_archive.py tests/unit/ingestion/entsoe/test_entsoe_xml_security.py -q
python -m pytest tests/integration/test_phase2_stage8_live.py tests/integration/test_esios_boundary_semantics.py -q
python -m pytest tests/unit/ingestion/omie tests/unit/ingestion/ren tests/unit/ingestion/esios tests/unit/ingestion/entsoe tests/unit/ingestion/weather tests/integration/test_stage3_flow.py tests/integration/test_stage4_omie_flow.py tests/integration/test_stage5_flow.py tests/integration/test_ren_flow.py tests/integration/test_esios_flow.py tests/integration/test_entsoe_flow.py tests/integration/test_open_meteo_flow.py tests/integration/test_esios_boundary_semantics.py -q
```

The provider selection extends the established Stage 7 selection with the
accepted ESIOS boundary suite; controller/ENTSO-E policy is also exercised in
Stage 8 selection. The 457-case security command is the established Stage 7
module selection rerun afresh, not its historical count copied as evidence.

## 13. Remaining limitations and classification

| Limitation | Classification | Why it does / does not prevent final Phase 2 acceptance |
| --- | --- | --- |
| REN authoritative label support and autumn value-to-fold ownership | **Phase 2 blocker (#4)** | Explicit empirical Stage 2 profile is implemented correctly, but retained evidence does not settle the stronger mandatory final requirement. See exact reasoning above. |
| REN exact arithmetic statistic (mean vs instantaneous) | Accepted non-blocking limitation for operational ingestion | ADR 0006 explicitly accepts source-period MW without asserting either statistic or converting to MWh. This does not independently excuse label/fold ambiguity in #4. |
| ESIOS native unit field absent | Accepted non-blocking limitation (#5) | Official selected product documents MW and authenticated magnitude/name/geo/cadence agree. No invented native unit field or scaling. |
| ESIOS provider-wide DST/filtering internals and ambiguous wire boundaries | Future validation concern; accepted non-blocking supported-envelope limitation | Explicit 0.2.0 grid/end-minus-300 rule passes captured half-open window and strict tests; ambiguous wire boundaries are refused, no universal algorithm claimed. |
| Historical forecast vintages | Later-phase data-governance concern | Phase 2 preserves distinct acquisitions/unknown editions as #17 requires; it does not promise reconstruction. Latest ICON-EU is not a historical forecast vintage; ERA5 is not forecast. |
| Historical market-cutoff availability | Later-phase data-governance concern | No cutoff-safe training data claimed or built; future selection must establish actual publication/availability separately. |
| Forecast issue/run/publication times unavailable | Accepted non-blocking limitation; later governance concern | Nullable source times are the explicit #16 requirement; acquisition/document/update times never replace issuance. |
| Future provider schema/model/grid changes, including announced ICON transition | Future validation concern | Supported profiles fail visibly on incompatible changes, original grid/raw identity retained; no future guarantee is required for observed compatibility. |
| Service availability, numeric quotas and natural error variants | Future validation concern | Finite limits, terminal/safe errors and strict unknown-shape failures protect current product; no SLA or exhaustive error catalogue promised. |
| History/correction completeness and earliest supported dates | Accepted non-blocking support-envelope limitation | One-day supported queries and immutable observed revisions are implemented, not bulk history or all-edition retrieval. |
| Licensing/redistribution/attribution | Later-phase data-governance and production-use restriction | Readiness §S expressly distinguishes local engineering from clearance; synthetic fixtures and external real evidence avoid claiming redistribution rights. REN/ESIOS restrictions, ENTSO-E article/owner subset and weather upstream/service notices remain explicit. |
| Production/commercial clearance | Later-phase operational/governance concern | Neither local tests nor live HTTP 200 grants legal/service permission, deployment readiness or a paid subscription. No Phase 2 production-clearance requirement is waived. |
| Trusted filesystem/local archive, managed logging and narrow echo detector | Accepted non-blocking architecture limits | ADRs 0002/0004 define these boundaries; application immutability is not WORM, handlers are managed, credential guard is not general DLP. |

## 14. Phase 2 completion boundary

Engineering capabilities now implemented: provider ingestion foundation;
provider-specific strict normalization; cross-source semantic compatibility;
immutable raw evidence; retrieval/parse provenance; deterministic offline replay;
security/boundedness hardening and controlled live validation. This inventories
implemented work, **not full phase closure**: criterion 4 still blocks it.

Not Phase 2 implementations: Snowflake ingestion, dbt transformations, feature
matrices, cutoff-safe training datasets, ML forecasting/model training, model
registry, scheduled prediction, serving/API/dashboard, cloud deployment, Kafka
or Kubernetes. Read-only baseline-to-HEAD path inspection confirms future
apps/platform/Terraform trees remain .gitkeep skeletons and features/models/
training/inference/monitoring packages are original empty stubs. CI changes are
quality checks only. Runtime dependencies remain HTTPX and Pydantic; no Stage 9
runtime dependency or infrastructure change.

## 15. Phase 3 handoff

The next roadmap stage is **Phase 3 — Snowflake Data Platform**. Available future
prerequisites are typed records/queries, explicit versioned provider semantics,
immutable local raw/retrieval/parse evidence, safe bounded acquisition and
network-free replay. The REN final-acceptance gap must remain visible before
any phase-closure decision. No Phase 3 implementation, plan code/Terraform,
paid-resource action or authorization is produced by this review.

## 16. Files changed

| Path | Purpose |
| --- | --- |
| README.md | Current Phase 2 acceptance/open status, seven products/live/replay and semantic boundaries. |
| docs/architecture/README.md | Actual implemented flow/profiles, bounded controller and unresolved final acceptance. |
| docs/runbooks/README.md | Current operator coverage/status and final report link. |
| docs/runbooks/ingestion.md | Final offline/live/replay instructions, credentials, budgets, ESIOS version distinction, limits/usage/evidence handling. |
| src/iberian_shakti/ingestion/phase2_live.py | Minimal ENTSO-E 429 whole-invocation stop, static safe category. |
| tests/integration/test_phase2_stage8_live.py | Strengthened original 429 regression, parameterized over all three products plus preservation/replay. |
| tests/data/esios/README.md | Synthetic sentinel/history versus observed live metadata and accepted bounded product. |
| tests/data/entsoe/README.md | Synthetic fixtures versus separately accepted live compatibility; rights remain unestablished. |
| docs/codex/prompts/phase_2/phase_2_stage_9_final_acceptance_closure.md | Exact saved prompt. |
| docs/codex/reports/phase_2_final_acceptance_report.md | This complete final acceptance trace and result. |

Only controller code changed; no provider parser/profile, contract/schema,
fixture body/manifest, dependency, CI or archive changes. Existing reports/prompts
and ADRs remain byte-identical to baseline.

## 17. Git status and hygiene

Reviewed `git status`, `git status --short`, `git diff --stat`, `git diff`,
empty cached diff and both complete new files (ordinary git diff omits them).
Tracked diff is eight files, **254 insertions / 106 deletions**, plus the two
new Markdown documents. All ten paths match §16, with no accidental temporary
file, debug dump, raw payload, live manifest or archive in nonignored paths.
A safe static private-key/credential-assignment/private-request pattern check
passed across those ten files. No credential was read or compared; this is
presence/exclusion and authored-content review, not a claim of an active-secret
scan. Fixture payloads/manifests, historical prompts/reports/ADRs and future-phase
skeletons are unchanged from HEAD. No real Stage 8 payload was added anywhere
under repository paths; no payload.bin/stage8-manifest.json is tracked.

`git check-ignore -v .env` returns `.gitignore:84:.env`; `.env` is absent from
`git ls-files` and ordinary status. It remains ignored/untracked and was never
opened, printed or modified. `.gitignore` itself is unchanged. Network-denied
full tests require neither credentials nor real archives.

Exact final `git status --short`:

```text
 M README.md
 M docs/architecture/README.md
 M docs/runbooks/README.md
 M docs/runbooks/ingestion.md
 M src/iberian_shakti/ingestion/phase2_live.py
 M tests/data/entsoe/README.md
 M tests/data/esios/README.md
 M tests/integration/test_phase2_stage8_live.py
?? docs/codex/prompts/phase_2/phase_2_stage_9_final_acceptance_closure.md
?? docs/codex/reports/phase_2_final_acceptance_report.md
```

Branch remains main at e3753ca, 11 commits ahead of locally recorded origin.
All changes are **unstaged**, index unchanged. No provider request, credential
probe/value inspection, cloud action, new branch, staging, commit, push, fetch,
pull, rebase, reset, restore or stash occurred. No real archive was mutated.
No Snowflake/dbt/features/ML/registry/prediction/serving/dashboard/deployment or
other Phase 3 implementation entered this task. Phase 3 has not started or been
authorized; final commit/push decisions remain with the operator.

## 18. Final verdict

Phase 2 Stage 9 — PASS WITH GAPS.

Phase 2 remains open.

Unresolved mandatory **criterion 4**: “REN's timezone and timestamp support
convention are established by concrete official/profile evidence; ordinary and
both DST profiles normalize without guessed folds or fabricated averaging
intervals. Unsupported profiles fail visibly.” Missing label-support and
value-to-fold evidence is externally blocked; the Stage 2-only provisional
acceptance rule is not an explicit replacement of the final phase criterion.
No provider request or later-phase implementation is authorized to close it.

[adrs]: ../../adr/README.md
[adr6]: ../../adr/0006-ren-provisional-period-semantics.md
[ready]: phase_2_readiness_assessment.md
[s1]: phase_2_stage_1_report.md
[s2]: phase_2_stage_2_ren_report.md
[s3]: phase_2_stage_3_esios_report.md
[s4]: phase_2_stage_4_entsoe_report.md
[s5]: phase_2_stage_5_open_meteo_report.md
[s6]: phase_2_stage_6_cross_source_integration_hardening_report.md
[s7]: phase_2_stage_7_pre_live_engineering_audit_report.md
[s8]: phase_2_stage_8_controlled_live_validation_report.md
[selection]: phase_2_stage_5_forecast_model_selection.md
[runbook]: ../../runbooks/ingestion.md
[readme]: ../../../README.md
[architecture]: ../../architecture/README.md
[queries]: ../../../src/iberian_shakti/contracts/queries.py
[contracts]: ../../../src/iberian_shakti/contracts/ingestion.py
[measurements]: ../../../src/iberian_shakti/contracts/measurements.py
[base]: ../../../src/iberian_shakti/contracts/_base.py
[geography]: ../../../src/iberian_shakti/contracts/geography.py
[market]: ../../../src/iberian_shakti/contracts/market.py
[ren-profile]: ../../../src/iberian_shakti/ingestion/ren/profile.py
[ren-parser]: ../../../src/iberian_shakti/ingestion/ren/parser.py
[ren-schema]: ../../../src/iberian_shakti/ingestion/ren/schema.py
[esios-profile]: ../../../src/iberian_shakti/ingestion/esios/profile.py
[esios-parser]: ../../../src/iberian_shakti/ingestion/esios/parser.py
[esios-schema]: ../../../src/iberian_shakti/ingestion/esios/schema.py
[entsoe-profile]: ../../../src/iberian_shakti/ingestion/entsoe/profile.py
[entsoe-parser]: ../../../src/iberian_shakti/ingestion/entsoe/parser.py
[entsoe-schema]: ../../../src/iberian_shakti/ingestion/entsoe/schema.py
[ack]: ../../../src/iberian_shakti/ingestion/entsoe/acknowledgement.py
[xml]: ../../../src/iberian_shakti/ingestion/entsoe/xml_boundary.py
[weather-profile]: ../../../src/iberian_shakti/ingestion/weather/profile.py
[weather-parser]: ../../../src/iberian_shakti/ingestion/weather/parser.py
[weather-schema]: ../../../src/iberian_shakti/ingestion/weather/schema.py
[weather-identity]: ../../../src/iberian_shakti/ingestion/weather/identity.py
[omie-identity]: ../../../src/iberian_shakti/ingestion/omie/identity.py
[omie-parser]: ../../../src/iberian_shakti/ingestion/omie/parser.py
[omie-live]: ../../../src/iberian_shakti/ingestion/omie/live_smoke.py
[archive]: ../../../src/iberian_shakti/ingestion/archive.py
[runner]: ../../../src/iberian_shakti/ingestion/runner.py
[replay]: ../../../src/iberian_shakti/ingestion/replay.py
[retrieval]: ../../../src/iberian_shakti/ingestion/retrieval.py
[live]: ../../../src/iberian_shakti/ingestion/phase2_live.py
[budget]: ../../../src/iberian_shakti/ingestion/_live_budget.py
[config]: ../../../src/iberian_shakti/ingestion/config.py
[auth]: ../../../src/iberian_shakti/ingestion/auth.py
[retry]: ../../../src/iberian_shakti/ingestion/retry.py
[http]: ../../../src/iberian_shakti/ingestion/http.py
[transport]: ../../../src/iberian_shakti/ingestion/_http_transport.py
[logging]: ../../../src/iberian_shakti/common/logging.py
[contracts-tests]: ../../../tests/contracts/test_multisource.py
[foundation]: ../../../tests/integration/test_multisource_foundation.py
[s6-semantics]: ../../../tests/integration/stage6/test_semantics.py
[s6-evidence]: ../../../tests/integration/stage6/test_evidence.py
[boundary-tests]: ../../../tests/integration/test_esios_boundary_semantics.py
[live-tests]: ../../../tests/integration/test_phase2_stage8_live.py
[audit-tests]: ../../../tests/integration/test_phase2_stage7_audit.py
[ren-tests]: ../../../tests/unit/ingestion/ren/test_ren_parser.py
[ren-profile-tests]: ../../../tests/unit/ingestion/ren/test_ren_profile.py
[ren-flow]: ../../../tests/integration/test_ren_flow.py
[esios-flow]: ../../../tests/integration/test_esios_flow.py
[entsoe-flow]: ../../../tests/integration/test_entsoe_flow.py
[weather-flow]: ../../../tests/integration/test_open_meteo_flow.py
[icon-tests]: ../../../tests/unit/ingestion/weather/test_icon_eu_forecast.py
[weather-tests]: ../../../tests/unit/ingestion/weather/test_open_meteo_parser.py
[entsoe-tests]: ../../../tests/unit/ingestion/entsoe/test_entsoe_parser.py
[xml-tests]: ../../../tests/unit/ingestion/entsoe/test_entsoe_xml_security.py
[omie-calendar-tests]: ../../../tests/unit/ingestion/omie/test_calendar.py
[archive-tests]: ../../../tests/unit/ingestion/test_stage5_archive.py
[private-tests]: ../../../tests/unit/ingestion/test_private_requests.py
[guard]: ../../../tests/conftest.py
[guard-tests]: ../../../tests/unit/test_offline_guard.py
[ci]: ../../../.github/workflows/ci.yml


## Targeted REN criterion-4 resolution

Continuation date: **2026-11-03**, Europe/Lisbon; existing **main** at committed
**e3753ca34dbb8670138d74887af17a1a5e4f79f1**. This continues Stage 9; it is not a
new phase/stage. All preceding report bytes, classifications and historical
reasoning are preserved. The previous §17 status and §12 gate results are the
original Stage 9 checkpoint; fresh continuation results/status appear below.
The [exact continuation prompt](../prompts/phase_2/phase_2_ren_criterion_4_resolution.md)
was saved first, with a terminal LF and no wording changes. Initial commands
were the required status/stat/diff-check/log inspection. The ten existing dirty
Stage 9 paths were recorded with preservation hashes, not reset or committed.

**Resolution C — evidence remains insufficient. Criterion 4 stays NOT SATISFIED.**
No unrelated classification, provider product/semantics/decision or Stage 8 live
acceptance is reopened. Totals remain **42 SATISFIED; 1 SATISFIED WITH DOCUMENTED
LIMITATION (#5); 1 NOT SATISFIED (#4)**. Phase 2 remains **OPEN / PASS WITH GAPS**.

### Exact question and competing interpretations

> REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly.

The alternatives below were written down in local analysis **before the new
official-documentation search**. Placement and ownership are separate questions:

| Hypothesis | Meaning | Current evidence judgement |
| --- | --- | --- |
| A | Europe/Lisbon label denotes interval start | Accepted provisional 0.2.0 implementation; empirical support, not established provider definition. |
| B | Europe/Lisbon label denotes interval end | Prior blackout comparison conditionally disfavors it, but lacked an independently bound comparison clock/support. Not excluded by a provider specification. |
| C | Label is a provider period identifier without established start/end placement | Cannot be excluded by period wording or chart metadata alone. |
| D | Two repeated autumn blocks have an independently specified chronological fold order | Compatible with source arrays and policy, but no independent REN rule was found. |
| E | Repeated labels/array order do not specify physical value-to-fold ownership sufficiently | Remains a viable explanation of the information available to the parser. |

A/B/C can combine with D/E. A 100-element ordered array supplies source index
but does not itself define the index as chronological physical period numbering.
Renaming a zero-based JSON index a provider period identifier would invent the
missing rule. Smoothness, count, chart renderer behavior and our fold assignment
are not independent evidence.

### A. Existing repository evidence reviewed first

Read the sole readiness §§E/K/V, Stage 2 report including original gate and §U,
the complete REN timing experiment's relevant acquisitions/hypotheses/fold
assessment, Stage 7 §19 row 4 and provider findings, Stage 8 §7, and this original
final acceptance report. Read ADRs 0005/0006, operational profile/parser/schema/
adapter/identity, both REN unit modules and the REN integration/replay suite.
Earlier material remains history, not rewritten as a successful semantic proof.

| Existing evidence | Classification | What it establishes / does not establish |
| --- | --- | --- |
| Official route and fifteen-minute period statement retained in Stage 2 | AUTHORITATIVE DIRECT for endpoint/period; INSUFFICIENT for placement/folds | An actual period is described, but its displayed endpoint and repeat ownership are not specified. |
| Actual ordinary/spring/autumn source-label observations in readiness/Stage 2/experiment | EMPIRICAL PROVIDER OBSERVATION | Ordinary 96, spring 92, autumn 100; repeated 01h sequence. No observed UTC/offset/fold/provider-defined chronological period field. |
| Blackout chronology/comparison | AUTHORITATIVE INDIRECT plus INFERENCE | Independently dated event context and conditional interval-start support. The comparison clock/support prerequisites were unresolved; it cannot prove autumn ownership. |
| ADR 0006 and profile 0.2.0 | IMPLEMENTATION POLICY | Explicit Europe/Lisbon, interval_start, provisional_empirical, ordered folds; not an independent provider convention. |
| Synthetic fixtures, generated physical calendar, normalization/replay tests | IMPLEMENTATION POLICY | Deterministic 92/96/100 support, strict failure and exact values/provenance; not observations of REN physical fold semantics. |
| Stage 8 ordinary live result | EMPIRICAL PROVIDER OBSERVATION | Real compatibility of the accepted provisional profile, not DST exercise or an authoritative label/fold definition. |

The statistic question remains closed for this task: **provider_period_value**
retains reported Decimal MW for a source period, without claiming mean, instant
or energy and without conversion. Honest statistic semantics cannot supply
missing timestamp/fold evidence.

### B. Additional official REN documentation search

The search was limited to the selected production endpoint and its governing
DataHub documentation/technical-publication context. Sixteen targeted search
queries covered exact endpoint identity; Portuguese/English fifteen-minute and
quarter-hour period placement; interval start/end; local/legal time, UTC/timezone;
summer/winter/DST change, repeated hour, 23/25-hour day, chronological order and
period numbering; and DataHub methodology. No other provider/source catalogue,
credential endpoint or additional data API was requested.

The official pages below were inspected on 2026-11-03. Some searches yielded only
already known pages; the final four precise queries returned no results. Search
absence is **not proof that no REN document exists**. PT/EN daily-balance routes
with language/trailing-slash variants timed out in the browser; the official
non-language canonical daily-balance route was readable. Those tooling errors
establish neither data availability nor timestamp semantics.

| Official source inspected | Evidence classification | Source-specific finding and limit |
| --- | --- | --- |
| [REN API instructions, PT](https://datahub.ren.pt/pt/instrucoes-api/) and [EN](https://datahub.ren.pt/en/api-instructions), parameters and electricity daily balance | AUTHORITATIVE DIRECT for selected endpoint/query; INSUFFICIENT for time support | Documents JSON, culture, date and ElectricityProductionBreakdownDaily. No explicit timezone, start/end support or repeated-hour numbering/order found in these instructions. Example data links were not followed. |
| [REN daily balance](https://datahub.ren.pt/eletricidade/balanco-diario), Repartição da Produção note | AUTHORITATIVE DIRECT for quarter-hour period; INSUFFICIENT for endpoint/folds | Associates the represented values with fifteen-minute periods and warns shorter variations are not shown. It does not identify which edge a label denotes or bind either repeated value block to UTC. |
| [REN About](https://datahub.ren.pt/pt/sobre/), electricity footnote | AUTHORITATIVE DIRECT for update cadence; INSUFFICIENT for support | Fifteen-minute data updates are documented. Refresh cadence is not a label-support or fold contract. |
| [REN glossary](https://datahub.ren.pt/pt/glossario/), Consumo/Ponta and relevant terms | AUTHORITATIVE INDIRECT; INSUFFICIENT for this API | General energy-in-period and peak-power definitions do not bind this chart's labels to an interval edge or repeated physical hour. Gas-day terminology was not transferred to electricity. |
| [REN Help](https://datahub.ren.pt/pt/ajuda/) | INSUFFICIENT | Points to glossary/contact routes, with no displayed product-specific period/timezone/fold rule. No contact or message was sent. |
| [REN publications index](https://datahub.ren.pt/pt/publicacoes/), first displayed entries only | AUTHORITATIVE INDIRECT | Identifies the two technical publications below. No catalogue enumeration or historical date search. |
| [Dados Técnicos 2025](https://datahub.ren.pt/media/firlbajn/dados-t%C3%A9cnicos-2025.pdf), electricity production and peak-load sections, printed pp. 6–13 | AUTHORITATIVE INDIRECT; INSUFFICIENT for API mapping | Generation/load context, dated peak annotations and a daily hour axis are present. The inspected electricity sections do not supply an API label-edge or repeated-hour contract; no UTC definition was found in extracted text. The publication is not an offset-bearing export of the selected chart. |
| [Informação Semanal, week 43/2026](https://datahub.ren.pt/media/cxyn4qxh/ren-informa%C3%A7%C3%A3o-semanal-do-sistema-eletroprodutor_2026_43.pdf), p. 1, published 2026-10-29 | AUTHORITATIVE INDIRECT; INSUFFICIENT for fold ownership | Weekly load diagram includes the fallback date 25 October and dated peak annotations. Its published day labels do not identify the two quarter-hour blocks or bind their values to offsets/period numbers. It cannot replace missing API semantics. |

No new **AUTHORITATIVE DIRECT** evidence was found for the remaining label-edge
or autumn value-to-fold questions. General REN authorship, a plotted calendar,
publication date or an energy-system convention without an explicit binding to
this endpoint is not promoted into the missing product contract. No third-party
commentary or other provider supplied a substitute convention.

### C. Existing raw/live REN evidence reviewed after documentation

Read-only inspection used the actual retained Stage 8 REN raw/retrieval objects
and production parser with network operations denied. No archive write/persist
function was called; no parse event was appended. All **five REN archive files**
were SHA-256 checked before/after and remained byte-identical, with unchanged
inventory. Other providers' live bodies/manifests were not opened.

| Retained Stage 8 evidence | Read-only result |
| --- | --- |
| Source day / HTTP / original attempts | 2026-10-24 / 200 / 1 |
| Original bytes / SHA-256 | 28,420 / 65145ea67ba42da8e30a54bff8d262eb11acf18998d8dca4393983134add30db |
| Retrieval UUID | f6150c10-6c67-4bde-a8c7-52f816a55ae2 |
| Labels / series | 96, 00:00–23:45 / 15 selected+ancillary arrays |
| Root structure | xAxis, yAxis, series |
| xAxis structure | title, categories, max, tickInterval |
| Relevant time metadata | No source UTC/offset/fold or provider-defined chronological period-index field |
| Read-only normalization/replay | success, 1,056 records under unchanged 0.2.0; original retrieval reused |
| Archive mutations | Zero payload/retrieval/parse/manifest changes; zero persisted parse events |

`xAxis.max` is a presentation count and `tickInterval` a chart setting; neither
is an independently defined per-value period number. Series metadata comprises
names/type/parallel values and declared inert styling fields. No annotation
changes the ordinary-day result into DST evidence.

Prior real transition evidence already exists in repository history:

| Prior observation, from original reports | Recorded bytes/hash | Relevant structure / current evidence availability |
| --- | --- | --- |
| Spring 2025-03-30, experiment A03 | 27,636; 8f85882839bfc6649e76e44cb7db7508295738d2ec6c3f26c7a2ae1c9ad5ce6e | 92 labels; 00:45 followed by 02:00, no local 01h. Historical report retained; original experiment root absent in this session. |
| Autumn 2025-10-26, experiment A04 | 29,586; b96725785e3a476626fa57d2f0b503940cbcd5f9bd472b84c9385b143ecfff34 | 100 labels; two successive 01:00/01:15/01:30/01:45 blocks before 02:00. No UTC/fold fields reported; root absent now. |
| Spring 2026-03-29, Stage 2 | 27,579; cb3e36f8741da7f35d1792431b637707bd54de4ab9ccba6cbda98cbd18ee5a34 | 92 labels; original Stage 2 report retained; source-evidence root absent now. |
| Autumn 2026-10-25, readiness | 29,466; d7c9e0b184dd0233d4cedaad53442bdae79c9b8d26bfce9aec2ec6f90f18ae5a | 100 labels, repeated local 01h; readiness report retained; observation root absent now. |

The absent roots are `/tmp/iberian-shakti-ren-eredes-time-experiment`,
`/tmp/iberian-shakti-ren-stage2-evidence` and
`/tmp/iberian-shakti-phase2-observations`. Their historical reported observations
were reviewed, but their raw bodies were **not independently reloaded in this
continuation**. No missing evidence was recreated or refetched. This does not
reopen the separately retained Stage 8 accepted ordinary acquisition or any other
criterion. Neither earlier experiment claimed to settle physical fold ownership.

### D. Optional autumn request decision

**No new REN data acquisition was necessary or justified: 0 logical requests,
0 HTTP data attempts, 0 new provider-body bytes.** Official documentation/PDF
reads above are reference research, not another logical endpoint acquisition.
No autumn date was selected for a new request and no spring request occurred.

The predeclared material test required an independent REN UTC/offset field,
defined chronological period index or source-bound repeated-hour rule. None was
found in documentation or existing chart structure. Existing history already
contains two real autumn dates with the same unresolved label-only representation.
Refetching the fixed chart schema merely to obtain another 100-row response
cannot establish which values belong to the earlier/later physical hour.
No broader query, undocumented endpoint/metadata probe, date search or fallback
is introduced. The conditional one-request authorization is unused, not converted
into unconditional permission or a reason to poll for changed schema.

The decisive information limitation is reproducible offline: exchange the two
four-value autumn blocks while preserving their identical labels. Both documents
remain structurally/calendar-valid under profile 0.2.0. Our parser assigns the
same provisional physical supports in either case. Thus source-label equality
alone cannot tell whether physical value ownership was correct; only external
semantics could choose. This is **INFERENCE from the available representation**,
not evidence that REN actually exchanges blocks or uses interval-end semantics.

### E. Production, ADR and regression decisions

No production code, profile/parser version, semantic-evidence status or ADR was
changed. Keep **0.2.0 / Europe/Lisbon / 15 min / interval_start /
provider_period_value / provisional_empirical** and all eleven selected concepts.
No evidence justifies either proving this policy or changing it to another one.
The existing Stage 9 ENTSO-E 429 correction and its regressions are preserved.
README/architecture/runbook status remains OPEN / PASS WITH GAPS.

`tests/unit/ingestion/ren/test_ren_parser.py` gained one permanent synthetic
regression, `test_autumn_chart_labels_cannot_establish_physical_value_to_fold_ownership`.
It exchanges distinguishable invented value blocks, retains identical repeated
labels, validates both responses, compares unchanged support assignments and
swapped values, and requires the profile to remain honestly provisional. It
neither treats JSON order as provider proof nor adds real payload fixtures.

The existing ordinary/spring/autumn/leap/year matrix now explicitly asserts UTC
support offsets, contiguous intervals and independently converted next-midnight
coverage in addition to the existing counts, exact 15-minute duration, unique
UTC starts, source label/value mapping and provider-period statistic. The fold
assertion is explicitly annotated as synthetic policy evidence.

| Time/profile case | Permanent test evidence | Scope of conclusion |
| --- | --- | --- |
| Ordinary 96 / spring 92 / autumn 100 | test_physical_days_normalize_without_claiming_averaging | Positive half-open UTC support, 900-second durations, complete physical-day coverage, no missing/duplicate physical interval or fabricated mean; deterministic policy mapping. |
| Autumn fold blocks | Same test and new block-exchange regression | Policy assigns first/second block to fold 0/1; actual provider ownership remains unproved. |
| Unexpected count / missing block / wrong local-day count | test_incomplete_day_fails_even_when_all_arrays_align; test_unexpected_order_or_fold_sequence_fails_without_partial_records | Atomic content failure, zero records. |
| Wrong cadence / invalid local time | Synthetic invalid-label fixture, schema quarter-hour HH:MM validation, test_synthetic_fixture_outcomes | Unsupported clock labels fail visibly, not repaired. |
| Duplicate / misordered / unsupported repeat layout | Existing reorder/duplicate/fold_removed/fold_interleaved cases | Entire parse fails; no sorting, filling, deduplication or guessed alternate layout. |
| Missing selected concepts / malformed ancillary values | Existing fixture inventory and bad-unselected-values test | Zero selected success from incomplete/invalid response. |
| Archive/replay ordinary/spring/autumn | Existing REN actual-component integration and legacy-history tests | Immutable acquisition/raw/query linkage and deterministic replay under the explicit empirical version. |

### F. Fresh continuation validation

| Fresh continuation gate | Result |
| --- | --- |
| REN unit `python -m pytest tests/unit/ingestion/ren -q` | **97 passed in 1.14 s** |
| REN integration `python -m pytest tests/integration/test_ren_flow.py -q` | **47 passed in 3.20 s**; combined REN **144** |
| Stage 6 cross-source compatibility | **119 passed in 33.92 s** |
| Established Stage 7 security selection | **457 passed in 7.60 s** |
| Complete Stage 8 offline controller/boundary selection | **76 passed in 8.16 s** |
| Provider-focused regression including bounded ESIOS | **1,190 passed in 11.80 s** |
| Credential-unset full pytest | **2,323 passed in 56.19 s**, zero failures/skips/warnings |
| Ruff check | **PASS** |
| Ruff format check | **PASS**, 170 files already formatted |
| mypy | **PASS**, 61 source files |
| `pre-commit run --all-files` | **PASS**, all eight hooks |
| Explicit hooks on all 12 changed/new paths | **PASS**, all six applicable hooks; YAML/TOML inapplicable |
| `git diff --check`, untracked-file whitespace/content checks | **PASS** |
| Original criterion text/classification and Stage 9 preservation checks | **PASS** |

The first draft of the new ambiguity regression failed in REN/provider runs
because the existing fixture deliberately uses constant values; exchanging equal
blocks cannot demonstrate distinguishable ownership. The generated in-memory
setup was corrected to give Consumption two distinct invented blocks. REN and
provider selections were rerun successfully above, followed by the full suite.
Fixture bytes and existing assertions were not weakened or altered. This was a
new test-setup correction, not a discovered production semantic defect.

Exact commands are the original §12 Stage 6, Stage 7 security, Stage 8 offline
and provider-focused selections, plus the following REN/full/static invocations.
The provider-focused selection includes the changed REN unit directory.

```bash
python -m pytest tests/unit/ingestion/ren -q
python -m pytest tests/integration/test_ren_flow.py -q
python -m pytest tests/integration/stage6 -q
python -m pytest tests/integration/test_phase2_stage7_audit.py tests/unit/test_offline_guard.py tests/unit/ingestion/test_private_requests.py tests/unit/ingestion/test_http.py tests/unit/ingestion/test_stage5_http.py tests/unit/ingestion/test_transport.py tests/unit/ingestion/test_archive.py tests/unit/ingestion/test_stage5_archive.py tests/unit/ingestion/entsoe/test_entsoe_xml_security.py -q
python -m pytest tests/integration/test_phase2_stage8_live.py tests/integration/test_esios_boundary_semantics.py -q
python -m pytest tests/unit/ingestion/omie tests/unit/ingestion/ren tests/unit/ingestion/esios tests/unit/ingestion/entsoe tests/unit/ingestion/weather tests/integration/test_stage3_flow.py tests/integration/test_stage4_omie_flow.py tests/integration/test_stage5_flow.py tests/integration/test_ren_flow.py tests/integration/test_esios_flow.py tests/integration/test_entsoe_flow.py tests/integration/test_open_meteo_flow.py tests/integration/test_esios_boundary_semantics.py -q
env -u ESIOS_API_TOKEN -u ENTSOE_API_TOKEN python -m pytest
ruff check .
ruff format --check .
mypy src
pre-commit run --all-files
git diff --check
```

All pytest runs retain the existing collection-time network denial, synthetic
credentials and temporary test archives. No tests depend on real bodies, local
Stage 8 paths, documentation-network access or the missing experiment directory.

### G. Preservation, hygiene and final Git review

Continuation changes exactly three paths relative to its initial dirty tree:
this report (append-only continuation), the new saved criterion-4 prompt and
`tests/unit/ingestion/ren/test_ren_parser.py` (46 added lines). The other nine
pre-existing Stage 9 files are byte-identical to the initial preservation hashes;
the complete original acceptance report is retained as an exact byte prefix.
No previous prompt, Stage 2/7/8 report, ADR, production module, profile, fixture
body/manifest, dependency or other provider test was changed by the continuation.

Reviewed required short status/stat/full diff/empty cached diff; the full tracked
diff was retained only in external temporary analysis and its new REN change
inspected explicitly. All three untracked documents were checked explicitly:
the new prompt matches the received text with terminal LF, the original Stage 9
prompt hash is unchanged, and the final report preserves its original prefix
and appends this resolution. Original 44 criterion texts and all classifications
are unchanged, including #5's accepted documented limitation.

`git check-ignore -v .env` still reports `.gitignore:84:.env`; no tracked .env or
staged change exists. `.env` was never opened, credentials were not read/probed,
and the full test process explicitly unsets both selected token variables.
Static private-key/credential-assignment/private-request pattern checks and
expected-file inventory checks passed on all 12 changed/new paths without reading
secret values. No real live payload, live manifest, downloaded PDF or temporary
analysis dump entered repository changes. No existing live archive was modified.

Exact final `git status --short`:

```text
 M README.md
 M docs/architecture/README.md
 M docs/runbooks/README.md
 M docs/runbooks/ingestion.md
 M src/iberian_shakti/ingestion/phase2_live.py
 M tests/data/entsoe/README.md
 M tests/data/esios/README.md
 M tests/integration/test_phase2_stage8_live.py
 M tests/unit/ingestion/ren/test_ren_parser.py
?? docs/codex/prompts/phase_2/phase_2_ren_criterion_4_resolution.md
?? docs/codex/prompts/phase_2/phase_2_stage_9_final_acceptance_closure.md
?? docs/codex/reports/phase_2_final_acceptance_report.md
```

Tracked stat: **9 files, 300 insertions / 106 deletions**, plus the three
untracked Markdown paths. All work remains unstaged on **main** at **e3753ca**,
11 commits ahead of locally recorded origin. No branch, staging, commit, push,
fetch, pull, rebase, reset, restore or stash occurred. No new REN or other-provider
logical data request, cloud action or Phase 3 implementation occurred. Official
REN reference research is recorded above and does not grant production clearance.

### H. Final criterion/phase decision

Criterion 4 remains **NOT SATISFIED**, for its exact original wording. No
independently grounded convention now establishes provider timestamp support
and repeated-hour value ownership; ordinary/spring/autumn implementation tests
cannot supply that external evidence. Direct API/period documentation and
empirical clock compatibility remain useful but insufficient for that missing
part. No acceptance-policy replacement or speculative semantic correction was
introduced. All other classifications remain intact: **42 SATISFIED; 1 SATISFIED
WITH DOCUMENTED LIMITATION; 1 NOT SATISFIED**. No Phase 3 work is authorized.

REN criterion 4 — NOT SATISFIED.

The remaining ambiguity concerns provider-authoritative
timestamp support and/or autumn repeated-hour value-to-fold
ownership. The available evidence is insufficient to replace
that ambiguity with a non-guessed semantic contract.

No speculative fold assignment or acceptance-policy weakening
was introduced.

Phase 2 Stage 9 — PASS WITH GAPS.

Phase 2 remains open.

No Phase 3 implementation has been started or authorized.


## Operator acceptance-policy resolution for REN criterion 4

Date: **2026-11-03**, Europe/Lisbon. This continues the existing Phase 2 Stage 9
final-acceptance task from dirty **main**, committed HEAD **e3753ca34dbb8670138d74887af17a1a5e4f79f1**.
The operator's [exact authorization](../prompts/phase_2/phase_2_ren_provisional_semantics_phase2_acceptance.md)
was saved before this continuation's documentation edits. [ADR 0009](../../adr/0009-ren-provisional-semantics-phase2-acceptance.md)
records the decision durably and the ADR index includes it. ADR 0006 and all
previous stage reports/prompts remain unchanged. This continuation changes only
ADR/documentation/report files; the earlier Stage 9 production/security fixes
and permanent REN ambiguity regression are preserved.

### Previous result and explicit policy replacement

The previous final classification was **NOT SATISFIED** for criterion 4, with
42 satisfied / 1 satisfied with documented limitation / 1 not satisfied.
The targeted investigation found no independently grounded rule establishing
provider-authoritative interval-edge semantics or physical ownership of the two
repeated autumn-hour value blocks. Official period wording and observed chart
arrays did not resolve that ambiguity. The experiment and later regression
showed why matching labels/array order cannot prove physical value ownership.
No new evidence now settles it; the stronger evidence remains unavailable in
the retained record. The previous failed reasoning is preserved above in full.

The operator explicitly authorizes accepting the existing REN **0.2.0** profile
as sufficient **Phase 2 engineering semantics**, despite that missing proof.
The stronger evidence requirement is therefore **superseded for final Phase 2
acceptance by explicit operator decision**. This is an acceptance-policy
replacement, not a reinterpretation that the original stronger evidence was
present, and not a claim that criterion 4 had previously passed.

The original criterion is still verbatim:

> REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly.

Final classification: **SATISFIED WITH DOCUMENTED LIMITATION**. The implementation
portion is satisfied: the explicit versioned profile normalizes ordinary, spring
and autumn physical-day shapes deterministically, rejects unsupported layouts
and does not fabricate averaging semantics. Provider-authoritative interval-edge
and autumn value-to-fold semantics remain unconfirmed. The operator explicitly
accepts those semantics as provisional for Phase 2 closure. No provider claim is
strengthened, and no provisional status is renamed authoritative.

| Acceptance dimension | Final meaning |
| --- | --- |
| Provider semantics | Timestamp edges and physical repeated-hour value ownership are not fully established. |
| Project implementation semantics | Explicit, deterministic and provisional; profile/parser 0.2.0, Europe/Lisbon, 15-minute cadence, interval_start, provider_period_value, provisional_empirical. |
| Final Phase 2 acceptance | Authorized by the operator under ADR 0009, with criterion 4 SATISFIED WITH DOCUMENTED LIMITATION. |

### Preserved implementation and future handling

The 96 ordinary / 92 spring / 100 autumn period shapes and unsupported layouts
remain permanently tested, including UTC-aware positive half-open support,
15-minute duration, continuity/complete-day coverage, duplicate/misordered and
invalid layouts. The ambiguity regression still demonstrates that source label
order alone does not establish physical value-to-fold ownership. Those tests
prove execution of the project profile; they are not new provider observations.

No parser behavior, profile/parser version, fold assignment, measurement value,
record schema, query identity, archive history or replay semantics changes.
The statistic remains provider_period_value, without a mean/instant/energy claim
or MW-to-MWh conversion. All eleven product selections and ancillary policy stay
unchanged. No production/test/dependency change is introduced in this policy
continuation. No provider request, credential access or live-archive read/write
is performed; retained live/denied-replay acceptance remains intact.

Current README, architecture and both runbook documents record Phase 2
**CLOSED / PASS**, dated 2026-11-03, and prominently retain the REN limitation.
Future feature engineering must not mistake the support/fold policy for provider
authority or infer historical cutoff-safe availability. Future authoritative REN
clarification may justify a new profile/parser version; any semantic correction
must be explicitly versioned. Never silently alter 0.2.0 or rewrite immutable raw,
retrieval/parse provenance or accepted replay history. New versioned parse events
may be appended for a deliberately selected reinterpretation.

Criterion 5 remains **SATISFIED WITH DOCUMENTED LIMITATION** for the documented
ESIOS native-unit-field absence. Its accepted bounded 0.2.0 behavior, metadata,
live result, replay evidence and unit interpretation are unchanged. All other
42 criterion classifications remain SATISFIED. No other provider, selection,
architecture, live-validation result, licensing boundary or future-phase scope
is reopened by this decision.

### Current authoritative 44-criterion reconciliation

This is the current checklist following the explicit operator policy. The
pre-policy 44-row table above remains a historical checkpoint. Every original
criterion number/text is preserved; the only status change is #4. Documentation,
gate and final-trace references are refreshed for current closure; inherited
engineering/live evidence remains valid and the fresh gates below apply.

| # | Original criterion | Final status | Primary evidence | Supporting evidence | Residual limitation |
| --- | --- | --- | --- | --- | --- |
| 1 | Accepted Phase 2 query/measurement/auth/semantic-outcome decisions are recorded in focused ADR(s) before corresponding implementation; Phase 1 ADR history is retained and this report remains the sole readiness assessment. | SATISFIED | [ADRs 0003–0008][adrs]; [Stage 1 §D][s1] | [Stage 2 §U][s2]; [Stage 5 completion][s5]; [Stage 8 §24][s8] | ADRs 0001/0002 and sole readiness unchanged; no new Stage 9 architectural decision. |
| 2 | All four mandatory providers and exactly the minimum products in §C are implemented; any scope change is explicitly approved and traced, never silently removed to obtain acceptance. | SATISFIED | [REN][ren-profile], [ESIOS][esios-profile], [ENTSO-E][entsoe-profile], [weather profiles][weather-profile] | [Stage 6 source matrix][s6]; [Stage 8 §§7–13,24][s8] | Exactly selected products; explicit ICON-EU operator selection, no IFS implementation. |
| 3 | REN's documented daily production endpoint supplies all selected load/generation/import/export series from one acquisition; ancillary series/presentation fields have explicit selection policy, with no double-counted totals. | SATISFIED | [ren/profile.py][ren-profile], [ren/parser.py][ren-parser], [ren/schema.py][ren-schema] | [REN parser tests][ren-tests]; [Stage 8 §7][s8] | Eleven selected/four ancillary series, all arrays validated; time evidence separately assessed in #4. |
| 4 | REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly. | SATISFIED WITH DOCUMENTED LIMITATION | [ADR 0009](../../adr/0009-ren-provisional-semantics-phase2-acceptance.md): explicit final operator acceptance-policy replacement | [REN period/ambiguity regressions][ren-tests]; [ADR 0006][adr6]; [Stage 8 §7][s8]; fresh closure gates below | Implementation portion satisfied: deterministic 92/96/100 physical-day shapes, unsupported-layout rejection, no fabricated averaging. Provider-authoritative interval edges and autumn value-to-fold ownership remain unconfirmed. Operator accepts existing provisional_empirical 0.2.0 for Phase 2 closure; this is policy replacement, not new REN evidence. |
| 5 | ESIOS 544 is verified against official authenticated name/unit/geography/sampling metadata, retained in a versioned catalogue; the peninsular forecast curve is not mislabelled as a complete D-1 forecast or actual load. | SATISFIED WITH DOCUMENTED LIMITATION | [ESIOS profile/schema][esios-profile]; [Stage 8 §§8,24 metadata][s8] | [Readiness §F][ready]; [ESIOS parser][esios-parser]; [boundary regressions][boundary-tests] | No native unit field in either live response. Official selected-product MW plus authenticated Potencia/name/geo/cadence supports pinned MW; 0.2.0 bounded success; see §10. |
| 6 | ENTSO-E implements ES A65/A16 actual total load and PT plus ES A69/A01 renewable forecasts, retaining document/series/process/domain/PSR identity and distinguishing absent technologies from zero output. | SATISFIED | [ENTSO-E profile][entsoe-profile], [schema][entsoe-schema], [parser][entsoe-parser] | [ENTSO-E parser tests][entsoe-tests]; [Stage 8 §§9–11][s8] | Only returned PSRs; ES offshore absent, PT offshore present in captured response. No completeness guarantee. |
| 7 | ENTSO-E namespace/version, Period resolution/position and A01/A03 curve handling are explicitly supported and tested, including multiple periods, constant blocks, missing sections and conflicting overlaps. | SATISFIED | [entsoe/schema.py][entsoe-schema], [xml_boundary.py][xml] | [test_entsoe_parser.py][entsoe-tests] A01/A03, multiple Periods, gaps/overlaps | Strict GL v3/ACK v7 subset, PT15M/PT30M/PT60M; unknown versions fail. |
| 8 | Open-Meteo archive ERA5 and selected-model forecast ingestion support exactly the three initial variables at six versioned sites, preserving requested/returned coordinates, grid/elevation and model identity. | SATISFIED | [Weather profile][weather-profile], [identity][weather-identity], [parser][weather-parser] | [ICON-EU tests][icon-tests]; [Stage 6 six-site matrix][s6]; [Stage 8 §§12–13][s8] | Six sites offline; minimal authorized live smoke uses Lisbon only. Model pinned by query; no required response model echo. |
| 9 | Query contracts carry validated nonsecret product/window/domain/variables/location/model identity and explicit selection semantics; API snapshots do not fabricate numeric OMIE revisions or guaranteed latest versions. | SATISFIED | [contracts/queries.py][queries]; provider identity validators | [test_multisource.py][contracts-tests]; [Stage 6 query tests][s6-semantics]; [boundary-tests][boundary-tests] | API snapshots have no numeric revision/latest-history guarantee. ERA5 legacy bytes retained. |
| 10 | New system/weather record families and parse schema-family versions are strict, frozen and typed; MarketPrice and Phase 1 serialized archive/provenance remain readable and behaviorally compatible. | SATISFIED | [contracts/measurements.py][measurements], [ingestion.py][contracts], [_base.py][base] | [Contract tests][contracts-tests]; [test_multisource_foundation.py][foundation] original_phase1_wire_and_stored_events_replay_without_migration | Explicit versions; old wire events are read without migration. |
| 11 | Geographic roles distinguish country, mainland/system perimeter, bidding zone, control area, EIC and coordinate; native IDs remain available and directed/aggregate interchange are not conflated. | SATISFIED | [contracts/geography.py][geography]; provider profiles | [Stage 6 geography tests][s6-semantics]; [REN profile tests][ren-profile-tests] | Country/system/bidding-zone/coordinate coincidence never implies equivalence; no invented import/export counterparty. |
| 12 | MW, MWh and EUR/MWh remain distinct; system/market decimals have no binary-float intermediate and financial serialization preserves exact decimal values. | SATISFIED | [measurements.py][measurements], [market.py][market]; direct Decimal JSON/XML parsers | [Contract precision/unit tests][contracts-tests]; [Stage 6 unit tests][s6-semantics] | MW provider_period_value cannot become MWh; no binary float intermediate for system/market values. |
| 13 | Scientific weather values are finite floats with explicit verified units, height/statistic and versioned plausibility/missing policy; no clipping or implicit unit conversion occurs. | SATISFIED | [weather/schema.py][weather-schema], [parser.py][weather-parser]; [measurements.py][measurements] | [Weather parser tests][weather-tests]; [Stage 8 §§12–13][s8] | Schema 1.0.0 broad plausibility bounds; null/out-of-profile values fail the selected product atomically, no clipping. |
| 14 | Every normalized time is UTC-aware; instant samples, positive half-open intervals, source cadence and weather preceding-hour support remain distinct and query boundary handling is tested. | SATISFIED | [Measurement timing][measurements], [queries][queries]; provider parsers | [Stage 6 support tests][s6-semantics]; [ESIOS exclusive-boundary tests][boundary-tests] | REN empirical support is qualified by #4. Radiation at midnight retains preceding-day interval. |
| 15 | Ordinary/leap/year boundaries, spring/autumn DST, duplicate local labels and UTC/local-day crossings are covered where applicable; GMT weather days are not forced to local 23/25-hour counts. | SATISFIED | [REN period tests][ren-tests]; [OMIE calendar tests][omie-calendar-tests]; [boundary tests][boundary-tests] | [ICON-EU calendar tests][icon-tests]; [Stage 6 independent_calendars_coexist_at_dst_and_midnight][s6-semantics] | DST synthetic tests establish implementation policy, not unseen provider observations; weather always 24 UTC samples. |
| 16 | Actual, forecast and reanalysis kind is explicit; issue/publication/update/acquisition times remain distinct and unknown source times/horizons stay null. | SATISFIED | [ValueKind/SourceTimes][measurements]; provider parsers | [Stage 6 unknown_source_times_and_native_update_metadata_remain_separate][s6-semantics]; [Stage 8 §§8–13,24][s8] | Unknown issue/run/publication/horizon remains null as required; update/document creation is not issuance. |
| 17 | Multiple known forecast editions and unknown-edition acquisition snapshots for the same target survive distinctly; historical refetches are never declared known at an earlier market cutoff without evidence. | SATISFIED | [Measurement business_identity][measurements]; [immutable archive][archive] | [Contract edition tests][contracts-tests]; [Stage 6 latest_forecast_cannot_establish_an_old_market_cutoff][s6-semantics]; provider correction tests | Requirement explicitly preserves unknown editions and forbids old-cutoff claims; historical reconstruction is not required or implemented. |
| 18 | Source-selected credentials use ESIOS_API_TOKEN and ENTSOE_API_TOKEN, validated before I/O and injected privately using the verified mechanism; anonymous providers and OMIE need neither credential. | SATISFIED | [Selected credential loader][config], [private auth][auth]; provider adapters | [Private request tests][private-tests]; [Stage 8 §6,24 real authenticated HTTP 200][s8] | ESIOS x-api-key; ENTSO-E securityToken privately. No Stage 9 probe or credential access. |
| 19 | Authentication/authorization failures are terminal, safely diagnosed and tested; there is no pasted-secret workflow, implicit dotenv load, auto-registration or token-refresh/probing loop. | SATISFIED | [config.py][config], [auth.py][auth], [http.py][http] | [Private request tests][private-tests]; [Stage 7 §5][s7]; [runbook][runbook] | Terminal synthetic 401/403; no implicit dotenv, registration, refresh or secret-pasting workflow. |
| 20 | Every external call uses finite phase/attempt/operation budgets, response caps, verified TLS, zero redirects and no hidden transport retries; whole-invocation query/attempt/byte/time caps are enforced. | SATISFIED | [http.py][http], [_http_transport.py][transport], [_live_budget.py][budget], [phase2_live.py][live] | [Stage 7 §6][s7]; [Stage 8 controller tests][live-tests]; [Stage 8 §17,24 accounting][s8] | Production Stage 8 caps include failed/retried body and conservative inbound bytes; Stage 6 plan remains test-only. |
| 21 | Retry policy has at most three attempts by default with bounded backoff, permanent/content/no-data failures do not retry, Retry-After is never shortened and ENTSO-E token bans end the invocation. | SATISFIED | [retry.py][retry], [http.py][http], [Stage 9 controller correction][live] | [Stage 7 composed budgets][audit-tests]; [three ENTSO-E 429 invocation regressions][live-tests]; §9 below | Stage 9 fixed continuing after ENTSO-E 429. All later selections now remain not_executed; prior evidence replayable. No live 429 claimed. |
| 22 | Selected query/record/JSON/XML bounds are implemented and documented; unexpected pagination/truncation/ZIP/content coding gives explicit coverage or unsupported failure rather than partial success. | SATISFIED | [Provider profiles][ren-profile], [ENTSO-E XML][xml], [weather schema][weather-schema]; [OMIE parser][omie-parser] | [Stage 7 §§7–8][s7]; [provider parser tests][entsoe-tests]; [controller budget tests][live-tests] | Strict supported envelope, no ZIP/pagination/implicit decoding/partial success; parser caps apply in replay too. |
| 23 | XML cannot resolve external resources or expand DTD/entities; encoding-aware element/depth/text/work safeguards and hostile-payload tests exercise the actual parser boundary, with any added security dependency justified. | SATISFIED | [entsoe/xml_boundary.py][xml] | [test_entsoe_xml_security.py][xml-tests]; [Stage 7 §8][s7] | Expat >=2.6.0; DTD/entity/external access rejected; actual callback work limits; no added dependency. |
| 24 | Original complete safe provider body bytes are archived unchanged before transformation/semantic parsing using reused SHA-256 content addressing and atomic no-replace publication. | SATISFIED | [runner.ingest_resolved][runner]; [archive._publish/persist][archive] | [Stage 6 raw provenance tests][s6-evidence]; all provider flows; [Stage 8 §15,24][s8] | Safe complete representation bytes before transformation; framing not payload; sensitive/interrupted bodies not published. |
| 25 | Independent identical acquisitions reuse content while retaining immutable events; changed bytes under unchanged provider/query/revision keys retain both versions and repeated event IDs remain idempotent. | SATISFIED | [archive.py][archive] | [test_stage5_archive.py][archive-tests]; [Stage 6 identical_and_revised_acquisitions_are_provider_local_and_immutable][s6-evidence] | Content reuse plus immutable independent events; no mutable latest overwrite or fabricated provider revision. |
| 26 | Retrieval provenance retains safe query/locator, acquisition UTC/status/attempts, native revision observations when known, byte/hash/archive linkage; no private request data is persisted. | SATISFIED | [RetrievalProvenance][contracts], [retrieval.py][retrieval], [archive.py][archive] | [Private request tests][private-tests]; [Stage 6 persisted-chain checks][s6-evidence]; [Stage 8 §15,24][s8] | Only safe locators/query and allowlisted observations; unknown native revisions/publication times stay unknown. |
| 27 | Separate parse provenance records parser/schema/catalogue versions and original raw/retrieval linkage; every normalized record links back to that chain and persistence failure prevents success. | SATISFIED | [MeasurementParseProvenance/ParseResult][contracts]; [runner][runner] | [Stage 6 required_persistence_failure_prevents_success_for_every_path][s6-evidence]; [contracts tests][contracts-tests] | Per-record parse/retrieval linkage, explicit parser/catalogue/schema; parse persistence failure prevents return of success. |
| 28 | Complete malformed safe 200 responses and semantic no-data/error documents are preserved with explicit parse/semantic outcomes and zero normalized success; interrupted/oversized responses never masquerade as complete acquisitions. | SATISFIED | [Shared HTTP][http], [runner][runner], provider parsers | [Stage 6 failure chains][s6-evidence]; [ENTSO-E acknowledgement flow tests][entsoe-flow]; [Stage 8 original ESIOS failure][s8] | Safe malformed 200/ACK retained with zero records; incomplete or oversized bodies not complete acquisitions. |
| 29 | Empty/null/missing/unsupported/future/provider-error results are distinguished from successful selected coverage; no bad rows are silently dropped, absent data converted to zero or undeclared partial dataset emitted. | SATISFIED | [REN schema][ren-schema], [ESIOS schema][esios-schema], [ENTSO-E acknowledgements][ack], [weather schema][weather-schema] | [ENTSO-E parser error/no-data tests][entsoe-tests]; [weather error flow tests][weather-flow]; [Stage 6 taxonomy][s6] | Implemented safe distinction required, not deliberate real failures. No natural live errors/no-data observed; unknown shapes fail, never success. See §10. |
| 30 | Provider-specific auth/quota/domain/semantic/schema errors map to controlled typed categories, including ENTSO-E acknowledgement context rather than reason 999 alone; raw error text is never logged. | SATISFIED | [ErrorCode/ParseOutcome][contracts]; [entsoe/acknowledgement.py][ack]; provider parsers | [ENTSO-E exact-context tests][entsoe-tests]; [Stage 7 §14][s7]; [Stage 6 failure isolation][s6-evidence] | Reason 999 alone is insufficient; unknown/mixed text remains controlled rejection, never raw prose logging. |
| 31 | Safe logging/CLI/exception/config/metadata boundaries are tested with synthetic secret-bearing URLs, headers, rejected validation inputs and credential echoes; sensitive raw-body publication is rejected without pretending redaction preserves original bytes. | SATISFIED | [auth.py][auth], [common/logging.py][logging], [config.py][config] | [Stage 7 encoded echo/origin/redirect tests][audit-tests]; [private tests][private-tests]; [Stage 8 safe manifest tests][live-tests] | Narrow active-credential guard with specified reversible encodings; no general DLP/unmanaged-handler guarantee required. |
| 32 | Each selected product replays entirely offline from archived bytes/history plus pinned catalogue metadata, with no name/geo/schema/weather/model network lookup and no fallback acquisition. | SATISFIED | [replay.py][replay]; provider pinned parsers/profiles | [Stage 6 combined_replay_and_full_raw_provenance_without_credentials_or_acquisition][s6-evidence]; [Stage 8 §16,24][s8] | No HTTP/name/geo/schema/model lookup, credentials or fallback; external real archives are not ordinary test dependencies. |
| 33 | Replay verifies hash/linkage and reproduces fixed-version normalized values and identities; only new parse event identity/time may differ and original retrieval history remains unchanged. | SATISFIED | [replay.py][replay], [archive.load/load_retrieval][archive] | [Stage 6 corruption/replay tests][s6-evidence]; [Stage 7 query tampering tests][audit-tests]; [Stage 8 replay digests][s8] | New parse ID/time excluded; raw, original retrieval, query and business fields compared; trusted local metadata, no signature guarantee. |
| 34 | Actual-component mocked integration covers each mandatory product's successful chain, failure chain, correction/duplicate handling and replay through the shared archive/runner. | SATISFIED | [Stage 6 actual-component evidence suite][s6-evidence] | [REN][ren-flow], [ESIOS][esios-flow], [ENTSO-E][entsoe-flow], [weather flow tests][weather-flow] | Synthetic transports, actual shared runner/archive/provider parsers; every selected product/domain and six weather sites. |
| 35 | Small versioned fixtures cover §P's valid/missing/malformed/boundary/time/revision/provider-error cases; manifests protect hashes/inventory, label original/synthetic/mutated evidence and record rights/attribution. | SATISFIED | tests/data/{omie,ren,esios,entsoe,open_meteo,shared_contracts}/manifest.json and README.md | [Provider fixture inventory tests][ren-tests]; [ENTSO-E fixtures][entsoe-tests]; [foundation checksum tests][foundation] | Synthetic/mutated cases clearly labelled; original OMIE inventory preserved; zero Stage 8 payload copies. |
| 36 | Existing OMIE fixtures and meaningful tests are preserved; shared changes pass Phase 1 regression and old-provenance/replay compatibility tests without weakening assertions. | SATISFIED | [OMIE parser/calendar tests][omie-calendar-tests]; [Phase 1 compatibility fixture/test][foundation] | [Stage 6 OMIE coexistence][s6]; §12 provider/full gates | Original OMIE fixture bytes/assertions preserved; Stage 7 independent cap retained. |
| 37 | Repository-wide python -m pytest succeeds with the existing network-denied guard active from collection, without credentials, real providers, subprocess networking or a live-enabling test switch. | SATISFIED | [tests/conftest.py][guard]; [test_offline_guard.py][guard-tests] | §12 fresh full pytest and security selection; [Stage 7 all-provider default-transport denials][audit-tests] | Guard active before collection; synthetic credentials only; no live switch, archive dependency or subprocess network. |
| 38 | Live commands are separate and explicit --live opt-in, refuse before network construction without it, reject fixture archive roots and are absent from pytest/pre-commit/automatic CI execution. | SATISFIED | [phase2_live.run/main/archive_root][live]; [OMIE live_smoke][omie-live] | [Stage 8 no-live/root/denied-replay tests][live-tests]; [boundary default-command test][boundary-tests]; [CI][ci] | Default offline, explicit --live; external archive required; no live invocation in pytest/pre-commit/CI. See runbook original-vs-bounded distinction. |
| 39 | Controlled live validation records successful data through implemented retrieval/archive/parser paths for REN, ESIOS 544, ENTSO-E ES actual plus PT/ES forecasts, and Open-Meteo archive plus forecast; unavailability/auth failure is never counted as success. | SATISFIED | [Stage 8 §§5,7–13,24 successful real acquisitions][s8] | §7 below; [production composition][runner]; [versioned parsers/profiles][esios-parser] | Seven required successful products total 1,848 records; original ESIOS failure is separate; REN operational acceptance does not satisfy #4 authority. |
| 40 | The actual live acquisitions in criterion 39 have retained safe checksums/query/provenance/outcomes and successful subsequent network-denied replay; request/attempt totals and deviations from §Q are explained. | SATISFIED | [Stage 8 §§15–17,24 safe provenance and denied replay][s8] | §§7–8 below; [controller replay tests][live-tests]; [boundary replay tests][boundary-tests] | Original 7 requests + separately authorized corrected ESIOS 1; 8 total attempts, zero retries/metadata calls; external evidence unchanged by Stage 9. |
| 41 | Source catalogues/runbooks/README/architecture status describe implemented scope, limits, units/time/forecast semantics, credentials, errors, revisions, replay, live opt-in and attribution/licensing boundaries without claiming production clearance or complete history. | SATISFIED | [README][readme], [architecture][architecture], [runbook][runbook], [ADR index][adrs] | §11 current-document acceptance; §4 matrix, §5 exact inventory, §13 limitations; versioned provider code profiles | Current documents record CLOSED / PASS by explicit operator policy and prominently retain REN/ESIOS limitations; no production/commercial/history guarantee. Earlier open verdicts remain historical. |
| 42 | Final Python 3.12 ruff check ., ruff format --check ., mypy src, python -m pytest, git diff --check and applicable pre-commit checks pass; full new/staged/unstaged diff and Git status are reviewed. | SATISFIED | [Fresh closure validation](#fresh-closure-validation), Python 3.12.9, on the operator-policy closure tree | [Final closure Git review](#final-closure-git-review); original §12 gates retained as history | No staging/commit/push; gate results recorded only after execution. |
| 43 | No Snowflake/dbt/features/ML/registry/inference/API/dashboard/deployment/Kafka/Kubernetes implementation, paid-resource change, bulk download or unnecessary runtime dependency enters Phase 2. | SATISFIED | §14 scope review; baseline-to-HEAD path diff a4191a3..e3753ca | Unchanged pyproject.toml runtime dependencies; empty future-package __init__.py and .gitkeep trees | Future skeletons predate Phase 2; CI quality workflow is not deployment; Stage 9 changes only documented scope and narrow controller correction. |
| 44 | Final acceptance traces every numbered criterion to concrete code/test/document/live evidence, reports external limitations honestly and leaves commit/push decisions to explicit operator authorization. | SATISFIED | [Current authoritative checklist](#current-authoritative-44-criterion-reconciliation) and explicit ADR 0009 policy trace | Original readiness/stage history preserved; fresh closure gates and final Git review below | Complete current 44-row trace, 42/2/0 totals, explicit policy replacement and immutable history. Commit/push remain operator decisions. |

Final totals: **42 SATISFIED; 2 SATISFIED WITH DOCUMENTED LIMITATION; 0 NOT SATISFIED**.
The two documented limitations are #4 REN provisional support/fold semantics
and #5 ESIOS native-unit-field absence. No criterion text is silently weakened
or omitted; #4's acceptance-policy replacement is explicit and separately traced.

### Fresh closure validation

All required gates passed freshly on the operator-policy closure tree, using
Python **3.12.9**. This documentation-only continuation changes no production or
test code; the prior Stage 9 fixes/regressions remain present. Final report-only
edits record these results and receive final hooks/diff checks.

| Fresh gate | Result |
| --- | --- |
| REN unit | **97 passed in 4.54 s** |
| REN integration | **47 passed in 4.54 s**; combined REN **144** |
| Stage 6 cross-source | **119 passed in 34.79 s** |
| Established Stage 7 security selection | **457 passed in 6.38 s** |
| Stage 8 offline controller + ESIOS boundary | **76 passed in 8.73 s** |
| Provider-focused regression | **1,190 passed in 15.41 s** |
| Credential-unset full pytest | **2,323 passed in 56.32 s**, zero failures/skips/warnings |
| `ruff check .` | **PASS**, all checks passed |
| `ruff format --check .` | **PASS**, 172 files already formatted |
| `mypy src` | **PASS**, 61 source files |
| `pre-commit run --all-files` | **PASS**, all eight hooks |
| Explicit hooks on the eight policy-continuation paths | **PASS**, all four applicable Markdown hooks; Python/YAML/TOML inapplicable |
| `git diff --check` plus explicit untracked whitespace/content checks | **PASS** |
| Current 44-row text/status/link checks and historical preservation | **PASS**, exact criterion text, only #4 status changes, 42/2/0 totals |

The Markdown hooks normalized trailing hard-break whitespace in the newly saved
operator prompt; its substantive wording is unchanged and checked against the
received authorization. No prior prompt/history, code or fixture was altered by
that normalization.

Exact focused commands are retained in the preceding targeted-resolution
validation section and rerun afresh for this policy continuation: REN unit and
integration separately; Stage 6; established nine-module Stage 7 security;
Stage 8 controller plus ESIOS boundary; and the established provider-focused
selection including all five provider unit directories, OMIE Stage 3/4/5 and
REN/ESIOS/ENTSO-E/weather flows plus bounded ESIOS tests. The full command is
`env -u ESIOS_API_TOKEN -u ENTSOE_API_TOKEN python -m pytest`. Both token settings
are unset for that process without reading their values. All pytest runs retain
collection-time network denial, synthetic credentials and temporary test archives.
No real provider/credential/Stage 8 archive is a test dependency.

### Final closure Git review

The policy continuation changes eight documentation paths: new ADR 0009,
ADR index, README, architecture README, both runbook documents, saved operator
acceptance prompt, and appended/current-status portions of this final report.
All existing code/tests and prior prompts are byte-identical to their initial
continuation hashes. ADR 0006 and earlier reports remain unchanged. The entire
pre-policy acceptance report is preserved verbatim between the new current-status
banner and this policy section; it was not rewritten to imply an earlier PASS.

Reviewed `git status --short`, `git diff --stat`, full tracked `git diff`, empty
`git diff --cached`, and all five untracked documents explicitly. Their expected
inventory, complete saved-prompt wording, ADR/policy content, old report history
and current 44-row table were checked. Full tracked diff and temporary preservation
analysis remain outside the repository. Tracked stat is **10 files, 325 insertions /
106 deletions**, plus five untracked Markdown files.

`git check-ignore -v .env` still reports `.gitignore:84:.env`; .env is untracked,
ignored, unopened and unchanged. No credential value was read/probed. Static
private-key/credential-assignment/private-request pattern and file-inventory
checks passed without reading active secrets. No real live payload, private
manifest, downloaded source, live-archive copy or temporary analysis file entered
repository changes. This continuation performed no provider request or live-archive
read/write. Ordinary tests remain independent of live evidence and credentials.

Exact final `git status --short`:

```text
 M README.md
 M docs/adr/README.md
 M docs/architecture/README.md
 M docs/runbooks/README.md
 M docs/runbooks/ingestion.md
 M src/iberian_shakti/ingestion/phase2_live.py
 M tests/data/entsoe/README.md
 M tests/data/esios/README.md
 M tests/integration/test_phase2_stage8_live.py
 M tests/unit/ingestion/ren/test_ren_parser.py
?? docs/adr/0009-ren-provisional-semantics-phase2-acceptance.md
?? docs/codex/prompts/phase_2/phase_2_ren_criterion_4_resolution.md
?? docs/codex/prompts/phase_2/phase_2_ren_provisional_semantics_phase2_acceptance.md
?? docs/codex/prompts/phase_2/phase_2_stage_9_final_acceptance_closure.md
?? docs/codex/reports/phase_2_final_acceptance_report.md
```

Existing **main**, committed HEAD **e3753ca**, remains 11 commits ahead of locally
recorded origin; all work is **unstaged**, index unchanged. No branch, staging,
commit, push, fetch, pull, rebase, reset, restore or stash occurred. No cloud/paid
resource action or later-phase implementation occurred. Phase 3 has not started
or been authorized. Operator review/commit/push decisions remain separate from
this acceptance-policy authorization.

### Final closure decision

The explicit operator policy is durably recorded, all original criterion text
is retained, #4 is accepted only with documented limitation, #5 remains accepted
with its existing limitation, the other 42 classifications remain intact, and all
fresh required gates pass. Phase 2 therefore closes under ADR 0009 on 2026-11-03.
No provider semantics, implementation behavior or historical evidence changed.

Phase 2 Stage 9 — PASS.

Phase 2 — Multi-Source Ingestion Expansion — CLOSED.

Final acceptance reconciles all 44 criteria:
42 SATISFIED,
2 SATISFIED WITH DOCUMENTED LIMITATION,
0 NOT SATISFIED.

REN profile/parser 0.2.0 remains explicitly
provisional_empirical. Provider-authoritative timestamp-edge and
autumn value-to-fold semantics are not claimed established; the
operator has explicitly accepted this limitation for Phase 2.

ESIOS retains its documented native-unit-field limitation.

No provider semantics were fabricated, no historical evidence was
rewritten, and no new live request was required.

No Phase 3 implementation has been started or authorized.
