# Iberian_Shakti — Phase 2 Stage 2
## REN Electricity Production / Consumption Integration

You are working in the existing **Iberian_Shakti** repository on `main`.

Phase 0 and Phase 1 are:

```text
Phase 0 — CLOSED/PASS
Phase 1 — CLOSED/PASS
```

Phase 2 is:

```text
Multi-Source Ingestion Expansion — IN PROGRESS
```

The authoritative Phase 2 readiness assessment is:

```text
docs/codex/reports/phase_2_readiness_assessment.md
```

Phase 2 Stage 1 has been completed and accepted as:

```text
PASS
```

Its report is:

```text
docs/codex/reports/phase_2_stage_1_report.md
```

Stage 1 established:

- ADR 0003 — multi-source query and measurement contracts;
- ADR 0004 — private authentication and semantic provider outcomes;
- `ApiSourceRequest`;
- typed geography/query contracts;
- `SystemMeasurement`;
- `WeatherMeasurement`;
- schema-family versioning;
- API snapshot semantics;
- shared API provenance;
- private fixed-origin request/authentication boundary;
- semantic provider outcomes;
- backward-compatible Phase 1 archive/replay;
- repository-wide offline test enforcement.

This task is **Phase 2 Stage 2 only: REN integration**.

Do not begin ESIOS, ENTSO-E or Open-Meteo implementation.

---

# 0. Preconditions

Before making any change, inspect:

```bash
git status
git log --oneline --decorate -15
```

Stage 1 must already be committed by the operator and the working tree should be clean.

Do not assume a particular Stage 1 commit hash.

Record the actual Stage 2 baseline in the report.

Read completely:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md
docs/codex/reports/phase_2_stage_1_report.md

docs/adr/0001-*
docs/adr/0002-*
docs/adr/0003-*
docs/adr/0004-*

docs/runbooks/ingestion.md

src/iberian_shakti/contracts/
src/iberian_shakti/ingestion/
src/iberian_shakti/ingestion/ren/

tests/contracts/
tests/unit/ingestion/
tests/integration/
tests/data/
```

Trace the actual Stage 1 contracts and API execution path before implementing REN.

Do not duplicate existing shared functionality.

---

# 1. Store this Stage 2 prompt first

The permanent Phase 2 prompt-history directory already exists:

```text
docs/codex/prompts/phase_2/
```

Before implementation, store the **complete operator-supplied Stage 2 prompt** as:

```text
docs/codex/prompts/phase_2/phase_2_stage_2_ren_integration.md
```

Preserve the substantive prompt exactly.

Do not replace it with a summary.

Do not modify the Stage 1 historical prompt.

---

# 2. Authoritative REN scope

Implement exactly the mandatory REN product selected by the Phase 2 readiness assessment:

```text
ElectricityProductionBreakdownDaily
```

Official source family:

```text
REN DataHub electricity API
```

Expected fixed origin:

```text
https://servicebus.ren.pt
```

Expected documented path:

```text
/datahubapi/electricity/ElectricityProductionBreakdownDaily
```

Expected public query parameters:

```text
culture=en-US
date=YYYY-MM-DD
```

Verify current implementation assumptions against the authoritative readiness report and any official REN documentation used during this stage.

Do not introduce arbitrary user-controlled URLs.

---

# 3. Selected REN series

The mandatory selected series are:

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

These must be explicitly mapped.

Interpretation:

```text
Consumption
→ actual load/system consumption

Wind
Solar
Hydro
Natural Gas
Biomass
Other Thermal
Coal
Wave
→ actual generation by technology

Import
Export
→ actual aggregate external interchange
```

Do not create derived totals.

Do not calculate renewable shares.

Do not combine series.

Do not double-count consumption or generation.

---

# 4. Explicitly unselected REN series

The readiness assessment identified ancillary/unselected concepts such as:

```text
Pumping
Batteries
Consumption + Storage
```

and possibly other presentation/source series.

Create an explicit selection policy.

Known intentionally unselected series may be recognized and ignored **only because the source profile explicitly classifies them as unselected**.

Do not silently discard unknown new series.

An unknown source concept must cause a controlled profile/schema failure until deliberately reviewed and mapped or classified as unselected.

This prevents silent provider-schema drift.

---

# 5. No second REN product

Do NOT implement normal ingestion of:

```text
ElectricityConsumptionSupplyDaily
```

Stage 2 uses the selected production-breakdown response because it already contains the mandatory load/generation/import/export context.

Do not perform a second aggregate download during ordinary REN ingestion.

Do not implement homepage scraping.

Do not implement undocumented REN forecast routes.

---

# 6. REN adapter architecture

Implement REN using the Stage 1 shared API architecture.

The intended path is conceptually:

```text
REN SourceRequest / ApiSourceRequest
        ↓
