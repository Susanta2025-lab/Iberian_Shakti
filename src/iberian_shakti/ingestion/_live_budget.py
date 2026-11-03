"""Stage 8 whole-run accounting around the existing production transport.

No retry engine lives here. Socket reads also consume a conservative inbound
budget (headers/framing included), so even buffered or rejected bodies cannot
evade the response-body ceiling. No addresses, headers or provider prose persist.
"""

from __future__ import annotations

import math
import signal
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import httpcore
import httpx

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion._http_transport import SocketOption
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason

MAX_BYTES = 32 * 1024 * 1024
MAX_SECONDS = 900.0
PACING_SECONDS = 1.1


class RunStop(Exception):
    """Only locally chosen static categories may cross the diagnostic boundary."""


@dataclass(frozen=True)
class Limits:
    logical: int = 8
    attempts: int = 24
    body_bytes: int = MAX_BYTES
    seconds: float = MAX_SECONDS

    def __post_init__(self) -> None:
        if (
            any(type(v) is not int or v < 1 for v in (self.logical, self.attempts, self.body_bytes))
            or self.logical > 8
            or self.attempts > 24
            or self.body_bytes > MAX_BYTES
            or not math.isfinite(self.seconds)
            or not 0 < self.seconds <= MAX_SECONDS
        ):
            raise ValueError("Invalid live limits")


@dataclass
class Budget:
    limits: Limits = field(default_factory=Limits)
    clock: Callable[[], float] = time.monotonic
    sleeper: Callable[[float], None] = time.sleep
    logical: int = 0
    optional: int = 0
    attempts: int = 0
    body_bytes: int = 0
    inbound_bytes: int = 0
    started: float = field(init=False)
    last_attempt: float | None = None
    current_attempts: int = 0

    def __post_init__(self) -> None:
        self.started = self.clock()

    @property
    def elapsed(self) -> float:
        return self.clock() - self.started

    def remaining_time(self) -> float:
        remaining = self.limits.seconds - self.elapsed
        if remaining <= 0:
            raise RunStop("wall_clock_budget_exhausted")
        return remaining

    def begin(self, *, optional: bool = False) -> None:
        self.remaining_time()
        if self.logical >= self.limits.logical:
            raise RunStop("logical_request_budget_exhausted")
        if optional and self.optional >= 1:
            raise RunStop("metadata_request_budget_exhausted")
        self.logical += 1
        self.optional += int(optional)
        self.current_attempts = 0

    def wait(self, seconds: float) -> None:
        if seconds >= self.remaining_time():
            raise RunStop("wall_clock_budget_exhausted")
        self.sleeper(seconds)
        self.remaining_time()

    def attempt(self) -> None:
        self.remaining_time()
        if self.logical < 1:
            raise RunStop("request_outside_authorized_plan")
        if self.attempts >= self.limits.attempts or self.current_attempts >= 3:
            raise RunStop("http_attempt_budget_exhausted")
        if max(self.inbound_bytes, self.body_bytes) >= self.limits.body_bytes:
            raise RunStop("attempted_byte_budget_exhausted")
        if self.last_attempt is not None:
            delay = PACING_SECONDS - (self.clock() - self.last_attempt)
            if delay > 0:
                self.wait(delay)
        self.last_attempt = self.clock()
        self.attempts += 1
        self.current_attempts += 1

    def read_limit(self, requested: int) -> int:
        self.remaining_time()
        remaining = self.limits.body_bytes - self.inbound_bytes
        if remaining <= 0:
            raise RunStop("attempted_byte_budget_exhausted")
        return min(requested, remaining)

    def body(self, size: int) -> None:
        self.remaining_time()
        if size > self.limits.body_bytes - self.body_bytes:
            raise RunStop("attempted_byte_budget_exhausted")
        self.body_bytes += size

    def counters(self) -> dict[str, int | float]:
        return {
            "logical_requests": self.logical,
            "optional_metadata_requests": self.optional,
            "http_attempts": self.attempts,
            "attempted_body_bytes": self.body_bytes,
            "inbound_transport_bytes": self.inbound_bytes,
            "elapsed_seconds": round(self.elapsed, 6),
        }

    def remaining(self) -> dict[str, int | float]:
        return {
            "logical_requests": self.limits.logical - self.logical,
            "http_attempts": self.limits.attempts - self.attempts,
            "body_bytes": self.limits.body_bytes - self.body_bytes,
            "inbound_transport_bytes": self.limits.body_bytes - self.inbound_bytes,
            "seconds": round(max(0.0, self.limits.seconds - self.elapsed), 6),
        }


