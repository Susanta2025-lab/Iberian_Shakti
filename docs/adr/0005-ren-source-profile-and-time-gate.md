# ADR 0005: REN production profile and unresolved time gate

- Status: Accepted
- Date: 2026-10-28

## Context

Phase 2 Stage 2 selects only the documented REN DataHub
`ElectricityProductionBreakdownDaily` product. ADRs 0001–0004 and the sole
[readiness assessment](../codex/reports/phase_2_readiness_assessment.md) remain
unchanged. This decision precedes REN implementation.

[Official API instructions](https://datahub.ren.pt/en/api-instructions) document
JSON, culture/date parameters and the fixed public endpoint. The inspected
[Portuguese daily page](https://datahub.ren.pt/pt/eletricidade/balanco-diario/)
describes quarter-hour periods without defining label start/end or averaging.
The [DataHub description](https://datahub.ren.pt/en/) describes provisional
metering/estimates and update cadence. Neither update cadence nor these
statements prove the required timestamp convention.

Two bounded observations on 2026-10-28 show ordinary/spring arrays of 96/92
labels. The readiness autumn response has 100 labels, repeating 01h. These
corroborate a Lisbon-like clock, but contain no offset or timestamp-statistic
metadata. No independently timestamped export or explicit convention was
established in the limited official material inspected. This is a specific
semantic gate, not another readiness assessment.

## Decision

Implement fixed-origin anonymous acquisition and strict complete chart validation
using existing API requests, HttpRetriever, archive, runner and offline replay.
Profile `0.1.0` explicitly has **unknown timezone, label meaning and statistic**.
Otherwise valid bytes produce `content_failure / time_semantics_unknown`, zero
SystemMeasurement records and persisted measurement parse provenance. No runtime
switch, user-supplied timezone, assumed fold, or provisional UTC normalization
can bypass this gate. A future evidence-backed profile/parser revision is needed.

Use source ID `ren` and versioned report identity
`ElectricityProductionBreakdownDaily.en-US.v0.1.0`. This contains the exact
product, sole culture and pinned profile in the existing safe query identity,
without adding optional query fields or changing Stage 1 serialization. The
request's UTC midnight-to-midnight window is **project partition context only**;
it does not declare REN's local-day boundaries or returned support. Transport
uses only the validated partition date and fixed culture. Once semantics are
established, a new profile must define the authoritative source-day window.

Map all eleven mandatory concepts explicitly to existing measure contracts.
Pumping, Consumption + Storage, Consumption of Batteries and Battery Injection
are the four observed unselected concepts. The informal term “Batteries” is not
an accepted alias for an unseen source name. Reject unknown/duplicate concepts
and undeclared fields; validate unselected arrays too. Preserve REN provider
perimeter identity; external interchange has no invented Spanish counterparty
or asserted physical-versus-commercial classification.

Bound original bytes to 1 MiB, series to 32, total values to 10,000; also bound
JSON depth, nodes, strings, numbers and collection sizes. Use direct Decimal
parsing, no binary float, rounding, filling, aggregation, MWh or shares. Treat
explicit chart styling fields as inert bounded data; never evaluate strings.
No assumed daily counts or calendar-to-UTC mapping is enforced while time is
unknown. Invalid labels/structure fail separately; plausible DST labels still
fail the semantic gate.

Use synthetic fixtures only. Keep real observations in `/tmp` outside Git and
exclude them from Stage 8 live acceptance. Do not infer future/error behavior or
assign REN 404 a no-data contract. Preserve default retry/transport rules and
sequential execution; deliberate successive acquisitions must be at least one
second apart. No scheduler, batch loop, second product or live CLI is introduced.

## Alternatives considered

Using Madrid/OMIE time, fixed WET/WEST, inferred interval means, or a test-only
normalization override would fabricate semantic evidence. Duplicating retrieval
or widening shared contracts is unnecessary. Pretending raw acquisition is
successful normalized ingestion would hide the unresolved Stage 2 requirement.

## Consequences

Stage 2 can be **PASS WITH GAPS**, never PASS, with this profile. Successful
SystemMeasurement normalization, authoritative ordinary/DST calendar validation
and value/identity replay remain blocked pending official timing evidence.
Offline replay can reproduce the exact controlled failure and original raw
linkage now. No provider rights clearance, complete history, live-smoke
acceptance or next-provider authorization is claimed.
