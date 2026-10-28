# Phase 2 — Multi-Source Ingestion Expansion: Authoritative Readiness Assessment

Verification date: **2026-10-27**, Europe/Lisbon; direct observations at approximately
14:36:52 UTC. Inspected baseline: existing `main`, HEAD and locally recorded
`origin/main` both `a4191a3` (`docs: close Phase 1 OMIE ingestion`), clean working
tree and index. No fetch was performed; remote freshness is not independently
certified. Phase 0 and Phase 1 remain CLOSED/PASS. Phase 2 implementation has
not started.

This is the **single authoritative Phase 2 readiness/source assessment**.
Future work proceeds through implementation verification, hardening, pre-live
engineering audit, controlled live validation, replay and final acceptance
against §V. Do not commission or recommend another Phase 2 readiness assessment.
Concrete source-profile verification and recording accepted decisions in ADRs
are implementation work, not replacement assessments. This document proposes
the implementation contract; it does not implement it or authorize paid services.

Evidence labels throughout:

- **D — officially documented:** current official pages or explicitly identified
  official indexed documentation; a documentation example is not a live result.
- **O — directly observed:** this task's bounded responses or local repository
  inspection. Observations establish only the particular interaction inspected.
- **I — inferred:** project recommendations, estimates or interpretations, never
  additional provider guarantees.
- **U — unknown:** not verified. Missing evidence is not a promise of absence,
  completeness, retention, publication time or availability.

All external references below were checked on the verification date. Some
JavaScript pages/PDF routes could only be inspected through official indexed
text; those limitations are identified. Search snippets from third parties are
not used as technical evidence. No guarantee of continuing compatibility is made.

## A. Executive verdict

**Phase 2 readiness verdict: GO WITH GAPS**

Mandatory providers: **REN, ESIOS / REE, ENTSO-E, Open-Meteo**. Their deliberately
small dataset responsibilities are fixed in §§C–D. **MIBGAS is deferred.**
There is no engineering blocker to beginning local deterministic implementation.
Missing adapters/contracts/tests are Phase 2 work, not readiness blockers.

Important external uncertainties and dependencies:

| Item | Classification | Consequence |
| --- | --- | --- |
| ESIOS and ENTSO-E credentials unavailable locally | External dependency | Offline implementation can start; successful authenticated live evidence is required before closure. No token was requested or generated. |
| REN time labels omit offsets and interval convention | External semantic dependency | Lisbon mapping is an evidence-supported inference, not documented fact. Resolve the concrete parser profile before emitting authoritative UTC records; ambiguity must fail visibly (§K). |
| ESIOS current indicator/geography/native sampling metadata not authenticated | External dependency | Verify and pin the small catalogue during its implementation stage; old documentation examples are insufficient production metadata. |
| Current ENTSO-E XML profiles and PT/ES forecast coverage not sampled | External dependency | Implement documented codes defensively; verify each required domain/product during bounded live validation. |
| REN reuse restrictions; ESIOS commercial-use prohibition; weather free-service restrictions | Commercial/legal restriction or uncertainty | Operator/legal confirmation recommended before production use. Readiness is for local engineering, not commercial clearance. |
| History, correction completeness, publication SLA and detailed error variants | Accepted implementation limitation | Declare supported profiles/windows, archive every acquired version, distinguish unavailable/partial/invalid and never invent missing facts. |

These gaps can be isolated safely while building the shared foundation. A source
stage cannot be accepted with guessed units/time semantics; Phase 2 cannot close
with a missing mandatory integration or missing required live success. A genuinely
contradictory source contract must be reported as a specific blocker, without
reopening this assessment or silently removing a mandatory dataset.

## B. Phase 1 baseline

**O:** Read `AGENTS.md`, `README.md`, architecture/ADR/runbook indexes, ingestion
runbook, both accepted ADRs, the original Phase 1 readiness report and Stage 7
closure report, `pyproject.toml` and `.env.example`. Inspected contracts,
acquisition/archive/replay/runner/config/error boundaries, OMIE identity,
calendar/parser/discovery/live entry points, contract/unit/integration test
coverage and fixture policy. This inspection informs reuse; it is not a Phase 1
re-audit and no Phase 1 validation was repeated.

The accepted foundation is:

```text
SourceRequest → provider resolution → bounded synchronous retrieval
  → immutable original-byte SHA-256 archive → retrieval provenance
  → strict provider parser → normalized contracts → parse provenance
  → checksum-verified offline replay
```

Reuse HTTPX/Pydantic, finite deadlines, three-attempt retry policy, injected
transports/clocks, local-file capability, safe opaque locators, allowlisted logs,
atomic no-replace publication and separate immutable acquisition/parse events.
Maintain Decimal EUR/MWh, UTC-aware records, unchanged OMIE calendar/grammar,
explicit live opt-in and repository-wide network-denied pytest. Stage 7 records
968 passing tests; that is inherited evidence, not a test run in this task.

**O:** `ren`, `esios`, `entsoe` and `weather` contain empty `__init__.py` stubs.
There is no Open-Meteo implementation or MIBGAS package. No placeholder is an
implemented source. Source-specific packages should own grammars and mappings;
shared execution must not be copied into four independent clients.

Important existing limitations are concrete: `SourceRequest` carries one day and
numeric revision selection; `ParseResult.records` is a tuple of `MarketPrice`;
parse schema versions are price-specific literals; `HttpRetriever` builds GET
requests with only an identity-encoding header; HTTP absence classification is
404-specific. These are extension points, not reasons to replace the architecture.

## C. Proposed Phase 2 scope

All selections here are **I — implementation recommendations** based on §§E–I.

| Mandatory provider | Exact minimum datasets/products | Purpose and support boundary |
| --- | --- | --- |
| REN | Documented `ElectricityProductionBreakdownDaily`, one completed source day: Consumption; Wind, Solar, Hydro, Natural Gas, Biomass, Other Thermal, Coal, Wave; Import and Export | Portuguese system load, technology generation and external exchange context from one response. Preserve REN's system perimeter and source labels. Pumping, batteries and Consumption + Storage remain identified but unselected ancillary series; do not add them to consumption/generation totals. |
| ESIOS / REE | `Demanda prevista Peninsular`, official analysis identifier **544**, native five-minute presentation, through authenticated indicator JSON | Spanish peninsular operator load forecast. It is the published forecast curve, not automatically a complete D-1 auction-time forecast. Confirm API metadata/geo before accepting the profile. |
| ENTSO-E | Actual Total Load for ES (`A65`/`A16`); Day-ahead Wind and Solar Forecasts for PT and ES (`A69`/`A01`), with native technology series | ES actual-load ownership avoids depending on an unverified ESIOS actual indicator. Renewable forecasts add forward-looking value for both countries. Only returned/supported wind technologies are required; absence of offshore production is not a fabricated zero. |
| Open-Meteo | Hourly Historical Weather API with ERA5 plus hourly Forecast API: `temperature_2m`, `wind_speed_10m`, `shortwave_radiation`; six fixed locations (§H) | Demand-temperature and renewable-weather covariates. Reanalysis and forecasts remain different products. No claim of point-in-time historical forecast availability. |

Historical support means one-day bounded query/replay capability for explicitly
catalogued formats. Initially support contemporary profiles verified against
fixtures, with any earlier supported profile named explicitly. No mandatory
bulk backfill, earliest-year coverage target or complete historical database.

Deferred: MIBGAS; REN undocumented page-service forecasts; ESIOS generation mix,
additional actual-load series, interconnections, settlement/imbalance prices and
archive files; ENTSO-E PT actual load except a later deliberate comparison,
load forecasts, generation by type, capacity, physical flows and schedules;
weather historical forecasts/single model runs, sub-hourly interpolation,
precipitation/humidity/direction/clouds and larger location grids. These are
assessed candidates, not hidden Phase 2 acceptance requirements.

No extra provider is optional inside the closure checklist. In particular there
is no conditional MIBGAS implementation stage. Adding a deferred dataset needs
an explicit scope decision with focused implementation evidence, not another
readiness assessment.

## D. Source responsibility matrix

**I:** Ownership concerns semantics and scope, not a claim that one operator is
universally faster or more complete. Latency/history comparisons remain U until
measured. ENTSO-E often republishes operator data, so overlap is not necessarily
independent measurement.

| Data concept | Portugal primary | Spain primary | Cross-border/fallback | Reason / Phase 2 status |
| --- | --- | --- | --- | --- |
| Day-ahead electricity price | Existing OMIE | Existing OMIE | None | Keep accepted Phase 1 authority; do not ingest republished OMIE prices again. |
| Actual demand | REN Consumption | ENTSO-E A65/A16, ES | REN vs ENTSO-E PT comparison deferred | One acquisition route per concept/area. Preserve self-consumption, pumping, loss and system-perimeter definitions. |
| Load forecast | Deferred | ESIOS 544, peninsular curve | ENTSO-E A65/A01 is a later comparable forecast product | A forecast curve and an auction-time D+1 forecast are distinct; do not pretend PT load forecast is in this minimum. |
| Actual generation by technology | REN selected production series | Deferred | ENTSO-E A75/A16 later | PT production is already in the selected REN response; adding ES generation now would expand scope and semantic mappings unnecessarily. |
| Renewable generation | REN native Wind/Solar/Hydro/Biomass/Wave | Deferred | No duplicated derived totals | Preserve technologies; renewable-share calculation and cross-source aggregation are later transformations. |
| Wind forecast | ENTSO-E A69/A01 | ENTSO-E A69/A01 | REN/ESIOS forecasts deferred | Consistent coded product across both areas; confirm coverage independently. |
| Solar forecast | ENTSO-E A69/A01 | ENTSO-E A69/A01 | No automatic fallback | Same reason; keep solar taxonomy and zero vs absent distinct. |
| Interchange | REN Import/Export, aggregate external boundary | Deferred | Directional ENTSO-E physical flows/schedules later | Do not equate REN aggregate balance to a named PT–ES physical circuit or scheduled exchange. |
| Weather | Open-Meteo PT locations | Open-Meteo ES locations | None | Coordinate/model-specific covariates, not countrywide observed weather. |
| Gas-market indicator | Deferred | Deferred | MIBGAS later | Useful potential fuel-cost signal; not needed to establish this ingestion expansion. |

