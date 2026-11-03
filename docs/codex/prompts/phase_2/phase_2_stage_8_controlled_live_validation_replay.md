# Iberian_Shakti — Phase 2 Stage 8
## Controlled Live Provider Validation and Network-Denied Replay

Execute **Phase 2 Stage 8 — Controlled Live Validation and Replay**.

Stage 7 has passed its final offline pre-live engineering audit.

Authoritative clean baseline:

```text
branch:
main

working tree:
clean

HEAD:
17d1e19 test: complete Phase 2 pre-live engineering audit
```

Committed history includes:

```text
17d1e19 test: complete Phase 2 pre-live engineering audit
c3476f1 test: complete Phase 2 cross-source integration hardening
77ff8e2 feat: complete Phase 2 Open-Meteo ingestion
f8dee4c feat: complete Phase 2 ENTSO-E ingestion
8ef31ef feat: complete Phase 2 ESIOS ingestion
09792e9 feat: complete Phase 2 REN ingestion
8a377dd feat: establish Phase 2 multi-source foundation
70f4204 docs: record Phase 2 readiness assessment
```

Local `main` is intentionally ahead of `origin/main` by 10 commits.

Do **not push**.

This prompt explicitly authorizes the bounded Stage 8 live-provider validation described below.

It does **not** authorize broader network exploration, provider discovery, quota probing, historical bulk downloads, cloud resources or Stage 9.

---

# 1. Stage 8 purpose

Stage 8 must validate the accepted Phase 2 ingestion implementation against real provider responses while preserving all engineering controls established in Stages 1–7.

Required live providers/products:

```text
REN
→ ElectricityProductionBreakdownDaily

ESIOS
→ indicator 544, Demanda prevista Peninsular

ENTSO-E
→ ES actual total load A65/A16
→ PT day-ahead wind/solar forecast A69/A01
→ ES day-ahead wind/solar forecast A69/A01

Open-Meteo
→ ERA5 Historical Weather
→ DWD ICON-EU forecast, models=icon_eu
```

The required minimum live data plan is therefore:

```text
1 REN request
1 ESIOS data request
3 ENTSO-E requests
1 ERA5 request
1 ICON-EU request

= 7 required logical data requests
```

At most:

```text
+ 1 ESIOS metadata request
```

may be made, and only if genuinely required to validate metadata that the normal 544 response cannot establish.

No other provider request is authorized.

---

# 2. OMIE is not part of the Stage 8 request plan

Do **not** make a new OMIE request by default.

Phase 1 already performed controlled OMIE live validation.

Stage 8 may rely on that accepted evidence plus current offline regressions.

Do not spend a live request repeating OMIE unless a new Stage 8 defect specifically requires it and the operator separately authorizes it.

---

# 3. Mandatory initial checks

Start with:

```bash
git status --short
git log --oneline --decorate -12
```

Require:

```text
branch = main
HEAD = 17d1e19
working tree = clean
```

If not:

```text
STOP
```

Do not alter Git state to satisfy the requirement.

Also verify committed Stage 7 report concludes:

```text
Phase 2 Stage 7 — PASS.
```

---

# 4. Git restrictions

During Stage 8 do not:

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

Leave Stage 8 code/report changes unstaged for operator review.

Do not synchronize with origin.

---

# 5. Save this prompt first

Before any implementation or network access, save this exact prompt as:

```text
docs/codex/prompts/phase_2/
phase_2_stage_8_controlled_live_validation_replay.md
```

No provider request may occur before the prompt is saved.

---

# 6. Read authoritative evidence before network access

Read:

```text
AGENTS.md

docs/codex/reports/phase_2_readiness_assessment.md

docs/codex/reports/phase_2_stage_2_ren_report.md
docs/codex/reports/phase_2_stage_3_esios_report.md
docs/codex/reports/phase_2_stage_4_entsoe_report.md
docs/codex/reports/phase_2_stage_5_open_meteo_report.md
docs/codex/reports/phase_2_stage_5_forecast_model_selection.md
docs/codex/reports/phase_2_stage_6_cross_source_integration_hardening_report.md
docs/codex/reports/phase_2_stage_7_pre_live_engineering_audit_report.md
```

