# Runbook: Local OMIE ingestion and replay

Applies to the implemented Phase 1 local workflow. Phase 1 is CLOSED/PASS;
Phase 2 is not started. There is no scheduler or deployed production service.
Last verified offline: 2026-10-27. Live evidence is the historical
[Stage 6 report](../codex/reports/phase_1_stage_6_live_validation.md);
Stage 7 made no provider request.

## Prerequisites and settings

Run from the repository root in the existing pyenv environment `iberian_shakti`
(Python 3.12), with the declared dependencies installed and host IANA timezone
data providing `Europe/Madrid`. OMIE uses the public anonymous `marginalpdbc`
route and requires no ESIOS, ENTSO-E or Snowflake credentials.

`load_ingestion_settings()` reads only these exported environment variables
(or an explicitly injected mapping). It does **not** load `.env`; copying
`.env.example` does not configure a process. Invalid settings fail validation
before acquisition; no archive is created by settings construction.

| Variable | Default | Meaning |
| --- | --- | --- |
| `RAW_ARCHIVE_ROOT` | `data/raw` | Archive root, relative to the process working directory unless absolute. The live CLI's required `--archive-root` overrides it after settings validation. |
| `INGESTION_TIMEOUT_SECONDS` | `10` | Positive finite connect/read/write/pool phase timeout. |
| `INGESTION_MAX_ATTEMPTS` | `3` | Positive total attempt count, including the first attempt. |
| `INGESTION_BACKOFF_SECONDS` | `1` | Finite nonnegative initial exponential backoff. |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR or CRITICAL for explicit library logging setup. |

Library entry points may call `common.logging.configure_logging()` explicitly;
imports do not configure handlers. Use the managed JSON formatter and controlled
event fields. Never dump payloads, models, raw headers, rejected validation
inputs, unchecked exceptions or transport URLs into logs. The live CLI emits
an allowlisted JSON outcome summary; it does not configure this logging handler.

## Default offline validation

```bash
python -m pytest
```

The repository-wide guard denies DNS, outbound socket operations and real
HTTPX sync/async transports from pytest configuration through collection and
execution. MockTransport, fake backends and local fixtures remain usable.
There is no environment variable, marker or pytest option enabling live access.
The guard prevents accidental Python network use; it is not an OS sandbox for
independent subprocesses/native code.

Full local quality gates are `ruff check .`, `ruff format --check .`,
`mypy src`, `python -m pytest` and `git diff --check`. Run applicable cached
pre-commit hooks against changed paths. Neither pytest nor pre-commit should
run a live provider check.

## Deliberate live smoke

These are command templates for an operator-authorized acquisition, not a
recurring test gate. Replace date, revision and path placeholders explicitly.
No further live run is needed to reproduce Stage 7 acceptance.

Exact revision (no listing request):

```bash
python -m iberian_shakti.ingestion.omie.live_smoke \
  --live \
  --delivery-date YYYY-MM-DD \
  --revision REVISION \
  --archive-root /some/operator-controlled/path
```

Latest observed (omit revision):

```bash
python -m iberian_shakti.ingestion.omie.live_smoke \
  --live \
  --delivery-date YYYY-MM-DD \
  --archive-root /some/operator-controlled/path
```

`--live` is mandatory and intentionally authorizes bounded network use. Without
it the command refuses before constructing acquisition dependencies. Dates
must be canonical `YYYY-MM-DD`; revisions are canonical positive integers.
The archive root must be operator-controlled and excluded from Git. Use ignored
`data/raw/` or an external custom root. **Never use `tests/data/omie` as a live
archive**; the CLI rejects that directory and its descendants when run from
the repository root. Fixtures and their manifest must retain their exact bytes.

The command uses the actual adapter → retriever → archive → parser → parse-event
path. A pass includes byte hash, selected revision, period/area counts and UTC
coverage, after required persistence. `attempt_count` describes report
retrieval; it does not record listing physical attempts. Event UUIDs live in
the stored metadata, not in the CLI summary.

| Exit | Outcome | Operator interpretation |
| --- | --- | --- |
| `0` | Pass | Archived complete report and successful persisted parse. |
| `2` | Missing `--live` or invalid arguments | No authorized acquisition; correct explicit inputs. |
| `3` | Unavailable | `not_found` or `not_listed`; no zero-record ingestion success. |
| `4` | Discovery failure/unknown coverage | Inspect safe outcome; an independently known exact revision bypasses the listing. |
| `5` | Retrieval/execution failure | Inspect stable error code; distinguish transport, status, encoding and budget failures. |
| `6` | Content failure | Complete raw report and failed parse retained; inspect/replay offline. |
| `7` | Archive failure | No ingestion success; preserve existing objects and investigate local storage. |
| `8` | Configuration/validation failure | Correct settings/inputs before another authorized run. |
| `70` | Unexpected internal failure | Static safe diagnostic; investigate locally without logging raw exception text. |

Passing local tests does not guarantee successful live validation.
A successful live observation does not guarantee permanent provider compatibility.

## Bounds and supported content

Default policy is three total attempts, with 1 then 2 seconds backoff (4-second
cap), 10-second phases, 30 seconds per attempt and 93 seconds per logical
acquisition including waits. Exact mode has at most three report attempts;
discovery has at most three listing plus three report attempts. An explicit
attempt-setting override changes these ceilings to N and 2N, subject to the
finite acquisition budgets. Listing and report have separate budgets, at most
186 seconds combined by default; local parsing/archive work is outside them.
Deadlines cooperate with host resolver/backend timeout behavior and do not
provide hard real-time preemption of a stalled OS call.

