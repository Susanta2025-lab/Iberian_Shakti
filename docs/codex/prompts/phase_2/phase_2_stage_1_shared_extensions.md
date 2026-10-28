# Iberian_Shakti — Phase 2 Stage 1
## Shared Multi-Source Contracts, Query Semantics, Authentication Boundary & Semantic Outcomes

You are working in the existing **Iberian_Shakti** repository on `main`.

Phase 0 and Phase 1 are formally:

```text
Phase 0 — CLOSED/PASS
Phase 1 — CLOSED/PASS
```

Phase 2 is:

```text
Multi-Source Ingestion Expansion
```

The single authoritative Phase 2 readiness/source assessment is:

```text
docs/codex/reports/phase_2_readiness_assessment.md
```

Its verdict is:

```text
GO WITH GAPS
```

Mandatory Phase 2 providers are:

```text
REN
ESIOS / REE
ENTSO-E
Open-Meteo
```

MIBGAS is:

```text
DEFER TO A LATER PHASE
```

This task is **Phase 2 Stage 1 only**.

---

# 0. Critical precondition

Before making implementation changes, inspect:

```bash
git status
git log --oneline --decorate -12
```

The Phase 2 readiness assessment must already exist in the repository and must be treated as the authoritative implementation contract.

Read it completely:

```text
docs/codex/reports/phase_2_readiness_assessment.md
```

Especially:

```text
§J  Normalized domain model requirements
§K  Time, timezone and DST policy
§L  Forecast/actual/revision semantics
§M  Retrieval/archive/replay implications
§N  Authentication and secret handling
§O  Dependencies
§P  Test and fixture strategy
§R  Security considerations
§U  Recommended implementation stages
§V  Phase 2 acceptance checklist
§W  Explicit non-goals
§X  Final readiness decision
```

Do not create another readiness assessment.

Do not redefine the Phase 2 scope.

Do not weaken or replace the 44 authoritative acceptance criteria.

---

# 1. Create the permanent Phase 2 prompt folder first

Before implementation, create:

```text
docs/codex/prompts/phase_2/
```

This directory will store the exact prompts used for all future Phase 2 stages.

Also create:

```text
docs/codex/prompts/phase_2/README.md
```

The README should explain briefly:

- this directory stores the operator-approved Codex prompts used during Phase 2;
- prompts are historical engineering records;
- they must not be rewritten later merely because implementation evolves;
- reports remain under `docs/codex/reports/`;
- prompts are instructions, not acceptance evidence by themselves;
- future prompt naming convention:

```text
phase_2_stage_<N>_<short_description>.md
```

For this task, save the **exact Stage 1 prompt received from the operator** as:

```text
docs/codex/prompts/phase_2/phase_2_stage_1_shared_extensions.md
```

Preserve the substantive instructions faithfully.

Do not replace the stored prompt with a summary.

Future Phase 2 prompts should also be stored in this directory before their corresponding stage implementation begins.

This prompt-storage requirement is documentation/history only; do not build a prompt execution framework.

---

# 2. Stage 1 objective

Implement only the shared foundation required before individual Phase 2 providers.

The authoritative assessment defines Stage 1 as:

```text
Record accepted query/measurement/forecast/auth/semantic-outcome decisions
in focused ADR(s);

implement versioned strict contracts;

implement the minimal private request/authentication seam;

preserve Phase 1 behavior and serialized history.
```

This stage should establish shared capabilities required by:

```text
REN
ESIOS
ENTSO-E
Open-Meteo
```

without implementing any of those providers yet.

---

# 3. Critical scope boundary

Do NOT implement:

- REN adapter/parser;
- ESIOS adapter/parser;
- ENTSO-E adapter/parser;
- Open-Meteo adapter/parser;
- MIBGAS;
- provider fixtures except synthetic shared-contract/security fixtures where genuinely required;
- provider live-smoke commands;
- provider catalogue harvesting;
- provider-specific live access;
- provider-specific source parsing;
- Snowflake;
- dbt;
- feature engineering;
- ML;
- model registry;
- inference;
- API;
- dashboard;
- scheduler;
- deployment;
- Kafka;
- Kubernetes.

Stage 1 is shared foundation only.

---

# 4. Network restriction

This Stage 1 implementation must be completely offline.

Do not:

- contact REN;
- contact ESIOS;
- contact ENTSO-E;
- contact Open-Meteo;
- perform provider DNS lookup;
- download schemas or fixtures;
- validate credentials against providers;
- use curl/wget against external systems;
- browse provider APIs from repository code;
- activate paid resources.

