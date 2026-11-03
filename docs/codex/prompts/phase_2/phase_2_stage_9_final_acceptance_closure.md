# Iberian_Shakti — Phase 2 Stage 9
## Final Acceptance, Evidence Reconciliation and Phase Closure

Execute **Phase 2 Stage 9 — Final Acceptance and Closure**.

This is the final stage of Phase 2.

The goal is to reconcile all Phase 2 engineering and live evidence, complete the authoritative 44-criterion acceptance checklist, finalize documentation, run the final repository-wide validation gates, and determine whether Phase 2 can be formally closed.

This task is:

```text
EVIDENCE RECONCILIATION
+
FINAL DOCUMENTATION
+
FINAL VALIDATION
+
FORMAL PHASE 2 ACCEPTANCE
```

This is **not**:

```text
new provider development
new source/model selection
new live experimentation
Phase 3 implementation
Snowflake work
dbt work
feature engineering
ML training
deployment
```

---

# 1. Authoritative clean baseline

Current verified repository state:

```text
branch:
main

working tree:
clean

HEAD:
e3753ca feat: complete Phase 2 controlled live validation
```

Current committed history:

```text
e3753ca (HEAD -> main) feat: complete Phase 2 controlled live validation
17d1e19 test: complete Phase 2 pre-live engineering audit
c3476f1 test: complete Phase 2 cross-source integration hardening
77ff8e2 feat: complete Phase 2 Open-Meteo ingestion
f8dee4c feat: complete Phase 2 ENTSO-E ingestion
8ef31ef feat: complete Phase 2 ESIOS ingestion
13d5ff6 ci: run pre-commit in GitHub Actions
8bb5618 ci: add GitHub Actions quality checks
09792e9 feat: complete Phase 2 REN ingestion
8a377dd feat: establish Phase 2 multi-source foundation
70f4204 docs: record Phase 2 readiness assessment
a4191a3 (origin/main, origin/HEAD) docs: close Phase 1 OMIE ingestion
```

Local `main` is intentionally ahead of `origin/main` by **11 commits**.

Do **not push**.

Treat:

```text
e3753ca
```

as the authoritative clean Stage 9 baseline.

---

# 2. Mandatory initial verification

Start with:

```bash
git status --short
git log --oneline --decorate -15
git diff --check
```

Require:

```text
branch = main
HEAD = e3753ca
working tree = clean
```

Also verify that the committed Stage 8 report currently concludes:

```text
Phase 2 Stage 8 — PASS.
```

and that its targeted ESIOS continuation is present in the committed tree.

If any of these conditions are false:

```text
STOP
```

Do not repair Git state automatically.

Report the exact discrepancy.

---

# 3. Git restrictions

During Stage 9 do not:

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

Leave all Stage 9 changes unstaged for operator review.

The operator will decide the final commit and later Phase 2 push.

---

# 4. Save this prompt first

Before changing code or documentation, save this exact prompt as:

```text
docs/codex/prompts/phase_2/
phase_2_stage_9_final_acceptance_closure.md
```

Do not modify earlier prompts.

---

# 5. Read the complete authoritative Phase 2 history

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

docs/codex/reports/
phase_2_stage_6_cross_source_integration_hardening_report.md

docs/codex/reports/
phase_2_stage_7_pre_live_engineering_audit_report.md

docs/codex/reports/
phase_2_stage_8_controlled_live_validation_report.md
```

Also read:

```text
docs/adr/
README.md
docs/architecture/
docs/runbooks/
```

and the accepted provider profiles/contracts where needed to verify final documentation.

Do not rely only on report summaries if a criterion requires code/test evidence.

---

# 6. Accepted provider/product scope

Phase 2 final acceptance covers exactly:

```text
REN
→ ElectricityProductionBreakdownDaily

ESIOS
→ indicator 544
→ Demanda prevista Peninsular
→ bounded profile/parser/report 0.2.0

ENTSO-E
→ ES actual total load A65/A16
→ PT day-ahead wind/solar forecast A69/A01
→ ES day-ahead wind/solar forecast A69/A01

