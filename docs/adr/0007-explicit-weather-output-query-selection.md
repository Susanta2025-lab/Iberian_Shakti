# ADR 0007: Explicit weather output selection in snapshot queries

- Status: Accepted
- Date: 2026-11-03

## Context

The operator accepted DWD ICON-EU in the
[Stage 5 completion prompt](../codex/prompts/phase_2/phase_2_stage_5_open_meteo_forecast_completion.md).
The forecast canonical query must explicitly include unit, timezone and time-format
selections. ADR 0003's weather query carries site/model/variables, with historical
ERA5 output choices implicit in its versioned report. Existing serialized queries,
query hashes and immutable historical events must retain their original meaning.

## Decision

Add an optional typed `WeatherOutputSelection` to `WeatherQuery`. It carries the
profile version, celsius temperature, m/s wind, GMT timezone and Unix time selectors.
These are finite literal choices, not an arbitrary provider parameter dictionary.
When absent, serialization omits the new field, preserving existing weather query
bytes and identities. Existing system/OMIE queries and event versions are unchanged.
New ICON-EU queries require this selection; full equality with the versioned product
request rejects omitted or altered selections before transport and parsing.

Retain the shared retriever, archive, runner, replay and weather measurement schema.
Separate historical/forecast report and parser identities. The forecast acquisition
policy accepts only the next UTC weather day relative to acquisition; replay checks
the original retrieval completion, never the current clock. This bounds target
selection, not a claim of run initialization, publication or actual lead time.

## Consequences

Compatibility tests must prove historical canonical bytes/hashes are unchanged.
Forecast query round trips, provenance and replay retain the explicit selection.
No archive migration, new dependency, fallback or historical-vintage API is needed.
The accepted model selection report remains unchanged.
