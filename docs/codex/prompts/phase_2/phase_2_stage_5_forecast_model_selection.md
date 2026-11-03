# Iberian_Shakti — Phase 2 Stage 5
## Open-Meteo Forecast Model Selection Study

Perform a targeted evidence-based model-selection study to resolve the one remaining blocker in **Phase 2 Stage 5 — Open-Meteo integration**.

This task is:

```text
RESEARCH + COMPARISON + DECISION ONLY
```

It is **not**:

```text
a new Phase 2 readiness assessment
Stage 5 implementation
a provider live-validation task
Stage 6 work
```

Do not implement the selected model yet.

The required deliverable is a permanent engineering comparison report with:

```text
candidate screening
eligibility decisions
weighted scoring
ranking
one recommended primary model
one fallback model
decision rationale
remaining uncertainties
```

---

# 1. Baseline

Start with:

```bash
git status --short
git log --oneline --decorate -10
```

Expected committed baseline:

```text
branch: main

HEAD:
f8dee4c feat: complete Phase 2 ENTSO-E ingestion
```

The working tree is expected to contain the existing uncommitted Stage 5 implementation.

Do not require a clean tree.

Do not:

```text
fetch
pull
rebase
reset
restore
stash
create a branch
stage
commit
push
```

Preserve all existing Stage 5 work.

---

# 2. Read first

Read at minimum:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md

docs/codex/prompts/phase_2/
phase_2_stage_5_open_meteo_integration.md

docs/codex/reports/
phase_2_stage_5_open_meteo_report.md

src/iberian_shakti/ingestion/weather/
tests/unit/ingestion/weather/
tests/integration/test_open_meteo_flow.py
```

Understand precisely why Stage 5 currently has:

```text
PASS WITH GAPS
```

The existing blocker is:

```text
No exact Open-Meteo forecast model
was authoritatively selected.
```

Do not modify the existing Stage 5 implementation during this study.

---

# 3. Save this prompt first

Save this exact prompt as:

```text
docs/codex/prompts/phase_2/
phase_2_stage_5_forecast_model_selection.md
```

---

# 4. Deliverable

Create:

```text
docs/codex/reports/
phase_2_stage_5_forecast_model_selection.md
```

The report must be detailed enough that a later Codex task can implement the chosen model without reopening the model-selection question.

---

# 5. Project requirement

The selected weather forecast model will provide exogenous weather inputs for later Iberian electricity-price forecasting.

Current fixed Stage 5 weather variables:

```text
temperature_2m
wind_speed_10m
shortwave_radiation
```

Fixed sites:

```text
PT.lisbon
PT.porto
PT.braganca

