# Iberian_Shakti — Phase 2 Stage 2
## Revised REN Engineering Implementation

Implement the revised REN Stage 2 engineering policy.

The objective is deliberately simple:

> **Use REN's reported 15-minute MW values directly as source-native forecasting measurements, while keeping the time interpretation explicit, provisional, versioned, and replayable.**

Do **not** require proof that each REN MW value is specifically an instantaneous reading or a quarter-hour arithmetic mean before ingestion succeeds.

Do **not** convert REN MW values to MWh.

This project forecasts electricity prices; REN generation/load MW values are forecasting features, not settlement-energy calculations.

---

## 1. Current situation

Phase 2 Stage 2 currently has:

```text
PASS WITH GAPS
```

because successful REN normalization was blocked by four semantic questions:

1. timezone;
2. HH:MM label role;
3. DST ordering/fold handling;
4. exact MW statistic.

Since then, additional evidence has established:

```text
Timezone:
strong empirical support for Europe/Lisbon

REN DST calendar:
exact 92 / 96 / 100 quarter-hour compatibility
with Europe/Lisbon

Label placement:
interval-start interpretation is empirically favored

MW:
REN reports MW values associated with 15-minute periods,
but the exact arithmetic/statistical definition remains unresolved
```

The independent experiment still classified the exact MW statistic as unresolved. That is acceptable under this revised policy.

---

# 2. Engineering decision

Stage 2 will no longer require:

```text
MW = proven instantaneous measurement
OR
MW = proven interval mean
```

before successful REN records can be produced.

Instead, represent the value honestly as a provider-reported power value associated with a 15-minute period.

Conceptually:

```text
source = REN
value = Decimal(...)
unit = MW
source_period = 15 minutes

timezone = Europe/Lisbon
label_role = interval_start

time_semantics_status = provisional_empirical

value_semantics = provider_period_power
```

Exact names should follow the existing codebase conventions.

Do not introduce unnecessary abstractions merely to reproduce these example names.

---

# 3. Important distinction

We are accepting a **forecasting-safe interpretation**, not claiming provider-authoritative semantics.

The system should mean:

```text
REN reported this MW value for this source period.
```

It should NOT claim:

```text
REN officially defines this as arithmetic mean MW.
```

Therefore:

- retain MW exactly as reported;
- do not calculate MWh;
- do not describe the value as `quarter_hour_mean_mw`;
- do not silently claim instantaneous measurement;
- keep the unresolved detail in provenance/documentation;
- allow later replay if REN clarifies the definition.

---

# 4. Time profile to adopt

Create or update the REN source profile so that the operational profile is explicitly versioned.

Use:

```text
timezone = Europe/Lisbon
period = 15 minutes
label_role = interval_start
DST mapping = ordered physical Europe/Lisbon quarter-hour sequence
status = provisional_empirical
```

The implementation must:

1. generate the physical `Europe/Lisbon` civil-day quarter-hour sequence;
2. require the REN labels to match that expected ordered sequence exactly;
3. support:
   - ordinary day: 96 periods;
   - spring DST day: 92 periods;
   - autumn DST day: 100 periods;
4. preserve both repeated autumn-hour blocks by ordered position;
5. map physical periods deterministically to UTC;
6. fail closed if the actual REN label sequence does not match the expected profile.

Do not use:

```text
fixed UTC offsets
Europe/Madrid
deduplication of repeated autumn labels
naive local datetime arithmetic
```

---

# 5. DST fold handling

Use ordered position in the validated `Europe/Lisbon` physical-day sequence.

For example, on the autumn DST day:

```text
01:00 fold 0
01:15 fold 0
01:30 fold 0
01:45 fold 0

01:00 fold 1
01:15 fold 1
01:30 fold 1
01:45 fold 1
```

This is an accepted **provisional engineering interpretation**.

Preserve enough source provenance so that if REN later states a different ordering rule, archived raw acquisitions can be replayed under a new profile.

Do not rewrite historical raw data.

---

# 6. Value representation

Prefer the smallest change compatible with the existing contracts.

Inspect the current `SystemMeasurement` model first.

If it currently requires only:

```text
instantaneous
interval_mean
```

then add one narrowly defined provider-native option such as:

```text
provider_period_value
```

or the nearest clear project-consistent name.

Its meaning should be:

> A provider-reported measurement associated with a defined source period, where the provider's precise statistical aggregation is not known.

Do not introduce multiple speculative categories such as:

```text
unknown_average
estimated_mean
probable_instant
assumed_sample
```

Keep this simple.

---

# 7. Required safeguards

A provider-period MW value must not automatically support energy conversion.

Therefore, if the codebase has or later introduces:

```text
MW → MWh
```

logic, `provider_period_value` must not be treated as a confirmed interval mean without an explicit semantic upgrade.

For Stage 2, no energy conversion is needed.

This restriction should be easy to understand from the contract or documentation.

---

# 8. Preserve source-native provenance

For each normalized REN record retain or link enough information to recover:

```text
source provider
source product
source day
source label
source array position
source value
unit
profile version
parse version
raw SHA-256 / acquisition linkage
```

