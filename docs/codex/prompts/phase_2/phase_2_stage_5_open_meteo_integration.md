# Iberian_Shakti — Phase 2 Stage 5
## Open-Meteo Historical ERA5 + Forecast Integration

Implement **Phase 2 Stage 5 only**.

The Stage 5 scope is:

```text
Provider: Open-Meteo

Historical:
- Historical Weather API
- ERA5 explicitly selected
- hourly observations

Forecast:
- Forecast API
- use the exact forecast model already selected/pinned
  in the authoritative Phase 2 readiness assessment
- hourly observations

Variables:
- temperature_2m
- wind_speed_10m
- shortwave_radiation

Sites:
- Lisbon
- Porto
- Bragança
- Madrid
- Zaragoza
- Seville
```

Keep the implementation simple, strict and consistent with the existing ingestion architecture.

Do not implement feature engineering, spatial interpolation, regional aggregation or additional weather variables.

---

# 1. Baseline

Start with:

```bash
git status --short
git log --oneline --decorate -10
```

Expected baseline:

```text
branch: main

HEAD:
f8dee4c feat: complete Phase 2 ENTSO-E ingestion

preceded by:
8ef31ef feat: complete Phase 2 ESIOS ingestion
13d5ff6 ci: run pre-commit in GitHub Actions
8bb5618 ci: add GitHub Actions quality checks
09792e9 feat: complete Phase 2 REN ingestion
8a377dd feat: establish Phase 2 multi-source foundation
70f4204 docs: record Phase 2 readiness assessment
```

Working tree should be clean.

Do not:

```text
fetch
pull
rebase
reset
create a branch
```

---

# 2. Read before implementing

Read at minimum:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md
docs/codex/reports/phase_2_stage_1_report.md
docs/codex/reports/phase_2_stage_2_ren_report.md
docs/codex/reports/phase_2_stage_3_esios_report.md
docs/codex/reports/phase_2_stage_4_entsoe_report.md

docs/adr/0003-*
docs/adr/0004-*
docs/adr/0006-*

src/iberian_shakti/contracts/
src/iberian_shakti/ingestion/
tests/contracts/
tests/integration/
```

In particular, inspect the existing:

```text
WeatherMeasurement
weather statistic/support contracts
location/geography contracts
query contracts
HttpRetriever
archive/provenance
replay
semantic outcomes
logging
```

Reuse them.

Do not create a second weather-data architecture.

---

# 3. Save this prompt first

Save this exact prompt before implementation:

```text
docs/codex/prompts/phase_2/
phase_2_stage_5_open_meteo_integration.md
```

Do not alter earlier prompt-history files.

---

# 4. Authoritative Stage 5 source selection

Implement only:

## Historical source

```text
Open-Meteo Historical Weather API
explicit model: ERA5
hourly
```

Do not use:

```text
ERA5-Land
ERA5-Seamless
Best Match
Historical Forecast API
Previous Runs API
Single Runs API
```

for historical Stage 5 ingestion.

ERA5 must be explicit so historical data does not silently change when Open-Meteo's default model-selection policy changes.

---

# 5. Forecast model selection

The generic Open-Meteo Forecast API defaults to `best_match`, which may combine different weather models.

Do **not** silently rely on that default.

Read the authoritative Phase 2 readiness assessment and use the **exact forecast model already selected there**.

The query must explicitly pin the model using Open-Meteo's model selection parameter.

If the readiness assessment does not actually identify one exact forecast model:

```text
do not guess one
do not silently use best_match
```

Instead:

1. document the exact gap;
2. implement everything that does not require the missing decision;
3. retain Stage 5 as `PASS WITH GAPS`;
4. stop without inventing a model choice.

Do not create an arbitrary model selection merely to obtain PASS.

---

# 6. Fixed sites

Use exactly these six Stage 5 locations:

```text
Portugal:
- Lisbon
- Porto
- Bragança

