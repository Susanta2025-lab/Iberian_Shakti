"""Exercise the shared guard without ever attempting an actual connection."""

import socket

import httpcore
import httpx
import pytest

# This runs at module collection, before any autouse/test fixture can help.
with pytest.raises(AssertionError, match="Default pytest forbids network access"):
    socket.create_connection(("127.0.0.1", 1))


@pytest.mark.parametrize(
    "api,args",
    [
        ("create_connection", (("127.0.0.1", 1),)),
        ("getaddrinfo", ("localhost", 1)),
        ("gethostbyname", ("localhost",)),
        ("gethostbyname_ex", ("localhost",)),
        ("gethostbyaddr", ("127.0.0.1",)),
        ("getnameinfo", (("127.0.0.1", 1), 0)),
        ("getfqdn", ("localhost",)),
    ],
)
def test_shared_guard_blocks_resolution_and_connection(api, args):
    with pytest.raises(AssertionError, match="Default pytest forbids network access"):
        getattr(socket, api)(*args)


@pytest.mark.parametrize("api", ["connect", "connect_ex", "send", "sendall", "sendto"])
def test_shared_guard_blocks_direct_socket_operations(api):
    args = {
        "connect": (("127.0.0.1", 1),),
        "connect_ex": (("127.0.0.1", 1),),
        "send": (b"",),
        "sendall": (b"",),
        "sendto": (b"", ("127.0.0.1", 1)),
    }[api]
    with pytest.raises(AssertionError, match="Default pytest forbids network access"):
        getattr(socket.socket, api)(None, *args)


def test_shared_guard_blocks_sendmsg():
    if hasattr(socket.socket, "sendmsg"):
        with pytest.raises(AssertionError, match="Default pytest forbids network access"):
            socket.socket.sendmsg(None, [b""])


def test_shared_guard_blocks_accidental_httpx_transport():
    with httpx.Client(trust_env=False) as client:
        with pytest.raises(AssertionError, match="Default pytest forbids network access"):
            client.get("https://127.0.0.1:1")


def test_shared_guard_blocks_async_httpx_transport_before_io():
    # Call the patched boundary directly; no event loop or real backend needed.
    with pytest.raises(AssertionError, match="Default pytest forbids network access"):
        httpx.AsyncHTTPTransport.handle_async_request(None, None)


def test_mock_transport_and_fake_core_backend_remain_usable():
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"offline"))
    ) as client:
        assert client.get("https://example.invalid").content == b"offline"
    backend = httpcore.MockBackend([b"synthetic"])
    stream = backend.connect_tcp("example.invalid", 443)
    assert stream.read(100) == b"synthetic"
    stream.close()
