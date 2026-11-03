# Iberian_Shakti — Phase 2 Stage 6
## Cross-Source Integration and Hardening

Implement **Phase 2 Stage 6 only**.

Stage 5 has reached:

```text
Phase 2 Stage 5 — PASS
```

with:

```text
OMIE          Phase 1
REN           Phase 2 Stage 2
ESIOS         Phase 2 Stage 3
ENTSO-E       Phase 2 Stage 4
Open-Meteo    Phase 2 Stage 5

Open-Meteo historical:
ERA5

Open-Meteo forecast:
DWD ICON-EU
models=icon_eu
```

Stage 6 must now prove that these independently accepted ingestion paths coexist safely and coherently under the shared ingestion architecture.

This task is:

```text
CROSS-SOURCE INTEGRATION
+
HARDENING
+
OFFLINE VERIFICATION
```

This is **not**:

```text
another readiness assessment
provider live validation
Snowflake work
dbt work
feature engineering
model training
Stage 7+
```

---

# 1. Mandatory clean-checkpoint precondition

Start with:

```bash
git status --short
git log --oneline --decorate -12
```

Stage 6 may begin only if:

```text
branch = main
working tree = clean
Stage 5 has been committed as an accepted checkpoint
```

The Stage 5 commit hash is intentionally not invented here.

Verify that the current HEAD contains the accepted Stage 5 implementation and report.

At minimum confirm that the committed tree contains:

```text
docs/codex/reports/phase_2_stage_5_open_meteo_report.md

docs/codex/reports/phase_2_stage_5_forecast_model_selection.md

DWD ICON-EU forecast integration
models=icon_eu
```

If the working tree still contains uncommitted Stage 5 changes:

```text
STOP
```

Do not:

```text
stage
commit
stash
reset
restore
```

them on the operator's behalf.

Return:

```text
Phase 2 Stage 6 — BLOCKED.

Reason:
Stage 5 passed engineering acceptance but has not yet been
preserved as the required clean committed checkpoint.
```

and stop.

If the precondition passes, continue.

---

# 2. Git rules

During Stage 6 do not:

```text
create a branch
stage
commit
push
fetch
pull
rebase
reset
restore
stash
```

Work directly on the clean `main` baseline.

Leave the completed Stage 6 change set unstaged for operator review.

---

# 3. Save this prompt first

Before implementation, save this exact prompt as:

```text
docs/codex/prompts/phase_2/
phase_2_stage_6_cross_source_integration_hardening.md
```

Do not alter previous Phase 2 prompts.

---

# 4. Read before implementation

Read at minimum:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md

docs/codex/reports/phase_2_stage_1_report.md

docs/codex/reports/phase_2_stage_2_ren_report.md

docs/codex/reports/phase_2_stage_3_esios_report.md

docs/codex/reports/phase_2_stage_4_entsoe_report.md

docs/codex/reports/phase_2_stage_5_open_meteo_report.md

docs/codex/reports/phase_2_stage_5_forecast_model_selection.md
```

Also inspect:

```text
src/iberian_shakti/contracts/
src/iberian_shakti/ingestion/

tests/contracts/
tests/unit/ingestion/
tests/integration/
```

and all ADRs relevant to:

```text
query identity
system/weather contracts
semantic outcomes
provider-period values
weather output identity
provenance
archive
replay
```

Do not perform another source-selection/readiness assessment.

---

# 5. Stage 6 objective

Stage 1–5 proved providers individually.

Stage 6 must prove the **multi-source ingestion system as a whole**.

The accepted source set is:

```text
OMIE
REN
ESIOS
ENTSO-E
Open-Meteo ERA5
Open-Meteo ICON-EU
```

Verify that their records can coexist without ambiguity in:

```text
identity
area/geography
time
support
statistic
unit
kind
publication/source-time semantics
query provenance
raw provenance
replay
failure behavior
```

Do not force providers into identical source semantics.

Normalization means:

```text
different source-native meanings
represented consistently and explicitly
```

not:

```text
different meanings rewritten as if identical
```

---

# 6. Preserve source-native products

The following distinctions must remain intact.

## OMIE

```text
electricity price
PT / ES
EUR/MWh
market intervals
```

## REN

```text
Portuguese system measurements
generation/load/import/export context
MW
provider_period_value
Europe/Lisbon period interpretation
```

## ESIOS

```text
Spanish peninsular demand forecast
series 544
MW
5-minute instantaneous forecast samples
ES.peninsular
```

## ENTSO-E

```text
ES actual total load
PT/ES day-ahead wind/solar forecasts
bidding-zone geography
MW
provider_period_value
```

## Open-Meteo ERA5

```text
weather reanalysis
six fixed sites
hourly UTC
```

## Open-Meteo ICON-EU

```text
weather forecast
six fixed sites
hourly UTC
explicit model icon_eu
```

Do not collapse any of these into a generic undifferentiated time series.

---

# 7. Geography hardening

Verify that the shared geography contracts safely distinguish at minimum:

```text
PT market area
ES market area

