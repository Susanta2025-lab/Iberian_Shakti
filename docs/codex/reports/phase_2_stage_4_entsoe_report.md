# Phase 2 Stage 4 — ENTSO-E Transparency Platform integration

Date: **2026-11-03**, Europe/Lisbon. **PASS for offline engineering acceptance.**
Phase 2 remains in progress. No provider API request, credential probe, real
response download, cloud action or Stage 5 work occurred. Public official
reference documentation was consulted; this is not live product evidence.

## Baseline, scope and references

The first commands were `git status --short` and
`git log --oneline --decorate -10`: clean existing **main**, HEAD **8ef31ef**
(`feat: complete Phase 2 ESIOS ingestion`), preceded by 13d5ff6, 8bb5618,
09792e9, 8a377dd and 70f4204. No fetch/pull/rebase/reset/branch operation.
The [exact operator prompt](../prompts/phase_2/phase_2_stage_4_entsoe_integration.md)
was saved before implementation; older prompts/reports remain unchanged.
Repository instructions, architecture/runbooks, readiness, Stage 1/2/3 reports,
ADRs 0003/0004/0006 and existing contracts/ingestion/tests informed this work.

Only these products are implemented:

| Product | Codes | API selector | Native EIC | Canonical area |
| --- | --- | --- | --- | --- |
| Spain actual total load | A65 / A16 | `outBiddingZone_Domain` | `10YES-REE------0` | `ES.entsoe_bidding_zone` |
| Portugal day-ahead wind/solar forecast | A69 / A01 | `in_Domain` | `10YPT-REN------W` | `PT.entsoe_bidding_zone` |
| Spain day-ahead wind/solar forecast | A69 / A01 | `in_Domain` | `10YES-REE------0` | `ES.entsoe_bidding_zone` |

All use `AreaRole.BIDDING_ZONE`, country PT/ES and `native_scheme=eic`.
The response's `outBiddingZone_Domain.mRID` is required for load; generation
requires `inBiddingZone_Domain.mRID`. Both require EIC coding scheme A01. Wrong
identity/direction fails. These roles follow the product dependency rules;
sharing an EIC across roles never makes it a country or control-area observation.
No equivalence with REN's mainland or ESIOS's peninsular perimeter is asserted.

The retained [readiness evidence](phase_2_readiness_assessment.md), §G, supplies
product selectors, EIC and PSR mappings, UTC requests and GL v3 namespace.
Additional official documents used for the bounded parser profile:

- [Generation/Load dependency tables, v3r0](https://eepublicdownloads.entsoe.eu/clean-documents/pre2015/resources/Transparency/MoP%20Ref05%20-%20EMFIP-1-gl-market-document_V3R0-2014-01-24.pdf): A65/A16 consumption business A04, area aggregation A01; A69/A01 solar business A94 / wind A93, resource-type aggregation A08, incoming bidding zone and PSR; 15/30/60-minute resolutions. This historical supported profile does not prove current API output.
- [Official Generation/Load XSD](https://gitlab.entsoe.eu/transparency/xsd/-/blob/main/iec62325-451-6-generationload.xsd), already established by readiness: Generation/Load v3 field and namespace evidence. No remote schema is loaded at runtime.
- [Curve guidance](https://transparencyplatform.zendesk.com/hc/en-us/articles/30262342482961-CurveType-A01-vs-CurveType-A03): A01 fixed blocks / A03 variable constant blocks; omissions inside A03 are encoding, not automatically gaps.
- [Query Response](https://transparencyplatform.zendesk.com/hc/en-us/articles/15727773247124-Query-Response): UTC, partial/exact matching periods and acknowledgement context.
- [Rejection of Request](https://transparencyplatform.zendesk.com/hc/en-us/articles/15854332833300-Rejection-of-Request): acknowledgement v7 example, 999 + no-matching-data context and request/data-volume rejection conditions.
- [Common code list v36r0](https://www.entsoe.eu/Documents/EDI/Library/Core/entso-e-code-list-v36r0.pdf): B16 solar, B18 offshore wind, B19 onshore wind, MAW megawatts and controlled acknowledgement code meanings. Versioned mappings are local support, not claims of observed Iberian coverage.
- [Production endpoint](https://transparencyplatform.zendesk.com/hc/en-us/articles/15696677194644-Request-Endpoint): fixed HTTPS production origin/path.

No new ADR, dependency, contract, record statistic, archive format, CI workflow,
live command or parallel ingestion framework is introduced. ADRs 0003/0004
already govern query/private authentication/semantic outcomes/archive/replay;
ADR 0006's existing system `provider_period_value` statistic is reused.

## Profile, query and authentication

Profile/catalogue **0.1.0**, parser **entsoe.generation-load / 0.1.0**.
Report IDs are `actual_load.A65.A16.v0.1.0` and
`wind_solar_forecast.A69.A01.v0.1.0`; `SystemQuery.series_ids` pins `A65.A16`
or `A69.A01`. Safe canonical query JSON/hash includes source, report/product/
profile, typed native domain and requested UTC window. Existing archive
partition is the UTC start date. Provider revision/forecast edition is never
invented; supplied `revisionNumber` remains native response metadata only.

`request_for(product, country, window)` accepts only the three table selections.
Positive explicit UTC windows are at most 25 hours, with whole-minute endpoints;
seconds are rejected rather than truncated. Transport uses fixed
`https://web-api.tp.entsoe.eu/api`, `documentType`, `processType`, the selected
domain parameter and `periodStart`/`periodEnd` as `yyyyMMddHHmm`. No timezone/DST
request arithmetic, PSR filter splitting, pagination or product discovery.

`EntsoeAdapter.retriever()` uses the existing selected-provider loader and
`PrivateRequestPolicy`. Only **ENTSOE_API_TOKEN** is read when explicitly
constructing an acquisition retriever. Missing/invalid credentials produce a
static `ConfigurationError` before client construction/network I/O. The existing
8–4096 printable non-whitespace ASCII application bound is not a provider token
grammar. No dotenv load, refresh, alternate login, token probe or CI secret.
All tests inject synthetic mappings; no real token was read.

The token enters only the private `securityToken` query parameter. It is absent
from canonical identity, locators, filenames and persisted query/retrieval/parse
metadata. The private origin policy rejects changes/preinjection. Stage 4 adds
an opt-in XML character-reference check to that existing active-secret guard:
predefined, decimal and hexadecimal references, including zero padding, cannot
hide an echoed credential before archival/normalization. Bytes are never redacted
or rewritten. Default policies for previous providers retain their behavior.
This remains a bounded active-credential guard, not general secret detection.

## XML boundary and schema support

Only XML **1.0**, strict **UTF-8**, optional UTF-8 BOM or absent declaration.
Other declared encodings (even ASCII-compatible), invalid UTF-8, UTF-16/32/NUL,
unknown XML versions and processing instructions fail visibly.

| Root | Only supported namespace |
| --- | --- |
| `GL_MarketDocument` | `urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0` |
| `Acknowledgement_MarketDocument` | `urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0` |

Namespace prefixes are immaterial, but full expanded names are validated at
every level. Unknown roots, foreign nested namespaces, unknown schema versions,
duplicate metadata and unsupported series semantics fail. Namespaces are never
stripped. This is a strict supported subset, not full XSD validation or a
universal ENTSO-E parser. Live metadata variations require a reviewed new profile.

Stdlib Expat must be **>=2.6.0**, addressing unfinished-large-token work; older
runtimes fail closed. Namespace-aware callbacks reject DOCTYPE before DTD
processing, all entity declarations, external/parameter entities, skipped entities,
notations and processing instructions. Parameter-entity parsing is disabled.
There is no filesystem/network resolver, external schema, stylesheet or XInclude
processor. Only XML's predefined/character references remain usable as text.

Limits apply during tree construction: **4 MiB original bytes**, depth **32**,
**100,000 elements**, **2 MiB cumulative character data**, **4,096 characters per
element** (including fragmented callbacks), **16 attributes per element**, and
**256 characters per tag/attribute name/value**. Schema work also bounds
**100 TimeSeries**, **64 Periods per series**, **20,000 normalized records**,
**128-character decimal tokens** and **25-hour document/Period spans**.
Original byte bounds also limit non-character XML work. Hostile tests exercise
actual callbacks, external-resource attempts, expansion, encodings, malformed
XML, attributes, depth/count/text/byte limits and the old-Expat refusal.
No parser configuration or callback can resolve external resources.

## Validation, normalization and timing

Document identity, UTC creation, type/process and positive declared interval
are mandatory. Native revision is optional and validated when supplied.
Optional participant identities/roles are checked when supplied. The document
must intersect the requested window; each Period must be inside its document.
Complete intersecting document support is preserved without clipping to a
partial query. Neither requested nor returned complete-day coverage is claimed.

Every series requires mRID, compatible business/aggregation, correct native
domain, `quantity_Measure_Unit.name=MAW`, supported curve and Periods. A69 requires
one selected PSR; A65 forbids fabricated PSR. Cancelled/resource/per-unit/Reason
series semantics and unexpected fields are unsupported, never silently discarded.

Records are existing `SystemMeasurement` objects:

| Product | Measure/kind | Statistic/support | Technology |
| --- | --- | --- | --- |
| ES A65/A16 | `load` / `actual` | `provider_period_value`, UTC interval, exact MW | None |
| PT/ES A69/A01 | `generation` / `forecast` | Same | B16 → `solar`; B18 → `wind_offshore`; B19 → `wind_onshore` |

MAW maps explicitly to MW. XML decimal lexical values become finite Decimal
without float, rounding, clipping, rescaling or invented sign restrictions.
`provider_period_value` expresses source-period power without claiming an
arithmetic mean, instant sample or energy total; it does not authorize MWh
conversion. `cadence_seconds` retains each Period's base resolution.

Native TimeSeries mRID, document mRID and supplied revision remain on each
record. Geography retains EIC and role. Native PSR is preserved by the explicit
reversible profile mapping plus the source series/raw linkage. Original XML
retains PSR/business/aggregation/direction/curve/Period identity; the support
interval identifies its originating Period/block. No provider metadata is
replaced by a guessed publication revision.

Document `createdDateTime` is parsed/validated and stays in the linked immutable
original document. It is not promoted to per-value issue/run/update/publication
time. All `SourceTimes` fields remain unknown under this profile. Acquisition
completion and parse UUID/time are separate immutable events. Historical API
acquisition does not reconstruct what was known at an earlier market cutoff.

Technologies remain independent business dimensions. No summing or aggregation.
PT fixtures omit offshore wind; solar-only and onshore-only mutations prove
absence stays absence. Unknown PSR fails explicitly; no `other` fallback.
**Absent wind/solar technology series never become synthetic zero records.**

## Periods, curves and conflicts

Each Period requires explicit UTC start/end, `PT15M`, `PT30M` or `PT60M`
resolution and ordered position/quantity pairs. Positive duration must be an
exact multiple of resolution. Unsupported ISO duration forms fail, rather than
being guessed equivalent. No global fixed resolution or local DST calendar.

- **A01:** positions must be exactly 1..N in source order. Missing, duplicate,
  non-increasing or out-of-range positions fail. Every fixed support interval
  remains inside the Period; no filling/sorting.
- **A03:** the first block starts at position 1; strictly increasing starts
  terminate the preceding block. The last ends at the Period end. Each constant
  block expands deterministically into base-resolution support intervals with
  its exact value. Omitted intermediate positions are the constant-block
  encoding. Missing initial coverage, duplicate/reversed/out-of-range starts
  and invalid derived duration fail. No carry across Period gaps.
- **Multiple Periods:** all supported ordered non-overlapping Periods normalize,
  independently validated, with per-Period resolution. Gaps remain gaps.
- **Duplicates/conflicts:** consistent with existing ESIOS's deterministic
  rejection policy, even identical duplicate observations fail `content_invalid`.
  Conflicting exact or partial overlaps also fail with zero records. Checks span
  Periods and different TimeSeries mRIDs for the same technology/business meaning;
  changing mRID cannot evade conflict detection. Series traversal order is not a
  selection rule. Nothing is kept first/last, averaged or summed.

## Acknowledgements, retries, archive and replay

Acknowledgement v7 requires document ID, UTC creation and 1–16 structured
Reasons. No acknowledgement is measurement success; all produce zero records.
999 alone means unspecified error. Exact supported context with 999 recognizes
no matching data, invalid query attributes/parameters, data-volume rejection and
missing/invalid-token context from the documented response/rejection conditions.
Common code-list mappings additionally recognize A04/A41 invalid interval/
resolution, A05 authorization/contract rejection, A23 invalid area and A94/B18
technical failure. These possibilities are synthetic, not observed API variants.
No substring/keyword heuristics. Missing text for 999, unknown codes/text and
mixed categories remain `unsupported_acknowledgement`, a controlled provider
rejection. Unsupported acknowledgement structures/namespaces fail schema.

No-data maps to `source_unavailable/no_data`; auth/authorization/domain failures
have their existing typed codes; invalid/technical/unsupported acknowledgements
use `provider_rejected/provider_rejected`. A controlled category is logged as
`reason`; original reasons/codes/text remain only in linked raw XML. Unrestricted
provider prose never enters logs/exceptions. Empty XML, missing TimeSeries and
HTTP 404 never acquire invented no-data meaning.

Existing `HttpRetriever` retries/deadlines apply: three total attempts, default
1/2-second backoff, 10-second phases, 30-second attempt and 93-second operation
budget. Auth 401/403 is terminal. Stage 4's optional shared `retry_rate_limits=False`
ends ENTSO-E 429 without early retry/sleep, as readiness requires; earlier
providers retain existing Retry-After behavior. Selected transient 5xx/timeouts
still retry within shared budgets. Permanent HTTP, acknowledgement, content and
schema failures never enter an ENTSO-E retry loop.

The unchanged runner archives complete safe HTTP-200 bytes before parsing,
including malformed XML and acknowledgements. SHA-256 content addressing,
separate immutable retrieval/parse events and no-replace publication are reused.
Same query/body shares content and retains separate acquisition histories;
changed body retains both versions and histories. Interrupted/oversized,
active-credential echoes or authenticated nonidentity responses cannot masquerade
as complete safe acquisitions. Persistence failure prevents success.

Each record links to retrieval UUID and parse UUID; those events link query,
raw hash/reference and parser/profile/schema versions. Replay verifies bytes,
hash and original retrieval linkage with zero network and no credential loader.
It reproduces values, intervals, source/domain/technology/native identity,
business identity and raw linkage; only new parse UUID/time changes. Original
history is byte-for-byte unchanged. Corrupt payload/hash/linkage fails without
refetch. Unknown forecast editions remain separate original acquisitions even
when bodies are identical; actual corrections retain their business identity
with separate immutable evidence.

## Validation and review

Python **3.12.9**, Expat **2.6.4**, existing named environment. The default
network-denied pytest guard and all previous tests/fixtures/CI remain unchanged.

| Gate | Final result |
| --- | --- |
| Focused Stage 4 unit/integration suite | **238 passed** (196 unit, 42 integration) |
| Full `python -m pytest` | **1,642 passed in 19.64s**, no failures/skips/warnings |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 134 files already formatted |
| `mypy src` | No issues in 54 source files |
| `pre-commit run --all-files` | All eight hooks passed |
| Explicit pre-commit check of all new/changed files | All applicable hooks passed on all 25 paths; untracked files checked without staging |
| `git diff --check` / new-file whitespace / diff review | Passed; tracked and new files reviewed; index unchanged and empty |

Focused secret-safety cases cover managed DEBUG logs, static exceptions,
canonical queries, safe locators/filenames, retrieval/parse provenance and all
serialized diagnostics, including raw/quoted/JSON/XML-reference credential
echoes. Successful and refused paths pass. No real credential was used.
All **1,404** prior Phase 1 / Stage 1 / REN / ESIOS cases remain intact.

## Files changed

Twenty-five unstaged paths; the entire change set is left for operator review:

- `src/iberian_shakti/ingestion/entsoe/profile.py`
- `src/iberian_shakti/ingestion/entsoe/identity.py`
- `src/iberian_shakti/ingestion/entsoe/adapter.py`
- `src/iberian_shakti/ingestion/entsoe/xml_boundary.py`
- `src/iberian_shakti/ingestion/entsoe/schema.py`
- `src/iberian_shakti/ingestion/entsoe/acknowledgement.py`
- `src/iberian_shakti/ingestion/entsoe/parser.py`
- `src/iberian_shakti/ingestion/auth.py` — opt-in XML credential-reference protection.
- `src/iberian_shakti/ingestion/http.py` — opt-in terminal rate-limit policy.
- `tests/unit/ingestion/entsoe/test_entsoe_profile.py`
- `tests/unit/ingestion/entsoe/test_entsoe_parser.py`
- `tests/unit/ingestion/entsoe/test_entsoe_xml_security.py`
- `tests/integration/test_entsoe_flow.py`
- `tests/data/entsoe/synthetic_es_load.xml`
- `tests/data/entsoe/synthetic_pt_forecast.xml`
- `tests/data/entsoe/synthetic_es_forecast.xml`
- `tests/data/entsoe/synthetic_acknowledgement.xml`
- `tests/data/entsoe/manifest.json`
- `tests/data/entsoe/README.md`
- `docs/codex/prompts/phase_2/phase_2_stage_4_entsoe_integration.md`
- `docs/codex/reports/phase_2_stage_4_entsoe_report.md`
- `README.md`
- `docs/architecture/README.md`
- `docs/runbooks/README.md`
- `docs/runbooks/ingestion.md`

## Reserved for separately controlled live validation

No offline Stage 4 engineering blocker remains. No real-provider success is
claimed. Later authorized validation must independently establish:

- Successful ENTSO-E authentication and account authorization.
- Actual current namespace/schema/field, business and aggregation variants;
  this profile deliberately accepts only the documented subset above.
- Exact returned native domain IDs/roles and PT/ES PSR combinations/coverage.
- Actual resolutions, A01/A03 occurrence and multi-Period occurrence.
- Real acknowledgement reason codes/text, rejection and no-data variants.
- Inclusive/exclusive request boundaries, returned coverage and document spans.
- Publication/update/creation meaning, forecast editions and historical corrections.
- Quotas/rate/bans, response sizes and encodings/compression.
- Historical availability/retention and applicable owner/item redistribution rights
  already identified in readiness; synthetic fixtures grant no rights to real data.

No source API call, token probing, branch, staging, commit, push, paid resource
operation, later provider or Stage 5 implementation occurred.

**Phase 2 Stage 4 — PASS.** Phase 2 Stage 5 has not been started or authorized.