Open-Meteo
→ ERA5 Historical Weather
→ DWD ICON-EU Forecast
→ models=icon_eu
```

Phase 1 OMIE remains a prerequisite/shared baseline and must continue to pass compatibility/regression checks.

Do not expand Phase 2 scope.

---

# 7. Stage 8 accepted final state

Treat the committed Stage 8 evidence as authoritative.

The targeted ESIOS continuation resolved the former gap with:

```text
ESIOS profile:
0.2.0

parser:
0.2.0

report:
indicator544.v0.2.0
```

for a bounded five-minute logical half-open UTC window.

The corrected controlled live request returned:

```text
288 samples
300-second cadence
no gaps
no duplicates
no samples outside logical window
successful normalization
successful network-denied replay
```

The original ESIOS overrun acquisition and failed parse history remain preserved separately.

Do not delete or rewrite that historical evidence.

---

# 8. Preserve the ESIOS version boundary

Final documentation must make clear that:

```text
0.1.0
```

is retained as historical behavior/evidence, while:

```text
0.2.0
```

is the accepted bounded product profile.

The 0.2.0 request semantics represent the logical half-open window by using the last desired five-minute native timestamp as the provider end filter.

Do not describe this as universal proof of all ESIOS DST/filtering internals.

Do not claim that ESIOS universally filters in Europe/Madrid wall time.

---

# 9. Preserve accepted REN limitation

REN remains accepted under:

```text
profile/parser:
0.2.0

timezone:
Europe/Lisbon

period interpretation:
interval_start

statistic:
provider_period_value

evidence status:
provisional_empirical
```

Stage 8 confirmed compatibility with the real response.

It did **not** establish a new authoritative provider definition of:

```text
mean vs instantaneous MW
fold semantics
label-placement semantics
```

Do not strengthen these claims during final documentation.

---

# 10. Preserve forecast-vintage limitations

Final documentation must clearly distinguish:

```text
current/live forecast acquisition
```

from:

```text
historical forecast known before a past market cutoff
```

In particular:

```text
Open-Meteo ICON-EU latest snapshot
!=
historical forecast vintage at an old MIBEL cutoff

ERA5 reanalysis
!=
historical weather forecast
```

Do not claim that Phase 2 solved historical forecast-vintage reconstruction.

That remains relevant to later feature-engineering/data-leakage controls.

---

# 11. No new live provider requests

Stage 9 is documentation/acceptance work.

Do **not** make any new request to:

```text
OMIE
REN
ESIOS
ENTSO-E
Open-Meteo
```

Do not probe:

```text
credentials
catalogues
availability
quota
rate limits
metadata
```

Use the retained Stage 8 evidence.

If a mandatory criterion appears impossible to close from existing evidence:

```text
do not make another request
```

Report the gap instead.

---

# 12. No live archive mutation required

Do not modify the retained Stage 8 live archives.

Do not copy real raw provider payloads into:

```text
tests/
fixtures/
Git
```

Do not make `/tmp` live archives part of the repository.

The final report may reference their safe evidence metadata already recorded in Stage 8.

---

# 13. Secret-safety verification

Verify that:

```text
.env
```

remains ignored and untracked.

Run:

```bash
git check-ignore -v .env
git status --short
```

Do not print `.env`.

Do not read or inspect credential values.

Do not require credentials for Stage 9.

Stage 9 tests must remain credential-free.

---

# 14. Final 44-criterion reconciliation

The authoritative Phase 2 readiness assessment contains **44 numbered final acceptance criteria**.

Stage 9 must reconcile **every one of them individually**.

Do not omit, merge, renumber or paraphrase away a requirement.

Create a final table with columns:

```text
#
Original criterion
Final status
Primary evidence
Supporting evidence
Residual limitation
```

Allowed final statuses:

```text
SATISFIED

SATISFIED WITH DOCUMENTED LIMITATION

