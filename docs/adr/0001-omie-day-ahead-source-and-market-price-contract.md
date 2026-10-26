# ADR 0001: OMIE day-ahead source and market-price contract

- Status: Accepted
- Date: 2026-10-26

## Context

Phase 1 needs one concrete Iberian day-ahead source and a precise market-price
contract before retrieval and parsing are implemented. This ADR records the
already accepted [Phase 1 assessment](../codex/reports/phase_1_readiness_assessment.md),
especially §§2 and 5.2–5.3; it does not reassess the architecture.

## Decision

### Report and revisions

Select OMIE's `marginalpdbc` report family. Each report contains Portugal and
Spain prices, in that column order; no second Portuguese-family download is
needed. Exclude intraday reports, retail tariffs, chart exports, and aggregates.
Use anonymous public HTTPS downloads at `https://www.omie.es/en/file-download`
with `parents=marginalpdbc` and an exact `filename=marginalpdbc_YYYYMMDD.v`.
No API token is required for this verified route.

Requests identify source, report, delivery date, and optionally a positive
numeric revision. An explicit revision selects that filename. Otherwise use
bounded discovery from the public family listing and choose the highest
numeric revision observed for the date. `.1` is neither guaranteed latest nor
the only revision; an actual `.2` file was downloaded during the assessment.
Preserve the selected revision and locator. Discovery means latest observed,
not complete revision history. Unknown listing coverage is an explicit outcome;
do not probe revisions without bounds or silently fall back to `.1`.

### Market intervals and prices

Use one normalized record per bidding area and market interval. For this
adapter, areas are `PT` and `ES`, market is `day_ahead`, currency is `EUR`,
and price unit is `MWh`: prices are EUR/MWh. Prices are signed, finite
`Decimal` values parsed from decimal text without any binary-float intermediate.
Preserve exact supported precision and serialize decimal values as strings.
Negative prices are valid; mutable regulatory price caps are not schema limits.

Retain delivery date, positive numeric source `period_index`, duration in
minutes, timezone-aware UTC start/end, and provenance reference. The source
period is part of identity; graphical labels such as H1Q1 do not replace it.
Shared contracts must remain extensible beyond OMIE's areas and durations.

The delivery-day calendar is `Europe/Madrid` for both bidding areas. `PT`
does not shift the report to Lisbon midnight, and the provider's shorthand
“CET” does not mean a permanent UTC+1 offset. Convert successive market-local
midnight boundaries separately to UTC, then add period offsets in UTC.
Host IANA timezone data is a prerequisite, to be checked when calendar startup
is implemented; absence must produce a clear configuration error.

| Delivery dates | Resolution | Ordinary / spring / autumn period counts |
| --- | --- | --- |
| Before 2025-10-01 | 60 minutes | 24 / 23 / 25 |
| From 2025-10-01 | 15 minutes | 96 / 92 / 100 |

Expected counts follow elapsed UTC minutes between those midnight boundaries.
Require the ordered sequence `1..N`, contiguous intervals covering the whole
day, and exactly two area records per source period. Reject the complete day
on any malformed or missing row. No partial-day acceptance, filling, resampling,
hourly averaging, or modern-to-hourly fallback is permitted.

### Supported source grammar and historical envelope

The selected profile uses `MARGINALPDBC;`, six nonempty semicolon-delimited
fields (year, month, day, integer period, PT price, ES price), trailing row
delimiter, and exactly one terminal `*`. Dates must match the request/filename.
Support LF/CRLF and strict ASCII decoding of the verified numeric subset;
do not infer a global charset guarantee. Reject BOM/non-ASCII, unknown schema,
interior blank rows, duplicate/reordered periods, truncation, or trailing data.
Price grammar accepts signed integers and one/two fractional digits; reject
exponents, comma/grouped decimals, missing/nonfinite values, and unsupported
precision. Preserve original bytes independently of this parsing policy.

Historical support covers the explicitly tested legacy numeric profile and
the modern profile, not every historical OMIE format or unlimited backfill.
The legacy autumn profile needs a representative fixture before final Phase 1
acceptance; its exact bytes were not verified in the assessment.

### Evidence and limits

External evidence was verified on 2026-10-26 in the accepted assessment:

- [OMIE launch release](https://www.omie.es/sites/default/files/2025-10/2501001_go_live_mtu15_md_en_vf.pdf):
  quarter-hour delivery began on 2025-10-01.
- [Public file format v1.37, §5.1.1.1](https://www.omie.es/sites/default/files/2025-09/formato_ficheros_inf_pub_137.pdf):
  selected family, field order, numeric periods, and modern period range.
- [Previous format v1.36, §6.18](https://www.omie.es/sites/default/files/2025-03/formato_ficheros_inf_pub_136.pdf):
  legacy period range and signed prices.
- [OMIE-hosted market rules, Annex 1](https://www.omie.es/sites/default/files/2025-03/resolucion_dcoor-de-009-24.pdf):
  sequential modern periods and clock-change counts.
- [Public family listing](https://www.omie.es/en/file-access-list?realdir=marginalpdbc)
  and anonymous downloads demonstrated ordinary, modern DST, legacy ordinary
  and spring days, negative/unequal area prices, revision `.2`, and one missing
  future filename returning 404. Exact sample filenames/hashes are in the assessment.

Unverified guarantees remain unverified: publication minute/SLA, all
prepublication response variants, contractual charset, same-filename content
stability, complete revision/retention/pagination coverage, every older format,
and a stable latest-revision API. Listing modification time is not guaranteed
first-publication time. Observations and project validation rules must not be
presented as additional OMIE guarantees.

## Alternatives considered

Separate area-family downloads duplicate information. Graphical exports and
hourly-only schemas lose the selected numeric-period semantics. Fixed-offset
calendars fail DST; float prices lose decimal fidelity. Assuming revision `.1`
or complete historical coverage contradicts the accepted evidence and limits.

## Consequences

Later contracts/parser stages must validate whole reports and both period
profiles, retain revision/content provenance, and fail visibly on unsupported
content. This ADR records the contract; Stage 1 implements no parser, discovery,
retrieval, or calendar conversion.

## Follow-up

See [ADR 0002](0002-local-ingestion-immutable-archive-and-replay.md) for
execution, archive, provenance, and replay. Shared contracts belong in
`contracts/`; OMIE-specific grammar/calendar rules belong in `ingestion/omie/`.
