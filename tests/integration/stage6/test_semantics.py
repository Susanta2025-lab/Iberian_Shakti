"""Accepted source matrix and temporal/geographic/unit identity interoperability."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from iberian_shakti.contracts.geography import AreaRole, ExternalBoundary
from iberian_shakti.contracts.ingestion import IngestionResult
from iberian_shakti.contracts.market import MarketPrice
from iberian_shakti.contracts.measurements import (
    SourceTimes,
    Statistic,
    SupportInterval,
    SystemMeasurement,
    ValidInstant,
    ValueKind,
    WeatherMeasurement,
    WeatherVariable,
)
from iberian_shakti.contracts.queries import ApiSourceRequest
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.entsoe import profile as entsoe
from iberian_shakti.ingestion.ren import profile as ren
from iberian_shakti.ingestion.weather import profile as weather

from .support import DAY, cases_for, seed


@pytest.fixture(scope="module")
def integrated(tmp_path_factory):
    archive = LocalRawArchive(tmp_path_factory.mktemp("stage6_semantics"))
    return seed(archive, cases_for(all_sites=True))


MATRIX = (
    ("omie", MarketPrice, None, None, 200),
    ("ren", SystemMeasurement, ValueKind.ACTUAL, AreaRole.SYSTEM, 1100),
    ("esios", SystemMeasurement, ValueKind.FORECAST, AreaRole.SYSTEM, 3),
    ("entsoe_load", SystemMeasurement, ValueKind.ACTUAL, AreaRole.BIDDING_ZONE, 3),
    ("entsoe_pt", SystemMeasurement, ValueKind.FORECAST, AreaRole.BIDDING_ZONE, 8),
    ("entsoe_es", SystemMeasurement, ValueKind.FORECAST, AreaRole.BIDDING_ZONE, 12),
    *tuple(
        (f"{model}:{site.site_id}", WeatherMeasurement, kind, None, 72)
        for model, kind in (("era5", ValueKind.REANALYSIS), ("icon_eu", ValueKind.FORECAST))
        for site in weather.SITES
    ),
)


@pytest.mark.parametrize("key,record_type,kind,role,count", MATRIX)
def test_source_matrix_survives_shared_serialization(
    integrated, key, record_type, kind, role, count
):
    result = integrated[key]
    # The real closed normalized union validates each source without dropping
    # native fields; no generic row/coercion or semantic test substitute exists.
    roundtrip = IngestionResult.model_validate_json(result.model_dump_json())
    assert roundtrip == result
    records = roundtrip.parse.records
    assert len(records) == count and all(isinstance(r, record_type) for r in records)
    assert len({r.business_identity for r in records}) == count
    if record_type is MarketPrice:
        assert {r.market_area for r in records} == {"PT", "ES"}
        assert {(r.currency, r.price_unit, r.market) for r in records} == {
            ("EUR", "MWh", "day_ahead")
        }
        assert {r.duration_minutes for r in records} == {15}
        assert all(isinstance(r.price, Decimal) for r in records)
    else:
        assert {r.kind for r in records} == {kind}
        assert all(
            r.native.profile_version == result.parse.provenance.catalogue_version for r in records
        )
        if record_type is SystemMeasurement:
            assert {r.unit for r in records} == {"MW"}
            assert all(isinstance(r.value, Decimal) for r in records)
            assert all(
                (
                    r.geography.area if isinstance(r.geography, ExternalBoundary) else r.geography
                ).role
                is role
                for r in records
            )
            if key == "esios":
                assert {r.native.series_id for r in records} == {"544"}
                assert {r.cadence_seconds for r in records} == {300}
                assert all(
                    isinstance(r.timing, ValidInstant) and r.statistic is Statistic.INSTANT
                    for r in records
                )
            else:
                assert all(
                    isinstance(r.timing, SupportInterval)
                    and r.statistic is Statistic.PROVIDER_PERIOD_VALUE
                    for r in records
                )
            if key == "ren":
                assert {r.native.series_id for r in records} == set(ren.SELECTED)
                assert {r.cadence_seconds for r in records} == {900}
            if key.startswith("entsoe_") and key != "entsoe_load":
                expected = {"solar", "wind_onshore"} | (
                    {"wind_offshore"} if key == "entsoe_es" else set()
                )
                assert {r.measure.technology for r in records} == expected
        else:
            model, site = key.split(":", 1)
            assert {r.model_id for r in records} == {model}
            assert {r.site.site_id for r in records} == {site}
            assert {r.cadence_seconds for r in records} == {3600}
            assert {(r.variable, r.unit) for r in records} == {
                (WeatherVariable.TEMPERATURE, "°C"),
                (WeatherVariable.WIND_SPEED, "m/s"),
                (WeatherVariable.SHORTWAVE_RADIATION, "W/m²"),
            }
            assert all(
                (r.statistic is Statistic.MEAN and isinstance(r.timing, SupportInterval))
                if r.variable is WeatherVariable.SHORTWAVE_RADIATION
                else (r.statistic is Statistic.INSTANT and isinstance(r.timing, ValidInstant))
                for r in records
            )


def test_whole_collection_has_no_cross_source_business_collisions(integrated):
    records = tuple(r for result in integrated.values() for r in result.parse.records)
    assert len(records) == 2190
    assert len({r.business_identity for r in records}) == len(records)
    assert {r.kind for r in records if not isinstance(r, MarketPrice)} == set(ValueKind)
    assert {r.statistic for r in records if not isinstance(r, MarketPrice)} == {
        Statistic.INSTANT,
        Statistic.MEAN,
        Statistic.PROVIDER_PERIOD_VALUE,
    }
    assert {r.cadence_seconds for r in records if not isinstance(r, MarketPrice)} == {
        300,
        900,
        1800,
        3600,
    }


def test_same_country_never_establishes_geographic_equivalence(integrated):
    pt_system = integrated["ren"].parse.records[0].geography
    es_system = integrated["esios"].parse.records[0].geography
    pt_zone = integrated["entsoe_pt"].parse.records[0].geography
    es_zone = integrated["entsoe_load"].parse.records[0].geography
    assert pt_system.country_code == pt_zone.country_code == "PT"
    assert es_system.country_code == es_zone.country_code == "ES"
    assert pt_system != pt_zone and es_system != es_zone
    assert {pt_system.project_id, es_system.project_id, pt_zone.project_id, es_zone.project_id} == {
        "ren_portuguese_system",
        "ES.peninsular",
        "PT.entsoe_bidding_zone",
        "ES.entsoe_bidding_zone",
    }
    assert pt_system.perimeter == "provider_defined" and es_system.perimeter == "mainland"
    assert pt_zone.native_id == entsoe.DOMAINS["PT"] and es_zone.native_id == entsoe.DOMAINS["ES"]
    for country, system, zone in (("PT", pt_system, pt_zone), ("ES", es_system, es_zone)):
        market = next(r for r in integrated["omie"].parse.records if r.market_area == country)
        assert market.market_area not in {system.project_id, zone.project_id}
        assert (
            market.business_identity != integrated["entsoe_load"].parse.records[0].business_identity
        )
    boundaries = [
        r.geography for r in integrated["ren"].parse.records if r.measure.kind == "interchange"
    ]
    assert boundaries and all(
        isinstance(b, ExternalBoundary) and b.area == pt_system for b in boundaries
    )


def test_six_requested_points_and_returned_grids_are_distinct_geographies(integrated):
    for model in ("era5", "icon_eu"):
        sites = [integrated[f"{model}:{site.site_id}"].parse.records[0] for site in weather.SITES]
        assert len({r.site for r in sites}) == 6
        for record in sites:
            assert record.site != record.returned_grid
            assert record.site.requested != record.returned_grid.coordinates
            assert record.site.country_code != record.site.site_id
            assert record.site.selection_version == "0.1.0"
            assert record.returned_grid.elevation_m == 123.5
    # Synthetic fixtures intentionally reuse returned grids. Distinct logical
    # point selections must survive even when the provider cell is identical.
    lisbon = integrated["icon_eu:PT.lisbon"].parse.records[0]
    madrid = integrated["icon_eu:ES.madrid"].parse.records[0]
    assert lisbon.returned_grid == madrid.returned_grid
    assert lisbon.site != madrid.site and lisbon.business_identity != madrid.business_identity


@pytest.mark.parametrize(
    "key,updates",
    [
        ("ren", {"unit": "EUR/MWh"}),
        ("ren", {"unit": "W/m²"}),
        ("ren", {"unit": "MWh"}),
        ("esios", {"unit": "EUR/MWh"}),
        ("entsoe_load", {"unit": "W/m²"}),
        ("era5:PT.lisbon", {"unit": "MW"}),
        ("icon_eu:PT.lisbon", {"unit": "m/s"}),
        ("omie", {"price_unit": "MW"}),
    ],
)
def test_shared_normalization_rejects_cross_unit_confusion(integrated, key, updates):
    record = integrated[key].parse.records[0]
    with pytest.raises(ValidationError):
        type(record).model_validate({**record.model_dump(), **updates})


@pytest.mark.parametrize(
    "key,index,updates",
    [
        ("ren", 0, {"statistic": Statistic.INSTANT}),
        ("esios", 0, {"statistic": Statistic.PROVIDER_PERIOD_VALUE}),
        ("entsoe_load", 0, {"statistic": Statistic.INSTANT}),
        ("era5:PT.lisbon", 0, {"statistic": Statistic.MEAN}),
        ("icon_eu:PT.lisbon", 2, {"statistic": Statistic.INSTANT}),
        ("icon_eu:PT.lisbon", 2, {"statistic": Statistic.PROVIDER_PERIOD_VALUE}),
        ("icon_eu:PT.lisbon", 2, {"unit": "MW"}),
    ],
)
def test_statistics_require_their_native_support_and_unit(integrated, key, index, updates):
    record = integrated[key].parse.records[index]
    with pytest.raises(ValidationError):
        type(record).model_validate({**record.model_dump(), **updates})


def test_provider_period_power_is_not_an_asserted_mean(integrated):
    for key in ("ren", "entsoe_load", "entsoe_pt", "entsoe_es"):
        record = integrated[key].parse.records[0]
        assert record.statistic is Statistic.PROVIDER_PERIOD_VALUE
        asserted_mean = SystemMeasurement.model_validate(
            {**record.model_dump(), "statistic": Statistic.MEAN}
        )
        assert (
            asserted_mean != record and asserted_mean.business_identity != record.business_identity
        )
    assert integrated["esios"].parse.records[0].timing != integrated["ren"].parse.records[0].timing


def test_unknown_source_times_and_native_update_metadata_remain_separate(integrated):
    for key, result in integrated.items():
        if key == "omie":
            assert result.retrieval.source_published_at is None
            continue
        for r in result.parse.records:
            assert r.source_times.issue_time is None
            assert r.source_times.model_run_time is None
            assert r.source_times.published_at is None
            if key == "esios":
                assert r.source_times.updated_at == datetime(2026, 10, 25, 2, 10, tzinfo=UTC)
                assert r.source_times.updated_at != result.retrieval.completed_at
                assert r.source_times.updated_at != result.parse.provenance.parsed_at
            else:
                assert r.source_times == SourceTimes()
    load = integrated["entsoe_load"].parse.records[0]
    assert load.native.document_id == "synthetic-load-document"
    assert load.native.revision_id == "1"
    assert load.source_times.updated_at is None  # XML createdDateTime remains raw context.


@pytest.mark.parametrize("key", ["esios", "entsoe_pt", "entsoe_es", "icon_eu:PT.lisbon"])
def test_latest_forecast_cannot_establish_an_old_market_cutoff(integrated, key):
    result = integrated[key]
    old_cutoff = datetime(2026, 10, 23, 10, tzinfo=UTC)
    assert result.retrieval.completed_at > old_cutoff
    for record in result.parse.records:
        assert record.kind is ValueKind.FORECAST
        assert record.source_times.issue_time is record.source_times.model_run_time is None
        # The typed identity includes the independent acquisition when source
        # edition is unknown. A later identical snapshot cannot replace it.
        replacement = type(record).model_validate(
            {**record.model_dump(), "retrieval_event_id": result.parse.provenance.parse_event_id}
        )
        assert replacement.business_identity != record.business_identity


@pytest.mark.parametrize(
    "field",
    [
        "provider",
        "product",
        "profile",
        "area",
        "selection",
        "window",
        "model",
        "site",
        "site_version",
        "output_profile",
    ],
)
def test_material_api_query_changes_cannot_share_identity(field):
    cases = {c.key: c for c in cases_for()}
    request = cases[
        "icon_eu:PT.lisbon"
        if field in {"model", "site", "site_version", "output_profile"}
        else "esios"
    ].source.request
    data = json.loads(request.model_dump_json())
    if field == "provider":
        data["source_id"] = "another_provider"
    elif field in {"product", "profile"}:
        data["report_id"] = (
            "another_product.v0.1.0" if field == "product" else "indicator544.v0.2.0"
        )
    elif field == "area":
        data["query"]["area"]["project_id"] = "ES.other_system"
    elif field == "selection":
        data["query"]["series_ids"] = ["545"]
    elif field == "window":
        data["window"]["end_utc"] = "2026-10-25T04:00:00Z"
    elif field == "model":
        data["query"]["model_id"] = "era5"
    elif field == "site":
        data["query"]["site"]["site_id"] = "ES.madrid"
    elif field == "site_version":
        data["query"]["site"]["selection_version"] = "0.2.0"
    else:
        data["query"]["output"]["profile_version"] = "0.2.0"
    other = ApiSourceRequest.model_validate_json(json.dumps(data))
    assert other != request and other.query_identity != request.query_identity
    # Valid contract alternatives need not be supported by this pinned provider
    # profile. Canonical identity must still distinguish their request meaning.
    rebuilt = ApiSourceRequest.model_validate_json(
        json.dumps(json.loads(request.model_dump_json()), sort_keys=True)
    )
    assert rebuilt == request and rebuilt.query_identity == request.query_identity
    assert (
        request.query_identity
        == hashlib.sha256(
            json.dumps(
                json.loads(request.model_dump_json()), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )


def test_selected_products_domains_sites_and_legacy_request_identity_are_distinct():
    cases = cases_for(all_sites=True)
    assert len({c.source.safe_locator for c in cases}) == len(cases) == 18
    api = [c.source.request for c in cases if isinstance(c.source.request, ApiSourceRequest)]
    assert len({r.query_identity for r in api}) == len(api) == 17
    by_key = {c.key: c.source.request for c in cases}
    assert by_key["era5:PT.lisbon"].query_identity != by_key["icon_eu:PT.lisbon"].query_identity
    assert by_key["entsoe_pt"].query_identity != by_key["entsoe_es"].query_identity
    ren_data = json.loads(by_key["ren"].model_dump_json())
    ren_data["report_id"] = "ElectricityConsumptionSupplyDaily.en-US.v0.2.0"
    assert (
        ApiSourceRequest.model_validate_json(json.dumps(ren_data)).query_identity
        != by_key["ren"].query_identity
    )
    legacy = by_key["omie"]
    assert json.loads(legacy.model_dump_json()) == {
        "source_id": "omie",
        "report_id": "marginalpdbc",
        "delivery_date": "2026-10-25",
        "revision": 1,
        "selection_mode": "exact_revision",
    }


@pytest.mark.parametrize(
    "day,quarters,madrid_start,lisbon_start,madrid_end,lisbon_end",
    [
        (
            date(2026, 10, 24),
            96,
            "2026-10-23T22:00",
            "2026-10-23T23:00",
            "2026-10-24T22:00",
            "2026-10-24T23:00",
        ),
        (
            date(2026, 3, 29),
            92,
            "2026-03-28T23:00",
            "2026-03-29T00:00",
            "2026-03-29T22:00",
            "2026-03-29T23:00",
        ),
        (DAY, 100, "2026-10-24T22:00", "2026-10-24T23:00", "2026-10-25T23:00", "2026-10-26T00:00"),
    ],
)
def test_independent_calendars_coexist_at_dst_and_midnight(
    tmp_path, day, quarters, madrid_start, lisbon_start, madrid_end, lisbon_end
):
    results = seed(LocalRawArchive(tmp_path), cases_for(day))

    def utc(text):
        return datetime.fromisoformat(text).replace(tzinfo=UTC)

    market = results["omie"].parse.records
    pt_market = [r for r in market if r.market_area == "PT"]
    ren_load = [r for r in results["ren"].parse.records if r.measure.kind == "load"]
    assert len(market) == 2 * quarters and len(ren_load) == quarters
    assert pt_market[0].interval_start_utc == utc(madrid_start)
    assert pt_market[-1].interval_end_utc == utc(madrid_end)
    assert ren_load[0].timing.start_utc == utc(lisbon_start)
    assert ren_load[-1].timing.end_utc == utc(lisbon_end)
    assert pt_market[0].interval_start_utc != ren_load[0].timing.start_utc
    for earlier, later in pairwise(ren_load):
        assert earlier.timing.end_utc == later.timing.start_utc
    start = datetime.combine(day, datetime.min.time(), UTC)
    for key in ("entsoe_load", "entsoe_pt", "entsoe_es"):
        records = results[key].parse.records
        assert records[0].timing.start_utc == start
        for r in records:
            assert r.timing.end_utc - r.timing.start_utc == timedelta(seconds=r.cadence_seconds)
        assert len(records) == {"entsoe_load": 3, "entsoe_pt": 8, "entsoe_es": 12}[key]
    samples = results["esios"].parse.records
    assert [r.timing.at_utc for r in samples] == [
        start + timedelta(minutes=m) for m in (55, 60, 65)
    ]
    for model in ("era5", "icon_eu"):
        records = results[f"{model}:PT.lisbon"].parse.records
        assert len(records) == 72
        assert records[0].timing == ValidInstant(at_utc=start)
        assert records[2].timing == SupportInterval(
            start_utc=start - timedelta(hours=1), end_utc=start
        )
        assert records[2].timing.start_utc.date() == day - timedelta(days=1)
    for sequence, zone, hour in ((ren_load, "Europe/Lisbon", 1), (pt_market, "Europe/Madrid", 2)):
        at = [
            r.timing.start_utc if isinstance(r, SystemMeasurement) else r.interval_start_utc
            for r in sequence
        ]
        local = [t.astimezone(ZoneInfo(zone)) for t in at]
        assert local[0].hour == local[0].minute == 0
        if day == DAY:
            repeated = [t for t in local if t.hour == hour]
            assert len(repeated) == 8 and [t.fold for t in repeated] == [0] * 4 + [1] * 4
        elif day.month == 3:
            assert all(t.hour != hour for t in local)