Spain:
- Madrid
- Zaragoza
- Seville
```

Use the **exact coordinates pinned by the Phase 2 readiness assessment**.

Do not:

```text
geocode dynamically
call another location API
change coordinates
use city centroids from general knowledge
add additional cities
```

Each site must have a stable versioned site identity independent of provider-returned grid-cell coordinates.

For example conceptually:

```text
PT.lisbon
PT.porto
PT.braganca

ES.madrid
ES.zaragoza
ES.seville
```

Follow existing project naming conventions.

---

# 7. Requested vs returned coordinates

Open-Meteo may return the coordinates of the grid cell actually used, which can differ from the requested coordinates.

Preserve both:

```text
requested latitude
requested longitude

returned latitude
returned longitude

returned elevation
```

Do not overwrite the configured site coordinates with returned grid-cell coordinates.

The normalized record should retain:

```text
logical site identity
+
source grid identity/context
```

using the existing contracts/provenance structure.

Do not add redundant fields if current contracts already support this distinction.

---

# 8. Historical query

Use the Historical Weather API with:

```text
model = ERA5

hourly =
temperature_2m
wind_speed_10m
shortwave_radiation
```

Use explicit UTC time output.

Do not request local civil timestamps.

Use bounded date/window queries consistent with the shared ingestion framework.

Do not request:

```text
daily aggregates
15-minute interpolation
multiple additional variables
automatic model blending
```

---

# 9. Forecast query

Use the Forecast API with:

```text
explicit selected model
hourly =
temperature_2m
wind_speed_10m
shortwave_radiation
```

Use UTC timestamps.

Do not rely on:

```text
auto timezone
local timestamps
default best_match model selection
```

Do not request forecast horizons beyond what is required by the accepted Stage 5 query/window contract.

Do not introduce historical forecast-run reconstruction in this stage.

---

# 10. Variable semantics

Implement the three variables exactly.

## temperature_2m

Meaning:

```text
air temperature at 2 metres
```

Support:

```text
instant
```

Use the provider-returned unit and validate the expected selected unit.

Prefer explicit query units if needed so that no implicit conversion occurs in our code.

---

## wind_speed_10m

Meaning:

```text
wind speed at 10 metres
```

Support:

```text
instant
```

Use an explicit API unit selection consistent with the existing WeatherMeasurement contract.

If the project expects metres/second, request Open-Meteo's m/s output directly rather than fetching another unit and converting locally.

Do not implement unnecessary unit conversion.

---

## shortwave_radiation

Meaning:

```text
global horizontal shortwave solar radiation
```

Support:

```text
preceding-hour mean
```

Unit:

```text
W/m²
```

This is important.

Do **not** represent `shortwave_radiation` as an instantaneous measurement.

Its support is the preceding one-hour interval ending at the returned timestamp.

Do not substitute:

```text
shortwave_radiation_instant
```

for the selected Stage 5 variable.

---

# 11. Historical vs forecast kind

Historical ERA5 records:

```text
kind = reanalysis
```

Forecast API records:

```text
kind = forecast
```

Do not label ERA5 as actual station observations.

Do not label Forecast API results as reanalysis.

Preserve this distinction in normalized records.

---

# 12. Time semantics

Use UTC.

For hourly values:

### temperature_2m

```text
ValidInstant at returned UTC timestamp
```

### wind_speed_10m

```text
ValidInstant at returned UTC timestamp
```

### shortwave_radiation

```text
positive half-open UTC interval
[timestamp - 1 hour, timestamp)
```

or the equivalent existing WeatherMeasurement support representation.

Do not use local DST calendars for these API responses.

Do not infer a local-day 23/25-hour structure from GMT weather data.

---

# 13. Hourly cadence

Preserve source hourly values.

Do not:

```text
interpolate to 15 minutes
forward-fill
back-fill
resample
smooth
aggregate sites
average cities
```

If an expected timestamp is absent, preserve the gap or fail according to the strict selected-product coverage policy.

Do not synthesize weather observations.

---

# 14. JSON response validation

Implement a strict bounded JSON parser.

Validate at minimum:

```text
latitude
longitude
elevation

