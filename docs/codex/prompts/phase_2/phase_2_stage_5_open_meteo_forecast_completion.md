# Iberian_Shakti — Phase 2 Stage 5 Completion
## Implement DWD ICON-EU Forecast Integration and Close Stage 5

Complete the existing **Phase 2 Stage 5 — Open-Meteo integration**.

This task resolves the only remaining Stage 5 blocker and should move Stage 5 from:

```text
PASS WITH GAPS
```

to:

```text
PASS
```

only if all required offline engineering criteria pass.

This is **not**:

```text
a new readiness assessment
a new model-selection study
Stage 6 work
a live-provider validation task
an electricity-price model implementation task
```

---

# 1. Authoritative selection decision

The forecast-model selection study is complete.

Read:

```text
docs/codex/reports/
phase_2_stage_5_forecast_model_selection.md
```

The accepted primary model is:

```text
Provider:
Open-Meteo public Forecast API

Upstream:
DWD

Model:
ICON-EU deterministic European domain

Approximate native resolution:
~7 km

Exact Open-Meteo selector:
models=icon_eu
```

Endpoint:

```text
https://api.open-meteo.com/v1/forecast
```

The accepted fallback is:

```text
ECMWF IFS HRES 9 km
models=ecmwf_ifs
```

but the fallback is **documentation only in this task**.

Do **not** implement automatic fallback.

Do **not** request both models.

Do **not** mix model outputs.

Do **not** use IFS to fill missing ICON-EU values.

Do **not** implement lower-ranked models.

Stage 5 requires one deterministic selected forecast product, and that product is:

```text
ICON-EU / icon_eu
```

---

# 2. Ranked model context

The accepted selection report ranked:

```text
1. DWD ICON-EU              85/100
2. ECMWF IFS HRES           83/100
3. DWD ICON Global          82/100
4. NOAA GFS Global          80/100
5. UKMO Global              75/100
6. ARPEGE Europe            74/100
7. ECMWF AIFS Single v2     68/100
```

This implementation task does **not** reopen this ranking.

Do not reconsider the winner unless implementation uncovers a genuine hard incompatibility contradicting the accepted selection evidence.

If such a blocker is found:

```text
stop Stage 5 at PASS WITH GAPS
document the exact blocker
do not silently switch to IFS
```

---

# 3. Baseline

Start with:

```bash
git status --short
git log --oneline --decorate -10
```

Expected committed HEAD:

```text
f8dee4c feat: complete Phase 2 ENTSO-E ingestion
```

Expected branch:

```text
main
```

The working tree is **not expected to be clean**.

It already contains:

```text
existing Stage 5 historical ERA5 implementation
Stage 5 prompt/report
forecast-model selection prompt/report
```

Preserve all current Stage 5 work.

Do not:

```text
fetch
pull
rebase
reset
restore
stash
checkout away changes
create a branch
```

---

# 4. Read before implementation

Read at minimum:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md

docs/codex/prompts/phase_2/
phase_2_stage_5_open_meteo_integration.md

docs/codex/reports/
phase_2_stage_5_open_meteo_report.md

docs/codex/prompts/phase_2/
phase_2_stage_5_forecast_model_selection.md

docs/codex/reports/
phase_2_stage_5_forecast_model_selection.md
```

Also inspect:

```text
src/iberian_shakti/ingestion/weather/

tests/unit/ingestion/weather/

tests/integration/test_open_meteo_flow.py

tests/data/open_meteo/
```

and all shared contracts used by:

```text
WeatherMeasurement
WeatherSite
WeatherGrid
SourceRequest
SystemQuery / weather query identity
HttpRetriever
LocalRawArchive
retrieval provenance
parse provenance
offline replay
semantic outcomes
```

Reuse existing architecture.

Do not create a second weather ingestion framework.

---

# 5. Save this completion prompt first

Before implementation, save this exact prompt as:

```text
docs/codex/prompts/phase_2/
phase_2_stage_5_open_meteo_forecast_completion.md
```

Preserve all earlier Stage 5 prompts unchanged.

---

# 6. Existing historical path remains accepted

The existing historical product is already accepted offline:

```text
Open-Meteo Historical Weather API
ERA5
hourly
kind=reanalysis
```

Endpoint:

```text
https://archive-api.open-meteo.com/v1/archive
```

Model:

```text
era5
```

Do not redesign or weaken it.

Historical variables remain:

```text
temperature_2m
wind_speed_10m
shortwave_radiation
```

Historical ERA5 must remain green after forecast implementation.

---

# 7. Fixed sites

Use exactly the existing six versioned sites:

```text
PT.lisbon
38.72, -9.14