PT mainland/system context
ES peninsular context

PT ENTSO-E bidding zone
ES ENTSO-E bidding zone

six point weather sites
provider weather grid cells
```

Do not assert equivalence such as:

```text
ES.peninsular == ES ENTSO-E bidding zone
PT REN mainland == PT ENTSO-E bidding zone
city weather point == national weather
```

unless an existing accepted contract explicitly states it.

They may be useful together later, but they are not identical geographic objects.

Add regression tests preventing accidental cross-area equivalence.

---

# 8. Cross-source temporal semantics

Verify that every normalized record has unambiguous temporal support.

At minimum exercise combinations involving:

```text
OMIE market intervals

REN 15-minute provider periods

ESIOS 5-minute ValidInstant samples

ENTSO-E 15/30/60-minute periods

Open-Meteo hourly ValidInstant samples

Open-Meteo hourly preceding-period radiation
```

Do not convert all providers to one cadence.

Do not:

```text
resample
interpolate
forward-fill
back-fill
average
sum
repeat
```

in Stage 6.

The purpose is to prove compatibility of contracts, not create model-ready aligned rows.

---

# 9. UTC and local-market boundaries

Add integrated tests covering difficult temporal boundaries.

At minimum include:

```text
ordinary day
spring DST transition
autumn DST transition
UTC midnight
local-market midnight
weather shortwave interval crossing UTC midnight
```

Verify that:

```text
source-native local semantics
→ canonical UTC support
```

remain correct independently for each provider.

Do not impose one provider's timezone policy on another.

---

# 10. Cross-source unit safety

Verify that units cannot accidentally mix.

At minimum:

```text
EUR/MWh price
MW power
°C temperature
m/s wind speed
W/m² radiation
```

must remain distinguishable.

Tests should demonstrate that a consumer cannot accidentally treat:

```text
MW
as
EUR/MWh
```

or:

```text
W/m²
as
MW
```

through shared normalization.

Do not add unit conversion merely for this test.

---

# 11. Statistic/support safety

Explicitly verify coexistence of:

```text
instant
mean
provider_period_value
```

and corresponding valid support types.

In particular prove:

```text
ESIOS forecast sample
!=
REN provider period

temperature instant
!=
shortwave preceding-hour mean

ENTSO-E provider_period_value
!=
an asserted arithmetic mean
```

Do not reinterpret `provider_period_value`.

---

# 12. Actual / forecast / reanalysis distinctions

Cross-source integration must preserve:

```text
actual
forecast
reanalysis
```

where supported by the existing contracts.

Test representative records such as:

```text
ENTSO-E actual load
ESIOS forecast load
ENTSO-E wind/solar forecast
Open-Meteo ERA5 reanalysis
Open-Meteo ICON-EU forecast
```

No downstream integration helper may erase these distinctions.

---

# 13. Source-time / acquisition-time safety

Verify that Stage 6 does not conflate:

```text
target/valid time
source issue time
model/run time
publication/update time
acquisition completion time
parse time
```

If a provider does not supply an authoritative source-time field:

```text
leave it unknown/null
```

Do not infer it from acquisition time.

This is particularly important for:

```text
Open-Meteo latest ICON-EU
ESIOS values_updated_at
ENTSO-E document createdDateTime
```

Preserve their already accepted semantics.

---

# 14. Forecast-vintage protection

Add cross-source tests proving that the system cannot accidentally claim:

```text
current/latest forecast
==
forecast historically available before an old market cutoff
```

No historical weather forecast reconstruction belongs in Stage 6.

No feature engineering belongs here.

The integration layer must merely preserve enough provenance for later cutoff-safe feature construction.

---

# 15. Canonical query identity hardening

Audit all accepted providers for query identity consistency.

Canonical query identity must distinguish:

```text
provider
product/report
profile/version
area/site
model where applicable
requested time window
product-specific selection
```

Verify that two materially different requests cannot accidentally hash or compare as the same business query.

Examples:

```text
ERA5 != ICON-EU

ICON-EU Lisbon != ICON-EU Madrid

