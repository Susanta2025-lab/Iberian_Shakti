# Operational Runbooks

Operational procedures, incident-response instructions, recovery procedures,
and production troubleshooting guides for Iberian_Shakti belong here.

Architecture is defined in [`docs/architecture/README.md`](../architecture/README.md).
Durable operational *policy* changes that alter architecture should be ADRs
([`docs/adr/`](../adr/README.md)); runbooks describe *how* to operate the
system as designed.

## Status

There is **no production system** yet. The repository is in a foundation phase.
These pages define the runbook catalog and operating rules so procedures can be
added as ingestion, Snowflake, inference, and serving are implemented.

Do not activate, provision, or modify paid cloud resources or Snowflake without
explicit instruction. Never put credentials, tokens, passwords, certificates, or
connection strings in runbooks; reference environment variables or approved
secret stores only.

## Operating principles

- Distinct **DEV**, **STAGING**, and **PROD** procedures; do not use production
  credentials or warehouses for local work.
- Least-privilege access. Do not bypass validation, authentication,
  authorization, auditing, or security controls.
- Prefer observable failure: timeouts, retries, backoff, and explicit alerts
  over silent retries.
- Important operational actions (model promotion, schema changes, warehouse
  resize, credential rotation) must be auditable.
- Prefer scheduled batch inference and serving of persisted forecasts. Do not
  run expensive model inference from the API as an incident workaround.

## Planned runbook catalog

Add one focused document per procedure as the corresponding capability exists.
Suggested filenames:

| Runbook | Purpose |
| --- | --- |
| `ingestion-failure.md` | External source outage, retries exhausted, duplicate or partial ingest |
| `data-quality.md` | Contract validation failures, dbt test failures, missing hours |
| `snowflake-access.md` | Role, warehouse, and schema troubleshooting (no secret values) |
| `feature-pipeline.md` | Feature build failure, training/serving feature drift |
| `inference-batch.md` | Scheduled forecast job failed, late, or produced empty serving tables |
| `serving-api.md` | API cannot read precomputed forecasts; stale or missing serving data |
| `model-promotion.md` | Promote or roll back a model only against explicit evaluation criteria |
| `incident-response.md` | Severity, communication, containment, and post-incident notes |
| `secret-rotation.md` | Rotate ESIOS, ENTSO-E, Snowflake, and app secrets without committing them |

## Runbook template

```markdown
# Runbook: Title

- Applies to: DEV | STAGING | PROD
- Last verified: YYYY-MM-DD
- Owner: (role or team)

## Symptoms

What operators observe.

## Immediate checks

Safe, read-only verification steps. No production writes.

## Mitigation

Smallest action that restores service within architecture boundaries.

## Recovery

Idempotent catch-up, replay, or rollback. Note data provenance constraints
(raw data is immutable).

## Escalation

When to stop and who owns the next decision (including any paid-resource change).
```

## Local development (until services exist)

1. Use Python 3.12 as specified in `pyproject.toml`.
2. Copy `.env.example` to `.env` locally; leave tokens empty unless you have
   been given them through an approved channel.
3. Do not run live external API checks as part of the normal test suite.
4. Quality gates: `ruff check .`, `ruff format --check .`, `mypy src`, and
   `pytest`. `tests/` exists; test modules are not implemented yet, so pytest
   currently collects 0 tests.
