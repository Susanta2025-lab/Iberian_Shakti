# Phase 1 Stage 6 — Explicit live OMIE smoke validation

## A. Stage objective

Stage 6 validated the already-hardened OMIE ingestion path against the real
public provider through operator-executed exact-revision and latest-observed
requests, then verified offline replay of the acquired content. This report
documents those completed observations and the current implementation.

This documentation task performed local/offline verification only: no new
provider request, DNS resolution, live CLI execution, browser lookup, dependency
download, or external-provider contact. Commands containing `--live` below are
historical operator evidence, not commands executed during this task.

Evidence sources are the operator's supplied command/output/exit-code record,
the retained archive at `/tmp/iberian-shakti-omie-smoke`, current implementation
and tests, and local Git history. Historical shell output and the intermediate
archive counts are attributed to the operator; current retained objects and
their linkage were independently checked offline. Shell execution timestamps
were not independently recorded; the persisted provenance timestamps are
acquisition/parse observations, not source publication times.

Read root `AGENTS.md`, README, architecture/ADR/runbook catalogs, the accepted
[Phase 1 assessment](phase_1_readiness_assessment.md),
[Stage 2](phase_1_stage_2_report.md), [Stage 3](phase_1_stage_3_report.md),
[Stage 4](phase_1_stage_4_report.md), [Stage 5](phase_1_stage_5_report.md),
the [pre-live engineering audit](phase_1_stage_6_pre_live_engineering_audit.md),
[ADR 0001](../../adr/0001-omie-day-ahead-source-and-market-price-contract.md),
and [ADR 0002](../../adr/0002-local-ingestion-immutable-archive-and-replay.md).
No new readiness/architecture assessment or acceptance criteria were produced.

## B. Baseline

```text
6290648 test: complete pre-live OMIE engineering audit
```

Operator-recorded baseline: existing `main`, clean working tree, local `main`
seven commits ahead of `origin/main`. Pre-live verdict:

```text
GO — NO DETECTABLE ENGINEERING BLOCKER
```

The audit explicitly established: **Local test success does not guarantee live
provider success.** Its 952-test baseline predates the 16 Stage 6 CLI cases.

Current local inspection confirms `main`, HEAD `6290648`, and seven commits
ahead of the locally stored `origin/main` reference. No fetch was performed;
this says nothing about remote freshness. Initially only the two Stage 6
implementation/test paths were untracked; tracked and cached diffs were empty.

## C. Files changed

Exactly these Stage 6 additions are present; no existing tracked file changed:

| Path | Role |
| --- | --- |
| `src/iberian_shakti/ingestion/omie/live_smoke.py` | Operator-added CLI: validated arguments, authorization, production composition, safe JSON and outcome exit codes. |
| `tests/unit/ingestion/omie/test_live_smoke.py` | Operator-added 16 offline CLI cases. |
| `docs/codex/reports/phase_1_stage_6_live_validation.md` | This authoritative Stage 6 implementation and evidence report, added during this task. |

The two operator-added Python files were inspected without modification.
The actual composition is:

```text
CLI argument validation
→ explicit --live gate
→ safe archive-root / validated settings
→ OmieAdapter + HttpRetriever + LocalRawArchive + SourceRequest
→ ingest()
  → adapter.resolve(): exact revision OR bounded latest-observed discovery
  → HttpRetriever report acquisition, using existing RetryPolicy
  → persist_retrieval(): immutable raw bytes and retrieval provenance
  → OmieAdapter.parser / OMIE calendar / shared interval contracts
  → persist_parse(): separate parse provenance
  → IngestionResult
→ allowlisted JSON summary and exit status
```

No alternate ingestion runner, parser, archive or retry implementation was
introduced. The same production retriever supplies listing and report
capabilities. The CLI omits `parsed_at`, allowing the existing runner to capture
parse time after acquisition persistence. Summaries select scalar fields;
unexpected exception text is replaced by a static error code.

## D. Explicit live authorization boundary

Operator-executed authorization check, before the live requests:

