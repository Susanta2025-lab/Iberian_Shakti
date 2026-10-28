"""Private request construction and active-credential echo protection; no I/O.

These execution objects are deliberately not persisted contracts. They have no
JSON/dict serialization API. Only safe query identity goes into provenance.
"""

import json
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import quote, quote_plus

import httpx
from pydantic import SecretStr

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason


def validate_credential(value: str) -> None:
    # Application bounds, not a statement about a provider's token grammar.
    if not 8 <= len(value) <= 4096 or any(not 33 <= ord(c) <= 126 for c in value):
        raise ValueError("Invalid selected-provider credential")


@dataclass(frozen=True)
class HeaderAuthentication:
    credential: SecretStr = field(repr=False)
    name: Literal["x-api-key"] = "x-api-key"

    def __post_init__(self) -> None:
        if self.name != "x-api-key" or not isinstance(self.credential, SecretStr):
            raise ValueError("Invalid private header authentication")
        validate_credential(self.credential.get_secret_value())


@dataclass(frozen=True)
class QueryAuthentication:
    credential: SecretStr = field(repr=False)
    name: Literal["securityToken"] = "securityToken"

    def __post_init__(self) -> None:
        if self.name != "securityToken" or not isinstance(self.credential, SecretStr):
            raise ValueError("Invalid private query authentication")
        validate_credential(self.credential.get_secret_value())


type PrivateAuthentication = HeaderAuthentication | QueryAuthentication


@dataclass(frozen=True)
class PrivateRequest:
    url: httpx.URL = field(repr=False)
    headers: tuple[tuple[str, str], ...] = field(repr=False)


@dataclass(frozen=True)
class PrivateRequestPolicy:
    """Execution-owned fixed origin and optional auth, never query metadata.

    The echo guard checks only the active credential's literal/quoted/escaped
    forms. It is not general DLP or a decoder for arbitrary response encodings.
    """

    origin: str
    authentication: PrivateAuthentication | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        try:
            url = httpx.URL(self.origin)
            valid = (
                url.scheme == "https"
                and bool(url.host)
                and not url.userinfo
                and not url.query
                and not url.fragment
                and url.path == "/"
            )
        except (TypeError, ValueError, httpx.InvalidURL):
            valid = False
        if not valid:
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR) from None
        if self.authentication is not None and not isinstance(
            self.authentication, HeaderAuthentication | QueryAuthentication
        ):
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.CONFIGURATION)
        # Revalidate potentially bypassed/custom objects before a request exists.
        if self.authentication is not None:
            validate_credential(self.authentication.credential.get_secret_value())

    def prepare(self, url: httpx.URL) -> PrivateRequest:
        origin = httpx.URL(self.origin)
        if (
            (url.scheme, url.host, url.port) != (origin.scheme, origin.host, origin.port)
            or url.userinfo
            or url.fragment
            or self.contains_credential(str(url).encode("utf-8"))
        ):
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR)
        headers: tuple[tuple[str, str], ...] = (("Accept-Encoding", "identity"),)
        auth = self.authentication
        # Never accept a credential from an upstream resolver, even without auth.
        if any(
            k.lower() in {"securitytoken", "token", "api_key", "apikey", "x-api-key"}
            for k in url.params
        ):
            raise ExecutionError(ErrorCode.INVALID_LOCATOR, FailureReason.LOCATOR)
        if isinstance(auth, HeaderAuthentication):
            headers += ((auth.name, auth.credential.get_secret_value()),)
        elif isinstance(auth, QueryAuthentication):
            url = url.copy_add_param(auth.name, auth.credential.get_secret_value())
        return PrivateRequest(url, headers)

    def contains_credential(self, data: bytes) -> bool:
        auth = self.authentication
        if auth is None:
            return False
        secret = auth.credential.get_secret_value()
        forms = (secret, quote(secret, safe=""), quote_plus(secret), json.dumps(secret)[1:-1])
        return any(value.encode("utf-8") in data for value in forms)
