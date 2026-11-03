# Synthetic ESIOS indicator 544 fixture

`synthetic_forecast.json` is handwritten test data, not an authenticated response.
It exercises the documented nested indicator/values/geos structure and an autumn
DST offset transition. Geography ID **999001 is a synthetic sentinel**, not a
claim about ESIOS's production catalogue. This historical 0.1.0 fixture does not
establish numeric catalogue IDs. Separately, Stage 8 observed Potencia (20),
Cinco minutos (219) and Península (8741) with the exact selected product name.
Neither live response supplied an explicit native unit field; MW remains
documented product policy. The final accepted bounded profile is 0.2.0;
`test_esios_boundary_semantics.py` generates its regression bodies offline.
The fixture bytes, synthetic sentinel and historical manifest remain unchanged.

The selected product's forecast/load/MW/five-minute semantics come from the
operator's Stage 3 prompt and readiness §F. Presentation metadata is optional.
Negative cases and revised values are in-memory mutations; no additional body
catalogue or provider data redistribution is necessary.

`manifest.json` records exact UTF-8 byte count, SHA-256, synthetic origin, profile
and expected record count. Intentional fixture changes require regenerating the
manifest and reviewing the parser/normalization assertions. No real credentials
or source bytes belong here.
