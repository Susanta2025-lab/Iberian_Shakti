# Phase 2 Stage 5 — Open-Meteo forecast model selection

Decision date: **2026-11-03**, Europe/Lisbon. Documentation/source research only.
This is a targeted selection decision, not a replacement readiness assessment,
implementation, empirical forecast comparison, live validation or Stage 6 work.

## 1. Executive decision

**PRIMARY MODEL: DWD ICON-EU, deterministic European domain, approximately 7 km.**
Pin **`models=icon_eu`** on **`https://api.open-meteo.com/v1/forecast`**.
Weighted suitability score: **85/100**; ranking confidence: **MEDIUM**.

**FALLBACK MODEL: ECMWF IFS HRES 9 km**, Open-Meteo selector
**`models=ecmwf_ifs`**, on the same endpoint. Score: **83/100**;
ranking confidence: **MEDIUM**. This is the explicit high-resolution deterministic
product, currently the IFS ENS Control lineage, not `ecmwf_ifs025`, an ensemble
mean, OpenIFS or an unspecified ECMWF default. Selector meanings are confirmed by
the official [OpenAPI][OM-SCHEMA] and [request-to-domain mapping][OM-MAPPING].

ICON-EU offers the best combined fit to the requested hourly energy covariates:
native hourly day-ahead output, one domain covering every site, native radiation
components, openly licensed model code, and useful run-oriented archive options.
IFS is a close, credible alternative with a different upstream producer. The
two-point margin is an engineering preference under the supplied weights, not
evidence of statistically significant Iberian forecast superiority.

Fallback means a documented alternative for a separately approved acquisition
profile, **not automatic substitution**, per-site switching, field filling or
mixing into a primary record. This report changes no runtime configuration.
Stage 5's existing `FORECAST_MODEL=None`, guard, tests and historical profile are
preserved. The missing selection question now has a recommendation for operator
review; forecast implementation and the Stage 5 verdict remain pending.

## 2. Stage 5 requirement and baseline

Existing branch **main**, HEAD **f8dee4c**, `feat: complete Phase 2 ENTSO-E
ingestion`. Initial status contained the expected 17 unstaged Stage 5 paths.
The exact study prompt was saved first at
`docs/codex/prompts/phase_2/phase_2_stage_5_forecast_model_selection.md`.

Read repository instructions, the [readiness assessment][LOCAL-READY], saved
[integration prompt][LOCAL-PROMPT], [Stage 5 report][LOCAL-REPORT], weather
source modules and focused unit/integration tests. Readiness §H named no exact
forecast model; the implementation correctly failed closed. This study preserves
that historical evidence instead of editing the assessment or claiming it had
already made this choice.

Only future weather forecasts for later MIBEL PT/ES day-ahead price inputs are
being selected. Emphasis: **12–48 h leads**, complete next delivery-day coverage,
temperature, 10 m wind and solar timing. Long-range atmospheric headline scores
do not determine this decision. Historical ingestion remains explicit ERA5,
hourly, `kind=reanalysis`; ERA5 is not a historical forecast vintage.

| Fixed site | Country | Latitude | Longitude |
| --- | --- | ---: | ---: |
| PT.lisbon | PT | 38.72 | -9.14 |
| PT.porto | PT | 41.15 | -8.61 |
| PT.braganca | PT | 41.81 | -6.76 |
| ES.madrid | ES | 40.42 | -3.70 |
| ES.zaragoza | ES | 41.65 | -0.89 |
| ES.seville | ES | 37.39 | -5.98 |

The accepted ingestion profile uses bounded UTC weather days. A local MIBEL
delivery day can intersect two UTC dates; one UTC-day response must not be
advertised as complete local-day coverage. A later acquisition planner can
request adjacent bounded weather days when needed. This study changes neither
the shared window contract nor the electricity-market calendar.

## 3. Methodology

First screen geography, selected fields, horizon, identity, operational feed and
published usage terms. Then allocate integer points within the eight requested
weights. Scores measure suitability and evidence strength, not measured weather
accuracy or expected electricity-price improvement. Missing relevant verification
reduces confidence and skill points rather than becoming an invented tie-breaker.

Gate D is interpreted as written: native hourly output is a **strong preference**,
with a substantial penalty for coarser products, not an absolute exclusion of all
6-hourly models. Thus AIFS is scored, but does not win. Missing shortwave output
is a hard Gate B failure; guessed radiation derivations do not pass it.

No weather API, model-update metadata API, data file, checkpoint, credential or
cloud resource was accessed. Only documentation, papers and source/licence files
were read. Search results pointing at live file indexes were not opened as data
validation. Failed documentation fetches are not evidence of model unavailability.
The previous Grid Intelligence repository was not used as individual-model skill
evidence; its unpinned requests would not establish such evidence.

## 4. Evidence hierarchy and references

Priority follows the operator's hierarchy: model/provider documentation;
Open-Meteo documentation/OpenAPI; official source/model cards; peer-reviewed
papers; official verification; independent research; secondary repositories.
Model implementation mappings supplement documentation where per-product fields
or selector aliases would otherwise be ambiguous. Provider `main` source is
implementation evidence, not proof of the exact revision deployed on API servers.

All references below were inspected on the decision date. Dates inside sources
are retained separately. `Documented` means published evidence; `inference` and
`unknown` are explicitly identified in the comparison. No provider observation
is claimed. The DWD direct legal-notice/PDF routes sometimes returned 403; their
indexed official text and DWD's own Natural Hazards Portal were used where stated.