Also inspect the actual provider adapters, request builders, parsers, archive, replay and Stage 7 security controls.

Do not reopen source/model selection.

---

# 7. Stage 7 defects are part of the baseline

Preserve the Stage 7 fixes:

```text
encoded active-credential echoes cannot be archived

OMIE direct parsing/replay enforces independent 4 MiB body cap
```

Do not weaken them for live compatibility.

---

# 8. Explicit live opt-in mechanism

Before making provider requests, implement or reuse a dedicated Phase 2 live-validation entry point.

Follow repository conventions rather than inventing an unrelated framework.

The live entry point must:

```text
require explicit --live

refuse before HTTP/client construction without --live

reject tests/data or fixture archive roots

reject ambiguous/default fixture destinations

perform all local preflight before network access

execute requests sequentially

enforce whole-run budgets

record safe request/attempt/byte/time accounting

write live raw evidence only to an operator/live archive root

never write provider payloads into tests/fixtures
```

A plan/dry-run mode may be added if useful, but default execution without `--live` must remain network-free.

---

# 9. This prompt is the operator authorization

This prompt authorizes the bounded Stage 8 plan.

Do not ask for another confirmation before executing the authorized seven-request plan.

However, if mandatory credentials are absent or the whole-run safety controls cannot be established:

```text
STOP BEFORE NETWORK ACCESS
```

and report the blocker.

---

# 10. Credential preflight

Before **any** provider request, verify only the presence/configuration validity required by existing code for:

```text
ESIOS_API_TOKEN
ENTSOE_API_TOKEN
```

Do not:

```text
print them
log them
inspect their semantic contents
send test/probe requests
paste them into files
persist them
```

Do not perform an invalid-key test.

Do not intentionally trigger authentication failures.

If either required credential is missing or fails existing local configuration validation:

```text
Phase 2 Stage 8 — BLOCKED
```

Stop before making any network request.

Anonymous providers must remain credential-free.

---

# 11. No credential probing

A real ESIOS or ENTSO-E request using the configured credential is allowed because it is part of the required product validation.

Separate credential probes are not allowed.

If a normal required request returns:

```text
401
403
```

treat it as real live evidence.

Do not retry beyond the accepted provider policy.

Do not mutate the credential.

Do not try alternate credential formats.

Do not query account/quota endpoints.

---

# 12. Whole-run hard limits

Stage 8 must enforce whole-run limits in addition to per-request limits.

Hard maximum:

```text
wall-clock runtime:
15 minutes

aggregate attempted response-body bytes:
32 MiB

required logical data requests:
7

optional ESIOS metadata requests:
maximum 1

logical requests maximum:
8
```

Per-provider retry policy remains the accepted production policy.

The whole-run mechanism must count **attempted bytes across retries**, not merely archived successful payloads.

Do not claim a whole-run 32 MiB cap if only successful bodies are counted.

---

# 13. Attempt ceiling

The existing default is at most three attempts per acquisition.

Therefore the absolute theoretical HTTP attempt ceiling for:

```text
8 logical requests × 3 attempts
```

is:

```text
24 HTTP attempts
```

Do not exceed this.

Provider-specific terminal behavior remains binding, especially:

```text
ENTSO-E 429
→ terminal
```

Retries count toward:

```text
attempt total
elapsed time
aggregate attempted bytes
```

---

# 14. Caller pacing

Read the authoritative readiness §Q and apply any exact pacing requirement documented there.

If §Q contains no exact numeric inter-request delay, use a simple conservative fixed sequential pacing policy and document the chosen value as a Stage 8 execution-safety choice.

Do not use:

```text
concurrency
parallel provider calls
polling
rapid repeated requests
```

---

# 15. Budget exhaustion behavior

