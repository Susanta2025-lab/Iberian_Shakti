"""Archive publication, integrity, provenance immutability, and concurrency."""

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import (
    ErrorCode,
    ParseProvenance,
    RawPayload,
    RetrievalResult,
)
from iberian_shakti.ingestion.archive import LocalRawArchive, archive_reference, persist_retrieval
from iberian_shakti.ingestion.errors import ArchiveError, FailureReason, ReplayError
from iberian_shakti.ingestion.replay import replay

from .conftest import EVENT_ID


def change(model, **updates):
    return type(model).model_validate({**model.model_dump(), **updates})


def replace_bytes(path: Path, content: bytes) -> None:
    # Deliberate external corruption; application code never writes this way.
    path.chmod(0o600)
    path.write_bytes(content)


def test_first_write_and_idempotent_reuse(tmp_path, payload, acquisition):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    path = tmp_path / ref.relative_path
    stat = path.stat()
    event = path.parent / "retrievals" / f"{EVENT_ID}.json"
    original_metadata = event.read_bytes()
    assert archive.persist(payload, acquisition) == ref
    assert path.stat().st_ino == stat.st_ino and path.stat().st_mtime_ns == stat.st_mtime_ns
    assert path.read_bytes() == payload.content
    assert event.read_bytes() == original_metadata
    assert list(path.parent.glob(".stage-*")) == []
    assert archive.load(ref) == payload
    stored = archive.load_retrieval(ref, EVENT_ID)
    assert stored.archive == ref and stored.completed_at == acquisition.completed_at
    assert stored.retrieval_event_id == acquisition.retrieval_event_id
    assert len(list(tmp_path.rglob("payload.bin"))) == 1


def test_changed_bytes_same_revision_separately_preserved(tmp_path, payload, acquisition):
    archive = LocalRawArchive(tmp_path)
    first = archive.persist(payload, acquisition)
    content = b"revised bytes"
    raw = change(
        payload.reference, sha256=hashlib.sha256(content).hexdigest(), byte_length=len(content)
    )
    revised = RawPayload(reference=raw, content=content)
    second = archive.persist(
        revised, change(acquisition, raw=raw, retrieval_event_id=UUID(int=103))
    )
    assert first != second
    assert archive.load(first) == payload and archive.load(second) == revised
    assert len(list(tmp_path.rglob("payload.bin"))) == 2


def test_same_bytes_other_revision_new_acquisition(tmp_path, payload, acquisition):
    archive = LocalRawArchive(tmp_path)
    first = archive.persist(payload, acquisition)
    source = change(
        acquisition.source, observed_revision=2, filename="report.2", safe_locator="public/report.2"
    )
    new = change(acquisition, source=source, retrieval_event_id=UUID(int=103))
    assert archive.persist(payload, new) == first
    events = list((tmp_path / first.relative_path).parent.glob("retrievals/*.json"))
    assert len(events) == 2
    assert archive.load_retrieval(first, UUID(int=103)).source.observed_revision == 2
    assert archive.load_retrieval(first, EVENT_ID).source.observed_revision == 1
    assert len(list(tmp_path.rglob("payload.bin"))) == 1


@pytest.mark.parametrize("corruption", [b"wrong", b"", b"x" * 100])
def test_existing_corruption_never_replaced(tmp_path, payload, acquisition, corruption):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    path = tmp_path / ref.relative_path
    replace_bytes(path, corruption)
    with pytest.raises(ArchiveError) as caught:
        archive.persist(payload, acquisition)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE
    assert path.read_bytes() == corruption
    assert not list(tmp_path.rglob(".stage-*"))


@pytest.mark.parametrize("wrong", ["length", "hash"])
def test_load_checks_reference(tmp_path, payload, acquisition, wrong):
    archive = LocalRawArchive(tmp_path)
    original = archive.persist(payload, acquisition)
    raw = change(
        payload.reference,
        **(
            {"byte_length": len(payload.content) + 1} if wrong == "length" else {"sha256": "f" * 64}
        ),
    )
    reference = archive_reference(raw)
    if wrong == "hash":
        destination = tmp_path / reference.relative_path
        destination.parent.mkdir(parents=True)
        destination.write_bytes(payload.content)
    with pytest.raises(ArchiveError) as caught:
        archive.load(reference)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE
    assert archive.load(original) == payload


