# Iberian_Shakti

**Predict. Explain. Empower. Save.**

Enterprise-style Iberian energy intelligence and electricity-price forecasting
platform for Portugal and Spain (MIBEL).

The intended system ingests market and related data, stores and transforms it
in Snowflake (RAW → CURATED → FEATURES → SERVING), trains and evaluates models
offline, runs **scheduled batch inference**, and serves **precomputed**
forecasts through FastAPI and a dashboard. Application and domain logic stay
portable; Snowflake is the planned central data, feature, model-governance, and
serving-data platform.

## Current status

Foundation phase. The repository layout and quality toolchain are in place;
runtime pipelines and serving are not.

Present today:

- Python 3.12 project (`pyproject.toml`) and `src/iberian_shakti` package
  skeleton (empty modules for ingestion, contracts, features, models, training,
  inference, monitoring, and common)
- `tests/` tree (`unit`, `integration`, `contracts`, `data`, `e2e`); no test
  modules yet, so `pytest` collects 0 tests
- Directory skeletons for `apps/`, `snowflake/`, `dbt/`, `infra/terraform/`,
  `docker/`, and `.github/workflows/`
- Environment template (`.env.example`) for ESIOS, ENTSO-E, and Snowflake
- Architecture, ADR, and runbook documentation under `docs/`

Not implemented: ingestion/transform/feature/training/inference logic, dbt
models, Snowflake SQL, Terraform, API, dashboard, or any provisioned cloud
resources.

Do not activate, provision, or modify paid cloud resources without explicit
instruction. Never commit secrets.

## Documentation

- [Architecture](docs/architecture/README.md) — data flow, package boundaries, ML and serving rules
- [Architecture Decision Records](docs/adr/README.md) — material decisions before implementation
- [Runbooks](docs/runbooks/README.md) — operational procedures (catalog only until services exist)

## Layout

| Path | Role |
| --- | --- |
| `src/iberian_shakti/` | Application package (skeleton) |
| `tests/` | `unit`, `integration`, `contracts`, `data`, `e2e` |
| `apps/` | API and dashboard (empty directories) |
| `snowflake/` | Snowflake SQL, roles, tasks, serving, governance (empty) |
| `dbt/` | Transformations and data-quality tests (empty) |
| `infra/terraform/` | Infrastructure as code (empty; DEV / STAGING / PROD env dirs) |

## Local development

Requires Python `>=3.12,<3.13`. Use the named pyenv virtual environment
`iberian_shakti` (do not create a separate `.venv`).

```bash
pyenv local iberian_shakti
python -m pip install -e ".[dev]"
cp .env.example .env
pre-commit install
```

Fill `.env` only via approved secret handling; never commit `.env`.

Quality gates:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Tests must not depend on live external APIs by default. Live-source validation
is explicit and separate from the deterministic suite.