NOT SATISFIED
```

Do not use:

```text
LIVE VALIDATION REQUIRED
FINAL ACCEPTANCE / STAGE 9
```

because Stage 9 must now resolve those provisional Stage 7 classifications.

---

# 15. Strict criterion interpretation

For each criterion ask:

```text
What does the original criterion actually require?
What code/test/document/live evidence satisfies it?
Does a retained limitation contradict the requirement?
```

Do not declare a criterion satisfied because a nearby requirement passed.

Do not silently weaken wording from the authoritative readiness assessment.

---

# 16. SATISFIED WITH DOCUMENTED LIMITATION

Use:

```text
SATISFIED WITH DOCUMENTED LIMITATION
```

only when:

1. the mandatory engineering intent of the criterion is satisfied;
2. the limitation is already explicitly accepted by the Phase 2 design/operator decision;
3. the limitation does not invalidate correctness of the implemented product;
4. the limitation is not being hidden merely to obtain Phase 2 PASS.

Examples that may require careful consideration include:

```text
REN provisional empirical semantics

ESIOS provider-wide ambiguous DST/filtering internals

unknown forecast issue/run times

historical forecast vintage availability

licensing/operational production clearance
```

Do not automatically classify these one way or another.

Compare them against the exact original criterion wording.

---

# 17. Criterion 4 — REN requires special scrutiny

Stage 7 previously treated the stronger REN evidence requirement conservatively.

Stage 8 demonstrated successful real compatibility but did not turn the provisional interpretation into an authoritative provider claim.

For criterion 4:

```text
read the exact original wording
read ADR 0006
read Stage 2 revised acceptance
read Stage 8 real REN findings
```

Then decide whether:

```text
SATISFIED WITH DOCUMENTED LIMITATION
```

is justified under the accepted Phase 2 operator decision,

or whether the original criterion remains genuinely unmet.

Do not invent official evidence.

If the original mandatory wording cannot truthfully be satisfied:

```text
Phase 2 cannot be declared fully CLOSED
```

unless the readiness/acceptance history itself explicitly records an accepted replacement criterion.

Document the reasoning precisely.

---

# 18. Criterion 5 — ESIOS

Reconcile criterion 5 using both:

```text
original Stage 3 implementation

Stage 8 first real acquisition

targeted ESIOS 0.2.0 acquisition
```

Evidence now includes observed real metadata:

```text
indicator 544
Demanda prevista Peninsular
Potencia (20)
Cinco minutos (219)
Península (8741)
```

and successful bounded 288-record validation/replay.

There remains no explicit native unit field in the live response.

Do not describe MW as a newly observed native `unit` field if it was not present.

---

# 19. Criterion 18 — authentication

Stage 8 provided successful normal authenticated requests for:

```text
ESIOS
ENTSO-E
```

without separate credential probing.

Use that evidence to reconcile authentication requirements.

Do not expose secrets in Stage 9 documentation.

---

# 20. Criterion 20 — whole-invocation limits

Stage 8 introduced and validated explicit whole-run controls including:

```text
logical request caps
HTTP attempt caps
aggregate attempted body cap
conservative inbound byte cap
wall-clock deadline
sequential pacing
```

Reconcile criterion 20 using:

```text
_live_budget.py
phase2_live.py
Stage 8 synthetic controller tests
actual Stage 8 run accounting
```

Do not describe test-only Stage 6 limits as production limits.

---

# 21. Criterion 29 — real error/no-data semantics

Interpret criterion 29 carefully.

Stage 8 did not deliberately provoke provider failures.

Existing offline parser/error tests establish controlled behavior for supported error documents, while Stage 8 established successful live product behavior.

Do not claim real examples of provider errors that were never observed.

Determine whether the criterion requires real natural errors or merely safe implemented distinction.

Document the distinction.

---

# 22. Criterion 38 — live command

Stage 8 implemented the explicit operator-only command:

```text
python -m iberian_shakti.ingestion.phase2_live
```

with:

```text
--live
--replay-only
```

and targeted ESIOS boundary mode.

Verify final documentation accurately states:

```text
default offline
explicit live opt-in
fixture/repository archive rejection
credential requirements
finite whole-run budgets
no CI/pre-commit/pytest live execution
```

---

# 23. Criteria 39 and 40 — controlled live evidence

Reconcile these against the completed real Stage 8 evidence.

All seven accepted required products now have successful live acquisition under the accepted final profiles:

```text
REN

