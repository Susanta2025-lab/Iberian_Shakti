"""Fixed indicator endpoint and shared private API-key transport; no live command."""

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
from iberian_shakti.ingestion.esios import profile
from iberian_shakti.ingestion.esios.identity import validate_resolved
from iberian_shakti.ingestion.esios.parser import EsiosParser
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.retrieval import utc_now


class EsiosAdapter:
    parser = EsiosParser()

    @staticmethod
    def resolve(request: ApiSourceRequest) -> ResolvedSource:
        source = ResolvedSource.for_api(request)
        validate_resolved(source)
        return source

    @staticmethod
    def transport_url(source: ResolvedSource) -> str:
        validate_resolved(source)
        assert isinstance(source.request, ApiSourceRequest)
        window = source.request.window
        parameters = urlencode(
            {"start_date": window.start_utc.isoformat(), "end_date": window.end_utc.isoformat()}
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
        # Selected-provider validation happens before any external request exists.
        authentication = load_provider_auth(profile.SOURCE_ID, environ)
        return HttpRetriever(
            self.transport_url,
            retrieval_event_id=retrieval_event_id,
            transport=transport,
            now=now,
            sleeper=sleeper,
            max_bytes=profile.MAX_BYTES,
            request_policy=PrivateRequestPolicy(profile.ORIGIN, authentication),
        )