Do not add redundant fields if the existing provenance objects already provide them.

Reuse existing Stage 1 / Stage 2 provenance architecture wherever possible.

---

# 9. Versioning

Do not mutate the meaning of the existing blocked profile silently.

Create a new profile/version for the accepted provisional semantics.

For example, if the existing REN profile is:

```text
0.1.0
```

with:

```text
time_semantics_unknown
```

use an appropriately incremented version such as:

```text
0.2.0
```

for the empirical operational profile.

Exact version naming should follow existing project conventions.

The old profile must remain understandable from history.

---

# 10. Future REN clarification

Design for this simple future workflow:

```text
raw REN acquisition
        |
        +--> profile 0.2.0 provisional empirical
        |
        +--> future authoritative profile
```

If REN later confirms:

```text
timezone
label placement
DST handling
MW meaning
```

create a new profile.

Then replay archived raw acquisitions under that profile.

Do not overwrite old provenance or pretend the old interpretation never existed.

No complicated migration framework is required now.

The existing replay architecture should be reused.

---

# 11. Do not over-engineer confidence scoring

Do NOT introduce numerical confidence scores such as:

```text
0.85 confidence
0.92 confidence
```

Do NOT create a generic evidence-ranking framework.

A small semantic status is sufficient, for example:

```text
authoritative
provisional_empirical
```

Only add such a status if needed by the current architecture.

The primary distinction is simply:

```text
provider-confirmed
vs
our accepted empirical interpretation
```

---

# 12. No MW → MWh conversion

Explicitly verify that Stage 2 REN implementation does not convert:

```text
MW × 0.25 h → MWh
```

for forecasting ingestion.

REN MW values should remain MW.

No energy accounting, settlement calculation, or synthetic MWh field is required.

---

# 13. Forecasting-oriented behavior

The resulting REN fields should be usable later as forecasting features such as:

```text
consumption_mw
wind_generation_mw
solar_generation_mw
hydro_generation_mw
natural_gas_generation_mw
biomass_generation_mw
other_thermal_generation_mw
coal_generation_mw
wave_generation_mw
import_mw
export_mw
```

Do not implement feature engineering in Stage 2.

Do not implement:

```text
lags
rolling averages
ramps
ratios
ML models
```

Those belong to later phases.

The purpose here is only to ensure that valid normalized MW measurements can reach those later stages.

---

# 14. Selected REN series

Continue using the already approved Stage 2 selection:

```text
Consumption

Wind
Solar
Hydro
Natural Gas
Biomass
Other Thermal
Coal
Wave

Import
Export
```

Continue explicitly excluding/unselecting ancillary series already documented in Stage 2.

Do not broaden the REN product scope.

---

# 15. Geography

Keep the existing Stage 2 geography interpretation.

Do not invent:

```text
Spain
specific interconnector
specific neighboring country
```

for REN Import/Export.

Retain the current aggregate external-boundary representation.

---

# 16. Parser behavior

The parser should still be strict.

Continue to reject:

```text
unexpected schema
unknown selected concepts
unknown units
non-finite values
invalid Decimal values
array-length mismatches
unexpected label sequence
invalid response structure
unsupported day length
```

This policy change relaxes only the unnecessary semantic blocker around the precise MW statistic.

It does **not** relax structural validation.

---

# 17. Existing archive/replay behavior

Preserve:

```text
immutable original bytes
SHA-256 content addressing
retrieval provenance
parse provenance
correction history
offline replay
same-query changed-body preservation
```

Do not redesign those mechanisms.

---

# 18. No new provider calls

This task is **offline implementation only**.

Do not call:

```text
REN
E-REDES
ESIOS
ENTSO-E
Open-Meteo
MIBGAS
```

Use existing synthetic fixtures and existing retained/test evidence.

No additional live validation is required for this implementation task.

---

# 19. Repository baseline

Start with:

```bash
git status --short
git log --oneline --decorate -10
```

Record:

```text
branch
HEAD
locally recorded origin/main
existing Stage 2 changes
```

Preserve all legitimate existing Stage 2 work.

Do not discard or overwrite pre-existing uncommitted work.

---

# 20. Read before modifying

Read:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md
docs/codex/reports/phase_2_stage_1_report.md
docs/codex/reports/phase_2_stage_2_ren_report.md
docs/codex/reports/phase_2_stage_2_ren_eredes_time_semantics_experiment.md

docs/adr/0003-*
docs/adr/0004-*
docs/adr/0005-*

src/iberian_shakti/contracts/
src/iberian_shakti/ingestion/ren/

tests/unit/ingestion/ren/
tests/integration/test_ren_flow.py
tests/data/ren/README.md
```

Understand the current blocker before changing it.

---

# 21. Store this prompt first

Before implementation, save this exact operator prompt at:

```text
docs/codex/prompts/phase_2/
phase_2_stage_2_ren_revised_semantics_implementation.md
```

Do not modify older prompt-history files.

---

# 22. Decision documentation

This changes an intentional previous Stage 2 fail-closed policy.

Preserve that decision history.

Prefer one short new ADR, for example:

```text
docs/adr/0006-ren-provisional-period-semantics.md
```

The ADR should explain, concisely:

```text
Why the previous gate existed.

