# Phase 2 Stage 5 — Open-Meteo integration

Current completion verdict (2026-11-03): **PASS — offline Stage 5 engineering**.
The initial **PASS WITH GAPS** record below is retained in full as history.
Its sole forecast-model blocker was closed by the accepted operator decision
selecting **DWD ICON-EU / models=icon_eu**, followed by the offline implementation
and validation recorded in the completion section. Phase 2 remains in progress;
Stage 6 has not been started or authorized. No live provider request was made.

## Original implementation record (retained)

Verification date: **2026-11-03**, Europe/Lisbon. **PASS WITH GAPS**.
Historical ERA5 ingestion is implemented and validated offline. Forecast
ingestion remains blocked by a specific missing authoritative model decision.
Phase 2 remains in progress; Stage 6 has not been started or authorized.

## Baseline and scope

Initial `git status --short` was empty. Existing branch **main**, HEAD **f8dee4c**
(`feat: complete Phase 2 ENTSO-E ingestion`), preceded by 8ef31ef, 13d5ff6,
8bb5618, 09792e9, 8a377dd and 70f4204 as expected. Python **3.12.9**, existing
named environment. The exact operator prompt was saved before implementation at
`docs/codex/prompts/phase_2/phase_2_stage_5_open_meteo_integration.md`.

Inputs: repository instructions, README/architecture/ADR/runbook references,
the sole Phase 2 readiness assessment, Stage 1–4 reports, ADRs 0003/0004/0006,
shared weather/geography/query/provenance contracts, retrieval/archive/runner/
replay/logging and existing contract/integration tests. No shared contract,
archive, retriever, runner, replay, dependency, CI or previous test was changed.
No new architectural decision requires an ADR.

## Exact forecast blocker