ESIOS 544 bounded 0.2.0

ENTSO-E ES actual load

ENTSO-E PT renewables

ENTSO-E ES renewables

ERA5

ICON-EU
```

and successful denied replay.

The original failed ESIOS acquisition remains preserved as historical evidence and does not negate the successful corrected profile.

---

# 24. Criterion 41 — final documentation

This is a primary Stage 9 responsibility.

Ensure final documentation accurately describes:

```text
implemented provider scope
product/profile/parser versions
credentials
queries
units
statistics
geography
time semantics
actual/forecast/reanalysis distinction
forecast-vintage limitation
revision/correction semantics
archive/provenance
replay
error handling
retry/bounds
live opt-in
known limitations
attribution/licensing boundaries
```

No documentation should imply:

```text
complete provider history
guaranteed future provider compatibility
production SLA
commercial/licensing clearance
historical cutoff-safe forecasts
```

unless actually established.

---

# 25. Criterion 42 — final engineering gates

Run all final repository quality gates against the actual Stage 9 tree.

Do not rely only on earlier Stage 8 results.

Freshly run:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
pre-commit run --all-files
```

Also inspect:

```bash
git status
git diff --stat
git diff
```

and all untracked Stage 9 files.

---

# 26. Criterion 43 — scope integrity

Verify Phase 2 still contains no implementation of:

```text
Snowflake
dbt
feature engineering
ML model training
model registry
batch prediction pipeline
FastAPI serving
dashboard
Kafka
Kubernetes
cloud deployment
```

Do not treat existing repository skeletons/placeholders for future phases as Phase 2 implementations if they predated Phase 2.

Confirm Stage 9 itself introduces none of these.

---

# 27. Criterion 44 — final acceptance trace

Produce a final acceptance trace mapping all 44 criteria to concrete evidence.

This must be stronger than the Stage 7 provisional table.

For every criterion include specific references such as:

```text
ADR
stage report
code module
test module
live evidence section
final documentation
```

Do not write vague evidence such as:

```text
"covered by tests"
```

where a more specific reference is available.

---

# 28. Final provider matrix

Create a concise final implemented-source matrix containing at least:

| Provider/product | Final version | Geography | Kind | Native cadence/support | Units | Live validated | Replay validated |
| --- | --- | --- | --- | --- | --- | --- | --- |

Include:

```text
OMIE prerequisite baseline
REN
ESIOS
ENTSO-E ES load
ENTSO-E PT renewables
ENTSO-E ES renewables
ERA5
ICON-EU
```

Keep OMIE clearly identified as the Phase 1 prerequisite rather than a new Phase 2 provider implementation.

---

# 29. Final version inventory

Document exact accepted final versions for:

```text
shared query/measurement/auth contracts where relevant

REN profile/parser

ESIOS profile/parser/report

ENTSO-E profile/parser/reports

ERA5 profile/parser/report

ICON-EU profile/parser/report

weather record schema

retrieval/provenance schemas
```

Do not guess version numbers.

Read them from the committed implementation/reports.

---

# 30. Final architecture documentation

Update architecture documentation only where required for the accepted Phase 2 final state.

The architecture should show:

```text
external provider
→ typed query
→ bounded retrieval
→ immutable raw archive
→ retrieval provenance
→ strict parser
→ normalized typed record
→ parse provenance
→ network-free replay
```

and the Phase 2 providers/products.

Do not introduce later-phase architecture as implemented.

---

# 31. README Phase 2 status

Update the README so that Phase 2 is clearly described as:

```text
complete
```

only if final acceptance passes.

Summarize:

```text
providers
products
offline/live validation
replay
major semantic boundaries
```

Keep it concise.

Do not put detailed audit evidence into the README.

---

# 32. Runbook finalization

Finalize the ingestion runbook for:

```text
normal offline tests
credential setup
explicit live validation command
live archive requirements
replay-only operation
ESIOS bounded profile behavior
safe handling of live evidence
known limitations
```

Do not include real token values.

Do not require `.env` specifically if process environment remains the formal application configuration mechanism; document the operator-local `.env` workflow only as appropriate and safe.

---

# 33. ADR index

Verify the ADR index includes all accepted Phase 2 decisions, including:

```text
ADR 0006 REN provisional period semantics

ADR 0007 explicit weather output query selection

ADR 0008 ESIOS bounded five-minute request
```

Do not create another ADR merely to declare Phase 2 complete.

Create a new ADR only if Stage 9 discovers an actual new durable architectural decision.

---

# 34. Historical reports remain immutable evidence

Do not rewrite previous stage reports to make history look cleaner.

Preserve:

```text
PASS WITH GAPS histories

blocked histories

original ESIOS failure

subsequent targeted resolution

REN earlier uncertainty
```

The final report should reconcile them rather than erase them.

---

# 35. No new production behavior unless required

Stage 9 should normally require:

```text
documentation
acceptance report
possibly acceptance-focused tests
```

not new provider behavior.

If a real inconsistency is discovered:

```text
fix only if locally determinable
add regression
document it
```

Do not make a new live request.

If fixing it would require provider observation:

```text
mark Phase 2 acceptance gap
```

instead.

---

# 36. Final network-denied assurance

The final full pytest suite must continue running under the existing network-denied configuration.

No test should require:

```text
real internet
real ESIOS token
real ENTSO-E token
Stage 8 /tmp archive
```

Do not add live evidence as a required test dependency.

---

# 37. Secret and repository hygiene

Before final acceptance verify:

```text
.env is ignored

.env is untracked

no credential appears in tracked/untracked Stage 9 artifacts

no real raw Stage 8 payload is under repository paths

no live manifest containing private request information is committed

no accidental temporary files exist
```

Use safe presence/exclusion checks only.

Never print credential values.

---

# 38. Stage 8 live archives

The final report may reference the Stage 8 live archive paths as operational evidence, but make clear:

```text
they are external local evidence
not repository fixtures
not required for ordinary tests
not committed to Git
```

Do not copy them into the repository.

---

# 39. Final limitations section

The final report must explicitly retain all genuine unresolved external limitations.

Review at minimum:

```text
REN provider-authoritative statistic/label/fold definition

ESIOS provider-wide filtering/DST internals beyond accepted bounded profile

historical forecast vintages

historical market-cutoff availability

forecast run/issue/publication times where unavailable

future provider schema/model changes

service availability

licensing/redistribution/attribution requirements

production/commercial clearance
```

Classify each as:

```text
accepted non-blocking limitation
future validation concern
later-phase data-governance concern
or Phase 2 blocker
```

Do not call something non-blocking without explaining why it does not invalidate the accepted product.

---

# 40. Phase 2 completion boundary

If Phase 2 closes, explicitly state what is now complete:

```text
provider ingestion foundation

provider-specific strict normalization

cross-source semantic compatibility

immutable raw evidence

retrieval/parse provenance

offline deterministic replay

security/boundedness hardening

controlled live validation
```

Also state what is **not** part of Phase 2:

```text
Snowflake ingestion

dbt transformation

feature matrices

cutoff-safe training datasets

forecast-model training

model registry

scheduled prediction

serving/dashboard
```

---

# 41. Phase 3 handoff

Do not implement Phase 3.

The final report may state that the next roadmap stage is:

```text
Phase 3 — Snowflake Data Platform
```

and may list only the high-level prerequisites now available from Phase 2.

Do not generate implementation code or terraform.

---

# 42. Final acceptance report

Create:

```text
docs/codex/reports/
phase_2_final_acceptance_report.md
```

Suggested structure:

