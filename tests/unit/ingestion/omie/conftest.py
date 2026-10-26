"""Stage 4 local fixtures; parent network denial remains scoped to ingestion units."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import SourceRequest
from iberian_shakti.ingestion.omie.identity import resolved_source
from iberian_shakti.ingestion.omie.parser import OmieParser
from iberian_shakti.ingestion.retrieval import result_for

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "omie"
NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)


@pytest.fixture
def fixture_root():
    return FIXTURES


@pytest.fixture
def manifest():
    return json.loads((FIXTURES / "manifest.json").read_text())["fixtures"]


@pytest.fixture
def omie_request():
    return SourceRequest(
        source_id="omie", report_id="marginalpdbc", delivery_date=date(2026, 10, 26)
    )


@pytest.fixture
def parse_report():
    def parse(content, day=date(2026, 10, 26), revision=1, **kwargs):
        request = SourceRequest(
            source_id="omie", report_id="marginalpdbc", delivery_date=day, revision=revision
        )
        acquired = result_for(
            resolved_source(request, revision), UUID(int=301), NOW, content=content
        )
        return OmieParser().parse(
            acquired.payload,
            acquired.provenance,
            parsed_at=NOW,
            parse_event_id=UUID(int=302),
            **kwargs,
        )

    return parse
