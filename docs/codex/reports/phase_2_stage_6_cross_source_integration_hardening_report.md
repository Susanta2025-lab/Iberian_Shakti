# Phase 2 Stage 6 — Cross-source integration and hardening

Date: **2026-11-03**, Europe/Lisbon. Scope: offline cross-source engineering
integration only. Phase 2 remains in progress. No Stage 7 work or Stage 8 live
validation is included; synthetic compatibility is not real-provider acceptance.
**Verdict: Phase 2 Stage 6 — PASS.**

## Baseline and change boundary

The first commands were `git status --short` and
`git log --oneline --decorate -12`. The working tree was clean on existing
**main**, HEAD **77ff8e2ab84f09666ea7223e5a9914ea6d85de19**
(`feat: complete Phase 2 Open-Meteo ingestion`). The preceding Stage 4 checkpoint
is **f8dee4c**. Both Stage 5 reports and the explicit DWD ICON-EU implementation
(`FORECAST_MODEL = "icon_eu"`) are in the committed HEAD. The accepted Stage 5
PASS is preserved as the required clean checkpoint. Local main's eight commits
ahead of locally recorded origin are intentional; no remote synchronization.

The [exact Stage 6 prompt](../prompts/phase_2/phase_2_stage_6_cross_source_integration_hardening.md)
was saved before implementation. Inputs were repository instructions,
README/architecture/runbook references, the sole readiness assessment, Stage 1–5
reports including the forecast-model selection, ADRs 0001–0007, and the actual
contracts, ingestion paths and existing tests. Source selection was not reopened.

No shared contract or production-code defect requiring a change was found in
this scope. All source/profile/schema/query bytes and versions remain unchanged.
The existing closed `NormalizedRecord` union, per-acquisition `IngestionResult`,
runner, archive and replay already support coexistence. A bounded **test-only**
fixture plan exercises those components; no production collection, provider
registry, scheduler, transaction coordinator, synchronization engine or ADR is
needed. No dependency was added. README/runbooks are unchanged because no
operational workflow changes.

## Permanent source matrix

Run the dedicated selection with `python -m pytest tests/integration/stage6 -q`.
`test_source_matrix_survives_shared_serialization` enforces every row below,
including all six sites separately for each weather product. The combined replay
test separately verifies every selection through original archive history.

| Source/product | Geography | Kind | Support/statistic | Units | Autumn scenario records |
| --- | --- | --- | --- | --- | ---: |
| OMIE marginalpdbc | PT and ES market areas | MarketPrice | Madrid market intervals, 15 minutes | Decimal EUR/MWh | 200 |
| REN production breakdown 0.2.0 | REN Portuguese system; aggregate external boundary for import/export | actual, provisional | Lisbon 15-minute periods, provider_period_value | Decimal MW | 1,100 |
| ESIOS 544 | ES.peninsular, native synthetic geo ID retained | forecast | UTC 5-minute instant samples | Decimal MW | 3 |
| ENTSO-E ES A65/A16 | ES EIC bidding zone | actual | UTC 30/60-minute provider_period_value, explicit gap | Decimal MW | 3 |
| ENTSO-E PT A69/A01 | PT EIC bidding zone | forecast | UTC 15-minute provider_period_value, separate solar/onshore wind | Decimal MW | 8 |
| ENTSO-E ES A69/A01 | ES EIC bidding zone | forecast | UTC 15-minute provider_period_value, separate solar/onshore/offshore wind | Decimal MW | 12 |
| Open-Meteo ERA5 | six versioned requested points and independent returned grids | reanalysis | hourly UTC instants and preceding-hour radiation mean | °C, m/s, W/m² | 432 |
| Open-Meteo ICON-EU, models=icon_eu | same six requested points; independent returned grids | forecast | hourly UTC instants and preceding-hour radiation mean | °C, m/s, W/m² | 432 |
| Total | Multiple geography types | Three measurement kinds plus market price | No cadence alignment | Five unit families | **2,190** |

The test fixture plan has **18 acquisitions**: OMIE 1 + REN 1 + ESIOS 1 +
ENTSO-E 3 + weather 12. Existing synthetic JSON/XML fixtures are reused with
in-memory date/failure/correction mutations. Synthetic OMIE rows use the accepted
calendar and deliberately constant prices. No realistic market/weather
correlation, downloaded fixture or new fixture copy is introduced.

## Contract, geography and temporal findings