The readiness assessment already performed source verification.

Provider live validation belongs to Stage 8.

---

# 5. Repository context

Read the existing implementation before designing extensions:

```text
AGENTS.md
README.md

docs/architecture/README.md
docs/adr/
docs/runbooks/ingestion.md

docs/codex/reports/phase_1_stage_7_final_acceptance.md
docs/codex/reports/phase_2_readiness_assessment.md

pyproject.toml
.env.example

src/iberian_shakti/config.py
src/iberian_shakti/common/
src/iberian_shakti/contracts/
src/iberian_shakti/ingestion/
src/iberian_shakti/ingestion/omie/

tests/contracts/
tests/unit/ingestion/
tests/integration/
tests/conftest.py
```

Trace actual Phase 1 serialization, archive, replay and parsing behavior before changing shared contracts.

Do not infer compatibility from names alone.

---

# 6. Preserve Phase 1

The Phase 1 implementation is accepted production-quality project history.

Stage 1 must preserve:

```text
OMIE exact-revision behavior
OMIE latest-observed behavior
MarketPrice
existing serialized request/retrieval/parse provenance
immutable archive paths
SHA-256 content identity
offline replay
retry behavior
HTTP raw-byte behavior
logging/redaction
default-offline pytest
live-smoke authorization
existing fixtures and hashes
```

Do not rewrite Phase 1 history.

Do not migrate old archive metadata destructively.

Do not change existing OMIE behavior merely to make the new abstraction cleaner.

Backward compatibility is a Stage 1 acceptance requirement.

---

# 7. ADRs before implementation

Create focused ADR(s) **before** the corresponding code.

Inspect existing ADR numbering and use the next sequential numbers.

Prefer a small number of focused ADRs rather than one giant document.

At minimum the accepted decisions must cover:

## ADR topic A — Multi-source query and normalized measurement contracts

Record:

- API-query identity;
- query-window semantics;
- provider product/dataset identity;
- geography/domain identity;
- API snapshot semantics;
- actual vs forecast vs reanalysis;
- source issue/publication/update/acquisition times;
- normalized system measurements;
- normalized weather measurements;
- units/numeric representation;
- schema-family versioning;
- backward compatibility with `MarketPrice`.

## ADR topic B — Private authentication/request construction and semantic provider outcomes

Record:

- private credential injection boundary;
- ESIOS header authentication;
- ENTSO-E private query-token mechanism;
- secret-free serialized query identity;
- safe locators;
- authentication/authorization outcome semantics;
- provider semantic errors/no-data;
- raw-body archival ordering;
- safe logging/redaction;
- existing retry/transport invariants.

If repository conventions support combining these cleanly into fewer ADRs, explain why.

Do not alter ADR 0001 or ADR 0002 unless a genuine factual correction is required.

Normally they should remain unchanged.

Update the ADR index if one exists.

---

# 8. Shared query contract

The Phase 1 `SourceRequest` is OMIE-oriented:

- one delivery day;
- numeric revision semantics.

Do not force new APIs into fake OMIE revision semantics.

Implement a strict, immutable, provider-neutral query representation for Phase 2 API acquisitions.

It must be capable of representing, as applicable:

```text
provider/source
report/product/dataset
requested UTC window
provider area/domain role
series/indicator/product identity
variables
location/site identity
requested coordinates
model identity
safe selection/snapshot semantics
```

Requirements:

- strict validation;
- immutable/frozen;
- deterministic serialization;
- no `dict[str, Any]` escape hatch;
- no secret values;
- no credential-bearing URL;
- no Authorization header;
- no ENTSO-E token;
- bounded strings/collections;
- explicit UTC-aware times where applicable.

Do not require every provider to populate irrelevant fields.

Prefer typed discriminated structures or small composable value objects over a giant optional-field bag.

Preserve the existing OMIE request representation unless a backward-compatible shared abstraction genuinely improves it.

---

# 9. API snapshot semantics

Phase 2 APIs may return changing content without numeric provider revision numbers.

Introduce explicit semantics for API acquisition snapshots.

Do not:

- fabricate revision `1`;
- fabricate `"latest"`;
- treat retrieval time as provider revision;
- collapse changed bytes under the same query.

Preserve:

```text
same query + same bytes
→ same content identity
→ independent acquisition event

same query + changed bytes
→ different content identity
→ both versions retained
```

Provider-native revision/document IDs, when later available, should remain optional native metadata.

---

