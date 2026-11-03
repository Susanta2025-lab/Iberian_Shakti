"""Strict acknowledgement v7 subset; controlled categories, never provider text.

999 means unspecified error, not no-data by itself. Only the exact documented
reason context below is recognized. Unknown/mixed variants remain unsupported;
raw bytes retain all reasons for later authorized analysis and replay.
"""

from dataclasses import dataclass
from enum import StrEnum
from xml.etree.ElementTree import Element

from iberian_shakti.contracts.ingestion import ErrorCode, ParseOutcome
from iberian_shakti.ingestion.entsoe import profile
from iberian_shakti.ingestion.entsoe.schema import (
    _PARTICIPANTS,
    field,
    identifier,
    participants,
    shape,
    tag,
    timestamp,
)
from iberian_shakti.ingestion.entsoe.xml_boundary import ProfileFailure


class AckCategory(StrEnum):
    NO_DATA = "no_matching_data"
    INVALID_REQUEST = "invalid_request"
    TECHNICAL = "technical_or_volume_rejection"
    AUTHENTICATION = "authentication_failure"
    AUTHORIZATION = "authorization_failure"
    DOMAIN = "unsupported_domain"
    UNSUPPORTED = "unsupported_acknowledgement"


@dataclass(frozen=True)
class Acknowledgement:
    category: AckCategory

    @property
    def outcome(self) -> ParseOutcome:
        return (
            ParseOutcome.SOURCE_UNAVAILABLE
            if self.category is AckCategory.NO_DATA
            else ParseOutcome.PROVIDER_REJECTED
        )

    @property
    def code(self) -> ErrorCode:
        return {
            AckCategory.NO_DATA: ErrorCode.NO_DATA,
            AckCategory.AUTHENTICATION: ErrorCode.AUTHENTICATION_FAILURE,
            AckCategory.AUTHORIZATION: ErrorCode.AUTHORIZATION_FAILURE,
            AckCategory.DOMAIN: ErrorCode.UNSUPPORTED_DOMAIN,
        }.get(self.category, ErrorCode.PROVIDER_REJECTED)


# Exact contexts from official Query Response / Rejection of Request pages.
# No substring/keyword matching against arbitrary provider prose.
_CONTEXTS = {
    "No matching data found": AckCategory.NO_DATA,
    "Invalid query attributes or parameters": AckCategory.INVALID_REQUEST,
    "More than 100 matching documents": AckCategory.TECHNICAL,
    "Unauthorized. Missing or invalid security token": AckCategory.AUTHENTICATION,
}
# Common code-list meanings; these are supported possibilities, not evidence
# that this API has returned these codes for our three products.
_CODES = {
    "A04": AckCategory.INVALID_REQUEST,  # Time interval incorrect
    "A05": AckCategory.AUTHORIZATION,  # Sender without valid contract
    "A23": AckCategory.DOMAIN,  # Area invalid
    "A41": AckCategory.INVALID_REQUEST,  # Resolution inconsistency
    "A94": AckCategory.TECHNICAL,  # Document cannot be processed by receiver
    "B18": AckCategory.TECHNICAL,  # Failure
}


def validate_acknowledgement(root: Element) -> Acknowledgement:
    namespace = profile.ACK_NAMESPACE
    shape(
        root,
        {"mRID", "createdDateTime", "received_MarketDocument.createdDateTime"} | _PARTICIPANTS,
        frozenset({"Reason"}),
        namespace=namespace,
    )
    identifier(field(root, "mRID", namespace))
    timestamp(field(root, "createdDateTime", namespace))
    participants(root, namespace)
    if root.find(tag("received_MarketDocument.createdDateTime", namespace)) is not None:
        timestamp(field(root, "received_MarketDocument.createdDateTime", namespace))
    reasons = root.findall(tag("Reason", namespace))
    if not 0 < len(reasons) <= 16:
        raise ProfileFailure(ErrorCode.SCHEMA_UNSUPPORTED)
    categories: set[AckCategory] = set()
    for reason in reasons:
        shape(reason, {"code", "text"}, namespace=namespace)
        code = field(reason, "code", namespace)
        context = (
            field(reason, "text", namespace)
            if reason.find(tag("text", namespace)) is not None
            else None
        )
        category = _CODES.get(code, AckCategory.UNSUPPORTED)
        if code == "999":
            category = _CONTEXTS.get(context or "", AckCategory.UNSUPPORTED)
        categories.add(category)
    return Acknowledgement(
        next(iter(categories)) if len(categories) == 1 else AckCategory.UNSUPPORTED
    )
