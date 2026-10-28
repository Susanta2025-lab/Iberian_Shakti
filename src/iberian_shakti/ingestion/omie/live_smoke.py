"""Explicitly opted-in OMIE live smoke command.

Importing this module performs no network or filesystem I/O.
Network-capable dependencies are constructed only after --live is present.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import (
    IngestionResult,
    ParseOutcome,
    ResolutionOutcome,
    ResolutionResult,
    RetrievalOutcome,
    SourceRequest,
)
from iberian_shakti.contracts.market import MarketPrice
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.config import (
    ConfigurationError,
    IngestionSettings,
    load_ingestion_settings,
)
from iberian_shakti.ingestion.errors import ArchiveError, ExecutionError
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.omie.adapter import OmieAdapter
from iberian_shakti.ingestion.omie.identity import (
    REPORT_ID,
    SOURCE_ID,
    download_url,
    listing_url,
)
from iberian_shakti.ingestion.retry import RetryPolicy
from iberian_shakti.ingestion.runner import ingest

EXIT_SUCCESS = 0
EXIT_NOT_AUTHORIZED = 2
EXIT_UNAVAILABLE = 3
EXIT_DISCOVERY = 4
EXIT_RETRIEVAL = 5
EXIT_CONTENT = 6
EXIT_ARCHIVE = 7
EXIT_CONFIGURATION = 8
EXIT_INTERNAL = 70


def _positive_revision(value: str) -> int:
    try:
        revision = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("revision must be a positive integer") from error
    if revision < 1 or str(revision) != value:
        raise argparse.ArgumentTypeError("revision must be a positive integer")
    return revision


def _delivery_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("delivery date must use YYYY-MM-DD") from error
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("delivery date must use YYYY-MM-DD")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m iberian_shakti.ingestion.omie.live_smoke",
        description="Explicit live OMIE marginalpdbc smoke validation.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly authorize the bounded live OMIE request.",
    )
    parser.add_argument(
        "--delivery-date",
        required=True,
        type=_delivery_date,
        help="OMIE delivery date in YYYY-MM-DD form.",
    )
    parser.add_argument(
        "--revision",
        type=_positive_revision,
        help="Exact positive revision. Omit for bounded latest-observed discovery.",
    )
    parser.add_argument(
        "--archive-root",
        required=True,
        type=Path,
        help="Local temporary archive root.",
    )
    return parser


def _safe_archive_root(path: Path) -> Path:
    root = path.expanduser().resolve(strict=False)
    fixture_root = Path("tests/data/omie").resolve(strict=False)

    if root == fixture_root or fixture_root in root.parents:
        raise ConfigurationError("Live smoke archive root must not be tests/data/omie")

    return root


def _settings(archive_root: Path) -> IngestionSettings:
    base = load_ingestion_settings()
    return IngestionSettings.model_validate(
        {
            **base.model_dump(),
            "raw_archive_root": archive_root,
        }
    )


def _print(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _resolution_failure(result: ResolutionResult) -> int:
    _print(
        {
            "delivery_date": result.request.delivery_date.isoformat(),
            "error_code": (result.error_code.value if result.error_code is not None else None),
            "outcome": result.outcome.value,
            "source": SOURCE_ID,
            "report": REPORT_ID,
            "verdict": "failed",
        }
    )

    if result.outcome is ResolutionOutcome.UNAVAILABLE:
        return EXIT_UNAVAILABLE

    return EXIT_DISCOVERY


def _retrieval_failure(result: IngestionResult) -> int:
    provenance = result.retrieval

    _print(
        {
            "attempt_count": provenance.attempt_count,
            "delivery_date": provenance.source.request.delivery_date.isoformat(),
            "error_code": (
                provenance.error_code.value if provenance.error_code is not None else None
            ),
            "http_status": provenance.http_status,
            "outcome": provenance.outcome.value,
            "source": SOURCE_ID,
            "report": REPORT_ID,
            "verdict": "failed",
        }
    )

    if provenance.outcome is RetrievalOutcome.UNAVAILABLE:
        return EXIT_UNAVAILABLE

    return EXIT_RETRIEVAL


def _successful_summary(result: IngestionResult) -> int:
    retrieval = result.retrieval
    parsed = result.parse

    if parsed is None:
        return _retrieval_failure(result)

    if parsed.provenance.outcome is not ParseOutcome.SUCCESS:
        _print(
            {
                "attempt_count": retrieval.attempt_count,
                "delivery_date": retrieval.source.request.delivery_date.isoformat(),
                "error_code": (
                    parsed.provenance.error_code.value
                    if parsed.provenance.error_code is not None
                    else None
                ),
                "filename": retrieval.source.filename,
                "http_status": retrieval.http_status,
                "outcome": parsed.provenance.outcome.value,
                "parser_id": parsed.provenance.parser_id,
                "parser_version": parsed.provenance.parser_version,
                "record_count": parsed.provenance.record_count,
                "source": SOURCE_ID,
                "report": REPORT_ID,
                "verdict": "failed",
            }
        )
        return EXIT_CONTENT

    # The shared record boundary now includes non-price families. OMIE still
    # requires exclusively MarketPrice; reject a wiring error, never drop records.
    records = tuple(record for record in parsed.records if isinstance(record, MarketPrice))
    if len(records) != len(parsed.records):
        _print({"error_code": "unexpected_record_family", "verdict": "failed"})
        return EXIT_CONTENT
    pt_records = tuple(record for record in records if record.market_area == "PT")
    es_records = tuple(record for record in records if record.market_area == "ES")
    period_indexes = {record.period_index for record in records}

    unexpected_areas = sorted({record.market_area for record in records} - {"PT", "ES"})
    if unexpected_areas:
        _print(
            {
                "error_code": "unexpected_market_area",
                "verdict": "failed",
            }
        )
        return EXIT_CONTENT

    raw = retrieval.raw
    archive = retrieval.archive
    assert raw is not None
    assert archive is not None

    starts = [record.interval_start_utc for record in records]
    ends = [record.interval_end_utc for record in records]

    _print(
        {
            "archive_reference": archive.relative_path,
            "attempt_count": retrieval.attempt_count,
            "byte_count": raw.byte_length,
            "delivery_date": retrieval.source.request.delivery_date.isoformat(),
            "es_record_count": len(es_records),
            "filename": retrieval.source.filename,
            "first_interval_start_utc": min(starts).isoformat(),
            "http_status": retrieval.http_status,
            "last_interval_end_utc": max(ends).isoformat(),
            "normalized_record_count": len(records),
            "observed_revision": retrieval.source.observed_revision,
            "parser_id": parsed.provenance.parser_id,
            "parser_version": parsed.provenance.parser_version,
            "pt_record_count": len(pt_records),
            "selection_mode": retrieval.source.request.selection_mode.value,
            "sha256": raw.sha256,
            "source": SOURCE_ID,
            "source_period_count": len(period_indexes),
            "report": REPORT_ID,
            "verdict": "pass",
        }
    )

    return EXIT_SUCCESS


def run(args: argparse.Namespace) -> int:
    # The authorization gate intentionally precedes all network-capable
    # dependency construction.
    if not args.live:
        _print(
            {
                "error_code": "live_authorization_required",
                "verdict": "not_run",
            }
        )
        return EXIT_NOT_AUTHORIZED

    try:
        archive_root = _safe_archive_root(args.archive_root)
        settings = _settings(archive_root)

        adapter = OmieAdapter()
        retriever = HttpRetriever(
            download_url,
            retrieval_event_id=uuid4(),
            classify_unavailable=adapter.classify_unavailable,
            resolve_listing_url=listing_url,
            policy=RetryPolicy.from_settings(settings),
        )
        archive = LocalRawArchive.from_settings(settings)

        request = SourceRequest(
            source_id=SOURCE_ID,
            report_id=REPORT_ID,
            delivery_date=args.delivery_date,
            revision=args.revision,
        )

        result = ingest(
            request,
            adapter=adapter,
            listing_retriever=retriever,
            retriever=retriever,
            archive=archive,
            parser=adapter.parser,
            parse_event_id=uuid4(),
        )

        if isinstance(result, ResolutionResult):
            return _resolution_failure(result)

        return _successful_summary(result)

    except ConfigurationError:
        _print(
            {
                "error_code": "invalid_configuration",
                "verdict": "failed",
            }
        )
        return EXIT_CONFIGURATION
    except ArchiveError as error:
        _print(
            {
                "error_code": error.code.value,
                "verdict": "failed",
            }
        )
        return EXIT_ARCHIVE
    except ExecutionError as error:
        _print(
            {
                "error_code": error.code.value,
                "verdict": "failed",
            }
        )
        return EXIT_RETRIEVAL
    except ValidationError:
        _print(
            {
                "error_code": "validation_failure",
                "verdict": "failed",
            }
        )
        return EXIT_CONFIGURATION
    except Exception:
        # Never expose raw provider/library exception text from the operator CLI.
        _print(
            {
                "error_code": "unexpected_internal_failure",
                "verdict": "failed",
            }
        )
        return EXIT_INTERNAL


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
