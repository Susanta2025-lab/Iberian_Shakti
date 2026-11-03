# Phase 2 Stage 2 — Independent REN / E-REDES timing experiment

Experiment date: **2026-10-29**, Europe/Lisbon. Evidence acquisition:
07:07:29–07:14:25 UTC. Timing-experiment verdict: **INCONCLUSIVE**.
Stage 2 remains **PASS WITH GAPS**. This is evidence only, outside Stage 8
controlled live validation and production acceptance.

The REN DST sequences exactly match independently generated Europe/Lisbon
calendars. Both proposed blackout thresholds reproduce by clock label. However,
the available E-REDES response encodes its clock labels with `+00:00`, its
metadata does not establish local-clock or interval-end support, and the fourth
candidate interval lacks a complete facility cohort. These failed prerequisites
prevent an unconditional physical alignment result. No data was repaired.

## A. Objective

- **H1:** REN `ElectricityProductionBreakdownDaily` uses Europe/Lisbon local
  civil-day clock labels.
- **H2:** REN HH:MM labels correspond to the START of their physical 15-minute
  period.
- **H3:** On DST transition days, ordered REN array positions correspond to
  successive physical Europe/Lisbon quarter-hour periods, including the repeated
  autumn hour.

Test mechanisms: independently acquired REN spring/autumn arrays and the
2025-04-28 blackout transition compared with bounded E-REDES substation energy
observations. MW statistic is a separate question; no assumption of mean MW is
made. Evidence labels: **D** official documentation, **O** direct observation,
**X** cross-source empirical evidence, **I** inference, **P** project policy,
**U** unresolved. Material conclusions below retain these distinctions.

## B. Baseline

**O — local Git:** initial commands were `git status --short` and
`git log --oneline --decorate -15`.

| Item | Observed baseline |
| --- | --- |
| Branch | Existing `main` |
| HEAD | `8a377ddcd6998f6d9e5aee90c11d71e431d83ce7` — feat: establish Phase 2 multi-source foundation |
| Locally recorded origin/main | `a4191a3c2e77896462f0b4c1f1066ebd8e84b782` — docs: close Phase 1 OMIE ingestion |
| Remote freshness | No fetch; not independently verified |
| Index | No staged changes |
| Working tree | Expected uncommitted Stage 2 work, preserved |
| Environment | Python 3.12.9, existing `iberian_shakti` environment |
| Stage 2 | PASS WITH GAPS; profile/parser 0.1.0; `time_semantics_unknown` |

Initial short status contained modified README, ADR/architecture/runbook indexes
and ingestion runbook; untracked ADR 0005, original Stage 2 prompt/report, five
REN implementation modules, REN fixtures/unit tests and integration test. Expanded
status accounts for **43 pre-existing changed/new Stage 2 files**.

Read the complete required assessment, Stage 1/2 reports, ADRs 0003–0005,
REN implementation/unit/integration files and fixture README, plus project
instructions and architecture references. The PortugueseOPD audit itself was
not found in the inspected local project material; the operator-supplied
classification C, unresolved MW status, candidate IDs and threshold assertion
were treated as hypotheses to reproduce, not acquired evidence.

The complete operator prompt was saved before provider requests at
[the new prompt](../prompts/phase_2/phase_2_stage_2_ren_eredes_time_semantics_experiment.md).
Historical prompts and the existing Stage 2 report were not edited.

## C. Request budget

**O — measured direct HTTP requests:**

| Provider / purpose | Logical requests | Physical attempts | Complete response bytes | Dates / windows |
| --- | ---: | ---: | ---: | --- |
| REN selected product | 3 | 3 | 85,123 | Exactly 2025-04-28, 2025-03-30, 2025-10-26 |
| E-REDES records/export | 10 | 10 | 254,489 | Queries described below, only blackout clock windows |
| E-REDES official catalogue/schema | 1 | 2 | 35,437 | Exact five IDs, limit 5; no data records |
| REN official chronology page | 1 | 1 | 87,743 | 2025-04-28 Update 3 |
| Total direct | **15** | **16** | **462,792** | No other direct requests |

Two search-engine discovery queries were also made in one web-tool invocation:
`site.e-redes.pt diagrama_carga_subestacao_01_a_07` and
`site:ren.pt 28 abril 2025 11h33 apagão`. They located the official portal and
chronology URL; no provider page was opened through the web tool. Budget these
as two additional metadata/research actions: **4 logical metadata/chronology/
discovery actions**, or **5 attempt units** including the failed catalogue
attempt. Counting the searches as two additional retrieval units gives **18
accounted units**, below 24. The web tool does not expose its backend HTTP
attempts; 16 is the exact independently logged provider HTTP count, not an
assertion about search-engine internal traffic. Search snippets are not used
as retained provider-body evidence; the conclusions use the direct acquisitions.

The first catalogue attempt failed inside the network sandbox with ConnectError,
zero response bytes and no HTTP status. The same identity succeeded once after
approved network escalation. No content/schema failure was retried. Every data
request and the chronology request succeeded on its first attempt.

E-REDES request plan and adaptation, **P/O**:

1. Five `/records` queries requested wire timestamps from 10:00Z through 11:00Z
   inclusive, projected identity/geography/time/energy fields, sorted by
   `datahora,codigo_subestacao`, limit 100, output timezone UTC. Including 10:00
   permits a preceding-value comparison. The 01–07 dataset reported 555 matches,
   returning its first 100; the other four returned zero matches.
2. One bounded `/exports/json` query on 01–07 requested the union of the wire-UTC
   window and candidate local-clock window: 10:00 through 12:00 wire timestamps,
   limit 1,000. It returned 894 rows, below the cap. Its first 100 equal the
   earlier page exactly; its first five clock positions contain all 555 matches
   reported for the initial window. This replaces a truncated observation for
   analysis without overwriting it. No pagination was used.
