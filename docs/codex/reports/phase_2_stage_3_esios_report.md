# Phase 2 Stage 3 — ESIOS indicator 544

Date: 2026-11-03. **PASS for offline engineering acceptance.** Phase 2 remains
in progress. No controlled live validation or Stage 4 work was performed.

## Baseline and scope

First commands were `git status --short` and `git log --oneline --decorate -10`.
The working tree was clean, on existing branch **main** at
**13d5ff66a93912aed96939ea012b9efb4f719557**
(`ci: run pre-commit in GitHub Actions`). Preceding local commits were
8bb5618, 09792e9, 8a377dd and 70f4204, as expected. No remote synchronization.

The [exact operator prompt](../prompts/phase_2/phase_2_stage_3_esios_integration.md)
was saved before implementation. Repository instructions, architecture,
readiness §F and shared design, Stage 1/2 reports, ADRs 0003/0004/0006 and the
existing contracts/ingestion/tests were inspected. The new operator instruction
permits offline Stage 3 acceptance and reserves authenticated metadata evidence
for controlled live validation; this does not satisfy full Phase 2 live closure.

Only **ESIOS / Red Eléctrica indicator 544 — Demanda prevista Peninsular** is
implemented. No new dependency, shared contract/statistic, archive framework,
ADR, CI change, live command, paid resource or later-phase component is added.
ADRs 0003/0004 already cover all durable design decisions used here. Existing
tests, historical prompts, reports and fixtures remain unchanged.

## Query and authentication

Profile **0.1.0**, parser **esios.indicator544 / 0.1.0**, report identity
**indicator544.v0.1.0**. `request_for(QueryWindow(...))` uses existing typed
`ApiSourceRequest`/`SystemQuery`, only series `544` and canonical peninsular area.
The UTC start date is archive partition context. Positive UTC windows are bounded
to the shared 25-hour maximum. Safe deterministic identity includes provider,
profile, indicator, area and window; it contains no secret or fabricated revision.

The only endpoint is `https://api.esios.ree.es/indicators/544`. The transport
encodes ISO-8601 UTC `start_date` and `end_date`; no API aggregation, truncation,
resampling, alternate indicator, catalogue lookup or guessed geo filter occurs.
Origin/profile/product changes fail before transport. There is one bounded
response per invocation; this is not a completeness or historical-retention claim.

The existing selected-provider loader reads **ESIOS_API_TOKEN** at retriever
construction, validates it and injects it privately into **x-api-key** through
`PrivateRequestPolicy`. Missing/invalid credentials raise the existing static
`ConfigurationError` before request construction or network I/O. No environment
file, refresh, fallback, credential probe, query token or CI secret is involved.
All tests inject synthetic credentials; actual operator credentials were not read.

## Parser and measurement policy

The bounded UTF-8 JSON parser validates the documented nested `indicator`,
`values` and `geos` concepts. Integer indicator identity must be 544. Required
value fields are finite JSON numeric `value`, explicit `datetime_utc`, and
positive native `geo_id`. Geography requires `Península` name evidence either
on the value or its matching indicator-level geo. Supplied optional name,
`unit`, `magnitud` and `tiempo` must agree with the selected product; descriptions
and presentation fields are not mandatory. Returned source metadata stays in
the immutable original document.

MW and five-minute semantics are pinned by the operator's selected product and
retained official product description, rather than fabricated numeric metadata
IDs. Optional metadata checks accept `Demanda prevista Peninsular`, `MW`,
`Potencia` and `Cinco minutos` respectively. These are conservative local profile
checks, not evidence that authenticated metadata was observed. Exact live labels
and catalogue shape remain to be validated. No numeric magnitude, cadence or
geography ID is asserted. Fixture geo ID **999001 is explicitly synthetic**.

Limits: 2 MiB original bytes, 2,000 values, 32 geos, depth 16, 50,000 JSON nodes,
4,096-character strings and 128-character numeric tokens. Duplicate JSON keys,
malformed structures/encoding/timestamps, nonfinite/null/nonnumeric quantities,
incompatible identity/unit/geography, unordered/duplicate/conflicting observations
and mixed geographic series fail with zero records. Safe malformed HTTP-200
bodies remain archived and get separate terminal failed parse events. Empty or
absent values do not become success or an invented provider no-data response.

Each successful observation is an existing **SystemMeasurement**:

| Concept | Representation |
| --- | --- |
| Meaning | `measure=load`, `kind=forecast`, exact Decimal `MW` |
| Target time | `ValidInstant` at provider `datetime_utc` |
| Statistic / cadence | `instant` timestamped forecast sample; 300 seconds |
| Geography | `AreaRole.SYSTEM`, `ES.peninsular`, country ES, mainland perimeter |
| Native identity | Provider `geo_id`, series `544`, profile `0.1.0` |
| Publication status | Unknown |
| Issue/run/publication time | Unknown; never inferred |

The instant representation makes no claim about actual measured demand or an
arithmetic interval mean. No interval duration, MWh conversion, interpolation,
filling, aggregation or extra statistic is introduced. Native geographic names,
local timestamp strings and array positions remain recoverable from raw bytes;
native ID + series + UTC instant uniquely identify a validated value there.

## Timestamp and vintage safety

