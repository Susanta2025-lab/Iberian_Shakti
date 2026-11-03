# ADR 0008: ESIOS bounded five-minute request semantics

- Status: Accepted for the explicitly bounded profile after controlled Stage 8 confirmation
- Date: 2026-11-03

## Context

The retained indicator-544 response to UTC 2026-10-24 00:00 through
2026-10-25 00:00 contains 301 five-minute samples through 01:00 UTC.
The requested endpoint is Madrid 02:00+02:00 (fold 0); the last returned
sample is Madrid 02:00+01:00 (fold 1). All local timestamps agree with UTC.
There are twelve samples after the endpoint and one exactly at it: thirteen
outside a half-open logical window. This is consistent with inclusive selection
ending at the later occurrence of an ambiguous local endpoint, but does not
prove the provider's internal algorithm.

The [official range-filter documentation](https://api.esios.ree.es/doc/indicator/getting_a_specific_indicator_filtering_values_by_a_date_range.html)
defines ISO-8601 start/end filters. It does not explicitly define inclusivity,
timezone comparison or fold policy. Its illustrative response includes a local
endpoint, but its UTC bounds and sample times are inconsistent; the official
site describes calls as examples. It cannot establish a UTC filtering contract.

Stage 3 deliberately permits an inclusive response endpoint in profile 0.1.0.
Making that profile strictly half-open would change accepted parse semantics.

## Decision

Use an explicit opt-in profile/parser 0.2.0, report `indicator544.v0.2.0`.
Its logical QueryWindow remains unchanged and half-open. For native grid-aligned
boundaries, send start unchanged and end minus 300 elapsed UTC seconds. Only
these two ISO-8601 UTC parameters are sent; no aggregation or timezone override.
Reject ambiguous Madrid wire boundaries before acquisition rather than assume
which fold the provider will select. Spring-forward arithmetic occurs in UTC;
no nonexistent local instant is constructed. Non-grid windows fail locally.

The parser validates every value and rejects the entire response if any sample
precedes start or is at/after end. Local/UTC/offset consistency, source metadata,
Decimal values, gaps and unknown forecast issuance retain existing meanings.
There is no filtering, sorting, clipping, filling or widened business window.
Profile 0.1.0 construction, parser outcomes and replay remain unchanged.

Versioning is intentional: the wire correction alone could retain logical query
identity, but enforcing exclusive response support changes Stage 3's accepted
meaning. The new report version therefore creates a distinct canonical query
identity while preserving the exact logical window. No shared contract changes.

## Alternatives considered

Silently changing 0.1.0 would change accepted history. Keeping its inclusive
parser would not enforce this task's exclusive-end requirement. Clipping or
widening would hide provider violations. Guessing fold conversions or making
additional exploratory requests is unjustified.

## Consequences

The one authorized targeted request tested the same logical business window after
offline boundary/DST/identity/atomic-failure/replay regressions passed. It returned
288 samples from 2026-10-24 00:00 through 23:55 UTC, with no out-of-window data,
matching local offsets and equal denied replay. Its 71,973 original bytes have
SHA-256 `476aecfc4b13b6ada038aabbd6cfce792d2c1804d62a1b87b08b96eb6f3de7ae`.
See the [Stage 8 continuation report](../codex/reports/phase_2_stage_8_controlled_live_validation_report.md#24-targeted-esios-544-semantics-resolution-continuation).
Ordinary/spring/autumn synthetic tests validate our arithmetic and rejection
policy, not unobserved provider behavior for those dates. Ambiguous wire
boundaries remain unsupported pending authoritative clarification. Raw and old
failed parse/replay events are immutable; no retrospective successful parse is
claimed. No other provider or Stage 9 is in scope.