PT.porto
41.15, -8.61

PT.braganca
41.81, -6.76

ES.madrid
40.42, -3.70

ES.zaragoza
41.65, -0.89

ES.seville
37.39, -5.98
```

Do not:

```text
geocode
change coordinates
add sites
remove sites
average sites
perform regional interpolation
```

Preserve:

```text
logical site identity
requested coordinates
returned grid coordinates
returned elevation
```

as distinct concepts.

---

# 8. Implement forecast product

Implement:

```text
Open-Meteo Forecast API
DWD ICON-EU
models=icon_eu
```

Endpoint:

```text
https://api.open-meteo.com/v1/forecast
```

Use anonymous access.

Do not add:

```text
OPEN_METEO_API_KEY
dotenv loading
API credentials
CI secrets
commercial endpoint
```

---

# 9. Exact model identity

The request must explicitly include:

```text
models=icon_eu
```

The selected forecast model must never depend on Open-Meteo's implicit default.

Do not allow:

```text
best_match
icon_seamless
icon_global
icon_d2
dwd_aicon_global_native
ecmwf_ifs
```

to substitute for the selected primary product.

Model identity must be included in:

```text
canonical query identity
report/product identity
profile identity
normalized records where supported
retrieval provenance
parse provenance
replay identity
```

A request missing or changing `icon_eu` must fail before successful acquisition/parsing.

---

# 10. Forecast variables

Request exactly:

```text
temperature_2m
wind_speed_10m
shortwave_radiation
```

No additional weather variables belong in Stage 5.

Do not add:

```text
humidity
cloud_cover
precipitation
wind_direction
wind_gusts
pressure
weather_code
solar-panel irradiance
daily summaries
```

---

# 11. Units

Request explicit canonical units:

```text
temperature_unit=celsius
wind_speed_unit=ms
```

Validate returned units:

```text
temperature_2m:
°C

wind_speed_10m:
m/s

shortwave_radiation:
W/m²
```

Do not silently convert unexpected units.

Do not implement generic unit-conversion infrastructure.

---

# 12. Time output

Request:

```text
timezone=GMT
timeformat=unixtime
```

Use explicit UTC timestamps.

Do not request local timestamps.

Do not derive source records using:

```text
Europe/Lisbon DST
Europe/Madrid DST
```

for the weather API response.

Market-day conversion belongs elsewhere.

---

# 13. Supported forecast window

Use one deterministic bounded request per:

```text
site
UTC weather day
```

The selected product should request one complete explicit UTC day:

```text
00:00 UTC
through
next 00:00 UTC
```

using the provider's date selectors consistently with the existing Stage 5 query abstraction.

Do not rely on Open-Meteo's default multi-day forecast payload.

Do not request an unbounded horizon.

Do not fetch seven or sixteen days simply because the API supports them.

---

# 14. Day-ahead intent

The Stage 5 forecast product is intended for approximately:

```text
12–48 hour lead times
```

for downstream MIBEL day-ahead price prediction.

ICON-EU main-cycle output is documented as native hourly through approximately:

```text
78 hours
```

which safely covers this use case.

Do not support Stage 5 forecast windows that require:

```text
3-hourly
or
coarser ICON-EU output
```

as if those were native hourly observations.

Reject unsupported forecast-window semantics rather than interpolate.

---

# 15. No local temporal interpolation

Do not:

```text
interpolate
forward-fill
back-fill
resample
smooth
repeat values
```

to manufacture hourly weather observations.

Selected forecast records must correspond to actual supported hourly source output.

Missing expected selected timestamps must fail according to the strict forecast coverage policy.

---

# 16. Important provider-cycle limitation

Do not infer a specific ICON-EU model run merely from:

```text
models=icon_eu
```

The latest Forecast API may represent the currently available product snapshot.

Keep separate:

```text
forecast target time
model identity
acquisition completion time
parse time
```

Do not fabricate:

```text
model initialization time
run time
issue time
publication time
provider update time
```

unless authoritative response metadata explicitly supplies it.

---

# 17. Forecast vintage safety

Current Open-Meteo Forecast API acquisition means:

```text
forecast available at acquisition time
```

It does **not** mean:

```text
forecast known at a historical MIBEL cutoff
```

Do not implement:

```text
Historical Forecast API
Single Runs API
Previous Runs API
historical forecast-vintage reconstruction
```

in this task.

Those require separately authorized work.

Document this limitation clearly.

---

# 18. Weather kind

Historical:

```text
kind=reanalysis
```

Forecast:

```text
kind=forecast
```

Never merge or confuse them.

---

# 19. Variable scientific semantics

Preserve the accepted semantics exactly.

## temperature_2m

Normalize as:

```text
variable:
temperature

