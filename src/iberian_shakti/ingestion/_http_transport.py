"""HTTPX transport with a shrinking timeout at each underlying socket operation.

HTTPX's required httpcore 1.x provides the public pool/backend interfaces.
Checking only between body chunks misses slow headers and repeated short reads
inside one protocol event. This backend also bounds those reads. No private
HTTPX/httpcore attributes are modified. OS name resolution and arbitrary injected
backends are subject to the host/backend timeout contract.
"""

import ssl
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

import httpcore
import httpx

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason

type SocketOption = (
    tuple[int, int, int] | tuple[int, int, bytes | bytearray] | tuple[int, int, None, int]
)
type Deadline = tuple[float, Callable[[], float]]

deadline_context: ContextVar[Deadline] = ContextVar("ingestion_http_deadline")


def remaining_timeout(timeout: float | None) -> float:
    deadline, clock = deadline_context.get()
    remaining = deadline - clock()
    if remaining <= 0:
        raise ExecutionError(ErrorCode.BUDGET_EXCEEDED, FailureReason.DEADLINE, retryable=True)
    return min(timeout, remaining) if timeout is not None else remaining


class DeadlineStream(httpcore.NetworkStream):
    def __init__(self, stream: httpcore.NetworkStream) -> None:
        self.stream = stream

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return self.stream.read(max_bytes, timeout=remaining_timeout(timeout))

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        self.stream.write(buffer, timeout=remaining_timeout(timeout))

    def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.NetworkStream:
        return DeadlineStream(
            self.stream.start_tls(ssl_context, server_hostname, remaining_timeout(timeout))
        )

    def get_extra_info(self, info: str) -> Any:
        return self.stream.get_extra_info(info)

    def close(self) -> None:
        self.stream.close()


class DeadlineBackend(httpcore.NetworkBackend):
    def __init__(self, backend: httpcore.NetworkBackend | None = None) -> None:
        self.backend = backend if backend is not None else httpcore.SyncBackend()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.NetworkStream:
        return DeadlineStream(
            self.backend.connect_tcp(
                host, port, remaining_timeout(timeout), local_address, socket_options
            )
        )

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[SocketOption] | None = None,
    ) -> httpcore.NetworkStream:
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.SCHEME)

    def sleep(self, seconds: float) -> None:
        # The pool is configured with retries=0: this is never a retry layer.
        raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION)


_ERRORS: tuple[tuple[type[Exception], type[httpx.RequestError]], ...] = (
    (httpcore.ConnectTimeout, httpx.ConnectTimeout),
    (httpcore.ReadTimeout, httpx.ReadTimeout),
    (httpcore.WriteTimeout, httpx.WriteTimeout),
    (httpcore.PoolTimeout, httpx.PoolTimeout),
    (httpcore.ConnectError, httpx.ConnectError),
    (httpcore.ReadError, httpx.ReadError),
    (httpcore.WriteError, httpx.WriteError),
    (httpcore.RemoteProtocolError, httpx.RemoteProtocolError),
    (httpcore.LocalProtocolError, httpx.LocalProtocolError),
    (httpcore.UnsupportedProtocol, httpx.UnsupportedProtocol),
)


@contextmanager
def translate_errors() -> Iterator[None]:
    try:
        yield
    except Exception as error:
        for core_type, httpx_type in _ERRORS:
            if isinstance(error, core_type):
                raise httpx_type("Transport operation failed") from error
        raise


class ResponseStream(httpx.SyncByteStream):
    def __init__(self, response: httpcore.Response) -> None:
        self.response = response

    def __iter__(self) -> Iterator[bytes]:
        with translate_errors():
            yield from self.response.iter_stream()

    def close(self) -> None:
        with translate_errors():
            self.response.close()


class DeadlineTransport(httpx.BaseTransport):
    """Verified TLS, no proxy/environment credentials, HTTP/1.1, zero retries."""

    def __init__(self, *, backend: httpcore.NetworkBackend | None = None) -> None:
        self.pool = httpcore.ConnectionPool(
            ssl_context=ssl.create_default_context(),
            retries=0,
            network_backend=DeadlineBackend(backend),
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        with translate_errors():
            response = self.pool.handle_request(
                httpcore.Request(
                    method=request.method,
                    url=httpcore.URL(
                        scheme=request.url.raw_scheme,
                        host=request.url.raw_host,
                        port=request.url.port,
                        target=request.url.raw_path,
                    ),
                    headers=request.headers.raw,
                    content=request.stream,
                    extensions=request.extensions,
                )
            )
        return httpx.Response(
            response.status,
            headers=response.headers,
            stream=ResponseStream(response),
            extensions=response.extensions,
        )

    def close(self) -> None:
        self.pool.close()
