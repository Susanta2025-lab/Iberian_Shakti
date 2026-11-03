# Synthetic ENTSO-E Stage 4 fixtures

All four XML documents are authored test examples, not authenticated provider
responses. Participant, document and series identifiers are synthetic; area,
PSR, business, aggregation, unit and namespace codes follow the pinned official
references in the Stage 4 report. No token or real provider payload is included.

ES load: A65/A16, A01 curve, two non-overlapping Periods with a real gap and
30/60-minute resolutions. PT forecast: A69/A01, solar and onshore wind only.
ES forecast also includes offshore wind. Both use 15-minute A03 constant blocks.
The acknowledgement exercises documented 999 + exact no-matching-data context.

`manifest.json` records original byte counts, SHA-256, synthetic evidence,
profile and expected record counts. Hostile, revised and invalid variants are
constructed in memory. Stage 8 separately established live compatibility/replay
for all three required product/domain paths under profile 0.1.0. These synthetic
fixtures are not that live evidence; rights to redistribute real responses remain
unestablished. Fixture bytes and manifests remain unchanged.
