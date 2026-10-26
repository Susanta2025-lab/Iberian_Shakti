"""Default pytest is offline, including collection and session fixtures.

There is deliberately no marker, CLI option, or environment escape hatch.
Explicit live validation belongs in a separate operator command outside pytest.
Patch operations rather than socket construction so fake backends and ordinary
filesystem work remain usable. Never include attempted addresses in diagnostics.
"""

import socket
from typing import NoReturn

import httpx
import pytest

_NETWORK_PATCH = pytest.StashKey[pytest.MonkeyPatch]()


def _network_denied(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError("Default pytest forbids network access")


def pytest_configure(config: pytest.Config) -> None:
    patch = pytest.MonkeyPatch()
    config.stash[_NETWORK_PATCH] = patch
    for name in (
        "create_connection",
        "getaddrinfo",
        "gethostbyname",
        "gethostbyname_ex",
        "gethostbyaddr",
        "getnameinfo",
        "getfqdn",
    ):
        patch.setattr(socket, name, _network_denied)
    for name in ("connect", "connect_ex", "send", "sendall", "sendto", "sendmsg"):
        if hasattr(socket.socket, name):
            patch.setattr(socket.socket, name, _network_denied)
    # Fail before transport exception translation/retry can obscure the denial.
    # MockTransport and the project's httpcore fake-backend tests stay available;
    # real custom transports still encounter the socket/DNS boundary above.
    patch.setattr(httpx.HTTPTransport, "handle_request", _network_denied)
    patch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _network_denied)


def pytest_unconfigure(config: pytest.Config) -> None:
    patch = config.stash.get(_NETWORK_PATCH, None)
    if patch is not None:
        patch.undo()
