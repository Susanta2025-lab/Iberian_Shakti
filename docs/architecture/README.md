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

The repository is in a **foundation** phase. `src/iberian_shakti` and the
`tests/` tree exist as a typed package and test-layout skeleton. Pipelines,
Snowflake objects, and serving surfaces are **not implemented**. Do not treat
this document as a description of a running system.

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

## Logical data flow

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
packages currently exist as empty modules. Serving apps and platform folders
are repository-root skeletons. Keep these responsibilities separate. Do not
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

Ingestion adapter packages (stubs): `esios`, `entsoe`, `omie`, `ren`, `weather`.

Environment configuration (see `.env.example`; do not add secrets to the
repository):

- ESIOS and ENTSO-E: API tokens
- Snowflake: connection and authentication settings (account, user, password,
  role, warehouse, database, and schema)

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
