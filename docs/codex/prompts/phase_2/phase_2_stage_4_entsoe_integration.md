# Iberian_Shakti — Phase 2 Stage 4
## ENTSO-E Transparency Platform Integration

Implement **Phase 2 Stage 4 only**.

The scope is exactly:

```text
1. Spain — Actual Total Load
   DocumentType: A65
   ProcessType:  A16

2. Portugal — Day-ahead Wind/Solar Generation Forecast
   DocumentType: A69
   ProcessType:  A01

3. Spain — Day-ahead Wind/Solar Generation Forecast
   DocumentType: A69
   ProcessType:  A01
```

Do not add other ENTSO-E products.

Keep the implementation understandable and reuse the existing Phase 1 / Phase 2 ingestion architecture.

---

## 1. Baseline

Start with:

```bash
git status --short
git log --oneline --decorate -10
```

Expected current baseline:

```text
branch: main

HEAD:
8ef31ef feat: complete Phase 2 ESIOS ingestion

preceded by:
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

# 2. Read before modifying

Read at minimum:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md
docs/codex/reports/phase_2_stage_1_report.md
docs/codex/reports/phase_2_stage_2_ren_report.md
docs/codex/reports/phase_2_stage_3_esios_report.md

docs/adr/0003-*
docs/adr/0004-*
docs/adr/0006-*

src/iberian_shakti/contracts/
src/iberian_shakti/ingestion/
tests/contracts/
tests/integration/
```

Understand and reuse:

```text
ApiSourceRequest / SystemQuery
SystemMeasurement
private authentication
HttpRetriever
immutable raw archive
retrieval provenance
parse provenance
semantic outcomes
offline replay
safe logging
```

Do not create a parallel ingestion framework.

---

# 3. Save this prompt first

Save this exact prompt before implementation:

```text
docs/codex/prompts/phase_2/
phase_2_stage_4_entsoe_integration.md
```

Do not modify older prompt-history files.

---

# 4. Selected products

Implement only these products.

## 4.1 Spain actual total load

```text
source: ENTSO-E
country/system: Spain
documentType: A65
processType: A16
meaning: Actual Total Load
measure: load
kind: actual
unit: MW
```

The official ENTSO-E extraction contract identifies:

```text
A65 = Total Load
A16 = Realised
```

Do not substitute:

```text
day-ahead load forecast
week-ahead load forecast
generation
consumption forecast
```

for this product.

---

## 4.2 Portugal + Spain day-ahead wind/solar forecasts

For each country independently:

```text
source: ENTSO-E
documentType: A69
processType: A01
meaning: Day-ahead generation forecasts for wind and solar
measure: generation
kind: forecast
unit: MW
```

Preserve the generation technology identity supplied by ENTSO-E.

Expected relevant PSR technologies include:

```text
Solar
Wind Offshore
Wind Onshore
```

Use the authoritative ENTSO-E code mappings already established by the readiness work / official code list.

Do not invent a technology code.

---

# 5. Important wind/solar rule

Do **not** combine all renewable forecast series into one value during ingestion.

Keep separate normalized records for:

```text
solar
wind_onshore
wind_offshore
```

when the provider supplies them.

Most importantly:

> **An absent technology series is not zero generation.**

For example, if Portugal returns:

```text
solar
wind_onshore
```

but no offshore-wind TimeSeries, do not synthesize:

```text
wind_offshore = 0
```

Absence must remain absence.

Likewise, do not manufacture missing solar or wind series.

Aggregation can happen in later feature engineering if required.

---

# 6. ENTSO-E authentication

Use the existing selected-provider credential:

```text
ENTSOE_API_TOKEN
```

through the current private-authentication mechanism.

Do not:

```text
hardcode the token
commit it
log it
persist it in provenance
put it in canonical query identity
put it in archive filenames
print it in errors
add it to GitHub Actions
```

Missing or invalid local configuration must fail before network I/O.

No token refresh, token probing or alternate authentication workflow is required.

All Stage 4 tests remain offline and use synthetic credentials.

---

# 7. API query identity

