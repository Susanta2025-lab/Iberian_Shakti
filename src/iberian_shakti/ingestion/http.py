"""Bounded synchronous HTTP retrieval; provider policy is injected, never inferred."""

import logging
import re
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from uuid import UUID

import httpx
from pydantic import ValidationError

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    HttpObservations,
    ListingRequest,
    ListingResult,
    ResolvedSource,
    RetrievalOutcome,
    RetrievalResult,
)
from iberian_shakti.contracts.queries import ApiSourceRequest
from iberian_shakti.ingestion._http_transport import DeadlineTransport, deadline_context
from iberian_shakti.ingestion.auth import PrivateRequestPolicy
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


@dataclass(frozen=True)
class _Acquisition:
    attempt: int
    outcome: RetrievalOutcome = RetrievalOutcome.RETRIEVED
    content: bytes | None = None
    code: ErrorCode | None = None
    status: int | None = None
    observations: HttpObservations | None = None


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
        (httpx.WriteError, ErrorCode.TRANSPORT_FAILURE, FailureReason.CONNECTION),
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
        resolve_listing_url: Callable[[ListingRequest], str] | None = None,
        listing_max_bytes: int = 1024 * 1024,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = utc_now,
        request_policy: PrivateRequestPolicy | None = None,
        retry_rate_limits: bool = True,
    ) -> None:
        validate_size(max_bytes)
        validate_size(listing_max_bytes)
        self.resolve_listing_url = resolve_listing_url
        self.listing_max_bytes = listing_max_bytes
        validate_event_id(retrieval_event_id)
        self.resolve_url = resolve_url
        self.event_id = retrieval_event_id
        self.retry_rate_limits = retry_rate_limits
        self.classify_unavailable = classify_unavailable
        self.policy = policy if policy is not None else RetryPolicy()
        self.transport = transport
        self.max_bytes = max_bytes
        self.request_policy = request_policy
        self.clock = clock
        self.sleeper = sleeper
        self.now = now

    @staticmethod
    def _url(resolve: Callable[[], str]) -> httpx.URL:
        try:
            url = httpx.URL(resolve())
        except (ValueError, TypeError, httpx.InvalidURL) as error:
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR) from error
        if url.scheme != "https":
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SCHEME)
        if not url.host or url.userinfo or url.fragment:
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR)
        return url

    def retrieve(self, source: ResolvedSource) -> RetrievalResult:
        validate_source(source)
        if isinstance(source.request, ApiSourceRequest) and self.request_policy is None:
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION)
        if self.request_policy is not None and self.request_policy.contains_credential(
            source.model_dump_json().encode("utf-8")
        ):
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION)
        classifier = self.classify_unavailable
        acquired = self._acquire(
            self._url(lambda: self.resolve_url(source)),
            source_context(source),
            self.max_bytes,
            (lambda status: classifier(source, status)) if classifier is not None else None,
        )
        return result_for(
            source,
            self.event_id,
            self.now(),
            attempt=acquired.attempt,
            outcome=acquired.outcome,
            content=acquired.content,
            code=acquired.code,
            status=acquired.status,
            observations=acquired.observations,
        )

    def retrieve_listing(self, request: ListingRequest) -> ListingResult:
        ListingRequest.model_validate_json(request.model_dump_json())
        resolver = self.resolve_listing_url
        if resolver is None:
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION)
        acquired = self._acquire(
            self._url(lambda: resolver(request)),
            {"safe_locator": request.safe_locator},
            self.listing_max_bytes,
            None,
        )
        return ListingResult(
            outcome=acquired.outcome,
            attempt_count=acquired.attempt,
            content=acquired.content,
            http_status=acquired.status,
            http=acquired.observations,
            error_code=acquired.code,
        )

    def _acquire(
        self,
        url: httpx.URL,
        context: dict[str, object],
        max_bytes: int,
        classify_unavailable: Callable[[int], ErrorCode | None] | None,
    ) -> _Acquisition:
        private = self.request_policy.prepare(url) if self.request_policy is not None else None
        headers = dict(private.headers) if private is not None else {"Accept-Encoding": "identity"}
        if private is not None:
            url = private.url
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
                    return self._failure(
                        {
                            **context,
                            "elapsed_seconds": self.clock() - start,
                            "reason": FailureReason.DEADLINE.value,
                        },
                        max(1, attempt - 1),
                        ErrorCode.BUDGET_EXCEEDED,
                    )
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
                        headers=headers,
                        timeout=httpx.Timeout(
                            timeout, connect=timeout, read=timeout, write=timeout, pool=timeout
                        ),
                    ) as response:
                        self._check_deadline(deadline)
                        status = response.status_code
                        observations = _observations(response)
                        guard = self.request_policy
                        if guard is not None and any(
                            guard.contains_credential(value.encode("utf-8"))
                            for value in response.headers.values()
                        ):
                            observations = None
                        if status == 404 and classify_unavailable is not None:
                            code = classify_unavailable(status)
                            if code in {ErrorCode.NOT_FOUND, ErrorCode.NOT_LISTED}:
                                logger.info(
                                    "retrieval_unavailable",
                                    extra={
                                        **context,
                                        "attempt": attempt,
                                        "http_status": status,
                                        "elapsed_seconds": self.clock() - start,
                                        "error_code": code.value,
                                    },
                                )
                                return _Acquisition(
                                    attempt=attempt,
                                    outcome=RetrievalOutcome.UNAVAILABLE,
                                    code=code,
                                    status=status,
                                    observations=observations,
                                )
                        if status == 200:
                            if (
                                guard is not None
                                and guard.authentication is not None
                                and response.headers.get("content-encoding", "identity").lower()
                                != "identity"
                            ):
                                # Unknown encoded content cannot be checked for a credential echo.
                                # Reject before publication, without decoding/altering raw bytes.
                                raise ExecutionError(
                                    ErrorCode.UNSUPPORTED_ENCODING, FailureReason.ENCODING
                                )
                            content = self._read(response, deadline, max_bytes)
                            if guard is not None and guard.contains_credential(content):
                                raise ExecutionError(
                                    ErrorCode.SENSITIVE_RESPONSE, FailureReason.SENSITIVE_RESPONSE
                                )
                            logger.info(
                                "retrieval_completed",
                                extra={
                                    **context,
                                    "attempt": attempt,
                                    "http_status": status,
                                    "elapsed_seconds": self.clock() - start,
                                    "byte_count": len(content),
                                },
                            )
                            return _Acquisition(
                                attempt=attempt,
                                content=content,
                                status=status,
                                observations=observations,
                            )
                        if status == 429:
                            retry_after = self._retry_after(response.headers.get("retry-after"))
                            raise ExecutionError(
                                ErrorCode.RATE_LIMITED,
                                FailureReason.RATE_LIMIT,
                                retryable=self.retry_rate_limits,
                            )
                        if guard is not None and status in {401, 403}:
                            raise ExecutionError(
                                ErrorCode.AUTHENTICATION_FAILURE
                                if status == 401
                                else ErrorCode.AUTHORIZATION_FAILURE,
                                FailureReason.AUTHENTICATION
                                if status == 401
                                else FailureReason.AUTHORIZATION,
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
                            "retrieval_failed",
                            extra={
                                **context,
                                "attempt": attempt,
                                "http_status": status,
                                "elapsed_seconds": self.clock() - start,
                                "error_code": error.code.value,
                                "reason": error.reason.value,
                            },
                        )
                        raise
                    failure = error
                finally:
                    deadline_context.reset(token)
                failure_context = {
                    **context,
                    "attempt": attempt,
                    "http_status": status,
                    "elapsed_seconds": self.clock() - start,
                    "error_code": failure.code.value,
                    "reason": failure.reason.value,
                }
                if not failure.retryable:
                    logger.warning("retrieval_failed", extra=failure_context)
                    return _Acquisition(
                        attempt=attempt,
                        outcome=RetrievalOutcome.PERMANENT_FAILURE,
                        code=failure.code,
                        status=status,
                        observations=observations,
                    )
                if attempt == self.policy.max_attempts:
                    return self._failure(
                        failure_context, attempt, failure.code, status, observations
                    )
                remaining = operation_deadline - self.clock()
                delay = self.policy.delay(attempt)
                if retry_after is not None:
                    delay = max(delay, retry_after)
                # Do not truncate a provider's minimum wait and retry too early.
                # If it cannot fit, terminate without sleeping or another request.
                if delay >= remaining:
                    code = failure.code if status == 429 else ErrorCode.BUDGET_EXCEEDED
                    return self._failure(failure_context, attempt, code, status, observations)
                logger.info("retry_scheduled", extra=failure_context)
                self.sleeper(delay)
        raise AssertionError("Finite nonempty attempt range must return")

    def _check_deadline(self, deadline: float) -> None:
        if self.clock() >= deadline:
            raise ExecutionError(ErrorCode.BUDGET_EXCEEDED, FailureReason.DEADLINE, retryable=True)

    def _read(self, response: httpx.Response, deadline: float, max_bytes: int) -> bytes:
        # Do not use iter_bytes/read/text: those decode Content-Encoding.
        if response.is_stream_consumed:
            raise ExecutionError(ErrorCode.INCOMPLETE_BODY, FailureReason.PROTOCOL)
        content = bytearray()
        for chunk in response.iter_raw():
            self._check_deadline(deadline)
            if len(chunk) > max_bytes - len(content):
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
        context: dict[str, object],
        attempt: int,
        code: ErrorCode,
        status: int | None = None,
        observations: HttpObservations | None = None,
    ) -> _Acquisition:
        logger.warning(
            "retry_exhausted",
            extra={
                **context,
                "attempt": attempt,
                "error_code": code.value,
            },
        )
        return _Acquisition(
            attempt=attempt,
            outcome=RetrievalOutcome.RETRY_EXHAUSTED,
            code=code,
            status=status,
            observations=observations,
        )