3. Four more `/records` queries checked the other datasets for the operator's
   candidate end labels 11:15, 11:30, 11:45 and 12:00. All returned zero matches.

The second group tests the explicit local-clock hypothesis; it does not declare
11:15Z–12:00Z to be the target physical window. The two candidate interpretations
are kept separate in §K. These five additional queries use the maximum ten
E-REDES data requests because of the initial truncation and unresolved clock
encoding. **Acquisition stopped at ten.** No further request, substitute dataset,
history expansion, rate probe or polling occurred.

**P — retrieval controls:** sequential GETs; at least 1.1 seconds between
successful deliberate acquisitions; verified TLS; `trust_env=False`; no
redirects; identity encoding; HTTPX transport retries zero; 10-second phase
timeouts and a 30-second cooperative streamed-attempt bound; 1 MiB original
body cap. No body reached its cap. Interrupted bodies cannot be published as
complete evidence. No authentication, credentials, proxy/user-agent override,
account action, write request or browser automation was used.

## D. Evidence inventory

All paths below are relative to the exact local evidence root:

```text
/tmp/iberian-shakti-ren-eredes-time-experiment/
```

Original bodies are unchanged `.bin` files. Every acquisition also has a
`.metadata.json` sidecar containing its exact safe GET identity, provider,
product/dataset, requested date/window, start/completion UTC, HTTP status,
attempt count, Content-Type, encoding, byte length, SHA-256 and absolute path.
`analysis/attempts.jsonl` preserves all sixteen attempts, including the failed
one. Sidecars count individual attempts; catalogue logical acquisition totals
two attempts. No real body is in Git.

| ID / provider / product | Acquisition UTC | HTTP / attempt | Content-Type | Bytes | SHA-256 | Local path under root |
| --- | --- | --- | --- | ---: | --- | --- |
| A01 / E-REDES / `bounded catalogue for five candidate substation datasets` | 2026-10-29T07:08:42.593550+00:00 | 200 / 1 | `application/json; charset=utf-8` | 35,437 | `f19a30ce8d8ec32de9fba1450556f676f95b97333c9fc1395d3bc5fd6b575f70` | `official_metadata/eredes-catalogue-attempt2.bin` |
| A02 / REN / `ElectricityProductionBreakdownDaily` | 2026-10-29T07:12:43.551977+00:00 | 200 / 1 | `text/plain; charset=UTF-8` | 27,901 | `a1e8b46998b4829e70da20423f5f11410335076de6a1c66de99625cc5d9b4aa0` | `ren/2025-04-28.bin` |
| A03 / REN / `ElectricityProductionBreakdownDaily` | 2026-10-29T07:12:45.117463+00:00 | 200 / 1 | `text/plain; charset=UTF-8` | 27,636 | `8f85882839bfc6649e76e44cb7db7508295738d2ec6c3f26c7a2ae1c9ad5ce6e` | `ren/2025-03-30.bin` |
| A04 / REN / `ElectricityProductionBreakdownDaily` | 2026-10-29T07:12:46.484565+00:00 | 200 / 1 | `text/plain; charset=UTF-8` | 29,586 | `b96725785e3a476626fa57d2f0b503940cbcd5f9bd472b84c9385b143ecfff34` | `ren/2025-10-26.bin` |
| A05 / E-REDES / `diagrama_carga_subestacao_01_a_07` | 2026-10-29T07:12:48.056768+00:00 | 200 / 1 | `application/json; charset=utf-8` | 25,636 | `bfcc98b67fdb1caff5291471037d0e388c30f97d413692fdd917866b84224886` | `eredes/diagrama_carga_subestacao_01_a_07.bin` |
| A06 / E-REDES / `diagrama_carga_subestacao_08_a_10` | 2026-10-29T07:12:49.416126+00:00 | 200 / 1 | `application/json; charset=utf-8` | 33 | `b40a5ce424590aa2d85084c9a423d90252d3ba8a22202193a62874533698a3a3` | `eredes/diagrama_carga_subestacao_08_a_10.bin` |
| A07 / E-REDES / `diagrama_carga_subestacao_11_a_12` | 2026-10-29T07:12:50.918303+00:00 | 200 / 1 | `application/json; charset=utf-8` | 33 | `b40a5ce424590aa2d85084c9a423d90252d3ba8a22202193a62874533698a3a3` | `eredes/diagrama_carga_subestacao_11_a_12.bin` |
| A08 / E-REDES / `diagrama_carga_subestacao_13_a_15` | 2026-10-29T07:12:52.429105+00:00 | 200 / 1 | `application/json; charset=utf-8` | 33 | `b40a5ce424590aa2d85084c9a423d90252d3ba8a22202193a62874533698a3a3` | `eredes/diagrama_carga_subestacao_13_a_15.bin` |
| A09 / E-REDES / `diagrama_carga_subestacao_16_a_18` | 2026-10-29T07:12:53.794340+00:00 | 200 / 1 | `application/json; charset=utf-8` | 33 | `b40a5ce424590aa2d85084c9a423d90252d3ba8a22202193a62874533698a3a3` | `eredes/diagrama_carga_subestacao_16_a_18.bin` |
| A10 / REN / `official news: power outage update 3` | 2026-10-29T07:12:55.146566+00:00 | 200 / 1 | `text/html; charset=utf-8` | 87,743 | `6b6bd14ddac0e9e876c8d58966c5403afbb152972a8d3ae9eca34f07277e5d1c` | `official_metadata/ren-blackout-update3.bin` |
| A11 / E-REDES / `diagrama_carga_subestacao_01_a_07` | 2026-10-29T07:14:19.951612+00:00 | 200 / 1 | `application/json; charset=utf-8` | 228,589 | `fff4960aefbad999c8dd934be423d2e277a34c9f8d3f187302643c12c19e5fed` | `eredes/diagrama_carga_subestacao_01_a_07-candidate-clock.bin` |
| A12 / E-REDES / `diagrama_carga_subestacao_08_a_10` | 2026-10-29T07:14:21.373928+00:00 | 200 / 1 | `application/json; charset=utf-8` | 33 | `b40a5ce424590aa2d85084c9a423d90252d3ba8a22202193a62874533698a3a3` | `eredes/diagrama_carga_subestacao_08_a_10-candidate-clock.bin` |
| A13 / E-REDES / `diagrama_carga_subestacao_11_a_12` | 2026-10-29T07:14:22.754592+00:00 | 200 / 1 | `application/json; charset=utf-8` | 33 | `b40a5ce424590aa2d85084c9a423d90252d3ba8a22202193a62874533698a3a3` | `eredes/diagrama_carga_subestacao_11_a_12-candidate-clock.bin` |
| A14 / E-REDES / `diagrama_carga_subestacao_13_a_15` | 2026-10-29T07:14:24.143582+00:00 | 200 / 1 | `application/json; charset=utf-8` | 33 | `b40a5ce424590aa2d85084c9a423d90252d3ba8a22202193a62874533698a3a3` | `eredes/diagrama_carga_subestacao_13_a_15-candidate-clock.bin` |
| A15 / E-REDES / `diagrama_carga_subestacao_16_a_18` | 2026-10-29T07:14:25.552852+00:00 | 200 / 1 | `application/json; charset=utf-8` | 33 | `b40a5ce424590aa2d85084c9a423d90252d3ba8a22202193a62874533698a3a3` | `eredes/diagrama_carga_subestacao_16_a_18-candidate-clock.bin` |

