"""One fixed anonymous REN product; no discovery, credentials or second download."""

import time
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

import httpx

from iberian_shakti.contracts.ingestion import ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest
from iberian_shakti.ingestion.auth import PrivateRequestPolicy
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.ren import profile
from iberian_shakti.ingestion.ren.identity import validate_resolved
from iberian_shakti.ingestion.ren.parser import RenParser
from iberian_shakti.ingestion.retrieval import utc_now


class RenAdapter:
    parser = RenParser()

    @staticmethod
    def resolve(request: ApiSourceRequest) -> ResolvedSource:
        source = ResolvedSource.for_api(request)
        validate_resolved(source)
        return source

    @staticmethod
    def transport_url(source: ResolvedSource) -> str:
        validate_resolved(source)
        # Date is validated; every other transport component is a pinned constant.
        return (
            f"{profile.ORIGIN}{profile.ENDPOINT_PATH}"
            f"?culture={profile.CULTURE}&date={source.request.delivery_date.isoformat()}"
        )

    def retriever(
        self,
        *,
        retrieval_event_id: UUID,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], datetime] = utc_now,
        sleeper: Callable[[float], None] | None = None,
    ) -> HttpRetriever:
        """Use shared default 3-attempt policy; no polling/batch/concurrency layer.

        Successive deliberate invocations must be paced by the caller at >=1s.
        The inherited default retry waits are 1s then 2s.
        """
        return HttpRetriever(
            self.transport_url,
            retrieval_event_id=retrieval_event_id,
            transport=transport,
            now=now,
            max_bytes=profile.MAX_BYTES,
            request_policy=PrivateRequestPolicy(profile.ORIGIN),
            sleeper=time.sleep if sleeper is None else sleeper,
        )