No recurring duplicate ingestion or automatic provider failover is required.
A future validation comparison must align perimeter, measurement type, units,
interval and revision first, then retain both source identities and report a
comparison rather than replacing one with the other.

## E. REN verification

**Readiness decision: GO WITH GAPS.** A documented structured route and a small
successful sample exist; timezone/measurement semantics and reuse rights remain
explicit gaps.

| Dimension | Evidence and decision |
| --- | --- |
| Provider/product/access | **D:** REN DataHub documents electricity JSON endpoints at `https://servicebus.ren.pt/datahubapi/electricity/`, including `ElectricityConsumptionSupplyDaily` and `ElectricityProductionBreakdownDaily`; parameters `culture=en-US`, `date=YYYY-MM-DD`. **O:** both worked anonymously. No invented key. [Official API instructions](https://datahub.ren.pt/en/api-instructions). |
| Mechanism | **D/O:** documented API, with a presentation-shaped nested response for production. Choose it over HTML scraping or an undocumented page-backed POST route. The aggregate balance endpoint was investigated but is not a mandatory ingestion product. |
| Format | **O:** balance is a JSON list of type/daily accumulation objects; production is JSON with `xAxis`, `yAxis`, `series`, despite `text/plain` MIME. No compression or pagination observed. Validate the endpoint's JSON grammar rather than trusting MIME alone. |
| Time/resolution | **O:** 2026-10-25 production has 100 quarter-hour labels from 00:00 to 23:45, repeating 01:00–01:45, and 100 values in each of 15 series. MW is explicit on `yAxis`. Labels contain no date/offset/UTC field. **I:** consistent with Lisbon autumn time, not Madrid's repeated 02:00. **U:** contractual timezone, start/end/instant semantics and historical resolution changes; do not guess them. |
| History | **D:** date query exists. **O:** the selected completed day is accessible. **U:** earliest day, retention, complete older profiles and historical correction availability. No history-depth claim. |
| Updates/revisions | **D:** DataHub describes provisional remote-metered/estimated production, updated every 15 minutes. This page cadence is not an API SLA or guaranteed interval average. **U:** finalization, exact revision cadence, revision IDs and historical immutability. [REN DataHub description](https://datahub.ren.pt/en/). |
| Missing/errors | **U:** future/invalid/unsupported dates, missing series, authentication-policy changes, quota and server-error body variants: **not verified**. No error probes were made. Empty arrays/HTML/nulls must not become success or zeros. |
| Bounds | **I:** one source day, one request, 1 MiB original-byte cap, at most 32 series and 10,000 values total; no pages. Sample production is approximately 29 KiB. Unknown response shapes/extra concepts fail or require a versioned explicit mapping, not silent normalization. |
| Quotas | **U:** published numeric API quota/approval requirement not found in the inspected instructions. Anonymous success is not unlimited permission. Serialize calls; initial ceiling one request/second, no polling or backfill in one invocation. |
| Terms | **D:** linked corporate terms reserve rights and restrict reproduction/reuse and substantial extraction. DataHub-specific raw-storage/commercial redistribution permission was not established. **Category: restriction identified; unclear / legal review may be required.** See §S. |

Direct observations (one request each, `date=2026-10-25`, `culture=en-US`):

| Endpoint | HTTP | Bytes | SHA-256 | Observation |
| --- | ---: | ---: | --- | --- |
| `ElectricityConsumptionSupplyDaily` | 200 | 1,394 | `556f8f1f812035791fd3d11136421731d3804a062ea1343a24673e69cb4ab57b` | 27 type/accumulation entries; bare numbers are not self-describing units. Do not reinterpret daily accumulation as MW. |
| `ElectricityProductionBreakdownDaily` | 200 | 29,466 | `d7c9e0b184dd0233d4cedaad53442bdae79c9b8d26bfce9aec2ec6f90f18ae5a` | 15 series; selected load/generation/import/export can share one acquisition. |

Bodies were retained only under `/tmp/iberian-shakti-phase2-observations/` as
assessment evidence, not Git fixtures or Phase 2 archive events. No adapter or
repository code was executed. A browser could not fetch these endpoint bodies;
the bounded approved shell requests succeeded. That is a tooling difference,
not evidence of a provider availability conflict.

**I:** Future enrichment can evaluate REN load/wind/solar forecasts visible on
the homepage; their homepage presence does not establish a documented historical
forecast API or issue-time contract. Do not build scraping into mandatory scope.

## F. ESIOS / REE verification

**Readiness decision: GO WITH GAPS.** Official API and forecast product exist;
authentication, native metadata and usage restrictions need operational handling.

| Dimension | Evidence and decision |
| --- | --- |
| Provider/access | **D:** Red Eléctrica's ESIOS API at `https://api.esios.ree.es`; `GET /indicators`, `GET /indicators/{id}`. Current examples specify `x-api-key` and a versioned JSON Accept header. Treat it as registered API-key access, despite the environment name containing TOKEN. Do not copy example keys or silently try multiple authentication schemes. [API catalogue](https://api.esios.ree.es/), [list route](https://api.esios.ree.es/doc/indicator/getting_a_list_of_indicators.html). |
| Token acquisition | **D:** official September 18, 2026 notice moves requests to the Token Request icon. Registration/approval and any token expiry must be handled by the operator; no account workflow was attempted. [Official notice listing](https://www.esios.ree.es/en/downloads?date_type=publicacion&end_date=19-09-2026&start_date=19-09-2026). |
| Query/format | **D:** nested JSON indicator/values/geos; ISO8601 `start_date`, `end_date`, optional `geo_ids[]`, aggregation/truncation controls. Examples expose `datetime` with offset, `datetime_utc`, `values_updated_at`. No mandatory pagination mechanism or numeric maximum was established. [Date-range reference](https://api.esios.ree.es/doc/indicator/getting_a_specific_indicator_filtering_values_by_a_date_range.html). |
| Time | **D:** offset and UTC representations appear in the API example. **I:** prefer `datetime_utc`, cross-check any supplied offset timestamp; use Europe/Madrid only for verified peninsular day boundaries. **U:** complete historical timezone/interval semantics and end-date inclusivity. Never infer interval end from an arbitrary next record across gaps. |
| Resolution/publication | **D:** official product page 544 describes MW, five-minute values; forecast publication at 00:00 for D and 13:30 for the first three hours of D+1. This is a documented cadence, not observed SLA. [Official indexed analysis page](https://www.esios.ree.es/es/analisis/544?start_date=30-09-2026T00%3A00). |
| Forecast meaning | **D:** operator forecast pages distinguish the five-minute curve, a D+1 hourly pre-auction forecast, and a quarter-hour D…D+7 product; the latter notes a self-consumption definition change from 2025-12-11. **I:** do not substitute those products for 544 or claim smoothed samples are independent native five-minute forecasts. [Official forecast descriptions](https://www.esios.ree.es/es/previsiones-os?date=09-10-2026). |
| History/revisions | **D:** date-range access and update metadata exist. **U:** earliest supported date per indicator, retention, complete old revisions and per-value issue time. Historical retrieval can expose updated information; do not label it as known before an old market cutoff. Final/provisional rules for 544: **not verified**. |
| Missing/errors | **U:** authenticated success, no-data/future/invalid-date bodies, 401 vs gateway 403 details, quota responses and server variants: **not verified**. Do not interpret 403 as unpublished, empty `values` as success, or a JSON error object as data. |
| Size/limits | **I:** one indicator/selected geo/day, 2 MiB raw cap, 2,000 selected values, 32 returned geos maximum. No aggregation requested merely to shrink data. One page; signal incomplete/unknown coverage if metadata indicates truncation. Numeric provider quotas and global date maximum: **U**. Initial application ceiling one request/second. |
| Compression | **D:** documentation examples include Brotli responses. **U:** whether live service honors identity encoding. Preserve any original encoded body, then explicitly reject unsupported coding. No Brotli dependency is justified without live evidence. |
| License | **D:** terms apply to both site and API, require attribution/update date and prohibit commercial use. **Category: restriction identified** (§S). This assessment does not override that restriction. |

Source catalogue, with the distinction between documentation and production:

| Identifier | Verified official meaning | Scope/use |
| --- | --- | --- |
| `544` | Demanda prevista Peninsular; product-page evidence above | Mandatory product candidate; before code pins it, archive a minimal authenticated response/metadata establishing returned name, MW magnitude, geo and sampling. The JavaScript page rendered blank when opened directly; official indexed text supplied the product evidence. |
| `1293` | Alias Demanda real in the official widget example | Documented example only, not a verified current production catalogue entry; excluded from mandatory scope. [Official widget example](https://api.esios.ree.es/doc/widget_v2/getting_a_specific_widget_metafora_by_id_with_latest_values_and_display_options.html). |
| Other demand/generation/forecast/interconnection IDs | **U:** no authenticated catalogue checked | No guessed IDs or geo IDs. Pin only after verifying official metadata; do not use documentation's synthetic example IDs as real series. |

**I:** ESIOS is valuable for Spanish operational forecasts and later system
indicators; the [official homepage](https://www.esios.ree.es/es/) distinguishes
actual instantaneous demand, scheduled generation and measured generation.
Those concepts and CO2-free share must not be conflated with renewable MW or
an interval-average total load. The mandatory actual ES load instead uses the
explicit ENTSO-E total-load product.

## G. ENTSO-E verification

**Readiness decision: GO WITH GAPS.** Token access and detailed public semantics
support a small implementation; no authenticated data/coverage observation exists.

**D:** use `https://web-api.tp.entsoe.eu/api`, not the main website's JSON content
APIs. HTTPS is required. Registration, operator-requested API access and a
security token are required; the published process includes confirmation before
token generation. Do not send an approval email from this task.
[Official endpoint](https://transparencyplatform.zendesk.com/hc/en-us/articles/15696677194644-Request-Endpoint),
[token instructions](https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token).

**D:** GET uses a private token parameter; safe examples/report URLs here omit
that parameter entirely. UTC `periodStart`/`periodEnd` use `yyyyMMddHHmm`;
`timeInterval` is an alternative. Use one bounded day, no update-time search
outside supported products. [Time parameters](https://transparencyplatform.zendesk.com/hc/en-us/articles/12783280128404-Request-Parameters-Time-Interval),
[request method example](https://transparencyplatform.zendesk.com/hc/en-us/articles/15696643163924-Request-Methods).

Verified catalogue and scope:

| Data item | Document/process | Domain/technology selection | Recommendation |
| --- | --- | --- | --- |
| Actual Total Load, 6.1.A | A65 / A16 | ES, `outBiddingZone_Domain` | Mandatory ES actual load. Official browser example establishes this selector for A65 actual load. |
| Day-ahead Total Load Forecast, 6.1.B | A65 / A01 | PT/ES bidding zones | Deferred to keep one ES forecast route and avoid adding PT load forecast now. |
| Wind/Solar Forecast, 14.1.D | A69 / A01 | PT and ES separately; `in_Domain`; B16 solar, B18 offshore wind, B19 onshore wind when returned | Mandatory PT/ES day-ahead renewable forecasts. Verify exact current response domain/PSR profile during implementation; selector combination is a project request profile, not a successful authenticated observation. |
| Generation per type, 16.1.B/C | A75 / A16 | `in_Domain`, production types | Deferred; duplicates PT native production and adds ES technology scope. |
| Actual generation; installed capacity | A73; A68 | Unit/domain-specific | Deferred; per-unit A73 has a documented one-day request ceiling. |
| Physical flows / commercial schedules | A11 / A09 document families | Directed in/out domains and product-specific parameters | Deferred; code-family identity alone is insufficient to specify a flow/schedule request. |

Codes are verified from official
[DocumentType](https://transparencyplatform.zendesk.com/hc/en-us/articles/15857043092756-DocumentType),
[ProcessType](https://transparencyplatform.zendesk.com/hc/en-us/articles/15857039772052-ProcessType)
and [PsrType](https://transparencyplatform.zendesk.com/hc/en-us/articles/15856995130004-PsrType)
lists; the [A65 browser example](https://transparencyplatform.zendesk.com/hc/en-us/articles/15854421431060-Query-via-Web-Browser)
verifies its actual-load selector. Country-domain identity is separately
verified below. No token-bearing URL is retained.

| Dimension | Evidence and implementation consequence |
| --- | --- |
| Geography | **D:** PT `10YPT-REN------W`, ES `10YES-REE------0`, each listed for several area roles. Preserve the requested role, not just the EIC string. Domain membership does not prove coverage for every article/date. [Official area list, updated 2026-09-21](https://transparencyplatform.zendesk.com/hc/en-us/articles/15885757676308-Area-List-with-Energy-Identification-Code-EIC). |
| Portugal coverage | **D:** PT domain exists. **U:** actual available A69 solar/wind periods, technologies, native resolution and history for the selected profile; no token. Require PT live evidence; do not infer it from Spain. |
| Spain coverage | **D:** ES domain exists. **U:** selected A65/A69 availability, metadata, interval granularity and continuity; no token. Require independent ES evidence. No islands-to-peninsula equivalence assumed. |
| Format | **D:** XML download documents follow the MoP implementation guides; time series use Period/timeInterval/resolution/Point positions, namespaces and document identifiers. **U:** exact currently returned namespace/version for our products. Pin supported profiles, document ID/revision, process, PSR, units and curveType; fail unknown profiles. [Official reference documentation](https://transparencyplatform.zendesk.com/hc/en-us/articles/12784099471764-Reference-Documentation), [MoP catalogue](https://www.entsoe.eu/data/transparency-platform/mop/). |
| Time/resolution | **D:** responses use UTC; queries can return partially matching periods and border directions are separate. Parse each Period's resolution, not an assumed hourly grid. **U:** specific PT/ES 15/30/60-minute historical transitions. [Query response](https://transparencyplatform.zendesk.com/hc/en-us/articles/15727773247124-Query-Response). |
| Curves | **D:** current platform uses variable-sized A03 blocks; support documented A01/A03 semantics. Missing position numbers in A03 may mean an unchanged value, not missing data. Expand only within explicit period/end semantics; never carry across a declared gap. [Official curve guidance](https://transparencyplatform.zendesk.com/hc/en-us/articles/30262342482961-CurveType-A01-vs-CurveType-A03). |
| History/publication | **D:** platform launched 2015-01-05; separate pre-2015 data exists. **U:** earliest complete API history for our PT/ES items, revision completeness, exact publication/finalization cadence: **not verified**. Platform launch is not a per-series completeness guarantee. [Official platform history](https://www.entsoe.eu/data/transparency-platform/). |
| Revisions | **D:** official MoP consumer description exposes submission time/older versions in the website. **U:** retrieval of every revision through our API products. Preserve returned mRID/revision/createdDateTime as distinct metadata; creation is not automatically first publication or model issue time. [Consumer description](https://www.entsoe.eu/Documents/MC%20documents/Transparency%20Platform/MOP/00_ENTSO-E%20Manual%20of%20Procedures_V2R1.pdf). |
| Limits | **D:** actual load/wind-solar requests allow up to one year; generation per unit one day; other document families have different limits. Selected products need no pagination for the project's daily envelope. No automatic offset walk or query subdivision. [Query limits](https://transparencyplatform.zendesk.com/hc/en-us/articles/15854536354964-API-Query-Size-Limit). |
| Rate limit | **D:** April 2026 R3 guidance says 400 requests/minute **per token**, no IP-based limiting/bans, possible approximately ten-minute token ban. Older December 2025 query-response text says per IP. Prefer newer specific guidance; document this official discrepancy, not a combined invented rule. Application proposal: sequential, at most one request/second; terminal 429 for this invocation. [Current rate-limit guidance](https://transparencyplatform.zendesk.com/hc/en-us/articles/12783148966036-API-Rate-Limit-Part-1). |
| Missing/errors | **D:** no matching data can be HTTP 200/reason 999; invalid query 400/reason 999; missing/invalid token 401; quota 429. Therefore reason 999 alone is not a no-data classifier. Unknown future/unsupported periods/semantic text remain **U**. Inspect bounded acknowledgement structure/context, never raw text logging. [Query response table](https://transparencyplatform.zendesk.com/hc/en-us/articles/15727773247124-Query-Response), [authentication](https://transparencyplatform.zendesk.com/hc/en-us/articles/15854491895828-Authentication-and-Authorization). |
| Bounds | **I:** one day/product/domain, 4 MiB original XML, 100 series, 64 Periods/series, 20,000 expanded records and 100,000 XML elements, depth 32. Do not increase the existing 30-second attempt/93-second operation budget to the provider's documented 300-second server timeout merely because that maximum exists. [Server timeout](https://transparencyplatform.zendesk.com/hc/en-us/articles/12783223209876-API-Rate-Limit-Part-2). |
| Compression | **U:** no ZIP was observed for selected queries. XML is the minimum supported body; unexpected ZIP is archived then explicitly unsupported. Do not build a ZIP framework for deferred outage/balancing products. |

**D:** the official [Generation/Load XSD](https://gitlab.entsoe.eu/transparency/xsd/-/blob/main/iec62325-451-6-generationload.xsd)
provides concrete field evidence for `GL_MarketDocument`, revision, creation time,
Period/Point structures and namespace
`urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0`.
The official [XML example](https://gitlab.entsoe.eu/transparency/xml-examples/-/blob/c8353a5eaa58fd052f482e6127df3e5e072622c6/Generation/ACTUAL%20GENERATION%20OUTPUT%20PER%20GENERATION%20UNIT%20%5B16.1.A%5D.xml)
illustrates `MAW` power units and `PT60M` resolution. These are schema/example
facts, not observed contemporary Iberian response profiles. Explicitly map
verified provider unit codes such as MAW to normalized MW; never accept an
unknown unit by similarity of its label.

The legacy `Guide.html` route failed through the browser. Current official help
articles supplied usable endpoint/codes/time/limit evidence. The MoP page links
a v3r5 ZIP that the browser could not render; no whole MoP package was downloaded.
No claim is made to have examined the XSDs inside that ZIP. Selecting concrete supported XML
fixtures/schema versions during implementation is necessary and scoped work.

## H. Open-Meteo verification

**Readiness decision: GO WITH GAPS.** Anonymous archive access was observed;
forecast product/model details and commercial service use remain explicit gaps.

| Dimension | Evidence and decision |
| --- | --- |
| Access/product | **D/O:** `https://archive-api.open-meteo.com/v1/archive` and **D:** `https://api.open-meteo.com/v1/forecast`, JSON GET, coordinates/variables/time parameters. Public noncommercial access requires no key or registration. Do not invent a credential setting. [Archive reference](https://open-meteo.com/en/docs/historical-weather-api), [forecast reference](https://open-meteo.com/en/docs). |
| History/cadence | **D:** ERA5 hourly from 1940, ERA5-Land from 1950; ERA5 updates daily with about five days' delay, while IFS has different coverage/cadence. Select ERA5 explicitly for reproducible historical product identity. Retention/immutability of every historical API result: **U**. [Archive data-source table](https://open-meteo.com/en/docs/historical-weather-api). |
| Forecasts | **D:** forecast horizon up to 16 days; defaults cover seven. **I:** request only next delivery day, with a pinned compatible model recorded in catalogue. Exact issue/model-run time may be absent: **U** until payload verified. Do not use `generationtime_ms` as publication/issue time. |
| Historical forecasts | **D:** dedicated historical-forecast page describes coverage around 2022 and a stitched series, while homepage advertises history from 2021. **U:** model-specific first available date. Do not treat this discrepancy as complete historical-run availability. Single Runs is a separate product and all these paths are deferred. [Historical forecasts](https://open-meteo.com/en/docs/historical-forecast-api), [homepage](https://open-meteo.com/). |
| Time | **D:** Unix seconds are UTC; archive docs describe fixed-offset ISO local-time output and ignoring DST transitions within a range. **I:** always request `timezone=GMT&timeformat=unixtime`; keep original returned timezone/offset and reject contradictions. Weather timestamp semantics differ by variable (§K). |
| Resolution | **D:** hourly; forecast `minutely_15` can involve interpolation outside native high-resolution regions. **I:** hourly only; no weather upsampling to OMIE quarter-hours. [Sub-hourly definitions](https://open-meteo.com/en/docs). |
| Error/missing | **D:** invalid query parameters produce 400 with JSON error/reason. **U:** all future archive/unsupported-model/quota/server variants; no error probes. Null measurements must remain explicit missing values, not zeros; unequal time/value array lengths fail the whole selected acquisition. [Error reference](https://open-meteo.com/en/docs). |
| Revisions | **I:** reanalysis/model corrections or changed API processing can change bytes; preserve versions, model selection, grid coordinates and update observations. No official version ID or no-revision guarantee verified. |
| Bounds | **I:** one coordinate/day/request; 1 MiB raw body, at most 48 timestamps and three variables, 144 measurements maximum. Six locations means six planned acquisitions, not one unbounded multi-location response. JSON pagination not documented for this path. |
| Quotas/terms | **D:** free service is noncommercial; less than 10,000 calls/day, 5,000/hour and 600/minute. Multi-variable/longer windows can count as more calls. Data CC BY 4.0 permits commercial reuse with attribution, but that does not grant commercial free-API service access. [Terms](https://open-meteo.com/en/terms), [pricing](https://open-meteo.com/en/pricing). |

**O:** One anonymous ERA5 archive request for 2026-10-01, requested coordinate
38.72/-9.14, the three selected variables, GMT, Unix time and `wind_speed_unit=ms`:
HTTP 200, 978 bytes, no Content-Encoding, 24 values/variable, units °C, m/s and
W/m². Returned grid coordinate was 38.75/-9.25, demonstrating why requested and
returned geography must both be retained. SHA-256:
`0010fead1a2cf079f4e2280c3e67798514bb5f516304463acfb0a9aa37f27775`.
This verifies one archive response only; no live forecast was requested.

**I — minimal variables:** temperature supports heating/cooling demand; 10 m wind
is an explainable weather proxy, not turbine hub-height output; shortwave
radiation supports solar-resource context. Start with those three common
variables. Humidity/cloud cover/direction add correlated dimensions; rainfall
is insufficient alone for hydro availability without catchments/lags. Defer all
four. A later switch to 100 m wind requires explicit product-height compatibility,
not a silent substitution.

**I — geographic strategy:** six fixed WGS84 locations with stable project IDs;
coordinates are project selections, not provider-certified national averages.

| Project location | Latitude | Longitude | Initial purpose |
| --- | ---: | ---: | --- |
| PT Lisbon | 38.72 | -9.14 | Demand centre/coastal weather |
| PT Porto | 41.15 | -8.61 | Northern demand/coastal contrast |
| PT Bragança | 41.81 | -6.76 | Northern interior/wind-region proxy |
| ES Madrid | 40.42 | -3.70 | Central demand/interior climate |
| ES Zaragoza | 41.65 | -0.89 | Ebro/wind-region proxy |
| ES Seville | 37.39 | -5.98 | Southern heat/solar proxy |

Use fixed sites rather than one national centroid or hundreds of grid points.
Store selection version and returned grid/elevation. No population weighting,
renewable-capacity weighting, national aggregates or engineered weather features
belong in Phase 2. Initial forecast model selection must be supported for all
three variables and both countries; incompatibility fails visibly, with no
silent fallback to `best_match`.

## I. MIBGAS decision

**Readiness decision: DEFER.**

**DEFER TO A LATER PHASE**

**I:** Gas prices plausibly explain combined-cycle marginal fuel costs, especially
when gas sets electricity prices. That is useful enrichment, not a prerequisite
for multi-source ingestion. Benefits need later feature/model evaluation.

**D:** the official public [file-access index](https://www.mibgas.es/en/file-access)
lists 2015–2026 directories; the
[2026 XLS directory](https://www.mibgas.es/en/file-access?path=AGNO_2026/XLS)
lists `MIBGAS_Data_2026.xlsx` (3.16 MB) and `MIBGAS_Data_2026.csv` (62.22 KB),
changed 2026-10-26. Thus machine-readable public files exist; this is not a
claim that the CSV contains every workbook product or that history is complete.
No data files were downloaded and no stable public API specification was located.
**I:** if later selected, start with one annual CSV, a 2 MiB raw cap and
20,000-row ceiling, no workbook dependency and no broad directory crawling;
these proposed bounds do not establish the unseen file schema.

**D:** official [app description](https://www.mibgas.es/en/cccontent/mibgas-app)
distinguishes PVB/VTP, daily/D+1/next-working-day products, EUR/MWh prices and
MWh volumes; app updates and seven-day views are not a guarantee for annual-file
publication or retention. **U:** file schema, gas-day timezone/boundaries, DST,
interval/price methodology, earliest VTP data, revisions, finalization, quotas,
no-data/invalid/future responses and CSV/workbook equivalence: **not verified**.

**D/O:** [legal notice](https://www.mibgas.es/en/cccontent/legal-notice) inspected
is largely privacy/cookies text; it did not establish a clear data reuse licence.
**Category: unclear / legal review may be required.** Authenticated agent trading
web services/certificates are a different mechanism; do not repurpose them for
public data ingestion. Anonymous listing availability does not grant all reuse.

**I:** a future bounded annual CSV reader might avoid a spreadsheet dependency,
but annual mutable files, gas-day/product semantics and licensing add work to an
already meaningful four-provider phase. No MIBGAS contract, credential, fixture,
parser, live call or acceptance requirement is added now.

## J. Normalized domain model requirements

**I:** extend shared immutable contracts with two coherent record families:
**system measurements** and **weather measurements**. Actual/forecast is an
explicit discriminant within each, not a provider-specific class hierarchy.
`LoadObservation`, `LoadForecast`, `GenerationObservation`, `GenerationForecast`
and `InterchangeObservation` can be typed variants of the system family.
`WeatherObservation` must distinguish reanalysis from measured observations;
weather forecast is another variant. Exact Python names may follow repository
style. `GasMarketObservation` is deferred with MIBGAS.

| Requirement | System measurement | Weather measurement |
| --- | --- | --- |
| Business identity | Source, report/product, original series/domain, measure/technology/direction, geography, valid time or interval; forecast edition where available | Source, product/model, variable/height, location selection version, requested/returned grid, valid time/interval; forecast edition where available |
| Source identity | Stable provider/report ID, indicator or document/series IDs, metadata/profile version | Open-Meteo API product, explicitly selected model, variable name and output metadata |
| Geography | Typed country + system/bidding-zone/control-area/provider-area role; native identifier retained; directed endpoints or aggregate external boundary | WGS84 requested coordinates, returned cell/elevation, stable project site ID and country context |
| Time | Either aware UTC valid-at sample or positive half-open interval with UTC start/end; cadence is separate from averaging support | Instant temperature/wind; radiation preceding-hour mean interval; do not force all weather fields into one timing convention |
| Unit/value | Explicit MW power vs MWh energy vs proportion; finite Decimal parsed without float intermediate | Finite bounded float with explicit °C, m/s, W/m² and measurement/statistic; explicit missing representation |
| Actual/forecast | Required kind; status (provisional/final/unknown) only from evidence | Required reanalysis/forecast kind; model is not a sensor |
| Issue/publication | Nullable source issue/publication/update times with semantics, not a renamed acquisition time | Nullable model-run/issue time; acquisition observation time separate |
| Revisions/provenance | Native document revision/series ID if available plus parse-event/raw/acquisition linkage | Product/model/grid and raw linkage; no fabricated provider revision number |

Use a closed discriminated union or typed generic parse result so the runner
can validate these records alongside unchanged `MarketPrice`. Do not use
`dict[str, Any]`, weaken strict/frozen validation, or add units to `MarketPrice`
to smuggle in non-price values. Name schema family/version separately from parse
provenance version; current `MarketSchemaVersion` cannot describe every family.

**I — units/numeric policy:**

| Unit / quantity | Representation | Rule |
| --- | --- | --- |
| EUR/MWh, other market money | Decimal | Direct lexical parse; preserve existing OMIE behavior/string serialization. No new gas/financial series mandatory. |
| MW, MWh (and any explicitly verified GWh) | Decimal | Preserve published decimal precision; MW is not MWh. JSON `parse_float=Decimal` avoids a float intermediate. GWh conversion only with verified unit and explicit Decimal factor. |
| Source positions, identifiers with numeric meaning, counts, durations | Strict integer | Reject bool/coercion/nonpositive interval durations. IDs can remain bounded strings when provider-defined. |
| °C | Finite float | Scientific precision tolerates binary float; broad explicit profile bound, initially -100 to 70 °C, treated as project plausibility limit rather than a provider guarantee. |
| m/s, W/m² | Finite float | Initially 0–150 m/s and 0–2,000 W/m²; fail out-of-profile values visibly, no clipping. Validate source units; request m/s explicitly. |
| %, mm, wind direction degrees | Float if later selected | Percent 0–100, nonnegative precipitation and explicit direction range; currently deferred, no unused mandatory fields. |

Broad physical plausibility bounds are versioned project validation policy;
provider-specific exceptions require explained changes, not silent correction.
No conversion, resampling, weather-to-generation model or feature calculation
is implemented in this assessment or required by this phase.

## K. Time, timezone and DST policy

**I:** normalized instants always have aware zero-offset UTC. Intervals are
half-open `[start, end)` and positive. Retain source timestamps/indices/cadence
and timing interpretation/profile version. Never equate a sample, interval mean,
interval total, publication time and acquisition completion time.

| Source | Observed/documented semantics | Required implementation direction |
| --- | --- | --- |
| OMIE | Accepted Europe/Madrid day for both areas, 60/15-minute profiles | Preserve unchanged; country PT must not switch its market calendar to Lisbon. |
| REN | Offset-free HH:MM labels; 100 quarter-hours with repeated 01h on 2026-10-25; MW axis (**O**) | Europe/Lisbon is **I**, not official timezone evidence. During the REN stage establish a source profile using official clarification or independently timestamped official export/metadata plus ordinary/spring/autumn evidence. Do not obtain ambiguity resolution by consulting another live source during parsing. Without sufficient evidence, retain bytes and fail `time_semantics_unknown`; do not emit guessed UTC intervals. |
| ESIOS | Offset/UTC fields in API example (**D**) | Prefer UTC, cross-check equivalent offset times; record peninsular area explicitly. Identify whether the selected values are samples/smoothed values or interval averages; repeated local labels use offsets, never label deduplication. |
| ENTSO-E | UTC query/response and variable Period resolution (**D**) | Compute position offset from each Period start, resolution and curve type. Validate end bound, overlapping periods, namespace/unit/domain identity. UTC day versus local delivery day is explicit request policy. |
| Open-Meteo | Unix seconds UTC, per-variable instant vs preceding-hour statistic (**D**) | GMT/Unix requests remove fixed-offset DST ambiguity. Keep temperature/wind valid-at timestamps; radiation at t represents `[t−1h,t)`. Retain sample at midnight even if its support interval starts the previous day. |
| MIBGAS | Gas-day/timezone semantics **U** | Deferred; no electricity-calendar reuse by assumption. |

REN's duplicate 01h evidence is stronger than the unsupported claim that every
Portuguese series uses Lisbon, but still does not settle whether power labels
represent interval starts, ends or instants. Store `valid_at` when justified as
a sample; do not invent a 15-minute averaging interval. Require direct semantic
evidence before declaring interval totals or averages. A documented supported
sample convention is acceptable; guessing is not.

Test ordinary/leap days, both European DST transitions, repeated hours and UTC
boundary crossings. Expected 23/24/25-hour days apply only to a verified local-day
profile; a GMT weather day remains 24 samples. Explicitly handle inclusive
provider query ends without retaining an extra endpoint record as a duplicate.
Incomplete selected coverage is an explicit outcome, not automatically a bad
provider day or a green empty parse. Require whole requested completed-day
coverage for actual-series smoke; forecast coverage is its declared returned
horizon (544 does not promise a whole D+1 day).

## L. Forecast/actual/revision semantics

**I:** retain these separate concepts:

| Time | Meaning |
| --- | --- |
| Observation/valid time | When a sampled or realized system/weather quantity applies |
| Delivery interval | Physical support interval for a mean/energy quantity or forecast target |
| Source issue/model-run time | Source-declared forecast edition, nullable if not available |
| Publication/update time | Source metadata with its exact meaning retained; may differ from issue time |
| Acquired-at time | Our independent UTC observation/completion time |
| Forecast horizon | Target time minus known issue time; nullable if issue time is unknown, never calculated from retrieval as a substitute |

Phase 1 already has nullable `RetrievalProvenance.source_published_at`; preserve
it, but one payload-level publication field cannot identify multiple forecast
editions/series. Add typed per-series/record issue/update/revision metadata and
query snapshot identity. No fabricated issue timestamp from an ETag, HTTP
Last-Modified, response-generation duration or apparent delivery date.

Repeated identical acquisitions share raw payload identity and add independent
immutable retrieval events. Identical event IDs remain idempotent. Changed bytes
under the same query/provider key get another hash and independent parse events.
Do not require a provider revision ID to preserve a correction.

Business keys distinguish source/product/geography/measure/valid interval and,
for known forecasts, issue/model-run edition. If the provider omits edition time,
retain separate acquisition snapshots through immutable provenance; mark edition
unknown and do not collapse them or claim a chronological forecast revision
order. Stable normalized identity includes parser/schema versions and raw content
identity; event UUID/time does not change normalized values on replay.

Overlapping sources remain separately identified. Within a provider document,
exact duplicate points may be rejected or explicitly identified as equivalent;
conflicting overlapping series/revisions require documented deterministic
selection with all original bytes retained. Do not select by response order or
arbitrary greatest timestamp. A mutable latest table/view is later platform work.
Historical actuals/reanalysis or forecasts fetched later must not be represented
as information known at a past forecasting cutoff. This phase records the facts
needed for later leakage controls, without building training data/features.

## M. Retrieval/archive/replay implications

**I:** retain the existing content-addressed payload layout and publication
mechanism. XML and JSON are bytes; neither needs another archive backend. Keep
`source/report/day/sha256/hash/payload.bin`; the day is an explicitly defined
query partition for new APIs, not a false claim that one body contains only
that delivery day. Use one day per query to avoid an unnecessary range-partition
migration. Weather radiation support may cross the partition boundary (§K).

Minimum shared extensions, recorded in a focused ADR before their implementation:

1. Add a validated immutable API-query specification associated with the existing
   SourceRequest/resolved acquisition: UTC requested window, provider-area role,
   dataset/series/variables, weather coordinate/model and safe parameter identity.
   Add API snapshot selection semantics; do not pretend an API query has numeric
   OMIE filename revisions or call a snapshot globally latest. Preserve Phase 1
   numeric selection behavior and serialized history through explicit versioning.
2. Generalize typed parse records/schema-family versions (§J) and record forecast
   editions/units/measurement semantics. Keep one raw/retrieval/parse chain and
   backward-compatible readers for existing Phase 1 metadata. Do not rewrite old
   archived events to a new schema.
3. Add a private allowlisted request-construction/auth-header seam to the shared
   retriever. Keep secrets out of SourceRequest, resolved source, filenames,
   serialized query specs and SafeReference. Fixed provider origins, GET, identity
   streaming, TLS, trust_env=False and zero redirects remain the default.
4. Add a typed semantic-result boundary after raw archival for valid no-data or
   provider-error bodies. An HTTP 200 Acknowledgement is a completed acquisition,
   never a successful data parse; add parse outcomes such as source-unavailable /
   provider-rejected with zero records and a controlled reason. Do not falsify
   its HTTP retrieval history as 404 or weaken OMIE's positive-record success rule.

Keep authentication/authorization failure codes distinct for operator action;
retain existing rate_limited, size_limit, budget, content_invalid,
unsupported_encoding and integrity/archive categories. Add a provider semantic
rejection category and a schema/time-semantics controlled reason where current
content_invalid is insufficient for diagnosis. Unsupported domain is a permanent
request/provider rejection, not absent data. No pagination_failure or
compressed_archive_failure category is needed while those paths are unsupported.

Retry policy remains three total attempts, 1/2-second exponential waits with
4-second cap, finite phases/30-second attempt/93-second acquisition budget.
Retry selected transport failures and 500/502/503/504 only. No content, auth,
authorization, invalid-domain, schema, unsupported-encoding or no-data retries.
Respect provider minimum waits; never shorten Retry-After to fit the budget.
For ENTSO-E 429, terminate the invocation because documented bans outlast that
budget. REN/ESIOS/Open-Meteo may use the existing bounded Retry-After rule;
unknown quota details never justify rapid probing. Initial sequential pacing
ceiling of one request/second/provider is project conservatism, not a provider
requirement. Rate policy applies across credentials sharing one provider account.

Recommended bounds in §§E–H are initial application limits, not statements of
provider maxima. Count HTTP attempts across the full planned invocation, not
just per request. With multiple selected system and weather acquisitions, do not hide loops:
the actual minimal request plan is REN 1 + ESIOS 1 + ENTSO-E 3 +
Open-Meteo 6 archive and/or 6 forecast. A single full day for both weather products
has **17 logical acquisitions**, at most **51 physical attempts** before the
ENTSO-E 429 exception, and a conservative global **30-minute/80-MiB** run cap.
A per-provider smoke uses a much smaller explicit plan (§Q). No unbounded date
iteration, provider discovery, polling or concurrent fan-out is introduced.

Parsing limits apply after archival too: bound JSON depth/array/string lengths,
XML elements/depth/expanded points and CPU work. Complete malformed 200 bytes
remain archived, with a failed semantic/parse event and no normalized partial
success; interrupted/oversized transport bodies are not complete archived data.
Persistence failures prevent success, as in Phase 1.

No selected minimum needs pagination or multipart acquisition. If unexpectedly
required, fail coverage explicitly; do not silently accept page one. A narrowly
justified future multi-page path would archive each original response separately
and add a small immutable ordered acquisition manifest of hashes, safe query/page
IDs and completeness. Never concatenate pages and call the result original
provider bytes. Likewise retain an original ZIP body before any bounded decoding;
member hashes/parser version are derived provenance, not replacement raw data.
Do not implement these facilities speculatively.

Every selected product can replay offline from body plus acquisition query
metadata and a versioned local source catalogue. ESIOS units/geos and ENTSO-E code
mappings needed for parsing must be embedded in payload or pinned with catalogue
version/hash, not fetched during replay. Avoid live geocoding, live timezone
resolution, remote XSD loading or indicator-name lookups in any parser. Original
acquisition history remains untouched; new parsing writes only a new parse event.

## N. Authentication and secret handling

**O:** `.env.example` already defines **`ESIOS_API_TOKEN`** and
**`ENTSOE_API_TOKEN`**. Keep those exact names; adding prefixed duplicates is
unnecessary. A presence-only check of those two exported names and exact matching
local `.env` keys found **ESIOS credential present: no; ENTSO-E credential present:
no**. No values, whole environment or `.env` contents were printed. Unrelated
credential stores/variables were not searched; absence here does not prove no
credential exists anywhere on the machine.

**I:** add source-specific validated secret settings only when that provider is
selected, with no automatic dotenv load, import-time I/O or requirements on
anonymous REN/Open-Meteo/OMIE paths. ESIOS injects the key into `x-api-key` at the
private HTTP construction boundary. ENTSO-E GET injects its token into the private
transport query only. A missing selected-provider credential fails before I/O;
401/403 is terminal with a safe operator action, no auto-refresh/probing.

Persist a credential-free query description and opaque safe locator. Logs,
exceptions, Pydantic error inputs, HTTPX/httpcore debug, CLI summaries, fixture
metadata and archive sidecars must never contain key/token values or complete
private URLs/headers. Report only credential presence and controlled auth status.
Do not request pasted secrets. Operators arrange registration/approval and export
credentials themselves, without this assessment sending emails.

No REN/Open-Meteo key is needed for the selected public evaluation mechanism.
A commercial weather subscription/customer endpoint is out of this task; do not
add an unused paid-service secret or activate a subscription automatically.

## O. Dependencies

**I:** no new runtime dependency is presently justified. Reuse HTTPX and Pydantic;
stdlib JSON with Decimal parsing, XML, hashlib, datetime/zoneinfo, CSV if later
needed, and gzip/zipfile only for an explicitly supported concrete path.
No pandas, entsoe-py, Open-Meteo SDK, requests, async framework, dotenv loader,
retry library, spreadsheet reader or provider plugin framework is required.

XML needs explicit security work, not merely `ElementTree.fromstring()` on
unchecked bytes. Python's [XML security documentation](https://docs.python.org/3.12/library/xml.html)
warns about malicious XML and system Expat versions. **I:** use a bounded
namespace-aware stdlib parser with DTD/entity/external-resource rejection before
expansion (parser callbacks or an equivalently tested safe boundary), supported
Expat version checks and element/depth/text/point limits. A raw substring scan
alone across arbitrary encodings is insufficient. Test UTF encodings, entity
expansion and external references. If a reliable maintainable stdlib boundary
cannot satisfy these requirements, justify `defusedxml` at the XML implementation
stage as a security dependency with compatibility tests. Do not add it now or
claim TLS makes XML safe. No dependencies were installed in this task.

## P. Test and fixture strategy

**O/I:** retain the existing `tests/contracts`, `tests/unit/ingestion`,
`tests/integration`, `tests/data` organization. Add small provider directories
and a checksum manifest using the Phase 1 original/synthetic/mutated convention.
Each fixture has safe source pattern, acquisition date, exact hash/length,
selected query/profile/schema, units/time expectations, expected outcome/count,
licence/attribution note and mutation parent/purpose. Preserve original bytes;
shortened or anonymized bodies are labelled synthetic/mutated, never originals.
Where reuse permission is unclear, use synthetic semantic fixtures rather than
committing provider originals pending review. Do not download history into Git.

| Source | Minimum deterministic fixture matrix |
| --- | --- |
| REN | Small complete ordinary-day selected series; spring/autumn labels including repeated 01h; leap/year boundary; incomplete/null/unequal arrays; future/missing/error response synthetic pending real evidence; invalid JSON/HTML/MIME discrepancy; unknown units/series/time semantics; same query corrected content. Preserve observed autumn example only if intentional and rights-reviewed. |
| ESIOS | Indicator 544 and geo/unit metadata; ordinary five-minute curve with native timing semantics; DST offset/UTC equivalence; query end-boundary; explicit missing values/no-data; synthetic 401/403/429 and JSON provider errors; malformed/nested/truncated JSON; revised values_updated_at without fabricated issue time; nonidentity encoding. |
| ENTSO-E | ES A65 actual; PT and ES A69 wind/solar; multiple TimeSeries/Periods/namespaces; A01/A03 including constant blocks and explicit missing sections; variable 15/30/60-minute profiles as synthetic unless observed; UTC/local DST query windows; overlapping/revised document IDs and absent issue time; Acknowledgement no-data vs rejection, 401/429; unsupported domains/units/namespaces; malformed/truncated XML, DTD/entities/depth/size adversaries. |
| Open-Meteo | Archive/reanalysis and forecast objects; units and requested/returned coordinates; 24 UTC hours over a local DST date; midnight preceding-hour radiation; nulls, mismatched arrays, nonfinite/out-of-bound values; invalid parameter JSON; future/unavailable synthetic; corrected archive and separate forecast acquisition snapshots with absent issue time. |

For all mandatory sources exercise real adapter → shared retriever → temporary
archive → parser → parse-event persistence with MockTransport; then replay
without any client. Assert whole-query selected coverage, original bytes/hash,
unit/time/kind/geography, record identity/provenance, correction retention,
unchanged old objects and controlled missing/error results. Unknown selected
fields/records cannot disappear silently. Intentionally unselected datasets or
presentation keys are documented as unselected, not malformed records discarded.

Existing `tests/conftest.py` denies DNS, outbound socket methods and real HTTPX
sync/async transports from configuration/collection onward; it covers the
recommended HTTPX clients and Python XML attempts at remote resources. This is
not an OS sandbox for native libraries/subprocesses. No new guard is required
for selected clients; add proof cases for their construction paths and imports.
Do not introduce subprocess/native networking. Default `python -m pytest` remains
fully offline, needs no tokens, and has no live-enabling switch.

Preserve existing Phase 1 tests and OMIE fixture bytes. Extend checks for schema
compatibility and offline replay of old metadata where shared contracts change.
No fixture checksum is updated merely to conceal an unintended byte change.

## Q. Live-validation strategy

**I:** after offline engineering verification → pre-live engineering audit →
explicit bounded smoke → offline replay. This is the future closure plan, not
work executed in this assessment. A live command must require `--live` before
constructing network dependencies, name source/product/domain/day, print only a
safe outcome and use ignored/external archive roots. No pytest/pre-commit/CI
invocation or periodic publication polling.

| Provider | Smallest required successful live request | Additional request justified by a distinct required path |
| --- | --- | --- |
| REN | One `ElectricityProductionBreakdownDaily` completed day, all selected series, anonymous access | None. Do not repeat the aggregate balance probe. DST semantic evidence can be offline/official clarification; another live day only if essential to establishing the supported time profile. |
| ESIOS | One indicator 544/verified peninsular geo date window, sufficient native samples to verify units/UTC/forecast shape and coverage | If response metadata lacks required geo/unit definition, one bounded official metadata request. Authentication is already exercised by the data request; no separate invalid-key request. |
| ENTSO-E | One ES A65/A16 narrow completed window | One PT A69/A01 and one ES A69/A01 window: two additional requests are justified by distinct required geography and forecast document path. Do not infer PT coverage from ES. One combined wind/solar response per area where supported; only split PSR queries if the official product requires it, with a revised finite call budget stated before execution. |
| Open-Meteo | One coordinate/day ERA5 archive request with all three variables | One same-coordinate next-day forecast request for the distinct forecast/model path. Remaining five points use identical coordinate grammar and deterministic configuration tests; repeated provider smoke at every site adds little evidence. |

Minimum plan is **seven successful logical data requests** (1 + 1 + 3 + 2),
plus at most one necessary ESIOS metadata request. Each request uses finite
transport/size/time limits and at most three physical attempts, so seven data
requests have an upper ceiling of 21 attempts (lower on permanent/ENTSO-E quota
failure). Set an explicit smoke run cap of **15 minutes, 32 MiB**, no unbounded
second-date searches. Use the smallest provider-supported window; a provider
may return a complete day instead. No quota, malformed-date, invalid-key or
publication-delay testing against live services.

Retain raw bytes, safe query metadata, parser/schema/catalogue versions, observed
unit/time/coverage and outcome; replay those exact acquisitions with network
denied and compare normalized values/identities. Only parse UUID/time may differ.
A missing credential/outage/no-data is a recorded external limitation and ends
that run; it is not successful live ingestion. Before closure obtain a deliberate
successful request for every mandatory path or report closure incomplete. A
later operator-authorized attempt is validation, not a new readiness assessment.
This task's REN/weather observations are source evidence, not implementation
live-smoke passes, because the Phase 2 production path does not yet exist.

## R. Security considerations

**I:** maintain fixed HTTPS origins and zero redirects; no arbitrary user URLs,
HTML crawling, certificate bypass or anti-bot circumvention. Provider request
parameters are validated against the selected product before I/O; identifiers
and filenames never become filesystem paths without existing containment checks.

ENTSO-E tokens in GET URLs can leak through exceptions, proxy/debug logs and
provider echoes. ESIOS keys can leak through headers/config dumps. Use the
existing safe-locator boundary and private auth seam, explicit logging setup
and transport-error translation. Never archive request headers or private URLs.
Use synthetic credentials in negative tests, including 401/403/429 and default
transport failures, not just happy-path mocks.

If a provider echoes a credential inside a complete 200 body, unchanged raw
archival and secret exclusion conflict: do not redact and call it original bytes,
and do not publish the secret into the normal archive. Reject safe publication,
report a controlled sensitive-response outcome, retain only nonsecret failure
metadata and require operator handling/rotation. Test this path; raw error bodies
are never printed. Non-200 diagnostic bodies are not successful archived reports.

Bound JSON nesting/strings/arrays and XML parsing/expansion (§O). Refuse remote
DTD/XSD/entity resolution, stylesheet execution and unknown namespace/schema
profiles. Treat presentation strings as data, not Python expressions: REN's
marker/tooltip style strings must never be evaluated. Unknown content coding
fails after preserving safe original bytes; no implicit HTTPX decoding.

ZIP/decompression bombs and malicious member names are relevant future risks,
but ZIP is not a mandatory Phase 2 path. If later justified, stream-decompress
after raw archival with explicit compressed/expanded byte, ratio, member-count,
member-size and CPU bounds; never extract provider member paths to disk or
accept traversal/symlinks/nested archives automatically. No such parser is added
by this assessment. Keep archives on the trusted local filesystem and outside
tracked content; Phase 1 application immutability is not WORM protection.

## S. Licensing/usage observations

These are provider statements and evidence categories, **not legal conclusions**.
Data rights and permission to use a hosted API are separate. Local development
is not automatic permission for commercial collection or redistribution.

| Source | Official evidence | Category and operational boundary |
| --- | --- | --- |
| REN | DataHub footer links corporate [terms](https://www.ren.pt/en-gb/terms-and-conditions), §§2–3.2: reserved rights, restrictions on copying/reuse/substantial extraction; services may have particular conditions. | **Restriction identified; unclear / legal review may be required.** Public documented API supports engineering investigation, but no clear licence for raw redistribution/commercial use was established. Operator/legal confirmation recommended before production use; rights review before committing real response fixtures. |
| ESIOS / REE | [Official Spanish terms](https://www.esios.ree.es/es/aviso-legal-y-politica-de-privacidad), §§6.1–6.2, explicitly cover site and API: source/update attribution, preserve meaning, no endorsement/logo licence, and commercial-use prohibition. | **Restriction identified.** Do not describe the API as commercially open. Operator/legal confirmation recommended before production use; obtain permission or approve a different future production source if necessary. This is a commercial scope dependency, not a reason to invent a technical fallback here. |
| ENTSO-E | Official indexed [2023 reuse list](https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2Fterms+and+conditions%2F231018_List_of_Data_available_for_reuse.pdf) and [terms](https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2Fterms+and+conditions%2F230309_ENTSOE_Transparency_Terms_Conditions_MC_APPROVED.pdf) describe a CC BY 4.0 subset with exclusions. Direct current PDF routes returned the application shell/error; the complete current list was not inspectable. | **Clearly permitted by published documentation for the listed subset; selected item/owner eligibility unclear / legal review may be required.** Do not claim every PT/ES item is licensed solely because it is public. Confirm selected articles/owners against the current list before redistribution/production and retain attribution/change notices. |
| Open-Meteo | [Terms](https://open-meteo.com/en/terms) and [pricing](https://open-meteo.com/en/pricing): CC BY 4.0 data, attribution and modification notices; free API noncommercial only. Paid customer access is separate. | **Clearly permitted by published documentation for data reuse subject to licence; restriction identified for free service access.** Confirm that local evaluation qualifies; operator/legal confirmation recommended before production use. No paid subscription or resource activation is authorized. |
| MIBGAS | Public files and [legal notice](https://www.mibgas.es/en/cccontent/legal-notice); no clear raw-storage/reuse/commercial licence established in the inspected material. | **Unclear / legal review may be required.** Defer. Agent trading API conditions cannot be assumed to govern public-download licensing. |

Attribution should travel with catalogue/provenance and future documentation;
raw storage alone does not fulfill every redistribution obligation. Unknown
rights are not an engineering excuse to remove immutable provenance. Use
synthetic fixtures until rights to distribute real samples are clear.

## T. Risk register

Likelihood/impact are **I — qualitative project estimates**. “Stage gate” means
the identified capability/evidence is required before that stage or final closure;
it does not block safe offline foundation implementation today.

| Risk | Provider | Likelihood | Impact | Mitigation | Blocking? |
| --- | --- | --- | --- | --- | --- |
| Missing/expired/unapproved credentials | ESIOS, ENTSO-E | High now | High | Validate selected-provider configuration, operator access process, terminal safe 401/403 | External dependency; live/closure gate, not implementation-start blocker |
| Undocumented timezone and power timestamp convention | REN | High | High | Preserve labels; establish explicit source profile before UTC emission; DST/interval tests; fail ambiguous data | REN semantic stage gate; no start blocker |
| Wrong series/geo/self-consumption definition | ESIOS/ENTSO-E | Medium | High | Pin official metadata, product/perimeter/unit; distinguish forecast variants and definition dates | Parser acceptance gate |
| A03 treated as missing or silently forward-filled | ENTSO-E | High without controls | High | Versioned A01/A03 profile; bounded Period expansion and missing-section tests | Engineering requirement before XML stage acceptance |
| Quota/token temporary ban | ENTSO-E; all | Medium | Medium | Sequential low-rate calls, global budget, terminal ENTSO-E 429, no polling | Non-blocking operational risk |
| Endpoint/namespace/schema or compression changes | All | Medium | High | Original raw archive, strict versioned profiles, unsupported outcomes, replay | Non-blocking external uncertainty |
| History unavailable or older formats differ | All | Medium | Medium | Declare verified envelope; no completeness/backfill guarantee | Accepted limitation |
| Provisional corrections and missing forecast issue times | All | High | High | Immutable snapshots and nullable source times; no retrospective known-at claim | Accepted limitation; edition-preservation implementation required |
| Large/malicious XML/JSON | ENTSO-E; all | Medium | High | Byte/element/depth/work limits, DTD/entity rejection, test real parser boundary | Engineering requirement |
| Auth material in URL/header/echoed body | ESIOS, ENTSO-E | Medium | High | Private credentials, allowlisted logging/metadata, sensitive-body rejection, synthetic-secret tests | Security acceptance gate |
| Commercial use conflicts with published terms | ESIOS, REN, Open-Meteo | High | High | Operator/legal confirmation before production; no commercial-clearance claim | Production-use restriction; not local implementation-start blocker |
| Incomplete licensing subset evidence | ENTSO-E, MIBGAS | Medium | High | Verify current owner/item terms before redistribution; synthetic fixtures | Commercial/legal uncertainty |
| Six locations poorly represent regional weather | Open-Meteo | Medium | Medium | Explicit fixed-site version/model/grid metadata; later modelling evaluation | Accepted initial limitation |
| Dataset overlap hides semantic disagreement | REN/ESIOS/ENTSO-E | Medium | High | Ownership matrix, no automatic merged latest/fallback | Non-blocking with contract controls |
| Provider outage prevents planned smoke | All | Medium | Medium | Record result, stop bounded run; later authorized validation | Closure external dependency; no invented pass |

No mandatory provider is assigned BLOCKED at readiness. If a concrete source
contradiction prevents a required implementation path, explicitly stop that path
and report the blocker rather than claiming Phase 2 complete.

## U. Recommended implementation stages

Proceed one provider at a time. Keep synchronous local batch execution and
small changes. Each stage includes deterministic tests and diff review. Paths
below describe future authorized implementation areas, not files changed now.

| Stage | Objective | Likely files/areas | Acceptance evidence | Explicit non-goals |
| --- | --- | --- | --- | --- |
| 1 — Shared extensions | Record accepted query/measurement/forecast/auth/semantic-outcome decisions in focused ADR(s); implement versioned strict contracts and minimal private request seam | `contracts/`, shared `ingestion/`, source-selected config, synthetic-secret tests, ADR/index and minimal env comments | Contract tests, old metadata/replay compatibility, OMIE regressions; no secret-bearing serialized state | No provider framework, archive backend rewrite, provider implementation, global mandatory credentials |
| 2 — REN | One documented daily production adapter/parser; resolve concrete time profile and document selected vs ancillary series | `ingestion/ren/`, tests/data/ren, unit/integration tests, runbook additions | Real-shaped/synthetic fixtures, unit/profile/DST evidence, bounded GET/archive/replay, all selected series accounted for | No scraping, page-service forecasts, second aggregate download in normal ingestion |
| 3 — ESIOS | Selected 544 forecast profile, private API-key header, metadata/geo checks | `ingestion/esios/`, catalogue fixture, tests, selected-provider settings/runbook | Verified official metadata, forecast-vs-actual/issue semantics, auth/error/redaction and offline replay tests | No guessed IDs, full catalogue harvesting, generation/settlement archive ingestion |
| 4 — ENTSO-E | ES actual load and PT/ES day-ahead wind/solar, namespace-aware bounded XML | `ingestion/entsoe/`, source catalogue, XML fixtures/tests; shared security fixes only when required | A01/A03/multiple-Period/revision/no-data tests, separate PT/ES coverage profiles, no remote XML resources | No full platform coverage, outages, per-unit generation, flows, capacity, speculative ZIP/pagination |
| 5 — Open-Meteo | Hourly ERA5 archive + forecast, three variables and six fixed sites | `ingestion/weather/`, location/model catalogue, fixtures/tests/runbook | Explicit units/GMT/Unix/instant-vs-mean/model-grid semantics; missing data and snapshot replay | No weighted national features, large grids, historical forecast runs or weather upsampling |
| 6 — Cross-source integration/hardening | Verify shared runner, immutable correction handling, old OMIE compatibility, safe query plans and global budgets | Shared `ingestion/`, `common/` only as needed; contracts/integration/network guard tests | Actual-component mocked flows for every path, repeated/revised acquisitions, offline replay, hostile payload/auth tests | No transformations/features, dedup across unrelated source concepts, new infrastructure |
| 7 — Pre-live engineering audit | Inspect implementation and finite call plans against this report | Code/tests/docs review; focused fixes and audit report | Applicable full offline gates pass; credentials and semantic gaps identified without values; live plan bounded | No second readiness assessment, speculative probes or live execution embedded in tests |
| 8 — Controlled live validation and replay | Run §Q only with explicit opt-in after audit; retain evidence | Separate provider live commands, ignored/external archives, safe evidence report | Seven minimal successful data paths plus needed metadata; checksums/provenance; network-denied replay reproduces records | No bulk history, bad-credential/quota tests, retries beyond policy, provider polling |
| 9 — Documentation and final acceptance | Update actual status/runbooks/catalogues/support envelopes; trace every §V item | README, architecture, ADR index, runbooks, phase implementation/closure reports | Full gates and complete diff/status review; all numbered criteria traced to evidence | No criterion replacement, new assessment, automatic commit/push or Phase 3+ work |

Provider stages may resolve concrete response/schema details within their fixed
products; this does not authorize another readiness assessment. If tokens are
not yet available, continue offline/provider-independent work and leave live
criteria pending. Do not call missing access an authenticated success.

## V. Phase 2 acceptance checklist

This is the **one authoritative final Phase 2 checklist: 44 criteria**. Later
stage/closure reports must reference these numbers and preserve requirements.
A pending mandatory criterion prevents closure; external uncertainties may remain
only within the documented support envelope, not as a waiver of missing behavior.

1. [ ] Accepted Phase 2 query/measurement/auth/semantic-outcome decisions are recorded in focused ADR(s) before corresponding implementation; Phase 1 ADR history is retained and this report remains the sole readiness assessment.
2. [ ] All four mandatory providers and exactly the minimum products in §C are implemented; any scope change is explicitly approved and traced, never silently removed to obtain acceptance.
3. [ ] REN's documented daily production endpoint supplies all selected load/generation/import/export series from one acquisition; ancillary series/presentation fields have explicit selection policy, with no double-counted totals.
4. [ ] REN's timezone and timestamp support convention are established by concrete official/profile evidence; ordinary and both DST profiles normalize without guessed folds or fabricated averaging intervals. Unsupported profiles fail visibly.
5. [ ] ESIOS 544 is verified against official authenticated name/unit/geography/sampling metadata, retained in a versioned catalogue; the peninsular forecast curve is not mislabelled as a complete D-1 forecast or actual load.
6. [ ] ENTSO-E implements ES A65/A16 actual total load and PT plus ES A69/A01 renewable forecasts, retaining document/series/process/domain/PSR identity and distinguishing absent technologies from zero output.
7. [ ] ENTSO-E namespace/version, Period resolution/position and A01/A03 curve handling are explicitly supported and tested, including multiple periods, constant blocks, missing sections and conflicting overlaps.
8. [ ] Open-Meteo archive ERA5 and selected-model forecast ingestion support exactly the three initial variables at six versioned sites, preserving requested/returned coordinates, grid/elevation and model identity.
9. [ ] Query contracts carry validated nonsecret product/window/domain/variables/location/model identity and explicit selection semantics; API snapshots do not fabricate numeric OMIE revisions or guaranteed latest versions.
10. [ ] New system/weather record families and parse schema-family versions are strict, frozen and typed; MarketPrice and Phase 1 serialized archive/provenance remain readable and behaviorally compatible.
11. [ ] Geographic roles distinguish country, mainland/system perimeter, bidding zone, control area, EIC and coordinate; native IDs remain available and directed/aggregate interchange are not conflated.
12. [ ] MW, MWh and EUR/MWh remain distinct; system/market decimals have no binary-float intermediate and financial serialization preserves exact decimal values.
13. [ ] Scientific weather values are finite floats with explicit verified units, height/statistic and versioned plausibility/missing policy; no clipping or implicit unit conversion occurs.
14. [ ] Every normalized time is UTC-aware; instant samples, positive half-open intervals, source cadence and weather preceding-hour support remain distinct and query boundary handling is tested.
15. [ ] Ordinary/leap/year boundaries, spring/autumn DST, duplicate local labels and UTC/local-day crossings are covered where applicable; GMT weather days are not forced to local 23/25-hour counts.
16. [ ] Actual, forecast and reanalysis kind is explicit; issue/publication/update/acquisition times remain distinct and unknown source times/horizons stay null.
17. [ ] Multiple known forecast editions and unknown-edition acquisition snapshots for the same target survive distinctly; historical refetches are never declared known at an earlier market cutoff without evidence.
18. [ ] Source-selected credentials use ESIOS_API_TOKEN and ENTSOE_API_TOKEN, validated before I/O and injected privately using the verified mechanism; anonymous providers and OMIE need neither credential.
19. [ ] Authentication/authorization failures are terminal, safely diagnosed and tested; there is no pasted-secret workflow, implicit dotenv load, auto-registration or token-refresh/probing loop.
20. [ ] Every external call uses finite phase/attempt/operation budgets, response caps, verified TLS, zero redirects and no hidden transport retries; whole-invocation query/attempt/byte/time caps are enforced.
21. [ ] Retry policy has at most three attempts by default with bounded backoff, permanent/content/no-data failures do not retry, Retry-After is never shortened and ENTSO-E token bans end the invocation.
22. [ ] Selected query/record/JSON/XML bounds are implemented and documented; unexpected pagination/truncation/ZIP/content coding gives explicit coverage or unsupported failure rather than partial success.
23. [ ] XML cannot resolve external resources or expand DTD/entities; encoding-aware element/depth/text/work safeguards and hostile-payload tests exercise the actual parser boundary, with any added security dependency justified.
24. [ ] Original complete safe provider body bytes are archived unchanged before transformation/semantic parsing using reused SHA-256 content addressing and atomic no-replace publication.
25. [ ] Independent identical acquisitions reuse content while retaining immutable events; changed bytes under unchanged provider/query/revision keys retain both versions and repeated event IDs remain idempotent.
26. [ ] Retrieval provenance retains safe query/locator, acquisition UTC/status/attempts, native revision observations when known, byte/hash/archive linkage; no private request data is persisted.
27. [ ] Separate parse provenance records parser/schema/catalogue versions and original raw/retrieval linkage; every normalized record links back to that chain and persistence failure prevents success.
28. [ ] Complete malformed safe 200 responses and semantic no-data/error documents are preserved with explicit parse/semantic outcomes and zero normalized success; interrupted/oversized responses never masquerade as complete acquisitions.
29. [ ] Empty/null/missing/unsupported/future/provider-error results are distinguished from successful selected coverage; no bad rows are silently dropped, absent data converted to zero or undeclared partial dataset emitted.
30. [ ] Provider-specific auth/quota/domain/semantic/schema errors map to controlled typed categories, including ENTSO-E acknowledgement context rather than reason 999 alone; raw error text is never logged.
31. [ ] Safe logging/CLI/exception/config/metadata boundaries are tested with synthetic secret-bearing URLs, headers, rejected validation inputs and credential echoes; sensitive raw-body publication is rejected without pretending redaction preserves original bytes.
32. [ ] Each selected product replays entirely offline from archived bytes/history plus pinned catalogue metadata, with no name/geo/schema/weather/model network lookup and no fallback acquisition.
33. [ ] Replay verifies hash/linkage and reproduces fixed-version normalized values and identities; only new parse event identity/time may differ and original retrieval history remains unchanged.
34. [ ] Actual-component mocked integration covers each mandatory product's successful chain, failure chain, correction/duplicate handling and replay through the shared archive/runner.
35. [ ] Small versioned fixtures cover §P's valid/missing/malformed/boundary/time/revision/provider-error cases; manifests protect hashes/inventory, label original/synthetic/mutated evidence and record rights/attribution.
36. [ ] Existing OMIE fixtures and meaningful tests are preserved; shared changes pass Phase 1 regression and old-provenance/replay compatibility tests without weakening assertions.
37. [ ] Repository-wide python -m pytest succeeds with the existing network-denied guard active from collection, without credentials, real providers, subprocess networking or a live-enabling test switch.
38. [ ] Live commands are separate and explicit --live opt-in, refuse before network construction without it, reject fixture archive roots and are absent from pytest/pre-commit/automatic CI execution.
39. [ ] Controlled live validation records successful data through implemented retrieval/archive/parser paths for REN, ESIOS 544, ENTSO-E ES actual plus PT/ES forecasts, and Open-Meteo archive plus forecast; unavailability/auth failure is never counted as success.
40. [ ] The actual live acquisitions in criterion 39 have retained safe checksums/query/provenance/outcomes and successful subsequent network-denied replay; request/attempt totals and deviations from §Q are explained.
41. [ ] Source catalogues/runbooks/README/architecture status describe implemented scope, limits, units/time/forecast semantics, credentials, errors, revisions, replay, live opt-in and attribution/licensing boundaries without claiming production clearance or complete history.
42. [ ] Final Python 3.12 ruff check ., ruff format --check ., mypy src, python -m pytest, git diff --check and applicable pre-commit checks pass; full new/staged/unstaged diff and Git status are reviewed.
43. [ ] No Snowflake/dbt/features/ML/registry/inference/API/dashboard/deployment/Kafka/Kubernetes implementation, paid-resource change, bulk download or unnecessary runtime dependency enters Phase 2.
44. [ ] Final acceptance traces every numbered criterion to concrete code/test/document/live evidence, reports external limitations honestly and leaves commit/push decisions to explicit operator authorization.

## W. Explicit non-goals

Snowflake; dbt; feature engineering; ML; model registry; scheduled batch
inference; FastAPI; dashboard; production deployment; production scheduling;
Kafka; Kubernetes; streaming/service meshes; new cloud resources or paid-service
activation. The intended later architecture remains external sources → ingestion
→ contracts/raw archive → Snowflake RAW/CURATED/FEATURES → training/evaluation
→ registry → scheduled inference → SERVING → API/dashboard.

Also excluded: MIBGAS implementation, wholesale historical backfill, arbitrary
provider plugin frameworks, extra async clients/microservices, universal data
lake abstractions, destructive latest-overwrites-history storage, broad crawling,
load tests and automatic commit/push. This assessment changes only this Markdown
file; it adds no provider code, contracts, fixtures, settings or dependencies.

## X. Final readiness decision

**GO WITH GAPS**

The selected official mechanisms and reusable Phase 1 foundation are sufficient
to begin local, bounded implementation. REN and weather archive checks establish
real machine-readable examples; ESIOS and ENTSO-E have official access mechanisms
and product/code evidence. A small shared extension set handles typed queries,
measurements, forecast editions, private auth and semantic response outcomes
without separate provider infrastructure or an archive redesign.

Credentials, REN time semantics, exact authenticated metadata/XML profiles,
PT/ES coverage and commercial-use permissions remain explicit dependencies.
They do not justify inventing data semantics or declaring closure early. The
44 criteria are the final implementation/acceptance contract; nine stages lead
directly to them. Each mandatory provider is GO WITH GAPS; MIBGAS is DEFER.
There is no engineering blocker to starting Phase 2 and no production-use
clearance is implied.

Assessment delivery verification is documentation-only: `git diff --check`,
applicable pre-commit hooks for this report, and complete status/stat/diff plus
untracked-file review. No repository runtime code was executed, so no
implementation tests are required for this change. The direct observations used
a disposable `/tmp` script and bodies, with no imports from repository code;
initial sandbox connection errors were followed by one approved bounded run.
No authenticated request, bulk download, cloud action, branch change, staging,
commit or push was performed. The expected sole Git addition is
`docs/codex/reports/phase_2_readiness_assessment.md`.


Assessment delivery check results:

| Check | Result |
| --- | --- |
| `git diff --check` and new-file `git diff --no-index --check` | Passed; no whitespace errors. |
| `pre-commit run --files docs/codex/reports/phase_2_readiness_assessment.md` | Passed: trailing whitespace, EOF, large-file and private-key checks; Ruff/format/YAML/TOML skipped as inapplicable to Markdown. |
| Structure/content review | Sections A–X, five provider decisions, nine implementation stages, 44 sequential criteria and three direct observation hashes verified. |
| `git status --short`, `git diff --stat`, `git diff`, cached diff and explicit new-file diff review | Only this report is untracked; tracked working tree/index unchanged. Ordinary Git diffs omit the untracked addition; no-index diff supplies its content/stat review. |

No implementation test suite was run for this Markdown-only task.
