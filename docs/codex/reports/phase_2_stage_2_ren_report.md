# Phase 2 Stage 2 — REN electricity production integration

Current implementation review: **2026-11-03**, Europe/Lisbon. The explicit
operator decision adopts provisional empirical profile/parser **0.2.0** under
[ADR 0006](../../adr/0006-ren-provisional-period-semantics.md). See **§U** for
the revised behavior, **Stage 2 — PASS** verdict and fresh validation results.

**Historical record:** §§A–T below describe the original 2026-10-28 profile
0.1.0 implementation and semantic continuation. Their PASS WITH GAPS verdict
and authoritative-evidence gate are retained as decision history, superseded
for the revised Stage 2 engineering acceptance rule in §U.

Verification date: **2026-10-28**, Europe/Lisbon. Phase 0 and Phase 1 remain
CLOSED/PASS; Phase 2 remains **in progress**. Stage 2 verdict: **PASS WITH GAPS**.
Authoritative UTC normalization is blocked by the source-time semantic gate.

## A. Objective

Implement only REN DataHub `ElectricityProductionBreakdownDaily`, culture
`en-US`, one source date and one logical acquisition. Explicitly select
Consumption, eight generation technologies, Import and Export. Reuse the Stage 1
API → bounded retrieval → immutable original bytes → acquisition provenance →
strict parser → measurement parse provenance → offline replay chain.

The acquisition, validation and controlled failure chain is implemented.
**No successful REN SystemMeasurement emission is claimed.** The operator's
§12 stop-rather-than-guess rule applies. No other provider, second REN product,
scraper, cloud component or live-smoke command is implemented.

## B. Baseline

Before changes, `git status` and `git log --oneline --decorate -15` confirmed:

- Branch `main`, initial HEAD `8a377dd` — `feat: establish Phase 2 multi-source foundation`.
- Locally recorded `origin/main`/`origin/HEAD`: `a4191a3` — `docs: close Phase 1 OMIE ingestion`.
- Local main two commits ahead: readiness `70f4204`, Stage 1 `8a377dd`.
- Working tree and index clean; no remote fetch or synchronization requirement.
- Python **3.12.9**, existing named pyenv environment **iberian_shakti**.

The previous attempt's dirty-tree precondition is resolved by the committed
Stage 1 baseline. The full original Stage 2 prompt was stored first at
`docs/codex/prompts/phase_2/phase_2_stage_2_ren_integration.md`. Historical Stage 1
prompt/report/ADRs and all existing tests/fixtures remain unchanged. No commit,
push, branch creation or staging was performed.

Continuation baseline (2026-10-28): `main` is still `8a377dd`, two commits ahead
of locally recorded origin. The 43 unstaged changed/new Stage 2 paths from the
previous execution are expected and preserved. This focused semantic continuation
changes only this existing report; it does not restart Stage 2 or require the
operator to commit the incomplete stage. Its test baseline is 1,281 passing cases.

## C. Authoritative inputs

- Sole [Phase 2 readiness assessment](phase_2_readiness_assessment.md), especially
  §§C–E/K/M/P/Q/U/V; no replacement assessment was created.
- Accepted [Stage 1 report](phase_2_stage_1_report.md).
- [ADR 0001](../../adr/0001-omie-day-ahead-source-and-market-price-contract.md),
  [0002](../../adr/0002-local-ingestion-immutable-archive-and-replay.md),
  [0003](../../adr/0003-multi-source-query-and-measurement-contracts.md),
  [0004](../../adr/0004-private-authentication-and-semantic-outcomes.md).
- New [ADR 0005](../../adr/0005-ren-source-profile-and-time-gate.md), written
  before REN code: pinned chart profile, safe versioned query identity,
  explicit unknown timing and zero-record failure policy.
- Repository instructions, actual contracts/shared execution, architecture,
  ingestion runbook and existing offline test/fixture conventions.

## D. REN source verification

Evidence categories are deliberately separate. Verification date: 2026-10-28.