ENTSO-E PT wind != ENTSO-E ES wind

ESIOS 544 != another theoretical series

REN selected product != another REN product
```

Do not change legacy query bytes/hashes unless a real defect requires it.

Any compatibility-sensitive query change requires:

```text
explicit migration reasoning
regression evidence
versioning where necessary
```

---

# 16. Cross-source raw provenance

Verify that every normalized record remains traceable through:

```text
record
→ parse event
→ retrieval event
→ immutable raw object
→ SHA-256
→ canonical request
```

Do this across every accepted provider family.

No shared integrated representation may detach records from their original evidence.

---

# 17. Combined offline replay

Create an integration test that replays a representative multi-source evidence set with:

```text
zero network
zero provider credentials
zero new retrieval events
```

The replay set should include representative accepted products from:

```text
OMIE
REN
ESIOS
ENTSO-E
Open-Meteo ERA5
Open-Meteo ICON-EU
```

The combined test must prove that:

```text
each source replays independently
all records coexist in one test workflow
raw identities remain source-specific
business identities remain source-specific
no source overwrites another
```

Do not create a new replay framework if the existing one can orchestrate this.

---

# 18. Replay determinism

For each source in the combined replay, verify:

```text
same archived bytes
same normalized business values
same source-native semantics
same raw linkage
```

while allowing only explicitly non-business parse-event identity/time differences.

Corrupt one source's evidence and prove that:

```text
that replay fails
```

without causing:

```text
network fallback
other source corruption
silent substitution
```

---

# 19. Failure isolation

Add integration coverage proving that one provider failure does not corrupt successful evidence from another provider.

Test representative failures such as:

```text
malformed REN body
ESIOS authentication/configuration failure
ENTSO-E acknowledgement/provider rejection
Open-Meteo malformed JSON
OMIE parse failure
```

The exact scenarios should reuse existing provider fixtures/helpers rather than duplicate large fixtures.

Expected property:

```text
source A failure
does not mutate or invalidate
source B archived evidence/history
```

Do not invent a multi-provider transaction that rolls back unrelated prior acquisitions unless one already exists by design.

---

# 20. Atomicity per acquisition

Audit the current runner/archive/parser pipeline for each provider and prove:

```text
successful normalized output
requires successful required persistence
```

and:

```text
parse failure
cannot publish successful normalized records
```

Preserve the existing rule that safe complete response bytes may be archived even when parsing subsequently fails.

Do not weaken evidence retention to simplify integrated tests.

---

# 21. Revision/correction isolation

Verify independently that revised source data remain provider-local.

Examples:

```text
OMIE revision
REN changed body
ESIOS changed body
ENTSO-E corrected response
Open-Meteo forecast revision
```

A revision must not:

```text
overwrite another source
change another source's canonical identity
erase earlier raw content
```

No generic "latest record wins across providers" behavior may be introduced.

---

# 22. Duplicate/collision hardening

Test for accidental identity collisions across:

```text
same timestamp
same numeric value
same country
similar concept names
```

Examples:

```text
REN load at 10:00
ENTSO-E load at 10:00
ESIOS load forecast at 10:00
```

These must remain different records because provenance/product/geography/kind/statistic differ.

Do not deduplicate across providers merely because time/value/concept appear similar.

---

# 23. Cross-source normalized collection

If the existing architecture already has a suitable normalized record collection/container, use it.

If no such abstraction is needed, do **not** invent a large new orchestration layer.

A Stage 6 test-level integration harness is acceptable if it proves compatibility.

Only add a production shared abstraction if:

```text
the absence creates a concrete correctness gap
```

and document why.

Prefer minimal architecture.

---

# 24. No synchronization engine

Do not build:

```text
time-series join engine
feature matrix
resampling engine
national aggregation
weather aggregation
market alignment table
```

Those belong to later transformation/feature phases.

Stage 6 verifies semantic interoperability, not analytical joining.

---

# 25. Contract audit

Audit shared contracts for assumptions that worked for one provider but fail across all providers.

Inspect at minimum:

```text
measurement type
unit representation
statistic
valid support
area/site identity
source data identity
source times
native identity
profile/version
provenance references
```

If no defect exists:

```text
do not change the contract
```

If a shared contract change is necessary:

1. keep it minimal;
2. preserve prior provider semantics;
3. add regression tests for every affected provider;
4. version if semantic compatibility changes;
5. document why the defect could not be fixed provider-locally.

---

# 26. Error taxonomy hardening

Review cross-source error mapping for collisions or ambiguity.

Ensure distinct categories remain meaningful across providers, including where applicable:

```text
configuration
authentication
authorization
transport
HTTP
source_unavailable
no_data
provider_rejected
schema/content
archive/persistence
replay integrity
```

Do not force every provider to emit every semantic outcome.

Do not map unknown provider prose using keyword heuristics.

---

# 27. Safe diagnostics

Audit logging/diagnostics across the full provider set.

Ensure logs/errors do not expose:

```text
ESIOS token
ENTSO-E token
private request headers/query secrets
raw unrestricted provider error prose
sensitive credential-bearing URLs
```

Open-Meteo and REN anonymity must not weaken private-provider protections.

Add cross-source regression tests where useful.

---

# 28. Bounds hardening

Verify every provider retains finite bounds for:

```text
response size
parser complexity
record count
time span
collection size
```

Stage 6 should identify accidental unbounded behavior introduced by multi-source use.

Do not globally raise parser limits merely for integration convenience.

Any bound adjustment must be:

```text
provider-specific where possible
evidence-based
tested
documented
```

---

# 29. Network-denied default

All Stage 6 tests must remain offline.

Existing network-denied test protection must continue to cover the full suite.

Do not:

```text
call OMIE
call REN
call ESIOS
call ENTSO-E
call Open-Meteo
probe credentials
```

No live requests.

No cloud resource changes.

---

# 30. Credentials

Do not read real credentials during Stage 6 tests.

Use existing synthetic/private-policy seams.

Verify:

```text
ESIOS
ENTSO-E
```

can participate in integration tests without real secrets.

Anonymous sources:

```text
OMIE
REN
Open-Meteo
```

must not gain unnecessary credential configuration.

---

# 31. Provider-specific regression preservation

All accepted provider behavior must remain green.

At minimum preserve:

```text
Phase 1 OMIE