Create a narrow versioned ENTSO-E source profile.

Safe query identity should include only relevant non-secret fields such as:

```text
provider
profile version
document type
process type
domain
requested UTC window
selected product family
```

Use the existing canonical query architecture.

Do not fabricate:

```text
provider revision number
publication version
forecast edition
```

unless actually supplied.

---

# 8. Domain identity

Use the correct ENTSO-E domain identifiers already established or verified for:

```text
Spain
Portugal
```

Preserve native EIC/domain identity in normalized records/provenance.

Do not reduce the provider identity merely to free-text country names.

At the same time, map records to the existing canonical geography contracts.

Do not guess whether a field represents:

```text
country
bidding zone
control area
system perimeter
```

Use the meaning required by the specific ENTSO-E product.

For Actual Total Load, follow the official dependency rule for its domain parameter.

For A69 generation forecasts, follow the official generation dependency rule.

---

# 9. Time request format

Use bounded UTC request windows.

Do not use naive local timestamps.

Do not create DST-specific request arithmetic if the provider contract operates in UTC.

The requested window is query context; it must not silently become a claim about:

```text
forecast publication time
issue time
model-run time
```

unless the response explicitly provides that information.

---

# 10. Response family

ENTSO-E can return at least two relevant semantic response families:

```text
Generation/Load MarketDocument
Acknowledgement_MarketDocument
```

Handle both explicitly.

A valid HTTP response containing an acknowledgement document is **not** successful measurement data.

Parse its controlled reason/code safely.

Do not log unrestricted provider error text.

---

# 11. XML parser security

This is an untrusted external XML boundary.

The implementation must prevent:

```text
DTD processing
external entity resolution
external resource loading
entity expansion attacks
unbounded nesting
unbounded text
unbounded number of elements
```

Do not use an XML parser configuration that can access the filesystem or network.

If the existing dependencies are sufficient, prefer them.

Do not add a runtime dependency unless necessary and justified.

Tests must exercise the **actual parser boundary** with hostile synthetic XML.

At minimum reject safely:

```text
DOCTYPE
ENTITY declarations
external entities
malformed XML
excessive nesting
excessive element count
excessive text
unsupported encoding
```

Keep the accepted encoding policy explicit.

---

# 12. XML namespace/version handling

Do not parse ENTSO-E XML by blindly stripping namespaces.

Recognize the supported Generation/Load document namespace/version explicitly.

Preserve a versioned parser/profile identity.

If ENTSO-E returns an unknown XML namespace/schema version:

```text
fail visibly
```

rather than interpreting it as the known schema.

Do the same for acknowledgement documents.

Avoid implementing a universal ENTSO-E XML parser.

Support only what Stage 4 needs.

---

# 13. Document-level validation

Validate the relevant document metadata before normalizing TimeSeries.

At minimum, where supplied/required, verify:

```text
document type
process type
document identity
created timestamp
time interval
domain identity
```

For the three selected requests, incompatible document/process combinations must fail.

Examples:

```text
A65 + A01  -> not Stage 4 actual load
A69 + A16  -> not Stage 4 day-ahead wind/solar forecast
```

Do not normalize a different ENTSO-E product merely because it contains quantities.

---

# 14. TimeSeries identity

Retain and validate useful source identities including, as applicable:

```text
TimeSeries mRID
business type
object aggregation
in/out domain
PSR type
measurement unit
curve type
Period
```

Do not discard PSR technology before normalized-record construction.

For actual load, PSR technology should not be fabricated.

For A69, technology identity is essential.

---

# 15. Measurement unit

Require the expected ENTSO-E MW unit.

Reject incompatible unit semantics.

Preserve numeric values using the existing exact system-measurement numeric policy.

Do not:

```text
round source values unnecessarily
clip negative/positive values
silently coerce malformed numbers
```

If provider/product semantics impose a valid sign restriction already established by authoritative evidence, enforce it; otherwise do not invent one.

---

# 16. Period parsing

ENTSO-E Period structures require:

```text
timeInterval/start
timeInterval/end
resolution
Point/position
Point/quantity
```

