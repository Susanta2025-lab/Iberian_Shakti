"""Actual OMIE events use closed safe fields, never listing/row/URL data."""

import io
import json
import logging
from unittest.mock import Mock

import pytest

from iberian_shakti.common.logging import SafeJsonFormatter
from iberian_shakti.contracts.ingestion import ListingResult, RetrievalOutcome
from iberian_shakti.ingestion.omie.adapter import OmieAdapter


@pytest.mark.parametrize(
    "case", ["selected", "unknown", "schema", "parse_failure", "parse_success"]
)
def test_omie_event_context_stays_safe(case, caplog, omie_request, parse_report, fixture_root):
    with caplog.at_level(logging.INFO):
        if case.startswith("parse_"):
            content = (fixture_root / "marginalpdbc_20261026.1").read_bytes()
            if case == "parse_failure":
                content = content.replace(b"228.59", b"synthetic-secret", 1)
            parse_report(content)
        else:
            html = {
                "selected": (
                    b'<table><a href="/en/file-download?parents=marginalpdbc'
                    b'&amp;filename=marginalpdbc_20261026.2">synthetic-secret</a></table>'
                ),
                "unknown": (
                    b'<table><a href="/en/file-download?parents=marginalpdbc'
                    b'&amp;filename=marginalpdbc_20200101.2">synthetic-secret</a></table>'
                ),
                "schema": b"<html>synthetic-secret</html>",
            }[case]
            OmieAdapter().resolve(
                omie_request,
                Mock(
                    retrieve_listing=Mock(
                        return_value=ListingResult(
                            outcome=RetrievalOutcome.RETRIEVED,
                            attempt_count=1,
                            http_status=200,
                            content=html,
                        )
                    )
                ),
            )
    stream = io.StringIO()
    formatter = SafeJsonFormatter()
    events = []
    for record in caplog.records:
        if record.name.startswith("iberian_shakti.ingestion.omie"):
            message = formatter.format(record)
            stream.write(message)
            events.append(json.loads(message))
    assert events
    assert "synthetic-secret" not in stream.getvalue()
    assert "file-download?" not in stream.getvalue() and "MARGINALPDBC;" not in stream.getvalue()
    assert all(event["event"] != "unstructured_event" for event in events)
    assert all(event["source"] == "omie" and event["report"] == "marginalpdbc" for event in events)
    assert (
        events[-1]["outcome"]
        == {
            "selected": "resolved",
            "unknown": "coverage_unknown",
            "schema": "failure",
            "parse_failure": "content_failure",
            "parse_success": "success",
        }[case]
    )
