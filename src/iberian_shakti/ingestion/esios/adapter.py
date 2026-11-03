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
from iberian_shakti.ingestion.esios.identity import validate_resolved, wire_end
from iberian_shakti.ingestion.esios.parser import BoundedEsiosParser, EsiosParser
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.retrieval import utc_now


class EsiosAdapter:
    parser = EsiosParser()
    bounded = False

    @classmethod
    def resolve(cls, request: ApiSourceRequest) -> ResolvedSource:
        source = ResolvedSource.for_api(request)
        validate_resolved(source, bounded=cls.bounded)
        return source

    @classmethod
    def transport_url(cls, source: ResolvedSource) -> str:
        validate_resolved(source, bounded=cls.bounded)
        assert isinstance(source.request, ApiSourceRequest)
        window = source.request.window
        end = wire_end(window) if cls.bounded else window.end_utc
        parameters = urlencode(
            {"start_date": window.start_utc.isoformat(), "end_date": end.isoformat()}
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


class BoundedEsiosAdapter(EsiosAdapter):
    """Opt-in 0.2.0 provider endpoint translation; no response filtering."""

    parser = BoundedEsiosParser()
    bounded = True