@pytest.mark.parametrize("operation", ["load", "replay"])
def test_missing_payload(tmp_path, payload, acquisition, operation):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    (tmp_path / ref.relative_path).unlink()
    with pytest.raises(ArchiveError if operation == "load" else ReplayError) as caught:
        archive.load(ref) if operation == "load" else replay(archive, ref, EVENT_ID)
    assert caught.value.code is ErrorCode.ARCHIVE_FAILURE


def test_unreadable_payload_translated(tmp_path, payload, acquisition, monkeypatch):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)

    def denied(*args, **kwargs):
        raise PermissionError("synthetic-secret")

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(ArchiveError) as caught:
        archive.load(ref)
    assert caught.value.reason is FailureReason.UNREADABLE
    assert isinstance(caught.value.__cause__, PermissionError)
    assert "synthetic-secret" not in str(caught.value)


@pytest.mark.parametrize("unsafe", ["../outside", "/tmp/outside", "x/../y", "x//y", "C:\\outside"])
def test_bypassed_archive_paths_rejected(tmp_path, payload, unsafe):
    archive = LocalRawArchive(tmp_path)
    invalid = archive_reference(payload.reference).model_copy(update={"relative_path": unsafe})
    with pytest.raises(ArchiveError) as caught:
        archive.load(invalid)
    assert caught.value.reason is FailureReason.PATH
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("target", ["payload", "directory", "metadata"])
def test_symlinks_rejected(tmp_path, payload, acquisition, target):
    archive = LocalRawArchive(tmp_path / "archive")
    reference = archive_reference(payload.reference)
    outside = tmp_path / "outside"
    outside.mkdir()
    payload_path = archive.root / reference.relative_path
    if target == "directory":
        archive.root.mkdir()
        (archive.root / "synthetic").symlink_to(outside, target_is_directory=True)
    elif target == "payload":
        payload_path.parent.mkdir(parents=True)
        (outside / "other").write_bytes(payload.content)
        payload_path.symlink_to(outside / "other")
    else:
        archive.persist(payload, acquisition)
        event = payload_path.parent / "retrievals" / f"{EVENT_ID}.json"
        event.unlink()
        event.symlink_to(outside / "other")
    with pytest.raises(ArchiveError) as caught:
        archive.persist(payload, acquisition)
    assert caught.value.reason is FailureReason.PATH


def test_atomic_no_clobber_complete_publication(tmp_path, payload, acquisition, monkeypatch):
    real_link = os.link
    destinations = []

    def inspect_link(src, dst, **kwargs):
        assert not Path(dst).exists()
        staged = Path(src)
        assert staged.parent == Path(dst).parent
        if Path(dst).name == "payload.bin":
            assert staged.read_bytes() == payload.content
        else:
            json.loads(staged.read_text(encoding="utf-8"))
        destinations.append(dst)
        return real_link(src, dst, **kwargs)

    monkeypatch.setattr(os, "link", inspect_link)
    archive = LocalRawArchive(tmp_path)
    archive.persist(payload, acquisition)
    assert len(destinations) == 2
    assert not list(tmp_path.rglob(".stage-*"))


@pytest.mark.parametrize("interruption", [OSError, KeyboardInterrupt])
def test_interrupted_staging_cleanup(tmp_path, payload, acquisition, monkeypatch, interruption):
    def interrupt(descriptor, data):
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data[:2])
            raise interruption("synthetic-secret")

    monkeypatch.setattr(LocalRawArchive, "_stage_write", staticmethod(interrupt))
    with pytest.raises(ArchiveError if interruption is OSError else KeyboardInterrupt):
        LocalRawArchive(tmp_path).persist(payload, acquisition)
    assert not list(tmp_path.rglob("payload.bin"))
    assert not list(tmp_path.rglob(".stage-*"))
    assert not list(tmp_path.rglob("*.json"))


