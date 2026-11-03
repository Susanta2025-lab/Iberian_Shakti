# Iberian_Shakti — Phase 2 Final Acceptance Continuation
## Targeted REN Criterion 4 Resolution

Continue the existing **Phase 2 final-acceptance work** from the current repository state.

This is **not a new phase or stage**.

It is a narrowly scoped attempt to resolve the **single remaining mandatory Phase 2 acceptance gap: criterion 4 for REN**.

Do not reopen any other Phase 2 provider, criterion, architecture decision, source selection, or live-validation result.

---

# 1. Current authoritative status

The committed baseline entering Stage 9 was:

```text
branch:
main

HEAD:
e3753ca feat: complete Phase 2 controlled live validation
```

Stage 9 work currently exists as an **unstaged working tree**.

The Stage 9 acceptance report currently concludes:

```text
Phase 2 Stage 9 — PASS WITH GAPS.

Phase 2 remains open.
```

The final 44-criterion reconciliation is currently:

```text
42 SATISFIED
1 SATISFIED WITH DOCUMENTED LIMITATION
1 NOT SATISFIED
```

The only `NOT SATISFIED` criterion is:

```text
criterion 4 — REN timestamp/timezone support semantics
```

Preserve all existing Stage 9 work.

Do not require a clean working tree.

---

# 2. Exact criterion to resolve

The original mandatory criterion is:

```text
REN's timezone and timestamp support convention are established
by concrete official/profile evidence; ordinary and both DST
profiles normalize without guessed folds or fabricated averaging
intervals. Unsupported profiles fail visibly.
```

Do not weaken, rewrite, replace, or reinterpret this criterion merely to obtain closure.

The task is to determine whether the existing REN implementation can now satisfy it with defensible evidence.

---

# 3. Current accepted REN engineering state

The accepted REN implementation is:

```text
profile/parser:
0.2.0

timezone:
Europe/Lisbon

source cadence:
15 minutes

timestamp interpretation:
interval_start

statistic:
provider_period_value

semantic evidence:
provisional_empirical
```

Accepted daily profile counts:

```text
ordinary:
96 source labels

spring DST:
92 source labels

autumn DST:
100 source labels
```

Selected concepts:

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

Ancillary series remain validated but unselected where already documented.

Do not change these product selections.

---

# 4. Existing accepted limitation

ADR 0006 and the revised Stage 2 acceptance intentionally avoided claiming:

```text
mean MW
instantaneous MW
energy-over-period MW
```

Instead they use:

```text
Statistic.PROVIDER_PERIOD_VALUE
```

That issue is **not the remaining blocker**.

Do not reopen arithmetic-statistic semantics unless new evidence directly requires it.

The unresolved issue is specifically:

```text
what support each REN time label denotes
```

and especially:

```text
which repeated autumn local-time block owns which values
```

---

# 5. What Stage 9 determined

Stage 9 concluded that existing evidence establishes:

```text
- real REN endpoint compatibility
- exact ordinary-day 96-label behavior
- synthetic 92/96/100 normalization
- Europe/Lisbon timezone policy
- deterministic parser execution
- unsupported-profile failure
- immutable raw/provenance/replay behavior
```

but does **not** establish:

```text
- provider-authoritative label-placement semantics
- physical value-to-fold ownership during autumn fallback
```

Synthetic UTC stepping proves our implementation follows the selected policy.

It does **not** prove the provider's real-world timestamp semantics.

Do not confuse implementation consistency with provider-semantic evidence.

---

# 6. Working-tree rules

Begin with:

```bash
git status --short
git diff --stat
git diff --check
git log --oneline --decorate -15
```

Preserve all current Stage 9 files and modifications.

Do not:

```text
branch
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

Do not erase or overwrite Stage 9 report history.

---

# 7. Save this prompt first

Save this exact prompt as:

```text
docs/codex/prompts/phase_2/
phase_2_ren_criterion_4_resolution.md
```

Do not replace the Stage 9 prompt.

---

# 8. Primary task objective

Determine whether criterion 4 can be satisfied using:

```text
A. existing authoritative/profile evidence already present in the repository

B. additional official/public REN documentation or metadata

C. existing archived/live REN evidence