height:
2 m

unit:
°C

statistic:
instant

support:
ValidInstant(t)
```

---

## wind_speed_10m

Normalize as:

```text
variable:
wind_speed

height:
10 m

unit:
m/s

statistic:
instant

support:
ValidInstant(t)
```

Open-Meteo may derive speed from ICON native 10 m U/V components.

That is acceptable provider processing.

Do not reconstruct U/V locally.

---

## shortwave_radiation

Normalize as:

```text
variable:
shortwave_radiation

unit:
W/m²

statistic:
mean

support:
[t - 1 hour, t)
```

This represents preceding-hour mean global horizontal shortwave radiation.

Do not normalize it as:

```text
instant
```

Do not substitute:

```text
shortwave_radiation_instant
direct_radiation
diffuse_radiation
direct_normal_irradiance
```

for the selected Stage 5 variable.

---

# 20. ICON radiation provenance

The selection report established that ICON's native direct and diffuse shortwave fluxes support Open-Meteo's exposed:

```text
shortwave_radiation
```

Do not implement a project-local radiation formula.

Treat Open-Meteo's selected `shortwave_radiation` field as the provider product.

Preserve original raw JSON for audit.

---

# 21. Strict JSON validation

Extend the existing strict Stage 5 JSON parser/profile for forecast responses.

Validate at minimum:

```text
latitude
longitude
elevation

timezone
utc_offset_seconds

hourly.time

hourly.temperature_2m
hourly.wind_speed_10m
hourly.shortwave_radiation

hourly_units
```

Validate array-length equality.

Reject:

```text
duplicate JSON keys
NaN
Infinity
invalid UTF-8
invalid Unicode
null selected value
boolean selected value
string numeric value
wrong unit
missing selected variable
duplicate timestamp
unordered timestamp
invalid timestamp
off-hour timestamp
out-of-window timestamp
array length mismatch
unsupported response structure
```

Late validation failure must produce:

```text
zero normalized records
```

Never partial success.

---

# 22. Forecast coverage

For a successful one-day forecast parse, require:

```text
24 ordered hourly UTC timestamps
```

and:

```text
72 normalized measurements
```

for:

```text
24 temperature
24 wind
24 shortwave
```

unless a documented product/calendar condition in the selected UTC representation justifies otherwise.

Because this is UTC:

```text
DST must not create 23/25-hour weather days
```

Do not apply local DST day lengths.

---

# 23. Requested vs returned coordinates

Preserve existing design:

```text
WeatherSite
→ requested logical coordinates