```bash
python -m iberian_shakti.ingestion.omie.live_smoke \
  --delivery-date 2026-10-26 \
  --revision 1 \
  --archive-root /tmp/iberian-shakti-omie-smoke
```

Observed stdout:

```json
{"error_code":"live_authorization_required","verdict":"not_run"}
```

Observed shell exit code: **2**. Missing `--live` prevents execution.
Argument parsing requires `--delivery-date` and `--archive-root`; revision is
optional, positive and canonical. Date syntax must be canonical `YYYY-MM-DD`.

Inspection confirms the first operation in `run()` checks authorization and
returns before archive-root processing, settings loading, adapter/retriever/
archive/request construction or `ingest()`. Module import does not initiate
provider access. Default behavior is zero network use. The corresponding test
replaces retriever construction with a rejection function and verifies the exact
JSON/return code. Authorized execution rejects a resolved root equal to or
beneath `tests/data/omie`, before retriever construction. The explicit CLI root
overrides the archive-root setting. The observed live root was outside Git.

## E. Offline CLI verification

The operator's final focused CLI run collected **16 tests: 16 passed**.
Independent offline rerun during this task:

```text
python -m pytest tests/unit/ingestion/omie/test_live_smoke.py -q
16 passed in 0.53s
```

Actual test coverage, including parameterized cases:

| Cases | Verified behavior |
| ---: | --- |
| 1 | Missing `--live`: exact refusal JSON, authorization return code, no retriever construction. |
| 1 | `tests/data/omie` archive root: configuration failure before retriever construction. |
| 4 | Revisions `0`, `-1`, `01`, `abc`: argparse rejection with exit 2. |
| 3 | Dates `2026-10-32`, `26-10-2026`, `2026/10/26`: argparse rejection with exit 2. |
| 1 | `/tmp/iberian-shakti-omie-smoke` is accepted as a safe root. |
| 1 | Exact wiring: no listing call, one report call, success/hash/revision/96 periods/96 PT/96 ES/192 records, exact archived bytes. |
| 1 | Latest-observed wiring: one fake listing call and one fake report call, revision 1, success and 192 records. |
| 1 | Report 404: unavailable exit, `not_found`, failed verdict, no listing call. |
| 1 | Complete report missing terminal marker: original malformed bytes archived, content failure exit, `content_invalid`, zero records. |
| 1 | Invalid discovery HTML: discovery failure exit and `discovery_schema`, no report retrieval. |
| 1 | Unexpected retriever-construction exception: internal failure exit with static JSON and no synthetic secret text. |
| **16** | **All offline.** |

Tests substitute `live_smoke.HttpRetriever` with an offline capability double;
they retain production settings, `SourceRequest`, adapter/resolver, runner,
archive, parser/calendar and result contracts. They do not exercise real HTTP
transport in these CLI cases or independently prove every CLI error branch.
Default pytest's existing `tests/conftest.py` denies DNS, outbound socket
operations and real HTTPX transports from configuration/collection onward.
The `--live` argument inside controlled tests cannot authorize real network I/O.

Operator-recorded full repository validation immediately before first live use:

| Command | Observed result |
| --- | --- |
| `ruff check .` | All checks passed. |
| `ruff format --check .` | 76 files already formatted. |
| `mypy src` | Success: no issues found in 33 source files. |
| `python -m pytest` | 968 passed in 8.42s; no failed tests. |
| `git diff --check` | No errors. |

At that time only the two Python paths in C were new/untracked. Operator-recorded
pre-live hook command:

```bash
pre-commit run --files \
  src/iberian_shakti/ingestion/omie/live_smoke.py \
  tests/unit/ingestion/omie/test_live_smoke.py
```

Ruff check, Ruff format, trim trailing whitespace, fix end of files,
check for added large files and detect private key all **Passed**.
Check YAML and check TOML were **Skipped** (no applicable files).

## F. Exact-revision live validation

Historical operator command, executed once:

```bash
python -m iberian_shakti.ingestion.omie.live_smoke \
  --live \
  --delivery-date 2026-10-26 \
  --revision 1 \
  --archive-root /tmp/iberian-shakti-omie-smoke
```