ES.madrid
ES.zaragoza
ES.seville
```

Historical weather remains:

```text
Open-Meteo Historical Weather API
ERA5
hourly
kind=reanalysis
```

This study concerns only the **future forecast product**.

---

# 6. Forecasting use case

The weather forecast must support downstream:

```text
MIBEL day-ahead electricity-price forecasting
Portugal + Spain
```

The relevant operational horizon is approximately:

```text
D-1 → delivery day D
```

Therefore prioritize forecast quality around:

```text
~12–48 hour lead times
```

and require sufficient coverage for at least a complete next delivery day.

Do not rank models primarily on long-range 7–15 day performance.

---

# 7. Mandatory candidate set

Evaluate at minimum:

## A. DWD ICON-EU

Evaluate the explicit Open-Meteo individual model corresponding to:

```text
DWD ICON Europe
~7 km
regional Europe
```

Investigate:

```text
source-code licence
operational status
native temporal resolution
forecast horizon
update frequency
Iberian coverage
three required variables
Open-Meteo selector
Historical Forecast / Single Runs availability
```

---

## B. DWD ICON Global

Evaluate separately from ICON-EU.

Do not treat:

```text
ICON Global
ICON-EU
ICON Seamless
```

as the same model product.

---

## C. NOAA GFS Global

Evaluate the explicitly selectable GFS global product.

Investigate its relationship to:

```text
NOAA operational GFS
Unified Forecast System
FV3
```

Verify the current open-source licence from authoritative sources.

Determine the exact Open-Meteo product and selector appropriate for deterministic global GFS.

---

## D. ECMWF IFS HRES

Evaluate:

```text
ECMWF IFS HRES
9 km
```

Also investigate the relationship between:

```text
operational IFS HRES
and
OpenIFS
```

Important:

OpenIFS becoming open source does **not automatically prove** that the exact current operational HRES source tree is identical to the current OpenIFS release.

Document this distinction explicitly.

---

## E. ECMWF AIFS Single

Evaluate the currently operational deterministic AIFS product.

Verify:

```text
current version
open-weight status
licence
Anemoi source-code licence
spatial resolution
native temporal resolution
forecast horizon
variables
Open-Meteo availability
```

Do not assume that Open-Meteo's hourly-normalized output means AIFS itself is natively hourly.

---

# 8. Research challengers

Screen, but do not automatically consider eligible:

```text
GraphCast
FourCastNet / FourCastNet2
DWD AICON
```

Also discover any other credible open-source or open-weight model that may materially outperform or better fit the Stage 5 requirement.

Possible additional candidates may include other:

```text
European regional NWP
open operational NWP
open-weight AI weather models
```

but include them only when supported by authoritative evidence.

Do not inflate the report with marginal models.

---

# 9. Best Match is not a primary candidate

Open-Meteo:

```text
best_match
```

may be included as a reference strategy.

It must **not** automatically win the ranking.

The project requires deterministic, reproducible model identity.

`best_match` can change provider/model by:

```text
location
variable
forecast hour
provider availability
future Open-Meteo configuration
```

Therefore evaluate it only as:

```text
reference / benchmark strategy
```

unless you can demonstrate that its changing identity is compatible with the project's provenance and reproducibility requirements.

---

# 10. Seamless products

Treat provider-specific:

```text
seamless
```

products carefully.

A seamless forecast may combine multiple model domains or resolutions.

Do not rank a seamless product as equivalent to one explicitly pinned model.

If considered, explain:

```text
which underlying models can contribute
how identity is preserved
whether composition can change
whether replay can reproduce the exact composition
```

Prefer explicit individual-model identity when forecast quality is otherwise comparable.

---

# 11. Evidence hierarchy

Use this evidence hierarchy:

```text
1. official model/provider documentation
2. official Open-Meteo documentation/OpenAPI
3. official source-code repository/model card
4. peer-reviewed model papers
5. official verification studies
6. high-quality independent studies
7. secondary project repositories
```

Do not base the decision primarily on:

```text
blog rankings
SEO comparison pages
generic weather websites
unsupported community opinions
```

For every material claim, record the source URL/reference in the report.

---

# 12. Open-source definition

Do not use the term "open source" loosely.

For every candidate distinguish separately:

```text
model source code open?
inference code open?
weights open?
forecast output open?
commercial use permitted?
redistribution permitted?
```

Examples of possible categories:

```text
fully open-source model code
open-weight model
open forecast data only
public API but proprietary model
mixed licensing
```

Record exact licences where authoritative evidence exists.

---

# 13. Hard eligibility gates

A candidate cannot be the Stage 5 primary model unless it satisfies all required gates.

## Gate A — Geography

Must support all six:

```text
Lisbon
Porto
Bragança
Madrid
Zaragoza
Seville
```

No location-specific model switching.

---

## Gate B — Required variables

Must support:

```text
temperature_2m
wind_speed_10m
shortwave_radiation
```

or a clearly documented native equivalent that Open-Meteo deterministically maps to those exact variables.

Do not assume variable availability from generic model descriptions.

Verify it.

---

## Gate C — Day-ahead horizon

Must provide sufficient forecast support for:

```text
complete next-day delivery forecast
```

Prefer comfortable coverage beyond 48 hours.

---

## Gate D — Temporal resolution

Strong preference:

```text
native hourly
```

for the relevant day-ahead horizon.

This distinction is critical.

Open-Meteo normalizes many model products to hourly output.

Therefore explicitly distinguish:

```text
native hourly model output
vs
Open-Meteo interpolation to hourly
```

A 3-hourly or 6-hourly native model should receive a substantial penalty unless evidence shows it materially improves forecast quality enough to justify interpolation.

---

## Gate E — Explicit identity

There must be a stable explicit:

```text
model/product identifier
```

that can become part of:

```text
canonical query
provenance
archive metadata
replay
model-version documentation
```

No implicit default selection.

---

## Gate F — Operational availability

The candidate must have a credible operational forecast data source suitable for repeatable acquisition.

Research code alone is insufficient.

---

## Gate G — Legal usability

The selected source/model/data must be usable for this project under documented terms.

Separate:

```text
prototype/non-commercial API terms
commercial use
source-code licence
forecast-data licence
attribution
redistribution
```

Do not make legal claims beyond published terms.

---

# 14. Strong preference criteria

Candidates passing the hard gates should then be evaluated on:

```text
forecast skill
Iberian relevance
spatial resolution
update frequency
historical forecast availability
forecast-vintage reconstruction
operational maturity
open-source reproducibility
integration simplicity
resource requirements
future maintainability
```

---

# 15. Historical forecast availability is important

Later model training must avoid look-ahead leakage.

Therefore investigate whether each candidate has archived historical forecasts corresponding to what was actually known at earlier forecast issuance times.

Check:

```text
Open-Meteo Historical Forecast API
Open-Meteo Single Runs API
provider-native historical archives
```

Record:

```text
available since when
run-level identity available?
historical initialization time available?
lead-time reconstruction possible?
```

A model with excellent current forecasts but no usable historical forecast vintages may be less valuable for Iberian_Shakti ML training.

---

# 16. Do not confuse ERA5 with forecast vintages

ERA5 is:

```text
reanalysis
```

It is not a historical day-ahead weather forecast.

Do not propose using ERA5 as a substitute for vintage-correct future weather forecasts in the production feature path.

ERA5 remains appropriate for historical observed/reanalysis weather features.

---

# 17. Forecast skill

Search for credible comparative forecast-skill evidence.

Prioritize evidence relevant to:

```text
Europe
Iberian Peninsula
near-surface temperature
10 m wind
solar radiation
12–48 h lead time
```

If direct Iberian comparisons are unavailable, say so.

Do not convert generic headline claims such as:

```text
"model X beats model Y globally"
```

into an Iberian-specific conclusion without evidence.

---

# 18. Electricity-price relevance

Weather model ranking should reflect the downstream electricity-price use case.

Consider especially:

```text
10 m wind accuracy
solar-radiation accuracy
temperature accuracy
temporal timing errors
regional spatial fidelity
forecast availability before price prediction
```

Do not rank solely on generic atmospheric metrics such as:

```text
500 hPa geopotential
global ACC
tropical cyclone track
```

unless they provide useful secondary evidence.

---

# 19. Solar radiation

Treat:

```text
shortwave_radiation
```

as a first-class requirement.

Verify whether the model:

```text
directly predicts radiation fields
or
Open-Meteo derives them
```

Record the derivation if known.

Current Stage 5 semantics require:

```text
shortwave_radiation
W/m²
preceding-hour mean
```

Do not silently substitute:

```text
instantaneous radiation
irradiance at another surface
daily radiation sum
```

---

# 20. Wind

Verify:

```text
10 m wind availability
native U/V vs speed
Open-Meteo derivation
temporal resolution
```

Do not treat wind forecasts at:

```text
80 m
100 m
120 m
```

as equivalent to the selected Stage 5 `wind_speed_10m`.

Later energy modelling may add hub-height wind separately.

Not in this decision.

---

# 21. Spatial resolution

Record:

```text
native horizontal resolution
regional vs global domain
grid structure where relevant
Open-Meteo grid selection/downscaling behavior
```

Do not assume:

```text
higher resolution = higher forecast skill
```

Treat resolution as one factor, not the decision itself.

---

# 22. Update frequency and latency

Record:

```text
model initialization frequency
typical publication/update frequency
forecast horizon
```

If reliable evidence exists, investigate whether a useful run would normally be available before the intended MIBEL forecast issuance time.

Do not invent exact operational latency where not documented.

Reserve real timing verification for controlled live validation.

---

# 23. Architecture compatibility

The selected model must fit the existing Stage 5 architecture:

```text
explicit request identity
bounded HTTP retrieval
immutable raw archive
retrieval provenance
strict parser
normalized WeatherMeasurement
parse provenance
offline replay
```

Prefer a model that can be integrated without creating:

```text
new GPU infrastructure
local NWP execution
large model checkpoints
new weather-serving service
new orchestration system
```

Stage 5 is an ingestion integration, not an atmospheric-model hosting project.

---

# 24. Open-Meteo integration

For each serious candidate, identify:

```text
Open-Meteo endpoint
exact model selector
forecast API support
Historical Forecast support
Single Runs support
required-variable support
```

Use official Open-Meteo documentation or OpenAPI definitions.

Do **not** make a provider API request.

Documentation access is allowed.

---

# 25. Candidate categories

Classify every candidate into one:

```text
ELIGIBLE — primary candidate
ELIGIBLE — fallback candidate
RESEARCH CHALLENGER
INELIGIBLE
```

Every ineligible model must have a precise reason.

Examples:

```text
missing shortwave radiation
not hourly enough
no operational feed
licence incompatible
not available over Iberia
no deterministic selector
requires local GPU execution
no suitable historical forecasts
```

---

# 26. Scoring model

After applying hard gates, score eligible candidates out of **100**.

Use these weights:

```text
25  forecast-skill evidence relevant to Iberia/Europe
15  native temporal resolution + day-ahead horizon
10  spatial coverage/resolution for Iberia
10  required variable fidelity
15  historical forecast / vintage reconstruction
10  operational maturity + update frequency
10  openness / licensing / reproducibility
 5  implementation simplicity in Iberian_Shakti
