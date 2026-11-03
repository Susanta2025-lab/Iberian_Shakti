# Iberian_Shakti — Phase 2 Stage 2
## Minimal Independent REN + E-REDES Blackout / DST Evidence Experiment

You are working in the existing **Iberian_Shakti** repository on `main`.

This is a focused continuation of **Phase 2 Stage 2 — REN Integration**.

Current Stage 2 verdict:

```text
PASS WITH GAPS
```

Stage 2 remains blocked by unresolved REN source-time semantics.

The previous external-project audit concluded:

```text
PortugueseOPD methodology classification:
C — Useful corroboration only

MW-statistic status:
UNRESOLVED
```

The audit recommended independently reproducing the empirical REN/E-REDES timing evidence before considering any change to the REN time profile.

This task performs exactly that bounded evidence experiment.

It is **not**:

```text
a new readiness assessment
Stage 3
Stage 8 controlled live validation
production acceptance
a request to modify the REN parser/profile
```

---

# 1. Primary objective

Independently test the following hypotheses:

```text
H1 — REN ElectricityProductionBreakdownDaily uses
     Europe/Lisbon local civil-day clock labels.

H2 — REN HH:MM labels correspond to the START
     of their physical 15-minute period.

H3 — On DST transition days, ordered REN array positions
     correspond to successive physical Europe/Lisbon
     quarter-hour periods, including the repeated autumn hour.
```

Use two evidence mechanisms:

```text
A. REN spring/autumn DST-day structure

B. Cross-source timing around the
   2025-04-28 Iberian blackout using:
   REN Consumption
   versus
   E-REDES substation load/energy observations
```

Do not assume any hypothesis is true before testing it.

---

# 2. Explicit limitation — MW statistic

This experiment does **not** automatically establish whether REN's MW values are:

```text
instantaneous power
quarter-hour mean power
another statistic
```

Treat that as an independent question.

Do not infer:

```text
15-minute labels
+
MW
=
15-minute mean MW
```

unless product-specific evidence independently proves it.

The previous audit found that PortugueseOPD converts E-REDES interval energy into mean MW, but this does not establish REN's own MW statistic.

If the experiment resolves H1–H3 but not the MW statistic, report that explicitly.

Do not change Iberian_Shakti's measurement contracts.

---

# 3. Repository baseline

Before doing anything:

```bash
git status --short
git log --oneline --decorate -15
```

Record:

```text
branch
HEAD
origin/main as locally recorded
working-tree state
```

Expected historical baseline before Stage 2 work:

```text
HEAD:
8a377dd — feat: establish Phase 2 multi-source foundation
```

The repository may currently contain the expected uncommitted Phase 2 Stage 2 REN work.

Do not treat those existing changes as contamination.

Preserve them.

---

# 4. Read authoritative local material first

Read completely:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md
docs/codex/reports/phase_2_stage_1_report.md
docs/codex/reports/phase_2_stage_2_ren_report.md

docs/adr/0003-*
docs/adr/0004-*
docs/adr/0005-*

src/iberian_shakti/ingestion/ren/
tests/unit/ingestion/ren/
tests/integration/test_ren_flow.py
tests/data/ren/README.md
```

Also review the previous PortugueseOPD audit available to the operator if its content is present in the task context.

Do not create another readiness assessment.

---

# 5. Prompt-history requirement

Before executing provider requests, store this complete operator prompt at:

```text
docs/codex/prompts/phase_2/phase_2_stage_2_ren_eredes_time_semantics_experiment.md
```

Do not alter historical Phase 2 prompts.

This prompt file and the final evidence report are the only planned repository documentation additions/changes for this experiment.

Do not modify implementation code, contracts, fixtures, existing tests or ADR semantics.

---

# 6. Final experiment report

Create:

```text
docs/codex/reports/phase_2_stage_2_ren_eredes_time_semantics_experiment.md
```

This is an **evidence experiment report**, not a replacement Stage 2 report.

Do not change the Stage 2 verdict automatically.

Any later change to:

```text
docs/codex/reports/phase_2_stage_2_ren_report.md
```

requires a separate operator-authorized implementation task.

---

# 7. Provider-call authorization

This prompt explicitly authorizes a very small number of **read-only public data requests** to:

```text
REN DataHub
E-REDES public open-data service
```

only for the exact experiment below.

No authentication probing.

No credentials.

No account creation.

No write operations.

No crawling.

No bulk history.

No pagination beyond what is strictly required for the specified bounded records.

No unrelated endpoints.

No ESIOS.

No ENTSO-E.

No Open-Meteo.

No MIBGAS.

---

# 8. Request budget

Hard experiment ceiling:

```text
REN logical data requests:       3
E-REDES logical data requests:   5 preferred, 10 maximum
official metadata/schema calls:  5 maximum

