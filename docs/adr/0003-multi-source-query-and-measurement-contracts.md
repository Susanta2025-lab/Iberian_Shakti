# ADR 0003: Multi-source query and measurement contracts

- Status: Accepted
- Date: 2026-10-28

## Context

Phase 2 Stage 1 implements the accepted
[readiness assessment](../codex/reports/phase_2_readiness_assessment.md), §§J–M,
without provider implementations. ADRs 0001/0002 and their historical serialized
objects must remain valid. This ADR is written before the corresponding code.

## Decision

Keep SourceRequest, MarketPrice and legacy version-1 provenance wire shapes.
Add a separate version-2 ApiSourceRequest with explicit `api_snapshot` selection,
source/report identity, archive partition day and positive half-open UTC query
window (at most 25 hours for this daily scope). Its query is a discriminated
system-series or weather-point selection. Typed area roles/native identifiers,
bounded series/variable tuples and weather site/model selection carry nonsecret
query meaning; no arbitrary parameter mapping, URL or credential fields exist.
Canonical query JSON (sorted keys and sorted unique selections) defines a SHA-256
query identity; it is independent of acquisition time and provider revision.
Resolved API locators/filenames are derived from this identity and have no fake
numeric revision. Archive partition day is operator-selected query context, not
an assertion that every returned interval lies in that day.

Use small frozen UTC instant/interval, geographic area/site/border and source-time
value objects. Keep country, system/mainland, bidding zone, control area,
provider area and EIC role/native ID distinct. Directed links and aggregate
external boundaries are distinct geographic types. Do not load catalogues or
infer provider timezones. Valid time/support, cadence, issue/model run,
publication/update and acquisition completion have separate meanings. Source
times remain nullable; an unknown forecast edition retains acquisition snapshot
linkage and never claims an earlier information cutoff.

Add SystemMeasurement and WeatherMeasurement with explicit schema family/version,
source/report/day partition, native series/document/revision/profile observations
and parse-event linkage. Closed measure variants enforce technology/direction
where appropriate; system units MW/MWh use finite Decimal with no float
intermediate and decimal-string JSON. Weather has generic temperature/wind-speed/
shortwave-radiation variables, explicit height/statistic/unit, finite float,
missing-value status, requested/returned coordinates/elevation and model identity.
Initial plausibility bounds are those in the assessment; no clipping, conversion,
resampling, derived totals or feature engineering. Instant samples and interval
statistics cannot be interchanged.

A closed normalized-record union supports unchanged MarketPrice plus these two
families. Legacy ParseProvenance remains version 1, price-only and requires
positive-record success. New version-2 API retrieval and measurement-parse
provenance identify API query/schema family and optional local catalogue version.
Readers select explicit versions; no old event is rewritten. New normalized
content identity includes family/version/catalogue alongside raw/parser identity.
Known issue/run editions distinguish business identity; unknown editions remain
separate through original acquisition snapshot identity, not a fabricated issue.

Reuse content-addressed raw paths, original-byte hashes, immutable event
publication, local retrieval and replay. The archive's event readers accept the
closed legacy/new event union. A shared resolved-source runner performs the same
persist-before-parse chain; existing OMIE resolution delegates to that chain.
No archive migration or provider framework is required.

## Alternatives considered

Adding fake revisions to API requests conflates snapshots with provider versions.
A giant optional parameter bag loses strictness. Replacing all legacy events
with mandatory new fields breaks immutable history. Untyped records and float
system quantities lose validation/precision. Separate per-provider archives or
runners duplicate accepted infrastructure.

## Consequences

Compatibility tests must retain legacy JSON fields, canonical stored events,
fixture hashes, exact/latest OMIE output and replay. New snapshot acquisitions
must retain identical/changed bodies independently with original query context.
No new runtime dependency, provider adapter/parser/catalogue or network action
is introduced. Full Phase 2 provider evidence remains for later stages.