REN adapter / source profile
        ↓
ResolvedSource.for_api(...)
        ↓
fixed-origin anonymous request policy
        ↓
shared HttpRetriever
        ↓
immutable raw archive
        ↓
retrieval provenance
        ↓
strict REN parser
        ↓
SystemMeasurement records
        ↓
measurement parse provenance
        ↓
offline replay
```

Reuse:

- `ApiSourceRequest`;
- shared query identity;
- `ResolvedSource.for_api`;
- existing HTTP retrieval;
- existing retries/time budgets;
- immutable archive;
- provenance;
- semantic outcomes;
- shared runner;
- replay.

Do not create a separate REN HTTP client framework.

---

# 7. Authentication

REN's selected mechanism is anonymous.

Do not add:

```text
REN_API_TOKEN
REN_API_KEY
```

or any other invented credential.

REN must remain usable without ESIOS or ENTSO-E credentials.

Do not read unrelated secret environment variables.

---

# 8. Source identity and query identity

Define stable REN identities following repository conventions.

At minimum distinguish:

```text
source = REN
product/report = ElectricityProductionBreakdownDaily
source day
query window
culture
selected source profile/version
```

Persist only safe query information.

Do not persist arbitrary full transport URLs if existing safe identity mechanisms already cover the request.

The query identity must not depend on retrieval time.

Repeated acquisition of the same query remains a distinct retrieval event even when raw content is identical.

---

# 9. REN source-day semantics

This is the most important unresolved Stage 2 semantic issue.

The readiness assessment observed a REN autumn-DST response containing:

```text
100 quarter-hour labels
00:00 ... 23:45
repeated 01:00 ... 01:45
```

This is consistent with Europe/Lisbon autumn DST behavior, but the readiness assessment explicitly did **not** treat that observation alone as contractual proof of:

- timezone;
- interval-start semantics;
- interval-end semantics;
- instant/sample semantics;
- averaging semantics.

Stage 2 must resolve the concrete supported REN time profile before claiming normalized UTC success.

---

# 10. Time-semantics evidence requirement

Use evidence in this preference order:

1. current official REN documentation explicitly defining time labels;
2. official REN API/source metadata;
3. official independently timestamped/exported REN material;
4. bounded direct provider observations across ordinary/DST profiles where needed to corroborate documented semantics.

Do not infer semantics merely because values appear every 15 minutes.

Do not assume REN uses Europe/Madrid.

Do not copy OMIE's calendar policy.

Portugal electricity-system REN data must have its own source profile.

---

# 11. Minimal external verification allowed

Stage 2 is primarily an implementation stage, not final live validation.

However, the authoritative assessment requires the REN time profile to be resolved here.

Therefore limited external verification is allowed **only when necessary to establish the source profile**.

Allowed:

- official REN documentation lookup;
- official REN API documentation;
- minimal bounded read-only requests to the selected public product;
- a small number of specifically chosen ordinary/spring/autumn dates if necessary to establish the supported profile.

Not allowed:

- bulk history;
- crawling;
- polling;
- load testing;
- broad endpoint discovery;
- repeated retries outside application policy;
- ESIOS/ENTSO-E/Open-Meteo access;
- production live-smoke acceptance claims.

Any direct REN observation during this implementation stage is:

```text
source-profile evidence
```

not:

```text
Phase 2 Stage 8 controlled live validation
```

Do not count it toward final Phase 2 live acceptance criterion 39.

---

# 12. Stop rather than guess

If sufficient evidence cannot establish the timestamp convention needed to emit authoritative normalized UTC records:

do not guess.

Instead:

- archive/retain safe test bytes where legally permitted;
- implement controlled `time_semantics_unknown`;
- document the unresolved source-semantic gate;
- do not claim Stage 2 PASS.

In that case the Stage 2 verdict must be:

```text
PASS WITH GAPS
```

or:

```text
FAIL
```

depending on how much of the required integration is incomplete.

A full Stage 2 `PASS` requires a defensible supported REN time profile.

---

# 13. Calendar implementation

If evidence establishes Europe/Lisbon source-day semantics, implement the provider calendar explicitly using:

```text
Europe/Lisbon
```

Do not use fixed WET/WEST offsets.

Derive local source-day boundaries independently and convert to UTC.

Support/test:

```text
ordinary day
spring DST day
autumn DST day
leap/year boundary where applicable
```

For a 15-minute local-day profile, expected physical counts would normally be:

```text
ordinary: 96
spring DST: 92
autumn DST: 100
```

but only enforce these counts if the verified REN profile supports that interpretation.

---

# 14. Instant vs interval

Do not automatically represent every REN value as a 15-minute mean.

Determine from source evidence whether values represent:

```text
instantaneous/sample MW
interval-average MW
another documented power statistic
```

If the source only justifies a timestamped sampled value, use the Stage 1 `valid_at`/instant representation.

If it explicitly defines an interval-supported mean, use a positive half-open interval.

Do not fabricate averaging support.

The parser/profile must encode this decision explicitly and version it.

---

# 15. REN parser input

The readiness assessment observed production responses shaped around:

```text
xAxis
yAxis
series
```

with JSON content despite a possible:

```text
Content-Type: text/plain
```

Do not trust MIME alone.

The parser should consume archived bytes and validate the complete supported JSON profile.

Use strict bounded JSON parsing.

Do not use provider HTML/presentation rendering.

---

# 16. Numeric parsing

System power values must use:

```text
Decimal
```

without binary-float intermediate.

Use an appropriate JSON parsing strategy such as:

```python
json.loads(..., parse_float=Decimal)
```

or the repository-equivalent safe implementation.

Reject:

- NaN;
- Infinity;
- booleans masquerading as numbers;
- unexpected strings;
- malformed numeric structures.

Do not round values.

Do not infer units.

---

# 17. Unit validation

The readiness assessment directly observed:

```text
MW
```

on the production response axis.

The parser must explicitly verify the supported unit/profile.

Do not accept a new unit because it “looks equivalent”.

Unexpected unit:

```text
→ controlled unsupported/schema/content outcome
```

not automatic conversion.

No MWh derivation belongs in Stage 2 unless the provider explicitly supplies energy data selected by scope—which it does not for the mandatory production series.

---

# 18. Series completeness

A successful selected REN day requires every mandatory selected concept expected by the supported profile.

Do not:

- silently omit a missing selected series;
- replace missing values with zero;
- emit partial success;
- silently truncate unequal arrays.

Validate:

```text
xAxis count
series count bounds
value-array length
selected-series presence
duplicate series
null values
unexpected structure
```

If mandatory selected coverage is incomplete, return an explicit failed/unavailable/content semantic outcome with zero normalized success.

---

# 19. Duplicate and unknown series

Reject or explicitly handle:

```text
duplicate selected series
conflicting duplicate series
unknown source concept
duplicate time labels inconsistent with DST profile
```

Do not select the first occurrence by response order.

Do not select the last occurrence arbitrarily.

Known DST repeated local labels must be resolved through the verified timezone/calendar profile, not string deduplication.

---

# 20. Presentation fields

REN responses may contain presentation-oriented information such as:

- colours;
- tooltips;
- style strings;
- labels;
- other chart configuration.

Treat presentation strings strictly as data.

Never evaluate them.

Ignore presentation-only fields only if the supported REN profile explicitly identifies them as irrelevant.

Do not dynamically execute or interpolate source strings into Python expressions.

---

# 21. Bounds

Apply the readiness-assessment initial application bounds unless concrete evidence requires a justified change:

```text
one source day
one logical report request