# 10. Shared normalized system measurement contracts

Implement a coherent typed normalized system-measurement family sufficient for later:

```text
load actual
load forecast
generation actual
generation forecast
interchange
```

Do not implement provider mappings yet.

The contracts must be able to express:

- source;
- report/product;
- measure type;
- actual/forecast distinction;
- technology where applicable;
- direction where applicable;
- geographic identity;
- valid instant OR delivery interval;
- source cadence;
- explicit unit;
- finite value;
- optional issue time;
- optional publication/update time;
- native series/document identifier;
- provenance/parse-event linkage.

Use direct Decimal parsing for system/energy quantities.

Do not permit binary float intermediates for:

```text
MW
MWh
EUR/MWh
```

Do not confuse:

```text
MW ≠ MWh
```

Do not derive renewable totals, country totals or feature values in this phase.

---

# 11. Shared normalized weather contracts

Implement a separate coherent weather-measurement family.

It must support later Open-Meteo:

```text
temperature_2m
wind_speed_10m
shortwave_radiation
```

without hard-coding Open-Meteo itself into generic contracts.

Represent:

- source/product/model;
- actual/reanalysis/forecast kind;
- project site identity;
- requested coordinates;
- returned-grid coordinates where available;
- elevation where available;
- variable;
- measurement height/statistic where applicable;
- valid instant OR support interval;
- explicit unit;
- finite scientific value;
- optional model-run/issue time;
- provenance linkage.

Scientific weather values may use finite float under explicit validation policy.

Do not convert weather values into Decimal simply for uniformity.

Do not perform:

- interpolation;
- national aggregation;
- resampling;
- weather-to-generation conversion;
- feature engineering.

---

# 12. Geography contracts

Introduce the smallest typed geographic representation needed to prevent semantic conflation.

The shared model must be able to distinguish concepts such as:

```text
country
mainland/system perimeter
bidding zone
control area
provider-native area
EIC domain
coordinate/site
directed border endpoint
aggregate external boundary
```

Do not assume:

```text
country == bidding zone == control area
```

Retain provider-native IDs separately from normalized/project identity.

Do not hard-code the full provider catalogues in Stage 1.

---

# 13. Time semantics

Normalized instants must remain timezone-aware UTC.

Normalized intervals must remain:

```text
[start, end)
```

with positive duration.

The contracts must distinguish:

```text
valid/observation time
delivery interval
forecast issue/model-run time
publication/update time
acquisition time
```

Unknown provider timestamps remain null/unknown.

Never substitute:

```text
retrieved_at
```

for:

```text
forecast issue time
```

or:

```text
provider publication time
```

Stage 1 must provide the shared structure for these distinctions but must not guess REN/ESIOS/ENTSO-E/Open-Meteo semantics.

---

# 14. Forecast editions and revision semantics

Support:

```text
actual
forecast
reanalysis
```

as explicit typed meaning.

For forecasts, permit:

- known issue/model-run edition;
- unknown issue edition;
- multiple acquisitions of the same target;
- multiple known forecast editions for the same target.

Do not collapse historical refetches into one value.

Do not assert information was known at an earlier forecasting cutoff unless the source actually supplies that evidence.

---

# 15. Schema-family versioning

The current Phase 1 schema-version mechanism is market-price specific.

Extend versioning conservatively so future parsers can identify:

```text
market price schema
system measurement schema
weather measurement schema
```

Requirements:

- explicit schema family;
- explicit schema version;
- deterministic serialization;
- strict validation;
- Phase 1 metadata remains readable.

Do not rewrite previously persisted metadata.

Do not make every old archive event require a new field that it never contained.

Add compatibility tests using existing Phase 1 representations.

---

# 16. Parse result generalization

The current parser result is oriented around `MarketPrice`.

Generalize the normalized-record boundary sufficiently to support:

```text
MarketPrice
SystemMeasurement
WeatherMeasurement
```

while keeping it:

- typed;
- immutable;
- strict;
- statically checkable;
- deterministic.

Do not use:

```python
tuple[object, ...]
```

or:

```python
dict[str, Any]
```

as the normalization abstraction.

Prefer a closed union / generic typed structure consistent with the repository architecture.

Existing OMIE parser behavior must remain unchanged.

---

# 17. Semantic provider outcomes

Add the minimum shared typed outcome vocabulary required for future APIs.

The existing Phase 1 behavior should remain valid.

Stage 1 should support future distinctions such as:

