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

- Phase 0 — CLOSED/PASS
- Phase 1 — CLOSED/PASS
- Phase 2 — not started

The [Phase 1 final acceptance report](docs/codex/reports/phase_1_stage_7_final_acceptance.md)
traces all 22 original acceptance criteria to implementation and verification.

Present today:

- OMIE day-ahead marginal-price ingestion (`marginalpdbc`), using exact revision
  selection or bounded latest-observed discovery from one listing page
- Strict complete-report parsing into PT and ES normalized `MarketPrice`
  records, with signed Decimal EUR/MWh prices and Europe/Madrid delivery periods
- Legacy hourly and modern quarter-hour profiles, including DST and the
  2025-10-01 resolution transition
- Bounded synchronous HTTP/local-file retrieval, immutable local raw archive,
  retrieval and parse provenance, checksum-verified offline replay
- Validated environment settings and an explicit secret-safe logging boundary
- Operator-controlled live smoke command with mandatory `--live`; successful
  exact/discovery observations and offline replay recorded in the
  [Stage 6 report](docs/codex/reports/phase_1_stage_6_live_validation.md)
- 968 deterministic tests; default pytest denies network access, including
  DNS, outbound socket operations and real HTTPX transports
- Directory skeletons for `apps/`, `snowflake/`, `dbt/`, `infra/terraform/`,
  `docker/`, and `.github/workflows/`

Future scope: REN, ESIOS, ENTSO-E, Open-Meteo and MIBGAS integrations; Snowflake,
dbt, feature engineering, ML training, model registry, batch forecasts, FastAPI,
dashboard, production scheduler and infrastructure deployment. These are not
implemented. Phase 1 operates locally; it is not a deployed production service.

Passing local tests does not guarantee successful live validation.
A successful live observation does not guarantee permanent provider compatibility.
Discovery establishes only the latest revision observed within its bounded
coverage; it does not establish complete historical revisions or retention.

Do not activate, provision, or modify paid cloud resources without explicit
instruction. Never commit secrets.

## Documentation

- [Architecture](docs/architecture/README.md) — data flow, package boundaries, ML and serving rules
- [Architecture Decision Records](docs/adr/README.md) — material decisions before implementation
- [Runbooks](docs/runbooks/README.md) — implemented local procedures and future catalog
- [OMIE ingestion runbook](docs/runbooks/ingestion.md) — settings, offline validation, deliberate live smoke, recovery and replay

## Layout

| Path | Role |
| --- | --- |
| `src/iberian_shakti/` | Implemented ingestion/contracts/logging; future domain package stubs |
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

The ingestion settings loader does **not** load `.env`. Export settings
explicitly; see the [runbook](docs/runbooks/ingestion.md). OMIE requires no
ESIOS, ENTSO-E or Snowflake credentials. Never commit `.env` or secrets.
Host IANA timezone data providing `Europe/Madrid` is required.

Quality gates:

```bash
ruff check .
ruff format --check .
mypy src
python -m pytest
```

Tests are network-denied by default, with no live-enabling pytest switch.
Live-source validation is an explicit separate operator action; it is not
invoked by pytest, pre-commit or automatic CI. Keep raw archives under ignored
`data/raw/` or an operator-controlled external root, never `tests/data/omie`.
