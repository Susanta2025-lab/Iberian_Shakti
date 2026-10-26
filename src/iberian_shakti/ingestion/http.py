"""Bounded synchronous HTTP retrieval; provider policy is injected, never inferred."""

import logging
import re
import ssl
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from uuid import UUID

import httpx
from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    HttpObservations,
    ResolvedSource,
    RetrievalOutcome,
    RetrievalResult,
)
from iberian_shakti.ingestion._http_transport import DeadlineTransport, deadline_context
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.retrieval import (
    DEFAULT_MAX_BYTES,
    result_for,
    source_context,
    utc_now,
    validate_event_id,
    validate_size,
    validate_source,
)
from iberian_shakti.ingestion.retry import RetryPolicy

logger = logging.getLogger(__name__)
type LocatorResolver = Callable[[ResolvedSource], str]
type UnavailableClassifier = Callable[[ResolvedSource, int], ErrorCode | None]


def _observations(response: httpx.Response) -> HttpObservations:
    # Invalid optional observations are omitted individually. They cannot
    # prevent preserving a complete body; no unchecked header text is logged.
    candidates: dict[str, object] = {}
    for field, header in (
        ("content_type", "content-type"),
        ("content_encoding", "content-encoding"),
        ("etag", "etag"),
    ):
        value = response.headers.get(header)
        if value is not None:
            if field == "content_type":
                value = value.split(";", 1)[0].strip()
            candidates[field] = value
    modified = response.headers.get("last-modified")
    if modified is not None:
        try:
            parsed = parsedate_to_datetime(modified)
            if parsed.tzinfo is not None:
                candidates["last_modified"] = parsed.astimezone(UTC)
        except (ValueError, TypeError, OverflowError):
            pass
    valid: dict[str, object] = {}
    for field, value in candidates.items():
        try:
            HttpObservations.model_validate({field: value})
        except ValidationError:
            if field == "content_encoding":
                raise ExecutionError(
                    ErrorCode.UNSUPPORTED_ENCODING, FailureReason.ENCODING
                ) from None
            continue
        valid[field] = value
    return HttpObservations.model_validate(valid)


def _transport_error(error: httpx.RequestError) -> ExecutionError:
    cause: BaseException | None = error
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, ssl.SSLError):
            return ExecutionError(ErrorCode.TLS_FAILURE, FailureReason.TLS)
        cause = cause.__cause__ or cause.__context__
    for error_type, code, reason in (
        (httpx.ConnectTimeout, ErrorCode.TIMEOUT, FailureReason.CONNECT_TIMEOUT),
        (httpx.ReadTimeout, ErrorCode.TIMEOUT, FailureReason.READ_TIMEOUT),
        (httpx.WriteTimeout, ErrorCode.TIMEOUT, FailureReason.WRITE_TIMEOUT),
        (httpx.PoolTimeout, ErrorCode.TIMEOUT, FailureReason.POOL_TIMEOUT),
        (httpx.ConnectError, ErrorCode.TRANSPORT_FAILURE, FailureReason.CONNECTION),
        (httpx.ReadError, ErrorCode.INCOMPLETE_BODY, FailureReason.PROTOCOL),
        (httpx.RemoteProtocolError, ErrorCode.INCOMPLETE_BODY, FailureReason.PROTOCOL),
    ):
        if isinstance(error, error_type):
            return ExecutionError(code, reason, retryable=True)
    return ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR)


