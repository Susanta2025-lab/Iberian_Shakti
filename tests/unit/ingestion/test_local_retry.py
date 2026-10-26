"""Local exact-byte retrieval and finite policy settings, without HTTP or writes."""

import hashlib
from pathlib import Path

import httpx
import pytest

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.archive import LocalRawArchive
from iberian_shakti.ingestion.config import IngestionSettings
from iberian_shakti.ingestion.errors import ExecutionError, FailureReason
from iberian_shakti.ingestion.retrieval import LocalFileRetriever, contained_path
from iberian_shakti.ingestion.retry import RetryPolicy

from .conftest import ACQUIRED_AT, EVENT_ID


@pytest.mark.parametrize("content", [b"line\n", b"line\r\n", b"\xff\x00\x80", b""])
def test_local_exact_bytes_no_http_no_archive(tmp_path, source, content, monkeypatch):
    input_root = tmp_path / "input"
    input_file = input_root / source.safe_locator
    input_file.parent.mkdir(parents=True)
    input_file.write_bytes(content)

    def forbidden(*args, **kwargs):
        raise AssertionError("No HTTP dependency")

    monkeypatch.setattr(httpx.Client, "__init__", forbidden)
    result = LocalFileRetriever(
        input_root, retrieval_event_id=EVENT_ID, now=lambda: ACQUIRED_AT
    ).retrieve(source)
    assert result.payload.content == content
    assert result.payload.reference.sha256 == hashlib.sha256(content).hexdigest()
    assert result.payload.reference.byte_length == len(content)
    assert result.provenance.http_status is None and result.provenance.http is None
    assert result.provenance.archive is None
    assert result.provenance.completed_at == ACQUIRED_AT
    assert not (tmp_path / "archive").exists()


def test_local_missing(tmp_path, source):
    with pytest.raises(ExecutionError) as caught:
        LocalFileRetriever(tmp_path, retrieval_event_id=EVENT_ID).retrieve(source)
    assert caught.value.code is ErrorCode.LOCAL_FAILURE
    assert caught.value.reason is FailureReason.MISSING


def test_local_unreadable(tmp_path, source, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("synthetic-secret")

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(ExecutionError) as caught:
        LocalFileRetriever(tmp_path, retrieval_event_id=EVENT_ID).retrieve(source)
    assert caught.value.reason is FailureReason.UNREADABLE
    assert isinstance(caught.value.__cause__, PermissionError)
    assert "synthetic-secret" not in str(caught.value)


@pytest.mark.parametrize(
    "path",
    [
        "../x",
        "/tmp/x",
        "x/../y",
        "x//y",
        "file:///tmp/x",
        "https://example.invalid/x",
        "C:\\x",
        "x\x00y",
    ],
)
def test_local_path_rejection(tmp_path, path):
    with pytest.raises(ExecutionError) as caught:
        contained_path(tmp_path, path)
    assert caught.value.reason is FailureReason.PATH


def test_local_symlink_rejection(tmp_path, source):
    target = tmp_path / "target"
    target.write_bytes(b"test")
    file = tmp_path / source.safe_locator
    file.parent.mkdir()
    file.symlink_to(target)
    with pytest.raises(ExecutionError) as caught:
        LocalFileRetriever(tmp_path, retrieval_event_id=EVENT_ID).retrieve(source)
    assert caught.value.reason is FailureReason.PATH


def test_local_limit(tmp_path, source):
    file = tmp_path / source.safe_locator
    file.parent.mkdir()
    file.write_bytes(b"12345")
    with pytest.raises(ExecutionError) as caught:
        LocalFileRetriever(tmp_path, retrieval_event_id=EVENT_ID, max_bytes=4).retrieve(source)
    assert caught.value.code is ErrorCode.SIZE_LIMIT


@pytest.mark.parametrize(
    "updates",
    [
        {"max_attempts": 0},
        {"max_attempts": True},
        {"max_attempts": 1.5},
        {"backoff_seconds": -1},
        {"backoff_seconds": float("inf")},
        {"backoff_seconds": True},
        {"phase_timeout_seconds": 0},
        {"phase_timeout_seconds": float("nan")},
        {"attempt_timeout_seconds": -1},
        {"operation_timeout_seconds": float("inf")},
        {"backoff_cap_seconds": 0},
    ],
)
def test_invalid_policy(updates):
    with pytest.raises(ExecutionError) as caught:
        RetryPolicy(**updates)
    assert caught.value.reason is FailureReason.CONFIGURATION


def test_settings_used_and_saturating_backoff():
    settings = IngestionSettings(max_attempts=5, backoff_seconds=0.5, timeout_seconds=2)
    policy = RetryPolicy.from_settings(settings)
    assert policy.max_attempts == 5 and policy.phase_timeout_seconds == 2
    assert [policy.delay(i) for i in range(1, 7)] == [0.5, 1, 2, 4, 4, 4]
    assert policy.delay(10**20) == 4
    assert RetryPolicy(backoff_seconds=0).delay(10**20) == 0
    assert LocalRawArchive.from_settings(settings).root == Path("data/raw")


@pytest.mark.parametrize("size", [0, -1, True, 1.5])
def test_invalid_size_configuration(tmp_path, size):
    with pytest.raises(ExecutionError):
        LocalFileRetriever(tmp_path, retrieval_event_id=EVENT_ID, max_bytes=size)


@pytest.mark.parametrize("event_id", ["not-a-uuid", None, 1])
def test_invalid_event_identity_before_io(tmp_path, event_id):
    from iberian_shakti.ingestion.http import HttpRetriever

    with pytest.raises(ExecutionError):
        LocalFileRetriever(tmp_path, retrieval_event_id=event_id)
    with pytest.raises(ExecutionError):
        HttpRetriever(lambda _: "https://example.invalid/report", retrieval_event_id=event_id)