class RunStream(httpcore.NetworkStream):
    def __init__(self, stream: httpcore.NetworkStream, budget: Budget) -> None:
        self.stream, self.budget = stream, budget

    def timeout(self, value: float | None) -> float:
        remaining = self.budget.remaining_time()
        return remaining if value is None else min(value, remaining)

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        data = self.stream.read(self.budget.read_limit(max_bytes), self.timeout(timeout))
        self.budget.inbound_bytes += len(data)
        if self.budget.inbound_bytes > self.budget.limits.body_bytes:
            raise RunStop("transport_accounting_failure")
        return data

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        self.stream.write(buffer, self.timeout(timeout))

    def start_tls(
        self, ssl_context: Any, server_hostname: str | None = None, timeout: float | None = None
    ) -> httpcore.NetworkStream:
        return RunStream(
            self.stream.start_tls(ssl_context, server_hostname, self.timeout(timeout)), self.budget
        )

    def get_extra_info(self, info: str) -> Any:
        return self.stream.get_extra_info(info)

    def close(self) -> None:
        self.stream.close()


class RunBackend(httpcore.NetworkBackend):
    def __init__(self, budget: Budget, backend: httpcore.NetworkBackend | None = None) -> None:
        self.budget = budget
        self.backend = backend if backend is not None else httpcore.SyncBackend()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.NetworkStream:
        remaining = self.budget.remaining_time()
        return RunStream(
            self.backend.connect_tcp(
                host,
                port,
                min(timeout, remaining) if timeout is not None else remaining,
                local_address,
                socket_options,
            ),
            self.budget,
        )

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.NetworkStream:
        raise RunStop("unsafe_transport")


class CountedStream(httpx.SyncByteStream):
    def __init__(self, stream: httpx.SyncByteStream, budget: Budget, cap: int) -> None:
        self.stream, self.budget, self.cap = stream, budget, cap

    def __iter__(self) -> Iterator[bytes]:
        size = 0
        for chunk in self.stream:
            self.budget.body(len(chunk))
            size += len(chunk)
            if size > self.cap:
                raise ExecutionError(ErrorCode.SIZE_LIMIT, FailureReason.SIZE)
            yield chunk

    def close(self) -> None:
        self.stream.close()


class CountedTransport(httpx.BaseTransport):
    def __init__(
        self, inner: httpx.BaseTransport, budget: Budget, expected_url: str, cap: int
    ) -> None:
        self.inner, self.budget, self.expected_url, self.cap = inner, budget, expected_url, cap
        self.statuses: list[int | None] = []
        self.error_body_read_failures = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        safe_url = request.url.copy_remove_param("securityToken")
        if request.method != "GET" or safe_url != httpx.URL(self.expected_url):
            raise RunStop("request_outside_authorized_plan")
        self.budget.attempt()
        self.statuses.append(None)
        response = self.inner.handle_request(request)
        self.statuses[-1] = response.status_code
        if 300 <= response.status_code < 400:
            response.close()
            raise RunStop("unsafe_redirect")
        if not isinstance(response.stream, httpx.SyncByteStream):
            raise RunStop("transport_accounting_failure")
        response.stream = CountedStream(response.stream, self.budget, self.cap)
        if response.status_code != 200:
            # Production intentionally ignores error prose. Consume it boundedly
            # here for attempted-byte accounting, without retaining or decoding it.
            try:
                for _ in response.iter_raw():
                    pass
            except (httpx.RequestError, ExecutionError):
                # Error bodies are never evidence. A failed bounded drain must
                # not turn a terminal 401/403/ENTSO-E 429 into a transport retry.
                # The known HTTP status still governs production retry policy.
                self.error_body_read_failures += 1
            finally:
                response.close()
        return response

    def close(self) -> None:
        self.inner.close()


@contextmanager
def hard_deadline(budget: Budget) -> Iterator[None]:
    """Host deadline also interrupts DNS, parsing and filesystem work on POSIX.

    Call only on the main thread with no pre-existing interval timer. Validate
    that requirement before constructing any client. Restore the signal handler.
    """
    previous = signal.getsignal(signal.SIGALRM)

    def expired(signum: int, frame: Any) -> None:
        raise RunStop("wall_clock_budget_exhausted")

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, budget.remaining_time())
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
