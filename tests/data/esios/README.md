# Synthetic ESIOS indicator 544 fixture

`synthetic_forecast.json` is handwritten test data, not an authenticated response.
It exercises the documented nested indicator/values/geos structure and an autumn
DST offset transition. Geography ID **999001 is a synthetic sentinel**, not a
claim about ESIOS's production catalogue. No numeric geography, magnitude or
cadence catalogue ID has been verified or guessed. The optional metadata labels
are profile consistency checks; their exact live spelling remains to be checked.

The selected product's forecast/load/MW/five-minute semantics come from the
operator's Stage 3 prompt and readiness §F. Presentation metadata is optional.
Negative cases and revised values are in-memory mutations; no additional body
catalogue or provider data redistribution is necessary.

`manifest.json` records exact UTF-8 byte count, SHA-256, synthetic origin, profile
and expected record count. Intentional fixture changes require regenerating the
manifest and reviewing the parser/normalization assertions. No real credentials
or source bytes belong here.