What evidence is now available.

Why exact mean-vs-instantaneous classification
is not required for the price-forecasting use case.

Why MW values remain unconverted.

Why the profile is provisional/versioned.

How future REN clarification will be handled.
```

Do not rewrite ADR 0005 as though the original decision never existed.

If project ADR conventions use a different next number, follow them.

---

# 23. Tests

Add only tests necessary for the revised behavior.

At minimum cover:

### Ordinary day

```text
96 REN periods
successful normalized SystemMeasurement records
Europe/Lisbon → UTC mapping
```

### Spring DST

```text
92 periods
missing local 01:00–01:45
correct unique UTC sequence
```

### Autumn DST

```text
100 periods
two repeated 01:00–01:45 blocks
100 unique physical UTC periods
no deduplication
```

### Value semantics

Verify:

```text
MW value retained exactly
provider-period semantic accepted
no MWh conversion
```

### Fail closed

Verify rejection of:

```text
wrong label order
wrong label count
unexpected duplicate outside valid fold
unit mismatch
array mismatch
unknown selected series
```

### Replay

Verify that successful normalized records can be reproduced offline from the same archived raw body/profile.

---

# 24. Regression protection

All existing Phase 1 and Stage 1 behavior must remain intact.

In particular:

```text
OMIE behavior unchanged
legacy serialization unchanged unless explicitly versioned
shared query/archive/replay unchanged
private-auth behavior unchanged
no provider-specific regression outside REN
```

Run:

```bash
ruff check .
ruff format --check .
mypy src
pytest
git diff --check
```

Use the repository's normal pre-commit validation.

Do not reduce or delete tests merely to obtain a pass.

---

# 25. Stage 2 report

Update:

```text
docs/codex/reports/phase_2_stage_2_ren_report.md
```

Preserve historical context.

Add a clearly dated section explaining that the engineering policy changed by explicit operator decision after:

```text
official REN 15-minute-period evidence
DST experiment
blackout experiment
comparison with forecasting practice
```

Do not pretend the original semantic uncertainty disappeared.

The report should distinguish:

```text
Known / accepted:
- MW source values
- 15-minute source period
- Europe/Lisbon empirical profile
- interval-start empirical interpretation
- ordered DST mapping

Still unresolved:
- provider-authoritative statement of exact MW statistic
- provider-authoritative label definition
- authoritative autumn fold contract
```

Then explain why those unresolved details no longer block forecasting ingestion.

---

# 26. Revised Stage 2 acceptance rule

Stage 2 may now PASS if all of the following hold:

```text
REN selected product fetch contract implemented
strict parser implemented
selected series mapped correctly
raw archive/provenance/replay work
ordinary-day normalization works
spring DST normalization works
autumn DST normalization works
MW preserved without conversion
provider-period semantic represented honestly
profile is explicitly provisional/versioned
tests pass
Phase 1 and Stage 1 regressions remain clean
documentation accurately records unresolved semantics
```

The following are **not required for Stage 2 PASS** anymore:

```text
proof that MW is arithmetic interval mean
proof that MW is instantaneous
written REN confirmation
authoritative REN DST/fold documentation
```

Those remain future semantic refinements.

---

# 27. Do not start Stage 3

Even if Stage 2 reaches PASS:

```text
do not implement ESIOS
do not implement ENTSO-E
do not implement Open-Meteo
do not implement MIBGAS
```

Stop after Stage 2 implementation, tests, and report.

Stage 3 requires separate operator instruction.

---

# 28. No later-phase work

Do not touch:

```text
Snowflake
dbt
features
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

# 29. Git rules

Do not:

```text
create branch
stage
commit
push
```

Leave all changes for operator review.

---

# 30. Final response

Return a concise implementation summary containing:

1. files changed;
2. contract change, if any;
3. REN profile version;
4. adopted timezone;
5. adopted label role;
6. DST behavior;
7. representation of REN MW values;
8. confirmation that no MW→MWh conversion exists;
9. successful normalized record behavior;
10. focused REN test count;
11. full pytest result;
12. Ruff result;
13. mypy result;
14. pre-commit/diff-check result;
15. updated Stage 2 verdict;
16. remaining unresolved semantic points;
17. exact Git status;
18. confirmation:
   - no provider request;
   - no branch;
   - no staging;
   - no commit;
   - no push.

If all revised acceptance criteria pass, finish with:

```text
Phase 2 Stage 2 — PASS

REN ingestion now uses a versioned provisional empirical
15-minute source-period profile suitable for downstream
price-forecasting features.

The exact provider definition of the MW statistic remains
documented but is no longer an ingestion blocker.

Stage 3 has not been started or authorized.
```

If any required engineering or regression criterion fails, keep:

```text
Phase 2 Stage 2 — PASS WITH GAPS
```

and describe the exact blocker.

Stop there.