---
100
```

Scores must be evidence-based.

Do not give high precision unsupported scores such as:

```text
87.43
```

Use whole-number scores and explain each component.

---

# 27. Evidence confidence

For each candidate assign:

```text
HIGH
MEDIUM
LOW
```

confidence to the ranking.

The confidence should reflect:

```text
quality of evidence
Iberian-specific validation
current documentation
historical availability
licensing clarity
```

A model with excellent theoretical properties but weak relevant evidence should not receive high confidence.

---

# 28. Required comparison table

Produce a table containing at minimum:

```text
Rank
Model
Provider
Model type
Operational?
Open-source/open-weight status
Licence
Coverage
Native spatial resolution
Native temporal resolution
Forecast horizon
Update frequency
temperature_2m
wind_speed_10m
shortwave_radiation
Explicit Open-Meteo selector
Historical forecast archive
Run-level/vintage reconstruction
Integration complexity
Weighted score
Confidence
Verdict
```

---

# 29. Required ranking

Produce:

## Ranking A — best model for Iberian_Shakti Stage 5

Rank all eligible candidates.

## Ranking B — open-source/open-weight models only

Rank only candidates satisfying the report's documented openness definition.

This prevents proprietary/open-data-only systems from obscuring the open-source comparison.

---

# 30. Required final decision

The report must select exactly:

```text
PRIMARY MODEL
```

and:

```text
FALLBACK MODEL
```

unless an actual hard blocker makes selection impossible.

Do not end with:

```text
"all models have advantages"
```

or:

```text
"more research is needed"
```

without making a recommendation.

A recommendation is required.

---

# 31. Decision quality

The winning model does not need to have the highest raw weather-skill reputation.

The correct decision is:

```text
best overall model for this specific
Iberian_Shakti Stage 5 architecture
and downstream day-ahead electricity-price use case
```

Balance:

```text
forecast skill
hourly fidelity
Iberian coverage
three variables
vintage availability
reproducibility
licensing
operational reliability
integration cost
```

---

# 32. Important known candidates

Do not assume these facts without verifying them, but investigate them:

```text
DWD ICON model code:
open-source BSD-3-Clause