D. at most one narrowly controlled autumn-DST REN acquisition,
   only if it can materially distinguish the competing interpretations
```

The order above is mandatory.

Do not begin with another live request.

---

# 9. First phase: repository evidence review

Read at minimum:

```text
docs/codex/reports/phase_2_readiness_assessment.md

docs/codex/reports/phase_2_stage_2_ren_report.md

docs/codex/reports/phase_2_stage_7_pre_live_engineering_audit_report.md

docs/codex/reports/phase_2_stage_8_controlled_live_validation_report.md

docs/codex/reports/phase_2_final_acceptance_report.md

docs/adr/0006-ren-provisional-period-semantics.md

all preceding REN ADR/history relevant to the superseded time gate

src/iberian_shakti/ingestion/ren/profile.py
src/iberian_shakti/ingestion/ren/parser.py
src/iberian_shakti/ingestion/ren/schema.py
src/iberian_shakti/ingestion/ren/adapter.py

all REN unit/integration/time/DST tests
```

Reconstruct exactly:

```text
what is known
what is inferred
what is synthetic
what is provider-observed
what remains unresolved
```

---

# 10. Identify the competing timestamp interpretations

Write down the actual competing interpretations before searching for evidence.

At minimum distinguish:

```text
A. label is interval start in Europe/Lisbon

B. label is interval end in Europe/Lisbon

C. label is a provider period identifier whose placement cannot
   safely be mapped to start/end

D. repeated autumn labels correspond to explicitly ordered folds

E. repeated autumn labels are presentation labels without enough
   information to establish physical fold ownership
```

Do not assume A merely because it is our current provisional profile.

---

# 11. Official REN evidence search

Search only for evidence relevant to the selected endpoint:

```text
ElectricityProductionBreakdownDaily
```

and the REN source/page/API documentation that governs its chart data.

Look for explicit wording concerning:

```text
15-minute period

timestamp/time-label meaning

quarter-hour interval

start/end of interval

Europe/Lisbon / Portuguese local time

summer/winter time

DST transition

repeated hour

25-hour day

23-hour day

hour numbering

fold/order convention

data publication methodology

generation/load measurement period
```

Prefer:

```text
REN official API/documentation
REN official methodology/data dictionary
REN official technical documentation
REN official portal metadata
REN official downloadable specification
```

Do not treat third-party commentary as authoritative evidence.

Third-party material may be used only as secondary corroboration and must be labelled as such.

---

# 12. Evidence classification

For every potentially relevant source, classify it as:

```text
AUTHORITATIVE DIRECT

AUTHORITATIVE INDIRECT

EMPIRICAL PROVIDER OBSERVATION

IMPLEMENTATION POLICY

INFERENCE

INSUFFICIENT
```

Do not promote indirect evidence to direct evidence.

For example:

```text
"data are in 15-minute periods"
```

does not automatically establish:

```text
"the displayed timestamp is the interval start"
```

Likewise:

```text
100 values on an autumn day
```

does not alone establish which repeated value belongs to fold 0 versus fold 1.

---

# 13. Profile evidence may satisfy the criterion only if independently grounded

The criterion permits:

```text
official/profile evidence
```

but a profile that merely records our provisional assumption is not independent evidence.

Determine whether the REN profile is grounded in another concrete provider convention that can establish:

```text
timezone

support placement

fold ordering
```

If not, do not count the profile itself as proof.

---

# 14. Existing live REN evidence

Inspect the existing Stage 8 REN result without modifying its archive.

The accepted Stage 8 REN response was:

```text
target source day:
2026-10-24

HTTP:
200

raw bytes:
28,420

records:
1,056

labels:
96 quarter-hour labels
00:00 through 23:45

profile/parser:
0.2.0
```

This ordinary day supports ordinary compatibility.

It does not exercise either DST transition.

Do not overclaim it.

---

# 15. Existing historical / experimental evidence

Review all prior REN timing experiments and evidence retained in Stage 2.

Explicitly determine whether any earlier source already contains:

```text
an actual spring DST REN day

an actual autumn DST REN day

offset-bearing timestamps

duplicate local-hour sequence

a provider-defined period index

a separate UTC field