total physical HTTP attempts:    24 maximum
```

Use fewer whenever possible.

Do not retry content/schema failures.

For transport/transient failures, use at most the project's normal bounded retry behavior.

Do not probe rate limits.

Do not poll.

Do not parallelize aggressively.

Use conservative sequential pacing.

If the experiment would exceed these limits:

```text
STOP
```

and report the exact reason.

---

# 9. REN experiment dates

Use exactly these REN source dates:

```text
2025-04-28 — Iberian blackout
2025-03-30 — spring DST transition
2025-10-26 — autumn DST transition
```

REN product:

```text
ElectricityProductionBreakdownDaily
```

Preferred request profile:

```text
culture=en-US
date=YYYY-MM-DD
```

Use the exact fixed REN route already established by Stage 2.

Do not fetch any other REN date unless absolutely necessary and operator-authorized separately.

---

# 10. Preserve provider evidence safely

Real provider bodies must **not** be committed to Git unless existing rights policy clearly permits that.

Default:

```text
/tmp/iberian-shakti-ren-eredes-time-experiment/
```

Use separate subdirectories for:

```text
ren/
eredes/
official_metadata/
analysis/
```

For every acquisition retain locally:

```text
exact safe request identity
provider
product/dataset
requested date/window
acquisition UTC timestamp
HTTP status
attempt count
Content-Type
byte length
SHA-256 of original response bytes
local evidence path
```

Preserve original complete bytes unchanged.

Do not normalize and overwrite raw evidence.

Do not log sensitive or unnecessarily large response bodies.

There should be no credentials in this experiment.

---

# 11. REN DST experiment

For:

```text
2025-03-30
2025-10-26
```

inspect:

```text
xAxis.categories
series count
array lengths
selected Consumption array
```

Verify actual source observations.

Do not simply assume the existing Stage 2 evidence.

For spring:

determine whether the ordered labels correspond exactly to the physical quarter-hour sequence of a `Europe/Lisbon` civil day.

Candidate expectation:

```text
92 quarter-hour positions
01:00
01:15
01:30
01:45
absent
```

For autumn:

candidate expectation:

```text
100 quarter-hour positions
01:00
01:15
01:30
01:45
appear twice
```

Generate the corresponding physical Europe/Lisbon calendar independently using:

```python
ZoneInfo("Europe/Lisbon")
```

Do not use fixed UTC offsets.

Compare:

```text
source ordered labels
vs
generated ordered Europe/Lisbon labels
```

Require exact ordered equality before describing the source as calendar-compatible.

---

# 12. DST conclusions must remain evidence-scoped

If exact equality occurs, classify it as:

```text
O — direct REN source behavior
```

supporting:

```text
Europe/Lisbon-compatible clock sequence
```

Do **not** automatically claim:

```text
D — REN officially defines Europe/Lisbon
```

unless provider-authored documentation is independently found.

Also note:

exact repeated-label ordering alone cannot prove that REN's values belong to the two physical folds in chronological order if the repeated labels are identical.

Evaluate that remaining ambiguity explicitly.

---

# 13. E-REDES source discovery

The previous audit identified these candidate E-REDES datasets:

```text
diagrama_carga_subestacao_01_a_07
diagrama_carga_subestacao_08_a_10
diagrama_carga_subestacao_11_a_12
diagrama_carga_subestacao_13_a_15
diagrama_carga_subestacao_16_a_18
```

The audit stated that these are a reproducible candidate product choice but that the original PortugueseOPD blackout profile's exact source query was not independently verified.

Before requesting records:

1. verify these dataset identifiers against the current official E-REDES public open-data service;
2. inspect only the minimum official dataset metadata/schema required to understand:
   - timestamp field;
   - energy/load field;
   - units;
   - geography/substation identity;
   - time support if documented;
3. record exact dataset IDs actually used.

If these dataset IDs no longer exist, do not substitute a materially different dataset without documenting why it is equivalent.

---

# 14. E-REDES blackout window

Target physical UTC interval window:

```text
2025-04-28 10:00Z
through
2025-04-28 11:00Z
```

At minimum evaluate four consecutive physical quarter-hours:

```text
[10:00, 10:15)
[10:15, 10:30)
[10:30, 10:45)
[10:45, 11:00)
```

Retrieve only the records necessary to establish the corresponding E-REDES behavior.

Preserve at minimum:

```text
original timestamp field
substation/facility identity
energy/load value
unit
source dataset
row count
missingness
```

Prefer a fixed, stable facility cohort across the four intervals.

Do not silently change the substation population between periods.

---

# 15. E-REDES aggregation discipline

If E-REDES data provides interval energy in kWh and the official dataset semantics establish that support, a derived interval-average power may be calculated as:

```text
MW = kWh / 1000 / 0.25
```

equivalently:

```text
MW = kWh / 250
```

But label the result clearly:

```text
derived E-REDES mean MW
```

Do not imply that REN uses the same statistic.

Document:

```text
raw E-REDES quantity
raw unit
derived quantity
derivation
record cohort
missing-data policy
```

No silent interpolation.

No zero filling.

No arbitrary station exclusions.

---

# 16. Blackout hypothesis

Test this specific candidate alignment:

```text
physical interval start:
2025-04-28 10:30Z