WeatherGrid
→ returned provider coordinates/elevation
```

Do not replace configured site coordinates with returned grid coordinates.

Returned coordinates may change because of provider processing/grid changes.

That must remain visible in archived/provenance evidence.

---

# 24. Announced ICON grid transition

The selection report identified an Open-Meteo/DWD ICON grid transition after:

```text
30 November 2026
```

Do not assume immutable returned grid geometry merely because:

```text
model_id=icon_eu
```

The profile must tolerate source grid metadata changing where existing contracts permit it while preserving:

```text
logical site identity
requested coordinates
returned grid coordinates
elevation
raw response
```

Do not silently change model identity because of a grid transition.

Do not preemptively implement future provider behavior that is not documented.

Document the transition as product context.

---

# 25. Parser bounds

Reuse existing bounded Stage 5 JSON protections.

Maintain finite limits for:

```text
response bytes
JSON depth
keys/object
array length
string length
numeric token length
node count
measurement count
one site/request
```

Do not weaken existing historical bounds merely to support forecast data.

If forecast requires a justified additive bound change, document it explicitly and test it.

---

# 26. Structured provider errors

Reuse the existing Open-Meteo structured error handling.

A response such as:

```json
{
  "error": true,
  "reason": "..."
}
```

must never be interpreted as weather observations.

Provider prose must not be blindly written to:

```text
logs
exceptions
provenance diagnostics
```

Map only safe controlled categories.

Do not invent:

```text
no_data
```

semantics from unsupported error forms.

---

# 27. HTTP behavior

Reuse existing shared `HttpRetriever`.

Do not introduce provider-specific concurrency or retry infrastructure.

Preserve existing finite:

```text
attempt limits
backoff
phase timeout
attempt timeout
operation budget
Retry-After handling
```

Semantic/schema/content failures must not retry.

Oversized or interrupted responses must not become successful archived acquisitions.

---

# 28. Archive

Reuse unchanged:

```text
HttpRetriever
→ ingest_resolved
→ LocalRawArchive
→ parser
```

Preserve:

```text
SHA-256 original bytes
immutable content-addressed raw storage
retrieval event
parse event
profile version
parser version
canonical query
```

Do not create a forecast-specific mutable cache as authoritative evidence.

---

# 29. Forecast corrections/revisions

For the same canonical forecast query:

```text
same bytes
→ one content object
→ separate acquisition histories
```

and:

```text
changed bytes
→ preserve both raw payload versions
→ preserve both retrieval histories
```

Never overwrite the earlier forecast.

This is important because weather forecasts may change between acquisitions.

---

# 30. Offline replay

Implement forecast replay through the existing replay architecture.

Replay must perform:

```text
zero HTTP
zero client construction
zero API credential loading
zero new acquisition
```

Replay must reproduce:

```text
forecast values
units
target timestamps
support semantics
kind=forecast
model=icon_eu
site identity
requested coordinates
returned grid coordinates
elevation
product/report identity
raw linkage
```

Only new parse-event UUID/time may differ where existing replay semantics permit it.

Corrupt:

```text
raw bytes
hash
retrieval linkage
```

must fail without refetch.

---

# 31. Forecast fixture

Add a small synthetic provider-shaped ICON-EU forecast fixture.

Do not download a real Open-Meteo body.

Synthetic fixture should represent:

```text
models=icon_eu request identity

24 UTC hours

temperature_2m
wind_speed_10m
shortwave_radiation

returned latitude
returned longitude
elevation

correct units
```

Update fixture manifest/checksum conventions.

Prefer one canonical fixture plus in-memory mutations.

Do not create a large fixture catalogue.

---

# 32. Forecast profile/versioning

Do not silently change the existing historical ERA5 semantic version.

Historical parser currently remains independently versioned.

Create an additive forecast product/profile/parser identity following current repository conventions.

Conceptually:

```text
open_meteo.icon_eu.hourly
```

and an explicit version such as:

```text
0.1.0
```

if consistent with existing version conventions.

Do not invent a versioning pattern that conflicts with the current code.

Forecast and historical identities must remain distinguishable.

---

# 33. Canonical forecast query

Canonical identity must include at minimum:

```text
provider=open_meteo

product=forecast ICON-EU

model=icon_eu

profile/version

logical site

requested latitude/longitude

selection version

UTC query window

selected variable set

unit selections

time-format/timezone selections
```

Do not include mutable provider presentation fields as business identity.

Do not omit model identity.

---

# 34. Tests — model selection enforcement

Add tests proving:

```text
models=icon_eu is always explicit
```

and:

```text
best_match rejected
icon_seamless rejected
icon_global rejected
icon_d2 rejected
AICON rejected
ecmwf_ifs rejected as primary
```

Do not allow caller-provided arbitrary model override for the primary product.

---

# 35. Tests — all six sites

Test:

```text
PT.lisbon
PT.porto
PT.braganca
ES.madrid
ES.zaragoza
ES.seville
```

Prove:

```text
correct site identity
correct requested coordinates
correct country
correct profile/model identity
```

Do not require six independent large fixtures if parameterized tests are sufficient.

---

# 36. Tests — weather semantics

Test:

```text
temperature:
instant

