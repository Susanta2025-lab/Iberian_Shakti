"""Shared validation primitives; no provider policy or I/O.

Validation error text hides rejected inputs. Callers must not log structured
ValidationError.errors() or whole models: those APIs can still contain inputs.
Frozen models must also use immutable field types. Pydantic's model_construct
and model_copy(update=...) bypass validation and are not ingestion boundaries;
validate new data with model_validate/model_validate_json instead.
"""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

type IngestionContractVersion = Literal["1.0.0"]
type ParseProvenanceContractVersion = Literal["1.0.0"]
type MarketSchemaVersion = Literal["1.0.0"]

INGESTION_CONTRACT_VERSION: IngestionContractVersion = "1.0.0"
PARSE_PROVENANCE_CONTRACT_VERSION: ParseProvenanceContractVersion = "1.0.0"
MARKET_SCHEMA_VERSION: MarketSchemaVersion = "1.0.0"


class FrozenContract(BaseModel):
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        validate_default=True,
        hide_input_in_errors=True,
    )


Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")]
Version = Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
PositiveInt = Annotated[int, Field(gt=0)]
NonnegativeInt = Annotated[int, Field(ge=0)]
Filename = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")]


def _relative_reference(value: str) -> str:
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Reference must contain safe relative components")
    return value


# Deliberately an opaque public identifier, not a transport URL. Adapters own
# mapping it to requests (and private credentials) outside persisted contracts.
# This excludes userinfo, queries, fragments, percent escapes and signed URLs.
SafeReference = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,511}$"),
    AfterValidator(_relative_reference),
]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("Timestamp must be aware and have UTC offset zero")
    return value


UtcDatetime = Annotated[datetime, AfterValidator(_utc)]