Stage 2 REN

Stage 3 ESIOS

Stage 4 ENTSO-E

Stage 5 Open-Meteo ERA5

Stage 5 Open-Meteo ICON-EU
```

No test skips.

No weakened assertions.

No fixture replacement that removes previous edge cases.

---

# 32. Source matrix test

Add a permanent integration test or equivalent evidence matrix covering:

| Source/product | Geography | Kind | Cadence/support | Unit family | Replay |
| --- | --- | --- | --- | --- | --- |
| OMIE price | PT/ES market | market price | source interval | EUR/MWh | yes |
| REN | PT system | actual | 15-min period | MW | yes |
| ESIOS 544 | ES peninsular | forecast | 5-min instant | MW | yes |
| ENTSO-E ES load | ES bidding zone | actual | provider period | MW | yes |
| ENTSO-E PT/ES wind/solar | bidding zone | forecast | provider period | MW | yes |
| ERA5 | six weather sites | reanalysis | hourly instant/mean | weather | yes |
| ICON-EU | six weather sites | forecast | hourly instant/mean | weather | yes |

Do not hard-code this as documentation only.

The permanent tests should enforce the important distinctions represented by the matrix.

---

# 33. Representative integrated scenario

Construct one compact synthetic integrated scenario, for example one UTC window containing representative records from all source families.

The scenario should demonstrate:

```text
same time range
multiple geography types
multiple kinds
multiple units
multiple statistics/support types
multiple raw acquisitions
```

while proving no identity collision.

Do not try to create realistic correlated market/weather values.

Synthetic values exist to test contracts, not forecasting science.

---

# 34. DST integration scenario

Add at least one cross-source DST-focused scenario that proves:

```text
REN local-period semantics
OMIE market-period semantics
ENTSO-E UTC periods
ESIOS UTC instant samples
Open-Meteo UTC weather
```

can coexist around a transition without forcing one shared row count.

The test should assert semantic correctness, not equal record counts.

---

# 35. Documentation

Create:

```text
docs/codex/reports/
phase_2_stage_6_cross_source_integration_hardening_report.md
```

Document:

```text
baseline
scope
sources included
shared invariants
geography distinctions
time/support distinctions
unit distinctions
kind distinctions
query identity audit
provenance audit
combined replay
failure isolation
revision isolation
security/diagnostics audit
bounds audit
tests
remaining gaps reserved for Stage 7/8
```

Create a new ADR only if Stage 6 introduces a genuinely durable new architectural decision.

Do not create an ADR merely because Stage 6 exists.

---

# 36. README/runbook updates

Update only where Stage 6 changes durable project behavior.

Do not perform broad documentation cleanup.

If no operational workflow changes, keep README/runbook edits minimal.

---

# 37. Focused Stage 6 tests

Create a dedicated Stage 6 test selection.

It should include at minimum:

```text
cross-source identity
cross-source geography
cross-source temporal support
unit/statistic safety
actual/forecast/reanalysis safety
combined replay
failure isolation
revision isolation
credential/diagnostic isolation
DST integration
```

Report the focused Stage 6 test count separately.

---

# 38. Full validation

Run:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
pre-commit run --all-files
```

