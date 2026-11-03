"""Fixed anonymous weather products using shared transport; no live command."""

import time
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

import httpx

from iberian_shakti.contracts.ingestion import ResolvedSource
from iberian_shakti.contracts.queries import ApiSourceRequest, WeatherQuery
from iberian_shakti.ingestion.auth import PrivateRequestPolicy
from iberian_shakti.ingestion.http import HttpRetriever
from iberian_shakti.ingestion.retrieval import utc_now
from iberian_shakti.ingestion.weather import profile
from iberian_shakti.ingestion.weather.identity import validate_forecast_window, validate_resolved
from iberian_shakti.ingestion.weather.parser import IconEuParser, OpenMeteoParser


class OpenMeteoAdapter:
    parser = OpenMeteoParser()
    report_id = profile.HISTORICAL_REPORT
    model_id = profile.HISTORICAL_MODEL
    origin = profile.HISTORICAL_ORIGIN
    path = profile.HISTORICAL_PATH

    @classmethod
    def resolve(cls, request: ApiSourceRequest) -> ResolvedSource:
        source = ResolvedSource.for_api(request)
        validate_resolved(source, report_id=cls.report_id)
        return source

    @classmethod
    def transport_url(cls, source: ResolvedSource) -> str:
        validate_resolved(source, report_id=cls.report_id)
        request = source.request
        assert isinstance(request, ApiSourceRequest) and isinstance(request.query, WeatherQuery)
        coordinates = request.query.site.requested
        parameters = urlencode(
            {
                "latitude": coordinates.latitude,
                "longitude": coordinates.longitude,
                "start_date": request.delivery_date.isoformat(),
                "end_date": request.delivery_date.isoformat(),
                "models": cls.model_id,
                "hourly": ",".join(profile.VARIABLES),
                "timezone": "GMT",
                "timeformat": "unixtime",
                "temperature_unit": "celsius",
                "wind_speed_unit": "ms",
            }
        )
        return f"{cls.origin}{cls.path}?{parameters}"

    def retriever(
        self,
        *,
        retrieval_event_id: UUID,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], datetime] = utc_now,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> HttpRetriever:
        def resolve_url(source: ResolvedSource) -> str:
            url = self.transport_url(source)
            if self.report_id == profile.FORECAST_REPORT:
                request = source.request
                assert isinstance(request, ApiSourceRequest)
                validate_forecast_window(request.window, now())
            return url

        return HttpRetriever(
            resolve_url,
            retrieval_event_id=retrieval_event_id,
            transport=transport,
            now=now,
            sleeper=sleeper,
            max_bytes=profile.MAX_BYTES,
            request_policy=PrivateRequestPolicy(self.origin),
        )


class OpenMeteoForecastAdapter(OpenMeteoAdapter):
    parser = IconEuParser()
    report_id = profile.FORECAST_REPORT
    model_id = profile.FORECAST_MODEL
    origin = profile.FORECAST_ORIGIN
    path = profile.FORECAST_PATH