timezone / utc_offset context as applicable

hourly.time

hourly.temperature_2m
hourly.wind_speed_10m
hourly.shortwave_radiation

hourly_units
```

Array lengths must match.

Reject:

```text
missing selected variable
unknown selected unit
null selected value
NaN
Infinity
non-numeric selected value
invalid timestamp
duplicate timestamp
unordered timestamps
array-length mismatch
unsupported response shape
```

Do not require unrelated presentation/performance fields unless semantically needed.

`generationtime_ms` is not business data.

---

# 15. Units

Validate the expected source units explicitly.

Do not silently accept an unexpected unit.

Preferred canonical semantics should remain approximately:

```text
temperature_2m:
°C

wind_speed_10m:
m/s if explicitly requested/selected

shortwave_radiation:
W/m²
```

Use the existing unit contracts.

Do not introduce generic unit-conversion infrastructure in Stage 5.

---

# 16. Model identity

Model identity is part of source provenance.

For historical data retain:

```text
ERA5
```

For forecasts retain:

```text
the explicit selected forecast model
```

Do not reduce all forecast sources to generic:

```text
open_meteo
```

when model identity is known.

Do not claim a model/run identity that the response/query does not support.

---

# 17. Forecast vintage safety

Keep separate:

```text
target timestamp
forecast model identity
acquisition timestamp
parse timestamp
provider update/run metadata if actually supplied
```

Do not infer:

```text
model run time
forecast issue time
publication time
```

unless the selected Open-Meteo response actually provides authoritative metadata for them.

A forecast fetched today is not automatically evidence of what would have been available at a historical market cutoff.

Historical forecast-vintage reconstruction belongs to later work if needed.

---

# 18. Error responses

Open-Meteo may return structured JSON errors for invalid requests.

Handle controlled provider errors separately from successful weather data.

Do not parse:

```json
{"error": true, ...}
```

as weather observations.

Provider reason text must not be blindly emitted into logs.

Map only safe controlled categories.

Do not invent no-data semantics for unverified response forms.

---

# 19. Authentication

The normal public Open-Meteo API selected for Stage 5 is anonymous.

Do not require:

```text
OPEN_METEO_API_KEY
```

unless the authoritative readiness assessment explicitly selected a commercial/customer endpoint, which is not expected.

Do not add secrets to:

```text
.env
GitHub Actions
configuration
```

for the normal public Stage 5 implementation.

If code supports an API-key parameter for unrelated Open-Meteo commercial use, do not activate it here.

---

# 20. Archive and provenance

Reuse unchanged:

```text
HttpRetriever
immutable original-byte archive
SHA-256 content addressing
retrieval provenance
parse provenance
offline replay
```

Every normalized weather record must trace back to:

```text
provider
dataset/product
model
site
requested coordinates
requested window
acquisition
raw hash/reference
parser/profile version
```

Preserve returned grid coordinates/elevation as source metadata where supported.

Do not redesign shared provenance.

---

# 21. Repeated acquisition and corrections

For the same canonical query:

```text
same bytes
-> shared content, separate acquisition event

changed bytes
-> retain both payload versions and histories
```

Never overwrite an earlier archived response.

This is especially important for forecasts, which may change between acquisitions.

Do not implement a mutable latest-only archive.

---

# 22. Offline replay

Successful historical and forecast records must replay:

```text
with zero network