An initial catalogue failure has no body/hash: local failure metadata is
`official_metadata/eredes-catalogue.metadata.json`, acquired
2026-10-29T07:07:29.053517+00:00, zero bytes received, HTTP status absent,
ConnectError. The successful same-identity retry is inventoried above.

Exact safe requests are reproduced below; parameters retain their literal
values and URL encoding in the sidecars/ledger.

- **A01** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets?where=dataset_id+in+%28%22diagrama_carga_subestacao_01_a_07%22%2C%22diagrama_carga_subestacao_08_a_10%22%2C%22diagrama_carga_subestacao_11_a_12%22%2C%22diagrama_carga_subestacao_13_a_15%22%2C%22diagrama_carga_subestacao_16_a_18%22%29&limit=5&lang=pt`

  Requested scope: schema only; no records.

- **A02** — `GET https://servicebus.ren.pt/datahubapi/electricity/ElectricityProductionBreakdownDaily?culture=en-US&date=2025-04-28`

  Requested scope: 2025-04-28.

- **A03** — `GET https://servicebus.ren.pt/datahubapi/electricity/ElectricityProductionBreakdownDaily?culture=en-US&date=2025-03-30`

  Requested scope: 2025-03-30.

- **A04** — `GET https://servicebus.ren.pt/datahubapi/electricity/ElectricityProductionBreakdownDaily?culture=en-US&date=2025-10-26`

  Requested scope: 2025-10-26.

- **A05** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_01_a_07/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T10%3A00%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T11%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: 2025-04-28T10:00:00Z through 2025-04-28T11:00:00Z inclusive timestamp endpoints; candidate supports not asserted.

- **A06** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_08_a_10/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T10%3A00%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T11%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: 2025-04-28T10:00:00Z through 2025-04-28T11:00:00Z inclusive timestamp endpoints; candidate supports not asserted.

- **A07** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_11_a_12/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T10%3A00%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T11%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: 2025-04-28T10:00:00Z through 2025-04-28T11:00:00Z inclusive timestamp endpoints; candidate supports not asserted.

- **A08** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_13_a_15/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T10%3A00%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T11%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: 2025-04-28T10:00:00Z through 2025-04-28T11:00:00Z inclusive timestamp endpoints; candidate supports not asserted.

- **A09** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_16_a_18/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T10%3A00%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T11%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: 2025-04-28T10:00:00Z through 2025-04-28T11:00:00Z inclusive timestamp endpoints; candidate supports not asserted.

- **A10** — `GET https://www.ren.pt/en-gb/media/news/power-outage-across-the-iberian-peninsula-affects-portugal-upadate-3`

  Requested scope: 2025-04-28 chronology.

