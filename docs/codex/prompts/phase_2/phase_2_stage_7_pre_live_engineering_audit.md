# Iberian_Shakti — Phase 2 Stage 7
## Final Pre-Live Engineering Audit

Perform **Phase 2 Stage 7 — Pre-Live Engineering Audit**.

This stage is the final exhaustive offline engineering review before controlled live-provider validation.

It must determine whether the complete Phase 2 ingestion system is technically ready to proceed to:

```text
Phase 2 Stage 8
Controlled Live Validation and Replay
```

This task is:

```text
READ
AUDIT
TEST
HARDEN IF REQUIRED
DOCUMENT
```

It is **not**:

```text
another readiness assessment
another source-selection study
live-provider validation
Stage 8
Stage 9 final acceptance
Snowflake
dbt
feature engineering
model training
deployment
```

---

# 1. Mandatory clean-checkpoint precondition

Start with:

```bash
git status --short
git log --oneline --decorate -12
```

The accepted Stage 6 report records:

```text
Phase 2 Stage 6 — PASS
```

but Stage 6 originally finished with six unstaged paths.

Stage 7 may begin only if:

```text
branch = main
working tree = clean
Stage 6 has been committed as an accepted checkpoint
```

The Stage 6 commit hash is intentionally not invented here.

Verify that committed HEAD contains:

```text
docs/codex/reports/
phase_2_stage_6_cross_source_integration_hardening_report.md

tests/integration/stage6/
```

and that the report still concludes:

```text
Phase 2 Stage 6 — PASS.
```

If Stage 6 remains uncommitted:

```text
STOP
```

Do not:

```text
stage
commit
stash
reset
restore
```

the operator's Stage 6 work.

Return:

```text
Phase 2 Stage 7 — BLOCKED.

Reason:
The accepted Stage 6 PASS has not yet been preserved as the
required clean committed checkpoint.
```

and stop.

If the precondition passes, continue.

---

# 2. Git rules

During Stage 7 do not:

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

Work from the clean committed `main` checkpoint.

Leave all Stage 7 changes unstaged for operator review.

---

# 3. Save this prompt first

Before implementation or audit changes, save this exact prompt as:

```text
docs/codex/prompts/phase_2/
phase_2_stage_7_pre_live_engineering_audit.md
```

Do not modify previous prompts.

---

# 4. Read authoritative evidence

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
```

Read all Phase 2 ADRs relevant to:

```text
query identity
geography
measurement semantics
provider-period values
weather output identity
authentication/private request handling
archive
provenance
replay
```

Inspect the actual source and tests rather than relying only on reports.

---

# 5. Scope of accepted ingestion system

Audit the complete accepted provider set:

```text
OMIE

REN

ESIOS

ENTSO-E

Open-Meteo ERA5

Open-Meteo ICON-EU
models=icon_eu
```

The audit must preserve all accepted source-specific semantics.

Do not reopen:

```text
REN source selection
ESIOS indicator selection
ENTSO-E product selection
Open-Meteo forecast-model ranking
```

unless a concrete implementation defect proves the accepted contract internally inconsistent.

---

# 6. Stage 7 objective

Stage 7 must answer:

```text
Is every locally detectable defect that could invalidate,
corrupt, leak, misclassify, deadlock, overrun or undermine
controlled live validation removed before Stage 8?
```

Passing tests alone are insufficient.

Perform an explicit engineering audit of:

```text
request construction
identity
authentication
authorization/error handling
timeouts
retries
response bounds
parser security
semantic validation
time handling
DST
units/statistics
geography
archive integrity
provenance
replay
failure isolation
diagnostics
network denial
dependency assumptions
```

---

# 7. No live I/O

Stage 7 is strictly offline.

Do not:

```text
call OMIE
call REN
call ESIOS
call ENTSO-E
call Open-Meteo

