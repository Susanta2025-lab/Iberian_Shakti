"""Private request construction and active-credential echo protection; no I/O.

These execution objects are deliberately not persisted contracts. They have no
JSON/dict serialization API. Only safe query identity goes into provenance.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import quote, quote_plus, unquote_to_bytes

import httpx
from pydantic import SecretStr

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason

_XML_REFERENCE = re.compile(r"&#(?:x[0-9a-fA-F]+|[0-9]+);|&(?:amp|lt|gt|quot|apos);")
_JSON_ESCAPE = re.compile(rb'\\(?:["\\/]|u[0-9a-fA-F]{4})')


def _json_escape(match: re.Match[bytes]) -> bytes:
    value = match.group()
    if value.startswith(b"\\u"):
        number = int(value[2:], 16)
        # Credentials are printable ASCII. No Unicode normalization, surrogate
        # assembly or recursive decoding is needed to recognize their echoes.
        return bytes([number]) if 33 <= number <= 126 else value
    return value[1:]


def _contains_form(data: bytes, secret: str) -> bool:
    forms = (secret, quote(secret, safe=""), quote_plus(secret), json.dumps(secret)[1:-1])
    if any(value.encode("utf-8") in data for value in forms):
        return True
    literal = secret.encode("ascii")
    # One pass per supported encoding, including mixed literal/escaped text.
    # Inputs are already byte-bounded; no body parser or recursive decoder runs.
    return (b"%" in data and literal in unquote_to_bytes(data)) or (
        b"\\" in data and literal in _JSON_ESCAPE.sub(_json_escape, data)
    )


def _xml_reference(match: re.Match[str]) -> str:
    value = match.group()
    if value.startswith("&#"):
        hexadecimal = value.startswith("&#x")
        digits = value[3:-1] if hexadecimal else value[2:-1]
        digits = digits.lstrip("0") or "0"
        # XML permits zero-padded references. Avoid Python's integer conversion
        # work/digit limit for hostile tokens while retaining valid codepoints.
        if len(digits) > (6 if hexadecimal else 7):
            return value
        number = int(digits, 16 if hexadecimal else 10)
        return chr(number) if 0 < number <= 0x10FFFF and not 0xD800 <= number <= 0xDFFF else value
    return {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'"}[value]


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

    The echo guard checks only the active credential's literal/quoted forms,
    single-pass percent/JSON escapes and optional XML character references.
    It is not general DLP or a decoder for arbitrary response encodings.
    """

    origin: str
    authentication: PrivateAuthentication | None = field(default=None, repr=False)
    xml_character_references: bool = False

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
        if _contains_form(data, secret):
            return True
        if self.xml_character_references:
            try:
                # Only XML's predefined/character references, one pass, no DTD
                # or XML execution. Check without altering archived originals.
                decoded = _XML_REFERENCE.sub(_xml_reference, data.decode("utf-8"))
            except UnicodeDecodeError:
                return False
            return _contains_form(decoded.encode("utf-8"), secret)
        return False
