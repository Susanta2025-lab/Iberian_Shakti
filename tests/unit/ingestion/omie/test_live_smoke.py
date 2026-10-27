from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ListingResult,
    RawContentReference,
    RawPayload,
    ResolvedSource,
    RetrievalOutcome,
    RetrievalProvenance,
    RetrievalResult,
)
from iberian_shakti.ingestion.omie import live_smoke


class _OfflineRetriever:
    def __init__(
        self,
        *,
        event_id: UUID,
        report_bytes: bytes,
        listing_bytes: bytes | None = None,
        unavailable: bool = False,
    ) -> None:
        self.event_id = event_id
        self.report_bytes = report_bytes
        self.listing_bytes = listing_bytes
        self.unavailable = unavailable
        self.listing_calls = 0
        self.report_calls = 0

    def retrieve_listing(self, request: Any) -> ListingResult:
        del request
        self.listing_calls += 1
        assert self.listing_bytes is not None
        return ListingResult(
            outcome=RetrievalOutcome.RETRIEVED,
            attempt_count=1,
            content=self.listing_bytes,
            http_status=200,
        )

    def retrieve(self, source: ResolvedSource) -> RetrievalResult:
        self.report_calls += 1

        if self.unavailable:
            provenance = RetrievalProvenance(
                source=source,
                completed_at=datetime.now(UTC),
                retrieval_event_id=self.event_id,
                outcome=RetrievalOutcome.UNAVAILABLE,
                attempt_count=1,
                http_status=404,
                error_code=ErrorCode.NOT_FOUND,
            )
            return RetrievalResult(provenance=provenance)

        raw = RawContentReference(
            source_id=source.request.source_id,
            report_id=source.request.report_id,
            delivery_date=source.request.delivery_date,
            sha256=hashlib.sha256(self.report_bytes).hexdigest(),
            byte_length=len(self.report_bytes),
        )
        payload = RawPayload(reference=raw, content=self.report_bytes)
        provenance = RetrievalProvenance(
            source=source,
            completed_at=datetime.now(UTC),
            retrieval_event_id=self.event_id,
            outcome=RetrievalOutcome.RETRIEVED,
            attempt_count=1,
            http_status=200,
            raw=raw,
        )
        return RetrievalResult(provenance=provenance, payload=payload)


def _report_bytes() -> bytes:
    return Path("tests/data/omie/marginalpdbc_20261026.1").read_bytes()


def _listing_bytes() -> bytes:
    return (
        b"<html><body><table><tr><td>"
        b'<a href="https://www.omie.es/en/file-download?'
        b'parents=marginalpdbc&amp;filename=marginalpdbc_20261026.1">'
        b"report"
        b"</a></td></tr></table></body></html>"
    )


def _install_retriever(
    monkeypatch: pytest.MonkeyPatch,
    *,
    report_bytes: bytes,
    listing_bytes: bytes | None = None,
    unavailable: bool = False,
) -> dict[str, _OfflineRetriever]:
    holder: dict[str, _OfflineRetriever] = {}

    def factory(
        _resolve_url: Any,
        *,
        retrieval_event_id: UUID,
        **_kwargs: Any,
    ) -> _OfflineRetriever:
        retriever = _OfflineRetriever(
            event_id=retrieval_event_id,
            report_bytes=report_bytes,
            listing_bytes=listing_bytes,
            unavailable=unavailable,
        )
        holder["retriever"] = retriever
        return retriever

    monkeypatch.setattr(live_smoke, "HttpRetriever", factory)
    return holder


def test_without_live_refuses_before_network(monkeypatch, capsys):
    def forbidden_retriever(*args, **kwargs):
        raise AssertionError("HttpRetriever must not be constructed without --live")

    monkeypatch.setattr(live_smoke, "HttpRetriever", forbidden_retriever)

    result = live_smoke.main(
        [
            "--delivery-date",
            "2026-10-26",
            "--revision",
            "1",
            "--archive-root",
            "/tmp/iberian-shakti-omie-smoke",
        ]
    )

    assert result == live_smoke.EXIT_NOT_AUTHORIZED

    output = json.loads(capsys.readouterr().out)
    assert output == {
        "error_code": "live_authorization_required",
        "verdict": "not_run",
    }


def test_fixture_directory_cannot_be_live_archive(monkeypatch, capsys):
    def forbidden_retriever(*args, **kwargs):
        raise AssertionError("HttpRetriever must not be constructed")

    monkeypatch.setattr(live_smoke, "HttpRetriever", forbidden_retriever)

    result = live_smoke.main(
        [
            "--live",
            "--delivery-date",
            "2026-10-26",
            "--revision",
            "1",
            "--archive-root",
            "tests/data/omie",
        ]
    )

    assert result == live_smoke.EXIT_CONFIGURATION

    output = json.loads(capsys.readouterr().out)
    assert output == {
        "error_code": "invalid_configuration",
        "verdict": "failed",
    }


@pytest.mark.parametrize(
    "revision",
    [
        "0",
        "-1",
        "01",
        "abc",
    ],
)
def test_invalid_revision_is_rejected(revision):
    with pytest.raises(SystemExit) as error:
        live_smoke.main(
            [
                "--delivery-date",
                "2026-10-26",
                "--revision",
                revision,
                "--archive-root",
                "/tmp/iberian-shakti-omie-smoke",
            ]
        )

    assert error.value.code == 2