Europe/Lisbon local start:
2025-04-28 11:30

candidate REN label:
11:30

candidate E-REDES interval-end label:
11:45
```

PortugueseOPD's test claims:

```text
REN Consumption at 11:30
<
30% of preceding REN Consumption value

and

E-REDES energy/load at 11:45
<
30% of its preceding 11:30 value
```

The previous audit could inspect this assertion but could not verify the underlying data because PortugueseOPD's evidence files were absent.

Reproduce this independently.

---

# 17. Do not rely only on the 30% threshold

The `<30%` threshold is a useful reproduction check, not proof by itself.

Build a small comparison table covering all four physical intervals.

For example:

```text
physical UTC interval
candidate REN local label
REN Consumption MW
REN change from prior interval

candidate E-REDES label
E-REDES aggregate energy/load
derived mean MW if justified
E-REDES change from prior interval
```

Evaluate whether the discontinuity occurs in the same physical interval under competing label interpretations.

---

# 18. Compare competing REN label hypotheses

At minimum evaluate:

```text
H-start:
REN HH:MM = interval start

H-end:
REN HH:MM = interval end

H-instant:
REN HH:MM = instantaneous/sample timestamp
```

For the blackout experiment determine which hypotheses are:

```text
consistent
inconsistent
indistinguishable
```

with the observed cross-source transition.

Do not force a binary answer if evidence cannot distinguish them.

Particularly:

a synchronized abrupt change may strongly discriminate start versus end placement, while still not distinguishing interval-average versus instantaneous statistic.

State that explicitly.

---

# 19. Independent blackout chronology

Search for the smallest suitable **official** source establishing timing of the 2025-04-28 Iberian blackout.

Prefer:

```text
REN
E-REDES
Portuguese government/regulator
REE
ENTSO-E
other official system-operator material
```

Look for an explicit timestamp with:

```text
UTC
timezone offset
or sufficiently unambiguous local legal time
```

Do not use news articles as primary timing authority if official material is available.

Do not perform broad historical research.

The purpose is only to provide an independent temporal anchor.

If no sufficiently precise official timestamp is found:

```text
record U — unresolved independent chronology
```

and continue the cross-source comparison without overstating it.

---

# 20. Evidence taxonomy

Every material conclusion must use:

```text
D — official/provider-authored documentation

