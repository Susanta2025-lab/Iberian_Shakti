"""Narrow Stage 4 catalogue; authoritative references are retained in the report.

Area roles follow the Generation/Load dependency tables, not country-name
inference. Supported historical schema codes are not claims of live coverage.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from iberian_shakti.contracts.geography import Area, AreaRole
from iberian_shakti.contracts.measurements import ValueKind

SOURCE_ID = "entsoe"
PROFILE_VERSION = "0.1.0"
PARSER_ID = "entsoe.generation-load"
PARSER_VERSION = "0.1.0"
ORIGIN = "https://web-api.tp.entsoe.eu"
ENDPOINT_PATH = "/api"
GL_NAMESPACE = "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"
ACK_NAMESPACE = "urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0"
MAX_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 32
MAX_ELEMENTS = 100_000
MAX_TEXT = 2 * 1024 * 1024
MAX_NODE_TEXT = 4096
MAX_SERIES = 100
MAX_PERIODS = 64
MAX_RECORDS = 20_000
MAX_DOCUMENT_DURATION = timedelta(hours=25)
RESOLUTIONS = {"PT15M": 900, "PT30M": 1800, "PT60M": 3600}
# Explicit, reversible PSR mapping; no fallback to 'other'.
TECHNOLOGIES = {"B16": "solar", "B18": "wind_offshore", "B19": "wind_onshore"}
DOMAINS = {"ES": "10YES-REE------0", "PT": "10YPT-REN------W"}

type Product = Literal["actual_load", "wind_solar_forecast"]
type Country = Literal["ES", "PT"]


@dataclass(frozen=True)
class ProductProfile:
    product: Product
    country: Country
    document_type: str
    process_type: str
    domain_parameter: str
    area: Area
    kind: ValueKind

    @property
    def report_id(self) -> str:
        return f"{self.product}.{self.document_type}.{self.process_type}.v{PROFILE_VERSION}"


def product_profile(product: Product, country: Country) -> ProductProfile:
    if country not in DOMAINS or product not in {"actual_load", "wind_solar_forecast"}:
        raise ValueError("Unsupported Stage 4 selection")
    load = product == "actual_load"
    if load and country != "ES":
        raise ValueError("Unsupported Stage 4 selection")
    return ProductProfile(
        product=product,
        country=country,
        document_type="A65" if load else "A69",
        process_type="A16" if load else "A01",
        domain_parameter="outBiddingZone_Domain" if load else "in_Domain",
        area=Area(
            role=AreaRole.BIDDING_ZONE,
            project_id=f"{country}.entsoe_bidding_zone",
            country_code=country,
            native_id=DOMAINS[country],
            native_scheme="eic",
        ),
        kind=ValueKind.ACTUAL if load else ValueKind.FORECAST,
    )


PROFILES = (
    product_profile("actual_load", "ES"),
    product_profile("wind_solar_forecast", "PT"),
    product_profile("wind_solar_forecast", "ES"),
)