maximum original body:
1 MiB

maximum series:
32

maximum total values:
10,000
```

These are project application limits, not claims about REN's provider maximums.

If the selected response exceeds a bound:

fail explicitly.

Do not silently truncate.

---

# 22. Retry/request policy

Preserve the shared Phase 1/Stage 1 retry architecture:

```text
maximum 3 total attempts
bounded 1/2-second backoff
finite attempt budget
finite operation budget
verified TLS
trust_env=False
zero redirects
zero hidden transport retries
Accept-Encoding: identity
```

Do not add REN-specific polling.

Do not retry parser/content/time-profile failures.

Do not turn an empty/malformed response into repeated provider polling.

---

# 23. Provider pacing

For any permitted profile verification or later execution, keep REN calls sequential.

Use an application-conservative ceiling of approximately:

```text
≤ 1 request / second
```

when multiple deliberate calls are required.

This is project pacing, not a claimed REN quota.

Do not implement concurrency for REN.

---

# 24. Raw archive

Original complete safe provider bytes must be archived unchanged before semantic parsing.

Reuse the existing:

```text
SHA-256 content addressing
atomic no-replace publication
retrieval provenance
parse provenance
```

Do not normalize JSON before archival.

Do not pretty-print and archive a transformed representation.

The archived payload must remain the actual original response body.

---

# 25. Licensing / fixture restriction

The readiness assessment did not establish clear rights to redistribute real REN response bodies inside the Git repository.

Therefore:

**Do not commit real REN response bodies as fixtures unless the repository already contains documented operator/legal approval.**

Default fixture policy for Stage 2:

```text
synthetic real-shaped fixtures
```

derived from the verified schema/semantics without reproducing provider data values unnecessarily.

Fixture documentation must clearly mark:

```text
synthetic
```

and record what source profile it represents.

Any real provider observation used for source-profile verification must remain outside Git, for example under `/tmp`, unless explicit rights approval exists.

---

# 26. Fixture matrix

Add a small REN fixture suite under the established fixture conventions.

Cover at minimum:

### Valid

- ordinary supported day;
- spring DST profile;
- autumn DST profile with repeated local-hour labels;
- leap/year boundary where meaningful.

### Structural failures

- invalid JSON;
- HTML/error body;
- missing `xAxis`;
- missing `series`;
- wrong value-array length;
- duplicate selected series;
- missing mandatory selected series;
- unknown source series;
- wrong/unknown unit;
- excessive series;
- excessive values.

### Value failures

- null mandatory value;
- nonnumeric value;
- nonfinite value;
- invalid time label.

### Semantic failures

- unknown time profile;
- unsupported calendar profile;
- incomplete selected coverage.

### Revision/correction

Create synthetic same-query responses where:

```text
body A != body B
```

and verify both content identities survive.

Protect fixtures with the repository checksum manifest policy.

---

# 27. REN source catalogue/profile

Create a small versioned REN source-profile/catalogue representation owned by:

```text
src/iberian_shakti/ingestion/ren/
```

or another repository-consistent provider-specific location.

It should encode only verified mandatory Phase 2 facts such as:

- source ID;
- report/product ID;
- endpoint path;
- culture;
- selected series;
- explicitly known unselected series;
- unit;
- source profile version;
- verified timing semantics;
- technology mappings;
- interchange mappings.

Do not put secrets in it.

Do not add unrelated REN datasets.

Do not build a generic provider-plugin registry.

---

# 28. Normalized mapping

Use Stage 1 `SystemMeasurement` contracts.

Expected conceptual mapping:

```text
Consumption
→ measure = load
→ kind = actual