```text
1. Executive verdict

2. Baseline and scope

3. Phase 2 development history
   - Stage 1
   - Stage 2 REN
   - Stage 3 ESIOS
   - Stage 4 ENTSO-E
   - Stage 5 Open-Meteo
   - Stage 6 cross-source
   - Stage 7 pre-live audit
   - Stage 8 controlled live validation

4. Final implemented provider/product matrix

5. Final profile/parser/version inventory

6. Shared architecture and invariants

7. Live evidence summary

8. Replay/provenance summary

9. Security/boundedness summary

10. Final 44-criterion reconciliation

11. Documentation acceptance

12. Final regression/quality gates

13. Remaining accepted limitations

14. Phase 2 completion boundary

15. Phase 3 handoff

16. Files changed

17. Git status

18. Final verdict
```

---

# 43. Development history summary

The final report should summarize the Phase 2 evolution factually.

Include major decisions such as:

```text
shared ingestion foundation

REN initial uncertainty → accepted provisional 0.2.0

ESIOS 544 implementation

ENTSO-E strict XML integration

ERA5 + explicit ICON-EU selection

cross-source hardening

pre-live security audit

controlled live validation

ESIOS 544 bounded 0.2.0 resolution
```

Do not turn the final report into a transcript.

Focus on engineering evidence and decisions.

---

# 44. Final Stage 6 regression

Run:

```bash
python -m pytest tests/integration/stage6 -q
```

This remains the permanent cross-source compatibility proof.

Record the fresh result.

---

# 45. Final Stage 7 security regression

Run the Stage 7 audit/security selection or the established equivalent command from the Stage 7 report.

Record a fresh result.

Do not merely copy the historical 457-case result.

If the selection command has evolved, document the exact current selection and result.

---

# 46. Final Stage 8 regression

Run the complete Stage 8 offline controller/ESIOS-boundary suite.

At minimum include:

```text
tests/integration/test_phase2_stage8_live.py

tests/integration/test_esios_boundary_semantics.py
```

Record a fresh result.

No real live call is permitted.

---

# 47. Provider-focused regression

Freshly run all provider-focused unit/integration suites for:

```text
OMIE
REN
ESIOS
ENTSO-E
Open-Meteo
```

Record the final count.

---

# 48. Full regression

Run:

```bash
python -m pytest
```

Acceptance requires:

```text
zero failures
zero skips introduced to obtain closure
```

If existing intentional skips existed before Phase 2, distinguish them rather than making a false claim.

Do not weaken tests.

---

# 49. Static validation

Run:

```bash
ruff check .
ruff format --check .
mypy src
pre-commit run --all-files
git diff --check
```

All must pass.

---

# 50. Final diff review

Review:

```bash
git status --short
git diff --stat
git diff
```

Remember that untracked files are not included in ordinary `git diff`.

Explicitly inspect every new Stage 9 file.

Ensure no accidental:

```text
credential
live payload
temporary file
debug dump
archive
```

is present.

---

# 51. Stage 9 PASS criteria

Stage 9 may conclude:

```text
Phase 2 Stage 9 — PASS.
Phase 2 — CLOSED.
```

only if:

```text
all 44 acceptance criteria are reconciled

no mandatory criterion is NOT SATISFIED

any SATISFIED WITH DOCUMENTED LIMITATION classification
is defensible from the authoritative requirement and accepted
Phase 2 decisions

all required final documentation is consistent

all seven Phase 2 required live products are accepted

all required network-denied replay evidence is accepted

Stage 6 cross-source regression passes

Stage 7 security regression passes

Stage 8 offline regressions pass

provider-focused regressions pass

full pytest passes

ruff passes

format passes

mypy passes

pre-commit passes

git diff --check passes

.env remains ignored/untracked

no credential or real live payload enters Git

no later-phase implementation entered Phase 2
```

---

# 52. Do not force closure

If even one mandatory criterion remains truthfully unresolved:

```text
do not declare Phase 2 CLOSED
```

Return:

```text
Phase 2 Stage 9 — PASS WITH GAPS.
Phase 2 remains open.
```

and state:

```text
criterion number
exact wording
missing evidence
why existing evidence is insufficient
whether it is externally blocked or locally fixable
```

Do not change the acceptance criterion merely to close the phase.

---

# 53. Locally fixable final documentation issue

