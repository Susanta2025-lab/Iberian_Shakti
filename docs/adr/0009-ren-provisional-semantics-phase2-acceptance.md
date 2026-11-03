# ADR 0009: REN provisional semantics for final Phase 2 acceptance

- Status: Accepted
- Date: 2026-11-03
- Decider: Project operator, by explicit final acceptance-policy authorization
- Supersedes: The stronger evidence condition of final Phase 2 criterion 4 for
  phase acceptance only. ADR 0006's operational semantics and evidence limits
  remain unchanged.

## Context

The original criterion remains verbatim in the authoritative checklist:

> REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly.

[ADR 0006](0006-ren-provisional-period-semantics.md) accepted the versioned
empirical profile for Stage 2 engineering. The Stage 9 review and targeted REN
investigation in the [final acceptance report](../codex/reports/phase_2_final_acceptance_report.md)
left criterion 4 NOT SATISFIED: official documentation and retained observations
did not establish provider-authoritative interval-edge semantics or physical
ownership of the two repeated autumn-hour value blocks. Deterministic parser
execution and matching 92/96/100 labels do not supply that missing evidence.

The operator has now explicitly authorized accepting those limitations for final
Phase 2 closure. The [exact authorization](../codex/prompts/phase_2/phase_2_ren_provisional_semantics_phase2_acceptance.md)
records that provider semantics are not fully established, project semantics
are explicit/deterministic/provisional, and Phase 2 acceptance is authorized.

## Decision

Phase 2 accepts REN profile/parser **0.2.0** as its operational contract despite
unresolved provider-authoritative timestamp placement and autumn value-to-fold
ownership. This is an **acceptance-policy replacement**, not new provider evidence.
The stronger final evidence condition is explicitly superseded for Phase 2
acceptance; the original criterion wording and earlier failed reasoning remain
preserved in the report history.

Classify final criterion 4 **SATISFIED WITH DOCUMENTED LIMITATION**, never simply
SATISFIED. Its implementation portion is satisfied: the pinned profile handles
ordinary/spring/autumn physical-day shapes deterministically, rejects unsupported
layouts and does not fabricate averaging semantics. The operator expressly
accepts the unresolved external timestamp/fold semantics as provisional for
Phase 2 closure. Criterion 5 retains its separate ESIOS native-unit-field
limitation; all other classifications remain unchanged.

Keep the exact existing REN contract:

| Property | Accepted value |
| --- | --- |
| Profile / parser | 0.2.0 / 0.2.0 |
| Timezone / cadence | Europe/Lisbon / 15 minutes |
| Support convention | interval_start, as project interpretation |
| Statistic | provider_period_value, Decimal MW without energy conversion |
| Evidence status | provisional_empirical |
| Ordinary / spring / autumn counts | 96 / 92 / 100, permanently tested |
| Repeated-hour assignment | Existing positional fold 0 then fold 1 policy |

No parser behavior, fold assignment, value, schema, query identity, provenance,
archive history or replay meaning changes. No new live request or production
code change is required. Unsupported layouts still fail atomically.

## Alternatives considered

Keeping the full phase open was required before explicit final policy authority
existed. It is now superseded by the operator's stated acceptance decision.
Claiming official interval-start semantics or proven autumn ownership would
fabricate evidence and remains prohibited. Silently changing the criterion,
profile meaning, evidence status or version would hide the decision history.

## Consequences

Subject to the final regression/quality gates, Phase 2 may close with **42
SATISFIED, 2 SATISFIED WITH DOCUMENTED LIMITATION, 0 NOT SATISFIED**. Acceptance
does not promote provisional_empirical to authoritative, settle mean versus
instantaneous MW, or grant production/commercial clearance.

Future feature engineering and data governance must retain the profile version
and its uncertainty: the interval edge and repeated-hour value ownership are
externally unconfirmed. Do not treat these measurements as authoritative
settlement energy or infer historical market-cutoff availability.

Future authoritative REN clarification may justify a new profile/parser version.
If interpretation changes or a correction is required, version it explicitly and
replay immutable acquisitions into new parse events. Never silently alter 0.2.0,
overwrite raw/retrieval/parse history, or erase its accepted replay evidence.
Earlier history remains valid evidence of the version used at that time.
This decision authorizes no Phase 3 implementation, provider request or cloud action.