Wind
→ generation / wind

Solar
→ generation / solar

Hydro
→ generation / hydro

Natural Gas
→ generation / natural_gas

Biomass
→ generation / biomass

Other Thermal
→ generation / other_thermal

Coal
→ generation / coal

Wave
→ generation / wave

Import
→ interchange / import
→ aggregate external boundary

Export
→ interchange / export
→ aggregate external boundary
```

Use exact enum/value names consistent with Stage 1 contracts rather than introducing parallel synonyms.

If the existing generic technology vocabulary lacks one required verified REN technology, extend it narrowly and test it.

Do not add technologies for deferred providers pre-emptively.

---

# 29. Geography

Represent REN's selected data as Portuguese system/perimeter data using the Stage 1 geography contracts.

Do not claim:

```text
country PT
==
MIBEL bidding zone
==
control area
==
every Portuguese physical measurement perimeter
```

Preserve REN-native source/perimeter identity.

Import/export are:

```text
aggregate external boundary
```

not automatically:

```text
PT ↔ ES physical flow
```

Do not fabricate a Spanish counterparty.

---

# 30. Parse provenance

Use the Stage 1 measurement parse provenance.

Persist at minimum the appropriate:

- parser ID;
- parser version;
- system-measurement schema family/version;
- REN source-profile/catalogue version;
- original retrieval linkage;
- raw content hash/reference;
- parse outcome;
- record count.

Every normalized REN record must link to the parse/retrieval/raw chain.

---

# 31. Replay

REN replay must be entirely offline.

Given:

```text
archived REN bytes
+
original retrieval/query metadata
+
local REN source profile
```

the parser must reproduce the same normalized records without:

- HTTP;
- DNS;
- live REN metadata;
- remote timezone lookup;
- remote schema lookup.

Replay must verify content hash/linkage.

A later new parse event may have a different parse UUID/time, but fixed parser/profile/schema versions must reproduce the same normalized values and identities.

---

# 32. Actual-component integration test

Add at least one full offline integration flow using:

```text
real REN adapter
real shared HttpRetriever
MockTransport or approved capability boundary
real LocalRawArchive
real REN parser
real shared runner
real provenance persistence
real replay
```

Prove:

```text
request
→ retrieve
→ archive original bytes
→ retrieval provenance
→ parse
→ SystemMeasurement records
→ parse provenance
→ replay
```

No real provider network use inside pytest.

---

# 33. Correction/republication test

Using synthetic REN bodies, verify:

```text
same API query
same content
→ one content-addressed payload
→ separate retrieval events

