"""Bounded namespace-aware UTF-8 XML, without DTDs, entities or external I/O.

Expat callbacks reject declarations before processing a DTD or expanding an
entity. No resolver, XInclude, schema fetch or stylesheet processor exists.
Limits apply while constructing the tree, including fragmented text callbacks.
"""

from typing import NoReturn
from xml.etree.ElementTree import Element, TreeBuilder
from xml.parsers import expat

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.entsoe import profile


class ProfileFailure(Exception):
    def __init__(self, code: ErrorCode = ErrorCode.CONTENT_INVALID) -> None:
        self.code = code
        super().__init__(code.value)


def _forbidden(*args: object) -> NoReturn:
    raise ProfileFailure()


def _declaration(version: str, encoding: str | None, standalone: int) -> None:
    if version != "1.0":
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    if encoding is not None and encoding.lower() != "utf-8":
        raise ProfileFailure(ErrorCode.UNSUPPORTED_ENCODING)


def _name(name: str) -> str:
    return "{" + name if "}" in name else name


def parse_xml(content: bytes) -> Element:
    if len(content) > profile.MAX_BYTES:
        raise ProfileFailure()
    # Expat >=2.6.0 fixes quadratic work on unfinished large tokens. Fail closed
    # on older runtimes rather than silently using an unsafe host library.
    if expat.version_info < (2, 6, 0):
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    try:
        content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ProfileFailure(ErrorCode.UNSUPPORTED_ENCODING) from None
    # NUL rules out UTF-16/32 auto-detection even for ASCII-compatible codepoints.
    if b"\x00" in content:
        raise ProfileFailure(ErrorCode.UNSUPPORTED_ENCODING)
    builder = TreeBuilder()
    stack_text: list[int] = []
    elements = total_text = 0

    def start(name: str, attributes: dict[str, str]) -> None:
        nonlocal elements
        elements += 1
        if elements > profile.MAX_ELEMENTS or len(stack_text) >= profile.MAX_DEPTH:
            raise ProfileFailure()
        if len(name) > 256 or len(attributes) > 16:
            raise ProfileFailure()
        if any(len(k) > 256 or len(v) > 256 for k, v in attributes.items()):
            raise ProfileFailure()
        stack_text.append(0)
        builder.start(_name(name), {_name(k): v for k, v in attributes.items()})

    def end(name: str) -> None:
        builder.end(_name(name))
        stack_text.pop()

    def text(data: str) -> None:
        nonlocal total_text
        total_text += len(data)
        if total_text > profile.MAX_TEXT:
            raise ProfileFailure()
        if stack_text:
            stack_text[-1] += len(data)
            if stack_text[-1] > profile.MAX_NODE_TEXT:
                raise ProfileFailure()
        builder.data(data)

    parser = expat.ParserCreate(encoding="UTF-8", namespace_separator="}")
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = text
    parser.XmlDeclHandler = _declaration
    parser.StartDoctypeDeclHandler = _forbidden
    parser.EntityDeclHandler = _forbidden
    parser.ExternalEntityRefHandler = _forbidden
    parser.UnparsedEntityDeclHandler = _forbidden
    parser.NotationDeclHandler = _forbidden
    parser.SkippedEntityHandler = _forbidden
    parser.ProcessingInstructionHandler = _forbidden
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:
        # Small chunks also bound callback delivery work; Expat's patched token
        # handling avoids repeated reparsing of incomplete attribute/name tokens.
        for offset in range(0, len(content), 8192):
            parser.Parse(content[offset : offset + 8192], False)
        parser.Parse(b"", True)
        return builder.close()
    except (expat.ExpatError, ValueError):
        raise ProfileFailure() from None