class HttpRetriever:
    """One explicit event identity per acquisition; transport injection is offline-friendly.

    The resolver maps an opaque safe locator to a private transport URL. Only
    HTTPS is supported; redirects are rejected (a bound of zero), so redirect
    bodies cannot trigger HTTPX's implicit unbounded decoded reads. Complete
    non-identity encoded bodies remain raw and are marked in HTTP observations;
    future parsers must explicitly reject encodings they do not support.
    """

    def __init__(
        self,
        resolve_url: LocatorResolver,
        *,
        retrieval_event_id: UUID,
        classify_unavailable: UnavailableClassifier | None = None,
        transport: httpx.BaseTransport | None = None,
        policy: RetryPolicy | None = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = utc_now,
    ) -> None:
        validate_size(max_bytes)
        validate_event_id(retrieval_event_id)
        self.resolve_url = resolve_url
        self.event_id = retrieval_event_id
        self.classify_unavailable = classify_unavailable
        self.policy = policy if policy is not None else RetryPolicy()
        self.transport = transport
        self.max_bytes = max_bytes
        self.clock = clock
        self.sleeper = sleeper
        self.now = now

    def _url(self, source: ResolvedSource) -> httpx.URL:
        try:
            url = httpx.URL(self.resolve_url(source))
        except (ValueError, TypeError, httpx.InvalidURL) as error:
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR) from error
        if url.scheme != "https":
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SCHEME)
        if not url.host or url.userinfo or url.fragment:
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR)
        return url

    def retrieve(self, source: ResolvedSource) -> RetrievalResult:
        validate_source(source)
        context = source_context(source)
        url = self._url(source)
        start = self.clock()
        operation_deadline = start + self.policy.operation_timeout_seconds
        # A supplied transport must implement finite phase timeouts and no
        # internal retries. MockTransport permits deterministic fake-clock tests.
        transport = self.transport if self.transport is not None else DeadlineTransport()
        with httpx.Client(
            transport=transport, trust_env=False, follow_redirects=False, max_redirects=0
        ) as client:
            for attempt in range(1, self.policy.max_attempts + 1):
                remaining = operation_deadline - self.clock()
                if remaining <= 0:
                    # No request started, including after an oversleep.
                    if attempt == 1:
                        raise ExecutionError(ErrorCode.BUDGET_EXCEEDED, FailureReason.DEADLINE)
                    return self._failure(source, max(1, attempt - 1), ErrorCode.BUDGET_EXCEEDED)
                deadline = min(
                    operation_deadline, self.clock() + self.policy.attempt_timeout_seconds
                )
                logger.info("retrieval_attempt", extra={**context, "attempt": attempt})
                status = None
                observations = None
                retry_after = None
                token = deadline_context.set((deadline, self.clock))
                try:
                    timeout = min(self.policy.phase_timeout_seconds, deadline - self.clock())
                    if timeout <= 0:
                        raise ExecutionError(
                            ErrorCode.BUDGET_EXCEEDED, FailureReason.DEADLINE, retryable=True
                        )
                    with client.stream(
                        "GET",
                        url,
                        headers={"Accept-Encoding": "identity"},
                        timeout=httpx.Timeout(
                            timeout, connect=timeout, read=timeout, write=timeout, pool=timeout
                        ),
                    ) as response:
                        self._check_deadline(deadline)
                        status = response.status_code
                        observations = _observations(response)
                        if status == 404 and self.classify_unavailable is not None:
                            code = self.classify_unavailable(source, status)
                            if code in {ErrorCode.NOT_FOUND, ErrorCode.NOT_LISTED}:
                                logger.info("retrieval_unavailable", extra=context)
                                return result_for(
                                    source,
                                    self.event_id,
                                    self.now(),
                                    attempt=attempt,
                                    outcome=RetrievalOutcome.UNAVAILABLE,
                                    code=code,
                                    status=status,
                                    observations=observations,
                                )
                        if status == 200:
                            content = self._read(response, deadline)
                            logger.info(
                                "retrieval_completed", extra={**context, "byte_count": len(content)}
                            )
                            return result_for(
                                source,
                                self.event_id,
                                self.now(),
                                attempt=attempt,
                                content=content,
                                status=status,
                                observations=observations,
                            )
                        if status == 429:
                            retry_after = self._retry_after(response.headers.get("retry-after"))
                            raise ExecutionError(
                                ErrorCode.RATE_LIMITED, FailureReason.RATE_LIMIT, retryable=True
                            )
                        raise ExecutionError(
                            ErrorCode.HTTP_FAILURE,
                            FailureReason.HTTP,
                            retryable=status in {500, 502, 503, 504},
                        )
                except httpx.RequestError as error:
                    failure = _transport_error(error)
                    failure.__cause__ = error
                except ExecutionError as error:
                    if error.code is ErrorCode.UNSUPPORTED_ENCODING:
                        logger.warning(
                            "retrieval_failed", extra={**context, "error_code": error.code.value}
                        )
                        raise
                    failure = error
                finally:
                    deadline_context.reset(token)
                if not failure.retryable:
                    logger.warning(
                        "retrieval_failed", extra={**context, "error_code": failure.code.value}
                    )
                    return result_for(
                        source,
                        self.event_id,
                        self.now(),
                        attempt=attempt,
                        outcome=RetrievalOutcome.PERMANENT_FAILURE,
                        code=failure.code,
                        status=status,
                        observations=observations,
                    )
                if attempt == self.policy.max_attempts:
                    return self._failure(source, attempt, failure.code, status, observations)
                remaining = operation_deadline - self.clock()
                delay = self.policy.delay(attempt)
                if retry_after is not None:
                    delay = max(delay, retry_after)
                # Do not truncate a provider's minimum wait and retry too early.
                # If it cannot fit, terminate without sleeping or another request.
                if delay >= remaining:
                    code = failure.code if status == 429 else ErrorCode.BUDGET_EXCEEDED
                    return self._failure(source, attempt, code, status, observations)
                logger.info("retry_scheduled", extra={**context, "attempt": attempt})
                self.sleeper(delay)
        raise AssertionError("Finite nonempty attempt range must return")

    def _check_deadline(self, deadline: float) -> None:
        if self.clock() >= deadline:
            raise ExecutionError(ErrorCode.BUDGET_EXCEEDED, FailureReason.DEADLINE, retryable=True)

    def _read(self, response: httpx.Response, deadline: float) -> bytes:
        # Do not use iter_bytes/read/text: those decode Content-Encoding.
        if response.is_stream_consumed:
            raise ExecutionError(ErrorCode.INCOMPLETE_BODY, FailureReason.PROTOCOL)
        content = bytearray()
        for chunk in response.iter_raw():
            self._check_deadline(deadline)
            if len(chunk) > self.max_bytes - len(content):
                raise ExecutionError(ErrorCode.SIZE_LIMIT, FailureReason.SIZE)
            content.extend(chunk)
        self._check_deadline(deadline)
        length = response.headers.get("content-length")
        if length is not None:
            if not re.fullmatch(r"[0-9]{1,20}", length) or int(length) != len(content):
                raise ExecutionError(
                    ErrorCode.INCOMPLETE_BODY, FailureReason.PROTOCOL, retryable=True
                )
        return bytes(content)

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        # RFC delta-seconds only. Saturate enormous valid numbers before float
        # conversion: they cannot fit the operation budget and must not trigger
        # either a giant sleep or an early fallback retry.
        if value is not None and re.fullmatch(r"[0-9]+", value.strip()):
            digits = value.strip().lstrip("0") or "0"
            return float(digits) if len(digits) <= 10 else 10_000_000_000.0
        return None

    def _failure(
        self,
        source: ResolvedSource,
        attempt: int,
        code: ErrorCode,
        status: int | None = None,
        observations: HttpObservations | None = None,
    ) -> RetrievalResult:
        logger.warning(
            "retry_exhausted",
            extra={
                **source_context(source),
                "attempt": attempt,
                "error_code": code.value,
            },
        )
        return result_for(
            source,
            self.event_id,
            self.now(),
            attempt=attempt,
            outcome=RetrievalOutcome.RETRY_EXHAUSTED,
            code=code,
            status=status,
            observations=observations,
        )
