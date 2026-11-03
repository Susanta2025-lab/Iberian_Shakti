"""Fixed-origin ENTSO-E acquisition via the shared private transport boundary."""

import time
from collections.abc import Callable, Mapping
from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

import httpx

from iberian_shakti.contracts.ingestion import ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest
from iberian_shakti.ingestion.auth import PrivateRequestPolicy
from iberian_shakti.ingestion.config import load_provider_auth
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.entsoe.identity import validate_resolved
from iberian_shakti.ingestion.entsoe.parser import EntsoeParser
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.retrieval import utc_now


class EntsoeAdapter:
    parser = EntsoeParser()

    @staticmethod
    def resolve(request: ApiSourceRequest) -> ResolvedSource:
        source = ResolvedSource.for_api(request)
        validate_resolved(source)
        return source

    @staticmethod
    def transport_url(source: ResolvedSource) -> str:
        selected = validate_resolved(source)
        assert isinstance(source.request, ApiSourceRequest)
        window = source.request.window
        parameters = urlencode(
            {
                "documentType": selected.document_type,
                "processType": selected.process_type,
                selected.domain_parameter: selected.area.native_id,
                "periodStart": window.start_utc.strftime("%Y%m%d%H%M"),
                "periodEnd": window.end_utc.strftime("%Y%m%d%H%M"),
            }
        )
        return f"{profile.ORIGIN}{profile.ENDPOINT_PATH}?{parameters}"

    def retriever(
        self,
        *,
        retrieval_event_id: UUID,
        environ: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], datetime] = utc_now,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> HttpRetriever:
        authentication = load_provider_auth(profile.SOURCE_ID, environ)
        return HttpRetriever(
            self.transport_url,
            retrieval_event_id=retrieval_event_id,
            transport=transport,
            now=now,
            sleeper=sleeper,
            max_bytes=profile.MAX_BYTES,
            request_policy=PrivateRequestPolicy(
                profile.ORIGIN, authentication, xml_character_references=True
            ),
            # Documented token bans outlast this invocation's finite budget.
            retry_rate_limits=False,
        )
