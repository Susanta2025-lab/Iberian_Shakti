# Architecture Decision Records

Significant technical and architectural decisions for Iberian_Shakti are
recorded here as Architecture Decision Records (ADRs).

The target architecture is described in
[`docs/architecture/README.md`](../architecture/README.md). ADRs capture *why*
a material choice was made, what alternatives were considered, and what
consequences follow.

## When to write an ADR

Write an ADR **before implementation** when a decision materially affects any
of the following:

- Data contracts or schemas
- Security, identity, or secret handling
- Infrastructure or cloud services
- Model lifecycle, promotion, or serving
- Production operations or environment boundaries (DEV / STAGING / PROD)
- Introduction of a major technology (for example Kafka, Kubernetes, or a
  streaming platform)

Do not use ADRs for routine implementation details. Prefer a small, reviewable
change plus an ADR only when the choice is durable.

## Status values

| Status | Meaning |
| --- | --- |
| Proposed | Under discussion; not yet accepted |
| Accepted | Binding until superseded |
| Superseded | Replaced by a later ADR (link the successor) |
| Deprecated | No longer in force; kept for history |

## File naming

Use a sequential, zero-padded number and a short kebab-case title:

```
docs/adr/0001-short-decision-title.md
```

Numbers are assigned in order and are never reused. Do not rewrite history;
supersede instead.

## Template

```markdown
# ADR NNNN: Title

- Status: Proposed | Accepted | Superseded | Deprecated
- Date: YYYY-MM-DD
- Deciders: (optional)

## Context

What problem or constraint requires a decision?

## Decision

What was chosen?

## Alternatives considered

What else was evaluated, and why was it rejected?

## Consequences

What becomes easier, harder, or newly constrained?

## Follow-up

Links to related ADRs, architecture docs, or implementation work.
```

## Index

| ADR | Status |
| --- | --- |
| [0001: OMIE day-ahead source and market-price contract](0001-omie-day-ahead-source-and-market-price-contract.md) | Accepted |
| [0002: Local ingestion execution, immutable archive, and replay](0002-local-ingestion-immutable-archive-and-replay.md) | Accepted |
| [0003: Multi-source query and measurement contracts](0003-multi-source-query-and-measurement-contracts.md) | Accepted |
| [0004: Private authentication and semantic provider outcomes](0004-private-authentication-and-semantic-outcomes.md) | Accepted |
| [0005: REN production profile and unresolved time gate](0005-ren-source-profile-and-time-gate.md) | Gate superseded by 0006 for profile 0.2.0; retained for 0.1.0 history |
| [0006: REN provisional source-period power semantics](0006-ren-provisional-period-semantics.md) | Accepted |

Founding constraints (MIBEL scope, Snowflake as
the planned data platform, batch inference with FastAPI serving precomputed
results, and rejection of Kafka/Kubernetes unless justified) are documented in
the architecture README until individual ADRs are recorded.