a publication or archive that disambiguates repeated local labels
```

If such evidence already exists, use it before considering another live call.

---

# 16. Define what evidence would actually resolve autumn fold ownership

Before authorizing any request, state exactly what observation would distinguish the alternatives.

A live request is useful only if the response exposes enough information to infer fold ownership.

Examples of potentially useful evidence:

```text
explicit UTC timestamps

explicit numeric period indices preserving a unique repeated-hour order

offset-bearing timestamps

documented repeated-hour numbering

two distinct repeated local blocks whose order is independently specified
```

Examples that are **not sufficient alone**:

```text
100 values

duplicate 02:00 labels

an ordered JSON array with no provider rule explaining what that order means

our own parser assigning fold 0/fold 1

matching expected record count
```

Do not make a live request if the response schema cannot materially improve the evidence.

---

# 17. Preferred resolution path

Preferred resolution hierarchy:

```text
1. authoritative REN documentation explicitly settles support/fold semantics

2. authoritative REN documentation + provider-observed DST response together
   settle the semantics

3. independently grounded provider profile/period numbering + DST response
   settles the semantics

4. otherwise criterion 4 remains NOT SATISFIED
```

Do not invent a fifth path based solely on convenience.

---

# 18. Controlled live authorization

This prompt authorizes **at most one additional REN logical data request**.

It may be executed only if all of the following are true:

```text
offline/documentation review is complete

the response can materially test a precise hypothesis

a specific historical DST date is selected for semantic reasons

the request uses the existing production REN path

no credential is required

the request remains bounded by existing Stage 8 safety controls
```

No date search.

No multiple dates.

No repeated call after an inconclusive result.

No catalogue enumeration.

No bulk history.

---

# 19. Which DST date to choose

If a live request is justified, choose **one autumn DST fallback day** in Europe/Lisbon.

Prefer a recent completed historical day whose transition is unambiguous from the IANA timezone database and which the provider should reasonably retain.

Before network access:

```text
derive the exact Lisbon UTC transition locally

derive the expected 100 quarter-hour physical intervals

derive both folds explicitly

record the expected UTC support sequence
```

Do not use fixed CET/WET arithmetic.

Use `zoneinfo` / Europe/Lisbon semantics.

---

# 20. No spring request by default

Do not request both spring and autumn days.

Criterion 4 requires ordinary and both DST profiles to normalize, but:

```text
ordinary:
already covered by real Stage 8 + tests

spring:
can remain deterministic normalization evidence if the provider
documentation settles support convention

autumn:
is the unresolved fold-ownership problem
```

A spring live request is not authorized by this prompt.

---

# 21. Live request safety

If the one REN request is executed:

```text
provider:
REN only

logical requests:
1 maximum

sequential:
yes

retries:
existing bounded production policy only

archive:
new dedicated external live archive

credentials:
none

other providers:
0 requests
```

Do not reuse or overwrite the existing Stage 8 archive.

Do not put live bytes into Git.

---

# 22. Preserve raw evidence

The additional REN acquisition, if any, must use:

```text
existing HttpRetriever
existing immutable LocalRawArchive
existing retrieval provenance
existing REN parser
existing parse provenance
```

Do not create a manual curl-only evidence path.

If experimental local inspection is needed after archival, inspect the immutable archived body.

---

# 23. Do not change the parser before evidence

Do not modify:

```text
REN timestamp semantics
fold assignment
profile version
parser version
```

before the evidence review is complete.

The current `0.2.0` behavior remains the accepted provisional implementation.

First determine whether its semantics are actually supported.

---

# 24. Resolution A — current 0.2.0 semantics proven

If authoritative/provider evidence establishes that:

```text
Europe/Lisbon labels are interval starts
```

and establishes a deterministic repeated-hour ordering/fold ownership compatible with current 0.2.0:

then:

```text
retain profile/parser 0.2.0 if no semantic change is required

upgrade the evidence status from provisional_empirical only if justified

add permanent tests encoding the newly grounded rule

update ADR 0006 or add a narrowly scoped successor ADR only if
the durable semantic decision materially changes its evidence status

