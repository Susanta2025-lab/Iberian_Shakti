Continue the existing **Phase 2 Stage 9 final-acceptance task** from the current repository and working-tree state.

The operator has now made an explicit final acceptance-policy decision for the remaining REN criterion-4 gap.

## Operator authorization

The operator explicitly authorizes the following Phase 2 acceptance policy:

> REN timestamp-support and DST-fold semantics remain provisional.
> For Phase 2, the existing versioned REN `0.2.0` profile is accepted as sufficient engineering semantics despite the absence of provider-authoritative proof of label placement and autumn repeated-hour value-to-fold ownership.

This authorization is intentional.

Do **not** interpret it as new provider evidence.

Do **not** claim that REN officially defines the timestamps as interval starts or that its autumn fold ordering has been proven.

The accepted distinction is:

```text
provider semantics:
not fully established

project implementation semantics:
explicit, deterministic and provisional

Phase 2 acceptance:
authorized
```

---

# 1. Preserve the current implementation

Keep the existing REN profile unchanged:

```text
profile/parser:
0.2.0

timezone:
Europe/Lisbon

cadence:
15 minutes

support convention:
interval_start

statistic:
provider_period_value

semantic evidence:
provisional_empirical
```

Do not change:

```text
parser behavior
profile version
fold assignment
measurement values
record schema
query identity
archive history
replay semantics
```

No new REN live request is authorized or needed.

---

# 2. Preserve the evidence distinction

The final documentation must state clearly that:

```text
92 / 96 / 100 period handling
```

is deterministic and permanently tested, including:

```text
ordinary day
spring DST
autumn DST
unsupported layouts
```

but:

```text
physical value-to-fold ownership
provider-authoritative interval-edge semantics
```

remain externally unconfirmed.

This is an accepted project limitation.

Do not convert:

```text
provisional_empirical
```

into:

```text
authoritative
```

or equivalent wording.

---

# 3. Record the operator-level acceptance decision durably

Create a focused successor ADR, unless repository conventions strongly indicate another durable acceptance-policy document is more appropriate.

Preferred new ADR:

```text
docs/adr/0009-ren-provisional-semantics-phase2-acceptance.md
```

Suggested decision:

```text
Phase 2 accepts REN profile/parser 0.2.0 as the operational
contract despite unresolved provider-authoritative timestamp
placement and autumn fold ownership.

The semantics remain explicitly provisional_empirical.

This decision is a project acceptance-policy decision, not a
claim about undocumented REN provider semantics.

Future authoritative clarification may justify a new versioned
profile, but does not invalidate retained 0.2.0 raw/provenance
history.
```

Update the ADR index accordingly.

Preserve ADR 0006 and all previous historical reasoning.

Do not rewrite earlier reports to pretend criterion 4 was previously satisfied.

---

# 4. Update criterion 4 final classification

The original criterion text must remain verbatim:

```text
REN's timezone and timestamp support convention are established
by concrete official/profile evidence; ordinary and both DST
profiles normalize without guessed folds or fabricated averaging
intervals. Unsupported profiles fail visibly.
```

Document explicitly that the previously unresolved stronger evidence requirement has now been **superseded for final Phase 2 acceptance by explicit operator decision**.

Reclassify criterion 4 as:

```text
SATISFIED WITH DOCUMENTED LIMITATION
```

with language equivalent to:

```text
The implementation portion is satisfied: the explicit versioned
profile normalizes ordinary, spring and autumn physical-day
shapes deterministically, rejects unsupported layouts and does
not fabricate averaging semantics.

Provider-authoritative interval-edge and autumn value-to-fold
semantics remain unconfirmed.

The operator explicitly accepts those semantics as provisional
for Phase 2 closure. This is an acceptance-policy replacement,
not new evidence about REN.
```

Do not classify it simply as `SATISFIED`.

---

# 5. Final 44-criterion totals

Assuming no other issue is discovered, revise the final totals to:

```text
42 SATISFIED

2 SATISFIED WITH DOCUMENTED LIMITATION

0 NOT SATISFIED
```

The two documented limitations are:

```text
criterion 4 — REN provisional timestamp/fold semantics

criterion 5 — ESIOS native unit-field limitation
```

Do not modify unrelated classifications.

---

# 6. Update the final acceptance report

Update:

```text
docs/codex/reports/phase_2_final_acceptance_report.md
```

Preserve the existing Stage 9 PASS WITH GAPS and targeted REN investigation as historical evidence.