Support the resolutions actually permitted for the selected products and justified by the source contract.

Do not assume one fixed resolution globally.

Validate:

```text
positive period duration
supported ISO-8601 duration
positions
quantity
coverage bounds
```

Each normalized support interval must be UTC-aware.

---

# 17. Curve type A01

Support:

```text
A01 = sequential fixed-size block
```

For A01:

- positions represent successive fixed-resolution intervals;
- expected positions must be complete for the Period;
- missing positions are failure;
- duplicate positions are failure;
- positions outside the Period are failure;
- derived interval boundaries must stay within the declared Period.

Do not fill missing points.

Do not sort malformed input into apparent validity unless ordering is semantically irrelevant and explicitly allowed by the source contract.

---

# 18. Curve type A03

Support:

```text
A03 = variable-size block
```

For A03:

- each supplied position begins a block;
- the block extends until the next supplied position;
- the final block extends to the Period end;
- the quantity applies over that block.

Expand it deterministically into normalized support intervals only where this representation fits the existing SystemMeasurement contract.

Do not pretend omitted A03 positions are missing data: omission is part of the curve encoding.

Reject:

```text
duplicate positions
non-increasing block starts
position outside Period
zero/negative derived block
```

Keep A01 and A03 logic clearly separated.

---

# 19. Multiple Period elements

A TimeSeries may contain more than one `Period`.

Support multiple Period elements where permitted.

Do not assume:

```text
one TimeSeries = one Period
```

Normalize all valid non-overlapping Periods.

Validate each independently.

---

# 20. Overlap and conflict handling

Do not silently overwrite normalized values.

If two source TimeSeries or Periods produce the same canonical business identity/support:

### identical semantic value

Handle according to the existing deterministic duplicate policy.

### conflicting value

Fail with a controlled conflict outcome.

Do not:

```text
keep first
keep last
average
sum
```

unless the source contract explicitly says to do so.

---

# 21. Actual load normalization

Spain A65/A16 should normalize as:

```text
measure = load
kind = actual
unit = MW
geography = Spanish ENTSO-E system/domain
```

Use the Period interval as the measurement support.

Do not force it into an instantaneous sample if ENTSO-E publishes interval quantities.

Use the existing suitable statistic/support representation based on the ENTSO-E product semantics already established by the project contracts.

Do not create a new statistic unless necessary.

---

# 22. Wind/solar forecast normalization

PT/ES A69/A01 should normalize as:

```text
measure = generation
kind = forecast
unit = MW
technology = source PSR technology
geography = corresponding PT or ES domain
```

Preserve:

```text
solar
wind_onshore
wind_offshore
```

as separate identities.

Do not aggregate them.

Do not create absent technology records.

---

# 23. Forecast vintage safety

Keep separate:

```text
target/support interval
document created timestamp
provider update/publication metadata
acquisition timestamp
parse timestamp
```

Do not assume:

```text
createdDateTime == forecast issue time for every value
```

unless the document semantics justify that interpretation.

Do not claim that a historical API acquisition reconstructs exactly what was known at an earlier market cutoff unless the provider evidence proves that.

Unknown edition/issue semantics remain unknown.

---

# 24. Acknowledgement documents

Implement a strict, safe acknowledgement parser sufficient to distinguish at least:

```text
no matching data
invalid request
technical/data-volume rejection
authentication/authorization-related failure where represented
other unsupported acknowledgement
```

Preserve the raw acknowledgement bytes in the immutable archive when safe and complete.

Normalized measurement count must be zero.

Do not treat:

```text
reason code 999
```

alone as a complete semantic interpretation if the document provides structured context.

Map only source-supported meanings.

Provider text must not leak secrets into logs.

---

# 25. Retry behavior

Reuse the existing shared retry/deadline behavior.

Do not create an ENTSO-E retry loop.

Authentication/authorization failure must be terminal.

Permanent acknowledgement/schema/content errors do not retry.

Transient HTTP errors may use existing bounded retries.

Respect supported `Retry-After` behavior.

---