If any whole-run budget would be exceeded:

```text
stop before the next network operation
```

Do not partially disable accounting.

Do not increase the budget automatically.

Preserve all evidence already acquired.

Report:

```text
budget exhausted
request count
attempt count
attempted bytes
elapsed time
remaining unexecuted planned requests
```

---

# 16. Live archive root

Use a dedicated local Stage 8 archive root consistent with repository archive conventions.

It must **not** be:

```text
tests/data/
a fixture archive
a committed fixture directory
```

Do not commit live raw provider payloads.

The archive must retain:

```text
original bytes
SHA-256
retrieval event
parse event
safe canonical query
provider/product identity
acquisition completion time
```

Use existing `LocalRawArchive`.

Do not create another evidence-storage format.

---

# 17. Run manifest

Create a local Stage 8 run manifest outside test fixtures containing only safe information needed to reproduce/replay the run.

Include:

```text
run ID

start/end UTC

source/product

logical request number

attempt count

safe canonical query identity/hash

raw archive reference

SHA-256

byte count

retrieval UUID

parse UUID

normalized record count

outcome category

replay status

whole-run cumulative request/attempt/byte counters
```

Do not persist:

```text
tokens
private headers
private credential query parameters
unchecked provider prose
raw bodies
```

in the manifest.

---

# 18. Fixed completed-day live date

Use one fixed completed historical date for the completed-day providers:

```text
2026-10-24
```

This is an ordinary pre-DST-transition day already exercised extensively offline.

Use this date for:

```text
REN

ESIOS 544

ENTSO-E ES actual load

ENTSO-E PT renewable forecast

ENTSO-E ES renewable forecast

ERA5
```

Do not search dates if this provider date is unavailable.

Do not automatically advance/backtrack dates.

If the selected date is unavailable for a required provider:

```text
record the live gap
```

and continue only if doing so remains safe and within the authorized plan.

No date-scanning loop is permitted.

---

# 19. ICON-EU live date

For ICON-EU, use the actual **next UTC day** at execution time, according to the production Stage 5 policy.

At the current expected execution date of 2026-11-03 this should ordinarily be:

```text
2026-11-04 UTC
```

but derive it from the actual execution clock rather than hard-coding a stale value.

Record the exact selected forecast target date.

Do not manipulate the production clock merely to obtain a preferred date.

---

# 20. Weather live site

For the minimal Stage 8 live plan, use exactly one representative configured site for each Open-Meteo product:

```text
PT.lisbon
38.72, -9.14
```

Use:

```text
ERA5 → PT.lisbon
ICON-EU → PT.lisbon
```

Do not issue all-six-site live smoke requests.

All-six-site behavior is already covered offline.

---

# 21. REN live request

Execute exactly one required REN acquisition for:

```text
ElectricityProductionBreakdownDaily

source day:
2026-10-24

profile/parser:
accepted 0.2.0
```

Use the existing production retrieval/archive/parser path.

Validate the real response against accepted Stage 2 semantics.

Check and record safely:

```text
HTTP/retrieval success

raw bytes archived

hash/reference

actual response byte count

selected array presence

ancillary/unselected arrays where present

ordered period labels

expected ordinary-day source sequencing

selected 11 concepts

record count

units

returned source metadata

parse outcome
```

Do not reinterpret provider-period values.

Do not invent mean/instant semantics.

Do not convert MW to MWh.

---

# 22. REN live semantic boundary

The accepted REN profile remains:

```text
provisional_empirical

Europe/Lisbon

interval_start

provider_period_value
```

A successful real response may validate compatibility with the accepted profile.

It does **not** automatically convert remaining empirical assumptions into provider-authoritative claims unless the response itself contains authoritative information supporting them.

Record any clarification honestly.

Do not rewrite ADR 0006 merely because the request succeeds.

---

# 23. ESIOS live request

Execute one ESIOS data acquisition for:

```text
indicator:
544

Demanda prevista Peninsular

date/window:
2026-10-24 UTC
```