HTTP sends `Accept-Encoding: identity`, reads raw streams, uses verified TLS,
disables environment proxies/credentials and transport retries, and follows
zero redirects. Report limit is 4 MiB; discovery is one page, 1 MiB and 10,000
anchor candidates. There is no revision probing, polling or rediscovery loop.
Selected transient failures retry; permanent statuses/TLS failures do not.
Valid integer delta-seconds Retry-After must fit the remaining budget;
HTTP-date Retry-After uses bounded backoff instead.

Discovery selects the highest numeric revision observed for the date within
recognized coverage. Pagination/unrecognized or uncovered listings are explicit
coverage/schema outcomes, not evidence of historical absence. `.1` is not
assumed. Publication time/SLA, retention and complete revision history are not
guaranteed. A selected report's 404 ends that run without rediscovery.

Only the tested ASCII numeric `MARGINALPDBC;` grammar is supported: six fields
(year, month, day, sequential period, PT price, ES price), trailing semicolons,
LF/CRLF and a terminal `*`. Signed Decimal prices accept integers or one/two
fractional digits; negatives are valid. The complete day must match request,
filename and calendar. Both bidding areas use `Europe/Madrid`, not Lisbon
midnight or a fixed CET offset:

| Delivery date | Resolution | Ordinary / spring / autumn periods |
| --- | --- | --- |
| Before 2025-10-01 | 60 minutes | 24 / 23 / 25 |
| From 2025-10-01 | 15 minutes | 96 / 92 / 100 |

Each period yields PT then ES EUR/MWh records with UTC intervals. Unsupported
encoding, malformed rows or incomplete days produce zero normalized records,
without silently dropping rows or using an hourly fallback. Synthetic legacy
autumn/transition fixtures test those profiles; they do not establish original
provider bytes for those dates or compatibility with every historical grammar.

## Immutable archive and recovery

```text
<root>/omie/marginalpdbc/<delivery-date>/sha256/<sha256>/
  payload.bin
  retrievals/<retrieval-event-id>.json
  parses/<parse-event-id>.json
```

SHA-256 identifies unchanged complete response bytes, before decoding/newline
conversion. Retrieval events record safe source/date/filename/revision, UTC
completion, attempts/status, hash/length and archive linkage; parse events add
parser/schema versions, original retrieval ID, outcome and count. Publication
time remains null when unknown. Only allowlisted HTTP observations are retained.

Identical bytes reuse the payload while independent acquisitions add events.
Changed content, even under the same filename/revision, gets another hash
directory; prior bytes/events remain untouched. Never edit an archived payload,
event or mutable latest pointer to recover a revision. An operator can request
an independently known exact revision deliberately; neither listing coverage
failure nor 404 justifies brute-force probing or treating absence as success.

Complete malformed/empty/HTML 200 bodies are archived before failed parsing.
Interrupted/oversized bodies and HTTP error pages are not successful raw reports.
Archive or event-persistence failure prevents ingestion success. An orphan
complete payload may remain after a metadata failure; it is not replayable
acquisition history without the actual original provenance. If the caller
retains that acquisition result, explicit persistence can verify/reuse it.
Never fabricate missing retrieval history. Investigate disk/permission/fsync
faults and checksum/event conflicts without replacing immutable objects.

The archive requires a trusted local directory tree, same-filesystem hard
links and directory fsync. It does not protect against hostile owner changes,
directory-swap attacks or promise network-filesystem/WORM guarantees. A killed
process can leave private staging files; these are not published payloads.

## Offline replay

```text
previously archived raw payload + original retrieval provenance
  → replay(archive, archive_reference, original_retrieval_event_id)
  → same verified raw content + original retrieval provenance
  → parser.parse(..., parsed_at=<UTC>, parse_event_id=<new UUID>)
  → archive.persist_parse(parsed.provenance)
```

Use `LocalRawArchive`, `ingestion.replay.replay()` and `OmieAdapter().parser`.
Choose the archive reference and original acquisition UUID from that operator's
retained retrieval metadata, validated as `RetrievalProvenance`; do not copy
temporary Stage 6 UUIDs into permanent procedures. `replay()` itself only loads
and verifies content and original acquisition linkage. It performs no new
acquisition, creates no retrieval event or payload, and never falls back to HTTP
on corruption/missing history. Parsing and persisting a new parse event are
separate explicit calls, using a new UUID and aware UTC parse time.

For fixed raw bytes and parser/schema versions, normalized values, business
identities and normalized-content identity reproduce. Parse time/UUID can
differ. A parser-version change can change normalized-content identity without
changing the original raw object or acquisition history. Replay supports
parser upgrades, reprocessing, reproducibility and auditing, including repeat
diagnosis of malformed reports.

## Deferred scope

REN, ESIOS, ENTSO-E, Open-Meteo and MIBGAS; Snowflake, dbt, feature engineering,
ML training, model registry, batch forecasts, FastAPI, dashboard, production
scheduler and infrastructure deployment remain future work. No paid-resource
action is part of this local workflow. See the
[closure report](../codex/reports/phase_1_stage_7_final_acceptance.md) for the
accepted limitations and future phase sequence.