Append a clearly separated section such as:

```text
Operator acceptance-policy resolution for REN criterion 4
```

Record:

```text
- previous NOT SATISFIED status
- evidence search result
- why stronger evidence remained unavailable
- explicit operator authorization
- exact provisional semantics accepted
- confirmation that no provider claim was strengthened
- criterion 4 revised classification
- revised 44-criterion totals
- final Phase 2 closure decision
```

Do not delete the previous failed-resolution reasoning.

---

# 7. Update current project-status documentation

Update current status in:

```text
README.md
docs/architecture/README.md
docs/runbooks/README.md
docs/runbooks/ingestion.md
```

from:

```text
Phase 2 OPEN / PASS WITH GAPS
```

to:

```text
Phase 2 CLOSED / PASS
```

while retaining the REN limitation prominently enough that future feature engineering cannot mistake the timestamp convention for authoritative provider semantics.

Use closure date:

```text
2026-11-03
```

if that remains the actual execution date.

---

# 8. Future handling of REN

Document that future authoritative REN evidence may lead to:

```text
a new profile/parser version
```

if it contradicts or refines `0.2.0`.

Do not silently alter historical `0.2.0`.

Existing:

```text
raw bytes
retrieval provenance
parse provenance
replay evidence
```

remain immutable.

A future semantic correction must be versioned.

---

# 9. No production-code change expected

This acceptance-policy continuation should normally require:

```text
ADR/documentation/report changes only
```

The permanent REN ambiguity regression already demonstrates why the external ambiguity cannot be solved from label order alone.

Do not change production code unless a genuine independent defect is found during final review.

Do not make any provider request.

---

# 10. Final validation

Run fresh:

```bash
python -m pytest tests/unit/ingestion/ren -q
python -m pytest tests/integration/test_ren_flow.py -q
python -m pytest tests/integration/stage6 -q
```

Run the established Stage 7 security selection.

Run:

```bash
python -m pytest \
  tests/integration/test_phase2_stage8_live.py \
  tests/integration/test_esios_boundary_semantics.py -q
```

Run provider-focused regression.

Then:

```bash
env -u ESIOS_API_TOKEN -u ENTSOE_API_TOKEN python -m pytest

ruff check .
ruff format --check .
mypy src
pre-commit run --all-files
git diff --check
```

No test may make live requests.

---

# 11. Hygiene

Verify:

```text
.env ignored
.env untracked
no credential read
no real live payload in Git
no temporary research file in Git
no live archive copied into repository
```

Do not access credential values.

---

# 12. Git restrictions

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

Leave the completed Phase 2 closure tree unstaged for operator review.

---

# 13. Final acceptance condition

If all existing criteria remain accepted, criterion 4 is reclassified according to the operator-approved provisional policy, and all fresh gates pass, conclude:

```text
Phase 2 Stage 9 — PASS.

Phase 2 — Multi-Source Ingestion Expansion — CLOSED.
```

Do not start Phase 3.

---

# 14. Final response

Report concisely:

1. baseline HEAD;
2. operator acceptance-policy decision recorded;
3. new ADR path;
4. REN profile unchanged;
5. REN semantics still `provisional_empirical`;
6. no new provider request;
7. criterion 4 revised classification;
8. criterion 5 unchanged classification;
9. final 44-criterion totals;
10. REN focused tests;
11. Stage 6 result;
12. Stage 7 result;
13. Stage 8 result;
14. provider-focused result;
15. full pytest;
16. Ruff;
17. format;
18. mypy;
19. pre-commit;
20. `git diff --check`;
21. documentation status;
22. exact Git status;
23. confirmation no staging/commit/push;
24. confirmation Phase 3 was not started.

Finish exactly with:

```text
Phase 2 Stage 9 — PASS.

Phase 2 — Multi-Source Ingestion Expansion — CLOSED.

Final acceptance reconciles all 44 criteria:
42 SATISFIED,
2 SATISFIED WITH DOCUMENTED LIMITATION,
0 NOT SATISFIED.

REN profile/parser 0.2.0 remains explicitly
provisional_empirical. Provider-authoritative timestamp-edge and
autumn value-to-fold semantics are not claimed established; the
operator has explicitly accepted this limitation for Phase 2.

ESIOS retains its documented native-unit-field limitation.

No provider semantics were fabricated, no historical evidence was
rewritten, and no new live request was required.

No Phase 3 implementation has been started or authorized.
```

Stop there.
