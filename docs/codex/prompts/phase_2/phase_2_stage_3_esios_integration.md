# Iberian_Shakti — Phase 2 Stage 3
## ESIOS / REE `Demanda prevista Peninsular` Integration

Implement **Phase 2 Stage 3 only**.

The selected provider/product is:

```text
Provider: ESIOS / Red Eléctrica
Indicator: 544
Name: Demanda prevista Peninsular
Geography: Spanish peninsular system
Unit: MW
Native cadence: 5 minutes
Kind: forecast
```

Keep this implementation small, explicit and consistent with the existing Phase 1 / Phase 2 ingestion architecture.

Do not start ENTSO-E, Open-Meteo, Snowflake, dbt, features, modelling or later phases.

---

## 1. Baseline

Start by recording:

```bash
git status --short
git log --oneline --decorate -10
```

Expected current local baseline:

```text
branch: main

HEAD:
13d5ff6 ci: run pre-commit in GitHub Actions

previous:
8bb5618 ci: add GitHub Actions quality checks
09792e9 feat: complete Phase 2 REN ingestion
8a377dd feat: establish Phase 2 multi-source foundation
70f4204 docs: record Phase 2 readiness assessment
```

The working tree should be clean.

Do not fetch, rebase, reset or synchronize with the remote.

Do not modify the recently added GitHub Actions workflow unless Stage 3 genuinely requires it.

---

# 2. Read before implementing

Read at minimum:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md
docs/codex/reports/phase_2_stage_1_report.md
docs/codex/reports/phase_2_stage_2_ren_report.md

docs/adr/0003-*
docs/adr/0004-*
docs/adr/0006-*

src/iberian_shakti/contracts/
src/iberian_shakti/ingestion/
tests/contracts/
tests/integration/
```

Inspect the shared:

```text
query contracts
SystemMeasurement
authentication/private-request policy
HttpRetriever
archive
retrieval provenance
parse provenance
replay
logging
semantic outcome handling
```

Reuse them.

Do not create another ingestion framework.

---

# 3. Save this prompt first

Before implementation save this exact prompt at:

```text
docs/codex/prompts/phase_2/
phase_2_stage_3_esios_integration.md
```

Do not modify previous prompt-history files.

---

# 4. Authoritative product semantics

Pin exactly one Stage 3 product:

```text
ESIOS indicator 544
Demanda prevista Peninsular
```

The accepted source semantics are:

```text
forecast of Spanish peninsular electricity demand
MW
one value every five minutes
```

Official ESIOS publication description states:

```text
00:00:
information for day D