probe credentials
refresh tokens
test provider availability
download provider files
query metadata APIs
perform cloud actions
```

Use:

```text
existing synthetic fixtures
existing archived synthetic evidence
source inspection
tests
officially retained repository documentation
```

If a question can only be answered against a real provider:

```text
reserve it for Stage 8
```

Do not guess.

---

# 8. Network-denial audit

Verify the test suite's network-denial mechanism actually protects all provider paths.

Audit for possible bypasses including:

```text
requests
httpx
urllib
socket
provider SDKs
redirects
alternate constructors
direct client use
```

Tests should prove that Stage 7 and the full offline suite cannot accidentally contact providers.

Do not create a second unrelated network-denial framework if the existing guard is sufficient.

If a bypass exists, fix it minimally and add regression coverage.

---

# 9. Request-construction audit

Audit every provider's request builder for deterministic bounded construction.

Verify at minimum:

```text
fixed provider origins
HTTPS where required
bounded windows
explicit product identity
explicit profile identity
explicit area/site identity
explicit model where required
canonical query serialization
safe private credential insertion
```

No provider should permit arbitrary:

```text
host
scheme
path
model
series
area
variable
```

where the accepted product contract is supposed to be fixed.

---

# 10. SSRF / origin-control audit

Inspect all HTTP request construction for:

```text
user-controlled host injection
scheme changes
redirect escape
credential forwarding to another host
path traversal
query-origin confusion
```

Private credentials must only be attached to the accepted fixed origin.

Tests must establish that credentials cannot be redirected or reused against an attacker-controlled origin through supported request paths.

Do not broaden networking capability.

---

# 11. Authentication audit

Audit ESIOS and ENTSO-E authentication seams.

Verify:

```text
missing credentials fail before network

synthetic credentials remain sufficient for offline tests

credential values are absent from canonical public identity

credential values are absent from archive locators

credential values are absent from exceptions

credential values are absent from managed logs

credential values are absent from parse/retrieval metadata
```

Do not read real:

```text
ESIOS_API_TOKEN
ENTSOE_API_TOKEN
```

during audit execution.

---

# 12. Credential echo audit

Explicitly audit existing secret-redaction/echo protections against:

```text
literal credential
quoted credential
URL-encoded credential
JSON-escaped credential
XML character references
header serialization
query serialization
transport debug text
provider response echo
```

Do not claim generic secret detection beyond the patterns actually supported.

If existing tests already prove a case, reuse them.

Add only missing regression coverage.

---

# 13. Retry audit

For every provider, inspect retry classification.

Verify:

```text
transient transport failures
selected transient 5xx
Retry-After handling where supported
terminal auth failures
terminal schema/content failures
terminal unsupported semantic failures
provider-specific rate-limit policy
```

No semantic parser failure should trigger another network call.

No authentication failure should be retried unless explicitly justified by the existing accepted policy.

Document provider differences.

---

# 14. Retry budget arithmetic

Audit exact retry/time-budget arithmetic.

Verify that configured:

```text
attempt count
backoff
phase timeout
attempt timeout
operation timeout
```

cannot exceed the documented finite operation budget.

Test edge cases such as:

```text
timeout on every attempt
Retry-After near upper bound
transport failure during final attempt
body read timeout
```

Do not merely assert constants independently.

Prove the composed operation remains bounded.

---

# 15. Provider-specific retry policy

Preserve accepted differences.

For example:

```text
ENTSO-E 429 remains terminal
```

if that is the accepted contract.

Do not globally normalize rate-limit behavior unless an actual defect exists.

Document why each provider's retry behavior is safe.

---

# 16. Response-size audit

Inspect every transport/parser boundary.

Verify byte limits are applied:

```text
before unbounded parsing/allocation
```

rather than merely after complete uncontrolled reads.

Accepted approximate caps currently include:

```text
OMIE          4 MiB data
REN           1 MiB
ESIOS         2 MiB
ENTSO-E       4 MiB
Open-Meteo    1 MiB
```

plus bounded OMIE discovery.

Verify implementation, not only documentation.

Oversized bodies must never become successful acquisitions.

---

# 17. Partial/interrupted body audit

Verify that:

```text
interrupted response
short/incomplete transport
declared/actual body mismatch where observable
decoder interruption
```

cannot publish a successful acquisition.

Do not discard safely received complete malformed 200 bodies when the accepted design requires archival before parsing.

Transport incompleteness and parser invalidity must remain distinct.

---

# 18. Compression audit

Audit actual compression behavior for every provider.

Do not assume compressed responses are supported merely because an HTTP library may transparently decode them.

Verify:

```text
what bytes are hashed
what bytes are archived
what Content-Encoding values are accepted
what unsupported encoding does
```

Preserve the requirement that archived evidence corresponds to the project's defined original-byte semantics.

If compression is intentionally unsupported:

```text
fail visibly and safely
```

rather than hashing ambiguous transformed bytes.

---

# 19. Parser-security audit — JSON

Audit REN, ESIOS and Open-Meteo JSON boundaries.

Verify finite handling of:

```text
duplicate keys
depth
node count
array length
key count
string length
numeric token length
NaN
Infinity
float overflow
invalid Unicode
invalid UTF-8
booleans masquerading as numbers
large integers/floats
unexpected shapes
```

Malformed input must not:

```text
partially emit records
retry
escape bounds
```

---

# 20. Parser-security audit — XML

Audit ENTSO-E XML processing.

Verify protection against:

```text
DOCTYPE
internal entities
external entities
parameter entities
external resources
processing instructions
unsupported namespaces
unexpected XML versions
unsupported encoding declarations
UTF-16/UTF-32 confusion
NUL bytes
excessive depth
excessive elements
excessive text
excessive attributes
oversized names
```

Confirm Expat/runtime assumptions remain compatible with the current environment.

No XML parser fallback should weaken these rules.

---

# 21. Parser-security audit — OMIE text/HTML discovery

Audit OMIE:

```text
discovery parsing
data-row grammar
revision resolution
archive behavior
```

Verify finite:

```text
anchor/page count
row count
line length
calendar count
revision handling
```

No HTML/script content should become executable or semantically trusted beyond the accepted discovery grammar.

---

# 22. Atomic parsing audit

For every provider prove:

```text
late failure
→ zero normalized records
```

Examples:

```text
last malformed value
last timestamp invalid
wrong late unit
duplicate final record
unsupported final element
```

Do not permit partially successful record collections.

---

# 23. Time-window audit

Inspect every provider's accepted request-window rules.

Verify:

```text
positive windows
bounded maximum duration
whole-minute/hour constraints where applicable
partition-date consistency
provider-specific market-day semantics
```

No request should silently expand beyond its canonical business window.

---

# 24. DST audit

Perform exhaustive regression review around:

```text
spring transition
autumn transition
ordinary day
UTC midnight
local midnight
folds
missing local hours
repeated local hours
```

Cover accepted source semantics:

```text
OMIE Europe/Madrid
REN Europe/Lisbon
ESIOS explicit UTC
ENTSO-E explicit UTC
Open-Meteo UTC
```

Do not enforce equal record counts across providers.

---

# 25. Temporal-support audit

Verify strict compatibility between:

```text
ValidInstant
SupportInterval
```

and:

```text
instant
mean
provider_period_value
```

Invalid combinations must fail construction/validation.

Reconfirm:

```text
shortwave radiation
→ [t−1h,t), mean