@pytest.mark.parametrize(
    "delivery_date",
    [
        "2026-10-32",
        "26-10-2026",
        "2026/10/26",
    ],
)
def test_invalid_delivery_date_is_rejected(delivery_date):
    with pytest.raises(SystemExit) as error:
        live_smoke.main(
            [
                "--delivery-date",
                delivery_date,
                "--archive-root",
                "/tmp/iberian-shakti-omie-smoke",
            ]
        )

    assert error.value.code == 2


def test_safe_temporary_archive_root():
    root = live_smoke._safe_archive_root(Path("/tmp/iberian-shakti-omie-smoke"))

    assert root == Path("/tmp/iberian-shakti-omie-smoke")


def test_exact_live_wiring_offline(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    report = _report_bytes()
    holder = _install_retriever(monkeypatch, report_bytes=report)

    result = live_smoke.main(
        [
            "--live",
            "--delivery-date",
            "2026-10-26",
            "--revision",
            "1",
            "--archive-root",
            str(tmp_path),
        ]
    )

    assert result == live_smoke.EXIT_SUCCESS

    output = json.loads(capsys.readouterr().out)
    assert output["verdict"] == "pass"
    assert output["selection_mode"] == "exact_revision"
    assert output["observed_revision"] == 1
    assert output["source_period_count"] == 96
    assert output["normalized_record_count"] == 192
    assert output["pt_record_count"] == 96
    assert output["es_record_count"] == 96
    assert output["sha256"] == hashlib.sha256(report).hexdigest()

    retriever = holder["retriever"]
    assert retriever.listing_calls == 0
    assert retriever.report_calls == 1

    archived = tmp_path / output["archive_reference"]
    assert archived.read_bytes() == report


def test_latest_observed_live_wiring_offline(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    holder = _install_retriever(
        monkeypatch,
        report_bytes=_report_bytes(),
        listing_bytes=_listing_bytes(),
    )

    result = live_smoke.main(
        [
            "--live",
            "--delivery-date",
            "2026-10-26",
            "--archive-root",
            str(tmp_path),
        ]
    )

    assert result == live_smoke.EXIT_SUCCESS

    output = json.loads(capsys.readouterr().out)
    assert output["verdict"] == "pass"
    assert output["selection_mode"] == "latest_observed"
    assert output["observed_revision"] == 1
    assert output["normalized_record_count"] == 192

    retriever = holder["retriever"]
    assert retriever.listing_calls == 1
    assert retriever.report_calls == 1


def test_unavailable_report_returns_unavailable_exit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    holder = _install_retriever(
        monkeypatch,
        report_bytes=_report_bytes(),
        unavailable=True,
    )

    result = live_smoke.main(
        [
            "--live",
            "--delivery-date",
            "2026-10-26",
            "--revision",
            "1",
            "--archive-root",
            str(tmp_path),
        ]
    )

    assert result == live_smoke.EXIT_UNAVAILABLE

    output = json.loads(capsys.readouterr().out)
    assert output["verdict"] == "failed"
    assert output["outcome"] == "unavailable"
    assert output["error_code"] == "not_found"

    retriever = holder["retriever"]
    assert retriever.listing_calls == 0
    assert retriever.report_calls == 1


def test_malformed_complete_report_is_archived_but_parse_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    valid = _report_bytes()
    marker = valid.rfind(b"*")
    assert marker >= 0
    malformed = valid[:marker] + valid[marker + 1 :]

    _install_retriever(monkeypatch, report_bytes=malformed)

    result = live_smoke.main(
        [
            "--live",
            "--delivery-date",
            "2026-10-26",
            "--revision",
            "1",
            "--archive-root",
            str(tmp_path),
        ]
    )

    assert result == live_smoke.EXIT_CONTENT

    output = json.loads(capsys.readouterr().out)
    assert output["verdict"] == "failed"
    assert output["outcome"] == "content_failure"
    assert output["record_count"] == 0
    assert output["error_code"] == "content_invalid"

    archived_payloads = list(tmp_path.glob("**/payload.bin"))
    assert len(archived_payloads) == 1
    assert archived_payloads[0].read_bytes() == malformed


def test_invalid_discovery_listing_stops_before_report_retrieval(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    holder = _install_retriever(
        monkeypatch,
        report_bytes=_report_bytes(),
        listing_bytes=b"<html><body>not a report table</body></html>",
    )

    result = live_smoke.main(
        [
            "--live",
            "--delivery-date",
            "2026-10-26",
            "--archive-root",
            str(tmp_path),
        ]
    )

    assert result == live_smoke.EXIT_DISCOVERY

    output = json.loads(capsys.readouterr().out)
    assert output["verdict"] == "failed"
    assert output["outcome"] == "failure"
    assert output["error_code"] == "discovery_schema"

    retriever = holder["retriever"]
    assert retriever.listing_calls == 1
    assert retriever.report_calls == 0


def test_unexpected_internal_error_does_not_expose_exception_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def exploding_retriever(*args: Any, **kwargs: Any) -> None:
        del args, kwargs
        raise RuntimeError("secret-token-must-not-appear")

    monkeypatch.setattr(live_smoke, "HttpRetriever", exploding_retriever)

    result = live_smoke.main(
        [
            "--live",
            "--delivery-date",
            "2026-10-26",
            "--revision",
            "1",
            "--archive-root",
            str(tmp_path),
        ]
    )

    assert result == live_smoke.EXIT_INTERNAL

    raw_output = capsys.readouterr().out
    assert "secret-token-must-not-appear" not in raw_output

    output = json.loads(raw_output)
    assert output == {
        "error_code": "unexpected_internal_failure",
        "verdict": "failed",
    }