- **A11** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_01_a_07/exports/json?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T10%3A00%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T12%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=1000&timezone=UTC`

  Requested scope: Wire timestamp versus candidate Lisbon clock: bounded 10:00..12:00 wire timestamps for available cohort; 11:15..12:00 candidate end labels for four other datasets; no physical reinterpretation asserted.

- **A12** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_08_a_10/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T11%3A15%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T12%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: Wire timestamp versus candidate Lisbon clock: bounded 10:00..12:00 wire timestamps for available cohort; 11:15..12:00 candidate end labels for four other datasets; no physical reinterpretation asserted.

- **A13** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_11_a_12/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T11%3A15%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T12%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: Wire timestamp versus candidate Lisbon clock: bounded 10:00..12:00 wire timestamps for available cohort; 11:15..12:00 candidate end labels for four other datasets; no physical reinterpretation asserted.

- **A14** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_13_a_15/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T11%3A15%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T12%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: Wire timestamp versus candidate Lisbon clock: bounded 10:00..12:00 wire timestamps for available cohort; 11:15..12:00 candidate end labels for four other datasets; no physical reinterpretation asserted.

- **A15** — `GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/diagrama_carga_subestacao_16_a_18/records?select=codigo_subestacao%2Csubestacao%2Cdistrito%2Cconcelho%2Cfreguesia%2Cdatahora%2Cdata%2Chora%2Cenergia&where=datahora+%3E%3D+date%272025-04-28T11%3A15%3A00Z%27+AND+datahora+%3C%3D+date%272025-04-28T12%3A00%3A00Z%27&order_by=datahora%2Ccodigo_subestacao&limit=100&timezone=UTC`

  Requested scope: Wire timestamp versus candidate Lisbon clock: bounded 10:00..12:00 wire timestamps for available cohort; 11:15..12:00 candidate end labels for four other datasets; no physical reinterpretation asserted.

Derived-artifact integrity and reproduction are recorded in §S. The temporary
files are local evidence, not a durable archive or source fixture distribution.

## E. Official documentation / chronology

**D — current E-REDES catalogue:** all five exact IDs exist and expose
`datahora`, `data`, `hora`, `codigo_subestacao`, `subestacao`, geography fields
and `energia`. The field label supplies kWh. Descriptions call the records
hourly and describe a rolling one-year window; neither the field descriptions
nor the inspected metadata define interval-end timestamps, a 15-minute energy
support or Europe/Lisbon. Catalogue timezone is null and attachments are empty.
See the [official 01–07 dataset](https://e-redes.opendatasoft.com/explore/dataset/diagrama_carga_subestacao_01_a_07/)
and the retained catalogue body. **U:** null timezone metadata is absence of a
definition, not documentation of UTC or Lisbon.

**D — independent chronology:** REN's dated
[28 April 2025 Update 3](https://www.ren.pt/en-gb/media/news/power-outage-across-the-iberian-peninsula-affects-portugal-upadate-3)
states that the interruption affected Portugal from 11:33 that day. This
official, contemporaneous text is a minute-resolution anchor independent of
the chart arrays and E-REDES energy values. **I:** interpreting that Portuguese
mainland news time as local legal time, ZoneInfo Europe/Lisbon converts it to
2025-04-28 10:33Z, inside [10:30Z,10:45Z). The article does not explicitly print
UTC or an offset; that conversion is not a quotation of an official UTC field.
No broad event reconstruction or further chronology research was needed.

**U — REN API semantics:** this experiment acquired no new provider definition
of timezone, label placement, MW statistic or fold ownership. Prior Stage 2
documentation remains background; observed sequence compatibility below does
not become a new D declaration by REN.

## F. REN spring DST result

**O:** fresh 2025-03-30 response: **92 labels**, **15 series**, and **92 finite
values in every series**, including Consumption. Unit axis is MW; x-axis is
Hour. Source order starts 00:00, 00:15, 00:30, 00:45, 02:00, 02:15 and ends
23:45. Each of 01:00, 01:15, 01:30 and 01:45 is absent. There are no duplicate
labels or null Consumption values.

**O/I — deterministic comparison:** independently form local midnight and next
local midnight with `ZoneInfo("Europe/Lisbon")`, convert both boundaries to UTC,
step in physical 15-minute UTC increments, and convert each point back to Lisbon
for `%H:%M`. The generated window is [2025-03-30 00:00Z, 2025-03-30 23:00Z).
**Exact ordered equality passes for all 92 labels.** UTC and Europe/Madrid
candidate calendars do not match this source sequence on this date.

Selected Consumption values around the gap, **O**, zero-based indices:

| Source index | REN label | Consumption MW |
| ---: | --- | ---: |
| 2 | 00:30 | 4,911.2 |
| 3 | 00:45 | 4,797.6 |
| 4 | 02:00 | 4,690.3 |
| 5 | 02:15 | 4,637.7 |

**Conclusion O/I:** Europe/Lisbon-compatible clock sequence for this date;
no fixed-offset calendar or wall-clock timedelta stepping was used. A match
does not distinguish every timezone with the same civil-clock rules.

## G. REN autumn DST result

**O:** fresh 2025-10-26 response: **100 labels**, **15 series**, and **100 finite
values in every series**, including Consumption. Labels begin 00:00 and end
23:45. Each of 01:00, 01:15, 01:30 and 01:45 appears twice, consecutively as
two four-label blocks, before 02:00.

**O/I:** the independently generated Lisbon window is
[2025-10-25 23:00Z, 2025-10-27 00:00Z). **Exact ordered equality passes for all
100 labels.** UTC and Europe/Madrid candidate sequences do not match on this
date. Generated candidate associations are shown for comparison only:

| Source index | REN label | Consumption MW | Generated UTC candidate | Generated fold |
| ---: | --- | ---: | --- | ---: |
| 4 | 01:00 | 4,686.8 | 00:00Z | 0 |
| 5 | 01:15 | 4,602.5 | 00:15Z | 0 |
| 6 | 01:30 | 4,514.2 | 00:30Z | 0 |
| 7 | 01:45 | 4,446.2 | 00:45Z | 0 |
| 8 | 01:00 | 4,436.0 | 01:00Z | 1 |
| 9 | 01:15 | 4,360.1 | 01:15Z | 1 |
| 10 | 01:30 | 4,308.0 | 01:30Z | 1 |
| 11 | 01:45 | 4,306.5 | 01:45Z | 1 |

The source itself contains neither generated UTC nor fold fields.
**O/I conclusion:** calendar-compatible, with value-to-fold ownership unresolved
(§M). No values were deduplicated, moved or normalized.

## H. REN blackout-day result

**O:** fresh 2025-04-28 response: 96 ordered labels, 15 aligned arrays of 96
finite values, MW axis. Exact equality with the ordinary Lisbon candidate
calendar also passes. Ordinary-day clock shape alone does not identify timezone.

| Source index | REN label | Consumption MW | Change from preceding value |
| ---: | --- | ---: | ---: |
| 43 | 10:45 | 5,773.7 | −0.71535% |
| 44 | 11:00 | 5,816.1 | +0.73436% |
| 45 | 11:15 | 5,861.1 | +0.77371% |
| 46 | 11:30 | 1,414.1 | −75.87313% |
| 47 | 11:45 | 106.5 | −92.46871% |
| 48 | 12:00 | 104.7 | −1.69014% |

**O/I:** 1,414.1 / 5,861.1 = **0.2412687038269…**, below 0.30. The proposed REN
threshold reproduces. Its abrupt fall starts at chart label 11:30; calling that
a physical interval start is a tested interpretation, not an observed offset
or statistic. The independently anchored interruption at approximately 11:33
local lies within a quarter-hour beginning 11:30.

## I. E-REDES source definition

**D/O:** exact verified IDs, with no replacement:

| Dataset ID | Official district grouping | Blackout rows found in tested windows |
| --- | --- | --- |
| `diagrama_carga_subestacao_01_a_07` | Aveiro, Beja, Braga, Bragança, Castelo Branco, Coimbra, Évora | Yes |
| `diagrama_carga_subestacao_08_a_10` | Faro, Guarda, Leiria | None |
| `diagrama_carga_subestacao_11_a_12` | Lisboa, Portalegre | None |
| `diagrama_carga_subestacao_13_a_15` | Porto, Santarém, Setúbal | None |
| `diagrama_carga_subestacao_16_a_18` | Viana do Castelo, Vila Real, Viseu | None |

Only 01–07 contributes numerical observations. The four empty datasets are not
zero-load populations. Empty exact-window queries do not establish complete
historical absence or a retention rule for each dataset. The rolling-window
description plausibly explains some absence (**I**); old observations still
returned by 01–07 demonstrate that it is not a uniform empirical cutoff (**O**).

**D/O — fields and quantity:** `codigo_subestacao` is the facility identity;
`subestacao` and district/municipality/parish identify its name/geography.
`datahora` is a datetime field; `data` and `hora` supply separate date/clock
strings. `energia` is numeric energy, unit kWh from the official field label.
Original projected values and all nulls remain in the acquired bytes.

**O/U — timestamp issue:** for example, the returned record contains
`datahora=2025-04-28T11:45:00+00:00`, `data=2025-04-28`, `hora=11:45`.
Parsing the wire datetime literally gives 11:45Z, or 12:45 Lisbon. The operator's
candidate end label is instead 11:45 Lisbon, or 10:45Z. Neither changing the
output timezone nor observing the separate `hora` field establishes that the
wire offset is wrong. Reinterpreting the clock as Lisbon would require separate
evidence. No such correction is applied.

**O versus D:** rows before 12:00 are spaced 15 minutes apart, whereas the
current description calls records hourly. Cadence alone does not document
energy integration support, endpoint placement or timezone. No inspected
official field defines an interval ending at `datahora` or `hora`.

**P/U — aggregation policy:** sum raw kWh only when all 111 cohort facilities
have one finite non-null observation at that label. Preserve genuine zeros.
Do not fill absent records, replace nulls, interpolate, select a changing
intersection or exclude stations to get a result. A regional cohort is not
national REN Consumption and magnitudes need not match. **No derived E-REDES
mean MW is calculated:** kWh is documented, but the required quarter-hour
support is not. `kWh / 250` would be valid only if that support were established.
REN statistic is independently unresolved even if that support is later proved.

## J. E-REDES blackout observations

**O:** the export contains **894 distinct facility/time rows** and **111
distinct facility IDs**. All 111 occur at each of the eight labels 10:00 through
11:45; none has a null energy in those positions. At 12:00 only six facility
rows exist, three with null energy. No duplicate facility/time key occurs.

The fixed cohort is all 111 facility IDs observed at 11:15; it equals the sets
at every earlier label and at 11:30/11:45. All IDs and the explicit missing/null
lists are retained in `analysis/results.json`; no station is excluded from
aggregation. Sorting by ID is for deterministic comparison, not selection.

| Raw `hora` | Raw `datahora` time (+00:00) | Rows / cohort | Null energy | Raw aggregate kWh | Change from preceding aggregate |
| --- | --- | ---: | ---: | ---: | ---: |
| 10:00 | 10:00 | 111 / 111 | 0 | 241,627.5 | Not evaluated |
| 10:15 | 10:15 | 111 / 111 | 0 | 229,372.5 | −5.07186% |
| 10:30 | 10:30 | 111 / 111 | 0 | 226,552.5 | −1.22944% |
| 10:45 | 10:45 | 111 / 111 | 0 | 225,945.0 | −0.26815% |
| 11:00 | 11:00 | 111 / 111 | 0 | 222,302.5 | −1.61212% |
| 11:15 | 11:15 | 111 / 111 | 0 | 218,382.5 | −1.76336% |
| 11:30 | 11:30 | 111 / 111 | 0 | 218,290.0 | −0.04236% |
| 11:45 | 11:45 | 111 / 111 | 0 | 51,607.5 | −76.35828% |
| 12:00 | 12:00 | 6 / 111 | 3 | Unavailable | Unavailable |

**O/I:** 51,607.5 / 218,290.0 = **0.2364171514957…**, below 0.30. The E-REDES
clock-label threshold reproduces for the same complete 111-station cohort.
The preceding complete aggregates are stable relative to this drop.

**O/U:** 12:00 has 105 missing facility rows, three null energy rows and only
three finite energy rows. Its valid cohort aggregate is unavailable, not zero
and not the sum of the surviving rows. The null facility IDs are
`0201S5050500`, `0605S5005800`, `0609S5004700`; no mechanism for their missingness
is established. Four consecutive complete candidate local-end intervals cannot
be evaluated. This is an explicit failed prerequisite, not a repaired table.

## K. Cross-source physical alignment

**X/I — candidate local-clock/end interpretation only:** the following assigns
REN labels as local interval starts and E-REDES clock labels as local interval
ends. The physical interval column is generated independently with ZoneInfo.
Those E-REDES assignments do **not** follow its wire offsets and are not accepted
normalization. Changes use the preceding complete raw label; displayed percentages
are rounded only for this report, with Decimal ratios retained in results.

| Candidate physical interval UTC, 2025-04-28 | REN candidate local start | REN Consumption MW | REN change | E-REDES candidate local end | Raw E-REDES kWh | E-REDES change |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| [10:00,10:15) | 11:00 | 5,816.1 | +0.73436% | 11:15 | 218,382.5 | −1.76336% |
| [10:15,10:30) | 11:15 | 5,861.1 | +0.77371% | 11:30 | 218,290.0 | −0.04236% |
| [10:30,10:45) | 11:30 | 1,414.1 | −75.87313% | 11:45 | 51,607.5 | −76.35828% |
| [10:45,11:00) | 11:45 | 106.5 | −92.46871% | 12:00 | Unavailable: incomplete cohort/nulls | Unavailable |

**X/I:** the large first drop occurs in the same candidate interval
[10:30,10:45), containing the chronology anchor at approximately 10:33Z.
This reproduces the reported one-quarter-hour clock-label displacement without
reproducing an independently verified physical E-REDES interval.

**O/I — competing literal wire-UTC interpretation:** if E-REDES `datahora` were
an actual UTC interval end, the four requested intervals instead use the values
below. The interval-end assumption itself remains U; respecting the printed
offset does not establish it.

| Candidate physical interval UTC | Literal wire-UTC candidate end | Raw E-REDES kWh | Change |
| --- | --- | ---: | ---: |
| [10:00,10:15) | 10:15Z | 229,372.5 | −5.07186% |
| [10:15,10:30) | 10:30Z | 226,552.5 | −1.22944% |
| [10:30,10:45) | 10:45Z | 225,945.0 | −0.26815% |
| [10:45,11:00) | 11:00Z | 222,302.5 | −1.61212% |

**X/U:** under this interpretation there is no synchronized blackout drop in
the requested window. The observed E-REDES drop at 11:45Z would belong to
[11:30,11:45)Z, one hour later than the local-clock candidate. This discrepancy
cannot be removed by silently relabelling the timestamp. Neither comparison
calculates mean MW or equates the two provider perimeters.

**Physical alignment answer:** **conditional yes; independently established no**.
The threshold and qualitative discontinuity support the local-clock/end
candidate, but E-REDES timing/support metadata and fourth-period coverage fail
the experiment's prerequisites. No unconditional physical-interval assertions
are made for those raw observations.

## L. Competing label hypotheses

The judgments below separate conditional discrimination from an accepted
REN source contract. **X/I/U** apply, not a provider D definition.

| REN hypothesis | Under E-REDES local-clock/end candidate | Against chronology assuming faithful Lisbon labels | Overall assessment |
| --- | --- | --- | --- |
| H-start: label starts the physical 15-minute period | Consistent: REN 11:30 and E-REDES 11:45 describe [10:30,10:45)Z and both first drop below 30%. | Consistent: 11:33 local lies in [11:30,11:45). | Favored conditional placement; not independently established through E-REDES. |
| H-end: label ends the physical 15-minute period | Inconsistent with synchronized placement: REN 11:30 would describe [10:15,10:30)Z, one quarter earlier than the E-REDES candidate. | Inconsistent with a faithful period ending 11:30, before the stated 11:33 interruption. | Disfavored under those explicit assumptions; no sufficient E-REDES physical binding to make this a definitive product contract. |
| H-instant: label is the exact instantaneous/sample time | Cross-source interval energy alone cannot identify the REN statistic. | A literal sample at 11:30 local would precede the stated interruption; an already collapsed value at that exact instant is inconsistent with that anchor. | Literal exact-at-label sampling is disfavored. Samples assigned to a reporting bin or another chart statistic remain indistinguishable without a product definition. |

If E-REDES wire UTC is authoritative, none of the above establishes synchronized
cross-source collapse in the target window. A one-quarter-hour REN shift does
not resolve a one-hour E-REDES clock discrepancy.

**I/U:** start placement has useful empirical support, particularly against
end placement, but the incomplete/semantically unbound E-REDES control prevents
an unconditional H2 result. The chronology is a minute-resolution event anchor,
not a definition of how REN calculates a published point. An interval-associated
sample, mean or other statistic can share the same chart label and abrupt
change; this experiment does not classify the arithmetic statistic. Even if a
later decision accepts start placement, mean-versus-sampled MW remains separate.

## M. DST fold assessment

**O/I:** exact source label ordering equals the physical Lisbon calendar's
ordered labels on both transition dates. Spring has the correct gap and autumn
has two successive 01h blocks. This strongly supports clock-sequence compatibility.

**U:** label equality is invariant if the two autumn blocks' measurement values
are exchanged while their identical labels are retained. No offset-bearing REN
point, independently timestamped fold-day series or provider sequence contract
was acquired. Smooth Consumption through the repeat is not proof of fold
ownership. The generated fold columns in §G are hypotheses, not observed source
metadata. **Conclusion: calendar-compatible but fold ownership unresolved.**

## N. MW-statistic assessment

**UNRESOLVED**

**O:** REN labels a power axis MW and publishes finite values. **U:** no
product-specific evidence establishes instantaneous power, quarter-hour mean
power or another statistic. A period count, cadence, shape near a blackout or
agreement with E-REDES energy cannot independently establish that definition.
No REN MWh, mean MW, support interval or `SystemMeasurement` is constructed.

## O. Evidence classification

| Category | Established evidence / limit |
| --- | --- |
| D | Official current E-REDES IDs/schema/kWh metadata and REN's dated 11:33 blackout statement. No official REN timezone/start/mean/fold definition was found in this bounded experiment. |
| O | Fresh REN 92/100/96 arrays and values; E-REDES wire offsets/clock fields, complete 111-station pre-12:00 cohorts, energy drop, missing/null 12:00 rows, eight empty exact queries; hashes and request results. |
| X | One-quarter clock-label displacement of the large drops, conditionally coincident under REN local start and E-REDES local end; literal wire UTC does not align. |
| I | Independent ZoneInfo calendars, minute-anchor legal-time conversion, Decimal sums/ratios and conditional hypothesis comparisons. |
| P | Fixed cohort, no filling/repair/conversion, budget/transport controls, no implementation or Stage 2 acceptance change. |
| U | E-REDES physical clock binding/interval endpoint/integration support; fourth candidate interval coverage; REN timestamp statistic and autumn value-to-fold ownership. |

## P. Hypothesis verdicts

| Hypothesis / independent question | Required classification | Evidence-scoped answer |
| --- | --- | --- |
| H1 / timezone | **strong empirical evidence for Europe/Lisbon** | O/I: exact ordered equality on both fresh DST days, compatible ordinary day and local blackout chronology. Not a D definition or uniqueness among equivalent clock-rule zones. |
| H2 / label placement | **multiple interpretations remain plausible** | X/I/U: interval start is favored against end under explicit local-clock/end assumptions; exact-instant-at-label is disfavored by chronology, but interval-associated sampling/other statistics are not resolved. E-REDES UTC/support ambiguity prevents unconditional physical alignment. |
| H3 / DST ordering | **calendar-compatible but fold ownership unresolved** | O/I/U: exact ordered labels pass; value ownership of the indistinguishable repeated-label blocks does not follow. |
| MW statistic | **UNRESOLVED** | U: no product-specific statistic evidence. |

H1 has strong empirical support; H2 is only conditional support; H3's label
sequence is established while its physical value-to-fold component remains
unresolved. None becomes an authorized normalization profile in this task.

## Q. Stage-2 implication

**I/P:** this evidence is sufficient to inform a later explicit empirical-profile
review, particularly its timezone/clock candidate. It is **insufficient by
itself to justify adopting a complete physical interval/mean/fold profile**.
The E-REDES timing definition, missing fourth-period cohort and independent REN
statistic/fold questions remain material. Resolving them is separate authorized
work; no additional retrieval is performed after the E-REDES ceiling.

**P:** Stage 2 stays PASS WITH GAPS; ADR 0005, parser/profile 0.1.0 and
`time_semantics_unknown` are unchanged. No positive normalized records, profile
version bump, contract change, acceptance waiver, Stage 3 or Stage 8 authorization
is implied.

## R. Remaining gaps

- **U:** E-REDES's datetime offset versus the proposed Lisbon clock, and official
  quarter-hour integration/endpoint semantics. Empirical resemblance cannot
  authorize correcting a provider timestamp.
- **O/U:** four datasets supply no records in either exact tested window;
  the available 111-facility cohort becomes incomplete/null at candidate 12:00.
  No national aggregate or fourth complete local-end interval is available.
- **U:** REN MW statistic, precise label convention and autumn fold ownership;
  exact sequence compatibility is narrower than the full H3 claim.
- **U:** the chronology article provides local context without an explicit
  UTC offset. Its conversion remains an explicit inference.
- **U:** PortugueseOPD's original underlying files/query/cohort are unavailable;
  this independently reproduces its threshold assertion for one disclosed
  regional cohort, not its exact original aggregation.
- **P/U:** evidence is bounded to three REN dates and the queried E-REDES windows;
  no completeness, history, immutability, retention, future compatibility,
  commercial acceptance or generalized statistical reliability is established.

## S. Repository integrity

**P/O:** only the two operator-authorized Markdown additions belong to this
experiment:

```text
docs/codex/prompts/phase_2/phase_2_stage_2_ren_eredes_time_semantics_experiment.md
docs/codex/reports/phase_2_stage_2_ren_eredes_time_semantics_experiment.md
```

All temporary analysis code is under the specified evidence root, without
repository imports or provider requests during analysis. No implementation,
contracts, tests, fixtures, configuration, ADR or historical report changed.
The pre-experiment content snapshot covers 196 tracked/untracked project files;
its exact status and SHA-256 inventory are retained locally. Final comparison
must show all 196 byte-identical and exactly the two new Markdown paths.

Reproduction, **I/P**, using Python 3.12 and the retained original bytes:

```bash
python /tmp/iberian-shakti-ren-eredes-time-experiment/analysis/analyze.py
```

Acquisition specifications are `analysis/metadata-plan.json`,
`analysis/metadata-retry-plan.json`, `analysis/data-plan.json` and
`analysis/candidate-clock-plan.json`; `analysis/acquire.py` executes one JSON
plan sequentially. They are an audit trail, not authorization to repeat any
provider request beyond this completed experiment's budget.

Algorithm `offline-evidence-v1`: verify all acquired byte lengths/hashes; parse
numeric tokens directly to Decimal with duplicate JSON keys rejected; validate
REN series/counts/finite values and independent UTC-stepped Lisbon calendar;
validate E-REDES keys, timestamp parsing, clock consistency and units; compare
sets against all 111 facility IDs; sum only complete non-null cohorts; retain
missing/null IDs and mark invalid comparisons unavailable. Results include every
provider input hash, generated candidate calendar excerpts, Consumption-array
hashes, full cohort, missingness, ratios and conditional comparison rows.

The local Lisbon TZif SHA-256 used is
`92b07cb24689226bf934308d1f1bd33c306aa4da610c52cd5bce25077960502c`
(`/usr/share/zoneinfo/Europe/Lisbon`). No fixed offset is encoded in the algorithm.
All three exact calendar checks pass, as do raw integrity, finite non-null
numeric validation, timestamp consistency, unit identification, uniqueness,
initial-page/export equality and the two clock-label threshold checks. The
four-period complete cohort and documented physical clock/support prerequisites
explicitly fail; the analysis reports INCONCLUSIVE without repair or silent
assertion suppression.

| Derived artifact under root | Bytes | SHA-256 / inputs and method |
| --- | ---: | --- |
| `analysis/acquire.py` | 2,731 | `c34d24a98c620761a9bc4f35cb0449f56d4688b072c5dc8b41829649208150da` |
| `analysis/analyze.py` | 9,605 | `e6259ce52b9fe1d4547b9a9ceec697c1c8e0a6546c5e498d58bc653a913e7d8e` |
| `analysis/attempts.jsonl` | 21,718 | `abe5b6d3a3c3a66b537e0f48d1b9cf7e854273953da22de9f73fc04755bd8c6c` |
| `analysis/baseline-sha256.json` | 21,803 | `70579770ed6eb27d6dd285116f3dc380f0bf2a704e00ee897ddf159f17163911` |
| `analysis/baseline-status.txt` | 1,964 | `aec58c8fd808dca8403fc308b9030108e9f893521baa6c191f86f4dfb4307074` |
| `analysis/build_report_inventory.py` | 2,313 | `57863332b88e0e0f2815e51748115ff1d43367f9ece87a48e758bb668d7c4b91` |
| `analysis/candidate-clock-plan.json` | 4,234 | `8e2d223f31f15dde9e594acf6d45b2612d7116422d8ad56a41b133d875bc6c82` |
| `analysis/data-plan.json` | 5,066 | `218010f2c288bfeb721fc0f64ebe5e5eecf01b9a7479320a8c37c0e4d14788f8` |
| `analysis/metadata-plan.json` | 608 | `738e922866319ddf50348256944ed0d6cb2c6639a29aafa4b6fd49bb4d532dd8` |
| `analysis/metadata-retry-plan.json` | 617 | `4df2d05325b2d06f385d1ea6d41d1eadf2341147c259e62a94349d5e7f82a778` |
| `analysis/results.json` | 25,104 | `2b6a2e5336f90b579fb71ae3a7ffb64b17e939138fd8ca01c7318c9e83fb9dbe` |

Inputs: acquisition script → exact JSON request plans; analysis script → all
provider bodies listed in `results.json.input_sha256` and local TZif; ledger/
sidecars → acquisition observations; baseline inventory/status → local Git
tracked/untracked file contents; this inventory builder → ledger and local
analysis files. All scripts are versioned here by exact SHA-256 rather than
a repository commit. `results.json` is deterministic; reanalysis does not
acquire or overwrite any provider body.


Delivery verification, **O/P**:

| Check | Result |
| --- | --- |
| Deterministic offline analysis | Passed valid-input checks; explicitly reported the two failed physical-comparison prerequisites and INCONCLUSIVE. Repeated offline analysis reproduced the same 25,104-byte results hash. |
| Pre-existing project bytes | All 196 baseline files byte-identical; exactly two new Markdown files. |
| Applicable pre-commit hooks on the two new files | Trailing whitespace, EOF, large-file and private-key checks passed; Ruff/format/YAML/TOML skipped as inapplicable. No file mutation. |
| Whitespace review | `git diff --check` plus explicit no-index whitespace checks for both untracked additions passed. |
| Git review | Short/expanded status, tracked stat/diff, untracked additions and empty cached diff reviewed; main/HEAD/local origin unchanged. |

`analysis/final-integrity.json` records the preservation comparison and added
paths. `analysis/artifact-manifest.json` inventories the local evidence files,
sidecars, plans, scripts, outputs and their exact byte lengths/SHA-256 values;
it excludes itself to avoid recursive hashing. Raw input hashes remain explicit
in the acquisition inventory and deterministic results. A final offline audit
verifies that manifest and the report's provenance before delivery.

No source/test/configuration regression run is required for these documentation
additions. The inherited 1,281-test result is background, not a new test claim.
Final Git status retains the expected pre-existing Stage 2 changes plus these
two untracked files. The index remains unchanged. No staging, commit, push,
branch creation or cloud action was performed.

## T. Final experiment verdict

**INCONCLUSIVE**

**O/X/I/U:** DST clock-sequence compatibility and both proposed numerical
thresholds reproduce. Unresolved E-REDES physical-time/support semantics and
missing/null fourth-period records prevent the required validated four-interval
physical comparison. Per the operator's prerequisite rule, these failures take
precedence over the favorable partial empirical results. The result does not
contradict Lisbon-compatible REN labels, establish a mean-MW statistic or change
the Stage 2 verdict.

Phase 2 Stage 2 remains unchanged pending operator review.
No Stage 3 authorization is implied by this experiment.