wind:
instant

shortwave:
preceding-hour mean
```

Verify:

```text
shortwave at timestamp t
→ support [t−1h, t)
```

including midnight-crossing support.

---

# 37. Tests — strict parser failures

At minimum test:

```text
missing temperature
missing wind
missing shortwave

wrong temperature unit
wrong wind unit
wrong radiation unit

null
NaN
Infinity
boolean
string numeric

array mismatch
duplicate timestamp
reversed timestamp
off-hour timestamp
missing hour
extra hour
outside requested window

wrong model query identity
wrong site query identity
wrong profile
provider error
oversized JSON
excessive nesting
```

All failure cases must produce no partial normalized output.

---

# 38. Tests — archive/revision

Prove:

```text
same canonical query + same body
→ shared content
→ separate retrieval events
```

and:

```text
same canonical query + changed body
→ both contents retained
→ both histories retained
```

---

# 39. Tests — replay

Prove:

```text
forecast replay
→ zero network
→ same normalized values
→ same support
→ same site/grid metadata
→ same model identity
→ same raw linkage
```

Also test:

```text
corrupt raw
corrupt hash
missing retrieval linkage
```

fail safely without refetch.

---

# 40. Keep IFS fallback documentation only

The accepted fallback is:

```text
ECMWF IFS HRES
models=ecmwf_ifs
```

Do not implement runtime fallback behavior.

Do not add automatic logic such as:

```python
try ICON
except:
    use IFS
```

Do not use IFS to repair:

```text
missing site
missing variable
missing hour
provider error
```

Those failures must remain visible.

A future IFS integration must use a separate:

```text
product identity
canonical query
profile
archive history
```

if explicitly authorized.

---

# 41. Do not implement lower-ranked models

Do not implement:

```text
ICON Global
GFS
UKMO
ARPEGE
AIFS
GraphCast
FourCastNet
AICON
WeatherNext
AIGFS
```

The ranking study is complete.

Adding all candidate models would increase complexity without helping Stage 5 acceptance.

---

# 42. Do not implement electricity-price models

The later modelling discussion is out of scope.

Do not implement:

```text
N-HiTS
LightGBM
XGBoost price forecasting
TFT
iTransformer
PatchTST
Chronos
stacking ensemble
SHAP
model training
feature engineering
```

Those belong to later phases.

---

# 43. No live Open-Meteo request

This remains an offline engineering task.

Do not:

```text
call Open-Meteo
probe icon_eu
download current forecast data
download historical forecast data
call Single Runs
call Historical Forecast
perform provider timing tests
```

Use:

```text
official documentation already retained
synthetic fixtures
offline tests
```

Controlled provider validation remains a later Phase 2 stage.

---

# 44. Update Stage 5 report

Update:

```text
docs/codex/reports/
phase_2_stage_5_open_meteo_report.md
```

Do not erase the original history.

The report must preserve:

```text
initial PASS WITH GAPS
reason:
forecast model not previously selected
```

Then record:

```text
forecast-model selection completed
primary:
DWD ICON-EU
selector:
icon_eu

fallback:
ECMWF IFS HRES
selector:
ecmwf_ifs
documentation only
```

Explain that the accepted operator decision closed the former blocker.

---

# 45. Stage 5 final report content

Document:

```text
historical ERA5 product
forecast ICON-EU product

endpoints
profile/parser versions
six sites
variables
units

native hourly assumption
supported forecast window

temperature support
wind support
shortwave support

requested vs returned coordinates
elevation

canonical query identity
model identity

archive
revisions
provenance
replay

forecast-vintage limitation
grid-transition context

fallback policy
```

---

# 46. Preserve selection report

Do not modify the substance of:

```text
docs/codex/reports/
phase_2_stage_5_forecast_model_selection.md
```

unless a factual cross-reference/path correction is necessary.

Do not rewrite the ranking after implementation.

---

# 47. Focused Stage 5 test suite

Run the complete Stage 5 weather test suite separately.

Report:

```text
historical ERA5 tests
forecast ICON-EU tests
combined focused Stage 5 count
```

All Stage 5 tests must pass.

---

# 48. Regression protection

All previous work must remain intact:

```text
Phase 1 OMIE