13:30:
adds the first three hours of D+1
```

Therefore this indicator must **not** be described as:

```text
complete D+1 forecast
complete day-ahead forecast
auction-time D-1 forecast
seven-day demand forecast
actual demand
scheduled demand
```

Do not substitute another ESIOS demand indicator such as:

```text
460
545
1293
```

Stage 3 is indicator **544 only**.

---

# 5. Query contract

Implement a versioned ESIOS query profile for indicator 544.

Use the official indicator API endpoint pattern:

```text
https://api.esios.ree.es/indicators/544
```

Use bounded ISO-8601:

```text
start_date
end_date
```

queries.

Do not request API-side aggregation unless required by the already accepted readiness design.

In particular, preserve the native five-minute observations rather than requesting:

```text
hourly
daily
average
sum
```

aggregation.

Query identity must contain only safe non-secret information, such as:

```text
provider
indicator ID
requested time window
profile version
```

The authentication token must never enter canonical query identity.

---

# 6. Authentication

Use:

```text
ESIOS_API_TOKEN
```

through the existing private-authentication mechanism.

Do not:

```text
hardcode tokens
commit tokens
persist tokens
log tokens
place tokens in query parameters
place tokens in safe locators
put tokens in provenance
load arbitrary dotenv files
implement token refresh
implement fallback authentication
```

Validate the token before constructing the external request.

If the credential is absent, fail before network I/O with the existing controlled authentication/configuration mechanism.

Use only the ESIOS authentication header mechanism already established by the authoritative readiness work / official API contract.

Do not invent multiple authentication alternatives.

---

# 7. CI remains offline

GitHub Actions must not require:

```text
ESIOS_API_TOKEN
```

Stage 3 tests must remain completely offline.

Do not add an ESIOS secret to GitHub.

Do not weaken the repository's network-denied pytest guard.

---

# 8. Response parsing

Implement a strict ESIOS JSON parser.

Use the actual documented indicator response structure.

At minimum validate the relevant indicator metadata and value records rather than blindly accepting arbitrary JSON.

Expected source concepts may include fields such as:

```text
indicator identity
name
magnitude
cadence/time metadata
geography metadata
values
datetime
datetime_utc
value
geo_id
geo_name
```

Only require fields actually justified by the official contract / retained Stage 3 evidence.

Do not make optional presentation metadata mandatory without reason.

Reject incompatible product identity.

A response for another indicator must not normalize as indicator 544.

---

# 9. Timestamp policy

Use the provider's explicit UTC timestamp when supplied:

```text
datetime_utc
```

as the canonical normalized time.

Do not reconstruct UTC from a naive Spanish local timestamp when an explicit provider UTC value exists.

If both local timestamp and UTC timestamp are supplied, validate that they are consistent where practical.

Retain useful source-native timestamp information in provenance or parse identity without duplicating fields unnecessarily.

No fixed CET/CEST offset.

No naive local-time arithmetic.

---

# 10. Five-minute cadence

Preserve the native observations.

Do not resample the series.

Do not interpolate missing values.

Do not forward-fill missing values.

Do not synthesize five-minute rows.

Do not aggregate the observations to 15 minutes or one hour in ingestion.

Feature engineering or later resampling belongs to later phases.

Validate expected five-minute ordering/cadence where the response provides contiguous coverage.

A genuine gap must remain visible rather than being silently repaired.

---

# 11. Measurement representation

Normalize indicator 544 as:

```text
measure: load
kind: forecast
unit: MW
geography: Spanish peninsular system
```

Treat each returned observation as a timestamped forecast sample at its provider UTC timestamp.

Do not claim that it is actual measured load.

Do not introduce a new measurement statistic unless the existing contracts genuinely cannot represent the source.

Prefer the simplest existing representation that does not make an unsupported claim.

In particular:

- do not infer an arithmetic interval mean;
- do not introduce another confidence/evidence framework;
- do not create special ESIOS-only measurement contracts if `SystemMeasurement` already handles the case.

---

# 12. Geography

Preserve ESIOS native geographic identity when supplied.

Map it to the existing canonical representation for the **Spanish peninsular electricity system**.

Do not collapse it to generic `Spain` if the source provides the more precise peninsular system identity.

Do not invent:

```text
bidding zone
control area
province
autonomous community
```

unless supported by the source metadata and existing contract.

---

# 13. Forecast-vintage safety

This is important.

An acquisition of historical indicator 544 values today does **not automatically prove** what forecast values were available at some historical market cutoff.

Keep these concepts separate:

```text
target timestamp
source update/publication metadata
acquisition timestamp
parse timestamp
```

If the source response contains something such as:

```text
values_updated_at
```

preserve it with its actual meaning.

Do not automatically turn it into a per-value:

```text
issued_at
forecast_created_at
D-1 forecast time
```

unless that interpretation is source-supported.

Unknown forecast-edition/issue times should remain unknown.

This prevents future training-data leakage claims.

---

# 14. Revisions and repeated acquisition

ESIOS values may change between acquisitions.

Reuse the existing immutable archive model:

```text
same query + same body
    -> reuse content, retain acquisition event

same query + changed body
    -> retain both bodies and both acquisition histories