update the final acceptance report
```

Do not create a version bump merely for documentation if wire/semantic behavior is unchanged.

---

# 25. Resolution B — semantics proven but differ from 0.2.0

If authoritative evidence proves a different support/fold rule:

```text
do not mutate 0.2.0 silently
```

Create a new versioned REN profile/parser only if necessary.

Preserve historical:

```text
0.2.0 raw acquisitions
0.2.0 parse events
Stage 2 acceptance history
Stage 8 ordinary-day evidence
```

Add:

```text
new profile version
new parser version
new tests
new parse provenance
```

where justified.

Do not rewrite old evidence.

If live confirmation of the new behavior would be required but the one authorized request has already been consumed inconclusively:

```text
Phase 2 remains open
```

Do not make another request.

---

# 26. Resolution C — evidence remains insufficient

If documentation and the single optional DST observation still cannot establish value-to-fold ownership:

```text
criterion 4 remains NOT SATISFIED
```

Do not:

```text
guess fold order
use our own array order as provider proof
downgrade the criterion
declare Phase 2 closed
```

Update the report with the stronger evidence search and exact remaining blocker.

---

# 27. Unsupported-profile behavior

Regardless of outcome, verify that unsupported REN profile shapes fail visibly.

Retain or strengthen tests for:

```text
unexpected label count

wrong cadence

duplicate/unexpected label sequence

invalid local time

unsupported DST layout

missing required selected concepts

misordered source labels
```

Do not add silent normalization.

---

# 28. Ordinary / spring / autumn regression matrix

The final REN time test matrix must explicitly cover:

```text
ordinary:
96 quarter-hour intervals

spring:
92 quarter-hour intervals

autumn:
100 quarter-hour intervals
```

For each, verify:

```text
UTC-aware normalized support

positive half-open intervals

exact 15-minute duration

no fabricated averaging interval

no missing physical interval

no duplicate physical UTC support

deterministic local/UTC mapping

visible failure on unsupported shape
```

If fold ownership is proven, verify it explicitly.

If not proven, tests must not pretend it is.

---

# 29. Statistic semantics stay conservative

Do not replace:

```text
provider_period_value
```

with:

```text
mean
instantaneous
energy
```

unless the same evidence explicitly establishes it.

Criterion 4 can be resolved without solving arithmetic measurement semantics if interval support is independently established.

---

# 30. Final acceptance report update

Update:

```text
docs/codex/reports/
phase_2_final_acceptance_report.md
```

Do not erase the original Stage 9 PASS WITH GAPS reasoning.

Add a clearly separated section:

```text
Targeted REN criterion-4 resolution
```

Record:

```text
existing evidence reviewed

official REN sources inspected

evidence classification

competing interpretations

whether a live request was necessary

exact request date if used

response structure relevant to semantics

raw hash / provenance if used

whether fold ownership became established

production changes if any

tests added

final criterion-4 classification

revised 44-criterion totals

revised Phase 2 verdict
```

---

# 31. Update criterion 4 only if justified

If resolved, change criterion 4 from:

```text
NOT SATISFIED
```

to:

```text
SATISFIED
```

or:

```text
SATISFIED WITH DOCUMENTED LIMITATION
```

only if the exact wording supports that classification.

Do not change unrelated criterion classifications without discovering a genuine error.

---

# 32. Phase 2 closure condition

Phase 2 may become:

```text
Phase 2 — CLOSED.
```

only if after this task:

```text
criterion 4 is no longer NOT SATISFIED

criterion 5 remains defensibly accepted with its documented limitation

all other 42 satisfied criteria remain intact