Observed safe stdout fields:

```json
{
  "archive_reference": "omie/marginalpdbc/2026-10-26/sha256/5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e/payload.bin",
  "attempt_count": 1,
  "byte_count": 2637,
  "delivery_date": "2026-10-26",
  "es_record_count": 96,
  "filename": "marginalpdbc_20261026.1",
  "first_interval_start_utc": "2026-10-25T23:00:00+00:00",
  "http_status": 200,
  "last_interval_end_utc": "2026-10-26T23:00:00+00:00",
  "normalized_record_count": 192,
  "observed_revision": 1,
  "parser_id": "omie.marginalpdbc",
  "parser_version": "1.0.0",
  "pt_record_count": 96,
  "report": "marginalpdbc",
  "selection_mode": "exact_revision",
  "sha256": "5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e",
  "source": "omie",
  "source_period_count": 96,
  "verdict": "pass"
}
```

Observed shell exit code: **0**. Exact revision 1 resolved to the selected
filename, report retrieval returned HTTP 200 on attempt 1, and 2,637 unchanged
raw bytes plus retrieval provenance were archived. Parsing succeeded and its
separate provenance persisted: 96 quarter-hour source periods, 96 PT and
96 ES records, 192 total, with the UTC boundaries shown above. CLI success is
returned only after required persistence completes.

Retained acquisition ID: `7b98e53f-c683-437e-a71a-1f0743aebbed`;
parse ID: `08da9820-2307-4163-b9e2-2972213aebbf`. Local typed metadata loads
and reprocessing confirm these fields. This proves the specific successful
interaction, without establishing a provider availability guarantee.

## G. Live-vs-fixture integrity comparison

The operator compared the exact live body with the committed fixture
`tests/data/omie/marginalpdbc_20261026.1`:

```text
fixture bytes: 2637
live bytes:    2637
fixture SHA-256:
5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e
live SHA-256:
5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e
```

**At the time of live validation, the committed fixture and OMIE's live
response were byte-for-byte identical.** Independent local verification checked
both hash/length and direct byte equality of the retained live payload and
fixture. The fixture has no diff against baseline/HEAD. No fixture was updated.
This observation does not establish permanent filename immutability or
equivalence of other reports to fixtures.

## H. Latest-observed discovery validation

Historical operator command, executed once:

```bash
python -m iberian_shakti.ingestion.omie.live_smoke \
  --live \
  --delivery-date 2026-10-26 \
  --archive-root /tmp/iberian-shakti-omie-smoke
```

Observed exit code: **0**; CLI verdict: **`pass`**.
Observed `selection_mode`: **`latest_observed`**. All other safe output fields
equal the exact-mode JSON in F: selected revision 1 and
`marginalpdbc_20261026.1`, HTTP 200, report `attempt_count: 1`, 2,637 bytes,
the same archive reference/SHA-256, parser `omie.marginalpdbc` version `1.0.0`,
96 periods, 96 PT, 96 ES, 192 normalized records and identical UTC boundaries.

The observed live listing was compatible with the implemented bounded parser
and permitted latest-observed resolution for this date. The chosen report was
successfully retrieved, archived and parsed. Retained acquisition ID:
`27670751-b641-4741-9754-c87279425b5d`; parse ID:
`16a465bb-5181-4159-8bb3-1bd19bd31921`.

**Attempt-count nuance:** the summary reads `result.retrieval.attempt_count`;
**1 belongs to report retrieval provenance**. Listing physical attempt count:
**not independently recorded**. Listing HTML is ephemeral and not retained in
the report archive; its successful compatibility is established by the
operator observation and the resolved latest-observed acquisition, not by a
new offline replay of that original HTML.

Under the recorded/current three-attempt retry policy, ceilings remain:

```text
exact mode:     maximum 3 physical report attempts
discovery:     maximum 3 listing + maximum 3 report = maximum 6 physical attempts
```

These are ceilings, not observed listing counts. The CLI obtains its policy
from validated ingestion settings; changing the configured attempt limit
would change those ceilings. The existing single retry engine and bounded
one-page discovery remain unchanged.

