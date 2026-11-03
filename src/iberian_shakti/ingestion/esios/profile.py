"""Stage 3 product policy from the accepted prompt and retained readiness §F.

No authenticated catalogue IDs for geography/magnitude/time are asserted here.
Those native IDs belong to the returned document, not a guessed lookup table.
"""

from iberian_shakti.contracts.geography import Area, AreaRole

SOURCE_ID = "esios"
INDICATOR_ID = 544
NAME = "Demanda prevista Peninsular"
PROFILE_VERSION = "0.1.0"
PARSER_ID = "esios.indicator544"
PARSER_VERSION = "0.1.0"
REPORT_ID = "indicator544.v0.1.0"
ORIGIN = "https://api.esios.ree.es"
ENDPOINT_PATH = "/indicators/544"
MAX_BYTES = 2 * 1024 * 1024
MAX_VALUES = 2000
MAX_GEOS = 32
CADENCE_SECONDS = 300
AREA = Area(
    role=AreaRole.SYSTEM,
    project_id="ES.peninsular",
    country_code="ES",
    perimeter="mainland",
)