Use:

```text
ESIOS_API_TOKEN
```

through the existing private-request mechanism only.

Validate safely:

```text
authentication succeeds

indicator identity

returned name where supplied

unit where supplied

geography metadata

native geo ID

UTC timestamps

local timestamp consistency where supplied

sampling/cadence

values_updated_at semantics

bounded coverage

record count

raw archive/provenance
```

Do not promote:

```text
values_updated_at
```

to per-value forecast issue time.

---

# 24. Optional ESIOS metadata request

A maximum of **one** additional ESIOS metadata request is authorized only if:

1. the normal 544 data response succeeds;
2. it does not contain enough authoritative metadata to assess the Stage 7 live criterion for name/unit/geography/sampling;
3. an explicit metadata endpoint/path is already known from accepted documentation/code.

Do not:

```text
discover endpoints
search the API
enumerate indicators
query unrelated catalogue entries
```

If the metadata cannot be established with the data response plus the one allowed metadata request:

```text
record a remaining Stage 8 gap
```

---

# 25. ENTSO-E live validation

Execute exactly three independent ENTSO-E product/domain acquisitions for:

```text
1. ES actual total load
   A65 / A16
   ES domain

2. PT day-ahead wind/solar forecast
   A69 / A01
   PT domain

3. ES day-ahead wind/solar forecast
   A69 / A01
   ES domain
```

Use:

```text
2026-10-24
```

with the exact existing UTC query semantics.

Use the existing `ENTSOE_API_TOKEN` private-query mechanism.

---

# 26. ENTSO-E response validation

For each of the three requests, safely verify and report:

```text
authentication/authorization success

namespace/version

document type

process type

business type

aggregation where applicable

domain/EIC identity

createdDateTime presence/context

TimeSeries identity

PSR identity where applicable

Period bounds

resolution

curve type

position handling

actual record count

technology coverage

gaps

absent technologies

raw byte/hash/archive linkage

parse outcome
```

Do not fabricate missing technologies as zero.

Do not fill Period gaps.

---

# 27. ENTSO-E acknowledgements

If a required request naturally returns an ENTSO-E acknowledgement:

```text
archive/parse it according to existing safe semantics
classify using exact accepted mappings
do not keyword-classify prose
do not provoke another error request
```

A no-data/auth/provider-rejected acknowledgement is live evidence but is **not** successful product validation.

Do not change date/domain simply to force success.

---

# 28. ERA5 live request

Execute one real Open-Meteo Historical Weather acquisition for:

```text
site:
PT.lisbon

date:
2026-10-24

model:
era5
```

Request exactly:

```text
temperature_2m
wind_speed_10m
shortwave_radiation

temperature_unit=celsius
wind_speed_unit=ms
timezone=GMT
timeformat=unixtime
```

Validate:

```text
explicit model identity

24 UTC hours

72 normalized measurements

temperature unit/support

wind unit/support

shortwave unit/support

returned latitude

returned longitude

elevation

timezone/offset metadata

raw archive/provenance
```

If ERA5 is unavailable for the chosen fixed date, do not date-search.

---

# 29. ICON-EU live request

Execute exactly one real Open-Meteo Forecast API acquisition for:

```text
site:
PT.lisbon

model:
icon_eu

target:
next UTC day at execution
```

The request must explicitly contain:

```text
models=icon_eu
```

No:

```text
best_match
icon_seamless
icon_global
IFS fallback
```

is permitted.

---

# 30. ICON-EU validation

Validate safely:

```text
24 expected UTC hourly timestamps

72 normalized measurements

temperature_2m

wind_speed_10m

shortwave_radiation

units

requested coordinates

returned grid coordinates

elevation

timezone/offset

actual response model metadata if supplied

response size

raw provenance

parse outcome
```

Temperature and wind remain:

```text
instant
```

Shortwave remains:

```text
preceding-hour mean
[t-1h,t)
```

