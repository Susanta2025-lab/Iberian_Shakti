# Synthetic REN production chart fixtures — profile 0.2.0

Every fixture here is **synthetic**. None contains a downloaded REN body or
reproduced provider measurement values. Attribution for schema evidence: REN
DataHub, [API instructions](https://datahub.ren.pt/en/api-instructions), inspected
2026-10-28, and the observation inventory in the Stage 2 report. Real observations
remain outside Git under `/tmp`; no redistribution rights have been assumed.

The fixtures model `ElectricityProductionBreakdownDaily`, culture `en-US`, JSON
`xAxis`/`yAxis`/`series`, Hour labels and MW values. All values and style strings
are invented. Decimal tokens such as `1.2300` intentionally test lexical
precision. The selected eleven concepts and four known unselected names model
the observed response shape. Changed fields and error forms are synthetic test
cases, never assertions about observed REN missing/future/error behavior.

Ordinary (96), spring (92, skipped 01h), autumn (100, repeated 01h), leap and
year-boundary fixtures exercise the accepted **provisional empirical** Lisbon
interval-start profile 0.2.0 (ADR 0006). They do not prove provider-authoritative
semantics; leap/year cases remain hypothetical, not provider observations.
Valid days emit eleven MW `provider_period_value` measurements per physical
period, without a mean/instant claim or energy conversion. Autumn source array
positions map to fold 0 then fold 1; inconsistent labels/order/count fail before
any record emission. Tests use the operational profile without a timing override.

Originally these same bytes exercised blocked profile 0.1.0 and returned
`time_semantics_unknown`, including otherwise valid clock shapes. ADR 0005 and
the historical Stage 2 report preserve that policy. The 2026-11-03 metadata
update changes expected outcomes/profile only, preserving every payload hash.
Integration tests retain old acquisition/query and failed parse events while
replaying those bytes under 0.2.0 with a separate successful parse event.

`manifest.json` inventories every fixture with exact SHA-256, byte length,
synthetic evidence label, source date, pinned profile/schema/unit, expected
failure/count, purpose and mutation parent. Preserve exact bytes; deliberate
changes require reviewed checksum/purpose updates. The correction pair is
`synthetic_ordinary.json` / `synthetic_corrected.json`: same query, different
invented numeric value and hash. It tests immutable history, not observed REN
revision behavior. Unknown-time/calendar fields are deliberate unsupported
schema additions; the supported offset-free response must instead match the
complete pinned ordered calendar exactly.

The large-value fixture has 10,010 values; the excessive-series fixture has 33
series. Other hostile bounds are generated in memory during tests to keep this
inventory small. All fixtures have a final LF. No live invocation, secret or
remote metadata lookup belongs in these tests.