def test_concurrent_identical_writers(tmp_path, payload, acquisition, monkeypatch):
    real_link = os.link
    barrier = Barrier(6)

    def race_link(src, dst, **kwargs):
        if Path(dst).name == "payload.bin":
            barrier.wait(timeout=10)
        return real_link(src, dst, **kwargs)

    monkeypatch.setattr(os, "link", race_link)
    archive = LocalRawArchive(tmp_path)

    def write(index):
        return archive.persist(
            payload, change(acquisition, retrieval_event_id=UUID(int=200 + index))
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        refs = list(executor.map(write, range(6)))
    assert len(set(refs)) == 1
    assert archive.load(refs[0]) == payload
    assert len(list(tmp_path.rglob("payload.bin"))) == 1
    assert len(list(tmp_path.rglob("*.json"))) == 6
    assert not list(tmp_path.rglob(".stage-*"))


def test_concurrent_identical_event(tmp_path, payload, acquisition):
    archive = LocalRawArchive(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as executor:
        refs = list(executor.map(lambda _: archive.persist(payload, acquisition), range(8)))
    assert len(set(refs)) == 1
    assert len(list(tmp_path.rglob("*.json"))) == 1
    assert not list(tmp_path.rglob(".stage-*"))


@pytest.mark.parametrize("operation", ["persist", "persist_parse"])
def test_metadata_failure_prevents_success(
    tmp_path, payload, acquisition, parse_event, monkeypatch, operation
):
    archive = LocalRawArchive(tmp_path)
    if operation == "persist_parse":
        archive.persist(payload, acquisition)
    real_link = os.link

    def fail_metadata(src, dst, **kwargs):
        if Path(dst).suffix == ".json":
            raise OSError("disk failure synthetic-secret")
        return real_link(src, dst, **kwargs)

    monkeypatch.setattr(os, "link", fail_metadata)
    with pytest.raises(ArchiveError) as caught:
        if operation == "persist":
            persist_retrieval(RetrievalResult(provenance=acquisition, payload=payload), archive)
        else:
            archive.persist_parse(parse_event)
    assert caught.value.reason is FailureReason.METADATA
    assert "synthetic-secret" not in str(caught.value)
    assert not list(tmp_path.rglob(".stage-*"))
    assert len(list(tmp_path.rglob("payload.bin"))) == 1


def test_permission_failure_is_safe(tmp_path, payload, acquisition, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("password=synthetic-secret")

    monkeypatch.setattr(Path, "mkdir", denied)
    with pytest.raises(ArchiveError) as caught:
        LocalRawArchive(tmp_path).persist(payload, acquisition)
    assert caught.value.reason is FailureReason.PERMISSION
    assert "synthetic-secret" not in repr(caught.value)


def test_conflicting_retrieval_event_rejected(tmp_path, payload, acquisition):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    event = (tmp_path / ref.relative_path).parent / "retrievals" / f"{EVENT_ID}.json"
    before = event.read_bytes()
    with pytest.raises(ArchiveError) as caught:
        archive.persist(payload, change(acquisition, attempt_count=2))
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE
    assert event.read_bytes() == before


def test_parse_idempotency_and_conflict(tmp_path, payload, acquisition, parse_event):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    retrieval_path = (tmp_path / ref.relative_path).parent / "retrievals" / f"{EVENT_ID}.json"
    original = retrieval_path.read_bytes()
    archive.persist_parse(parse_event)
    path = (tmp_path / ref.relative_path).parent / "parses" / f"{parse_event.parse_event_id}.json"
    before = path.read_bytes()
    inode = path.stat().st_ino
    archive.persist_parse(parse_event)
    assert path.stat().st_ino == inode
    assert ParseProvenance.model_validate_json(before) == parse_event
    with pytest.raises(ArchiveError) as caught:
        archive.persist_parse(change(parse_event, parser_version="1.0.1"))
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE
    assert path.read_bytes() == before and retrieval_path.read_bytes() == original


@pytest.mark.parametrize(
    "update",
    [{"archive": None}, {"retrieval_event_id": UUID(int=999)}, {"parse_event_id": EVENT_ID}],
)
def test_parse_requires_persisted_acquisition(tmp_path, payload, acquisition, parse_event, update):
    archive = LocalRawArchive(tmp_path)
    archive.persist(payload, acquisition)
    with pytest.raises(ArchiveError):
        archive.persist_parse(change(parse_event, **update))
    assert not list(tmp_path.rglob("parses/*.json"))


def test_wrong_provenance_before_write(tmp_path, payload, acquisition):
    other_raw = change(payload.reference, sha256="a" * 64)
    with pytest.raises(ArchiveError):
        LocalRawArchive(tmp_path).persist(payload, change(acquisition, raw=other_raw))
    assert not list(tmp_path.iterdir())


def test_offline_replay_preserves_acquisition_and_accepts_parse(
    tmp_path, payload, acquisition, parse_event, monkeypatch
):
    archive = LocalRawArchive(tmp_path)
    stored = persist_retrieval(RetrievalResult(payload=payload, provenance=acquisition), archive)
    ref = stored.provenance.archive
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    replayed = replay(archive, ref, EVENT_ID)
    assert replayed == stored
    assert replayed.provenance.completed_at == acquisition.completed_at
    assert replayed.provenance.retrieval_event_id == acquisition.retrieval_event_id
    archive.persist_parse(parse_event)
    assert all(path.read_bytes() == content for path, content in before.items())


@pytest.mark.parametrize("corruption", [b"different hash", b""])
def test_replay_corruption_fails(tmp_path, payload, acquisition, corruption):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    replace_bytes(tmp_path / ref.relative_path, corruption)
    with pytest.raises(ReplayError) as caught:
        replay(archive, ref, EVENT_ID)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE
    assert caught.value.reason is FailureReason.REPLAY


@pytest.mark.parametrize("metadata", [b"{bad", b"{}", b"\xff", b"[]", b"x" * 65537])
def test_invalid_metadata_rejected_by_contract(tmp_path, payload, acquisition, metadata):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    path = (tmp_path / ref.relative_path).parent / "retrievals" / f"{EVENT_ID}.json"
    replace_bytes(path, metadata)
    with pytest.raises(ReplayError) as caught:
        replay(archive, ref, EVENT_ID)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE


def test_missing_retrieval_event(tmp_path, payload, acquisition):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    with pytest.raises(ReplayError):
        replay(archive, ref, UUID(int=999))


@pytest.mark.parametrize("wrong", ["event", "archive"])
def test_valid_metadata_wrong_linkage(tmp_path, payload, acquisition, wrong):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    stored = archive.load_retrieval(ref, EVENT_ID)
    update = {"retrieval_event_id": UUID(int=999)} if wrong == "event" else {"archive": None}
    other = change(stored, **update)
    path = (tmp_path / ref.relative_path).parent / "retrievals" / f"{EVENT_ID}.json"
    replace_bytes(path, other.model_dump_json().encode())
    with pytest.raises(ArchiveError) as caught:
        archive.load_retrieval(ref, EVENT_ID)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE


def test_event_path_rejects_non_uuid(tmp_path, payload):
    with pytest.raises(ArchiveError):
        LocalRawArchive(tmp_path).load_retrieval(archive_reference(payload.reference), "../escape")


def test_same_length_payload_corruption_fails_hash(tmp_path, payload, acquisition):
    archive = LocalRawArchive(tmp_path)
    reference = archive.persist(payload, acquisition)
    replace_bytes(tmp_path / reference.relative_path, b"x" * len(payload.content))
    with pytest.raises(ReplayError) as caught:
        replay(archive, reference, EVENT_ID)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE


def test_concurrent_conflicting_event_has_one_immutable_winner(tmp_path, payload, acquisition):
    archive = LocalRawArchive(tmp_path)

    def write(index):
        try:
            archive.persist(payload, change(acquisition, attempt_count=index + 1))
            return "success"
        except ArchiveError as error:
            assert error.code is ErrorCode.INTEGRITY_FAILURE
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(write, range(2)))
    assert sorted(outcomes) == ["conflict", "success"]
    ref = archive_reference(payload.reference)
    assert archive.load_retrieval(ref, EVENT_ID).attempt_count in {1, 2}
    assert archive.load(ref) == payload
    assert not list(tmp_path.rglob(".stage-*"))
