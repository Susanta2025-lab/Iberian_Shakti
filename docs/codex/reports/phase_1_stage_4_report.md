# Phase 1 Stage 4 — OMIE resolution, parsing, calendars, and complete reports

Date: 2026-10-26. Working tree: existing `main`, no commit or push.

## A. Stage objective

Implemented the first concrete provider integration, OMIE `marginalpdbc`
day-ahead prices for PT and ES: exact revision or bounded latest-observed
resolution, Stage 3 retrieval and immutable archival, strict complete-report
parsing, provider calendar profiles, normalized records, and persisted parse
events. Replay consumes the same parser without acquisition.

The accepted [Phase 1 baseline](phase_1_readiness_assessment.md),
[Stage 2](phase_1_stage_2_report.md), [Stage 3](phase_1_stage_3_report.md),
[ADR 0001](../../adr/0001-omie-day-ahead-source-and-market-price-contract.md),
and [ADR 0002](../../adr/0002-local-ingestion-immutable-archive-and-replay.md)
remain authoritative. No readiness or architecture reassessment was performed.

## B. Files changed

Three existing files modified:

| Exact path | Purpose |
| --- | --- |
| `src/iberian_shakti/contracts/ingestion.py` | Minimal listing acquisition contracts/protocol and corrected resolution dependency; see D. |
| `src/iberian_shakti/ingestion/http.py` | Share the existing bounded acquisition loop between report retrieval and ephemeral listing acquisition. |
| `src/iberian_shakti/common/logging.py` | Add only `omie_resolution_completed` and `omie_parse_started` to the closed event allowlist. |

New implementation and test files:

| Exact path | Purpose |
| --- | --- |
| `src/iberian_shakti/ingestion/omie/identity.py` | Central source/report/market/parser identities, filename grammar, agreement validation, private URL mapping. |
| `src/iberian_shakti/ingestion/omie/adapter.py` | Exact resolution, bounded listing interpretation, numeric revision selection, explicit absence/coverage/schema outcomes, provider 404 policy. |
| `src/iberian_shakti/ingestion/omie/calendar.py` | Transition/profile selection and Europe/Madrid mapping using the generic Stage 2 interval helper. |
| `src/iberian_shakti/ingestion/omie/parser.py` | Strict ASCII, exact report grammar, complete-day validation, PT/ES normalization and parse provenance. |
| `src/iberian_shakti/ingestion/runner.py` | Small synchronous composition of resolution, Stage 3 retrieval/persistence, parser and parse-event persistence. |
| `tests/unit/ingestion/omie/conftest.py` | Local fixture access and parser inputs; inherits the existing ingestion-unit network denial. |
| `tests/unit/ingestion/omie/test_calendar.py` | OMIE profiles, transition, UTC bounds, DST and missing timezone configuration. |
| `tests/unit/ingestion/omie/test_discovery.py` | Discovery/link grammar, explicit outcomes, shared HTTP bounds/retries, contract and compatibility regressions. |
| `tests/unit/ingestion/omie/test_parser.py` | Complete fixtures, grammar/Decimal/area/linkage checks, no partial success, manifest inventory/hashes. |
| `tests/unit/ingestion/omie/test_omie_logging.py` | Real OMIE events through the existing safe formatter; no payload/HTML/URL/secret leakage. |
| `tests/integration/test_stage4_omie_flow.py` | Actual adapter, retriever, archive, parser and replay chain under mocked HTTP and scoped network denial. |
| `tests/data/omie/README.md` | Fixture origin, generation/mutation labels and exact-byte maintenance. |
| `tests/data/omie/manifest.json` | Inventory, attribution, dates/revisions, profiles, intended outcomes and SHA-256 for every data fixture. |
| `docs/codex/reports/phase_1_stage_4_report.md` | This report. |

The 25 individual data-fixture paths are listed in H. Including them, there
are 42 changed/added paths: three modifications and 39 additions. `.gitignore`,
dependencies, architecture documents, ADRs and existing tests are unchanged.

## C. OMIE source implementation

Only source `omie`, report `marginalpdbc`, market `day_ahead` is supported.
The single report supplies both PT and ES columns.

