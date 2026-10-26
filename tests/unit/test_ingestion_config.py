"""Deterministic configuration validation, independent of credentials and I/O."""

import builtins
import socket
from collections.abc import Iterator, Mapping
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError

from iberian_shakti.common.logging import LogLevel
from iberian_shakti.ingestion.config import (
    ConfigurationError,
    IngestionSettings,
    load_ingestion_settings,
)


def test_defaults() -> None:
    settings = load_ingestion_settings({})
    assert settings.raw_archive_root == Path("data/raw")
    assert settings.timeout_seconds == 10.0
    assert settings.max_attempts == 3
    assert settings.backoff_seconds == 1.0
    assert settings.log_level is LogLevel.INFO


def test_environment_overrides() -> None:
    settings = load_ingestion_settings(
        {
            "RAW_ARCHIVE_ROOT": "/tmp/stage1-archive",
            "INGESTION_TIMEOUT_SECONDS": "2.5",
            "INGESTION_MAX_ATTEMPTS": "5",
            "INGESTION_BACKOFF_SECONDS": "0.25",
            "LOG_LEVEL": " debug ",
        }
    )
    assert settings.raw_archive_root == Path("/tmp/stage1-archive")
    assert settings.timeout_seconds == 2.5
    assert settings.max_attempts == 5
    assert settings.backoff_seconds == 0.25
    assert settings.log_level is LogLevel.DEBUG


@pytest.mark.parametrize(
    ("name", "value", "field"),
    [
        ("INGESTION_TIMEOUT_SECONDS", value, "timeout_seconds")
        for value in ("", "bad", "0", "-1", "nan", "inf", "-inf", "1e999")
    ]
    + [
        ("INGESTION_MAX_ATTEMPTS", value, "max_attempts")
        for value in ("", "bad", "0", "-1", "1.5", "3.0", "nan", "inf", "1e2", "true")
    ]
    + [
        ("INGESTION_BACKOFF_SECONDS", value, "backoff_seconds")
        for value in ("", "bad", "-1", "nan", "inf", "-inf", "1e999")
    ]
    + [("LOG_LEVEL", value, "log_level") for value in ("", "TRACE", "NOTSET", "20")]
    + [("RAW_ARCHIVE_ROOT", value, "raw_archive_root") for value in ("", " ")],
)
def test_invalid_settings(name: str, value: str, field: str) -> None:
    with pytest.raises(ConfigurationError, match=field) as caught:
        load_ingestion_settings({name: value})
    assert caught.value.code == "invalid_configuration"


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_supported_log_levels(level: str) -> None:
    assert load_ingestion_settings({"LOG_LEVEL": level}).log_level == level


def test_zero_backoff_and_one_total_attempt_are_valid() -> None:
    settings = load_ingestion_settings(
        {"INGESTION_BACKOFF_SECONDS": "0", "INGESTION_MAX_ATTEMPTS": "1"}
    )
    assert settings.backoff_seconds == 0
    assert settings.max_attempts == 1


def test_injected_environment_does_not_fall_back_to_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INGESTION_TIMEOUT_SECONDS", "invalid-process-value")
    assert load_ingestion_settings({}).timeout_seconds == 10
    assert load_ingestion_settings({"INGESTION_TIMEOUT_SECONDS": "7"}).timeout_seconds == 7
    with pytest.raises(ConfigurationError):
        load_ingestion_settings()
    monkeypatch.setenv("INGESTION_TIMEOUT_SECONDS", "8")
    assert load_ingestion_settings().timeout_seconds == 8


def test_only_ingestion_keys_are_read() -> None:
    class RestrictedEnvironment(Mapping[str, str]):
        def __getitem__(self, key: str) -> str:
            if key.startswith(("ESIOS", "ENTSOE", "SNOWFLAKE")):
                raise AssertionError("Unrelated credential was read")
            raise KeyError(key)

        def __iter__(self) -> Iterator[str]:
            raise AssertionError("The whole environment was enumerated")

        def __len__(self) -> int:
            raise AssertionError("The whole environment was inspected")

    assert load_ingestion_settings(RestrictedEnvironment()) == IngestionSettings()


def test_unrelated_credentials_are_optional_and_ignored() -> None:
    assert load_ingestion_settings(
        {"ESIOS_API_TOKEN": "", "ENTSOE_API_TOKEN": "", "SNOWFLAKE_ACCOUNT": ""}
    ) == load_ingestion_settings({})


def test_construction_does_no_io(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive = tmp_path / "uncreated"
    forbidden = Mock(side_effect=AssertionError("Unexpected I/O"))
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        for method in ("open", "mkdir", "stat", "resolve", "read_text", "read_bytes"):
            patch.setattr(Path, method, forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(httpx.Client, "request", forbidden)
        settings = load_ingestion_settings({"RAW_ARCHIVE_ROOT": str(archive)})
        assert settings.raw_archive_root == archive
        assert IngestionSettings().raw_archive_root == Path("data/raw")
        with pytest.raises(ConfigurationError):
            load_ingestion_settings({"INGESTION_TIMEOUT_SECONDS": "bad"})
    forbidden.assert_not_called()
    assert not archive.exists()


def test_no_automatic_dotenv_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("INGESTION_TIMEOUT_SECONDS=not-valid\n")
    monkeypatch.chdir(tmp_path)
    assert load_ingestion_settings({}).timeout_seconds == 10


def test_errors_do_not_display_rejected_values() -> None:
    synthetic_secret = "synthetic-config-secret-123"
    with pytest.raises(ConfigurationError) as caught:
        load_ingestion_settings({"INGESTION_TIMEOUT_SECONDS": synthetic_secret})
    assert synthetic_secret not in str(caught.value)
    assert synthetic_secret not in repr(caught.value)
    assert caught.value.__suppress_context__
    with pytest.raises(ValidationError) as model_error:
        IngestionSettings.model_validate({"timeout_seconds": synthetic_secret})
    assert synthetic_secret not in str(model_error.value)


@pytest.mark.parametrize("field", ["timeout_seconds", "max_attempts", "backoff_seconds"])
def test_model_rejects_boolean_numbers(field: str) -> None:
    with pytest.raises(ValidationError):
        IngestionSettings.model_validate({field: True})


def test_settings_are_frozen_and_reject_unknown_fields() -> None:
    settings = load_ingestion_settings({})
    with pytest.raises(ValidationError):
        settings.max_attempts = 9
    with pytest.raises(ValidationError):
        IngestionSettings.model_validate({"provider_password": "synthetic-unused-password"})