same normalized values
same units
same site identity
same requested coordinates
same returned grid metadata
same support semantics
same model identity
same raw linkage
```

Only parse-event identity/time may change where expected.

Corrupt hash/linkage must fail without refetching.

---

# 23. Bounds

Use finite explicit limits for:

```text
response bytes
JSON nesting
object keys
array lengths
string lengths
numeric token lengths
number of hourly points
number of sites per invocation
```

Use reasonable values for the selected Stage 5 scope.

Do not implement arbitrary multi-year bulk downloads in one request.

The parser must fail visibly on bounds violations rather than partially returning records.

---

# 24. Query strategy

Keep the first implementation simple.

Prefer a deterministic query identity per:

```text
product/model
site
window
selected variable set
```

Do not create complicated multi-site batching unless the existing shared architecture clearly benefits from it.

If one request per site is simpler and more auditable, use that.

Avoid provider-specific concurrency machinery.

---

# 25. Site completeness

A successful query for one site should return all three selected variables over its supported requested range.

Do not silently emit a partial weather dataset if one selected variable is absent.

Do not replace missing values with zero.

---

# 26. Scientific value policy

Use finite numeric weather values.

Apply versioned plausibility bounds only if they already exist in the Stage 1 shared weather contract or are explicitly required by the readiness assessment.

Do not clip scientifically unusual values.

A value outside a hard physical/parser bound should fail visibly rather than being changed.

Do not invent aggressive climate-range assumptions merely to reject outliers.

---

# 27. Synthetic fixtures

Use small synthetic JSON fixtures.

Do not copy real provider bodies into Git unless explicitly justified and redistribution rights permit it.

At minimum cover:

```text
valid historical ERA5 response
valid forecast response

all three variables
units
requested/returned coordinate distinction
returned elevation

instant temperature
instant wind
preceding-hour shortwave support

missing variable
wrong unit
array mismatch
null value
non-finite value
invalid timestamp
duplicate timestamp
unordered timestamp
provider error response
wrong/unexpected model/profile identity where applicable
changed-body revision
```

Prefer a few fixtures plus in-memory mutations rather than a large fixture catalogue.

Maintain repository fixture manifest/checksum conventions.

---

# 28. Six-site tests

Test all six configured logical sites.

Do not require six large full-response fixtures if parametrized tests over site profiles are sufficient.

At minimum prove stable identities for:

```text
Lisbon
Porto
Bragança
Madrid
Zaragoza
Seville
```

and that PT/ES country/site mappings do not accidentally interchange.

---

# 29. Historical tests

Verify:

```text
ERA5 explicitly selected
reanalysis kind
hourly UTC timestamps
temperature instant
wind instant
shortwave preceding-hour mean
units correct
site/grid metadata retained
```

---

# 30. Forecast tests

Verify:

```text
explicit selected forecast model
forecast kind
hourly UTC timestamps
same three variables
correct support/statistic semantics
model identity retained
site/grid metadata retained
```

Also prove that the implementation does **not** silently fall back to Open-Meteo `best_match`.

---

# 31. No live Open-Meteo request

This Stage 5 implementation task is offline.

Do not:

```text
call Open-Meteo
probe the API
download ERA5 data
download current forecasts
perform coordinate discovery
```

Do not use web requests from tests.

Public documentation may be consulted if necessary, but that is not live product validation.

Controlled live provider validation belongs to the later Phase 2 live-validation stage.

---

# 32. Documentation

Create:

```text
docs/codex/reports/
phase_2_stage_5_open_meteo_report.md
```

Document:

```text
historical endpoint/model
forecast endpoint/model
six fixed sites
three variables
requested vs returned coordinates
elevation metadata
hourly cadence
instant vs preceding-hour support
query identity
archive/replay
limitations reserved for live validation
```

Create a new ADR only if Stage 5 introduces a genuinely new durable architectural decision.

Do not create an ADR for routine provider integration.

Update README/architecture/runbooks only where necessary.

---

# 33. Focused tests

Create focused Stage 5 tests for:

```text
site profile
historical query
forecast query
model pinning
JSON parser
units
time/support semantics
coordinate/grid metadata
error responses
archive/revisions
offline replay
bounds
```

Report the focused Stage 5 test count separately.

---

# 34. Regression protection

All previous behavior must remain green:

```text
Phase 1 OMIE
Phase 2 Stage 1 shared foundation
Stage 2 REN
Stage 3 ESIOS
Stage 4 ENTSO-E
GitHub CI workflow
```

Do not weaken earlier contracts to simplify Open-Meteo.

Do not delete or skip tests.

---

# 35. Validation

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

The existing offline/network-denied pytest guard must remain active.

No credential or cloud resource should be required.

---

# 36. Stage 5 acceptance criteria

Stage 5 may PASS offline when:

```text
six fixed site profiles implemented