Do not infer a model run/issue time if the provider does not supply one authoritatively.

---

# 31. ICON-EU grid transition

Record the actually returned:

```text
latitude
longitude
elevation
```

without expecting them to equal synthetic/pre-transition values.

The previously documented post-30-November grid transition remains provider context.

Do not treat changed returned grid metadata as a model-identity change.

Do not modify configured logical site coordinates.

---

# 32. No fallback model

IFS HRES remains:

```text
documentation-only fallback
```

during Stage 8.

Do not make an IFS request.

Do not switch to IFS if ICON-EU fails.

Do not mix weather models.

A failed ICON-EU live validation is a Stage 8 gap, not permission to substitute another model.

---

# 33. No provider searching

Do not perform:

```text
date searches
catalogue enumeration
model enumeration
domain probing
geographic discovery
pagination exploration
availability polling
quota queries
rate-limit experiments
invalid credential experiments
```

Only the explicitly authorized request plan may touch providers.

---

# 34. Natural failures only

Observe errors encountered naturally during the required requests.

Do not intentionally provoke:

```text
401
403
404
429
quota exhaustion
invalid domain
invalid model
oversized body
malformed query
```

Live error testing through deliberate bad requests is not authorized.

Synthetic tests already cover those cases.

---

# 35. Retry behavior

Use existing production retry policy unchanged.

Do not manually repeat a failed logical acquisition after the production retry policy terminates.

A logical request that exhausts its allowed attempts remains one failed Stage 8 validation item.

Record:

```text
logical request
actual attempt count
status/outcome
```

---

# 36. Parser mismatch policy

If a real complete safe response is successfully archived but parsing fails:

1. preserve the raw evidence;
2. inspect the archived response locally;
3. determine whether the failure is:
   - an implementation defect,
   - unsupported provider evolution,
   - genuinely incompatible response;
4. do not immediately refetch.

If the problem is a locally fixable parser/contract defect:

```text
fix it minimally
add a synthetic/permanent regression
replay the SAME archived real bytes
```

Prefer replay over another network request.

Do not spend another logical provider request merely to test a parser fix.

---

# 37. No silent semantic expansion

Do not weaken strict validation merely to accept a real response.

Examples of prohibited fixes:

```text
ignore unknown units
drop malformed rows
sort unordered timestamps silently
fill missing hours
accept another model
accept another area
convert missing technologies to zero
ignore namespace mismatch
ignore wrong geography
guess DST folds
```

If the provider response contradicts the accepted contract and cannot be safely/versionedly reconciled:

```text
record a Stage 8 gap
```

---

# 38. Versioning for real incompatibilities

If real evidence proves a legitimate provider evolution requiring semantic change:

```text
do not overwrite old parser/profile semantics
```

Use a new version only if required.

Preserve:

```text
old raw evidence
old profile/parser
old parse events
new interpretation
```

Do not create a new version for superficial presentation metadata.

---

# 39. Raw evidence review

For every complete safe 200 response:

```text
archive original representation bytes before semantic parsing
```

Verify:

```text
content length
SHA-256
archive path
retrieval UUID
parse UUID
canonical request linkage
```

Do not include raw provider bodies in the Markdown report.

---

# 40. Compression/content encoding

Observe the actual `Content-Encoding`.

Do not change the existing policy merely because a provider returns an unsupported encoding.

If a selected provider returns unsupported nonidentity encoding under current policy:

```text
record the live incompatibility
```

Do not silently hash decoded bytes or introduce ambiguous evidence semantics during the live run.

---

# 41. Safe diagnostics

Run with the repository's managed diagnostic boundary.

Verify no live output/report contains:

```text
ESIOS token
ENTSO-E token
private header
securityToken
unchecked provider error prose
credential-bearing URL
raw provider body
```

If sensitive-response detection triggers:

```text
stop that acquisition safely
```

Do not archive/redact/rewrite the sensitive body.

---

# 42. Whole-run accounting

The Stage 8 runner must produce final accounting:

```text
logical requests planned
logical requests executed
logical requests successful

optional metadata requests used

HTTP attempts

response bytes attempted
response bytes archived

wall-clock duration

retries by provider

budget remaining/consumed
```

Do not infer these numbers from logs manually if the runner can track them explicitly.

---

# 43. Stop conditions

Immediately stop further network requests on any safety/integrity failure such as:

```text
credential leak detection

whole-run budget enforcement failure

archive integrity failure

unsafe origin/redirect behavior

unexpected attempt accounting failure

evidence publication inconsistency

network request outside authorized plan
```

Preserve existing evidence and report the blocker.

A normal provider:

```text
no-data
401
403
5xx exhaustion
schema incompatibility
```

does not necessarily require stopping other planned providers unless continuing would be unsafe.

---

# 44. Replay after live acquisition

After all safe authorized live requests finish, perform replay only from the archived real evidence.

No provider request is permitted during replay.

Replay every successfully archived required acquisition.

For authenticated-provider replay:

```text
credential loading must not be required
```

---

# 45. Network-denied replay proof

The replay validation must explicitly fail if it attempts to:

```text
construct an HTTP provider client
create a retriever
load ESIOS credentials
load ENTSO-E credentials
perform socket/DNS/network activity
```

Use the repository's existing denial/injection techniques rather than trusting replay by inspection alone.

Do not copy live raw payloads into committed fixtures to achieve this.

---

# 46. Replay equality

For every successfully parsed live acquisition, replay must reproduce the accepted business content:

```text
values
units
valid/support times
kind
geography
native identities
product/model identity
query identity
raw linkage
retrieval linkage
```

Only the allowed new parse-event identity/time may differ.

---

# 47. Replay failure

If a live acquisition succeeded initially but cannot replay from archived evidence:

```text
Stage 8 cannot PASS
```

Do not refetch to hide the failure.

Fix a locally detectable replay defect if possible and replay the same evidence.

---

# 48. Real response metadata

Record provider metadata conservatively.

Do not promote:

```text
HTTP Date
retrieval completion
parse time
document creation time
values_updated_at
```

into forecast issue/publication/run times unless the provider contract explicitly defines that semantic.

Unknown source times stay null.

---

# 49. Historical cutoff safety

Stage 8 does not solve historical forecast-vintage reconstruction.

A successful current ICON-EU request means:

```text
forecast available at this acquisition
```

not:

```text
forecast historically available before a past MIBEL auction
```

Likewise ERA5 is reanalysis, not a historical forecast vintage.

Do not implement training cutoff helpers here.

---

# 50. Stage 8 implementation tests

Any Stage 8 live-run controller/budget/manifest code added must have offline tests covering:

```text
no --live → zero network/client construction

missing credential → zero network

fixture archive root rejection

seven-request plan

optional ESIOS metadata limit

logical request cap

HTTP attempt cap

aggregate attempted-byte cap

15-minute wall-clock cap

sequential execution

budget exhaustion

safe manifest serialization

secret exclusion

replay-only path

network-denied replay

provider failure accounting
```

Tests must use synthetic transports only.

---

# 51. Existing regressions

After any Stage 8 code changes, preserve all existing:

```text
Phase 1
Stage 1
Stage 2
Stage 3
Stage 4
Stage 5
Stage 6
Stage 7
```

tests.

Do not weaken security/parser assertions to accommodate live responses.

---

# 52. Stage 8 report

Create:

```text
docs/codex/reports/
phase_2_stage_8_controlled_live_validation_report.md
```

The report must not expose secrets or raw response bodies.

Recommended structure:

```text
1. Executive verdict
2. Baseline and authorization
3. Live safety plan
4. Whole-run budgets
5. Exact request plan
6. Credential preflight
7. REN result
8. ESIOS result
9. ENTSO-E ES-load result
10. ENTSO-E PT-renewables result
11. ENTSO-E ES-renewables result
12. ERA5 result
13. ICON-EU result
14. Provider deviations/incompatibilities
15. Real evidence archive/provenance
16. Network-denied replay
17. Request/attempt/byte/time accounting
18. Code corrections caused by live evidence
19. Regression validation
20. Remaining Stage 9 items
21. Files changed
22. Git status
23. Final verdict
```