O — directly observed source behavior

X — cross-source empirical evidence

I — engineering inference

P — project policy

U — unresolved
```

Examples:

```text
REN 2025-10-26 contains 100 values
→ O

REN's ordered labels exactly equal a Europe/Lisbon physical-day sequence
→ O + I

REN officially declares Europe/Lisbon
→ D only if documented

REN label is interval start because blackout alignment fits
→ X/I

REN value is quarter-hour mean MW
→ U unless independently established
```

Do not collapse these categories.

---

# 21. Determine what the experiment actually establishes

Answer independently:

### A. Timezone

One of:

```text
strong empirical evidence for Europe/Lisbon
weak corroboration only
contradicted
unresolved
```

### B. Label placement

One of:

```text
strong evidence for interval start
strong evidence for interval end
instant/sample remains plausible
multiple interpretations remain plausible
unresolved
```

### C. DST ordering

One of:

```text
strong evidence that source order follows physical Europe/Lisbon sequence
calendar-compatible but fold ownership unresolved
contradicted
unresolved
```

### D. MW statistic

Exactly one of:

```text
RESOLVED
UNRESOLVED
```

Use `RESOLVED` only with actual product-specific evidence.

---

# 22. Stage 2 acceptance restraint

Even if A–C become strong empirical evidence:

do not modify:

```text
src/iberian_shakti/ingestion/ren/
```

Do not emit positive `SystemMeasurement` records.

Do not change:

```text
time_semantics_unknown
```

Do not bump the REN source profile.

Do not modify ADR 0005.

Do not change the Stage 2 verdict.

This experiment produces evidence only.

A separate operator-authorized task will decide whether to adopt an explicitly empirical source profile.

---

# 23. No Stage 3

Do not implement or investigate:

```text
ESIOS
ENTSO-E
Open-Meteo
MIBGAS
```

beyond incidental references already in documentation.

Do not authorize Phase 2 Stage 3.

---

# 24. No Phase 3+ work

Do not touch:

```text
Snowflake
dbt
features
ML
training
registry
batch inference
FastAPI
dashboard
deployment
Kafka
Kubernetes
```

---

# 25. Local analysis tooling

Temporary analysis code may be created only under:

```text
/tmp/iberian-shakti-ren-eredes-time-experiment/
```

Do not add analysis scripts to the repository.

Prefer deterministic Python scripts/notebooks-free command-line analysis.

Record sufficient commands/methodology in the report so the experiment can later be reproduced.

---

# 26. Safety / retrieval requirements

Use:

```text
verified TLS
finite timeouts
bounded bodies
no redirects where project policy prohibits them
no hidden infinite retries
conservative request pacing
```

No user-agent or proxy tricks.

No scraping of authenticated interfaces.

No browser automation if a documented public API can provide the records.

No attempt to bypass provider controls.

---

# 27. Evidence integrity

For every real provider artifact used in conclusions record:

```text
SHA-256
byte length
acquisition UTC
safe request identity
provider
dataset/product
requested window
```

For derived tables/scripts record:

```text
input hashes
algorithm/version description
output hash if persisted
```

Do not put real provider bodies into Git.

The final report may include small numerical excerpts needed to demonstrate the conclusion, but do not reproduce complete provider datasets.

---

# 28. Validation of analysis

Use deterministic checks.

For REN DST:

```text
assert actual label count
assert array lengths agree
assert exact ordered label equality against generated candidate calendar
```

For blackout analysis:

```text
assert timestamps parse consistently
assert selected E-REDES cohort is stable
assert values are finite
assert units are known
assert no silent null/zero replacement
assert REN and E-REDES comparisons use clearly defined physical intervals
```

If any prerequisite fails, mark the experiment inconclusive rather than repairing the data heuristically.

---

# 29. Repository quality checks

Because implementation code must not change, a complete 1,281-test regression is not required unless repository changes unexpectedly extend beyond documentation.

At minimum run:

```bash
git diff --check
```

and applicable pre-commit hooks for:

```text
the new prompt file
the new experiment report
```

If any source/test/configuration file changes accidentally:

restore your own accidental change.

Do not restore or remove pre-existing Stage 2 changes.

---

# 30. Final Git review

Run:

```bash
git status --short
git diff --stat
git diff --check
```

Expected intentional repository differences from this experiment:

```text
docs/codex/prompts/phase_2/phase_2_stage_2_ren_eredes_time_semantics_experiment.md

