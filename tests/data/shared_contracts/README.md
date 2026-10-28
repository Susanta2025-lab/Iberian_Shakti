# Synthetic compatibility metadata

`phase_1_history.json` was generated offline with the committed pre-Stage-1
Python source at `70f4204`. It contains synthetic request/retrieval/parse UUIDs
and times, the baseline canonical archive sidecar bytes and first MarketPrice
serialization. It references an existing unchanged OMIE fixture; no new provider
payload or live acquisition is included. It is not historical live evidence.

The checksum manifest protects the exact synthetic metadata. Do not regenerate
it from Stage 1 models to hide a serialization regression. Compatibility tests
load it as old history, reproduce the existing fixture's normalized prices and
verify that persistence never rewrites old sidecars.