```text
successful data
source unavailable / no data
authentication failure
authorization failure
rate limited
provider rejected request
unsupported domain/profile
schema/profile unsupported
time semantics unknown
content invalid
```

Do not implement provider-specific classification yet except generic shared structure/tests.

Important:

An HTTP 200 provider acknowledgement/error document must be capable of being represented as:

```text
retrieval succeeded
+
semantic parse/provider outcome failed or unavailable
+
zero normalized records
```

Do not falsify it into HTTP 404.

Do not weaken OMIE's existing positive-record success behavior.

---

# 18. Private authentication/request seam

Extend the shared HTTP acquisition boundary minimally so later providers can add private request material without exposing it to persistence/logging.

It must support future:

```text
ESIOS:
x-api-key header

ENTSO-E:
securityToken private query parameter
```

while retaining:

```text
fixed provider HTTPS origin
GET
TLS verification
trust_env=False
zero redirects
Accept-Encoding: identity
existing retry engine
raw-byte streaming
```

The private auth material must exist only at the transport/request-construction boundary.

It must NOT appear in:

- `SourceRequest`;
- API query serialization;
- `ResolvedSource`;
- safe locator;
- archive reference;
- retrieval provenance;
- parse provenance;
- JSON logs;
- CLI summaries;
- exception messages emitted to operators;
- fixture metadata.

Do not implement token refresh.

Do not implement account login.

Do not implement provider registration.

---

# 19. Credential configuration

The readiness assessment identifies the existing environment names:

```text
ESIOS_API_TOKEN
ENTSOE_API_TOKEN
```

Inspect `.env.example` and existing configuration before changing anything.

Do not invent duplicate prefixed variable names if these names are already authoritative.

Implement the minimum validated selected-provider secret configuration necessary for future private injection.

Requirements:

- no automatic `.env` loading;
- no import-time environment read;
- no global requirement for both credentials;
- OMIE, REN and Open-Meteo must remain usable without these credentials;
- missing credential should fail before provider I/O when that selected provider later requires it;
- secret values must not appear in Pydantic validation messages or repr output.

Do not require real credentials in tests.

Use synthetic secrets only.

---

# 20. Safe request identity

Separate:

```text
private transport request
```

from:

```text
safe persisted query identity
```

For example, ENTSO-E may later send a token in a query parameter.

The persisted/logged query identity must exclude that token entirely.

Never redact a private URL and then treat the redacted URL as the original transport request.

The transport request and safe provenance identity are different objects with different responsibilities.

---

# 21. Secret-response safety

Create shared protection for the future pathological case where a provider echoes a credential in a response/error.

Do not silently redact the bytes and archive them as though they were original.

The shared design should permit a controlled sensitive-response failure:

```text
safe publication rejected
+
nonsecret diagnostic metadata
+
no secret-bearing normal archive payload
```

Test this using synthetic credentials and synthetic response content.

Do not log the response body.

Keep the design narrow; do not build a general DLP system.

---

# 22. Retry and transport compatibility

Do not redesign the Phase 1 retry engine.

Retain by default:

```text
maximum attempts: 3
backoff: bounded exponential
finite phase timeouts
finite attempt budget
finite operation budget
zero redirects
zero underlying transport retries
```

Stage 1 may extend controlled error taxonomy needed by future authentication/rate-limit/semantic failures.

Do not add provider-specific retry behavior yet.

Do not add aggressive polling.

---

# 23. Archive compatibility

The Phase 2 assessment explicitly does **not** require an archive backend rewrite.

Preserve the content-addressed immutable payload model.

Stage 1 may add query metadata/version fields only where required and backward-compatible.

Confirm existing Phase 1 objects still:

- serialize;
- deserialize;
- validate;
- load;
- replay.

Do not migrate old files.

Do not change existing payload paths unless a genuine accepted requirement makes it unavoidable.

If an archive compatibility issue is discovered, stop and explain before introducing a migration.

---

# 24. Replay compatibility

Existing Phase 1 replay must continue working unchanged.

Add tests proving old:

```text
OMIE archived content
retrieval provenance
parse provenance
MarketPrice normalization
```

remain valid after Stage 1 extensions.

Future Phase 2 records must be designed so replay will require only:

```text
archived bytes
+
original acquisition metadata
+
local versioned catalogue/schema
```

No parser should require live network lookup.

Do not implement provider catalogues yet.

---

# 25. Logging and redaction

Extend existing safe logging only if required for new shared outcome/query/auth concepts.

Retain the Phase 1 closed allowlist philosophy.

Add synthetic-secret tests covering at least:

- header credential;
- query credential;
- configuration value;
- URL with token-like parameter;
- exception containing synthetic token;
- validation failure containing synthetic token;
- provider response echo containing synthetic token.

No raw HTTP body should enter normal logs.

Do not enable HTTPX/httpcore debug logging.

---

# 26. Dependency rule

Strong preference:

```text
NO NEW RUNTIME DEPENDENCY
```

Reuse:

- Pydantic;
- HTTPX;
- stdlib;
- existing project utilities.

Stage 1 should not add:

- pandas;
- requests;
- entsoe-py;
- Open-Meteo SDK;
- dotenv;
- retry libraries;
- XML libraries;
- async frameworks.

XML-security dependency evaluation belongs to the ENTSO-E implementation stage, when the concrete parser boundary exists.

---

# 27. Tests required

Add focused Stage 1 tests covering at minimum:

## Contracts

- strict/frozen query structures;
- invalid/naive timestamps rejected;
- deterministic serialization;
- secret fields impossible to serialize into safe query objects;
- system measurement validity;
- weather measurement validity;
- geography distinctions;
- units;
- finite numeric checks;
- forecast/actual/reanalysis distinctions;
- issue/publication/update null semantics;
- forecast editions;
- schema family/version;
- normalized-record union.

## Compatibility

- existing MarketPrice unchanged;
- existing SourceRequest unchanged where possible;
- existing retrieval provenance JSON still loads;
- existing parse provenance JSON still loads;
- old archive events remain readable;
- existing replay works;
- OMIE parser outputs remain identical.

## Private request/auth seam

Use only synthetic secrets.

Test:

```text
private header injection
private query injection
safe query/provenance excludes secrets
logs exclude secrets
exceptions exclude secrets
validation errors exclude secrets
```

## Semantic outcomes

Test:

- successful data;
- no-data/provider-unavailable;
- auth failure;
- authorization failure;
- rate limit;
- provider rejection;
- schema unsupported;
- time semantics unknown;
- content invalid.

Do not test real provider responses yet.

---

# 28. Repository-wide offline guard

The existing pytest network denial must remain authoritative.

Do not add a bypass.

Ensure any new request-construction paths remain testable through injected/fake transport boundaries.

Run at least one focused test proving the new private request seam does not require real network access.

Normal:

```bash
python -m pytest
```

must remain fully offline and credential-free.

---

# 29. Phase 2 acceptance criteria primarily addressed by Stage 1

Stage 1 should establish concrete evidence toward at least the following authoritative Phase 2 criteria:

```text
1
9
10
11
12
13
14
16
17
18
19
20
24
25
26
27
30
31
32
33
36
37
42
43
```

Do not falsely mark provider-dependent portions complete.

For example:

- criterion 18 can establish configuration and private-injection design now, but provider authentication success remains later;
- criterion 32 can establish replay architecture compatibility now, but each provider's actual replay remains later;
- criterion 20 can preserve shared transport budgets now, while provider-specific invocation caps remain later.

The Stage 1 report must distinguish:

```text
fully satisfied by Stage 1
partially established / later provider evidence required
not applicable to Stage 1
```

Do not alter the original criterion wording.

---

# 30. Documentation updates

Update only documentation necessary for Stage 1.

Expected documentation may include:

```text
docs/adr/<new ADRs>
docs/adr/README.md
docs/codex/prompts/phase_2/README.md
docs/codex/prompts/phase_2/phase_2_stage_1_shared_extensions.md
docs/codex/reports/phase_2_stage_1_report.md
```

Update root/architecture/runbook documentation only if Stage 1 introduces a current-facing statement that would otherwise become false.

Do not prematurely document REN/ESIOS/ENTSO-E/Open-Meteo as implemented.

Phase status remains:

```text
Phase 2 — in progress
```

not CLOSED/PASS.

---

# 31. Required Stage 1 report

Create:

```text
docs/codex/reports/phase_2_stage_1_report.md
```

Use this structure.

## A. Objective

Describe Stage 1 shared-foundation scope.

## B. Baseline

Record:

- branch;
- initial HEAD;
- origin/main relationship as locally known;
- initial working-tree state;
- Python version/environment.

Do not fetch solely for the report.

## C. Authoritative inputs

Identify:

- Phase 2 readiness assessment;
- Phase 1 ADRs;
- Phase 1 closure;
- existing architecture/runbook.

## D. ADR decisions

List new ADRs and exact accepted decisions.

## E. Query/snapshot contracts