docs/codex/reports/phase_2_stage_2_ren_eredes_time_semantics_experiment.md
```

plus the already-existing uncommitted Stage 2 changes.

No code implementation file should change because of this experiment.

Do not stage.

Do not commit.

Do not push.

Do not create a branch.

---

# 31. Required report structure

The experiment report must contain:

## A. Objective

Exact hypotheses tested.

## B. Baseline

Git state and existing Stage 2 status.

## C. Request budget

For each provider:

```text
logical requests
physical attempts
bytes
dates/windows
```

## D. Evidence inventory

For every retained artifact:

```text
provider
product/dataset
request identity
acquisition UTC
HTTP result
bytes
SHA-256
local temporary path
```

## E. Official documentation / chronology

Relevant `D` evidence.

## F. REN spring DST result

Actual label sequence/count and Europe/Lisbon comparison.

## G. REN autumn DST result

Actual label sequence/count, repeated-hour positions and Europe/Lisbon comparison.

## H. REN blackout-day result

Relevant Consumption sequence.

## I. E-REDES source definition

Dataset IDs, timestamp semantics, units and aggregation rules actually supported by official evidence.

## J. E-REDES blackout observations

Fixed-cohort records / aggregate behavior.

## K. Cross-source physical alignment

Table comparing the four quarter-hours around the transition.

## L. Competing label hypotheses

Evaluate:

```text
interval start
interval end
instant/sample
```

## M. DST fold assessment

State what source ordering does and does not prove.

## N. MW-statistic assessment

Exactly:

```text
RESOLVED
or
UNRESOLVED
```

with evidence.

## O. Evidence classification

Summarize:

```text
D
O
X
I
P
U
```

## P. Hypothesis verdicts

Explicit answers for H1/H2/H3.

## Q. Stage-2 implication

State whether evidence is sufficient to justify a later explicit empirical-profile decision.

Do not implement that decision.

## R. Remaining gaps

Especially MW statistic.

## S. Repository integrity

Confirm no implementation change.

## T. Final experiment verdict

Use exactly one:

```text
STRONG EMPIRICAL SUPPORT
PARTIAL EMPIRICAL SUPPORT
INCONCLUSIVE
CONTRADICTED
```

This verdict applies only to the timing experiment.

It is not the Stage 2 verdict.

---

# 32. Final Codex response

Return:

1. REN request count;
2. E-REDES request count;
3. official metadata request count;
4. physical attempt total;
5. evidence hashes;
6. spring DST result;
7. autumn DST result;
8. blackout REN transition;
9. blackout E-REDES transition;
10. whether the transitions align under REN interval-start interpretation;
11. competing-hypothesis result;
12. timezone conclusion;
13. label-placement conclusion;
14. DST-ordering conclusion;
15. MW-statistic status;
16. experiment verdict;
17. report path;
18. exact changed repository paths;
19. Git status;
20. confirmation of no commit/push/branch.

End with:

```text
Phase 2 Stage 2 remains unchanged pending operator review.
No Stage 3 authorization is implied by this experiment.
```

Do not implement any semantic change after obtaining the evidence.

Stop after the experiment and report.