| Category | Evidence and limits |
| --- | --- |
| **Officially documented** | [API instructions](https://datahub.ren.pt/en/api-instructions) identify JSON, the selected production route, culture and ISO date parameters. No authentication mechanism is specified for this public route. |
| **Officially documented** | [DataHub description](https://datahub.ren.pt/en/) describes provisional production from metering/estimates and 15-minute updates. Update cadence does not establish averaging or label placement. |
| **Officially documented** | The [Portuguese daily page](https://datahub.ren.pt/pt/eletricidade/balanco-diario/) describes quarter-hour periods without shorter variations, and Portuguese mainland context. It does not define the API label as start/end/instant or supply offsets. |
| **Officially inspected, insufficient for timing** | [Glossary](https://datahub.ren.pt/en/glossary/) provides general energy/consumption definitions, not this chart's timestamp convention. The inspected API, EN/PT description and daily page contain no sufficient explicit binding of these labels to UTC or a power statistic. Targeted official-domain searches found no additional usable timing reference. This is not proof that clarification exists nowhere. |
| **Directly observed, this stage** | Two sequential, bounded, anonymous selected-product requests: ordinary 2026-10-24 and spring 2026-03-29. Both HTTP 200, one attempt each, 15 series, explicit Hour/MW axes, no date/offset/statistic metadata, 96/92 aligned values with no nulls. |
| **Directly observed, prior assessment** | Retained 2026-10-25 autumn body: 100 aligned labels, repeated 01:00–01:45, 15 series. This stage inspected the retained bytes; it did not refetch autumn. |
| **Inferred/project policy** | The three clock shapes corroborate a Europe/Lisbon-like calendar. This remains inference, not an authorized UTC/timestamp/statistic profile. Bounds, safe query partition and sequential pacing are application policy, not provider quotas. |
| **Unknown** | Contractual timezone, label start/end/instant convention, instantaneous-versus-average statistic, historical profile changes, issue/update times, finalization, retention, corrections and actual missing/future/error variants. No independent timestamped official export binding these chart labels was established. |

Source-profile observations only; **none counts toward Phase 2 criterion 39/40
or Stage 8 controlled live validation**. A first sandbox attempt ended without
HTTP status (`retry_exhausted`, one attempt); the approved bounded execution
then made the two successful requests, with a 1.1-second wait between them.
There was no error probing, crawling, bulk history, polling or other-provider
access. The observation script reused the shared retriever with one attempt,
finite default budgets, identity streaming, verified TLS and a 1 MiB cap.

| Source date | Observation time UTC | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| 2026-10-24 | 2026-10-28 08:33:47 | 28,418 | `0fb902ceba4d61c4949f5f1ca592b69b3bd0c153a386726a621025c1c0951adf` |
| 2026-03-29 | 2026-10-28 08:33:48 | 27,579 | `cb3e36f8741da7f35d1792431b637707bd54de4ab9ccba6cbda98cbd18ee5a34` |
| 2026-10-25 | Prior assessment, 2026-10-27 | 29,466 | `d7c9e0b184dd0233d4cedaad53442bdae79c9b8d26bfce9aec2ec6f90f18ae5a` |

Real bodies remain only in `/tmp/iberian-shakti-ren-stage2-evidence/` and the
prior assessment's `/tmp/iberian-shakti-phase2-observations/`. These paths are
local temporary evidence, not durable repository fixtures or archive history.

### Focused semantic continuation — 2026-10-28

The operator requested independent answers for timezone, label placement, power
statistic and DST. The additional investigation followed the evidence priority:
API instructions → relevant official technical/publication material → official
help/glossary → independently dated official diagrams. The following are **D —
officially documented** facts, with their applicability limits kept explicit.
Only official REN pages/documents were opened and relied on; unrelated search
results were not adopted as evidence.

| Official source inspected | D — fact established | U — missing binding for the selected API |
| --- | --- | --- |
| [Portuguese API instructions](https://datahub.ren.pt/pt/instrucoes-api/) and [English instructions](https://datahub.ren.pt/en/api-instructions), parameters and electricity daily balance sections | JSON, culture/date inputs and the selected production route. | No timezone, HH:MM placement, MW statistic or DST sequence/fold contract is supplied. |
| [Portuguese daily balance](https://datahub.ren.pt/pt/eletricidade/balanco-diario/), Repartição da Produção note | Represented values concern 15-minute periods and do not show shorter variations. | A period description does not state arithmetic averaging or whether its label is its start/end. It does not authorize an instant fallback either. |
| [Portuguese About](https://datahub.ren.pt/pt/sobre/), final footnote | Electricity information is updated every 15 minutes. | Refresh frequency does not define the observation statistic or timestamp. |
| [Portuguese glossary](https://datahub.ren.pt/pt/glossario/), Consumo and Ponta | General consumption-in-a-period and maximum-power definitions. | Neither defines the production chart's MW values or offset-free labels. A peak definition cannot classify every chart point. |
| [Portuguese Help](https://datahub.ren.pt/pt/ajuda/) | Directs terminology questions to the glossary and other questions to REN's contact route. | No additional API-specific time/export manual was provided in the inspected help text. No contact/message was sent. |
| [Dados Técnicos 2025](https://datahub.ren.pt/media/firlbajn/dados-t%C3%A9cnicos-2025.pdf), printed pp. 4–5 and 10–11 (PDF pages 3 and 6), especially the annual-peak-day load diagram | Official dated consumption/generation material, MW diagrams, date/time peak annotations and an hour axis. | No explicit timezone, timestamp placement, integration/averaging definition or mapping to ElectricityProductionBreakdownDaily was established in these sections. Date/clock annotations are not independent UTC timestamps. |
| [Weekly electricity-system bulletin, week 42/2026](https://datahub.ren.pt/media/dutei1up/ren-informa%C3%A7%C3%A3o-semanal-do-sistema-eletroprodutor_2026_42.pdf), pp. 1–2, published 2026-10-22 | Dated load diagrams, MW maxima with day/month/hour annotations, daily energy tables and provisional-status notice. | The publication date is not a measurement UTC offset. No API label/statistic/fold convention or independently offset-timestamped equivalent series was established. |

The two PDFs were followed directly from the official
[publication catalogue](https://datahub.ren.pt/pt/publicacoes/), without paging
through history. Their dated charts are useful context, but not an authoritative
API/export schema. Targeted searches covered the selected product/DataHub with
Portuguese and English timezone, civil/legal hour, UTC/GMT, instantaneous/mean
power, quarter-hour, methodology/manual and export/load-diagram terms. They did
not locate a usable REN definition binding all required semantics to this route.
This bounded search is **not proof that REN has no such documentation**.

**O — directly observed:** this continuation made **zero selected-product/API
requests** and created no new provider-body observation. The original 96/92/100
observations remain the only direct clock-shape evidence used. No new body,
PDF or screenshot was placed in Git. No third-party interpretation, client
JavaScript/chart alignment or other provider was used to fill the gap.

**I — inferred/project policy:** Lisbon civil time remains a corroborated
candidate, not an established source convention. Neither those clock shapes nor
the independently dated diagrams identify interval placement, averaging or fold
identity. More daily observations without semantic metadata would repeat the
same uncertainty, so no additional data request was justified.

**U — unknown / decision:** all four authoritative answers remain unresolved
for this API. Preserve profile/parser/catalogue `0.1.0`, all existing selected
mappings and all failure protections. No new profile/version, calendar,
SystemMeasurement construction, positive normalization fixture or success claim
is introduced. Retain **PASS WITH GAPS** and the `time_semantics_unknown` gate.

## E. Product/query profile

- Source `ren`; sole product `ElectricityProductionBreakdownDaily`.
- Fixed HTTPS origin `https://servicebus.ren.pt`; fixed path
  `/datahubapi/electricity/ElectricityProductionBreakdownDaily`.
- Query only `culture=en-US&date=YYYY-MM-DD`, strictly validated source date.
- Profile/parser `0.1.0`; parser ID `ren-production-breakdown`.
- Safe report ID `ElectricityProductionBreakdownDaily.en-US.v0.1.0` explicitly
  carries exact product, culture and profile in the existing canonical query
  identity. This avoids changing shared query contracts or old wire shapes.
- `delivery_date` is source query/archive partition. The requested UTC
  midnight-to-midnight window is **project partition context only**, not a
  statement that REN uses UTC days or that returned support lies within it.
  Authoritative local source-day query boundaries require a later verified profile.
- Query SHA-256 and opaque locator are independent of acquisition time; API
  snapshots have no invented numeric revision. Nonprofile queries fail before I/O.
- One logical request, at most three physical attempts; original body 1 MiB,
  series 32, total numeric values 10,000. No pages, second product or truncation.
- Additional parser work limits: depth 12, nodes 30,000, object keys 64,
  strings 4,096 characters, numeric tokens 128 characters, array work 10,000.
  These limit parsing, not REN's contractual calendar or maximum response size.

## F. Selected/unselected series

All selected mappings use existing Stage 1 measure contracts. Kind is explicitly
`actual`; provisional status comes from the official description. This is the
pinned semantic mapping, **not evidence of emitted normalized records**.

| Native concept | Measure | Technology / direction | Geography |
| --- | --- | --- | --- |
| Consumption | load | — | REN Portuguese system |
| Wind | generation | wind | REN Portuguese system |
| Solar | generation | solar | REN Portuguese system |
| Hydro | generation | hydro | REN Portuguese system |
| Natural Gas | generation | natural_gas | REN Portuguese system |
| Biomass | generation | biomass | REN Portuguese system |
| Other Thermal | generation | other_thermal | REN Portuguese system |
| Coal | generation | coal | REN Portuguese system |
| Wave | generation | wave | REN Portuguese system |
| Import | interchange | import | aggregate external boundary |
| Export | interchange | export | aggregate external boundary |
| Pumping | explicitly unselected | no record | — |
| Consumption + Storage | explicitly unselected | no record | — |
| Consumption of Batteries | explicitly unselected | no record | — |
| Battery Injection | explicitly unselected | no record | — |

The last four are exact observed source names; “Batteries” is an informal concept,
not an accepted alias for an unseen series. All names must be unique; unknown
concepts fail `schema_unsupported`. No first/last occurrence selection, combined
series, renewable share or derived total exists. Unselected arrays still undergo
complete structural/numeric validation. No generic technology enum extension was
needed: Stage 1 GenerationMeasure already accepts bounded technology identifiers.

## G. Time and DST profile

**Verified timezone: not established. Timestamp meaning: unknown. Power statistic:
unknown. Interval/instant representation: deliberately neither emitted.**

| Profile | Evidence | Supported behavior now |
| --- | --- | --- |
| Ordinary | Direct selected-product observation: 96 labels 00:00–23:45 | Complete synthetic shape validated; zero records, `time_semantics_unknown`. |
| Spring | Direct 2026-03-29 observation: 92 labels, 01:00–01:45 absent | Same semantic gate; no guessed UTC mapping. |
| Autumn | Prior 2026-10-25 body: 100 labels, repeated 01:00–01:45 | Repeated labels retained, not deduplicated or assigned guessed folds; same gate. |
| Leap/year boundary | Synthetic 2024-02-29 and 2025-12-31, not observed source evidence | Query date rollover is deterministic; no authoritative calendar success claimed. |
| Inconsistent duplicate labels / incomplete plausible clock | Synthetic shapes | Cannot become normalized success; time gate remains. No inferred calendar count is enforced. |

The continuation answers the four questions independently:

| Question | Conclusion / evidence category | Exact evidence still needed |
| --- | --- | --- |
| A. Timezone | **U** — Europe/Lisbon, UTC or another convention is not authoritatively established for this route. Lisbon remains **I**, corroborated by prior **O** clock shapes. | An official binding between the selected API's source day/labels and its timezone, or a sufficiently timestamped equivalent official representation. |
| B. HH:MM placement | **U** — start, end, instant/sample or another label convention is not established. | An official definition or equivalence that identifies what a label such as 12:15 denotes. |
| C. MW statistic | **U** — instant, quarter-hour mean or another power statistic is not established. | A product-specific measurement/support definition. Fifteen-minute refresh or represented periods alone do not prove a mean. |
| D. DST | **U** — the gap/repeat shapes are observed, but source ordering/fold semantics are not established. | Evidence that labels plus sequence order represent successive physical periods/instants under the declared timezone and timestamp convention. |

Consequently positive ordinary/spring/autumn UTC record counts remain **zero**.
The existing candidate-shape/failure tests pass; no positive normalization,
successful normalized ingestion or normalized-value/business-identity replay
has been claimed. Criteria 3 and 4 remain PARTIALLY ESTABLISHED — LATER EVIDENCE
REQUIRED. See §D's continuation evidence rather than promoting shapes to proof.

No Europe/Madrid reuse, fixed WET/WEST, 15-minute mean fabrication, instant
fallback, runtime timing override or synthetic “success” profile exists.
The Portuguese page's quarter-hour-period statement still leaves label placement
and statistic unresolved. Official clarification or independently timestamped
REN material that binds these labels and statistic is required before adding a
versioned Europe/Lisbon calendar and authoritative ordinary/DST UTC tests.

## H. Parser and normalization

The parser consumes original archived bytes, not MIME or HTML rendering.
UTF-8 decoding, pre-allocation nesting check, duplicate-key rejection, direct
`Decimal` float-token parsing, bounded integers, finite numeric validation and
node/string/collection limits precede strict typed chart validation. Numeric
strings, booleans, nulls, NaN/Infinity, malformed structures and excessive tokens
fail; no float intermediate, clipping, conversion or rounding occurs.

The supported root has exactly `xAxis`, `yAxis`, `series`. Hour and MW titles are
explicit. Every series has a line type, exact name and numeric array; xAxis
category count/max and all array lengths must agree. All eleven selected names
are required; duplicate/unknown concepts and unknown fields fail. Empty coverage
is failure, not successful zero records or invented provider no-data behavior.

Only observed presentation keys (`color`, `zIndex`, `tooltipOptions.style.color`,
`marker.lineColor`, `lineWidth`, plus axis chart fields) are declared irrelevant
and validated as bounded inert data. Unknown presentation fields also fail.
No source string is evaluated/interpolated into code.

Geography is a project-labelled REN Portuguese system, `provider_defined`
perimeter. No source-native area code is supplied in these responses, so native
area ID/scheme remain null; source/product and exact series labels are retained.
Import/export use ExternalBoundary, no Spanish endpoint and no asserted
physical/commercial conversion. MW is not MWh. Typed selection mappings are
implemented, but SystemMeasurement construction is blocked pending §G.

## I. Retrieval/archive/provenance

`RenAdapter.retriever()` returns the real shared HttpRetriever, pinned anonymous
PrivateRequestPolicy and a 1 MiB cap. Existing defaults remain three total
attempts, 1/2-second backoff, 10-second phase, 30-second attempt and 93-second
operation budgets. TLS verification, trust_env=False, identity raw streaming,
zero redirects/transport retries remain inherited. No REN-specific polling or
parallel execution is added; callers pace successive explicit requests at ≥1s.

Real shared `ingest_resolved()` persists original safe complete bytes and
retrieval metadata before invoking RenParser, then persists the measurement
parse event. SHA-256, atomic no-replace publication, safe locators, version-2
acquisition and schema-family parse provenance are reused unchanged. Failed
parse events carry parser/schema/catalogue version, original retrieval UUID,
raw hash/reference, outcome/code and count zero. Archive failure prevents return
of an ingestion result. No shared runtime module or contract was modified.

## J. Correction/republication behavior

The real-component synthetic test executes one query three times: original,
identical original, corrected numeric content. It retains two payload hashes,
three retrieval events and three parse events. Existing files remain unchanged;
repeated event persistence is idempotent. Both changed bodies and all original
acquisition histories replay. No provider revision ID, overwrite/latest pointer
or claim about actual REN correction publication is introduced.

## K. Offline replay

Real LocalRawArchive/replay verify byte hash and original retrieval linkage;
RenParser uses only bytes, query metadata and pinned local code/profile.
Tests disable retrieval additionally to the repository network guard. Every
fixture reproduces its exact failure/code, zero records and normalized-content
identity while only parse UUID/time changes. Original retrieval/payload/events
remain unchanged. Corruption and wrong acquisition linkage fail without refetch.

**Successful normalized value/business-identity replay is not established:** no
REN normalized records can be emitted until the timing gate is resolved. The
actual-component success chain required by original §32 therefore remains a gap;
these are actual-component failure/archive/replay tests, not a fabricated success.

## L. Security/logging

No credentials, environment reads, dotenv, arbitrary URLs, schema lookup, code
execution or transport-body logging is introduced. The existing managed logging
boundary emits safe source/report/date, opaque query filename/hash, attempts,
status, byte count, parser version, outcome/code and record count. Tests place
synthetic token-like source text in response fields and verify it never reaches
managed output; no full transport URL or chart strings appear in logs.

Unknown schema/series/unit and malformed content fail after archival; plausible
unknown timing fails separately. Permanent HTTP errors, including synthetic
404, terminate without a REN no-data interpretation. Actual REN future/error
forms remain unverified; synthetic error cases are labelled accordingly.
Unsupported coding preserves original anonymous bytes before failed parsing.
Interrupted/oversized acquisitions do not become complete archived reports.

## M. Fixture policy

`tests/data/ren/` contains **25 synthetic JSON fixtures**, README and checksum
manifest. No real body or provider measurement values were copied. Each manifest
entry has SHA-256, bytes, synthetic label, source day, profile/schema/unit,
expected outcome/code/count, purpose and mutation parent. Tests enforce exact
inventory and bytes. The ordinary/corrected pair differs in an invented value.

The matrix covers ordinary/spring/autumn/leap/year shapes, malformed JSON/HTML,
missing roots, unequal arrays, duplicate/missing/unknown series, unknown unit,
null/nonnumeric/nonfinite values, invalid labels, series/value bounds, unsupported
time/calendar metadata, empty coverage and revisions. In-memory hostile cases
cover depth/string/number/body bounds, duplicate keys and additional fields.
None establishes observed REN no-data/error behavior. Rights clearance for real
fixture redistribution remains absent; all real observations stay outside Git.

## N. Tests

| Focused module | Passing cases |
| --- | ---: |
| `tests/unit/ingestion/ren/test_ren_profile.py` | 23 |
| `tests/unit/ingestion/ren/test_ren_parser.py` | 66 |
| `tests/integration/test_ren_flow.py` | 44 |
| Total | **133** |

Final focused invocation: `python -m pytest tests/unit/ingestion/ren tests/integration/test_ren_flow.py -q`:
**133 passed in 2.49s**. No existing test/fixture was changed, removed, skipped or
weakened. An initial full collection found a basename collision with the existing
OMIE test_parser module; new REN modules were given unique names. A test-local
environment guard was also narrowed to restore pytest's environment before
reporting. Final collection and execution are clean.

## O. Full validation

All final checks use Python 3.12.9 with the default offline guard intact.

| Command | Final result |
| --- | --- |
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 105 files already formatted. |
| `mypy src` | Success: no issues found in 42 source files. |
| `python -m pytest` | **1281 passed in 11.64s**, zero failed/skipped; all 1148 baseline cases plus 133 new cases. |
| `git diff --check` | Passed, no output. New paths also receive explicit whitespace/diff review. |
| `pre-commit run --files <all changed/new paths>` | Passed on all 43 changed/new paths: Ruff check/format, whitespace, EOF, large-file and private-key hooks; YAML/TOML had no applicable files. No files mutated. |

All 968 Phase 1 and 180 Stage 1 cases are retained and green, including old wire
history/replay and immutable OMIE fixture checksum tests. No real HTTP, DNS,
credentials, subprocess network or live-enabling switch is used by pytest.

The semantic continuation reran the focused suite and every full quality gate
above against its 1,281-test baseline; the table contains the fresh results.
Report-inclusive hooks cover the same 43 paths. No implementation or test change
was made by the investigation; no cases were removed, skipped or weakened, and
no warnings were reported. The continuation diff was compared with the saved
pre-investigation bytes: only this report changed; all other Stage 2 files
retain identical SHA-256 values. The index remains empty.

## P. Phase 2 acceptance traceability

Original criterion numbers/text below are taken from authoritative §V. Status
is Stage 2 evidence, not Phase 2 closure. In particular criteria 3/4 remain
partial: acquisition/selection is implemented, authoritative normalization is not.

| Original criterion | Stage 2 status | Evidence / remaining work |
| --- | --- | --- |
| 1. Accepted Phase 2 query/measurement/auth/semantic-outcome decisions are recorded in focused ADR(s) before corresponding implementation; Phase 1 ADR history is retained and this report remains the sole readiness assessment. | SATISFIED | ADRs 0003/0004 retained; ADR 0005 records the time gate before REN code. |
| 2. All four mandatory providers and exactly the minimum products in §C are implemented; any scope change is explicitly approved and traced, never silently removed to obtain acceptance. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | REN acquisition/validation only; successful REN normalization and the other three providers remain pending. |
| 3. REN's documented daily production endpoint supplies all selected load/generation/import/export series from one acquisition; ancillary series/presentation fields have explicit selection policy, with no double-counted totals. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | One selected production query; eleven explicit mappings and four unselected names. No normalized records until §G is resolved. |
| 4. REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | §D/§G evidence and controlled time_semantics_unknown. No authoritative UTC/instant/interval/DST normalization. |
| 5. ESIOS 544 is verified against official authenticated name/unit/geography/sampling metadata, retained in a versioned catalogue; the peninsular forecast curve is not mislabelled as a complete D-1 forecast or actual load. | NOT YET APPLICABLE | ESIOS not implemented in this stage. |
| 6. ENTSO-E implements ES A65/A16 actual total load and PT plus ES A69/A01 renewable forecasts, retaining document/series/process/domain/PSR identity and distinguishing absent technologies from zero output. | NOT YET APPLICABLE | ENTSO-E not implemented in this stage. |
| 7. ENTSO-E namespace/version, Period resolution/position and A01/A03 curve handling are explicitly supported and tested, including multiple periods, constant blocks, missing sections and conflicting overlaps. | NOT YET APPLICABLE | ENTSO-E XML deferred. |
| 8. Open-Meteo archive ERA5 and selected-model forecast ingestion support exactly the three initial variables at six versioned sites, preserving requested/returned coordinates, grid/elevation and model identity. | NOT YET APPLICABLE | Open-Meteo deferred. |
| 9. Query contracts carry validated nonsecret product/window/domain/variables/location/model identity and explicit selection semantics; API snapshots do not fabricate numeric OMIE revisions or guaranteed latest versions. | SATISFIED | identity.request_for/validate_resolved; versioned product/culture/profile in canonical safe report identity; API snapshots. |
| 10. New system/weather record families and parse schema-family versions are strict, frozen and typed; MarketPrice and Phase 1 serialized archive/provenance remain readable and behaviorally compatible. | SATISFIED | Unchanged Stage 1 strict contracts and all old wire/replay tests pass. |
| 11. Geographic roles distinguish country, mainland/system perimeter, bidding zone, control area, EIC and coordinate; native IDs remain available and directed/aggregate interchange are not conflated. | SATISFIED | Explicit provider-defined PT system and ExternalBoundary; no invented zone/native area code/Spanish counterparty. |
| 12. MW, MWh and EUR/MWh remain distinct; system/market decimals have no binary-float intermediate and financial serialization preserves exact decimal values. | SATISFIED | schema.validate_chart direct Decimal and MW validation; precision and invalid-number tests; shared unit contracts unchanged. |
| 13. Scientific weather values are finite floats with explicit verified units, height/statistic and versioned plausibility/missing policy; no clipping or implicit unit conversion occurs. | NOT YET APPLICABLE | Weather deferred; Stage 1 scientific contracts remain green. |
| 14. Every normalized time is UTC-aware; instant samples, positive half-open intervals, source cadence and weather preceding-hour support remain distinct and query boundary handling is tested. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | UTC-safe query context retained, but actual REN timestamp/statistic normalization is blocked. |
| 15. Ordinary/leap/year boundaries, spring/autumn DST, duplicate local labels and UTC/local-day crossings are covered where applicable; GMT weather days are not forced to local 23/25-hour counts. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Synthetic clock/leap/year shapes tested; no asserted UTC DST calendar success. Later providers also pending. |
| 16. Actual, forecast and reanalysis kind is explicit; issue/publication/update/acquisition times remain distinct and unknown source times/horizons stay null. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Profile pins actual/provisional; no issue/update/publication timestamps fabricated. Actual normalized records remain gated. |
| 17. Multiple known forecast editions and unknown-edition acquisition snapshots for the same target survive distinctly; historical refetches are never declared known at an earlier market cutoff without evidence. | NOT YET APPLICABLE | No REN forecast product; shared edition tests retained. |
| 18. Source-selected credentials use ESIOS_API_TOKEN and ENTSOE_API_TOKEN, validated before I/O and injected privately using the verified mechanism; anonymous providers and OMIE need neither credential. | SATISFIED | REN factory has anonymous PrivateRequestPolicy and no environment loader; Stage 1 selective credential tests pass. |
| 19. Authentication/authorization failures are terminal, safely diagnosed and tested; there is no pasted-secret workflow, implicit dotenv load, auto-registration or token-refresh/probing loop. | NOT YET APPLICABLE | No REN credentials; generic synthetic 401/403 terminal behavior exercised. Authenticated providers deferred. |
| 20. Every external call uses finite phase/attempt/operation budgets, response caps, verified TLS, zero redirects and no hidden transport retries; whole-invocation query/attempt/byte/time caps are enforced. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Real shared defaults/caps and one REN request; whole multi-provider invocation caps remain later work. |
| 21. Retry policy has at most three attempts by default with bounded backoff, permanent/content/no-data failures do not retry, Retry-After is never shortened and ENTSO-E token bans end the invocation. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | REN factory uses shared three-attempt 1/2-second policy; permanent/parse failures never poll. ENTSO-E policy later. |
| 22. Selected query/record/JSON/XML bounds are implemented and documented; unexpected pagination/truncation/ZIP/content coding gives explicit coverage or unsupported failure rather than partial success. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | REN JSON/body/selection work bounds and explicit coding/unknown-field failures implemented. Other formats/providers pending. |
| 23. XML cannot resolve external resources or expand DTD/entities; encoding-aware element/depth/text/work safeguards and hostile-payload tests exercise the actual parser boundary, with any added security dependency justified. | NOT YET APPLICABLE | No XML parser added. |
| 24. Original complete safe provider body bytes are archived unchanged before transformation/semantic parsing using reused SHA-256 content addressing and atomic no-replace publication. | SATISFIED | Real shared runner/archive and all-fixture integration prove original-byte preservation before parsing. |
| 25. Independent identical acquisitions reuse content while retaining immutable events; changed bytes under unchanged provider/query/revision keys retain both versions and repeated event IDs remain idempotent. | SATISFIED | Three same-query synthetic acquisitions retain two hashes and three histories; idempotent event persistence tested. |
| 26. Retrieval provenance retains safe query/locator, acquisition UTC/status/attempts, native revision observations when known, byte/hash/archive linkage; no private request data is persisted. | SATISFIED | Shared version-2 retrieval sidecars retain only safe query identity, attempts/status/hash/original linkage. |
| 27. Separate parse provenance records parser/schema/catalogue versions and original raw/retrieval linkage; every normalized record links back to that chain and persistence failure prevents success. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Measurement parse provenance and persistence failure tested; positive REN record linkage awaits normalization. |
| 28. Complete malformed safe 200 responses and semantic no-data/error documents are preserved with explicit parse/semantic outcomes and zero normalized success; interrupted/oversized responses never masquerade as complete acquisitions. | SATISFIED | Actual-component malformed/HTML/empty/coding failure archival and body-cap tests; no zero-record success. |
| 29. Empty/null/missing/unsupported/future/provider-error results are distinguished from successful selected coverage; no bad rows are silently dropped, absent data converted to zero or undeclared partial dataset emitted. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | REN malformed/empty/missing selection/unknown profile safely fail. Actual REN future/no-data response forms remain unknown. |
| 30. Provider-specific auth/quota/domain/semantic/schema errors map to controlled typed categories, including ENTSO-E acknowledgement context rather than reason 999 alone; raw error text is never logged. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | REN content/schema/time codes controlled; provider error grammar and deferred providers remain pending. |
| 31. Safe logging/CLI/exception/config/metadata boundaries are tested with synthetic secret-bearing URLs, headers, rejected validation inputs and credential echoes; sensitive raw-body publication is rejected without pretending redaction preserves original bytes. | SATISFIED | Managed-log provider-string test plus unchanged Stage 1 synthetic credential/echo/security regressions pass. |
| 32. Each selected product replays entirely offline from archived bytes/history plus pinned catalogue metadata, with no name/geo/schema/weather/model network lookup and no fallback acquisition. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | REN failed parses replay offline with pinned local profile; successful normalized replay still gated; other providers pending. |
| 33. Replay verifies hash/linkage and reproduces fixed-version normalized values and identities; only new parse event identity/time may differ and original retrieval history remains unchanged. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Hash/linkage/failure identity reproduced; positive REN values/business identities cannot yet be verified. |
| 34. Actual-component mocked integration covers each mandatory product's successful chain, failure chain, correction/duplicate handling and replay through the shared archive/runner. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | Real REN adapter/HttpRetriever/LocalRawArchive/runner/parser/replay failure chain and corrections; success chain remains blocked. |
| 35. Small versioned fixtures cover §P's valid/missing/malformed/boundary/time/revision/provider-error cases; manifests protect hashes/inventory, label original/synthetic/mutated evidence and record rights/attribution. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | 25 synthetic checksummed REN fixtures and hostile in-memory cases; no authorized normalized-time fixture or other-provider suite yet. |
| 36. Existing OMIE fixtures and meaningful tests are preserved; shared changes pass Phase 1 regression and old-provenance/replay compatibility tests without weakening assertions. | SATISFIED | All 968 Phase 1 and 180 Stage 1 tests/fixture bytes retained and pass. |
| 37. Repository-wide python -m pytest succeeds with the existing network-denied guard active from collection, without credentials, real providers, subprocess networking or a live-enabling test switch. | SATISFIED | 1281 passing cases with unchanged collection-time network guard; no credentials/network/skip reduction. |
| 38. Live commands are separate and explicit --live opt-in, refuse before network construction without it, reject fixture archive roots and are absent from pytest/pre-commit/automatic CI execution. | NOT YET APPLICABLE | No REN live CLI introduced; existing explicit OMIE command remains unchanged. |
| 39. Controlled live validation records successful data through implemented retrieval/archive/parser paths for REN, ESIOS 544, ENTSO-E ES actual plus PT/ES forecasts, and Open-Meteo archive plus forecast; unavailability/auth failure is never counted as success. | NOT YET APPLICABLE | Two profile observations and retained autumn evidence explicitly excluded from live acceptance. |
| 40. The actual live acquisitions in criterion 39 have retained safe checksums/query/provenance/outcomes and successful subsequent network-denied replay; request/attempt totals and deviations from §Q are explained. | NOT YET APPLICABLE | No criterion-39 production acquisition or successful normalized REN replay is claimed. |
| 41. Source catalogues/runbooks/README/architecture status describe implemented scope, limits, units/time/forecast semantics, credentials, errors, revisions, replay, live opt-in and attribution/licensing boundaries without claiming production clearance or complete history. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | README/architecture/runbook/ADR/profile/report accurately describe implemented acquisition, limits and unresolved timing; other providers pending. |
| 42. Final Python 3.12 ruff check ., ruff format --check ., mypy src, python -m pytest, git diff --check and applicable pre-commit checks pass; full new/staged/unstaged diff and Git status are reviewed. | SATISFIED | Final offline gates and all-path hooks recorded in §O; complete tracked/untracked/cached review. |
| 43. No Snowflake/dbt/features/ML/registry/inference/API/dashboard/deployment/Kafka/Kubernetes implementation, paid-resource change, bulk download or unnecessary runtime dependency enters Phase 2. | SATISFIED | Only REN/local tests/docs; no new dependency, cloud/paid resource, bulk history or Phase 3+ implementation. |
| 44. Final acceptance traces every numbered criterion to concrete code/test/document/live evidence, reports external limitations honestly and leaves commit/push decisions to explicit operator authorization. | PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED | All 44 criteria traced here; full Phase 2/live closure not claimed; no commit/push/branch/staging. |

## Q. Files changed

Every changed/new path is listed below; all are unstaged. The fixture manifest
provides individual fixture hashes/lengths/purposes; no existing fixture changes.

| Path | Purpose |
| --- | --- |
| `docs/adr/0005-ren-source-profile-and-time-gate.md` | Accepted REN source-profile/time-gate decision before code. |
| `docs/codex/prompts/phase_2/phase_2_stage_2_ren_integration.md` | Complete original Stage 2 operator prompt; historical Stage 1 prompt untouched. |
| `docs/codex/reports/phase_2_stage_2_ren_report.md` | Stage 2 implementation/evidence/validation/limitations/traceability report. |
| `src/iberian_shakti/ingestion/ren/adapter.py` | Fixed REN transport resolution/shared retriever factory. |
| `src/iberian_shakti/ingestion/ren/identity.py` | Strict versioned API query/partition validation. |
| `src/iberian_shakti/ingestion/ren/parser.py` | Raw/linkage validation and controlled measurement parse failure. |
| `src/iberian_shakti/ingestion/ren/profile.py` | Pinned source/product/selection/unit/unknown-time profile. |
| `src/iberian_shakti/ingestion/ren/schema.py` | Strict bounded Decimal JSON/chart grammar. |
| `tests/data/ren/README.md` | Synthetic offline policy/parser/full-component tests or fixture documentation. |
| `tests/data/ren/manifest.json` | Exact synthetic inventory/hash/bytes/profile/outcome/purpose metadata. |
| `tests/data/ren/synthetic_autumn.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_corrected.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_duplicate_series.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_empty_coverage.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_excessive_series.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_excessive_values.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_html.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_inconsistent_duplicates.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_invalid_json.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_invalid_label.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_leap.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_missing_selected.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_missing_series.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_missing_xAxis.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_nonfinite.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_nonnumeric.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_null_value.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_ordinary.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_spring.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_unknown_series.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_unknown_time_profile.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_unsupported_calendar.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_wrong_length.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_wrong_unit.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/data/ren/synthetic_year_boundary.json` | Synthetic fixture; expected failure and checksum in manifest. |
| `tests/integration/test_ren_flow.py` | Synthetic offline policy/parser/full-component tests or fixture documentation. |
| `tests/unit/ingestion/ren/test_ren_parser.py` | Synthetic offline policy/parser/full-component tests or fixture documentation. |
| `tests/unit/ingestion/ren/test_ren_profile.py` | Synthetic offline policy/parser/full-component tests or fixture documentation. |
| `README.md` | Focused status/operating guidance or ADR-index update made necessary by Stage 2. |
| `docs/adr/README.md` | Focused status/operating guidance or ADR-index update made necessary by Stage 2. |
| `docs/architecture/README.md` | Focused status/operating guidance or ADR-index update made necessary by Stage 2. |
| `docs/runbooks/README.md` | Focused status/operating guidance or ADR-index update made necessary by Stage 2. |
| `docs/runbooks/ingestion.md` | Focused status/operating guidance or ADR-index update made necessary by Stage 2. |

Total: **43 paths**. Shared runtime/contracts, dependency files, environment
templates, existing tests/fixtures, Stage 1 historical material and the sole
readiness assessment are unchanged.

## R. External limitations

The blocking limitation is sufficient source evidence defining timezone and
label timestamp/statistic meaning for the selected production response. The
96/92/100 shapes alone cannot establish authoritative UTC instants or half-open
mean intervals. Completed-day normalization/completeness, DST fold resolution
and normalized value/identity replay therefore remain unimplemented.

Historical formats/retention/finalization/correction completeness, exact source
publication/update times, numeric quotas, real no-data/future/error documents
and fixture/commercial reuse rights remain unknown. Corporate restrictions
identified in the readiness report are not waived by public access. Synthetic
fixtures avoid redistributing provider bodies; this report grants no production
or commercial clearance. Temporary observations are not durable live acceptance.

## S. Stage verdict

**PASS WITH GAPS**

Fixed selected-product acquisition, strict chart/selection validation, safe
failure provenance, immutable corrections and failure replay are implemented
and pass offline gates. Original Stage 2 PASS requirements 4/5/6/9 and the
positive-record actual-component requirement are not fully established:
source-time semantics prevent any authoritative UTC SystemMeasurement success.
There is no waiver of criterion 4 or claim of complete REN integration.

## T. Next stage

Remain at **Phase 2 Stage 2**. Resolve the exact REN source-time/statistic gate
with sufficient official clarification or independently timestamped official
material; then implement and validate a new explicit time/profile version,
positive ordinary/DST normalization and successful normalized replay. No next
provider implementation is authorized by this result. Stop here without
ESIOS/ENTSO-E/Open-Meteo implementation, pre-live audit, final live validation,
commit or push.

## U. Revised engineering policy and acceptance — 2026-11-03

**Phase 2 Stage 2 — PASS**, under the explicit revised
[operator acceptance rule](../prompts/phase_2/phase_2_stage_2_ren_revised_semantics_implementation.md).
Phase 0/1 remain CLOSED/PASS; Phase 2 remains in progress. Stage 3 has not been
started or authorized. §§A–T above and ADR 0005 remain the historical record
of blocked profile 0.1.0; they are not the current operational instructions.

### Decision and evidence

The operator changed engineering policy after official REN 15-minute-period
evidence, the DST experiment, the blackout experiment and comparison with
forecasting practice. The accepted purpose is price forecasting: retain REN's
reported power as a feature input, without requiring settlement-energy semantics.
This is an explicit acceptance decision, not a claim that the evidence became
provider-authoritative. The independent experiment still says INCONCLUSIVE and
the exact MW statistic remains unresolved. Its report is unchanged. No new
provider request, external research or live validation occurred in this task.

| Known / accepted | Basis and operational meaning |
| --- | --- |
| MW source values | REN's explicit unit; preserve each finite Decimal exactly, including scale/sign. |
| 15-minute source period | Official REN period evidence; distinct from proving arithmetic averaging. |
| Europe/Lisbon | Strong empirical support, accepted as a provisional source-day profile. |
| Interval-start labels | Empirically favored placement, explicitly accepted engineering interpretation. |
| Ordered DST mapping | Exact physical-calendar label equality; spring skips 01h, autumn first/second 01h blocks map to fold 0/1 by array position. |

Still unresolved: provider-authoritative statement of the exact MW statistic,
provider-authoritative label definition and authoritative autumn fold contract.
The blackout result does not prove mean MW, and matching labels cannot prove
which repeated block's values own a fold. These facts no longer block ingestion
under the revised rule because values are represented honestly as source-period
power and the empirical interpretation is versioned and replayable.

### Implementation and contract

[ADR 0006](../../adr/0006-ren-provisional-period-semantics.md) was written before
implementation. REN profile and parser are **0.2.0**; report identity for new
requests is `ElectricityProductionBreakdownDaily.en-US.v0.2.0`. The profile pins
`Europe/Lisbon`, 15 minutes, `interval_start`, `provisional_empirical` and
`Statistic.PROVIDER_PERIOD_VALUE`. Time-semantic status is profile metadata,
separate from REN's provisional publication status; no confidence score exists.

The only additive contract option is `provider_period_value`: a provider-reported
measurement associated with a defined source period, with unknown precise
statistical aggregation. SystemMeasurement requires interval support for it and
rejects MWh; WeatherMeasurement rejects it. Existing mean/instant/sum rules,
wire shapes, schema defaults, Stage 1 history and MarketPrice are preserved.
No generic provenance fields or conversion service are introduced.

REN reuses `market_day_intervals`, a provider-neutral physical-day partition
helper already used by OMIE. Each local midnight is independently converted to
UTC, then intervals step only in UTC. The parser requires 92/96/100 periods and
exact equality of the entire ordered source-label tuple before constructing any
record. New queries use the resulting 23/24/25-hour UTC window. No fixed offset,
Madrid calendar, naive local stepping, sorting or deduplication is used.

Valid ordinary/spring/autumn days emit **1,056 / 1,012 / 1,100** SystemMeasurement
records respectively: eleven selected concepts per physical period. They use
actual kind, provisional publication, 900-second cadence, half-open UTC support
and unchanged source-native Decimal MW. Import/Export retain the existing
aggregate external boundary, without a country, interconnector or physical-flow
claim. All four ancillary concepts remain unselected and structurally validated.
No features, totals, lags, ratios, models or other providers are implemented.

**No MW-to-MWh conversion exists in Stage 2 REN ingestion.** Source inspection
finds no conversion arithmetic or mean/sum assignment in the REN implementation;
normalization tests compare every selected value with the source array, and
precision cases retain `1.2300`, signed values and long/scientific Decimals.
The contract rejects a provider-period record with MWh. Any future energy
conversion requires a separate explicit semantic upgrade to a confirmed statistic.

### Provenance, archive and replay

Each record retains source/report/day, exact native series, value/unit, native
profile version and parse/retrieval UUIDs. The parse event retains parser and
catalogue versions, raw SHA-256/reference and acquisition/archive linkage.
Original bytes retain the label and array position. For a selected series, its
physical interval start uniquely determines the zero-based position in the
validated day; that position indexes the original label/value, including both
autumn blocks. No redundant position/label fields are needed.

Shared query/archive/runner/replay and private-auth runtime code are unchanged.
Complete safe original bytes still archive before parsing; malformed responses
retain controlled failed parse events with zero records. Identical acquisitions
reuse content, while changed same-query bytes and all events remain immutable.

Offline tests reproduce all successful values, record/business identities and
normalized-content identities; only new parse UUID/time changes. Separate
ordinary/spring/autumn tests archive exact legacy **0.1.0** requests and failed
parse events, then replay under **0.2.0**, adding a successful parse without
rewriting any existing file. Legacy report IDs and UTC partition windows remain
the original acquisition metadata, while native/parse profile identifies the
new interpretation. Transport rejects legacy identities for new fetches.

Future provider clarification requires a new profile/parser version and new
parse events over the same archived acquisitions. Do not overwrite raw bytes,
old query metadata or earlier parse history. No migration framework is required.

### Baseline and preserved scope

First commands: `git status --short`, `git log --oneline --decorate -10`.
Branch **main**, HEAD **8a377ddcd6998f6d9e5aee90c11d71e431d83ce7**; locally recorded
origin/main **a4191a3c2e77896462f0b4c1f1066ebd8e84b782**. No fetch was performed.
The existing Stage 2 edits were expected: modified README/ADR/architecture/runbook
indexes and ingestion runbook, plus untracked ADR 0005, two original Stage 2
prompts, Stage 2/experiment reports, REN modules, fixtures and tests. They were
preserved, with focused amendments to operational REN behavior and documentation.
The exact revised prompt was saved before implementation. ADR 0005, older
prompts, experiment report and all 25 synthetic raw fixture payloads are unchanged.
Only fixture manifest profile/expected-outcome metadata changed.

This revision changes **19 files** (the complete working tree, including prior
Stage 2 work, has **49 changed/new paths**):

| Files changed by this revision | Purpose |
| --- | --- |
| `src/iberian_shakti/contracts/measurements.py` | One narrowly defined source-period power statistic and safeguards. |
| `src/iberian_shakti/ingestion/ren/{profile,identity,parser,schema}.py` | Versioned empirical calendar, current/legacy query validation, complete-day normalization and grammar documentation. |
| `tests/unit/ingestion/ren/{test_ren_profile,test_ren_parser}.py` | Physical query/calendar, exact values/mappings, folds and strict sequence failures. |
| `tests/integration/test_ren_flow.py` | Success/failure replay, corrections and legacy acquisition reinterpretation. |
| `tests/contracts/test_multisource.py` | Source-period interval/MW acceptance and instant/MWh/weather rejection. |
| `tests/data/ren/{README.md,manifest.json}` | Current expectations/history; unchanged payload hashes. |
| `docs/adr/0006-ren-provisional-period-semantics.md` | Explicit accepted policy and future replay. |
| `docs/codex/prompts/phase_2/phase_2_stage_2_ren_revised_semantics_implementation.md` | Exact operator prompt. |
| `docs/codex/reports/phase_2_stage_2_ren_report.md` | This dated revision, preserving historical sections. |
| `README.md`, `docs/adr/README.md`, `docs/architecture/README.md`, `docs/runbooks/{README.md,ingestion.md}` | Current scope/semantics and operational replay guidance. |

### Fresh offline validation

Python **3.12.9**, existing `iberian_shakti` environment; no dependency added.

| Gate | Result |
| --- | --- |
| Focused REN unit/integration suite | **143 passed in 4.45s** (25 profile, 71 parser, 47 integration). |
| Focused REN plus measurement contracts | **238 passed in 5.48s**. |
| Full `python -m pytest -q` | **1292 passed in 14.19s**, no failures/skips/warnings; default network guard active. |
| `ruff check .` | All checks passed. |
| `ruff format --check .` | 109 files already formatted. |
| `mypy src` | Success: no issues found in 42 source files. |
| Normal `pre-commit run --files <all changed/new paths>` | All applicable hooks passed on 49 paths: Ruff check/format, whitespace, EOF, large-file and private-key checks. YAML/TOML skipped as inapplicable; no hook changed files. |
| `git diff --check` and explicit untracked-file whitespace review | Passed. |
| Git review | Tracked diff, complete untracked source/tests/docs/fixture metadata and empty cached diff reviewed; no staging. |

All 968 Phase 1 and 180 Stage 1 cases remain intact and pass, including OMIE,
old serialized history/replay and private-auth behavior. One new shared contract
test plus ten additional REN cases bring the original 1,281 total to 1,292.
No tests were deleted, skipped, weakened or reduced to achieve passing results;
former semantic-gate assertions now check the explicitly revised behavior.

### Revised acceptance and limits

| Revised Stage 2 requirement | Result |
| --- | --- |
| Selected fetch contract, strict parser and exact eleven mappings | PASS; same fixed product/bounds, ancillary validation and geography. |
| Immutable archive/provenance/corrections/offline replay | PASS; successful and failed parses, including legacy acquisition replay. |
| Ordinary, spring and autumn normalization | PASS; 96/92/100 unique physical UTC periods, no lost autumn values. |
| MW preserved; honest provider-period semantics; no energy conversion | PASS; Decimal/source comparison and contract rejection tests. |
| Explicit provisional/versioned profile | PASS; profile/parser 0.2.0 and ADR 0006. |
| Full quality gates and Phase 1/Stage 1 regressions | PASS. |
| Unresolved semantics accurately documented | PASS; exact statistic, authoritative label definition and autumn fold contract remain unresolved. |

The original Phase 2 criterion 4 sought stronger authoritative semantics. This
operator decision supersedes that gate for **Stage 2 engineering acceptance**;
it does not assert newly obtained provider confirmation or completion of the
other providers, controlled live validation or full Phase 2 closure. Historical
retention/corrections, finalization/source timestamps, real missing/error shapes,
quotas and reuse/commercial rights remain bounded limitations recorded above.
No additional live validation was required or performed.

No provider request, branch creation, staging, commit, push, cloud/resource
change, Stage 3 or later-phase work occurred. Stop at Stage 2.
