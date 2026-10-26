"""Validated local settings; construction never opens files or makes requests."""

import os
import re
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from iberian_shakti.common.logging import LogLevel


class ConfigurationError(ValueError):
    """Invalid settings, with field names only and no rejected input values."""

    code = "invalid_configuration"


class IngestionSettings(BaseModel):
    """Minimal frozen settings, independent of other provider credentials.

    Relative archive roots are relative to the process working directory.
    Paths are not resolved, inspected, or created here. Model validation hides
    input in error text; use the loader's ConfigurationError for diagnostics,
    never raw ValidationError.errors() (which can contain rejected inputs).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    raw_archive_root: Path = Path("data/raw")
    timeout_seconds: float = Field(default=10.0, gt=0, allow_inf_nan=False)
    max_attempts: int = Field(default=3, gt=0, strict=True)
    backoff_seconds: float = Field(default=1.0, ge=0, allow_inf_nan=False)
    log_level: LogLevel = LogLevel.INFO

    @field_validator("raw_archive_root", mode="before")
    @classmethod
    def validate_archive_root(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("Archive root must be nonempty")
        return value

    @field_validator("timeout_seconds", "backoff_seconds", mode="before")
    @classmethod
    def validate_numeric_type(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Expected a number")
        return value

    @field_validator("max_attempts", mode="before")
    @classmethod
    def parse_attempts(cls, value: object) -> object:
        if isinstance(value, str):
            if not re.fullmatch(r"[0-9]+", value, flags=re.ASCII):
                raise ValueError("Expected a positive integer")
            return int(value)
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


_ENVIRONMENT_FIELDS: dict[str, str] = {
    "RAW_ARCHIVE_ROOT": "raw_archive_root",
    "INGESTION_TIMEOUT_SECONDS": "timeout_seconds",
    "INGESTION_MAX_ATTEMPTS": "max_attempts",
    "INGESTION_BACKOFF_SECONDS": "backoff_seconds",
    "LOG_LEVEL": "log_level",
}


def load_ingestion_settings(environ: Mapping[str, str] | None = None) -> IngestionSettings:
    """Read only ingestion settings; an injected empty mapping uses defaults.

    No .env loading, provider credential reads, I/O, or logging setup occurs.
    Errors deliberately discard Pydantic input/context before presentation.
    """
    environment = os.environ if environ is None else environ
    values = {
        field: environment[name]
        for name, field in _ENVIRONMENT_FIELDS.items()
        if name in environment
    }
    try:
        return IngestionSettings.model_validate(values)
    except ValidationError as error:
        fields = sorted(
            {
                str(item["loc"][0])
                for item in error.errors(include_input=False, include_context=False)
            }
        )
        raise ConfigurationError("Invalid ingestion settings: " + ", ".join(fields)) from None