Canonical time comes directly from explicit zero-offset `datetime_utc`.
If local `datetime` is supplied it must be offset-aware, denote the same instant
and use the Europe/Madrid offset valid at that instant. Both spring and autumn
DST cases are tested; there is no fixed CET/CEST offset or local-time UTC
reconstruction. Times must be strictly increasing on the five-minute UTC grid.
Missing samples remain visible as gaps. No sorting or deduplication occurs.

Returned timestamps must lie between the requested endpoints. A possible
provider-inclusive end sample is preserved; live endpoint inclusivity remains
unknown. No requested-window or complete-day coverage is claimed.

`values_updated_at`, when present, becomes UTC `SourceTimes.updated_at` as
**indicator-level snapshot update context**, attached to the records; it is not
proof of per-value forecast creation. Raw bytes retain its original spelling.
Target time, source update, acquisition completion and parse time remain
separate. Issue/model-run/publication times remain null. Unknown forecast
editions retain original acquisition snapshot identity, including unchanged
values acquired again. Historical acquisition does not prove availability at
an earlier market cutoff.

Official publication description: 00:00 supplies D; 13:30 adds the first three
hours of D+1. Indicator 544 is not represented as a guaranteed complete D+1,
auction-time D-1 or seven-day forecast.

## Archive, outcomes, replay and secret safety

The existing `HttpRetriever` → `ingest_resolved` → `LocalRawArchive` chain is
reused unchanged. Complete safe successful bytes archive before parsing.
Same query/body reuses SHA-256 content with independent acquisition events;
changed bytes retain both bodies and all histories. There is no mutable latest
copy. Acquisition and version-2 parse events retain query, raw hash/reference,
parser/catalogue/schema versions and record linkage.

Shared retry/deadline policy remains three attempts with 1/2-second default
backoff and finite 10/30/93-second phase/attempt/operation budgets. 401/403 are
terminal auth/authorization failures; unverified 404 is a permanent HTTP failure.
429 honors supported delta-seconds Retry-After; supported 5xx/timeouts use bounded
shared retries. Permanent schema/content failures do not retry. Oversized bodies,
active-credential echoes and authenticated nonidentity encoding are rejected
before raw publication under the existing private policy.

Shared replay verifies bytes/hash and original retrieval linkage, needs no
credential/network and reproduces normalized values, business identities, target
times, native identity and raw linkage. Only new parse identity/time changes.
Tests forbid acquisition and HTTP client construction during successful replay,
preserve earlier files byte-for-byte and check corrupted archives have no refetch.

Focused synthetic-secret tests pass for logs, controlled exception messages,
query identity, safe/archive locators, retrieval/parse provenance and serialized
metadata. Literal, URL-quoted and JSON-escaped active-credential echoes cannot
publish raw content; secret-bearing optional response observations are omitted.
No real token is present in fixtures or diagnostics. This reuses ADR 0004's
narrow active-credential guard, without claiming general secret detection.

## Validation

Python **3.12.9**, existing environment; default pytest network guard unchanged.

| Check | Result |
| --- | --- |
| Focused ESIOS unit/integration suite | **112 passed in 0.79s**: 20 profile/auth, 68 parser, 24 integration |
| Full `python -m pytest` | **1404 passed in 13.83s**, no failures/skips/warnings |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 119 files already formatted |
| `mypy src` | No issues in 47 source files |
| `pre-commit run --all-files` | All eight hooks passed |
| Explicit pre-commit check of every changed/new path | All applicable hooks passed; includes untracked files without staging |
| `git diff --check` | Passed; new-file whitespace also checked |

All **1,292** existing cases remain intact and green. Neither GitHub Actions
nor the network-denied pytest guard was changed. Full tracked diff, new files,
fixture checksum and empty index diff were reviewed. No test was removed,
skipped or weakened to obtain a pass.

## Files changed

Seventeen paths, all unstaged:

| Paths | Purpose |
| --- | --- |
| `src/iberian_shakti/ingestion/esios/{profile,identity,adapter,schema,parser}.py` | Pinned product, safe query, private transport and strict normalization |
| `tests/unit/ingestion/esios/{test_esios_profile,test_esios_parser}.py` | Query/authentication, values, metadata, timestamp/DST/gaps and strict failure tests |
| `tests/integration/test_esios_flow.py` | Real-component archive/revisions/replay, transport errors and secret safety |
| `tests/data/esios/{synthetic_forecast.json,manifest.json,README.md}` | One small synthetic body, checksum/origin policy; failures/revisions are in-memory mutations |
| `docs/codex/prompts/phase_2/phase_2_stage_3_esios_integration.md` | Exact saved operator prompt |
| `docs/codex/reports/phase_2_stage_3_esios_report.md` | This report |
| `README.md`, `docs/architecture/README.md`, `docs/runbooks/{README.md,ingestion.md}` | Current status and focused operating/replay guidance |

## Reserved for controlled live validation

No offline engineering blocker remains under this Stage 3 instruction. Later
authorized validation must establish successful real authentication, exact live
metadata labels/shape and numeric native mappings, actual response encoding,
end-date inclusivity/returned coverage, historical retention and revisions,
source update meaning, no-data/future/error responses and numeric quotas. There
is no per-value issue-time or guaranteed old-cutoff reconstruction claim. Rights
limitations remain as recorded in readiness; synthetic fixtures grant no source
redistribution or commercial clearance.

No provider request, branch creation, staging, commit, push, cloud action or
Stage 4/later implementation occurred. Stage 3 changes remain for operator review.

**Phase 2 Stage 3 — PASS.** Phase 2 Stage 4 has not been started or authorized.