Explain the new query identity and why it does not misuse OMIE revision semantics.

## F. Normalized record model

Explain:

- MarketPrice compatibility;
- system measurements;
- weather measurements;
- geography;
- units;
- timing;
- actual/forecast/reanalysis.

## G. Schema/version strategy

Explain compatibility with historical Phase 1 metadata.

## H. Authentication/request boundary

Explain private-vs-safe request separation.

Explicitly prove secret material is not persisted.

## I. Semantic outcomes

Document the shared typed outcome extensions.

## J. Archive/replay compatibility

Document what remained unchanged and test evidence.

## K. Security/redaction

Document synthetic-secret cases.

## L. Tests added

Give exact focused test counts and what they prove.

## M. Full validation

Record final exact results for:

```text
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
pre-commit
```

## N. Phase 2 acceptance traceability

For the criterion numbers listed in §29, classify each:

```text
SATISFIED
PARTIALLY ESTABLISHED — LATER EVIDENCE REQUIRED
NOT YET APPLICABLE
```

Do not mark provider-live evidence satisfied.

## O. Files changed

Account for every path.

## P. Remaining Stage 1 limitations

List only genuine limitations.

## Q. Stage verdict

Use exactly one:

```text
PASS
PASS WITH GAPS
FAIL
```

Stage 1 should normally be `PASS` only if all Stage 1 implementation requirements are complete and the full repository remains green.

## R. Next stage

State only:

```text
Phase 2 Stage 2 — REN integration
```

Do not implement Stage 2.

---

# 32. Implementation style

Follow existing repository conventions.

Prefer:

- explicit types;
- small immutable value objects;
- bounded enums/Literals;
- narrow protocols;
- dependency injection;
- deterministic serialization;
- closed unions.

Avoid:

- generic plugin framework;
- abstract factory layers without concrete need;
- dynamic provider registry;
- giant optional models;
- arbitrary dictionaries;
- provider-name string branching throughout shared code;
- async conversion;
- microservices.

This stage should make later provider implementations simpler, not create a framework project.

---

# 33. Validation workflow

After implementation, run focused tests first.

Then run:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
```

All normal tests must remain offline.

Also run applicable pre-commit hooks against every changed path:

```bash
pre-commit run --files <all changed paths>
```

If hooks mutate files:

1. inspect the changes;
2. rerun relevant tests/checks;
3. ensure nothing is silently altered.

Do not rely solely on test count.

Review warnings and resource errors as well.

---

# 34. Git review

Inspect:

```bash
git status --short
git diff --stat
git diff
git diff --cached --stat
git diff --cached
```

Review all new files explicitly because untracked files may not appear in normal diff output.

No temporary scripts, caches, provider payloads or secrets may remain in the repository.

---

# 35. No live/provider data in Git

Do not add any readiness-assessment `/tmp` observations to Git.

Do not add:

```text
REN live response
Open-Meteo live response
ESIOS token
ENTSO-E token
provider private URLs
provider headers
```

Stage 1 fixtures should be synthetic shared-contract/security fixtures only if required.

Provider-specific fixture acquisition belongs to later provider stages and must respect rights/licensing decisions.

---

# 36. No commit/push/branch

Do not:

```text
git commit
git push
git switch -c
git checkout -b
```

Work on existing `main`.

Leave all Stage 1 changes for operator review.

Do not stage files unless a tool absolutely requires it; prefer:

```text
pre-commit run --files ...
```

The operator will decide when to commit.

---

# 37. Stage 1 stop condition

Do not start REN implementation after Stage 1 passes.

End this task after:

```text
shared contracts implemented
ADRs completed
private auth seam implemented
semantic outcomes implemented
compatibility verified
full offline suite green
Stage 1 report complete
prompt stored
```

Then stop.

---

# 38. Final response

Return a concise summary containing:

1. initial baseline;
2. prompt folder/files created;
3. ADRs created;
4. shared contracts added/changed;
5. query/snapshot model;
6. normalized system/weather model;
7. schema/version compatibility strategy;
8. authentication/request seam;
9. semantic outcomes added;
10. security/redaction coverage;
11. focused tests added and passing;
12. final full pytest count;
13. Ruff result;
14. mypy result;
15. pre-commit result;
16. Phase 1 regression status;
17. Stage 1 report path;
18. Stage 1 verdict;
19. Git status;
20. next stage.

Do not commit.

Do not push.

Do not begin REN implementation.

End with:

```text
Next authorized implementation stage:
Phase 2 Stage 2 — REN integration
```