| ID | Authoritative source / evidence scope |
| --- | --- |
| OM-SCHEMA | [Open-Meteo forecast OpenAPI][OM-SCHEMA]: exact `models` enums, variables, units and date parameters |
| OM-MAPPING | [ForecastapiController.swift][OM-MAPPING]: explicit selector/domain mapping and seamless composition |
| OM-ICON | [DWD ICON API][OM-ICON]: products, hourly horizon, native fields and announced grid migration |
| DWD-DATABASE | [DWD ICON database manual][DWD-DATABASE]: native grids, domains and run-dependent horizons; official indexed text |
| ICON-CODE | [ICON licensing][ICON-CODE]: BSD-3-Clause model code |
| DWD-TERMS | [DWD Natural Hazards Portal copyright][DWD-TERMS]: CC BY 4.0 geodata reuse |
| OM-IFS | [ECMWF API][OM-IFS]: distinct HRES/0.25°/AIFS products and field mappings |
| IFS-CYCLE | [ECMWF confirmed 50r1/AIFS v2 implementation][IFS-CYCLE]: 12 May 2026 upgrade |
| IFS-CONTROL | [IFS 50r1 implementation][IFS-CONTROL]: ex-HRES and ENS Control consolidation |
| OPENIFS | [OpenIFS releases][OPENIFS] and [2026 Apache announcement][OPENIFS-LICENCE]: parent cycle and licence |
| ECMWF-DATA | [ECMWF open-data documentation][ECMWF-DATA]: data rights, output grids and rolling retention |
| OM-GFS | [GFS API][OM-GFS]: output cadence and native/derived fields |
| NOAA-GFS | [NOAA EMC GFS][NOAA-GFS]: GFS–UFS–FV3 relationship and operational cadence |
| UFS-LICENCE | [Official UFS LICENSE.md][UFS-LICENCE]: current mixed component licences |
| NOAA-TERMS | [NWS disclaimer][NOAA-TERMS]: public-domain data and attribution/endorsement conditions |
| AIFS-CARD | [ECMWF AIFS Single 2.0 model card][AIFS-CARD]: open weights, 6-hour cadence, resolution and training limits |
| AIFS-OPS | [ECMWF AIFS operational dataset][AIFS-OPS]: current v2, deployment and data licence |
| AIFS-FIELDS | [AIFS v2 implementation][AIFS-FIELDS]: prognostic surface T/10 m wind and diagnostic SSRD |
| ANEMOI | [Official Anemoi licence][ANEMOI]: Apache-2.0 code |
| OM-HISTORY | [Historical Forecast API][OM-HISTORY]: stitched history and per-model starting dates |
| OM-RUNS | [Single Runs API][OM-RUNS]: initialization selector, dates and IFS hindcast caveat |
| OM-UPDATES | [Model update documentation][OM-UPDATES]: initialization, modification and API availability are different times |
| OCF-ARCHIVE | [Open Climate Fix ICON-EU archive card][OCF-ARCHIVE]: archived runs from 2020; now superseded |
| DYNAMICAL | [Dynamical/Open Climate Fix archive documentation][DYNAMICAL]: copied ICON-EU GRIB runs and incomplete-directory caveat |
| DWD-RETENTION | [DWD ICON tutorial 2025][DWD-RETENTION]: 18-month forecast database retention, PAMORE context |
| NOAA-ARCHIVE | [NCEI model archive catalogue][NOAA-ARCHIVE]: historical GFS forecast grids; distinct from analyses |
| OM-MF | [Météo-France API][OM-MF]: ARPEGE/AROME coverage and native fields |
| MF-GRID | [Météo-France current glossary][MF-GRID]: ARPEGE native ~5 km over Europe, 5–24 km globally |
| MF-TERMS | [Météo-France public-data licence page][MF-TERMS]: Licence Ouverte; exact data-service terms remain applicable |
| OM-UKMO | [UK Met Office API][OM-UKMO]: temporal output, extra open-data delay and CC BY-SA 4.0 exception |
| UKMO-CODE | [Met Office UM infrastructure][UKMO-CODE]: tailored model-code partnership licensing |
| OM-KNMI | [KNMI API][OM-KNMI]: domain and distinction from seamless ECMWF extension |
| EUROPE-T2 | [ECMWF European winter temperature verification][EUROPE-T2]: surface observations, conditional 12–48 h relevance |
| ECMWF-VERIFY | [Forecast performance 2025][ECMWF-VERIFY]: official 2026 report, surface skill and terrain qualifications |
| DWD-VERIFY | [DWD Green Book 2024][DWD-VERIFY]: ICON/IFS surface verification, northern hemisphere |
| IBERIA-SOLAR | [Rodríguez-Benítez et al., Solar Energy 2020][IBERIA-SOLAR]: Iberian short-term irradiance; not a current-model 48 h ranking |
| EUROPE-PREPRINT | [Gabler et al., 2026 preprint][EUROPE-PREPRINT]: relevant European surface comparison with competitor-author and processing limitations |
| GRAPHCAST | [Current official GraphCast README][GRAPHCAST]: code/weights terms, August 2026 relicensing and forcing distinction |
| GRAPHCAST-FIELDS | [Open-Meteo GraphCast field enumeration][GRAPHCAST-FIELDS]: no selected surface shortwave field |
| FCN-CODE | [Original FourCastNet licence][FCN-CODE]: BSD-3-Clause source |
| FCN2 | [NVIDIA FourCastNet2 model card][FCN2]: six-hourly fields, hardware and artifact-specific licence |
| AICON-PAPER | [DWD authors' AICON preprint][AICON-PAPER]: operational status, 13 km, 3-hour steps and code-availability statement |
| AICON-FIELDS | [Open-Meteo AICON enumeration][AICON-FIELDS]: supplied surface fields omit shortwave |
| WN2 | [Official WeatherNext repository][WN2] and [Open-Meteo WeatherNext documentation][OM-WN2]: availability and field limitations |
| OM-TERMS | [Open-Meteo terms][OM-TERMS]: free service versus data reuse rights |

Source-code version anchors, Git blob SHA-1s inspected via the GitHub connector:

| Repository file | Inspected blob |
| --- | --- |
| Open-Meteo `openapi/forecast.yml` | `6ad631ea61f9a8a33266a063bc3488d8b7a3555c` |
| `Sources/App/Controllers/ForecastapiController.swift` | `293df67bd4f9fa2b8096831e0e3b6360440408e5` |
| `Sources/App/Icon/Icon.swift` | `6cce7652f304a32a6cc89b3717870814490d9bc5` |
| `Sources/App/Icon/IconDownloadDomains.swift` | `0aab2045a4d34f45cfc5f075cb73191925788f85` |
| `Sources/App/Icon/AiconVariable.swift` | `894a42a392596948f7fb42dbf9f563ebf40aea4d` |
| `Sources/App/Gfs/GfsVariableDownloadable.swift` | `2c0d770260b3adfb3bf688b09ff373a2d951a57d` |
| `Sources/App/Ecmwf/EcmwfVariable.swift` | `62503643f1b0a7347371038d405c20ec510059e4` |
| `Sources/App/EcmwfEcpds/EcmwfEcpdsVariable.swift` | `19666873c521b68e567f83e1fbf489d3fb183106` |

[LOCAL-READY]: phase_2_readiness_assessment.md
[LOCAL-PROMPT]: ../prompts/phase_2/phase_2_stage_5_open_meteo_integration.md
[LOCAL-REPORT]: phase_2_stage_5_open_meteo_report.md
[OM-SCHEMA]: https://github.com/open-meteo/open-meteo/blob/main/openapi/forecast.yml
[OM-MAPPING]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Controllers/ForecastapiController.swift
[OM-ICON]: https://open-meteo.com/en/docs/dwd-api
[DWD-DATABASE]: https://www.dwd.de/DWD/forschung/nwv/fepub/icon_database_main.pdf
[ICON-CODE]: https://www.icon-model.org/icon_model/getting_started
[DWD-TERMS]: https://www.naturgefahrenportal.de/en/copyright
[OM-IFS]: https://open-meteo.com/en/docs/ecmwf-api
[IFS-CYCLE]: https://forum.ecmwf.int/t/confirmation-ifs-cycle-50r1-and-aifs-v2-joint-implementation-on-12-may-2026/14937
[IFS-CONTROL]: https://confluence.ecmwf.int/pages/viewpage.action?navigatingVersions=true&pageId=662505883
[OPENIFS]: https://confluence.ecmwf.int/spaces/OIFS/pages/61124850/OpenIFS%2BReleases
[OPENIFS-LICENCE]: https://forum.ecmwf.int/t/openifs-model-now-available-for-all-under-open-source-apache-2-0-licence/14759
[ECMWF-DATA]: https://www.ecmwf.int/en/forecasts/datasets/open-data
[OM-GFS]: https://open-meteo.com/en/docs/gfs-api
[NOAA-GFS]: https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gfs.php
[UFS-LICENCE]: https://github.com/ufs-community/ufs-weather-model/blob/develop/LICENSE.md
[NOAA-TERMS]: https://www.weather.gov/disclaimer
[AIFS-CARD]: https://huggingface.co/ecmwf/aifs-single-2.0
[AIFS-OPS]: https://www.ecmwf.int/en/forecasts/dataset/aifs-machine-learning-data
[AIFS-FIELDS]: https://confluence.ecmwf.int/spaces/FCST/pages/620418870/Implementation%2Bof%2BAIFS%2BSingle%2Bv2
[ANEMOI]: https://github.com/ecmwf/anemoi-core/blob/main/LICENSE
[OM-HISTORY]: https://open-meteo.com/en/docs/historical-forecast-api
[OM-RUNS]: https://open-meteo.com/en/docs/single-runs-api
[OM-UPDATES]: https://open-meteo.com/en/docs/model-updates
[OCF-ARCHIVE]: https://huggingface.co/datasets/openclimatefix/dwd-icon-eu
[DYNAMICAL]: https://source.coop/dynamical/dwd-icon-grib/README.md
[DWD-RETENTION]: https://www.dwd.de/DE/leistungen/nwv_icon_tutorial/pdf_einzelbaende/icon_tutorial2025.pdf?__blob=publicationFile&v=3
[NOAA-ARCHIVE]: https://www.ncei.noaa.gov/has/has.dsselect?datasetname=6500
[OM-MF]: https://open-meteo.com/en/docs/meteofrance-api
[MF-GRID]: https://education.meteofrance.fr/meteo-a-z/glossaire
[MF-TERMS]: https://donneespubliques.meteofrance.fr/?amp=&fond=dossier&id_dossier=1
[OM-UKMO]: https://open-meteo.com/en/docs/ukmo-api
[UKMO-CODE]: https://www.metoffice.gov.uk/research/weather/weather-science-it/um-infrastructure
[OM-KNMI]: https://open-meteo.com/en/docs/knmi-api
[EUROPE-T2]: https://www.ecmwf.int/en/about/media-centre/aifs-blog/2025/verifying-2-m-temperature-forecasts-wintertime-anticyclonic
[ECMWF-VERIFY]: https://www.ecmwf.int/en/newsletter/187/news/forecast-performance-2025
[DWD-VERIFY]: https://www.ecmwf.int/sites/default/files/elibrary/092024/81600-application-and-verification-of-ecmwf-products-2024-germany.pdf
[IBERIA-SOLAR]: https://www.sciencedirect.com/science/article/abs/pii/S0038092X19311296
[EUROPE-PREPRINT]: https://arxiv.org/html/2608.09972v1
[GRAPHCAST]: https://github.com/google-deepmind/weathernext/blob/main/docs/weathernext1_graph/README.md
[GRAPHCAST-FIELDS]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/GfsGraphCast/GfsGraphCastVariable.swift
[FCN-CODE]: https://github.com/NVlabs/FourCastNet/blob/master/LICENSE
[FCN2]: https://build.nvidia.com/nvidia/fourcastnet/modelcard
[AICON-PAPER]: https://arxiv.org/html/2608.24651v1
[AICON-FIELDS]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Icon/AiconVariable.swift
[WN2]: https://github.com/google-deepmind/weathernext
[OM-WN2]: https://open-meteo.com/en/docs/google-weathernext-api
[OM-TERMS]: https://open-meteo.com/en/terms

## 5. Candidate discovery

Mandatory candidates are evaluated individually: ICON-EU, ICON Global, GFS Global,
IFS HRES and AIFS Single. Additional serious operational comparators are ARPEGE
Europe and UKMO Global: each has a documented explicit product, sufficient horizon
and the selected fields ([OM-MF], [OM-UKMO], [OM-MAPPING]). Research screens cover
GraphCast, FourCastNet/2 and AICON, plus the materially relevant operational
WeatherNext 2 and NOAA AIGFS options discovered in current documentation.

ICON-D2, AROME France and KNMI HARMONIE Europe are screened for geographic
exclusion rather than treated as Iberia-wide high-resolution replacements.
Seamless and `best_match` are reference strategies only. No marginal global model
with weaker documented fit is added merely to lengthen the ranking.

## 6. Hard-gate screening

A = all six sites; B = all three exact variables or documented deterministic
equivalents; C = complete day-ahead horizon; D = native cadence; E = explicit
identity; F = operational source; G = documented usable data/access terms.
`P` means a documented pass, not a tested real response. `P*` for G means use
within the published noncommercial-evaluation terms; it does not authorize free
API use for commercial trading, undisclosed commercial research or production.

| Candidate | A | B | C | D | E | F | G | Classification / precise exclusion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ICON-EU | P | P | P | Hourly to 78 h | P | P | P* | **ELIGIBLE — primary candidate; selected** |
| IFS HRES 9 km | P | P | P | Hourly to 90 h | P | P | P* | **ELIGIBLE — fallback candidate; selected** |
| ICON Global | P | P | P | Hourly to 78 h | P | P | P* | ELIGIBLE — primary candidate, lower ranked |
| GFS Global | P | P | P | Hourly to 120 h | P | P | P* | ELIGIBLE — primary candidate, lower ranked |
| UKMO Global | P | P | P | Hourly to 54 h | P | P | P*, BY-SA exception | ELIGIBLE — primary candidate, lower ranked |
| ARPEGE Europe | P | P | P | Hourly relevant range | P | P | P* | ELIGIBLE — primary candidate, lower ranked |
| AIFS Single v2 | P | P | P | **6 h; large penalty** | P | P | P* | ELIGIBLE — primary candidate, lower ranked; no evidence justifies choosing interpolation here |
| GraphCast | P | **Fail** | Sufficient chained/research horizon | 6 h | NOAA variant selector exists | Research/variant dependent | Current upstream weights open | **RESEARCH CHALLENGER**; no documented selected surface shortwave; cannot pass B |
| FourCastNet / FourCastNet2 | P | **Fail** | Research rollouts | 6 h | No supported matching Stage 5 selector established | Research/experimental feeds | Artifact dependent | **RESEARCH CHALLENGER**; selected GHI absent, E/F integration not established |
| DWD AICON | P | **Fail** | P | 3 h | `dwd_aicon_global_native` | P | Open output; weights not verified | **RESEARCH CHALLENGER**; current Open-Meteo field set lacks shortwave |
| WeatherNext 2 | P | **Fail** | P | Coarse AI output | Explicit ensemble products | Operational feed documented | Code/weights open | **INELIGIBLE** for this stage: no required shortwave in documented product, ensemble scope also excluded |
| NOAA AIGFS | P | **Fail** | P | 6 h | `ncep_aigfs025` | P | Separate model/component rights | **INELIGIBLE**: no native/documented selected shortwave mapping |
| ICON-D2 / AROME France | **Fail** | Not pursued | Not pursued | Fine output | P | P | Not decisive | **INELIGIBLE**: not all six sites, including southern Spain |
| KNMI HARMONIE Europe | **Fail** | Not decisive | 60 h | Hourly | P | P | Not decisive | **INELIGIBLE**: Central/Northern Europe domain cannot be presumed to cover all Iberia |
| `best_match` / provider seamless | Location dependent | May combine products | Broad | May interpolate | **Fail individual identity** | Operational strategy | Mixed | **INELIGIBLE** as a pinned individual primary/fallback; benchmark only |

Eligibility sources: [OpenAPI][OM-SCHEMA], [per-model mapping][OM-MAPPING],
[DWD][OM-ICON], [ECMWF][OM-IFS], [GFS][OM-GFS], [Météo-France][OM-MF],
[UKMO][OM-UKMO], [KNMI][OM-KNMI], and challenger field/licence references in §16.

Geographic inference is explicit: the inspected ICON-EU regular output grid starts
at 29.5°N, −23.5°E and spans 657×1377 points at 0.0625°; every fixed coordinate
lies inside it. ARPEGE Europe's inspected output domain is 20–72°N, −32–42°E.
AROME starts at 37.5°N, excluding Seville (37.39°N); ICON-D2's grid starts at
43.18°N. These are source-code domain checks, not geocoding or live grid probes:
[ICON domain][ICON-DOMAIN], [Météo-France domain][MF-DOMAIN].

[ICON-DOMAIN]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Icon/Icon.swift
[MF-DOMAIN]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/MeteoFrance/MeteoFranceDomain.swift

## 7. Candidate technical profiles and required comparison

All seven eligible rows use `https://api.open-meteo.com/v1/forecast`, one explicit
`models` value, and the same site/variable selections. Native spatial resolution
means model mesh, distinguished from a regular distributed output grid. Native
temporal resolution means published model output, not the physics integration
timestep. All seven can be ingested without running an atmospheric model locally.

The following deliberately wide table contains the full requested comparison.
`HF` is stitched Historical Forecast history; `SR` is Single Runs. Archive dates
are documented catalogue dates, not completeness guarantees. Detailed vintage
qualifications in §10 apply to every row.

| Rank | Model | Provider | Model type | Operational? | Source/weights status | Licence | Coverage | Native spatial resolution / delivered grid | Native temporal resolution | Forecast horizon | Update frequency | temperature_2m | wind_speed_10m | shortwave_radiation | Explicit selector | Historical forecast archive | Run-level/vintage reconstruction | Integration complexity | Score | Confidence | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | ICON-EU | DWD | Deterministic physics NWP, European nest | Yes | Open model code; weights N/A | BSD-3-Clause code; CC BY 4.0 data | All six, Europe | ~6.5 km triangular mesh; ~7 km API label, regular 0.0625° before announced transition | 1 h to 78 h; 3 h later | Main cycles 120 h; Open-Meteo side-cycle importer 30 h, see below | Every 3 h; long cycles 00/06/12/18 | Native 2 m T | Derived from native 10 m U/V | Native direct + diffuse fluxes, provider interval processing | `icon_eu` | HF 2022-11-24; OCF run archive from 2020 | SR 2026-04-02; native-derived run archives, availability caveats | Low, bounded JSON | **85** | MEDIUM | Selected primary |
| 2 | IFS HRES 9 km | ECMWF | Deterministic physics NWP / ENS Control lineage | Yes | Open forecast data; exact current operational source not established open | CC BY 4.0 data; OpenIFS Apache-2.0 is a different release | Global | ~9 km, reduced Gaussian O1280 | 1 h to 90 h; 3 h after; 6 h after 144 h | API up to 15 d; SR table says 10 d; immaterial at 48 h | Every 6 h | Native 2 m T | Derived native 10 m U/V | Native SSRD, deaccumulated/interval normalized by provider | `ecmwf_ifs` | HF catalogue 2017-01-01; not issuance history | SR 2024-03-14, **49r1 hindcasts** before upgrade; 50r1 from 2026-05-12 06Z | Low | **83** | MEDIUM | Selected fallback |
| 3 | ICON Global | DWD | Deterministic physics NWP, separate global domain | Yes | Same open code family; weights N/A | BSD-3-Clause code; CC BY 4.0 data | Global | ~13 km R3B07 native; Open-Meteo overview labels regular product ~11 km | 1 h to 78 h; 3 h later | 180 h 00/12; 120 h 06/18 | Every 6 h in selected feed | Native 2 m T | Derived native 10 m U/V | Native direct + diffuse | `icon_global` | HF 2022-11-24 | SR 2026-04-02; no older complete anonymous native archive verified | Low | **82** | MEDIUM | Eligible, lower resolution and same upstream as primary |
| 4 | GFS Global | NOAA/NCEP | Deterministic FV3/UFS NWP | Yes | Open code family, mixed component licences; weights N/A | LGPL-3.0 / Apache-2.0 / public domain and component notices; native NWS data public domain, API terms separate | Global | ~13 km cubed-sphere computation; Gaussian surface ~0.11°, supplemental 0.25° fields | 1 h to 120 h; 3 h thereafter | 384 h | 00/06/12/18 | Native TMP 2 m | Native UGRD/VGRD at 10 m, speed derived | Native DSWRF surface | `ncep_gfs_global` | HF 2021-03-23 | SR 2026-04-02; NCEI native forecast grids have older run records | Low | **80** | MEDIUM | Eligible; long-range advantage not decisive |
| 5 | UKMO Global 10 km | UK Met Office | Deterministic physics NWP | Yes | Open output, UM code under partnership licences | **CC BY-SA 4.0** output; model code separately licensed | Global | ~10 km native class; API 0.09° | 1 h to 54 h; 3 h after; 6 h after 144 h | ~7 d | Every 6 h; documented extra 4 h open-data delay | Native 2 m T | Native 10 m speed/direction | Native global shortwave flux | `ukmo_global_deterministic_10km` | HF 2022-03-01 | SR 2026-04-02; older suitable native archive not verified | Low technical; rights handling extra | **75** | LOW | Eligible; latency and share-alike burden |
| 6 | ARPEGE Europe | Météo-France | Deterministic stretched-grid global NWP, European output domain | Yes | Open data; exact operational model source openness not established | Licence Ouverte native open data; API CC BY 4.0 terms | All six, European output | Native ~5 km Europe, 5–24 km globally; European API delivery 0.1° (~11 km); not AROME | Hourly day-ahead output | ~4 d | Every 6 h | Native 2 m T | Derived native 10 m U/V | Native global solar field | `meteofrance_arpege_europe` | HF 2022-11-13 | SR 2026-04-02; native historical access/retention not verified | Low | **74** | LOW | Eligible; less matched skill evidence |
| 7 | AIFS Single v2 | ECMWF | Deterministic graph/transformer AI | Yes, v2 from 2026-05-12 | Open weights + open inference framework; not fully reproducible training data | CC BY 4.0 weights/output; Apache-2.0 scripts/Anemoi | Global | ~31 km native N320 class; API regular 0.25° (~25–28 km label) | **6 h**, hourly API values interpolated | 15 d | 00/06/12/18 | Native prognostic 2 m T | Native prognostic 10 m U/V, derived speed | Diagnostic model SSRD at coarse cadence; hourly distribution is provider processing | `ecmwf_aifs025_single` | HF 2025-02-20, version transitions | SR 2026-04-02; v1.1/v2 change must remain explicit context | Low JSON, high hourly-fidelity compromise | **68** | MEDIUM | Eligible under D preference, not recommended |

Technical evidence: [DWD manual][DWD-DATABASE], [Open-Meteo ICON][OM-ICON],
[NOAA GFS][NOAA-GFS], [ECMWF products][OM-IFS], [AIFS card][AIFS-CARD],
[UKMO][OM-UKMO], [ARPEGE][OM-MF], [model mapping][OM-MAPPING] and licensing §8.
ARPEGE's native-versus-delivered mesh distinction is documented in [MF-GRID].
The native ICON Global ~13 km and API overview ~11 km labels are not treated as
equal scientific resolution. Neither the Open-Meteo output lattice nor a finer
latitude/longitude spacing creates extra native model skill.

### ICON-EU cadence and imminent grid change

The [inspected downloader][ICON-DOWNLOAD] uses full ICON-EU cycles to 120 h,
hourly through 78 h, and 30-hour side cycles. The current DWD manual's indexed
text describes additional short cycles to 51 h. These are different claims
(provider capability versus provider integration); assume only the conservative
30-hour importer support for side cycles until controlled validation establishes
otherwise. The main cycles comfortably cover D-1→D. An eight-updates/day label
does not mean every update is an independent five-day forecast.

Open-Meteo explicitly announces native-grid transition **after 30 November 2026**
for `dwd_icon_eu`/global/D2. `icon_eu` and `dwd_icon_eu` currently map to the same
individual EU product in source, including regular/native storage handling;
this does not blend EU with global or D2 for the selected three fields. Pin the
OpenAPI spelling `icon_eu`; record the documented transition as product context.
Do not assert grid immutability from selector immutability. Requested sites stay
fixed while returned cells/elevation and raw snapshots preserve changed processing.
This announced transition warrants a profile compatibility check, not a model
selection reopening or an automatic switch to another model.

[ICON-DOWNLOAD]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Icon/IconDownloadDomains.swift

### Surface-field fidelity

For ICON, native `t_2m`, `u_10m`, `v_10m`, `aswdir_s` and `aswdifd_s`
support the selection. Speed is the norm of native wind components; GHI is the
sum of direct horizontal and diffuse radiation. Open-Meteo handles source
time-averaged radiation before exposing its hourly preceding-interval mean.
For GFS, the inspected downloader explicitly maps shortwave to `DSWRF:surface`.
For IFS/AIFS, `ssrd` is a native/diagnostic accumulated energy field, with provider
interval processing and J/m²-to-W/m² normalization. No local conversion,
cloud-to-radiation estimator or replacement solar model is needed in Stage 5.
See [ICON fields][ICON-VARS], [GFS mappings][GFS-VARS], [IFS HRES mappings][IFS-VARS]
and [ECMWF coarse-product mappings][ECMWF-VARS].

Shortwave is **surface global horizontal radiation**, not top-of-atmosphere
forcing, net radiation, tilted-panel irradiance, a daily sum or the instant
variant. The API's `shortwave_radiation` uses W/m² and mean support `[t−1h,t)`;
temperature/wind are instant samples. With AIFS, that hourly radiation support
is provider-distributed from a six-hour product, not six independently predicted
hourly cloud/radiation states. This is a material drawback for price inputs.

[ICON-VARS]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Icon/IconVariableDownloadable.swift
[GFS-VARS]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Gfs/GfsVariableDownloadable.swift
[IFS-VARS]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/EcmwfEcpds/EcmwfEcpdsVariable.swift
[ECMWF-VARS]: https://github.com/open-meteo/open-meteo/blob/main/Sources/App/Ecmwf/EcmwfVariable.swift

Open-Meteo normally selects a suitable land grid cell and uses elevation context
for downscaling. A city request therefore does not mean a station forecast or an
untouched native grid value. Retain requested coordinates separately from returned
cell/elevation; do not add project interpolation or regional averaging. This is
documented API processing, not an observed result of this study ([OpenAPI][OM-SCHEMA]).

## 8. Open-source, weights, output and licensing

For Ranking B, eligible candidates must expose either (a) weather model source
under a recognised open-source licence, beyond just a client SDK; or (b) usable
inference code and released weights with published reuse terms. An open-weight
model is labelled as such rather than described as fully reproducible training.
Open forecast output alone does not satisfy that definition.

| Candidate | Model source / inference code | Weights | Forecast output | Commercial use / redistribution distinction |
| --- | --- | --- | --- | --- |
| ICON-EU and ICON Global | ICON code BSD-3-Clause; numerical integration is the inference engine | N/A | DWD CC BY 4.0 | Code and data allow reuse under their respective notices/attribution; free API access remains noncommercial |
| GFS Global | UFS/FV3 source open; current licence manifest mixes LGPL-3.0 components, Apache-2.0 physics/framework, public-domain US work and further component licences | N/A | NWS data generally public domain unless annotated; Open-Meteo service terms separate | No blanket claim that the entire coupled system is Apache, BSD or public domain; source/binary redistribution follows each included component |
| IFS HRES | Exact current 50r1 operational source/assimilation system not established as an open release; OpenIFS 48r1 is Apache-2.0 | N/A | ECMWF CC BY 4.0 | Data reuse and redistribution with attribution; this does not grant the current operational source tree or free commercial API access |
| AIFS Single v2 | Anemoi Apache-2.0; demonstration/inference scripts Apache-2.0 | ECMWF CC BY 4.0 | ECMWF CC BY 4.0 | Published weights/code support commercial reuse under their licences; some 50r1 esuite fine-tuning data are unavailable, preventing full training reproduction |
| ARPEGE Europe | Exact current operational source release/licence not verified; no open-source claim from IFS ancestry | N/A | Native Licence Ouverte, API data terms apply | Reuse requires applicable notices; model source rights are not inferred from data rights |
| UKMO Global | UM under tailored partnership licences; not open merely because FCM/build tools are open | N/A | **CC BY-SA 4.0** as documented by Open-Meteo | Commercial data use possible under that licence; redistribution/adaptations require applicable attribution/share-alike compliance; downstream product treatment remains to be assessed |
| GraphCast | Apache-2.0 upstream code | **Current CC BY 4.0**, explicitly updated 2026-08-06 from CC BY-NC-SA 4.0 | Feed-specific output/access terms | Do not repeat the obsolete blanket noncommercial-weights prohibition; archived forks/checkpoints need artifact-specific notices checked |
| FourCastNet / FourCastNet2 | Original FourCastNet source BSD-3-Clause | Artifact-specific; NVIDIA's inspected FCN2 packaged model uses **NVIDIA AI Product Agreement** | Research/feed specific | Original code licence does not prove every checkpoint is BSD; inspected packaged artifact permits commercial use subject to its own agreement |
| AICON | Anemoi code Apache-2.0; DWD-specific full model/inference release and weight licence not verified | No authoritative released-weight licence established | DWD open output | Anemoi licence and ICON's BSD licence do not automatically license AICON checkpoints or its complete operational code |
| WeatherNext 2 | Official code Apache-2.0 | Upstream CC BY 4.0 materials | Platform/API terms separate | Openness does not cure the missing selected radiation field or change excluded ensemble scope |
| AIGFS | Source/weight package licence not established in this screen | Not verified | NOAA feed and API terms separate | Excluded by missing required field; no broader open-source claim is needed |

Sources: [ICON-CODE], [DWD-TERMS], [UFS-LICENCE], [NOAA-TERMS], [ECMWF-DATA],
[AIFS-CARD], [ANEMOI], [MF-TERMS], [UKMO-CODE], [OM-UKMO], [GRAPHCAST],
[FCN-CODE], [FCN2], [AICON-PAPER], [WN2], [OM-TERMS].

### OpenIFS is not current operational IFS HRES

OpenIFS 48r1 was first released in January 2024 and re-released under Apache-2.0
on **5 March 2026**. Its parent is **IFS CY48R1**, operational **27 June 2023–
11 November 2024**. Current release documentation gives a 48r1.1 tag example dated
2026-08-25. Operational IFS advanced through 49r1 to **50r1 on 12 May 2026**.
OpenIFS releases do not accompany every operational cycle ([OPENIFS],
[OPENIFS-LICENCE], [IFS-CYCLE]).

Same-cycle forecasting ancestry is not evidence of identical current source,
assimilation, initial conditions, configuration or binaries. OpenIFS's research
forecasting code is not a mechanism to reproduce the current 9 km operational
product bit for bit. Therefore IFS HRES is classified **open forecast data only
for this current-product comparison**, and excluded from Ranking B; OpenIFS
itself is genuinely open-source software. No OpenIFS local execution is proposed.

### Service terms are independent

The published free Open-Meteo API is limited to noncommercial use; subscriptions
are the commercial access route. The usual API data licence is CC BY 4.0, with
the UKMO BY-SA exception. Code, weights, forecast output, service access and
redistribution are separate rights. This report selects a model suitable for
the repository's evaluation stage; it does not determine that future commercial
trading or undisclosed commercial research qualifies for free service, purchase
access, or grant legal clearance ([OM-TERMS], [OM-UKMO]).

## 9. Iberian and day-ahead forecast relevance

No current, independent, like-for-like study was found validating **all three
variables at all six sites at 12–48 h**, with identical operational cutoffs and
versions. There is consequently no responsible claim that ICON-EU is universally
the most accurate weather forecast for Iberia.

| Evidence | Applicability and weight in decision |
| --- | --- |
| [ECMWF winter European T2 verification][EUROPE-T2], May 2025 | AIFS can improve T2 RMSE in stable winter conditions, including 36–48 h. European stations, older versions, regime-specific; not a solar/wind or six-city conclusion |
| [ECMWF 2025 performance report][ECMWF-VERIFY], published May 2026 | AIFS surface T/wind advantages over IFS, particularly flatter European terrain. Official verification supports AIFS skill credit despite cadence penalty; not Iberian hourly irradiance proof |
| [DWD 2024 surface verification][DWD-VERIFY] | ICON and IFS compared at 24/120 h over northern-hemisphere stations. Supports operational surface forecasting competence; ICON Global results are not automatically ICON-EU site rankings |
| [Iberian solar study][IBERIA-SOLAR], 2020 | Four-station, two-year evaluation at up to 6 h; season and coastal effects matter. Wrong lead range/model generation for ranking current day-ahead candidates |
| [European 2026 preprint][EUROPE-PREPRINT] | Relevant wind/T/GHI and 1–48 h comparison includes ICON-EU. Authors work for competing vendor Jua; not peer reviewed. Results include rolling bias adjustment/bilinear station mapping. Spain has no solar stations in the described network; Portugal absent from its country list. Useful secondary support, not decisive Iberian validation |

The last study reports favourable ICON-EU European results, but its processing
is not Stage 5's raw ingestion, and its solar panel cannot establish Iberian
solar skill. No debiasing, station interpolation, vendor benchmark pipeline or
claimed numeric Iberian accuracy improvement is imported into the project.
Generic global ACC/500 hPa and cyclone claims carry little weight here.

Engineering inference: coastal demand sites, Bragança's terrain, Zaragoza's wind
context and Seville's solar/heat context benefit from preserving hourly weather
timing and source geography. Finer mesh may help representation but does not
guarantee skill. 10 m wind is an exogenous weather proxy, not turbine-height
power output; no 80/100/120 m substitution is warranted by this study.

Run initialization is not publication. The exact price-prediction issuance time
and operational run-availability policy are not specified in the project. Main
ICON-EU cycles and IFS horizons give comfortable day-ahead room, but whether a
particular run is available before an actual cutoff remains a live timing check.
Use documented intervals as planning context, never guessed per-response issue
times. UKMO's additional documented four-hour open-data delay weakens that fit.

## 10. Historical forecast and vintage analysis

Three concepts must remain separate: stitched near-initialization history;
initialization-addressable model output; and proof of **actual availability before
a historical decision cutoff**. Only the last establishes what could have been
known then. Initialization alone does not establish publication latency.

| Model | Open-Meteo stitched HF start | Open-Meteo individual runs | Provider/native archive evidence and practical limitation |
| --- | --- | --- | --- |
| ICON-EU | 2022-11-24 | 2026-04-02 documented SR general start | OCF records four runs/day from 2020-01-01; early subset includes T2, 10 m U/V and direct/diffuse shortwave. Old HF dataset no longer updated; successors on Dynamical/Source Cooperative. Check spatial/version/field/step completeness and availability before use |
| ICON Global | 2022-11-24 | 2026-04-02 | DWD operational database/PAMORE access is not a perpetual anonymous forecast archive; 2025 tutorial cites 18-month retention. Earlier exact-product availability unknown |
| GFS Global | 2021-03-23 | 2026-04-02 | NCEI has older forecast-grid records with initialization/lead identity; grid-4 catalogue dates reach 2006, not a promise of the exact current 0.11° hourly surface product. Analyses are separate datasets |
| IFS HRES | Catalogue 2017-01-01 | 2024-03-14; docs identify **IFS 49r1 hindcasts**, then 50r1 from 2026-05-12 06Z | ECMWF native open-data retention is only latest 12 runs (~2–3 days). Long historical access uses other archive/service arrangements. Do not call a retrospective 49r1 hindcast a forecast available in March 2024 |
| ARPEGE Europe | 2022-11-13 | 2026-04-02 general SR start | Older native run archive/access and exact selected-field retention not verified |
| UKMO Global | 2022-03-01 | 2026-04-02 general SR start | Older native run archive/access not verified; BY-SA redistribution context remains relevant |
| AIFS Single | 2025-02-20 catalogue start | 2026-04-02 general SR start | Catalogue begins around pre-operational launch; current v2 begins 2026-05-12. No assumption that early archived records use current weights or were operationally available |

Sources: [OM-HISTORY], [OM-RUNS], [OCF-ARCHIVE], [DYNAMICAL],
[DWD-RETENTION], [NOAA-ARCHIVE], [ECMWF-DATA], [AIFS-OPS].

The OCF archive card documents the 2020–March 2023 subset and subsequent expanded
schema; the successor copies original GRIB per initialization and lead. Public
archive storage does not prove complete uploads or historical API availability.
No archive body was downloaded or its completeness certified here.

HF uses the historical host `historical-forecast-api.open-meteo.com` and stitches
initial model hours. SR uses `single-runs-api.open-meteo.com/v1/forecast`, with
`run=YYYY-MM-DDTHH:MM` as initialization. The same explicit selectors identify
the eligible models. The docs advertise compatible weather fields/output formats;
per-model/day availability remains untested. HF's 2017 IFS start is especially
not proof of multi-year operational 9 km forecast vintages ([OM-HISTORY], [OM-RUNS]).

Native runs or SR make target-minus-initialization lead reconstruction possible;
cutoff-correct training additionally needs publication/availability evidence,
model-cycle context and an explicit run-selection policy. ECMWF retrospective
hindcasts can be useful experiments, but must carry that status and cannot prove
historical tradability. Neither latest forecasts fetched today nor ERA5 supplies
missing historical forecasts. No Historical Forecast, Previous Runs or Single
Runs ingestion is implemented or authorized by this study.

Open-Meteo documents separate initialization, conversion/modification and API
availability metadata, with possible server-copy lag. Such metadata is not
automatically attached to each current forecast response, and no metadata
endpoint was queried. Preserve acquisition/parse timing; do not fabricate issue
or run time from it ([OM-UPDATES]).

## 11. Weighted scoring

Each cell is an awarded number of points, already weighted. Column maxima are
exactly the operator's weights. Scores are judgement-based evidence allocations,
not transformations of an invented measured RMSE. Totals are integer sums.

| Model | Skill /25 | Native cadence + horizon /15 | Iberian spatial fit /10 | Variable fidelity /10 | History/vintages /15 | Operations/updates /10 | Openness/rights/reproducibility /10 | Simplicity /5 | Total /100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ICON-EU | 16 | 15 | 9 | 10 | 12 | 9 | 9 | 5 | **85** |
| IFS HRES | 18 | 15 | 9 | 10 | 11 | 10 | 5 | 5 | **83** |
| ICON Global | 16 | 15 | 7 | 10 | 11 | 9 | 9 | 5 | **82** |
| GFS Global | 13 | 15 | 7 | 10 | 12 | 10 | 8 | 5 | **80** |
| UKMO Global | 14 | 15 | 8 | 10 | 11 | 7 | 5 | 5 | **75** |
| ARPEGE Europe | 13 | 15 | 7 | 10 | 11 | 8 | 5 | 5 | **74** |
| AIFS Single v2 | 18 | 5 | 5 | 7 | 11 | 8 | 9 | 5 | **68** |

Component rationale, in the same eight-column order:

- **ICON-EU:** (16) relevant surface evidence, but no complete independent Iberian
  trial; (15) native hourly safely beyond 48 h in main runs; (9) fixed European
  ~7 km domain contains every point; (10) selected native T/wind/radiation fields;
  (12) run archive options back to 2020 complement recent SR, with gaps/latency
  unresolved; (9) mature DWD feed, side-run and announced-grid-change qualifications;
  (9) BSD code and attribution data, exact operational reconstruction not promised;
  (5) fits the current JSON/archive contracts. Evidence §§6–10.
- **IFS HRES:** (18) strong official European surface evaluation context without
  claiming six-site dominance; (15) hourly to 90 h; (9) 9 km global grid;
  (10) all required native fields; (11) long run-addressable catalogue discounted
  for hindcasts and unknown publication history; (10) mature four-cycle operation;
  (5) open data, exact current operational source not established open;
  (5) simple same-endpoint integration. Evidence [OM-IFS], [IFS-CYCLE], [OM-RUNS],
  [ECMWF-VERIFY], [OPENIFS].
- **ICON Global:** (16) official northern-hemisphere surface evidence, regional
  transfer uncertainty; (15) hourly to 78 h; (7) coarser than EU; (10) native
  selected fields; (11) recent SR and uncertain older run archive; (9) mature
  feed but same DWD transition/dependency; (9) open code/data; (5) simple JSON.
  Evidence [DWD-VERIFY], [DWD-DATABASE], [ICON-CODE], [OM-MAPPING].
- **GFS:** (13) credible operational system but weaker matched Iberian evidence
  found; (15) native hourly day-ahead; (7) ~13 km grid; (10) correct native fields;
  (12) useful older native forecast archives, exact product mismatch caveat;
  (10) mature four-cycle feed; (8) open ecosystem with component-licence and
  operational-configuration complexity; (5) same ingestion shape. Evidence
  [NOAA-GFS], [GFS-VARS], [NOAA-ARCHIVE], [UFS-LICENCE].
- **UKMO:** (14) established forecasting competence, sparse directly matched
  evidence in this screen; (15) hourly through 54 h covers intended leads;
  (8) ~10 km global coverage; (10) native selected fields; (11) recent run archive,
  no older verified vintage source; (7) documented extra dissemination delay;
  (5) open output with share-alike, not open operational code; (5) straightforward
  JSON. Evidence [OM-UKMO], [UKMO-CODE], [OM-RUNS].
- **ARPEGE:** (13) no persuasive matched 12–48 h six-site comparison found;
  (15) hourly relevant range, ~4-day horizon; (7) European 0.1° API output despite
  a finer native stretched mesh;
  (10) required native fields; (11) recent run archive, older vintage uncertainty;
  (8) established six-hour cycles but less examined here; (5) data openness,
  operational source rights not verified; (5) same JSON integration. Evidence
  [OM-MF], [MF-DOMAIN], [OM-RUNS], [MF-TERMS].
- **AIFS:** (18) credible European T/wind skill earns equal skill points to IFS;
  (5) ten-point cadence penalty for six-hour predictions; (5) coarser ~31 km
  native grid; (7) additional radiation-fidelity penalty for distributing coarse
  diagnostics into hourly energy covariates; (11) recent run archive but version
  changes; (8) operational v2 has a shorter track record than mature physics
  systems; (9) open weights/code, unavailable fine-tuning data; (5) no local AI
  infrastructure required. Evidence [AIFS-CARD], [AIFS-FIELDS], [EUROPE-T2],
  [ECMWF-VERIFY], [ANEMOI]. The two penalties distinguish temporal sample density
  from the resulting hourly radiation/support fidelity; no new disqualification
  is hidden in the score.

No skill score exceeds 18/25 because relevant Iberian validation is incomplete.
The 85 versus 83 margin is sensitive: reallocating three judgement points in skill
or vintage confidence could reverse it. If the openness advantage were removed,
IFS would lead; that is why the overall recommendation is MEDIUM confidence,
not a claim of a clear weather-accuracy winner. The supplied weights explicitly
value openness, making ICON-EU the selected engineering choice now.

## 12. Ranking A — overall Stage 5 suitability

| Rank | Eligible model | Score | Confidence | Main reason for position |
| --- | --- | ---: | --- | --- |
| 1 | **DWD ICON-EU** | **85** | MEDIUM | Hourly European fields, open code/data and run-archive options |
| 2 | **ECMWF IFS HRES 9 km** | **83** | MEDIUM | Excellent close alternative; current operational source and hindcast caveats |
| 3 | DWD ICON Global | 82 | MEDIUM | Full hourly fields/open code, coarser and same producer as primary |
| 4 | NOAA GFS Global | 80 | MEDIUM | Mature hourly/open system, older archive options; weaker matched skill evidence |
| 5 | UKMO Global | 75 | LOW | Sound fields/resolution; latency, rights and evidence disadvantages |
| 6 | ARPEGE Europe | 74 | LOW | Compatible hourly output, fewer demonstrated advantages for this specific use |
| 7 | ECMWF AIFS Single v2 | 68 | MEDIUM | Surface skill is credible, six-hourly generation compromises the selected use case |

## 13. Ranking B — open-source/open-weight eligible models only

The scoring weights and points are unchanged; this is a filter, not a new rubric.

| Rank B | Model | Openness classification | Overall score | Confidence |
| --- | --- | --- | ---: | --- |
| 1 | ICON-EU | Open-source numerical model code | 85 | MEDIUM |
| 2 | ICON Global | Open-source numerical model code | 82 | MEDIUM |
| 3 | GFS Global / UFS–FV3 | Open-source model ecosystem, mixed component licences | 80 | MEDIUM |
| 4 | AIFS Single v2 | Open weights plus open inference code | 68 | MEDIUM |

IFS HRES is excluded from this filtered ranking, without denying OpenIFS's
Apache licence. ARPEGE and UKMO lack evidence of an openly released exact current
operational model. GraphCast is now open-weight under published updated terms,
and original FourCastNet code is open, but neither passes the Stage 5 field/feed
screen; openness does not create eligibility. AICON weight/source openness is
not established. See §8 for each distinct right and §16 for exclusions.

## 14. Primary recommendation

Select **DWD ICON-EU / `icon_eu`**. The decisive combination is:

1. Native hourly day-ahead T2/10 m wind with radiation components supporting
   the requested preceding-hour GHI, avoiding a six-hourly AI-output dependency.
2. One approximately 7 km European product covers all six fixed points; neither
   geocoding nor location-dependent provider switching is required.
3. BSD-3-Clause model code and CC BY 4.0 output are separate, documented rights.
4. Recent model-run archives and older native-derived ICON-EU archives provide
   a credible later vintage path, with explicit completeness/cutoff limitations.
5. Integration uses existing bounded HTTP/JSON, `WeatherMeasurement`, immutable
   archive/provenance and replay, with no GPU or weather-hosting service.

These are evidence-based fit arguments from §§6–11, not proof of optimal price
prediction. A later actual six-site weather/price evaluation may recommend a
new versioned selection, while preserving original acquisitions.

## 15. Fallback recommendation

Select **ECMWF IFS HRES 9 km / `ecmwf_ifs`** as the sole named fallback. It
provides the three fields hourly through the relevant horizon and diversifies
the upstream producer. ICON Global is a close lower-ranked candidate but shares
DWD failure modes; it is not the designated fallback. GFS is compatible but
does not displace IFS on this evidence/weighting.

No fallback requests are authorized now. Any later use must produce a distinct
canonical product/model identity and independent acquisition history, never
retain `icon_eu` provenance on IFS values. A failure of a primary variable/site
must remain visible; do not fill it with fallback values or zeros. Switching
profiles requires explicit operator scope, not an opportunistic runtime default.

## 16. Rejected models, challengers and reference strategies

| Candidate | Technical/openness finding | Stage 5 decision and ranking confidence |
| --- | --- | --- |
| GraphCast | 0.25°, six-hour research model; explicit NOAA/Open-Meteo variant exists. Upstream weights now CC BY 4.0, code Apache-2.0. TOA incident radiation is a forcing, not predicted surface GHI | RESEARCH CHALLENGER, **B fails**; current field enumeration has no shortwave; no inference of a supported surface-radiation formula. LOW suitability confidence, HIGH confidence in the inspected-field exclusion |
| FourCastNet / FourCastNet2 | Original AFNO code BSD-3-Clause; FCN2 SFNO native six-hour output. Inspected 73-variable FCN2 card includes T2 and 10 m U/V but no surface shortwave. Packaged weights licence differs from original source | RESEARCH CHALLENGER, **B/E/F integration not satisfied**; experimental/local GPU inference is not the accepted ingest path. LOW ranking confidence |
| AICON | Operational since 2026-03-02, native ~13 km triangular grid and three-hour steps. Open-Meteo imports 00/06/12/18 runs, 180 h at 00/12 and 120 h at 06/18. Anemoi framework open; DWD-specific weights/code licence unverified | RESEARCH CHALLENGER, **B fails** in current AICON field enumeration; no shortwave. LOW ranking confidence; operational status is not dismissed as mere research |
| WeatherNext 2 | Credible current open-code/open-weight, global 0.25° AI feed; Open-Meteo exposes ensemble and mean strategies. Documented selected fields omit shortwave | INELIGIBLE under **B**, and outside deterministic nonensemble scope; no new local TPU/GPU path. LOW ranking confidence |
| NOAA AIGFS | Operational NOAA emulator, six-hour output and explicit Open-Meteo selector. Product documentation lists temperature/wind/pressure/precipitation/humidity, not selected solar radiation | INELIGIBLE under **B**; model-specific openness was not needed to establish exclusion. LOW ranking confidence |
| ICON-D2 / AROME / HARMONIE regional options | High resolution is attractive, but documented domains do not establish all-six-site coverage; AROME excludes Seville even at its rectangular boundary | INELIGIBLE under **A**; no seamless geographic extension permitted. HIGH confidence in exclusions based on explicit inspected domains; MEDIUM for HARMONIE domain screen |
| `best_match` | Provider strategy selects from models/domains by place and variable; composition can evolve | Reference benchmark only, fails individual-model **E**. Raw replay reproduces saved values but does not reveal every unstated component/run used |
| ICON/GFS/Météo-France seamless | ICON may combine global/EU/D2; GFS may add HRRR; Météo-France adds AROME to ARPEGE. Composition/availability varies; fields may use different readers | INELIGIBLE as an individual pinned primary. A strategy name and raw bytes alone do not establish component-level lineage. Use individual selectors instead |

Sources: [GRAPHCAST], [GRAPHCAST-FIELDS], [FCN-CODE], [FCN2], [AICON-PAPER],
[AICON-FIELDS], [ICON-DOWNLOAD], [OM-WN2], [WN2], [OM-GFS], [OM-MAPPING],
[ICON-DOMAIN], [MF-DOMAIN], [OM-KNMI].

The ECMWF experimental-model page still describes running GraphCast/FourCastNet,
but its newer [50r1 change notice][IFS-CONTROL] says experimental Aurora,
FourCastNet, GraphCast and Pangu runs stop with that upgrade. Do not treat an
older experimental-feed page as current operational availability. Even an
alternative feed would not resolve the selected shortwave requirement here.

## 17. Remaining live-validation and engineering questions

These are validation questions, not a request to reopen the selected primary:

- Does a real, explicitly `icon_eu` request return all 24 requested UTC hours and
  all three selected variables/units at the six fixed coordinates? No sample was
  requested. Check strict coverage, missing/null/error forms and inclusivity.
- What actual native/regular cell, elevation and downscaling context is returned,
  including the announced post-November grid change? Keep original metadata and
  test parser compatibility without changing site coordinates.
- Which main/side cycles contribute to an actual latest-product snapshot, and
  is usable complete next-day coverage available before the chosen market cutoff?
  Resolve the importer 30 h/provider 51 h side-cycle difference empirically later.
- Does the response provide authoritative model/run/update metadata? If absent,
  keep source times null and use independent acquisition snapshots. Initialization,
  download completion and API availability must not be conflated.
- Are SR/native archives complete for the necessary historical fields/dates and
  actual cutoff policy? Mark hindcasts explicitly; validate grid/version changes,
  first/last lead and availability evidence before training data construction.
- Verify real provider errors, limits, response size/compression, revision/update
  behavior, applicable attribution and service access rights during separately
  authorized validation. Neither a paid subscription nor a commercial-use finding
  is implied by this report.
- Measure relevant six-site T/wind/GHI skill later with timestamp-aligned observed
  targets, seasonal/terrain strata and true availability cutoffs. Do not use global
  atmospheric scores or this subjective suitability total as empirical evidence
  of downstream electricity-price benefit.

Study change control: only the two requested new Markdown files were created.
Preservation hashes cover all 246 pre-existing tracked/untracked nonignored files.
No existing implementation, test, fixture, documentation history or index content
was changed. All seven weighted totals, point maxima, Markdown reference IDs and
local link targets were checked. `git diff --check`, new-document whitespace/EOF
checks and all applicable pre-commit hooks on the two new paths passed; Python,
YAML and TOML hooks correctly had no applicable files. Application tests need
not be rerun for this documentation-only decision, and previous test results are
not claimed as new executions. No branch, fetch/pull/rebase/reset/restore/stash,
staging, commit, push, credential use, provider data request or paid/cloud action.

## 18. Implementation contract for the next operator-reviewed task

This is a specification, **not authorization to implement or perform live I/O**.

| Contract field | Decision |
| --- | --- |
| Selected provider | Open-Meteo public Forecast API; upstream DWD |
| Primary model | **DWD ICON-EU deterministic European domain (~7 km)** |
| Exact model selector | **`models=icon_eu`**; canonical `model_id=icon_eu`; one value only. Do not use `best_match`, `icon_seamless`, `icon_global`, D2 or AICON |
| Endpoint | **`https://api.open-meteo.com/v1/forecast`** |
| Required hourly variables | **`temperature_2m,wind_speed_10m,shortwave_radiation`** only |
| Units | Request `temperature_unit=celsius`, `wind_speed_unit=ms`; validate returned **°C, m/s, W/m²**, without local conversion |
| UTC output | `timezone=GMT`, `timeformat=unixtime`; integer source timestamps |
| Window/horizon | One fixed site and one complete explicit UTC day, midnight to next midnight, using start_date=end_date for that requested day. Future intended next delivery-day use, ~12–48 h leads, within available horizon; no default seven-day payload. Do not equate UTC weather day with local-market-day coverage |
| Native temporal assumption | Main-cycle ICON-EU output is native hourly through 78 h, comfortably covering selected leads. Short cycles have conservative 30 h importer support until verified; latest API can combine editions of the same model. No local interpolation/filling/resampling; incomplete selected coverage fails |
| Six fixed sites | PT.lisbon (38.72, −9.14); PT.porto (41.15, −8.61); PT.braganca (41.81, −6.76); ES.madrid (40.42, −3.70); ES.zaragoza (41.65, −0.89); ES.seville (37.39, −5.98). Preserve existing selection version/coordinates |
| Normalized kind/support | `kind=forecast`; T2 at height 2 m and wind at height 10 m use `ValidInstant(t)`/instant; radiation uses positive half-open `[t−1h,t)`/mean, W/m² |
| Model/provenance | Separate forecast report/profile identity from historical ERA5. Pin `icon_eu` in canonical query and records; version forecast parser/catalogue explicitly. Reuse shared retriever/archive/replay. Retain requested site and returned grid/elevation, raw hash/reference, requested window, retrieval/parse events. Record known provider grid transition as profile context; never invent a cycle/run/issue time |
| Forecast vintage limitation | Current Forecast API is an acquisition snapshot of latest model output, not proof of a single run or historical cutoff. Source times remain null unless authoritative metadata is supplied. No HF/SR/Previous Runs ingestion or vintage reconstruction in the next Stage 5 scope unless separately authorized |
| Fallback | **ECMWF IFS HRES 9 km, `models=ecmwf_ifs`**, same three variables/units and distinct product identity. Document only; no automatic use, per-site switch or primary-field repair |
| Historical path | Existing explicit ERA5 Historical Weather API, `kind=reanalysis`, remains unchanged |
| Completion boundary | Later task implements/validates offline forecast integration after operator review; controlled live validation and Stage 6 remain separately authorized work |