Exact selection constructs `marginalpdbc_YYYYMMDD.v` with a positive numeric
revision, validates request/filename/date/revision/locator agreement, and makes
no listing request. The safe locator is
`omie/marginalpdbc/<filename>`. Only the execution URL mapper produces the
public HTTPS download query; transport URLs never enter provenance or logs.

Latest-observed selection acquires the accepted public route
`https://www.omie.es/en/file-access-list?realdir=marginalpdbc` once. Standard-library
`HTMLParser` and URL parsing recognize download anchors inside closed tables.
Only the exact HTTPS origin `www.omie.es`, `/en/file-download`, and exactly one
each of `parents=marginalpdbc` and `filename=<validated filename>` are accepted.
Invalid calendar dates/revisions, unexpected origins/paths, userinfo, fragments,
extra/duplicate query fields and unrelated families cannot select a report.
Duplicate valid entries are deduplicated. Revisions are compared as integers,
including `.9` versus `.10`; `.2` works without `.1`. No revision probing exists.

Bounds:

| Bound | Value / behavior |
| --- | --- |
| Listing pages | One, explicitly `MAX_LISTING_PAGES = 1`; pager links are detected and never followed. |
| Listing requests | One logical acquisition, at most three HTTP attempts under the default Stage 3 policy. |
| Listing body | 1 MiB streamed limit in `HttpRetriever`; adapter independently rejects larger supplied listing results. |
| Parsed anchor candidates | 10,000, including duplicates/unrelated anchors, then typed discovery/schema failure. |
| Redirects | Zero, retaining Stage 3 policy. |
| Phase/attempt/operation acquisition time | Existing defaults: 10 / 30 / 93 seconds, including bounded retries/backoff in the operation budget. Parsing separately has bounded input/candidate work. |
| Whole ingestion HTTP attempts | At most three for exact selection, or six with discovery, with default policies. No rediscovery/polling loop. |

A valid covering listing means recognized closed download tables, no detected
pagination, and the requested date inside the observed minimum/maximum date
span. Absence there returns `unavailable/not_listed`, meaning absence from that
observed listing, not a claim that no historical revision exists. Outside that
window, or absent with rejected family links, returns
`coverage_unknown/coverage_unknown`. Detected pagination returns coverage unknown
even if the first page has a match; incomplete traversal cannot establish the
selection. Empty/unrecognized/malformed table structure, invalid UTF-8 listing
bytes, and candidate overflow return `failure/discovery_schema`. Listing
transport/size/encoding failures retain safe typed failure codes and never claim
report absence. HTML bytes/metadata are not persisted as report provenance.

This deliberately limited listing grammar is tested with synthetic HTML, not
presented as a newly verified live DOM/retention guarantee. Stage 6 owns live
validation. Exact revision resolution remains usable independently of listing
coverage.

## D. Protocol compatibility

The original `SourceAdapter.resolve(request, retriever: Retriever)` was
insufficient for honest listing execution: `Retriever.retrieve()` consumes a
`ResolvedSource`, which does not exist until discovery is complete. Treating
HTML as a resolved report would fabricate report identity, revision and raw
provenance.

Smallest implemented refinement:

- Add frozen `ListingRequest(safe_locator)` and ephemeral `ListingResult`
  containing bounded-acquisition outcome, attempts, HTTP observations and private
  bytes. Its bytes are excluded from repr/serialization. It cannot report
  `unavailable` as though a specific report had been acquired.
- Add `ListingRetriever.retrieve_listing(request)` and change only the
  `SourceAdapter.resolve` dependency annotation to `ListingRetriever`.
- `HttpRetriever` implements both interfaces, with an optional execution-private
  listing URL mapper and independent size limit. An internal `_Acquisition`
  result extracts the existing HTTP loop; report and listing methods adapt its
  result to their respective existing/new contracts. There is still one retry
  engine, one deadline/transport policy and synchronous execution.

`Retriever.retrieve`, `LocalFileRetriever`, retrieval/raw/archive/parse contracts,
archive layout and replay remain unchanged. Existing construction arguments
remain valid. A future implementation of `SourceAdapter.resolve` must accept
the listing capability; a report-only retriever need not implement discovery.
The runner takes the two capabilities explicitly, permitting one `HttpRetriever`
for both or a separate local report retriever.

Regression coverage includes existing report retrieval tests, listing
503/exhaustion/backoff/success, deadlines, size, redirects, safe locator callback
errors for both methods, exact selection without listing, and absence of
invented listing acquisition history. All original 512 tests pass unchanged.
No architecture decision or schema-version change was required.