Historical Weather API:
- ERA5 explicitly selected
- hourly data
- three variables
- reanalysis semantics correct

Forecast API:
- explicit readiness-selected model
- hourly data
- same three variables
- forecast semantics correct

temperature_2m represented as instant
wind_speed_10m represented as instant
shortwave_radiation represented as preceding-hour mean

units validated
requested coordinates retained
returned coordinates/elevation retained separately

strict JSON parser implemented
array/timestamp/value failures visible
provider error documents handled

immutable archive/provenance works
changed acquisitions preserved
offline replay works

no silent best_match fallback
no resampling/interpolation/filling

all earlier regressions pass
all quality gates pass
```

No live Open-Meteo request is required for offline Stage 5 engineering PASS.

---

# 37. Reserve for later controlled live validation

The Stage 5 report must explicitly reserve validation of:

```text
successful real Historical API request
successful real Forecast API request

actual returned coordinate/grid/elevation behavior
actual units and timestamp arrays
actual selected forecast model response behavior
actual forecast coverage/horizon
historical ERA5 availability/delay
real provider error/no-data variants
request-boundary inclusivity
response size/compression
model update behavior
forecast revision behavior
rate limits
licensing/redistribution constraints
```

Do not claim those have been observed in this offline task.

---

# 38. Scope exclusions

Do not implement:

```text
humidity
precipitation
cloud cover
pressure
weather codes
wind direction
wind gusts
daily variables

ERA5-Land
ERA5-Seamless
Historical Forecast API
Previous Runs API
Single Runs API

automatic best_match forecasting
multi-model ensemble ingestion

site averaging
regional weather indexes
feature engineering
lags
rolling means

MIBGAS

Snowflake
dbt
model training
model registry
batch inference
FastAPI
dashboard
deployment
Kafka
Kubernetes
AKS
```

---

# 39. Git rules

Do not:

```text
stage
commit
push
create a branch
```

Leave the complete Stage 5 change set for operator review.

---

# 40. Final response

Return a concise engineering summary containing:

1. baseline branch and HEAD;
2. all files changed;
3. profile/parser versions;
4. six site identities and coordinates used;
5. historical endpoint/model;
6. forecast endpoint/model;
7. selected variables;
8. unit handling;
9. time/support semantics for each variable;
10. requested vs returned coordinate handling;
11. elevation handling;
12. historical/reanalysis normalization;
13. forecast normalization;
14. model-identity behavior;
15. confirmation that `best_match` is not silently used;
16. parser/error behavior;
17. archive/provenance behavior;
18. revision behavior;
19. replay behavior;
20. focused Stage 5 test result;
21. full pytest result;
22. Ruff result;
23. formatting result;
24. mypy result;
25. pre-commit result;
26. `git diff --check` result;
27. remaining controlled-live-validation items;
28. Stage 5 verdict;
29. exact Git status;
30. confirmation:
   - no provider request;
   - no branch;
   - no staging;
   - no commit;
   - no push.

If all offline acceptance criteria pass, finish with:

```text
Phase 2 Stage 5 — PASS

Open-Meteo ERA5 historical reanalysis and the explicitly
selected forecast model are implemented for Lisbon, Porto,
Bragança, Madrid, Zaragoza and Seville using the three
approved hourly weather variables.

Temperature and 10 m wind retain instantaneous support;
shortwave radiation retains its documented preceding-hour
mean support.

Requested site coordinates and provider-returned grid
coordinates/elevation remain distinct and traceable.

No live Open-Meteo request was made.

Phase 2 Stage 6 has not been started or authorized.
```

If any required engineering criterion remains unresolved, finish with:

```text
Phase 2 Stage 5 — PASS WITH GAPS
```

and state the precise blocker.

Stop there.