all final regression/quality gates pass
```

---

# 33. README / architecture status

If criterion 4 is resolved and Phase 2 closes:

update current Phase 2 status in:

```text
README.md
docs/architecture/README.md
docs/runbooks/README.md
docs/runbooks/ingestion.md
```

from:

```text
OPEN / PASS WITH GAPS
```

to:

```text
CLOSED / PASS
```

Do not rewrite historical Stage 2/7/8 reports.

If criterion 4 remains unresolved, retain Phase 2 open status.

---

# 34. ADR handling

Do not automatically create a new ADR.

Use:

```text
ADR 0006 update
```

only if it is appropriate to append/clarify evidence without falsifying history.

Prefer a successor ADR if:

```text
the actual semantic contract changes
the profile version changes
the provisional interpretation is superseded
```

Historical wording must remain understandable.

Do not erase the fact that earlier evidence was provisional.

---

# 35. No other provider changes

Do not modify semantics or code for:

```text
OMIE
ESIOS
ENTSO-E
Open-Meteo
```

Do not make any requests to them.

Do not reopen Stage 9's ENTSO-E 429 correction.

---

# 36. No Phase 3

Do not implement:

```text
Snowflake
dbt
feature engineering
model training
model registry
batch inference
API/dashboard
deployment
```

No paid cloud action.

---

# 37. Fresh validation after any change

Run:

```bash
python -m pytest tests/unit/ingestion/ren -q
```

plus the established REN integration tests.

Then rerun:

```bash
python -m pytest tests/integration/stage6 -q
```

Run the established Stage 7 security selection.

Run:

```bash
python -m pytest \
  tests/integration/test_phase2_stage8_live.py \
  tests/integration/test_esios_boundary_semantics.py -q
```

Then provider-focused regression.

Finally:

```bash
env -u ESIOS_API_TOKEN -u ENTSOE_API_TOKEN python -m pytest

ruff check .
ruff format --check .
mypy src
pre-commit run --all-files
git diff --check
```

No test may make a live request.

---

# 38. Secret and live-evidence hygiene

Confirm:

```text
.env remains ignored
.env remains untracked
.env is not opened
no credential is read
no live raw payload enters Git
no temporary analysis dump enters Git
```

REN requires no credential.

---

# 39. Final Git review

Run:

```bash
git status --short
git diff --stat
git diff
git diff --cached
```

Explicitly inspect all untracked files because normal `git diff` omits them.

Do not stage or commit.

---

# 40. Final response requirements

Return a concise but complete engineering summary containing:

1. branch;
2. baseline committed HEAD;
3. existing Stage 9 dirty tree preserved;
4. exact criterion 4;
5. existing REN evidence reviewed;
6. official REN sources inspected;
7. authoritative evidence found;
8. competing interpretations considered;
9. whether one live request was necessary;
10. if executed:
    - date;
    - logical request count;
    - attempts;
    - bytes;
    - SHA-256;
    - label count;
    - relevant DST label structure;
    - parse result;
    - replay result;
11. whether interval-start semantics are now established;
12. whether autumn fold ownership is now established;
13. statistic semantics status;
14. profile/parser version decision;
15. code changes;
16. ADR changes;
17. tests added/changed;
18. REN focused test result;
19. Stage 6 result;
20. Stage 7 security result;
21. Stage 8 regression result;
22. provider-focused result;
23. full pytest result;
24. Ruff;
25. format;
26. mypy;
27. pre-commit;
28. git diff --check;
29. final criterion 4 classification;
30. revised 44-criterion totals;
31. final Phase 2 verdict;
32. exact Git status;
33. confirmation of no branch/stage/commit/push;
34. confirmation no Phase 3 work occurred.

---

# 41. Successful resolution wording

If criterion 4 is genuinely resolved and no mandatory criterion remains unsatisfied, finish exactly:

```text
REN criterion 4 — SATISFIED.

The REN timezone, timestamp-support and autumn-fold convention
are now established by concrete evidence sufficient for the
accepted profile. Ordinary, spring-DST and autumn-DST profiles
normalize without guessed folds or fabricated averaging
intervals, and unsupported profiles fail visibly.

Phase 2 Stage 9 — PASS.

Phase 2 — Multi-Source Ingestion Expansion — CLOSED.

All 44 final acceptance criteria are now reconciled with no
mandatory criterion remaining unsatisfied.

No Phase 3 implementation has been started or authorized.
```

---

# 42. Unresolved wording

If the evidence remains insufficient, finish exactly:

```text
REN criterion 4 — NOT SATISFIED.

The remaining ambiguity concerns provider-authoritative
timestamp support and/or autumn repeated-hour value-to-fold
ownership. The available evidence is insufficient to replace
that ambiguity with a non-guessed semantic contract.

No speculative fold assignment or acceptance-policy weakening
was introduced.

Phase 2 Stage 9 — PASS WITH GAPS.

Phase 2 remains open.

No Phase 3 implementation has been started or authorized.
```

Stop there.
