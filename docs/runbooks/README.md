# Operational Runbooks

Operational procedures, incident-response instructions, recovery procedures,
and production troubleshooting guides for Iberian_Shakti belong here.

Architecture is defined in [`docs/architecture/README.md`](../architecture/README.md).
Durable operational *policy* changes that alter architecture should be ADRs
([`docs/adr/`](../adr/README.md)); runbooks describe *how* to operate the
system as designed.

## Status

There is **no deployed production system** yet. Phase 1 local OMIE ingestion,
archive and replay are implemented and CLOSED/PASS. Phase 2 is in progress
(shared foundation only; new provider integrations pending).
The [OMIE ingestion runbook](ingestion.md) covers the implemented operator path;
the catalog below lists future procedures, not existing services.

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

## Local development

1. Use Python 3.12 as specified in `pyproject.toml`.
2. Use the named `iberian_shakti` environment. Export ingestion settings
   explicitly when needed; `.env.example` is a template, not an automatic loader.
   Public OMIE ingestion needs no unrelated provider credentials.
3. Normal `python -m pytest` is network-denied from configuration/collection
   onward. Live smoke is a separate, deliberate `--live` operator action.
4. Quality gates: `ruff check .`, `ruff format --check .`, `mypy src`, and
   `python -m pytest` (968 passing cases at Phase 1 closure), followed by
   `git diff --check` and applicable pre-commit hooks.