---

# 53. Per-request report table

Include a safe table similar to:

```text
Provider/product
Target window/date
Logical request #
Attempts
HTTP/provider outcome
Bytes
Raw SHA-256
Normalized records
Parse result
Replay result
Deviation
```

Do not include private URLs.

For ENTSO-E, do not show the `securityToken` query.

For ESIOS, do not show private headers.

---

# 54. Success criteria — REN

REN is successful only if:

```text
real request succeeds
complete safe body archived
accepted parser handles body
selected source concepts are present as required
records normalize successfully
provenance persists
replay succeeds
```

A transport success with parse failure is not successful live validation.

---

# 55. Success criteria — ESIOS

ESIOS is successful only if:

```text
configured credential authenticates/authorizes
indicator 544 response succeeds
accepted metadata/identity is sufficiently verified
values normalize safely
provenance persists
replay succeeds
```

A 401/403 or incompatible response is not success.

---

# 56. Success criteria — ENTSO-E

Each of the three ENTSO-E paths must succeed independently.

Stage 8 cannot mark ENTSO-E complete if only some product/domain paths succeed.

Required:

```text
ES actual load PASS

PT renewable forecast PASS

ES renewable forecast PASS
```

Each requires successful replay.

---

# 57. Success criteria — Open-Meteo

Both must independently succeed:

```text
ERA5 historical/reanalysis

ICON-EU forecast
```

The API returning HTTP 200 is insufficient if:

```text
model identity
coverage
units
timestamps
grid metadata
strict parsing
```

do not satisfy the accepted product.

---

# 58. Stage 8 PASS

Stage 8 may conclude:

```text
Phase 2 Stage 8 — PASS.
```

only if all seven required live data acquisitions succeed through the implemented production ingestion paths:

```text
REN                     PASS
ESIOS 544               PASS
ENTSO-E ES load         PASS
ENTSO-E PT renewables   PASS
ENTSO-E ES renewables   PASS
ERA5                    PASS
ICON-EU                 PASS
```

and:

```text
all required evidence archived

all required parse/provenance chains persisted

all successful acquisitions replay network-free

whole-run limits respected

no unauthorized request occurred

no credential exposure occurred

all relevant offline regressions pass
```

---

# 59. PASS WITH GAPS

Return:

```text
Phase 2 Stage 8 — PASS WITH GAPS.
```

if the controlled execution remains safe but one or more required live validations cannot be completed because of:

```text
provider unavailability

real authentication/authorization failure

no-data on the fixed authorized date

unsupported real schema/product evolution

required field/metadata absence

live compression incompatibility

forecast availability mismatch

replay failure not locally resolvable

provider-side ambiguity requiring external clarification
```

Identify exactly which criterion/product remains unresolved.

Do not substitute another provider/date/model to obtain PASS.

---

# 60. BLOCKED

Return:

```text
Phase 2 Stage 8 — BLOCKED.
```

without network execution if:

```text
mandatory credentials are absent

working tree/baseline precondition fails

explicit live opt-in cannot be enforced

fixture/archive separation cannot be guaranteed

whole-run request/byte/time budgeting cannot be enforced

another local safety requirement fails before execution
```

---

# 61. Locally fixable defects discovered by real evidence

If a required real response reveals a genuine local implementation defect:

```text
fix minimally
add permanent synthetic regression
replay the already archived live body
rerun focused tests
rerun full suite
```

Do not automatically issue another provider request.

Document:

```text
defect
real evidence that exposed it
code correction
regression
same-body replay result
```

---

# 62. No broad implementation expansion

Do not implement:

