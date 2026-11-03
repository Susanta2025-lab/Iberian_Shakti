"""Hostile synthetic bytes pass through the actual production XML/parser boundary."""

import builtins
from xml.parsers import expat

import pytest
from test_entsoe_parser import BODY, failed, parse

from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.entsoe.xml_boundary import ProfileFailure, parse_xml


@pytest.mark.parametrize(
    "declaration",
    [
        b"<!DOCTYPE GL_MarketDocument>",
        b'<!DOCTYPE GL_MarketDocument SYSTEM "file:///etc/passwd">',
        b'<!DOCTYPE GL_MarketDocument SYSTEM "https://xml-resource.invalid/evil.dtd">',
        b'<!DOCTYPE GL_MarketDocument [<!ENTITY x "attack">]>',
        b'<!DOCTYPE GL_MarketDocument [<!ENTITY x SYSTEM "file:///etc/passwd">]>',
        b'<!DOCTYPE GL_MarketDocument [<!ENTITY % x SYSTEM "https://xml-resource.invalid/evil.dtd">%x;]>',
        b'<!DOCTYPE GL_MarketDocument [<!ENTITY a "0123456789"><!ENTITY b "&a;&a;&a;&a;">]>',
    ],
)
def test_doctype_entities_external_resource_and_expansion_fail_before_access(
    monkeypatch, declaration
):
    def forbidden(*args, **kwargs):
        pytest.fail("XML attempted filesystem resource access")

    monkeypatch.setattr(builtins, "open", forbidden)
    body = BODY.replace(b"?>", b"?>" + declaration, 1).replace(b"23000.12300", b"&x;", 1)
    with pytest.raises(ProfileFailure):
        parse_xml(body)
    failed(parse(body), ErrorCode.CONTENT_INVALID)


@pytest.mark.parametrize(
    "body",
    [
        b'<!ENTITY x SYSTEM "file:///etc/passwd"><x>&x;</x>',
        b"<a>&undeclared;</a>",
        b"<a><b></a>",
        b'<a attr="duplicate" attr="duplicate"/>',
        BODY.replace(b"?>", b'?><?xml-stylesheet href="file:///etc/passwd"?>', 1),
    ],
)
def test_malformed_xml_and_processing_instructions_are_inert_failures(body):
    failed(parse(body), ErrorCode.CONTENT_INVALID)


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-16-be", "utf-32", "latin-1"])
def test_non_utf8_bytes_rejected_without_auto_detection(encoding):
    body = BODY.decode().replace("synthetic-load", "synthetic-é-load").encode(encoding)
    failed(parse(body), ErrorCode.UNSUPPORTED_ENCODING)


@pytest.mark.parametrize("encoding", ["UTF-16", "UTF-32", "ISO-8859-1", "US-ASCII"])
def test_even_ascii_document_cannot_declare_unsupported_encoding(encoding):
    failed(parse(BODY.replace(b"UTF-8", encoding.encode(), 1)), ErrorCode.UNSUPPORTED_ENCODING)


def test_utf8_bom_and_absent_declaration_are_explicitly_supported():
    assert parse(b"\xef\xbb\xbf" + BODY).provenance.outcome is ParseOutcome.SUCCESS
    assert parse(BODY.split(b"?>", 1)[1]).provenance.outcome is ParseOutcome.SUCCESS


def test_xml_version_is_explicit():
    failed(parse(BODY.replace(b'version="1.0"', b'version="1.1"')), ErrorCode.SCHEMA_UNSUPPORTED)


@pytest.mark.parametrize(
    "body",
    [
        b"<a>" * (profile.MAX_DEPTH + 1) + b"</a>" * (profile.MAX_DEPTH + 1),
        b"<root>" + b"<a/>" * profile.MAX_ELEMENTS + b"</root>",
        b"<a>" + b"x" * (profile.MAX_NODE_TEXT + 1) + b"</a>",
        b"<a>" + b"&#120;" * (profile.MAX_NODE_TEXT + 1) + b"</a>",
        b"x" * (profile.MAX_BYTES + 1),
        b"<a " + b" ".join(f'a{i}="x"'.encode() for i in range(17)) + b"/>",
        b'<a attr="' + b"x" * 257 + b'"/>',
        b"<" + b"x" * 257 + b"/>",
    ],
    ids=lambda value: f"synthetic-{len(value)}-bytes",
)
def test_real_depth_count_text_bytes_and_attribute_limits(body):
    with pytest.raises(ProfileFailure):
        parse_xml(body)
    failed(parse(body))


def test_cumulative_text_limit_is_enforced_before_tree_growth(monkeypatch):
    monkeypatch.setattr(profile, "MAX_TEXT", 30)
    body = b"<a>" + b"<b>1234567890</b>" * 4 + b"</a>"
    with pytest.raises(ProfileFailure):
        parse_xml(body)
    failed(parse(body))


def test_fragmented_character_callbacks_cannot_bypass_per_node_limit():
    body = b"<a>" + b"&amp;" * (profile.MAX_NODE_TEXT + 1) + b"</a>"
    with pytest.raises(ProfileFailure):
        parse_xml(body)


def test_older_expat_fails_closed(monkeypatch):
    monkeypatch.setattr(expat, "version_info", (2, 5, 0))
    failed(parse(), ErrorCode.SCHEMA_UNSUPPORTED)


@pytest.mark.parametrize("bound,value", [("MAX_SERIES", 0), ("MAX_PERIODS", 1), ("MAX_RECORDS", 2)])
def test_semantic_series_period_and_normalization_work_limits(monkeypatch, bound, value):
    monkeypatch.setattr(profile, bound, value)
    failed(parse())