If the only issue is:

```text
stale README wording
missing runbook detail
missing ADR index entry
incorrect status text
missing final test reference
```

fix it during Stage 9 and rerun relevant validation.

Do not leave a trivial locally fixable documentation defect as a Phase 2 gap.

---

# 54. Production-code defect discovered during Stage 9

If review discovers a genuine production-code defect:

```text
fix minimally
add permanent regression
rerun affected provider suite
rerun Stage 6/7/8 relevant selections
rerun full validation
```

Do not make any new live request.

If the fix cannot be validated without new provider access:

```text
Phase 2 remains open
```

and report why.

---

# 55. Final README status if Phase 2 passes

If final acceptance succeeds, update the Phase 2 roadmap status to clearly state:

```text
Phase 2 — Multi-Source Ingestion Expansion
CLOSED / PASS
```

Include the closure date:

```text
2026-11-03
```

if that remains the actual Stage 9 execution date.

If execution occurs on another date, use the real execution date.

---

# 56. No commit during Stage 9

Do not commit the Stage 9 changes.

The operator will review the final report and then authorize the Phase 2 closure commit.

Do not push.

---

# 57. Expected final commit later

Do not execute this, but the operator may later choose a commit such as:

```text
docs: close Phase 2 multi-source ingestion
```

or another appropriate message after reviewing Stage 9.

This prompt does not authorize that commit.

---

# 58. Final response requirements

Return a concise engineering summary containing:

1. branch;
2. baseline HEAD;
3. initial clean-state confirmation;
4. files changed;
5. production code changed, if any;
6. final provider/product matrix;
7. final version inventory;
8. Stage 8 acceptance confirmation;
9. REN limitation classification;
10. ESIOS final classification;
11. forecast-vintage limitation classification;
12. live evidence/provenance status;
13. network-denied replay status;
14. final 44-criterion totals:
    - SATISFIED
    - SATISFIED WITH DOCUMENTED LIMITATION
    - NOT SATISFIED;
15. any criterion requiring special reasoning;
16. Stage 6 regression result;
17. Stage 7 security result;
18. Stage 8 offline regression result;
19. provider-focused regression result;
20. full pytest result;
21. Ruff result;
22. format result;
23. mypy result;
24. pre-commit result;
25. `git diff --check` result;
26. `.env` ignore/untracked verification;
27. secret/live-payload hygiene result;
28. documentation consistency result;
29. remaining accepted limitations;
30. Phase 3 handoff statement;
31. exact final Git status;
32. confirmation:
    - no provider request;
    - no credential probe;
    - no cloud action;
    - no branch;
    - no staging;
    - no commit;
    - no push;
    - no Phase 3 implementation.

---

# 59. Successful final wording

If every Phase 2 acceptance requirement is satisfied, finish exactly with:

```text
Phase 2 Stage 9 — PASS.

Phase 2 — Multi-Source Ingestion Expansion — CLOSED.

The final 44-criterion acceptance reconciliation is complete.
All mandatory Phase 2 ingestion, normalization, provenance,
replay, boundedness, security, cross-source and controlled-live
validation requirements are satisfied, with retained limitations
documented explicitly and without overstating provider guarantees.

REN, ESIOS 544, ENTSO-E ES load, ENTSO-E PT/ES renewable
forecasts, Open-Meteo ERA5 and Open-Meteo ICON-EU are accepted
under their final versioned profiles.

Phase 1 OMIE compatibility remains intact.

Real live provider evidence remains outside Git, while immutable
checksums, safe provenance and network-denied replay evidence are
documented.

No Snowflake, dbt, feature engineering, ML training, serving,
deployment or other later-phase implementation entered Phase 2.

Phase 3 has not been started or authorized.
```

---

# 60. Gap wording

If Phase 2 cannot truthfully close, finish exactly with:

```text
Phase 2 Stage 9 — PASS WITH GAPS.

Phase 2 remains open.
```

Then list each unresolved mandatory acceptance criterion with the exact blocker.

Do not begin Phase 3.

Stop there.
