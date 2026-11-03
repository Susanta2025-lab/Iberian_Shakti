# ADR 0006: REN provisional source-period power semantics

- Status: Accepted
- Date: 2026-11-03
- Supersedes: ADR 0005's normalization gate for operational profile 0.2.0;
  profile 0.1.0 and its recorded failures retain their original meaning.

## Context

[ADR 0005](0005-ren-source-profile-and-time-gate.md) blocked normalization
because timezone, label placement, DST fold ownership and exact MW statistic
were not provider-confirmed. Official REN material associates MW values with
15-minute periods. The retained [timing experiment](../codex/reports/phase_2_stage_2_ren_eredes_time_semantics_experiment.md)
found exact ordered 92/96/100-label compatibility with Europe/Lisbon. Blackout
chronology favors interval-start placement empirically; the cross-source
experiment remained inconclusive and did not prove the MW statistic.

The explicit [operator decision](../codex/prompts/phase_2/phase_2_stage_2_ren_revised_semantics_implementation.md)
accepts these measurements for price-forecasting inputs. That use needs honest
source-period power values, not settlement energy or proof of arithmetic mean
versus instantaneous sampling. This decision precedes implementation.

## Decision

Use REN profile/parser 0.2.0: Europe/Lisbon, 15-minute source periods,
interval-start labels, `provisional_empirical` time semantics. Generate physical
periods by stepping in UTC between independently converted civil-day midnights.
Require exact ordered equality of all labels and a supported 92/96/100 count.
Assign the two autumn 01h blocks by position to fold 0 then fold 1. Never
deduplicate, sort, fill, or move source values. Fail before any record emission
on a mismatch. New requests use the resulting physical source-day window.

Add only `Statistic.PROVIDER_PERIOD_VALUE` (`provider_period_value`): a
provider-reported measurement associated with a defined source period, whose
precise statistical aggregation is unknown. Use it only for interval-supported
system MW measurements. Preserve Decimal values exactly, without conversion,
rounding or derived fields. This statistic is neither a confirmed mean nor an
instantaneous measurement and must not authorize MW-to-MWh conversion. Any
future energy conversion requires an explicit semantic upgrade to a confirmed
statistic. Existing contract wire shapes and defaults stay unchanged.

Retain source series/day, value/unit, native profile and parse/retrieval linkage.
Original bytes contain labels and zero-based array positions; the validated
physical interval uniquely recovers that position, including autumn folds.
Reuse existing raw hashes and immutable acquisition/parse events. Profile
status belongs to the pinned REN profile; no generic confidence system or
redundant per-record provenance fields are needed.

## Alternatives considered

Continuing the mean-versus-instantaneous gate unnecessarily blocks forecasting.
Claiming an authoritative mean/instant or calculating MWh would overstate the
evidence. Fixed offsets, Madrid time or deduplication lose physical periods.

## Consequences

Valid days emit 11 measurements per physical period. Exact provider MW
statistic, authoritative label definition and autumn fold contract remain
unresolved, explicitly documented refinements rather than ingestion blockers.
Stage 2 may PASS under the revised acceptance rule; this does not close Phase 2
or authorize Stage 3, live validation or other products.

Future REN clarification requires a new profile/parser version and offline
replay of immutable acquisitions, with new parse events. The parser accepts the
exact legacy 0.1.0 query identity for replay as well as current 0.2.0 identity;
transport accepts only the current profile. Legacy query/report metadata and
old failed parse events are preserved. No migration or historical rewrite is
required; ADR 0005 and the original report remain the decision history.
