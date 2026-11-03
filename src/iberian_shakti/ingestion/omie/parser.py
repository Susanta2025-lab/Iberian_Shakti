"""Strict, complete-report MARGINALPDBC parser. No I/O or partial success."""

import logging
import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ParseOutcome,
    ParseProvenance,
    ParseResult,
    RawPayload,
    RetrievalOutcome,
    RetrievalProvenance,
)
from iberian_shakti.contracts.market import MarketPrice
from iberian_shakti.ingestion.errors import ExecutionError
from iberian_shakti.ingestion.omie.calendar import intervals_for
from iberian_shakti.ingestion.omie.identity import (
    MARKET,
    PARSER_ID,
    PARSER_VERSION,
    validate_resolved,
)
from iberian_shakti.ingestion.retrieval import (
    DEFAULT_MAX_BYTES,
    require_identity_encoding,
    source_context,
)

HEADER = "MARGINALPDBC;"
# Bounded field widths follow the selected numeric layout, not generic CSV guessing.
ROW = re.compile(
    r"([0-9]{4});([0-9]{1,2});([0-9]{1,2});([1-9][0-9]{0,2});"
    r"([+-]?[0-9]+(?:\.[0-9]{1,2})?);([+-]?[0-9]+(?:\.[0-9]{1,2})?);",
    re.ASCII,
)
logger = logging.getLogger(__name__)


class OmieParser:
    parser_id = PARSER_ID
    parser_version = PARSER_VERSION

    def parse(
        self,
        payload: RawPayload,
        retrieval: RetrievalProvenance,
        *,
        parsed_at: datetime,
        parse_event_id: UUID,
    ) -> ParseResult:
        context = {**source_context(retrieval.source), "parser_version": self.parser_version}
        logger.info("omie_parse_started", extra=context)
        code = None
        records: tuple[MarketPrice, ...] = ()
        # Caller/linkage errors cannot masquerade as a different successfully acquired report.
        if (
            retrieval.outcome is not RetrievalOutcome.RETRIEVED
            or retrieval.raw != payload.reference
        ):
            code = ErrorCode.INTEGRITY_FAILURE
        elif len(payload.content) > DEFAULT_MAX_BYTES:
            # Direct parsing and replay must retain the same work bound as
            # acquisition, even for objects produced by a different retriever.
            code = ErrorCode.CONTENT_INVALID
        else:
            try:
                RawPayload(reference=payload.reference, content=payload.content)
            except ValidationError:
                code = ErrorCode.INTEGRITY_FAILURE
        if code is None:
            try:
                validate_resolved(retrieval.source)
                require_identity_encoding(retrieval)
            except ExecutionError as error:
                code = (
                    ErrorCode.UNSUPPORTED_ENCODING
                    if error.code is ErrorCode.UNSUPPORTED_ENCODING
                    else ErrorCode.CONTENT_INVALID
                )
        if code is None:
            try:
                text = payload.content.decode("ascii", errors="strict")
            except UnicodeDecodeError:
                code = ErrorCode.UNSUPPORTED_ENCODING
            else:
                # ASCII-compatible BOMs (UTF-7) are not a supported report header either.
                if text.startswith("+/v"):
                    code = ErrorCode.UNSUPPORTED_ENCODING
                else:
                    try:
                        records = self._records(text, payload, parse_event_id)
                    except ValueError:
                        code = ErrorCode.CONTENT_INVALID
        outcome = ParseOutcome.SUCCESS if code is None else ParseOutcome.CONTENT_FAILURE
        provenance = ParseProvenance(
            retrieval_event_id=retrieval.retrieval_event_id,
            raw=payload.reference,
            archive=retrieval.archive,
            parser_id=self.parser_id,
            parser_version=self.parser_version,
            parsed_at=parsed_at,
            parse_event_id=parse_event_id,
            outcome=outcome,
            error_code=code,
            record_count=len(records),
        )
        logger.info(
            "parse_completed" if code is None else "validation_failed",
            extra={
                **context,
                "outcome": outcome.value,
                "record_count": len(records),
                **({"error_code": code.value} if code else {}),
            },
        )
        return ParseResult(provenance=provenance, records=records)

    @staticmethod
    def _records(text: str, payload: RawPayload, event_id: UUID) -> tuple[MarketPrice, ...]:
        # Accept LF and CRLF only. Remove at most one final line ending.
        text = text.replace("\r\n", "\n")
        if "\r" in text:
            raise ValueError("line_ending")
        if text.endswith("\n"):
            text = text[:-1]
        lines = text.split("\n")
        raw = payload.reference
        intervals = intervals_for(raw.delivery_date)
        if len(lines) != len(intervals) + 2 or lines[0] != HEADER or lines[-1] != "*":
            raise ValueError("report_structure")
        prices: list[tuple[Decimal, Decimal]] = []
        for index, row in enumerate(lines[1:-1], start=1):
            match = ROW.fullmatch(row)
            if match is None:
                raise ValueError("row_grammar")
            year, month, day, period, pt, es = match.groups()
            if date(int(year), int(month), int(day)) != raw.delivery_date or int(period) != index:
                raise ValueError("date_or_period")
            prices.append((Decimal(pt), Decimal(es)))
        # All source rows have passed before constructing any normalized record.
        return tuple(
            MarketPrice(
                **interval.model_dump(),
                source_id=raw.source_id,
                report_id=raw.report_id,
                market=MARKET,
                market_area=area,
                delivery_date=raw.delivery_date,
                price=price,
                currency="EUR",
                price_unit="MWh",
                parse_event_id=event_id,
            )
            for interval, pair in zip(intervals, prices, strict=True)
            for area, price in zip(("PT", "ES"), pair, strict=True)
        )
