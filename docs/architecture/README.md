# Iberian_Shakti Architecture

**Predict. Explain. Empower. Save.**

Iberian_Shakti is an enterprise-style, production-oriented energy intelligence
and electricity-price forecasting platform for Portugal and Spain (MIBEL).

This directory is the authoritative architecture documentation. Architecture
decisions that materially affect data contracts, security, infrastructure,
model lifecycle, or production operations must be recorded as ADRs
([`docs/adr/`](../adr/README.md)) before implementation.

Operational procedures live in [`docs/runbooks/`](../runbooks/README.md).

## Status

Phase 0 and Phase 1 are **CLOSED/PASS**; Phase 2 is in progress. Stage 1
implements shared multi-source contracts/request security. Stage 2 implements
REN acquisition/chart validation and provisional empirical source-period UTC
normalization under profile 0.2.0. ESIOS, ENTSO-E and Open-Meteo remain pending. Phase 1
implements local OMIE ingestion, immutable archival, provenance and offline
replay, verified by the
[final acceptance report](../codex/reports/phase_1_stage_7_final_acceptance.md).
Snowflake, transformations, features, ML, forecasting, serving and deployment
remain planned. There is no deployed production service.

Paid cloud resources and Snowflake must not be activated, provisioned, or
modified without explicit instruction.

## Design principles

- Production architecture, not a demo-only application.
- Clear separation between ingestion, transformation, features, training,
  inference, serving, monitoring, and infrastructure.
- Snowflake is the planned central data, feature, model-governance, and
  serving-data platform.
- Scheduled batch inference with forecasts persisted to serving tables.
- FastAPI serves precomputed results; it does not trigger expensive model
  inference on request.
- Application and domain logic stay reasonably portable; avoid unnecessary
  vendor lock-in.
- Simple, justified architecture over unused infrastructure.
- Kafka, Kubernetes, streaming platforms, service meshes, and extra cloud
  services are out of scope unless a demonstrated requirement justifies them.

## Implemented Phase 1 flow

```text
OMIE public source
  → SourceRequest
  → exact revision OR bounded latest-observed discovery
  → bounded HTTP retrieval
  → immutable raw archive
  → retrieval provenance
  → strict OMIE parsing
  → Europe/Madrid calendar normalization
  → PT / ES MarketPrice records
  → parse provenance
```

`contracts/` owns strict frozen request, resolution, acquisition, archive,
parse and market schemas plus synchronous protocols. `ingestion/` owns
configuration, transport, retry/error policy, local files, archive, replay and
the runner; `ingestion/omie/` owns provider identity, discovery, grammar and
calendar policy. `common/` owns the explicit safe logging boundary.

The runner persists complete raw bytes and acquisition metadata **before**
parsing. A complete malformed 200 body remains archived with a separate failed
parse event and zero normalized records. Interrupted/oversized acquisitions
do not become complete archived reports. Persistence failures prevent success.

Raw bodies use SHA-256 identity and atomic no-replace local publication;
new acquisitions and parses are separate immutable events. Identical bytes
reuse one payload; changed bytes under the same filename/revision remain
separate versions. This assumes a trusted local filesystem with hard-link and
fsync support; it is application immutability, not WORM storage.

```text
immutable archive + original retrieval provenance
  → verified offline replay
  → same OMIE parser and calendar
  → normalized records + new parse event
```

Replay loads verified bytes and original acquisition history. It creates
neither a new payload nor a retrieval event; parsing and persistence of a new
parse event are explicit separate calls.

One `marginalpdbc` report supplies PT and ES Decimal prices in EUR/MWh. Both
areas use `Europe/Madrid`, with separately converted local midnight boundaries
and UTC interval stepping. Before 2025-10-01 the ordinary/spring/autumn profiles
are 24/23/25 hourly periods; from that date they are 96/92/100 quarter-hours.
There is no fixed CET offset or hourly fallback. Only the tested strict ASCII
numeric grammar is supported; complete days are validated before emission.

Discovery reads one page, bounded to 1 MiB and 10,000 anchor candidates;
numeric revision selection is latest observed, not complete historical coverage.
Pagination or uncertain coverage fails explicitly; exact revision bypasses
listing discovery. HTTP uses identity raw streaming, no redirects and one
bounded retry policy. See [ADR 0001](../adr/0001-omie-day-ahead-source-and-market-price-contract.md),
[ADR 0002](../adr/0002-local-ingestion-immutable-archive-and-replay.md) and the
[runbook](../runbooks/ingestion.md) for limits, settings and recovery.

Default pytest denies network use. The separate live command requires `--live`.
Passing local tests does not guarantee successful live validation.
A successful live observation does not guarantee permanent provider compatibility.
The [Stage 6 observations](../codex/reports/phase_1_stage_6_live_validation.md)
establish compatibility only for those recorded interactions.

## Phase 2 shared foundation

[ADRs 0003/0004](../adr/README.md) record API snapshot/query identity,
system/weather measurements, explicit source timing/geography/units, private
fixed-origin authentication and semantic HTTP-200 outcomes. The closed record
union includes unchanged MarketPrice; version-1 history retains its wire shape
and version-2 API/measurement events are explicit. Raw paths/hashes/atomic
publication and offline replay are reused without migration. A shared
`ingest_resolved` chain handles persisted acquisition before parsing.