```text
Snowflake
dbt
feature engineering
training
model registry
batch inference
API/dashboard
Kubernetes
cloud deployment
historical weather-vintage pipeline
provider monitoring
scheduler
multi-day backfill
```

---

# 63. No Stage 9 work

Do not close Phase 2.

Do not perform final documentation/acceptance reconciliation beyond recording the live evidence needed by Stage 9.

Stage 9 remains separately authorized.

---

# 64. Post-live validation suite

After live acquisition/replay work is complete, run relevant new Stage 8 offline tests plus:

```bash
python -m pytest tests/integration/stage6 -q
python -m pytest
ruff check .
ruff format --check .
mypy src
pre-commit run --all-files
git diff --check
```

Also rerun relevant:

```text
Stage 7 security/audit suite
provider-focused ingestion suites
```

Do not rerun provider live requests as part of pytest.

The default test suite must remain network-denied.

---

# 65. Live evidence must not enter pytest automatically

No test may require:

```text
real internet
real credentials
real live archive
```

to pass.

Do not place the Stage 8 live command in:

```text
pytest
pre-commit
CI
```

The live path remains explicit/operator-only.

---

# 66. Documentation updates

Update README/runbook only if needed to document the durable explicit live-validation mechanism.

Keep changes narrow.

Document clearly:

```text
default offline behavior
explicit --live requirement
credential requirements
live archive separation
whole-run limits
no automatic provider/model fallback
```

Do not describe the project as production-cleared.

---

# 67. Final Git rules

At completion:

```text
do not stage
do not commit
do not push
```

Leave all Stage 8 code/report/document changes unstaged for operator review.

Do not add live raw payloads to Git.

---

# 68. Final response

Return a concise but complete summary including:

1. branch;
2. baseline HEAD;
3. clean-checkpoint confirmation;
4. live runner/entry point added or reused;
5. exact archive root used;
6. credential preflight result without secret values;
7. exact historical validation date;
8. exact ICON-EU target date;
9. planned logical requests;
10. executed logical requests;
11. optional metadata request count;
12. total HTTP attempts;
13. total attempted bytes;
14. total archived bytes;
15. wall-clock duration;
16. REN result;
17. ESIOS result;
18. ENTSO-E ES-load result;
19. ENTSO-E PT-renewables result;
20. ENTSO-E ES-renewables result;
21. ERA5 result;
22. ICON-EU result;
23. real response deviations;
24. locally fixable defects discovered;
25. corrections made;
26. real evidence provenance result;
27. network-denied replay result;
28. Stage 7 security regression result;
29. Stage 6 regression result;
30. provider-focused regression result;
31. full pytest result;
32. Ruff result;
33. format result;
34. mypy result;
35. pre-commit result;
36. `git diff --check` result;
37. remaining live/final-acceptance gaps;
38. exact Git status;
39. confirmation:
    - no unauthorized provider request;
    - no quota/auth probing;
    - no date searching;
    - no model fallback;
    - no paid/cloud action;
    - no branch;
    - no staging;
    - no commit;
    - no push;
    - no Stage 9 work.

If every required live acquisition and replay succeeds, finish exactly with:

```text
Phase 2 Stage 8 — PASS.

The seven authorized live product/domain acquisitions completed
through the implemented Phase 2 ingestion paths within the
approved whole-run request, attempt, byte and time limits.

Real provider bytes, checksums, canonical request identities,
retrieval provenance and parse provenance were preserved in the
dedicated live archive.

All successfully parsed live acquisitions replayed from retained
evidence with network and credential access denied.

No unauthorized provider request, date search, quota probe,
model fallback or bulk download occurred.

Phase 2 Stage 9 has not been started or authorized.
```

If one or more required live items remain unresolved, finish with:

```text
Phase 2 Stage 8 — PASS WITH GAPS.
```

and enumerate the exact product/criterion gaps.

If preflight prevents any safe live execution, finish with:

```text
Phase 2 Stage 8 — BLOCKED.
```

and state the exact pre-network blocker.

Stop there.