same API query
changed content
→ separate payload hashes
→ both retrieval histories retained
```

Do not introduce destructive latest-overwrite semantics.

---

# 34. Provider unavailable/error behavior

Stage 2 should add deterministic REN-specific cases based only on verified provider evidence or clearly labelled synthetic behavior.

Do not claim synthetic response forms are observed REN behavior.

At minimum ensure:

- malformed/HTML body does not become data;
- empty selected coverage does not become successful zero records;
- invalid response structure fails safely;
- HTTP permanent failures do not trigger polling storms.

If actual REN future/missing/error behavior is still unverified, state that explicitly.

Do not invent a 404 contract.

---

# 35. Logging

REN logs must use the existing safe structured boundary.

Useful safe fields may include:

```text
source
report
query identity
delivery/source date
attempt
HTTP status
outcome
byte count
parser/profile version
record count
```

Do not log:

- raw response body;
- arbitrary chart strings;
- complete transport URL when unnecessary;
- environment configuration;
- unchecked exception strings.

No credentials should exist for REN.

---

# 36. No Phase 3+ leakage

Do not implement:

- Snowflake;
- dbt;
- feature tables;
- aggregation;
- renewable share;
- forecast models;
- API/dashboard;
- scheduler;
- cloud deployment.

Normalized REN records end at the Phase 2 ingestion boundary.

---

# 37. Acceptance criteria addressed by Stage 2

Explicitly trace Stage 2 evidence to the authoritative 44 Phase 2 criteria.

Stage 2 should materially address at least:

```text
2
3
4
9
10
11
12
14
15
16
20
21
22
24
25
26
27
28
29
31
32
33
34
35
36
37
41
42
43
```

Do not claim criterion 2 fully satisfied because the other three mandatory providers remain unimplemented.

Use the same classification style as Stage 1:

```text
SATISFIED
PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED
NOT YET APPLICABLE
```

Criterion 3 and criterion 4 are the critical REN-specific stage gates.

---

# 38. Stage 2 PASS requirements

Stage 2 may receive:

```text
PASS
```

only if all of the following are true:

1. the selected `ElectricityProductionBreakdownDaily` product is implemented;
2. all mandatory selected series are mapped correctly;
3. selected/unselected/unknown series behavior is explicit;
4. REN source-time semantics are sufficiently established for supported normalized UTC records;
5. ordinary and DST behavior is tested;
6. units and measurement semantics are explicit;
7. original bytes are archived before parsing;
8. correction/republication behavior works;
9. offline replay reproduces normalized records;
10. default pytest remains network-denied;
11. Phase 1/Stage 1 regressions remain green;
12. no provider-specific real fixture rights violation occurs;
13. full repository quality gates pass.

If source-time semantics remain unresolved:

do not mark Stage 2 PASS.

---

# 39. Stage 2 report

Create:

```text
docs/codex/reports/phase_2_stage_2_ren_report.md
```

Use the following structure.

## A. Objective

Define the exact REN scope.

## B. Baseline

Record:

- branch;
- initial HEAD;
- locally known origin relationship;
- working-tree state;
- Python environment.

## C. Authoritative inputs

Reference:

- Phase 2 readiness assessment;
- Stage 1 report;
- ADRs 0001–0004;
- any new REN source-profile ADR/document.

## D. REN source verification

Separate evidence as:

```text
officially documented
directly observed
inferred/project policy
unknown
```

Record verification date.

## E. Product/query profile

Document:

```text
ElectricityProductionBreakdownDaily
culture
date semantics
safe query identity
bounds
```

## F. Selected/unselected series

Provide a mapping table.

## G. Time and DST profile

This section must clearly state:

- verified timezone;
- timestamp meaning;
- interval/instant meaning;
- ordinary profile;
- spring DST profile;
- autumn DST profile;
- any remaining uncertainty.

Do not hide inference.

## H. Parser and normalization

Document complete JSON validation, Decimal parsing, units, geography and SystemMeasurement mapping.

## I. Retrieval/archive/provenance

Document how Stage 1/Phase 1 components were reused.

## J. Correction/republication behavior

Document same-query same/different-byte behavior.

## K. Offline replay

Document exact replay guarantees and test evidence.

## L. Security/logging

Document safe fields and unsupported/unknown source behavior.

## M. Fixture policy

State:

- synthetic vs real;
- checksum inventory;
- licensing/reuse handling.

## N. Tests

List focused modules and exact counts.

## O. Full validation

Record exact results for:

```text
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
pre-commit
```

## P. Phase 2 acceptance traceability

Trace the criteria listed in §37.

## Q. Files changed

Account for every path.

## R. External limitations

Keep provider uncertainties honest.

## S. Stage verdict

Use exactly one:

```text
PASS
PASS WITH GAPS
FAIL
```

## T. Next stage

If and only if Stage 2 is PASS:

```text
Phase 2 Stage 3 — ESIOS / REE integration
```

Do not implement Stage 3.

---

# 40. Documentation

Update only documentation made stale by Stage 2.

Possible paths:

```text
docs/runbooks/ingestion.md
docs/architecture/README.md
README.md
```

Do not broadly rewrite documentation.

Clearly say:

```text
REN implemented
ESIOS pending
ENTSO-E pending
Open-Meteo pending
Phase 2 in progress
```

Do not claim Phase 2 closure.

---

# 41. Tests

Run focused REN tests first.

Then run the full offline repository suite:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
```