The private request policy injects header/query credentials outside safe query
contracts, rejects origin changes and active-credential echoes before payload
publication, and keeps raw streaming/retry/deadline rules. It is not a general
secret detector; authenticated nonidentity bodies fail before publication.
REN supplies a pinned production chart profile. Historical profile 0.1.0 blocked
normalization ([ADR 0005](../adr/0005-ren-source-profile-and-time-gate.md));
[ADR 0006](../adr/0006-ren-provisional-period-semantics.md) accepts profile 0.2.0:
15-minute Europe/Lisbon interval-start periods, `provisional_empirical`, with
ordered DST mapping. Strict full-day label validation precedes emission of
source-native Decimal MW `provider_period_value` records. This additive system
statistic requires interval support and cannot represent MWh; it does not prove
an arithmetic mean or authorize energy conversion. Weather semantics and legacy
serialization remain unchanged. The shared runner/archive/replay are unchanged.
New parse events can reinterpret exact legacy acquisitions without rewriting
their original query or failed parse events. No new live command or XML
parser is implemented. See the [Stage 1 report](../codex/reports/phase_2_stage_1_report.md)
for deterministic evidence and remaining provider-stage work.

## Planned end-to-end data flow

```
External sources
  → ingestion
  → validation / contracts
  → immutable raw storage
  → Snowflake RAW
  → CURATED
  → FEATURES
  → training / evaluation
  → model registry
  → scheduled inference
  → SERVING
  → API / dashboard
```

Pipeline expectations:

- Preserve raw source data and provenance; do not destructively transform
  source data.
- Transformations are reproducible and deterministic where practical.
- Training and serving feature definitions must not drift apart.
- Pipelines are idempotent where possible; duplicate ingestion is handled
  explicitly.

## Repository layout

Python application code lives under `src/iberian_shakti` (Python 3.12). Domain
packages outside ingestion, contracts and shared logging remain empty stubs.
Serving apps and platform folders are repository-root skeletons. Keep these
responsibilities separate. Do not
move business logic into API routes, dashboards, Terraform, or SQL merely for
convenience.

| Path | Responsibility |
| --- | --- |
| `src/iberian_shakti/ingestion/` | External-source acquisition, retries, provenance, source-specific parsing |
| `src/iberian_shakti/contracts/` | Schemas, validation rules, interfaces, shared data contracts |
| `src/iberian_shakti/features/` | Deterministic feature engineering |
| `src/iberian_shakti/models/` | Model definitions and model-specific logic |
| `src/iberian_shakti/training/` | Training, evaluation, experiment execution, promotion logic |
| `src/iberian_shakti/inference/` | Forecast generation and inference workflows |
| `src/iberian_shakti/monitoring/` | Data quality, drift, model performance, pipeline and service monitoring |
| `src/iberian_shakti/common/` | Genuinely shared utilities only |
| `apps/api/` | Serving interfaces and API-specific logic |
| `apps/dashboard/` | Presentation and dashboard logic |
| `snowflake/` | Snowflake-specific SQL, roles, tasks, serving structures, and governance |
| `dbt/` | Transformation models and data-quality tests |
| `infra/terraform/` | Infrastructure as code |
| `tests/` | `unit`, `integration`, `contracts`, `data`, `e2e` |

OMIE is implemented. REN acquisition/validation and provisional empirical
normalization are implemented; authoritative label/statistic/fold definitions
remain unresolved refinements. `esios`, `entsoe`
and `weather` remain stubs: ESIOS pending, ENTSO-E pending, Open-Meteo pending.
MIBGAS remains deferred. Phase 2 is in progress.

Environment configuration (see `.env.example`; do not add secrets to the
repository):

- Phase 1 reads only local archive, timeout, attempt, backoff and log-level
  settings explicitly, without automatic `.env` loading or provider credentials.
- A separate explicit selected-provider loader reads only ESIOS_API_TOKEN or
  ENTSOE_API_TOKEN when requested; anonymous sources read neither. No authenticated adapter
  uses them yet; REN remains anonymous. Phase 1 does not read these tokens or Snowflake placeholders.

Snowflake subdirectories (`raw`, `curated`, `features`, `serving`, `ml`,
`roles`, `tasks`, `audit`) and Terraform environment dirs (`dev`, `staging`,
`prod`) exist as empty placeholders.

## ML and serving

- Establish simple baselines before advanced models.
- Prefer evidence-based model selection.
- Treat XGBoost or another strong tabular baseline as a production candidate
  before complex deep-learning models.
- Keep training separate from online / request-time serving.
- Prefer scheduled batch forecasting with persisted predictions.
- Track model version, data version, feature version, evaluation metrics, and
  forecast generation time.
- Do not promote models without explicit evaluation criteria.

## Environments and operations

- Maintain distinct **DEV**, **STAGING**, and **PROD** boundaries.
- Least-privilege access; do not bypass validation, authentication,
  authorization, auditing, or security controls for convenience.
- External integrations use timeouts, retries, backoff, and observable
  failures. Avoid single points of silent failure.
- Important operational actions are auditable.
- Never expose, print, hard-code, or commit credentials, API tokens,
  passwords, certificates, or secrets. Read configuration from environment
  variables or approved configuration mechanisms.

## Changing the architecture

Do not change this architecture without explaining the reason first and, when
the change is material, recording an ADR. If a requested change conflicts with
these boundaries, document the conflict before implementing it.