# 26. Archive and provenance

Reuse without redesign:

```text
immutable original bytes
SHA-256 content addressing
retrieval events
parse events
offline replay
```

Every successful normalized record must link to:

```text
safe query
acquisition
raw hash/reference
parser/profile version
source TimeSeries identity
native domain
native PSR identity where applicable
```

Malformed but complete safe responses should still archive before parse failure.

Interrupted or oversized responses must not appear as complete acquisitions.

---

# 27. Corrections and repeated acquisitions

For identical query identity:

```text
same body
-> shared content + separate acquisition history

changed body
-> retain both bodies and both histories
```

Never overwrite old data.

Do not implement a mutable latest-only model.

---

# 28. Offline replay

Successful Stage 4 records must replay with:

```text
zero network
zero credential requirement
same normalized values
same support intervals
same source/domain/technology identity
same raw linkage
```

Only the new parse-event identity/time may differ where designed.

Corrupt archive/hash/linkage must fail without refetching.

---

# 29. Synthetic fixtures

Use small synthetic XML fixtures.

Do not commit real authenticated ENTSO-E responses unless explicitly approved and redistribution rights are established.

Prefer a small number of representative fixtures plus in-memory mutations.

At minimum cover:

```text
valid ES A65/A16 load
valid PT A69/A01 solar/wind
valid ES A69/A01 solar/wind
A01 fixed curve
A03 variable block
multiple Period elements
acknowledgement document
malformed XML
wrong namespace
wrong document type
wrong process type
wrong domain
wrong unit
unknown PSR type
duplicate position
missing A01 position
conflicting overlap
DTD/entity attack
oversized/deep XML
changed-body revision
```

Maintain the repository's fixture manifest/checksum conventions.

---

# 30. Unknown PSR technology

For the selected A69 product:

- known selected solar/wind PSR codes should map explicitly;
- an unsupported unexpected PSR type must fail visibly or remain unsupported according to the strict source profile;
- do not silently classify an unknown PSR type as `other`;
- do not treat absence as zero.

---

# 31. Provider no-data semantics

Do not invent no-data semantics from:

```text
empty XML
missing TimeSeries
HTTP 404
```

unless verified.

Use acknowledgement-document semantics where supported.

Until controlled live validation establishes real provider variants, keep unknown forms explicit.

---

# 32. Logging and secret safety

Test that `ENTSOE_API_TOKEN` cannot appear in:

```text
logs
exceptions
canonical query identity
archive locator
retrieval provenance
parse provenance
serialized diagnostics
```

Use synthetic token-like values only.

No real credential should be read during tests.

---

# 33. No live ENTSO-E request

This implementation task is offline only.

Do not:

```text
call ENTSO-E
probe the token
test authentication live
download historical data
perform metadata discovery through the API
```

Do not modify GitHub secrets.

Controlled provider validation belongs to the later Phase 2 live-validation stage.

Where source behavior cannot be proven offline from accepted authoritative documentation, record the gap rather than guessing.

---

# 34. Documentation

Create:

```text
docs/codex/reports/
phase_2_stage_4_entsoe_report.md
```

The report should clearly describe:

```text
selected products
query identities
authentication
XML namespaces/schema support
A01/A03 behavior
multiple Period handling
domain mapping
technology mapping
acknowledgement behavior
archive/replay
limitations reserved for live validation
```

Create a new ADR only if Stage 4 requires a genuinely new durable architectural decision not already covered by existing ADRs.

Do not create an ADR for routine parser implementation.

Update README/architecture/runbook only where necessary.

---

# 35. Focused tests

Create focused tests for:

```text
query/profile
private authentication
XML parser
load normalization
wind/solar normalization
A01
A03
multiple Periods
duplicates/conflicts
acknowledgements
XML security
archive/revisions
offline replay
secret safety
```

Report the focused Stage 4 test count separately.

---

# 36. Regression protection

All earlier behavior must remain green:

```text
Phase 1 OMIE
Phase 2 Stage 1 shared foundation
Stage 2 REN
Stage 3 ESIOS
GitHub CI workflow
```