The full typed results round-trip through the existing closed record union
without losing source/native/profile/geography/time/unit/kind/provenance fields.
All 2,190 business identities remain distinct. Coincident load values, UTC times,
country labels and concept names across REN/ESIOS/ENTSO-E remain independently
identified; an ES OMIE price at that same time/value is also a separate record.

REN's `ren_portuguese_system` is a provider-defined system perimeter, not an
asserted country/mainland or ENTSO-E zone equivalence. ESIOS's ES.peninsular is a
mainland system object, not ES.entsoe_bidding_zone. ENTSO-E retains bidding-zone
role plus native EIC/scheme for PT and ES. OMIE's legacy PT/ES market-area fields
retain their own contract and provenance. Import/export retains an aggregate
external boundary, with no invented Spanish endpoint or physical-flow claim.

All six WeatherSite objects retain selection version, requested coordinates and
country context separately from WeatherGrid coordinates/elevation. Identical
synthetic returned grids across sites do not make the requested points equal.
No point is treated as national weather or as an electricity-system area.

Integrated ordinary **2026-10-24**, spring **2026-03-29** and autumn
**2026-10-25** scenarios assert explicit independently specified UTC boundaries:

- OMIE uses Europe/Madrid for **both** PT and ES, with 96/92/100 quarters per
  area and contiguous source intervals.
- REN uses its accepted provisional empirical Europe/Lisbon profile, with
  96/92/100 periods and eleven native measurements per period. Its first UTC
  support is one hour after the OMIE market start on these dates. This is not
  new authoritative evidence for REN's remaining statistic/label/fold refinements.
- Autumn repeated Lisbon 01h and Madrid 02h preserve both folds in physical
  order, eight quarters with fold 0 then fold 1. The corresponding spring hour
  is absent. No naive local stepping or label deduplication is introduced.
- ENTSO-E retains its UTC 15/30/60-minute Period support and gaps. Native A03
  decoding remains the existing provider interpretation, not cross-source filling.
- ESIOS preserves the explicit UTC 00:55/01:00/01:05 samples and valid native
  Madrid offset timestamps, with 300-second cadence and no interval inference.
- Both weather products keep exactly 24 hourly samples / 72 records per site,
  including on 23/25-hour local days. Radiation at UTC midnight retains
  `[previous day 23:00, midnight)`; temperature/wind retain ValidInstant(midnight).

Tests assert semantic correctness and differing source counts, without creating
aligned rows. No resampling, interpolation, forward/back filling, averaging,
summing, national/site aggregation or feature engineering occurs.

## Unit, statistic, kind and source-time safety

Market EUR/MWh, system MW and weather °C/m/s/W/m² remain separate typed fields.
Cross-family unit substitution and MW-to-MWh relabelling with provider-period
statistics fail validation. Decimal financial/system values retain direct source
precision; weather remains finite scientific floats with existing profile bounds.
No conversion was added.

Instant statistics require ValidInstant; period statistics require SupportInterval.
ESIOS forecast samples remain distinct from REN periods. Temperature/wind remain
instant while shortwave is preceding-hour mean. REN and ENTSO-E remain
`provider_period_value`, which neither asserts arithmetic mean nor authorizes
power-to-energy conversion. An explicitly different mean has a different business
identity; the integration never makes that reinterpretation.

Actual (REN/ENTSO-E load), forecast (ESIOS/ENTSO-E renewables/ICON-EU), and
reanalysis (ERA5) survive round-trip serialization and replay. MarketPrice retains
its legacy price semantics instead of acquiring an invented measurement kind.

Unknown issue/run/publication times remain null. ESIOS values_updated_at is only
indicator snapshot update context; ENTSO-E createdDateTime remains linked raw XML
metadata, not per-value issue/run/update/publication. Weather source times remain
unknown. Acquisition completion, parse time and valid/support time stay separate.
Latest forecasts do not prove availability at an old market cutoff. Repeated
identical unknown-edition forecasts have distinct acquisition-based business
identities, and replay preserves those original acquisitions. A current completion
time cannot relabel an old ICON-EU target as a supported next-day acquisition.
No historical-vintage reconstruction or cutoff feature helper was added.

## Query identity audit

Canonical API identity already includes provider, versioned product/report,
partition/window and typed selection. Weather adds model, logical site/version,
coordinates, variables and explicit ICON-EU output/profile selection. System
selection includes role/native area and sorted series IDs. ENTSO-E selects the
whole supported A69/A01 wind/solar product per domain; no new PSR subquery exists.