```

Do not overwrite previous source bytes.

Do not maintain only a mutable "latest" copy.

The source may revise values; ingestion must preserve that fact without requiring Stage 3 to model every historical forecast edition.

---

# 15. Archive and provenance

Reuse the existing:

```text
original-byte archive
SHA-256 content addressing
retrieval provenance
parse provenance
offline replay
```

Archive the complete safe successful response before semantic parsing.

Every normalized ESIOS record must be traceable to:

```text
provider
indicator
safe query
acquisition event
raw SHA-256
parser/profile version
native value identity
```

Do not redesign shared provenance.

---

# 16. Error behavior

Use existing typed outcomes.

At minimum cover controlled behavior for:

```text
missing credential
401 / 403
404
429
5xx
timeout
oversized body
invalid JSON
wrong indicator
missing values
invalid timestamps
non-finite numeric values
unexpected unit
unexpected geography/product identity
duplicate conflicting observations
```

Authentication errors are terminal.

Permanent schema/content errors do not retry.

Use existing bounded shared retry behavior instead of introducing ESIOS-specific retry loops.

Respect `Retry-After` through the existing transport policy where supported.

---

# 17. Secret-safe diagnostics

Add focused tests proving the ESIOS token cannot appear in:

```text
logs
exceptions
query identity
archive locators
retrieval provenance
parse provenance
serialized metadata
```

Use synthetic token-like strings only.

Never print a real token.

---

# 18. Fixtures

Use small synthetic ESIOS fixtures.

Do not commit a real authenticated ESIOS response unless repository policy and redistribution rights explicitly allow it.

Create only the fixtures necessary to test:

```text
valid five-minute forecast
multiple values
UTC timestamps
peninsular geography
missing value
invalid numeric value
bad timestamp
wrong indicator
wrong unit
duplicate/conflicting timestamp
malformed JSON
changed-value revision
```

Maintain a fixture manifest/checksum policy consistent with the existing project.

Avoid a large fixture catalogue when a small set plus in-memory mutations is sufficient.

---

# 19. Required tests

At minimum implement tests for:

### Query/auth

```text
indicator 544 only
safe deterministic query identity
token injected privately
missing token fails before I/O
token never persisted/logged
```

### Successful normalization

Verify:

```text
forecast kind
load measure
MW
Spanish peninsular geography
provider UTC timestamp
five-minute cadence
source values preserved
```

### Timestamp handling

Test:

```text
explicit UTC parsing
offset-aware local timestamp if present
DST-relevant timestamp consistency
ordering
gaps remain gaps
```

Do not create REN-style calendar complexity unless the ESIOS response actually requires it.

### Failure

Test:

```text
wrong indicator
wrong unit
wrong geography when mandatory
malformed timestamps
non-finite numbers
schema mismatch
conflicting duplicates
```

### Revision/archive

Test:

```text
same query / same body
same query / changed body
immutable histories
```

### Offline replay

A successful archived ESIOS acquisition must replay with:

```text
zero network
same normalized values
same business identities
same source timestamps
same raw linkage
```

Only parse-event identity/time may change where expected.

---

# 20. No live provider request in this task

This Stage 3 implementation task is offline.

Do not make an authenticated ESIOS request.

Do not probe the token.

Do not add an automatic live test.

Do not add ESIOS credentials to CI.

Controlled live validation belongs to the later Phase 2 live-validation stage.

If the existing retained evidence is insufficient to implement a specific source field safely, document that exact gap rather than guessing or making an unapproved provider request.

---

# 21. Documentation

Create a focused Stage 3 report:

```text
docs/codex/reports/
phase_2_stage_3_esios_report.md
```

Add a focused ADR only if Stage 3 introduces a durable design decision not already covered by ADR 0003/0004.

Do not create an ADR merely to document ordinary implementation detail.

Update README/runbook/architecture only where current operational documentation genuinely requires it.

Keep documentation concise.

---

# 22. Stage 3 acceptance

Stage 3 may PASS offline when:

```text
indicator 544 query contract implemented
private authentication implemented safely
strict JSON parser implemented
five-minute source observations preserved
UTC timestamp normalization works
Spanish peninsular geography retained
forecast/load/MW semantics correct
historical acquisition is not mislabelled as full D-1 vintage
archive/provenance works
revision preservation works
offline successful replay works
secret leakage tests pass
Phase 1 / Stage 1 / Stage 2 regressions remain green
full repository quality gates pass
```

No live ESIOS request is required for this Stage 3 engineering PASS.

Any source behavior that can only be proven live should be recorded for later controlled validation.

---

# 23. Validation

Run:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
pre-commit run --all-files
```

Also run a focused Stage 3 ESIOS suite and report its count separately.

Do not delete, skip or weaken existing tests to achieve a pass.

The existing GitHub CI workflow should remain compatible with the full test suite.

---

# 24. Scope exclusions

Do not implement:

```text
ESIOS indicator 460
ESIOS indicator 545
ESIOS actual demand
other ESIOS products

ENTSO-E
Open-Meteo
MIBGAS

Snowflake
dbt
feature engineering
forecast models
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

# 25. Git rules

Do not:

```text
create a branch
stage files
commit
push
```

Leave the completed Stage 3 working tree for operator review.

---

# 26. Final response

Return:

1. baseline branch/HEAD;
2. files changed;
3. ESIOS profile/parser version;
4. exact selected indicator;
5. query/window behavior;
6. authentication mechanism and missing-token behavior;
7. normalized measurement semantics;
8. timestamp handling;
9. geography handling;
10. revision behavior;
11. archive/provenance/replay behavior;
12. secret-safety result;
13. focused ESIOS test result;
14. full pytest result;
15. Ruff result;
16. formatting result;
17. mypy result;
18. pre-commit result;
19. `git diff --check` result;
20. Stage 3 verdict;
21. remaining items reserved for controlled live validation;
22. exact Git status;
23. confirmation of:
   - no provider request;
   - no branch;
   - no staging;
   - no commit;
   - no push.

If all offline acceptance criteria pass, finish with:

```text
Phase 2 Stage 3 — PASS

ESIOS indicator 544 is implemented as an authenticated,
five-minute Spanish peninsular demand-forecast source with
immutable acquisition provenance and offline replay.

Historical acquisitions are not represented as guaranteed
complete D-1 forecast vintages.

No live ESIOS request was made.

Phase 2 Stage 4 has not been started or authorized.
```

Otherwise use:

```text
Phase 2 Stage 3 — PASS WITH GAPS
```

and identify the exact remaining engineering blocker.

Stop there.