Do not modify existing behavior merely to make ENTSO-E easier to implement.

Do not weaken or delete tests.

---

# 37. Validation

Run:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
pre-commit run --all-files
```

Also run the focused Stage 4 suite separately.

The default network-denied pytest guard must remain active.

No test should require:

```text
ESIOS_API_TOKEN
ENTSOE_API_TOKEN
network access
cloud resources
```

---

# 38. Stage 4 acceptance criteria

Stage 4 may PASS offline when all of these hold:

```text
ES A65/A16 query implemented
ES actual load normalization works

PT A69/A01 query implemented
ES A69/A01 query implemented

solar/onshore/offshore technology identity retained
absent technology never becomes zero

private ENTSO-E authentication works safely
missing credential fails before I/O

strict Generation/Load XML parser implemented
supported namespace/version explicit

A01 fixed-block handling works
A03 variable-block handling works
multiple Period handling works

invalid/missing/conflicting positions fail visibly
conflicting overlaps fail visibly

Acknowledgement_MarketDocument handled explicitly

XML DTD/entity/resource attacks rejected
parser work limits enforced

archive/provenance works
changed acquisitions remain immutable
successful offline replay works

secret-safety tests pass

all earlier regressions pass
all repository quality gates pass
```

No live ENTSO-E request is required for **offline Stage 4 engineering PASS**.

---

# 39. Reserve for later controlled live validation

The Stage 4 report must explicitly reserve real-provider validation of items such as:

```text
successful ENTSO-E authentication
actual current namespaces/schema variants
exact real domain IDs returned
actual PSR combinations for PT and ES
actual resolutions
A01/A03 occurrence in selected products
multi-Period occurrence
real acknowledgement codes/text
no-data behavior
inclusive/exclusive request boundaries
publication/update metadata
historical corrections
quota/rate behavior
response sizes/encoding
```

Do not claim these have been observed during this offline task.

---

# 40. Scope exclusions

Do not implement:

```text
other ENTSO-E load products
actual generation
day-ahead total load forecast
installed capacity
interchange
cross-border flows
prices
balancing
outages

additional ESIOS products
additional REN products
Open-Meteo
MIBGAS

Snowflake
dbt
feature engineering
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

# 41. Git rules

Do not:

```text
stage
commit
push
create a branch
```

Leave the entire Stage 4 change set for operator review.

---

# 42. Final response

Return a concise engineering summary containing:

1. baseline branch and HEAD;
2. all files changed;
3. profile/parser version;
4. selected ENTSO-E products;
5. domain/query mapping;
6. authentication behavior;
7. XML namespace/version support;
8. XML security behavior;
9. actual-load normalization;
10. PT/ES wind/solar normalization;
11. PSR technology behavior;
12. confirmation that absent technologies remain absent;
13. A01 behavior;
14. A03 behavior;
15. multiple-Period behavior;
16. overlap/conflict behavior;
17. acknowledgement handling;
18. archive/provenance behavior;
19. replay behavior;
20. secret-safety result;
21. focused Stage 4 test count/result;
22. full pytest result;
23. Ruff result;
24. formatting result;
25. mypy result;
26. pre-commit result;
27. `git diff --check` result;
28. remaining controlled-live-validation items;
29. Stage 4 verdict;
30. exact Git status;
31. confirmation:
   - no provider request;
   - no branch;
   - no staging;
   - no commit;
   - no push.

If all offline acceptance criteria pass, finish with:

```text
Phase 2 Stage 4 — PASS

ENTSO-E Spain Actual Total Load (A65/A16) and
Portugal/Spain day-ahead wind/solar forecasts (A69/A01)
are implemented with strict XML parsing, native technology
identity, immutable provenance and offline replay.

Absent wind/solar technology series remain absent and are
never converted into synthetic zero observations.

No live ENTSO-E request was made.

Phase 2 Stage 5 has not been started or authorized.
```

Otherwise finish with:

```text
Phase 2 Stage 4 — PASS WITH GAPS
```

and identify the exact blocker.

Stop there.