Tests distinguish ERA5/ICON-EU, Lisbon/Madrid, PT/ES renewable queries,
544/theoretical 545, REN production/another product, profile/output/site versions,
area, provider and time window. JSON key-order changes round-trip deterministically
to the same SHA-256. Unsupported alternatives remain distinguishable at the
contract level without implying provider support. All 18 selected safe locators
are unique; all 17 API query hashes are unique. OMIE keeps its exact-revision
legacy request wire shape and separate numeric-revision policy.

No query serialization/hash change or migration is required. Existing Stage 1
wire-history and Stage 5 ERA5-byte/hash regressions remain unchanged and pass.

## Provenance and combined offline replay

For every selection, tests follow record → persisted parse event → persisted
original retrieval → immutable raw object → SHA-256 → original canonical request.
OMIE uses its legacy parse-event linkage; measurements also retain retrieval UUID.
Schema/parser/catalogue/native profiles remain explicit. Stored events are read
and compared with the actual runner results, not replaced by synthetic parsers.

All 18 acquisitions replay in one archive with **zero network, zero credentials,
zero new retrieval events**. During replay, HTTP client/retriever construction,
retrieval and every selected credential-loader seam explicitly fail if called,
in addition to the unchanged collection-time repository network guard.
Original bytes, business values, native semantics, record/business identities,
normalized-content identities, query and raw linkage reproduce. Only new parse
UUID/time differs. All earlier archive/history bytes remain unchanged; 18 new
parse events are appended, for 36 total.

Eight distinct composite raw identities back the 18 acquisitions. Identical
weather fixture bytes intentionally share a raw object **within** a source/report/
day partition while retaining separate site queries and acquisitions. A SHA-256
alone is not the full raw identity. Providers/reports remain distinct even for
identical bytes; no fabricated per-site hash or overwrite is needed.

Corruption is injected separately into every representative product's payload.
That source's replay raises ReplayError; all other sources still reproduce,
unaffected evidence/history remains byte-identical, and retrieval counts do not
change. No refetch, silent substitution or network fallback occurs.

## Failure isolation, persistence and corrections

One shared archive retains successful prior acquisitions while new failures are
injected: OMIE parse failure, malformed REN JSON, ESIOS schema/401/403/missing
configuration, ENTSO-E rejected/no-data acknowledgements, and malformed weather
JSON for both products. Previously successful data, including the failing
provider's earlier acquisition, remain replayable without changes.

Every representative product separately fails at raw publication, retrieval
metadata publication and parse-event publication (24 persistence cases). Raw or
retrieval persistence failure prevents parser invocation. Parse persistence
failure raises ArchiveError before the runner can return successful records.
No successful parse event is published. Prior evidence remains intact and
replayable. Complete safe malformed 200 bytes remain archived with unsuccessful
parse events and zero records; HTTP/auth/oversize failures never masquerade as
complete successful acquisitions. There is no cross-provider rollback transaction.

Duplicate and revised acquisitions are exercised independently for OMIE, REN,
ESIOS, each ENTSO-E product/domain, ERA5 and ICON-EU. Identical bytes reuse payloads
with independent retrieval/parse histories; changed source values retain both raw
versions and all prior files. OMIE's numeric revision change remains local.
Actual/reanalysis corrections retain business identity with separate evidence;
unknown forecast snapshots remain distinct even when their bytes match.
All prior and revised acquisitions replay independently. No cross-provider
latest-wins selection or source identity mutation exists.

## Error taxonomy and safe diagnostics

ConfigurationError remains separate from acquisition outcomes and is raised
before HTTP construction for missing selected credentials. Authentication and
authorization retain terminal distinct codes; transport timeout/retry exhaustion,
ordinary HTTP failure, schema/content failure, archive failure and replay integrity
retain their own boundaries. ENTSO-E no-data is source_unavailable/no_data;
unknown acknowledgement prose is provider_rejected, including text containing
authentication/no-data keywords. No keyword classifier was introduced.
Other providers are not forced to emit ENTSO-E semantic categories.

Mixed anonymous/private success and failure paths run under managed DEBUG
logging. Synthetic active-token echoes cannot publish raw content; unchecked
transport/provider prose, private headers and credential URLs are absent from
results, metadata and managed diagnostics. All credential values come from
explicit synthetic mappings; no real credential/environment file is read.
Replay needs no credential configuration. OMIE, REN and weather acquire without
private headers/query credentials. Existing literal/quoted/JSON/XML-reference
echo, fixed-origin and transport-debug protections remain unchanged.
This is scoped regression evidence, not a new exhaustive security audit or a
claim of general secret detection in anonymous content.

## Bounds audit