Also run:

```text
focused Stage 6 suite
all provider-focused ingestion suites where practical
```

Do not claim a test result that was not actually executed.

---

# 39. Stage 6 PASS criteria

Stage 6 may finish as:

```text
PASS
```

only if all of the following hold:

```text
all accepted provider paths remain green

cross-source identity is collision-safe

geography distinctions remain explicit

temporal support is compatible without forced resampling

units/statistics cannot be confused

actual/forecast/reanalysis distinctions survive integration

query identity remains deterministic

all records retain immutable raw provenance

combined replay works with zero network

one-source replay corruption does not trigger network fallback

provider failures are isolated

revisions remain provider-local and immutable

private-provider credentials remain protected

bounds remain finite

network-denied default remains effective

focused Stage 6 tests pass

full regression suite passes

Ruff passes
format passes
mypy passes
pre-commit passes
git diff --check passes
```

---

# 40. Stage 6 PASS WITH GAPS

Do not force PASS.

Return:

```text
PASS WITH GAPS
```

if a real offline engineering issue remains, such as:

```text
shared contract ambiguity
cross-provider identity collision
replay cannot compose safely
source failure corrupts other evidence
geography semantics are conflated
time/support semantics cannot coexist
credential leakage
unbounded integrated behavior
regression failure
```

State the precise blocker.

Do not solve a genuine architectural defect with test-only exceptions.

---

# 41. Reserved for Stage 7

Do not perform the full formal pre-live audit yet.

Stage 7 will separately perform the systematic pre-live engineering audit.

Stage 6 may identify issues relevant to Stage 7, but do not rename Stage 6 into the Stage 7 audit.

Reserve items such as:

```text
final exhaustive timeout/retry review
final security audit
final parser-security audit
final pre-live checklist reconciliation
```

for Stage 7 unless a concrete Stage 6 defect requires fixing now.

---

# 42. Reserved for Stage 8

Do not perform controlled live validation.

Stage 8 will validate real provider behavior for:

```text
OMIE
REN
ESIOS
ENTSO-E
Open-Meteo ICON-EU
```

and replay real archived acquisitions.

Do not claim real-world provider compatibility in Stage 6.

---

# 43. No later-phase work

Do not implement:

```text
Snowflake
dbt
feature engineering
training datasets
N-HiTS
LightGBM
XGBoost
TFT
stacking
model registry
batch inference
FastAPI serving
dashboard
deployment
```

---

# 44. Final response

Return a concise engineering summary containing:

1. branch and baseline HEAD;
2. confirmation Stage 5 was a clean committed checkpoint;
3. files changed;
4. shared contracts changed, if any;
5. providers/products included;
6. cross-source geography findings;
7. temporal/support findings;
8. unit/statistic findings;
9. actual/forecast/reanalysis findings;
10. query-identity findings;
11. provenance findings;
12. combined replay result;
13. failure-isolation result;
14. revision-isolation result;
15. security/credential result;
16. bounds result;
17. DST integration result;
18. focused Stage 6 test result;
19. full pytest result;
20. Ruff result;
21. format result;
22. mypy result;
23. pre-commit result;
24. `git diff --check` result;
25. remaining Stage 7/8 items;
26. exact Git status;
27. confirmation:
   - no provider request;
   - no cloud action;
   - no branch;
   - no staging;
   - no commit;
   - no push.

If all acceptance criteria pass, finish exactly with:

```text
Phase 2 Stage 6 — PASS.

OMIE, REN, ESIOS, ENTSO-E and Open-Meteo now coexist
under the shared ingestion architecture with explicit,
source-native geography, temporal support, statistics,
units, kinds, provenance and replay semantics.

Cross-source integration introduces no resampling,
interpolation, aggregation or feature engineering.

Combined offline replay and provider-failure isolation
are verified with zero network access.

Phase 2 Stage 7 has not been started or authorized.
```

If a required engineering criterion remains unresolved, finish with:

```text
Phase 2 Stage 6 — PASS WITH GAPS.
```

and state the precise blocker.

Stop there.