## I. Exact vs discovery comparison

| Observation | Exact revision | Latest observed |
| --- | --- | --- |
| Observed revision | 1 | 1 |
| Filename | `marginalpdbc_20261026.1` | `marginalpdbc_20261026.1` |
| Raw bytes | 2637 | 2637 |
| SHA-256 | `5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e` | `5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e` |
| Source periods | 96 | 96 |
| PT / ES / total records | 96 / 96 / 192 | 96 / 96 / 192 |
| UTC interval coverage | 2026-10-25 23:00 → 2026-10-26 23:00 | 2026-10-25 23:00 → 2026-10-26 23:00 |

Both paths converged to the same raw content identity and normalized result.
Independent offline parsing also compared every normalized record value
excluding only `parse_event_id`, which correctly differs between events.

## J. Archive verification

Operator inspection after both successful live acquisitions:

```text
payload files:    1
retrieval events: 2
parse events:    2
```

Identical bytes reuse one immutable content-addressed payload. Exact mode
added one acquisition event and discovery added a second independent event;
each ingestion added its own parse event. The two acquisition/parse pairs in
F and H remain present and linked to the same raw/archive reference. The
intermediate count is the operator's recorded observation; current inspection
also includes the subsequent replay event.

## K. Offline replay

After live acquisition the operator used `LocalRawArchive`, `replay()`, the
actual archived live payload and original latest-observed retrieval event,
then `OmieAdapter.parser` with a newly generated parse UUID. No `HttpRetriever`
was constructed and no provider request was made. Observed output:

```json
{
  "es_record_count": 96,
  "network_used": false,
  "new_parse_event_id": "969fa49d-7e61-43c5-9132-962c026877df",
  "normalized_record_count": 192,
  "original_retrieval_event_id": "27670751-b641-4741-9754-c87279425b5d",
  "parse_outcome": "success",
  "pt_record_count": 96,
  "retrieval_event_preserved": true,
  "sha256": "5427ac31d033e2b59acbcc78c372b6fd55fe32bb7a358d87a7b4ad9b4ee8124e",
  "source_period_count": 96,
  "verdict": "pass"
}
```

This preserves the original retrieval ID and raw hash while creating a distinct
successful parse event: 96 source periods, 96 PT, 96 ES and 192 records.
The retained replay JSON independently confirms original-acquisition linkage,
new parse ID, parser version, content identity and successful record count.
Inspection confirms `replay()` only loads verified payload/original retrieval
metadata; parser invocation and parse persistence are separate operations.

During this task a temporary read-only verification script used `LocalRawArchive`,
`replay()` and `OmieAdapter.parser` with the three already-recorded parse IDs and
times. It validated all retained provenance through the typed contracts,
reproduced each stored parse provenance and compared normalized values across
all three events. A Python audit hook rejected socket events and DNS helpers
were replaced with rejection functions. No retriever was constructed, no event
was persisted and before/after hashes of every archive file were identical.
This did not create a fourth parse event or another live acquisition.

## L. Archive state after replay

Operator-observed counts, independently confirmed locally:

```text
payload files:    1
retrieval events: 2
parse events:    3
```

| Event | ID | Meaning |
| --- | --- | --- |
| Retrieval 1 | `7b98e53f-c683-437e-a71a-1f0743aebbed` | Exact live acquisition. |
| Retrieval 2 | `27670751-b641-4741-9754-c87279425b5d` | Latest-observed live acquisition. |
| Parse 1 | `08da9820-2307-4163-b9e2-2972213aebbf` | Exact live parse, linked to retrieval 1. |
| Parse 2 | `16a465bb-5181-4159-8bb3-1bd19bd31921` | Discovery live parse, linked to retrieval 2. |
| Parse 3 | `969fa49d-7e61-43c5-9132-962c026877df` | Later offline replay parse, linked to retrieval 2. |

One immutable raw payload backs all events. Replay adds a parse observation,
not an acquisition: no new retrieval event and no new payload were created.
This is expected content-addressed archive behavior.