temperature/wind
→ ValidInstant(t), instant

REN/ENTSO-E
→ provider_period_value on intervals

ESIOS
→ forecast instant
```

---

# 26. Unit audit

Verify no accepted path can silently:

```text
convert
relabel
coerce
```

between incompatible units.

At minimum:

```text
EUR/MWh
MW
°C
m/s
W/m²
```

must remain distinct.

Do not add conversion infrastructure.

---

# 27. Decimal / float audit

Verify:

```text
market/system financial and power quantities
```

retain their accepted Decimal semantics where required.

Weather floats must remain finite and bounded.

Audit accidental:

```text
Decimal → float
float → Decimal through binary approximation
rounding
clipping
```

on accepted paths.

---

# 28. Geography audit

Reconfirm no code path conflates:

```text
OMIE PT/ES market area

REN Portuguese system perimeter

ESIOS ES.peninsular

ENTSO-E bidding zones

weather logical sites

weather returned grids
```

No equality or deduplication should arise solely from:

```text
same country
same coordinate
same timestamp
same concept
```

---

# 29. Query-identity audit

Audit canonical serialization and hashing.

Verify materially different requests always remain distinct.

Test representative changes in:

```text
provider
report/product
profile
model
area
site
coordinates
selection version
series
window
variables
output selection
```

Verify key-order normalization where appropriate.

Do not alter existing wire/hash compatibility without a demonstrated defect.

---

# 30. Raw-identity audit

Verify raw identity is not assumed to be:

```text
SHA256 alone
```

where provider/report/partition context is part of existing raw identity.

Check identical bytes across:

```text
different providers
different reports
different sites/acquisitions
```

for correct sharing/isolation according to existing archive rules.

No cross-provider overwrite may occur.

---

# 31. Archive path-safety audit

Inspect filesystem archive handling for:

```text
path traversal
unsafe identifiers
separator injection
absolute paths
symlink assumptions
partial write
replace behavior
temporary-file publication
permissions
```

All persisted paths must derive from controlled safe identities.

Do not allow provider strings to become arbitrary filesystem paths.

---

# 32. Immutable publication audit

Verify:

```text
existing raw object cannot be overwritten
```

and that:

```text
same content
changed content
duplicate acquisition
revised acquisition
```

produce the accepted immutable behavior.

Test concurrent/repeated publication behavior if locally meaningful and deterministic.

Do not introduce concurrency solely for this audit.

---

# 33. Persistence-failure audit

For representative providers verify failures at:

```text
raw publication
retrieval-event publication
parse-event publication
```

cannot return successful records.

Previously persisted evidence must remain intact.

No partial metadata chain may be mistaken for complete successful provenance.

---

# 34. Replay-integrity audit

Audit replay for:

```text
raw missing
raw changed
hash mismatch
wrong retrieval linkage
wrong query linkage
missing event
corrupt event
profile mismatch
parser mismatch
```

Replay must:

```text
fail closed
perform zero refetch
perform zero credential loading
perform zero HTTP construction
```

---

# 35. Replay determinism audit

Reconfirm representative replay across all accepted products:

```text
OMIE
REN
ESIOS
ENTSO-E
ERA5
ICON-EU
```

Business values and accepted native semantics must reproduce.

Only explicitly non-business parse-event metadata may change.

---

# 36. Error-taxonomy audit

Review all error boundaries for ambiguity.

Keep distinct where implemented:

```text
ConfigurationError
authentication
authorization
transport
HTTP
source_unavailable/no_data
provider_rejected
schema/content
archive/persistence
replay integrity
```

Do not classify using unrestricted keyword matching.

Provider-specific error semantics may differ.

---

# 37. Diagnostic-safety audit

Run provider failure paths under managed DEBUG logging.

Inspect emitted:

```text
logs
exceptions
structured diagnostics
metadata
```

for:

```text
credentials
private headers
private query values
unchecked provider prose
raw-body leakage
unsafe URLs
```

Synthetic secrets should be distinctive enough to detect accidental echoes.

---

# 38. Exception-safety audit

Review exception chaining and formatting.

Do not expose sensitive causes through:

```text
repr(exception)
nested request objects
HTTP library exception text
```

if those may contain credentials.

Preserve useful controlled failure categories without raw secret-bearing details.

---

# 39. Configuration audit

Audit environment/config loading.

Verify:

```text
missing private settings fail deterministically
anonymous sources need no credential
defaults do not silently select another product
```

In particular:

```text
Open-Meteo ICON-EU must remain icon_eu
```

with no:

```text
best_match
automatic IFS fallback
seamless model
```

---

# 40. Open-Meteo forecast audit

Reconfirm the accepted forecast product:

```text
DWD ICON-EU
models=icon_eu
```

and that:

```text
IFS HRES remains documentation-only fallback
```

No runtime fallback or repair behavior may exist.

Verify forecast target-window policy, acquisition-clock handling and replay-clock behavior cannot accidentally validate unsupported historical/latest combinations.

---

# 41. REN provisional-profile audit

REN 0.2.0 remains an accepted provisional empirical profile.

Audit that:

```text
Europe/Lisbon
interval_start
provider_period_value
92/96/100 sequence
```

remain explicit and cannot accidentally be promoted into stronger claims.

Do not reopen the Stage 2 decision.

Record remaining semantic limitations for Stage 8/future clarification.

---

# 42. ENTSO-E acknowledgement audit

Audit supported acknowledgement handling.

Verify:

```text
known no-data
known auth/domain/provider rejection
unknown reason/code
```

remain correctly separated.

No provider prose containing words such as:

```text
auth
no data
domain
```

may drive classification heuristically.

---

# 43. ESIOS semantics audit

Reconfirm:

```text
indicator 544
ES.peninsular
5-minute forecast samples
ValidInstant
```

and that:

```text
values_updated_at
```

is not promoted to per-value issuance time.

No geographic ID discovered offline should be promoted as authoritative unless already accepted.

---

# 44. Stage 6 integration regression

Run the full Stage 6 suite as part of Stage 7.

All cross-source guarantees must remain green:

```text
identity isolation
geography isolation
time/support coexistence
unit/statistic safety
kind safety
combined replay
failure isolation
revision isolation
bounds
DST
diagnostic safety
```

---

# 45. Dependency/runtime audit

Record exact locally used versions relevant to parser/security behavior, at minimum:

```text
Python
Expat
httpx or request transport dependency
Pydantic
```

where applicable.

Do not upgrade dependencies merely because newer versions exist.

Only change dependencies if a concrete correctness/security incompatibility affecting this project is demonstrated.

---

# 46. Dead-code / unreachable-path audit

Inspect provider implementations for:

```text
unused fallback branches
obsolete model paths
legacy unsafe helper paths
unreachable retry code
test-only assumptions leaking into production
```

Do not perform broad refactoring.

Remove or harden only code that creates an actual pre-live correctness risk.

---

# 47. TODO / FIXME audit

Search relevant ingestion/contracts/archive/replay source for:

```text
TODO
FIXME
HACK
XXX
pass
NotImplemented
temporary
```

Classify each occurrence as:

```text
safe intentional
future-phase item
pre-live blocker
```

Resolve only true Stage 7 blockers.

Document the remainder.

---

# 48. Static search audit

Use targeted repository searches for risky patterns including:

```text
verify=False
timeout=None
requests.get(
httpx.get(
eval(
exec(
pickle.load
yaml.load
shell=True
subprocess
os.system
open(
except Exception
pass
```

Interpret results contextually.

Do not claim a defect solely from a textual match.

---

# 49. Full Phase 2 offline checklist reconciliation

Use the authoritative Phase 2 readiness report's final **44-criterion checklist**.

Create a Stage 7 reconciliation table classifying every criterion as:

```text
OFFLINE SATISFIED
LIVE VALIDATION REQUIRED
FINAL ACCEPTANCE / STAGE 9
NOT APPLICABLE
```

For each item include:

```text
evidence
test/report reference
reason if deferred
```

Do not mark a live-dependent item satisfied from synthetic tests.

Do not close Phase 2 in Stage 7.

---

# 50. Stage 8 entry gate

Create an explicit Stage 8 entry checklist.

At minimum require:

```text
all local regressions green
all parser bounds green
all credential protections green
all retry/time budgets finite
all archive/replay integrity tests green
network-denied suite green
no unresolved locally detectable correctness issue
```

Then list the exact questions that require real provider observations.

---

# 51. Fix policy

If the audit finds a concrete offline defect:

```text
fix it
add a permanent regression test
rerun focused tests
rerun full tests
document defect and correction
```

Do not merely list a locally fixable defect as a Stage 8 question.

Conversely, do not simulate a real-provider answer for something that genuinely requires Stage 8.

---

# 52. No gratuitous refactoring

Stage 7 is not a code-cleanup project.

Do not:

```text
rename large modules
reorganize packages
replace working abstractions
introduce new frameworks
change accepted provider semantics
```

unless necessary to fix a demonstrated pre-live defect.

Prefer minimal patches.

---

# 53. Stage 7 report

Create:

```text
docs/codex/reports/
phase_2_stage_7_pre_live_engineering_audit_report.md
```

Recommended structure:

```text
1. Executive verdict
2. Baseline and scope
3. Audit methodology
4. Network and origin controls
5. Authentication and secret handling
6. Retry/time-budget audit
7. Transport/body/compression audit
8. Parser-security audit
9. Time/DST/support audit
10. Units/statistics/geography audit
11. Query/raw identity audit
12. Archive/persistence audit
13. Replay-integrity audit
14. Error taxonomy and diagnostics
15. Provider-specific findings
16. Stage 6 integration regression
17. Dependency/runtime findings
18. Risk-pattern/TODO audit
19. 44-criterion reconciliation
20. Stage 8 entry gate
21. Validation results
22. Files changed
23. Remaining live-only questions
24. Final verdict
```

---

# 54. Required validation

Run focused Stage 7 tests plus all relevant provider and integration suites.

Then run:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
git diff --check
pre-commit run --all-files
```

Also rerun:

```bash
python -m pytest tests/integration/stage6 -q
```

Do not report any result not actually executed.

---

# 55. Stage 7 PASS criteria

Stage 7 may conclude:

```text
PASS
```

only if:

```text
no unresolved locally detectable correctness defect exists

network denial is effective

origins are fixed/safe

private credentials cannot leak through supported paths

retry/time budgets are finite and compositionally safe

response bodies are bounded

parser complexity is bounded

XML entity/resource attacks remain blocked

JSON malformed-input paths fail atomically

OMIE parsing/discovery remains bounded

time/DST semantics remain correct

units/statistics/geographies remain explicit

query identities remain collision-safe

raw archive remains immutable

persistence failure cannot return success

replay fails closed and never refetches

error taxonomy remains controlled

diagnostics remain safe

Stage 6 integration guarantees remain green

all locally applicable Phase 2 checklist items are satisfied

all focused tests pass

full pytest passes

Ruff passes

format check passes

mypy passes

pre-commit passes

git diff --check passes
```

---

# 56. PASS WITH GAPS

Return:

```text
Phase 2 Stage 7 — PASS WITH GAPS.
```

if a real offline issue remains that prevents controlled live validation.

Examples:

```text
credential leakage
unbounded parser
retry budget violation
network-denial bypass
archive corruption risk
unsafe replay fallback
ambiguous canonical identity
unresolved local DST defect
provider-specific contract inconsistency
failing regression
```

State the exact blocker.

Do not authorize Stage 8 implicitly.

---

# 57. Stage 8 questions are not Stage 7 gaps

The following may remain pending without preventing Stage 7 PASS if they genuinely require provider observation:

```text
real authentication acceptance

real schemas

real current field coverage

real provider timestamps

real error/no-data responses

real rate limits

real revisions/corrections

real response compression

real availability timing

real returned weather grids/elevation

ICON-EU cycle/grid behavior

REN provider-side unresolved semantic refinements

historical forecast publication availability

provider licensing/service-access confirmation
```

Document them as:

```text
Stage 8 controlled-live validation items
```

not offline defects.

---

# 58. No Stage 8 execution

Do not make any provider request even if Stage 7 PASS is obvious.

Stage 8 requires separate operator authorization.

---

# 59. Final response

Return:

1. branch and baseline HEAD;
2. confirmation of clean Stage 6 committed checkpoint;
3. Stage 7 files changed;
4. production defects found;
5. production defects fixed;
6. tests added;
7. network/origin audit result;
8. credential/security audit result;
9. retry/time-budget audit result;
10. transport/body/compression result;
11. JSON parser-security result;
12. XML parser-security result;
13. OMIE parser/discovery result;
14. time/DST/support result;
15. unit/statistic/geography result;
16. query/raw identity result;
17. archive/persistence result;
18. replay result;
19. error/diagnostic result;
20. provider-specific audit result;
21. Stage 6 regression result;
22. runtime/dependency result;
23. TODO/risk-pattern audit result;
24. 44-criterion reconciliation summary;
25. Stage 8 entry-gate result;
26. focused Stage 7 test result;
27. Stage 6 suite result;
28. provider-focused suite result;
29. full pytest result;
30. Ruff result;
31. format result;
32. mypy result;
33. pre-commit result;
34. `git diff --check` result;
35. remaining live-only questions;
36. exact Git status;
37. confirmation:
   - no provider request;
   - no credential probe;
   - no cloud action;
   - no branch;
   - no staging;
   - no commit;
   - no push.

If all Stage 7 criteria pass, finish exactly with:

```text
Phase 2 Stage 7 — PASS.

The complete Phase 2 ingestion system has passed the final
offline pre-live engineering audit.

All locally detectable correctness, boundedness, security,
identity, provenance, persistence and replay requirements
required before controlled provider validation are satisfied.

Remaining questions require real provider observations and
are reserved for Phase 2 Stage 8.

Phase 2 Stage 8 has not been started or authorized.
```

If a blocker remains, finish with:

```text
Phase 2 Stage 7 — PASS WITH GAPS.
```

and state the exact blocker.

Stop there.