## E. Parser grammar

Parser identity is centrally defined as `omie.marginalpdbc`, version `1.0.0`.
Normalized schema remains `1.0.0`.

- Strict ASCII decode; reject non-ASCII/BOM and unsupported Content-Encoding.
  No fallback decoder, replacement characters or encoding guessing.
- Exact header `MARGINALPDBC;`.
- Six nonempty fields: year, month, day, positive numeric period, PT price,
  ES price, each separated by `;`, with the required trailing `;`.
- Four-digit year, one/two-digit month/day, valid calendar date matching the
  acquired/requested delivery date. Provider filename identity is also checked.
- Prices use `[+-]?[0-9]+(?:\.[0-9]{1,2})?`, directly converted to `Decimal`.
  Signed integers, negative values, zero and one/two fractional digits preserve
  precision. No float conversion or regulatory cap. Reject exponents,
  NaN/infinity, commas/grouping, spaces, malformed signs and extra precision.
- LF or CRLF; no bare CR, interior blank rows, extra/missing fields, or whitespace
  trimming that could conceal malformed source content.
- Exactly one final `*`, optionally followed by one line ending; no other data,
  extra terminators, or extra blank lines afterward.
- Exactly the complete ordered source sequence `1..N` for the applicable market
  profile; duplicate, missing, skipped, reordered and out-of-range periods fail.

Every source row is validated before normalized records are constructed. Any
invalid row, including the last row, yields `ParseOutcome.CONTENT_FAILURE`,
`content_invalid` (or the encoding/integrity category), zero records and a parse
event. There is no silent row skipping or partial output. Calendar configuration
errors remain clear execution errors rather than fabricated content success.

## F. Calendar profiles

Provider-owned transition is **2025-10-01**, with `Europe/Madrid` for both areas:

| Profile | Resolution | Ordinary / spring / autumn periods |
| --- | ---: | --- |
| Before transition | 60 minutes | 24 / 23 / 25 |
| From transition | 15 minutes | 96 / 92 / 100 |

`intervals_for()` selects the profile then delegates to the Stage 2 generic
`market_day_intervals`. Consecutive local midnights are independently converted
to UTC. Their elapsed minutes divided by resolution determine N. Period offsets
advance in UTC, covering the complete day contiguously through skipped/repeated
local hours. No fixed offset, Lisbon date rewrite, naive local stepping,
resampling, filling or hourly fallback is introduced. Missing IANA timezone
data produces a safe configuration error.

Tests assert 2025-09-30 / 2025-10-01 explicitly, all six period profiles, exact
UTC boundaries and duration, contiguous intervals, and both folds of the autumn
02:00 hour. A modern 24-row file is rejected.

## G. Normalized mapping

Each source period produces PT then ES records using that exact source-column
order. Both records share the same interval, numeric period and duration.
`MarketPrice` supplies immutable typed prices with source/report/date,
`market=day_ahead`, `currency=EUR`, `price_unit=MWh`, aware UTC interval endpoints
and exact Decimal values. The original unequal-price spring fixture independently
checks both columns; six source rows differ.

| Day | Source periods | Normalized records |
| --- | ---: | ---: |
| Legacy ordinary | 24 | 48 |
| Legacy spring | 23 | 46 |
| Legacy autumn | 25 | 50 |
| Modern ordinary | 96 | 192 |
| Modern spring | 92 | 184 |
| Modern autumn | 100 | 200 |

Every record links to its parse UUID. Parse provenance records parser/schema
versions, a separate UUID/time, and original acquisition UUID/raw/archive
references. Business identity retains the existing source/report/area/day/period/
duration tuple; normalized content identity retains raw hash and parser/schema
versions. New acquisitions and replays do not change normalized business values.

## H. Fixtures

All fixture paths below are relative to `tests/data/omie/`. These 25 data files
total **47,456 bytes**, plus `README.md` and `manifest.json`. No bulk dataset or
CSV exception was added. `git check-ignore` confirms native fixture filenames
and the manifest are permitted while root `data/raw` remains ignored.

