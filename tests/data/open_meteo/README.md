# Synthetic Open-Meteo hourly fixture

`synthetic_era5.json` is handwritten/generated offline test data, not a provider
response. It contains 24 UTC hours on a local DST transition date, three selected
variables and deliberately distinct requested Lisbon and returned grid coordinates.
Elevation 123.5 m and all values are synthetic. No real provider body is copied.

`manifest.json` pins UTF-8 bytes, SHA-256, synthetic origin, profile and expected
record count. Negative cases and corrections use in-memory mutations.

`synthetic_icon_eu.json` is the single synthetic forecast fixture. It uses the
same 24-hour UTC day (2026-10-25), approved variables/units and deliberately distinct
Lisbon/grid coordinates, with explicit `model=icon_eu` metadata. The manifest pins
its `models=icon_eu` request context, product/parser versions, requested coordinates,
UTC day, synthetic acquisition completion (2026-10-24 12:00 UTC) and output settings.
These timestamps are test inputs, not provider-run/publication evidence. Negative
cases, changed forecasts and changed grid metadata use in-memory mutations. There
are no downloaded bodies, forecasts from other models, or inferred real vintages.