[Readiness §H](phase_2_readiness_assessment.md#h-open-meteo-verification) says:

> forecast product/model details and commercial service use remain explicit gaps.

Its forecast row requires a pinned compatible model but supplies **no exact
model identifier**. The closing paragraph requires compatibility for three
variables and both countries and forbids silent `best_match`. No other assessment
section pins a forecast model. Selecting one here would invent a missing decision.

The intended public Forecast API endpoint is
`https://api.open-meteo.com/v1/forecast`; **selected forecast model: unresolved**.
`FORECAST_MODEL` is explicitly `None`. `forecast_request_for(window, site_id)`
validates the independent site/day context and raises static `ConfigurationError`
before resolution/HTTP. It has no caller-supplied model override. The actual
adapter/parser validate the complete canonical ERA5 query and reject forecast,
wrong-model, changed-site and wrong-profile identities. **No silent `best_match`
fallback exists.**

Consequently, successful forecast acquisition/normalization, a valid selected-model
forecast fixture, forecast-specific vintage/revision tests and forecast replay
are **not implemented or claimed**. These depend on the missing exact model and
its compatible next-day product profile. The existing shared weather kind/support/
source-time/acquisition contracts already support that later work; no provisional
model or second weather architecture was introduced. This follows the prompt's
explicit missing-decision path rather than claiming full Stage 5 acceptance.

## Implemented profile and sites

Profile/catalogue **0.1.0**, parser **open_meteo.era5.hourly / 0.1.0**,
weather record schema **1.0.0** and shared retrieval/measurement-event contract
**2.0.0**. Source `open_meteo`, report/product `historical.era5.v0.1.0`,
model `era5` (ERA5). Model identity comes from the validated explicit query;
the standard response need not echo a model or run. If optional `model`/`models`
text is supplied, it must agree with `era5`.

Exactly the six versioned readiness sites, WGS84, selection version **0.1.0**:

| Site identity | Name | Country | Requested latitude | Requested longitude |
| --- | --- | --- | ---: | ---: |
| PT.lisbon | Lisbon | PT | 38.72 | -9.14 |
| PT.porto | Porto | PT | 41.15 | -8.61 |
| PT.braganca | Bragança | PT | 41.81 | -6.76 |
| ES.madrid | Madrid | ES | 40.42 | -3.70 |
| ES.zaragoza | Zaragoza | ES | 41.65 | -0.89 |
| ES.seville | Seville | ES | 37.39 | -5.98 |

No coordinate lookup, interpolation, national aggregation or feature engineering.
Logical `WeatherSite` retains requested coordinates/country/version. Independent
`WeatherGrid` retains returned latitude, longitude and required finite elevation
in metres. Existing coordinate/elevation bounds apply. Elevation is provider
response metadata, not a claim about surveyed city or grid terrain elevation.
Returned timezone/offset and any presentation metadata remain in original bytes.

## Historical request, units and time

Endpoint **https://archive-api.open-meteo.com/v1/archive**. Anonymous GET,
explicit **models=era5**, one site and complete UTC day per request. Shared
`QueryWindow` is further narrowed to midnight through next midnight, exactly
24 hours. Both inclusive API date selectors name that one day. No unbounded
backfill, batching, concurrency, forecast horizons or date iteration is added.

Only three hourly variables; `timezone=GMT`, `timeformat=unixtime`,
`temperature_unit=celsius`, `wind_speed_unit=ms`. No local time, implicit wind
conversion, daily or sub-hourly variable, alternative reanalysis or model blending.
Canonical query identity includes provider/report/profile, model, fixed site/
coordinates/selection version, window, partition date and canonical variable set.
Unit/time choices are fixed by this versioned product rather than mutable inputs.

| Source variable | Normalized variable/height | Valid time/support | Statistic | Validated source unit |
| --- | --- | --- | --- | --- |
| temperature_2m | temperature, 2 m | ValidInstant at returned UTC t | instant | °C |
| wind_speed_10m | wind_speed, 10 m | ValidInstant at returned UTC t | instant | m/s |
| shortwave_radiation | shortwave_radiation, no height | [t−1h,t) UTC | mean | W/m² |

Every record is **kind=reanalysis**, never actual station observations or
forecasts. Cadence is 3,600 seconds; all 24 ordered integer Unix hourly timestamps
must exactly cover the requested UTC day. Missing, extra, duplicated, reversed,
off-hour or outside timestamps fail the whole parse. Midnight radiation retains
support in the preceding partition day. DST dates still have 24 UTC samples.
No sorting, filling, smoothing, clipping, resampling or averaging occurs.

Finite scientific floats use unchanged shared bounds: temperature −100..70 °C,
wind 0..150 m/s, shortwave 0..2,000 W/m². These are existing versioned project
plausibility bounds, not new climate assumptions or provider guarantees.
Source issue/model-run/publication/update times remain null. Acquisition completion,
parse time and measurement time remain distinct; HTTP/presentation timing is not
promoted to a forecast edition or historical information-cutoff guarantee.

Public documentation was consulted, without product requests:
[Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
for units, model selection, Unix time, coordinate/elevation metadata and radiation
support; [Forecast API](https://open-meteo.com/en/docs) for the distinct product.
Documentation is not a live observation made in this task.

## Strict JSON, errors and bounds

Strict UTF-8 JSON object; duplicate keys, NaN/Infinity, float overflow, invalid
Unicode surrogates and unsupported shapes fail visibly. Required grid/elevation,
zero integer UTC offset, explicit recognized GMT/UTC timezone, hourly time/arrays
and units validate before normalization. Optional timezone abbreviation must
agree. Selected hourly/units objects forbid extra fields; unrelated bounded root
presentation fields (including `generationtime_ms`) are optional inert bytes.
All three numeric arrays must match time length. Nulls, booleans, strings or other
non-numbers cannot become weather values; unexpected units cannot be converted.
Late validation failures emit zero records, never partial success.

Limits: **1 MiB** original response, JSON depth **16**, **64 keys/object**,
**48 items/array**, **4,096 characters/string or key**, **128 characters/numeric
token**, **4,096 traversed JSON nodes**, **48 hourly points / 144 potential
measurements** and **one site/request**. Strict daily success is **24 points /
72 records**. JSON decode/recursion errors and bound violations fail atomically;
the byte cap also bounds decoder allocations before structural traversal.
The only catalogue contains six sites. No invocation accepts a site collection.

Bounded structured `error=true` with string `reason` becomes controlled
`provider_rejected/provider_rejected`; no raw reason reaches exceptions or logs.
Unknown/malformed error documents fail schema/content rather than invented
no-data semantics. Complete safe 200 bodies archive before parsing, including
errors/malformed JSON. Non-200 responses retain unchanged shared HTTP handling:
400/404 are terminal HTTP failures, bodies unarchived/unlogged; no no-data guess.

The shared anonymous fixed-origin private request policy reads no credential.
No `OPEN_METEO_API_KEY` setting or commercial endpoint is introduced. Retries
remain three attempts, default 1/2-second backoff, finite 10/30/93-second
phase/attempt/operation budgets and supported bounded Retry-After. Semantic,
schema and content failures do not retry. Transport oversized/interrupted bodies
cannot publish as complete acquisitions. Compression is unsupported by the parser;
anonymous nonidentity bodies remain original archived bytes with parse failure.

## Archive, corrections and replay

Unchanged `HttpRetriever` → `ingest_resolved` → immutable `LocalRawArchive` →
parser chain. SHA-256 original bytes, no-replace publication, independent retrieval
and parse UUID/events, versioned schema/profile and requested query link every
normalized record to product/model/site/window/acquisition/raw hash/reference.
Returned grid/elevation and source-variable identity remain on each record.

Identical query/body shares content but preserves independent acquisitions;
changed body preserves both payload versions and every history. Reanalysis
corrections retain their business identity with distinct raw evidence. No mutable
latest copy. No forecast correction/vintage behavior is claimed without the model.

Shared replay verifies bytes/hash/reference and original retrieval linkage with
zero HTTP/client construction or new acquisition. All normalized fields, values,
units, site/requested/returned metadata, support, model/native identity, business
identity and raw linkage reproduce; only parse UUID/time changes. Original history
remains byte-for-byte unchanged. Corrupt bytes or linkage and missing acquisition
events fail without refetch. Persistence failure prevents success.

## Validation

Small synthetic fixture plus in-memory mutations; manifest pins exact byte count,
SHA-256, origin/profile/count. No real provider bytes or credential was used.
All six site/country mappings and all six archive/replay paths are tested.
The unchanged network-denied pytest guard remains active throughout.

| Gate | Result |
| --- | --- |
| Focused Stage 5 unit/integration suite | **175 passed** |
| Full `python -m pytest` | **1,817 passed**, all 1,642 previous cases retained |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 145 files already formatted |
| `mypy src` | No issues in 59 source files |
| `pre-commit run --all-files` | All eight hooks passed |
| Explicit pre-commit check of every changed/new file | All applicable hooks passed; untracked files checked without staging |
| `git diff --check`, new-file whitespace and diff review | Passed; index unchanged and empty |

## Files changed

Seventeen unstaged paths, left for operator review:

- `src/iberian_shakti/ingestion/weather/profile.py`
- `src/iberian_shakti/ingestion/weather/identity.py`
- `src/iberian_shakti/ingestion/weather/adapter.py`
- `src/iberian_shakti/ingestion/weather/schema.py`
- `src/iberian_shakti/ingestion/weather/parser.py`
- `tests/unit/ingestion/weather/test_open_meteo_profile.py`
- `tests/unit/ingestion/weather/test_open_meteo_parser.py`
- `tests/integration/test_open_meteo_flow.py`
- `tests/data/open_meteo/synthetic_era5.json`
- `tests/data/open_meteo/manifest.json`
- `tests/data/open_meteo/README.md`
- `docs/codex/prompts/phase_2/phase_2_stage_5_open_meteo_integration.md`
- `docs/codex/reports/phase_2_stage_5_open_meteo_report.md`
- `README.md`
- `docs/architecture/README.md`
- `docs/runbooks/README.md`
- `docs/runbooks/ingestion.md`

## Reserved for controlled live validation

Nothing below was observed through a real provider request in this task:

- Successful real Historical API and Forecast API requests.
- Actual returned coordinates/grid/elevation behavior, units and timestamp arrays.
- Actual explicitly selected forecast-model response and coverage/horizon.
- Historical ERA5 availability/delay and request-boundary inclusivity.
- Real provider error/no-data variants, response size and compression.
- Model update behavior, forecast revisions and rate limits.
- Licensing/redistribution constraints, attribution and free-service access terms;
  no commercial clearance or subscription is claimed.

No provider request, geocoding, secret, paid/cloud resource, fetch/pull/rebase/reset,
new branch, staging, commit, push or later-phase implementation occurred.
Public documentation reads were the only external source access.

**Phase 2 Stage 5 — PASS WITH GAPS.** Precise blocker: the authoritative readiness
assessment does not identify an exact forecast model; forecast ingestion and its
success/vintage/replay evidence remain pending that explicit decision.


## Completion record — accepted ICON-EU integration

Completion baseline: **main**, **f8dee4c**, `feat: complete Phase 2 ENTSO-E ingestion`.
The working tree already contained the historical Stage 5 implementation,
integration prompt/report and selection prompt/report. Those changes were preserved.
The exact completion prompt was saved first at
[phase_2_stage_5_open_meteo_forecast_completion.md](../prompts/phase_2/phase_2_stage_5_open_meteo_forecast_completion.md).
The [model-selection report](phase_2_stage_5_forecast_model_selection.md) and both
earlier prompts remain unchanged. The ranking was not reopened. The accepted
operator decision closes the former missing-model-selection blocker.

| Product | Endpoint | Report / model | Profile / parser |
| --- | --- | --- | --- |
| Historical ERA5 | `https://archive-api.open-meteo.com/v1/archive` | `historical.era5.v0.1.0` / `era5` | 0.1.0 / `open_meteo.era5.hourly` 0.1.0 (unchanged) |
| DWD ICON-EU deterministic European domain, ~7 km | `https://api.open-meteo.com/v1/forecast` | `forecast.icon_eu.v0.1.0` / `icon_eu` | Independent 0.1.0 / `open_meteo.icon_eu.hourly` 0.1.0 |

The historical adapter/parser retain their public names. The additive
`OpenMeteoForecastAdapter` / `IconEuParser` specialize the same implementation;
there is no second weather ingestion framework. Record schema remains 1.0.0;
API/retrieval/measurement-event contracts remain 2.0.0.

Exactly the six sites in the original table remain at selection version 0.1.0:
PT.lisbon 38.72/-9.14, PT.porto 41.15/-8.61, PT.braganca 41.81/-6.76,
ES.madrid 40.42/-3.70, ES.zaragoza 41.65/-0.89, ES.seville 37.39/-5.98.
No geocoding, changed coordinates, site aggregation or interpolation was added.

Both products request only `temperature_2m,wind_speed_10m,shortwave_radiation`,
`temperature_unit=celsius`, `wind_speed_unit=ms`, `timezone=GMT`,
`timeformat=unixtime`. Forecast URLs explicitly include **models=icon_eu**.
No arbitrary model override is exposed. Missing/changed model identity, changed
site/country/coordinates/selection version, wrong product/profile, omitted output
selection or changed variables fail before acquisition/parsing success.
`best_match`, seamless/global/D2/AICON and IFS are rejected as primary products.

### Window, scientific semantics and grid context

One site and one complete explicit UTC weather day per request, midnight through
next midnight, half-open. `start_date=end_date` names that requested day. Success
requires exactly **24 ordered hourly timestamps and 72 measurements**. DST cannot
produce 23/25-hour UTC weather days. There is no default multi-day payload,
interpolation, resampling, smoothing, sorting, filling or repeated-value repair.

Forecast acquisition is conservatively restricted to the **next UTC day** relative
to the injected acquisition clock; unsupported historical/today/later-day targets
fail before client construction. The parser checks again using the original
retrieval completion time; a midnight-crossing acquisition may fail closed.
Replay uses that original time, never parse time or today's clock. Intended use
is approximately **12–48 h** day-ahead. The selected main-cycle product is
**documented native hourly through 78 h**; this implementation does not expose
longer/coarser windows as native hourly output. This is a target-window policy,
not a computed true lead time: run initialization is unknown. Short cycles may
have only conservative 30 h importer support; actual snapshot cycle composition
and availability remain controlled-live questions. A UTC weather day is not a
claim of complete local MIBEL delivery-day coverage.

| Variable | Normalization | Unit | Statistic and support |
| --- | --- | --- | --- |
| temperature_2m | temperature, height 2 m | °C | instant, `ValidInstant(t)` |
| wind_speed_10m | wind_speed, height 10 m | m/s | instant, `ValidInstant(t)` |
| shortwave_radiation | shortwave_radiation, no height | W/m² | mean, `[t−1h,t)` including midnight crossing |

Forecast records use **kind=forecast**; ERA5 remains **kind=reanalysis**.
Open-Meteo's speed processing from ICON native U/V and selected shortwave product
from native direct/diffuse fluxes are provider processing. No local U/V, radiation
formula, alternative radiation field or unit conversion is introduced.

`WeatherSite` retains configured logical identity, country, requested coordinates
and selection version. `WeatherGrid` retains independently returned coordinates
and required finite elevation. Existing shared geographic/elevation/scientific
bounds remain unchanged. The announced Open-Meteo/DWD ICON grid transition **after
30 November 2026** is product context. Valid changed returned coordinates/elevation
are accepted and preserved with raw snapshots, without changing site or model
identity. Synthetic post-transition-date tests exercise metadata tolerance, not
predictions about future provider behavior.

### Identity, validation, archive and replay

[ADR 0007](../../adr/0007-explicit-weather-output-query-selection.md), written
before its implementation, records the additive typed `WeatherOutputSelection`:
profile version, temperature/wind unit choices, GMT and Unix time. New forecast
canonical JSON/hash retains these alongside source/product/model, site/requested
coordinates/selection version, UTC window/partition and canonical variable set.
Absent optional output selection serializes exactly as before, preserving ERA5
query bytes/hashes. This is tested against the original historical query shape.
Mutable provider presentation/grid fields do not enter request identity.

The shared bounded JSON boundary is reused without increasing any historical
limit: 1 MiB, depth 16, 64 keys/object, 48 items/array, 4,096 characters/string/key,
128 characters/numeric token, 4,096 nodes, one site; strict success caps emitted
measurements at 72. Duplicate keys, invalid UTF-8/Unicode, NaN/Infinity, null,
boolean/string numeric values, missing fields, wrong units, wrong model echoes,
unequal arrays and missing/extra/duplicate/reversed/off-hour/outside timestamps
fail the complete parse with **zero records**, including late value failures.
Provider `error=true` with string `reason` becomes controlled `provider_rejected`;
no unchecked prose enters logs/exceptions/diagnostics. Unsupported errors fail
schema/content validation, without invented no-data outcomes or fallback.

Unchanged **HttpRetriever → ingest_resolved → LocalRawArchive → parser** handles
anonymous fixed-origin acquisition, finite existing retry/time budgets and bounded
Retry-After. Semantic/schema/content failures do not retry. Oversized/interrupted
bodies never publish complete acquisitions; safe complete malformed 200 bodies
remain archived before failed parsing. No credential loading, dotenv or API key
setting is added.

Original bytes retain SHA-256 content addressing and immutable independent
retrieval/parse histories. Same canonical query + same bytes shares one payload
with separate acquisition events. Changed bytes preserve both payload versions
and all retrieval/parse histories. Unknown forecast editions remain distinct by
original retrieval UUID, including identical-body reacquisitions; no run or
revision number is fabricated. Product/model/query are retained in retrieval
provenance; forecast report/parser/profile/schema/raw/retrieval linkage is explicit
in parse provenance and normalized records.

Shared replay constructs no HTTP client/retriever, loads no API credential,
performs no network/new acquisition and reproduces values, units, target/support,
kind/model/product, site/requested/returned grid/elevation, native identity,
business identity and raw linkage. Only new parse UUID/time differs. Tests verify
unchanged prior files and retrieval counts. Corrupt bytes/hash/retrieval linkage
and missing retrieval events fail without refetch.

### Vintage limitation and fallback policy

The latest Forecast API snapshot means **forecast available at acquisition time**,
not forecast known at a historical MIBEL cutoff and not necessarily one ICON-EU
run. Target time, acquisition completion and parse time remain separate.
Issue/model-run/publication/update times remain null without authoritative source
metadata. No Historical Forecast, Single Runs, Previous Runs or historical-vintage
reconstruction is implemented. Historical ERA5 cannot substitute for a forecast
vintage.

**ECMWF IFS HRES 9 km / models=ecmwf_ifs remains documentation only.** No fallback
requests, automatic switching, per-site substitution, model mixing or IFS repair
of missing ICON-EU fields/hours/errors exists. A separately authorized IFS
integration must have distinct product/query/profile and archive histories.
Lower-ranked models, electricity-price models and Stage 6 remain out of scope.

### Completion verification

One synthetic `synthetic_icon_eu.json` fixture (1,755 bytes), no downloaded body;
manifest records checksum/request context/profile/parser. The historical fixture
bytes/checksum remain unchanged. In-memory mutations cover errors, revisions and
grid changes. The previous six missing-model guard cases now verify the accepted
explicit forecast product for all six sites; all historical cases are retained.
Existing parser and integration cases are parameterized over both products.

| Gate executed for completion | Result |
| --- | --- |
| Historical ERA5/shared focused suite (`-k 'not forecast'`) | **169 passed**, 201 deselected |
| ICON-EU focused suite (`-k forecast`) | **201 passed**, 169 deselected |
| Complete Stage 5 unit/integration suite | **370 passed** |
| Full `python -m pytest` | **2,012 passed**, network-denied protection unchanged |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 150 files already formatted |
| `mypy src` | No issues in 59 source files |
| `pre-commit run --all-files` | All eight hooks passed |
| Explicit pre-commit on every changed/new file, without staging | All applicable hooks passed |
| `git diff --check`, untracked whitespace/diff review | Passed |

The historical count includes shared site/query checks and the two-product
fixture-manifest check. The forecast count includes the explicit legacy-query
compatibility test. Counts are disjoint and sum to the complete focused suite.
All 1,642 pre-Stage-5 regressions remain present; no old provider test or CI
configuration changed, and no skip was added.

### Completion change inventory

Relative to this task's dirty baseline, changed/added:

- Shared query contract `src/iberian_shakti/contracts/queries.py`, ADR 0007 and ADR index.
- Existing weather `profile.py`, `identity.py`, `adapter.py`, `schema.py`, `parser.py`.
- Existing weather profile/parser tests and `tests/integration/test_open_meteo_flow.py`;
  new `tests/unit/ingestion/weather/test_icon_eu_forecast.py`.
- New `tests/data/open_meteo/synthetic_icon_eu.json`; fixture manifest and README.
- Saved completion prompt and this report; README, architecture and runbook status/details.

The entire Stage 5 working tree (including prior untracked historical/selection
artifacts) remains unstaged for operator review. No branch, fetch, pull, rebase,
reset, restore, stash, staging, commit or push occurred. No provider request,
credential use, paid/cloud change or later-stage implementation occurred.

### Remaining controlled-live questions (not offline acceptance blockers)

Separately authorize real ICON-EU acquisition before claiming actual response
shape, 24-hour coverage, units, grid/elevation, preceding-hour shortwave behavior,
main/side-run composition, next-day availability before a chosen MIBEL cutoff,
provider errors, rate limits, response size/compression, grid-transition behavior,
service terms/attribution, historical archive completeness or true run
availability/publication timing. Historical ERA5 availability/delay and boundary
inclusivity also remain unverified here. No live validation or new model-selection
study is implied by offline acceptance.

**Phase 2 Stage 5 — PASS.** Historical ERA5 remains accepted; explicit ICON-EU
forecast ingestion satisfies all required offline engineering criteria. Phase 2
Stage 6 has not been started or authorized.