No bound was raised. Each provider still uses bounded HttpRetriever and one
finite response. Existing parser/security regressions exercise the actual
complexity limits; new cross-source cap tests prove oversized acquisitions do
not modify other evidence.

| Path | Response cap | Parser/collection work | Time/normalized output bounds |
| --- | --- | --- | --- |
| OMIE | 4 MiB; discovery separately 1 MiB / one page / 10,000 anchors | strict ASCII row grammar and complete ordered calendar rows | one market day, at most 100 periods / 200 area prices |
| REN | 1 MiB | depth 12, 30,000 nodes, 32 series, 10,000 total values, bounded keys/strings/numeric tokens | one Lisbon day, 92/96/100 periods, at most 1,100 selected records |
| ESIOS | 2 MiB | depth 16, 50,000 nodes, 2,000 values, 32 geos, bounded strings/numeric tokens | requested window ≤25 h, 5-minute grid, at most 2,000 records |
| ENTSO-E | 4 MiB | depth 32, 100,000 elements, 2 MiB cumulative text, 4,096 chars/node, 100 series, 64 Periods/series, bounded attributes/numeric tokens | request/document/Period ≤25 h, at most 20,000 expanded records |
| ERA5 / ICON-EU | 1 MiB each | depth 16, 4,096 nodes, 64 keys/object, 48 items/array, bounded strings/numeric tokens, one site/request | exactly one UTC day, 24 points / 72 successful records; parser outer bound 48 points / 144 measurements |

Shared defaults remain finite: three total attempts, 10-second phases,
30-second attempts and 93-second operation budgets; ENTSO-E 429 is terminal.
The test-only plan has a fixed maximum of 18 selected acquisitions and no date
iteration, dynamic discovery/fan-out or growing shared accumulator. The existing
archive loads one reference/event at a time; metadata reads are capped at 64 KiB.
No operational multi-source runner/global-budget implementation was introduced
or implicitly claimed. Any future operational planner must retain its explicit
invocation-wide limits; that is outside this test-harness change.

## Validation

Python **3.12.9**, existing named environment. The network-denied default and
all prior provider tests/fixtures remain unchanged. No skips or weakened existing
assertions were introduced. Final executed results are recorded below.

| Gate | Result |
| --- | --- |
| Dedicated Stage 6 suite | **119 passed in 38.78s** |
| Provider-focused unit/integration suites | **1,164 passed in 14.24s** |
| Full `python -m pytest` | **2,131 passed in 57.51s**, no failures/skips |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 155 files already formatted |
| `mypy src` | No issues in 59 source files |
| `pre-commit run --all-files` | All eight hooks passed |
| Explicit pre-commit on all six new paths, without staging | All applicable hooks passed |
| `git diff --check`, new-file whitespace and complete change review | Passed; index remains empty |

The provider selection includes all five provider unit directories and the
existing OMIE Stage 3/4/5 flow, REN, ESIOS, ENTSO-E and Open-Meteo integration
modules. Full pytest additionally covers the entire unchanged Phase 1 and
Stage 1–5 regression baseline. A new ESIOS malformed-shape test initially
expected content_invalid; inspection confirmed the accepted parser correctly
uses schema_unsupported. The new expectation was corrected to that precise
taxonomy; production code and prior tests were unchanged.

## Files and remaining stages

Exactly six new unstaged paths:

- `docs/codex/prompts/phase_2/phase_2_stage_6_cross_source_integration_hardening.md`
- `docs/codex/reports/phase_2_stage_6_cross_source_integration_hardening_report.md`
- `tests/integration/stage6/__init__.py`
- `tests/integration/stage6/support.py`
- `tests/integration/stage6/test_semantics.py`
- `tests/integration/stage6/test_evidence.py`

Stage 7 retains the formal exhaustive timeout/retry, security, parser-security
and pre-live checklist audit; it has not been started. Stage 8 retains separately
authorized controlled provider requests and replay of real archived acquisitions,
including authentication, native metadata, coverage/error/revision behavior and
ICON-EU/grid compatibility. Existing REN provisional refinements and unknown
forecast editions remain honestly represented; they are not new Stage 6 defects.
No real-world provider compatibility, historical forecast cutoff reconstruction,
licensing clearance or Phase 2 closure is claimed.

No provider request, credential probe, cloud action, branch creation, staging,
commit or push occurred. No fetch/pull/rebase/reset/restore/stash occurred.
All changes remain unstaged on main for operator review.

**Phase 2 Stage 6 — PASS.** No unresolved offline Stage 6 engineering issue
remains. Phase 2 Stage 7 has not been started or authorized.