Phase 2 Stage 1
shared ingestion foundation

Phase 2 Stage 2
REN

Phase 2 Stage 3
ESIOS

Phase 2 Stage 4
ENTSO-E

Stage 5 historical ERA5

GitHub CI configuration
```

Do not weaken earlier contracts.

Do not delete tests.

Do not add skips merely to obtain green status.

---

# 49. Full validation

Run:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
pre-commit run --all-files
```

Also run the focused Stage 5 suite separately.

The existing network-denied pytest protection must remain enabled.

---

# 50. Stage 5 PASS criteria

Stage 5 may become:

```text
PASS
```

only when all of these are true:

```text
Historical ERA5 ingestion remains PASS

ICON-EU forecast product implemented

models=icon_eu explicitly pinned

no best_match fallback

all six sites supported

temperature_2m implemented
wind_speed_10m implemented
shortwave_radiation implemented

temperature support = instant
wind support = instant
shortwave support = preceding-hour mean

units validated

UTC hourly coverage enforced

no interpolation/filling/resampling

requested and returned coordinates remain distinct

elevation retained

strict bounded JSON parsing works

structured provider errors handled

immutable archive works

same-body reacquisition works

changed-body forecast revisions preserved

offline replay works

forecast identity preserved in replay

all focused Stage 5 tests pass

all previous regression tests pass

Ruff passes
format check passes
mypy passes
pre-commit passes

git diff --check passes
```

---

# 51. PASS WITH GAPS conditions

Do **not** force Stage 5 to PASS.

Keep:

```text
PASS WITH GAPS
```

if any required offline engineering item remains unresolved.

Examples:

```text
icon_eu cannot be represented safely
required variable semantics unsupported
hourly coverage cannot be enforced
forecast identity cannot be preserved
archive/replay incomplete
existing regressions fail
```

Document the precise blocker.

Do not silently choose another ranked model.

---

# 52. Controlled-live validation remains separate

Even if Stage 5 becomes PASS offline, explicitly reserve:

```text
real icon_eu request

actual response structure

actual 24-hour coverage

actual units

actual grid coordinates/elevation

actual shortwave behavior

actual main/side run behavior

availability before chosen MIBEL cutoff

real provider errors

rate limits

response size/compression

grid transition behavior

service terms / attribution

historical archive completeness

true run availability/publication timing
```

These are not blockers for offline Stage 5 engineering acceptance.

---

# 53. Git rules

Do not:

```text
stage
commit
push
create a branch
```

Leave the entire Stage 5 change set for operator review.

---

# 54. Final response

Return a concise engineering summary containing:

```text
baseline branch
baseline HEAD

files changed

historical profile/parser versions

forecast profile/parser versions

primary model:
DWD ICON-EU

selector:
icon_eu

fallback:
ECMWF IFS HRES
documentation only

endpoint

six sites

three variables

units

time semantics

forecast window/horizon rule

requested/grid coordinate handling

elevation handling

strict parser behavior

provider error behavior

archive behavior

revision behavior

replay behavior

forecast-vintage limitation

ICON grid-transition note

focused historical test result
focused forecast test result
combined Stage 5 test result

full pytest result
Ruff result
format result
mypy result
pre-commit result
git diff --check result

remaining controlled-live questions

exact Git status

confirmation:
no provider request
no branch
no staging
no commit
no push
```

If all offline acceptance criteria pass, finish exactly with:

```text
Phase 2 Stage 5 — PASS.

Historical Open-Meteo ERA5 ingestion remains accepted.

DWD ICON-EU is now the explicit Stage 5 forecast product,
pinned as models=icon_eu for all six Iberian sites and the
three approved hourly weather variables.

Temperature and 10 m wind retain instantaneous support.
Shortwave radiation retains preceding-hour mean support.

Forecast model identity, site identity, requested and
returned grid metadata, immutable provenance and replay
remain explicit and auditable.

ECMWF IFS HRES remains a documented fallback only.
No automatic fallback or model mixing is implemented.

No live Open-Meteo request was made.

Phase 2 Stage 6 has not been started or authorized.
```

If any required criterion remains unresolved, finish with:

```text
Phase 2 Stage 5 — PASS WITH GAPS.
```

and state the exact blocker.

Stop there.