The Stage 1 full-suite baseline is:

```text
1148 passed
```

The Stage 2 final count must not be lower because existing tests were removed, skipped or weakened.

Investigate any count reduction.

Normal pytest must require:

```text
zero real network
zero real REN calls
zero credentials
```

---

# 42. Pre-commit

Run applicable hooks against **every changed/new path**:

```bash
pre-commit run --files <all Stage 2 changed paths>
```

If hooks mutate files:

- inspect changes;
- rerun affected tests;
- rerun full quality checks as appropriate.

---

# 43. Git inspection

At the end inspect:

```bash
git status --short
git diff --stat
git diff
git diff --cached --stat
git diff --cached
```

Review untracked files explicitly.

Do not leave:

- `/tmp` observations;
- raw provider responses;
- debug files;
- secrets;
- caches;
- generated scratch scripts

inside the repository.

---

# 44. No commit/push/branch

Do not:

```text
git commit
git push
git switch -c
git checkout -b
```

Remain on existing `main`.

Leave all changes unstaged unless unavoidable for tooling.

The operator will review and commit Stage 2.

---

# 45. Stop condition

Stop after REN Stage 2 is fully documented and validated.

Do not begin:

```text
ESIOS
ENTSO-E
Open-Meteo
```

Do not perform Phase 2 pre-live audit.

Do not perform final Phase 2 live validation.

---

# 46. Final response

Return a concise summary containing:

1. Stage 2 baseline;
2. stored prompt path;
3. REN implementation paths;
4. REN product implemented;
5. selected-series mapping;
6. verified time semantics;
7. ordinary/spring/autumn profile evidence;
8. parser/normalization behavior;
9. archive/provenance behavior;
10. replay result;
11. correction/republication result;
12. fixture strategy;
13. focused test count;
14. final full pytest count;
15. Ruff result;
16. mypy result;
17. pre-commit result;
18. Phase 1/Stage 1 regression status;
19. Stage 2 report path;
20. Stage 2 verdict;
21. Git status;
22. next authorized stage.

If Stage 2 is PASS, end with:

```text
Next authorized implementation stage:
Phase 2 Stage 3 — ESIOS / REE integration
```

If REN time semantics remain unresolved, do **not** print that authorization line. Instead identify the unresolved Stage 2 semantic gate.

Do not commit.

Do not push.

Do not begin Stage 3.
