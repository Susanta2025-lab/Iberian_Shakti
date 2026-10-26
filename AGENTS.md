# AGENTS.md

## Project

**Iberian_Shakti — Predict. Explain. Empower. Save.**

Iberian_Shakti is an enterprise-style, production-oriented Iberian energy intelligence and electricity-price forecasting platform for Portugal and Spain (MIBEL).

Read the repository architecture and relevant ADRs before making substantial changes.

Primary references:

- `README.md`
- `docs/architecture/README.md`
- `docs/adr/README.md`
- `docs/runbooks/README.md`

## Development principles

- Use Python 3.12.
- Preserve the existing `src/iberian_shakti/` package layout.
- Keep ingestion, contracts, features, models, training, inference, monitoring, serving, and infrastructure clearly separated.
- Prefer small, reviewable changes.
- Do not rewrite unrelated files.
- Do not change established architecture without explaining the reason.
- Add dependencies only when required by the task.
- Keep application/domain logic reasonably portable.
- Avoid unnecessary infrastructure complexity.

## Architecture guardrails

The intended flow is:

External sources
→ ingestion
→ validation/contracts
→ immutable raw storage
→ Snowflake RAW
→ CURATED
→ FEATURES
→ training/evaluation
→ model registry
→ scheduled inference
→ SERVING
→ API/dashboard

Snowflake is the planned central data, feature, model-governance, and serving-data platform.

Prefer scheduled batch inference. FastAPI should primarily serve precomputed results rather than run expensive model inference per request.

Do not introduce Kafka, Kubernetes, streaming platforms, service meshes, or additional major infrastructure unless explicitly justified by requirements.

## Data and ingestion

- Preserve original raw source payloads and provenance.
- Raw archives are immutable.
- Never overwrite an archived raw payload with a revised source version.
- Treat revisions as separate immutable versions.
- Design ingestion to be replay-safe and idempotent where practical.
- Use explicit finite timeouts for external calls.
- Retries must be bounded and use backoff.
- Distinguish retryable failures from permanent or expected-unavailable responses.
- Never silently discard malformed or invalid records.
- Keep live external-source tests separate from the deterministic default test suite.

## Python quality

Code must remain compatible with:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Use typed, maintainable Python.

Do not suppress linting or type errors merely to make checks pass.

Do not weaken tests simply to obtain a green result.

## Testing

Use the existing test structure:

- `tests/unit/`
- `tests/contracts/`
- `tests/integration/`
- `tests/data/`
- `tests/e2e/`

Prefer deterministic fixtures and mocked external services for normal tests.

Real external API calls must be explicit and opt-in.

Never put real credentials or secrets in tests or fixtures.

## Security and secrets

Never:

- hard-code credentials or tokens
- print secrets
- commit `.env`
- commit private keys or certificates
- expose credentials in logs or diagnostics

Use environment variables or approved secret-management mechanisms.

## Cloud and cost controls

Do **not** activate, provision, resize, modify, or delete paid cloud resources without explicit user instruction.

This includes Snowflake and any AWS, Azure, GCP, or other paid infrastructure.

Do not assume permission to make cloud changes merely because credentials or configuration are available.

## Change workflow

For substantial work:

1. Inspect the current repository state.
2. Read relevant documentation and ADRs.
3. Define or confirm the scope.
4. Implement the smallest coherent change.
5. Add or update relevant tests.
6. Run applicable quality gates.
7. Review `git diff`.
8. Report results, limitations, and remaining risks.

Do not automatically commit or push unless explicitly instructed.

## Git workflow

Development currently occurs directly on the existing main/master branch unless the user explicitly requests another branch.

Before any commit, verify:

```bash
ruff check .
ruff format --check .
mypy src
pytest
git diff --check
git status
git diff
```

Only commit or push after the user is satisfied with the implementation and validation results.

## Current project scope

Do not infer that planned components are already implemented.

Always inspect the repository before describing current status.

When working on a numbered phase, remain inside that phase's defined scope unless an explicit dependency requires otherwise.