## M. Live compatibility corrections

**No live-discovered production compatibility correction was required.**

Local history still ends at pre-live baseline `6290648`; tracked working-tree
and index diffs are empty. Only the new Stage 6 CLI, its tests and this report
are present. The CLI is new Stage 6 functionality, not a compatibility
correction. The pre-live audit's earlier corrections were already in the
baseline and were not prompted by these live calls. No current code/history
evidence indicates a post-live change to the existing production path.

## N. Final offline validation

Named environment: `iberian_shakti`, Python **3.12.9**. All checks ran offline
after the report was drafted; no live module command was executed.

| Command | Exact observed result |
| --- | --- |
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `77 files already formatted` |
| `mypy src` | `Success: no issues found in 33 source files` |
| `python -m pytest` | `968 passed in 7.38s`; 968 collected, no failures or skips. |
| `git diff --check` | Exit 0; no output. |
| Focused Stage 6 command in E | `16 passed in 0.53s` |
| Read-only archive verification in K | Pass; zero network use, exact fixture equality, all three parse results equivalent, archive unchanged. |

Final applicable hook command:

```bash
pre-commit run --files \
  src/iberian_shakti/ingestion/omie/live_smoke.py \
  tests/unit/ingestion/omie/test_live_smoke.py \
  docs/codex/reports/phase_1_stage_6_live_validation.md
```

Exit **0**. Ruff check, Ruff format, trim trailing whitespace, fix end of files,
check for added large files and detect private key **Passed**. Check YAML and
check TOML **Skipped**, with no matching files. Pinned hook repositories and
installed environments were verified present in the local cache before running;
no initialization, download or external access was needed. Hooks were also
rerun against the completed report. No hook-generated content mutation remained.

All five requested Git inspections were completed. Working-tree/index diffs
and stats remain empty because all three Stage 6 additions are untracked.
Their contents were reviewed explicitly and checked with no-index diffs against
`/dev/null`; no added-file whitespace errors were found. Status lists exactly
the three paths in C, all `??`; nothing is staged. Existing source/fixture/hook
configuration diffs against baseline/HEAD are empty.

## O. External limitations

Successful Stage 6 live validation confirms real compatibility for the specific
observed OMIE interactions performed during this stage. It does not prove:

- Permanent endpoint availability, anonymous access, routing/DNS or TLS behavior.
- Permanent listing DOM stability, full pagination/retention behavior, complete
  historical revision coverage or a guaranteed latest-revision API.
- Publication time/SLA or every prepublication HTTP/body variant.
- Same-filename immutability, or unchanged bytes between listing and retrieval.
- Compatibility with every historical grammar or a contractual global charset.
- Absence of future provider changes.

Source publication time, publication SLA and listing physical attempt count
were **not independently recorded**. Retained HTTP observations record
`application/octet-stream`; Content-Encoding, ETag and Last-Modified are null.
No additional remote metadata or publication facts are inferred.

```text
local verification ≠ guaranteed live success
successful live observation ≠ permanent provider guarantee
```

## P. Scope confirmation

Stage 6 documentation and offline verification only. No Snowflake, dbt, ML,
API/dashboard, scheduling, other-provider work, cloud provisioning or
paid-resource action. No new network access, live call or provider DNS lookup.
No dependencies, fixtures, architecture, acceptance criteria or unrelated
files changed. No Stage 7 acceptance was performed.

Work remains on existing `main`. No branch was created and nothing was staged,
committed or pushed. Final Git review covers `git status --short`,
`git diff --stat`, `git diff`, `git diff --cached --stat` and
`git diff --cached`, plus explicit review/whitespace checks of the three
untracked additions (ordinary Git diffs omit them). Hook-generated changes were
checked and none remain unaccounted for.

## Q. Remaining Phase 1 work

Stage 7 — final Phase 1 documentation and acceptance verification

## R. Stage 6 verdict

PASS

Applies to Stage 6 only: operator-recorded exact/discovery observations,
verified local raw/provenance/replay evidence and green final offline checks.
This report makes no final Phase 1 acceptance decision.