NOAA UFS Weather Model:
open-source; operational GFS relationship

ECMWF OpenIFS:
made open source in 2026

ECMWF AIFS:
open model weights / Anemoi ecosystem

GraphCast:
open code but licensing of pretrained weights
requires separate examination

FourCastNet:
open-source research model

AICON:
operational DWD AI weather model;
verify source/weight openness,
variables and temporal resolution
```

---

# 33. Important distinction: OpenIFS vs IFS HRES

Do not claim:

```text
OpenIFS == current operational IFS HRES
```

without evidence.

Document:

```text
which operational IFS cycle
the current OpenIFS release derives from
```

and whether that matters for reproducibility.

---

# 34. AI weather models

Do not favour AI weather models simply because they are newer.

For:

```text
AIFS
GraphCast
FourCastNet
AICON
other AI candidates
```

evaluate:

```text
native output cadence
required surface fields
radiation availability
operational maturity
run initialization
historical forecast accessibility
licence
hardware/runtime needs
Open-Meteo availability
```

A 6-hourly AI model may be less suitable than an hourly physics model for this use case even if its global headline weather scores are better.

---

# 35. No empirical provider calls

This task is documentation/research only.

Do not:

```text
call Open-Meteo Forecast API
download forecasts
benchmark live models
probe endpoints
use credentials
perform paid/cloud operations
```

Do not infer success from HTTP calls.

Controlled provider validation is a later Phase 2 stage.

---

# 36. No implementation

Do not modify:

```text
src/
tests/
existing fixtures
shared contracts
```

except for the prompt/report documentation requested here.

Do not implement the winning model.

The next operator-reviewed task will do that separately.

---

# 37. Previous Grid Intelligence evidence

If you inspect:

```text
https://github.com/xucenying/grid-intelligence
```

note carefully:

the previous project used the Open-Meteo Forecast API but did **not** explicitly pin an individual weather model in its forecast request.

Therefore it is evidence that:

```text
Open-Meteo forecasts were operationally usable
```

but **not** evidence that:

```text
ICON
GFS
IFS
or another exact model
```

was previously validated by that project.

Do not misstate this.

---

# 38. Report structure

Use approximately:

```text
1. Executive decision
2. Stage 5 requirement
3. Methodology
4. Evidence hierarchy
5. Candidate discovery
6. Hard-gate screening
7. Candidate technical profiles
8. Open-source/licensing comparison
9. Iberian/day-ahead relevance
10. Historical forecast/vintage analysis
11. Weighted scoring
12. Ranking A — overall Stage 5 suitability
13. Ranking B — open-source/open-weight only
14. Primary model recommendation
15. Fallback recommendation
16. Rejected/challenger models
17. Remaining live-validation questions
18. Implementation contract for the next task
```

---

# 39. Implementation contract

End the report with a compact contract for the future implementation task containing:

```text
selected provider
selected model
exact Open-Meteo selector
endpoint
required variables
required units
forecast horizon/window constraint
native temporal-resolution assumption
six sites
model identity/provenance requirement
historical-vintage limitation
fallback model
```

Do not implement it.

---

# 40. Final response

Return:

1. exact report path;
2. models investigated;
3. models eliminated by hard gates;
4. final ranked table;
5. winning model;
6. fallback model;
7. winning weighted score;
8. confidence level;
9. the 3–5 decisive reasons;
10. remaining live-validation questions;
11. exact Git status;
12. confirmation that no implementation/provider request/staging/commit/push occurred.

Finish with:

```text
Phase 2 Stage 5 forecast-model selection — DECISION COMPLETE.

Primary model:
<model>

Fallback model:
<model>

The existing Stage 5 implementation has not been modified.

Stage 5 forecast implementation remains pending operator review of this decision.
```

If the available evidence genuinely cannot support a responsible decision, finish instead with:

```text
Phase 2 Stage 5 forecast-model selection — DECISION BLOCKED.
```

but this outcome requires a specific hard evidentiary blocker, not general uncertainty.

Stop there.