| Exact relative path | Type | Purpose |
| --- | --- | --- |
| `marginalpdbc_20250330.1` | original | Complete legacy spring, 23 periods; negative and unequal PT/ES prices. |
| `marginalpdbc_20250930.1` | original | Complete legacy ordinary, 24 periods, last legacy delivery day. |
| `marginalpdbc_20251127.2` | original | Complete observed revision-2 report, 96 periods. |
| `marginalpdbc_20260329.1` | original | Complete modern spring, 92 periods. |
| `marginalpdbc_20261025.1` | original | Complete modern autumn, 100 periods and negative prices. |
| `marginalpdbc_20261026.1` | original | Complete modern ordinary, 96 periods. |
| `synthetic_marginalpdbc_20241027.1` | synthetic | Complete 25-period legacy autumn numeric profile. |
| `synthetic_marginalpdbc_20251001.1` | synthetic | Complete first modern day, 96 periods, unequal/negative/zero values. |
| `revised_marginalpdbc_20261026.2` | mutated | Valid controlled revised prices; not a verified OMIE revision. |
| `truncated.omie` | mutated | Truncated body. |
| `missing_terminator.omie` | mutated | Missing terminal marker. |
| `wrong_header.omie` | mutated | Wrong header. |
| `wrong_fields.omie` | mutated | Extra field. |
| `invalid_price.omie` | mutated | NaN price. |
| `duplicate_period.omie` | mutated | Duplicate source period. |
| `missing_period.omie` | mutated | Missing row. |
| `reordered_period.omie` | mutated | Swapped periods. |
| `wrong_date.omie` | mutated | One inconsistent date. |
| `after_terminator.omie` | mutated | Extra data after marker. |
| `html_body.omie` | mutated | HTML replacement body. |
| `non_ascii.omie` | mutated | Unsupported source byte. |
| `bom.omie` | mutated | Unsupported UTF-8 BOM. |
| `listing_covering.html` | synthetic | Recognized observed date span with the requested date absent. |
| `listing_paginated.html` | synthetic | First-page match with incomplete pagination. |
| `listing_malformed.html` | synthetic | Unrecognized structure. |

The six originals were copied byte-for-byte from assessment downloads still in
`/tmp`. Their filenames, lengths and profiles match the accepted evidence. The
three SHA-256 values printed in the accepted assessment were verified before
copying. The manifest records exact hashes for all six originals, the verified
public source URLs, acquisition date 2026-10-26, date/revision, counts/resolution
and purpose. Synthetic/mutated samples are explicitly labelled; mutations name
their parent. Missing original evidence is not represented as a live fact.

Manifest tests check the complete inventory and every exact-byte checksum.
Original CRLF is deliberately preserved. Ordinary `git diff --check` passes for
the working-tree diff. Added files were also checked with no-index diffs allowing
`cr-at-eol`; default Git whitespace checking calls source CRLF trailing whitespace
when these files are later staged, so reviewers should recognize CRLF rather
than normalize fixture bytes. No Git configuration was changed.

## I. Archive/replay integration

`ingestion.runner.ingest()` composes the established boundaries:

```text
SourceRequest -> adapter.resolve
  unresolved -> explicit ResolutionResult
  resolved -> Stage 3 retrieve -> persist_retrieval
    unavailable/failure -> IngestionResult without parse
    complete archived body -> OMIE parse -> archive.persist_parse -> IngestionResult
```

No parser success can escape this production-style path before raw and
acquisition metadata persistence. Complete malformed/HTML/unsupported-encoding
200 bodies remain archived, acquisition stays successful, and a separate failed
parse event is persisted. Parsing and archive errors never reenter HTTP retries.
Archive/provenance persistence errors cannot return successful ingestion.

Same bytes reuse the immutable content object while adding independently
identified retrieval/parse events. Revised bytes create another SHA directory,
including changed bytes under the same revision label. Both prior payload and
metadata remain unchanged and independently traceable. A selected file returning
404 yields controlled `unavailable/not_found` without rediscovery or parsing.

Stage 3 `replay` remains unchanged: verify archived hash/length and original
acquisition, then invoke the same parser with a new explicit parse UUID/time and
persist that event. Tests block HTTP-client construction/retrieval during replay,
compare all normalized values/business identities, and verify existing history
has not changed. There is no new replay transport or fabricated acquisition.

## J. Tests

Focused command:

```bash
python -m pytest tests/unit/ingestion/omie tests/integration/test_stage4_omie_flow.py -q
```

**188 passed**, no skips/failures/live calls:

| File | Count | Categories |
| --- | ---: | --- |
| `tests/unit/ingestion/omie/test_calendar.py` | 13 | Six profiles, transition, UTC coverage/DST and timezone configuration. |
| `tests/unit/ingestion/omie/test_discovery.py` | 67 | Exact/latest, numeric revisions, links/dates/schema/coverage, finite acquisition, disappearance and compatibility regressions. |
| `tests/unit/ingestion/omie/test_parser.py` | 86 | Fixtures, manifest, strict grammar/encoding/Decimal, complete ordering, PT/ES and provenance. |
| `tests/unit/ingestion/omie/test_omie_logging.py` | 5 | Selected/unknown/schema/parse success/failure events and safe context. |
| `tests/integration/test_stage4_omie_flow.py` | 17 | Actual component chain, revisions, malformed archival, replay, unavailability, and persistence failures. |
| **Stage 4** | **188** | Offline deterministic tests. |
| Existing Stages 1–3 | 512 | Existing tests retained unchanged. |
| **Full suite** | **700** | All passing. |

All Stage 4 HTTP uses `httpx.MockTransport`; local fixtures are never downloaded
by tests. Unit tests inherit the existing ingestion-scoped socket/DNS denial;
new integration tests have their own scoped denial. The repository-wide guard
remains Stage 5 work. An initial full-suite collection found a basename collision
with the existing logging test; the new file was renamed `test_omie_logging.py`
and the full suite then passed. No existing test or test configuration was weakened.

## K. Validation evidence

Named environment `iberian_shakti`, Python 3.12.9:
`/home/home/.pyenv/versions/iberian_shakti/bin/python`.

| Exact command | Result |
| --- | --- |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `64 files already formatted` |
| `mypy src` | `Success: no issues found in 32 source files` |
| `python -m pytest` | `700 passed` |
| Focused command in J | `188 passed` |
| `git diff --check` | Exit 0; no output. |

Inspected `git status --short`, `git diff --stat`, `git diff`, every untracked
implementation/test file, the fixture inventory/bytes/hashes, and this report.
Untracked additions were checked separately because ordinary diffs omit them.
Fixture hashes/inventory agree. The only invalid source bytes are intentional
malformed fixtures. No credentials/private keys, bulk raw dataset, live test
requirement, dependency addition, future-provider changes or Stage 5+ production
implementation entered the change.

## L. External facts / remaining uncertainty

No new external request, live provider validation, or source-fact verification
was needed: the accepted documentation and retained downloaded samples supplied
the report facts. Listing HTML fixtures are synthetic. The current live DOM,
retention and full revision/pagination coverage have not been newly verified.
Discovery intentionally supports one observed page and fails visibly on
unrecognized structure/pagination; exact revision requests bypass that limit.

The exact bytes of a legacy autumn original and a transition-day original
remain unverified; complete synthetic fixtures exercise those accepted calendar
profiles. Unchanged uncertainties include publication SLA/minute, every
prepublication response, contractual charset, same-filename stability, and every
older historical grammar. Strict ASCII and the two selected profiles define the
implemented support envelope. These are documented limits, not new readiness
blockers. Stage 3 host-resolver/deadline and trusted-local-filesystem limits also
remain applicable.

## M. Scope confirmation

Only Stage 4 implementation and its required component integration/tests/report
were added. No repository-wide network guard, live CLI, automatic live tests,
scheduler, async framework, additional provider, Snowflake/dbt/features/ML/
training/inference/API/dashboard, infrastructure or cloud work was performed.
No external or paid resource was activated, provisioned, modified, resized or
deleted. No branch, commit, push or Git-index mutation was made. Work remains
reviewable and uncommitted on the existing `main` working tree.

## N. Remaining Phase 1 work

- Stage 5: remaining general edge cases/redaction and integration hardening,
  including the repository-wide default offline network guard.
- Stage 6: explicitly opted-in live smoke command and separately recorded
  provider validation; no automatic pytest/CI live execution.
- Stage 7: operational/developer documentation and final verification against
  the existing accepted Phase 1 criteria.

## O. Stage verdict

**PASS**

Applies only to Phase 1 Stage 4. Stages 5–7 remain pending with the documented
support envelope and external uncertainties above.
