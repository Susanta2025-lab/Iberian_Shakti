"""Fault injection, explicit recovery, and immutable concurrent event publication."""

import json
import os
import stat
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import UUID

import pytest

from iberian_shakti.contracts.ingestion import ErrorCode
from iberian_shakti.ingestion.archive import LocalRawArchive, archive_reference
from iberian_shakti.ingestion.errors import ArchiveError, FailureReason, ReplayError
from iberian_shakti.ingestion.replay import replay
from iberian_shakti.ingestion.retrieval import result_for

from .conftest import ACQUIRED_AT, EVENT_ID
from .test_archive import change, replace_bytes


def snapshot(root):
    return {p: (p.read_bytes(), p.stat().st_ino) for p in root.rglob("*") if p.is_file()}


def assert_preserved(before):
    assert all((p.read_bytes(), p.stat().st_ino) == value for p, value in before.items())


def inject_fault(patch, fault):
    def fail(*args, **kwargs):
        raise OSError("password=synthetic-archive-secret")

    if fault == "mkdir":
        patch.setattr(Path, "mkdir", fail)
    elif fault == "mkstemp":
        patch.setattr(tempfile, "mkstemp", fail)
    elif fault in {"write", "flush"}:
        real_fdopen = os.fdopen

        class BrokenStream:
            def __init__(self, descriptor, mode):
                self.stream = real_fdopen(descriptor, mode)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def write(self, data):
                if fault == "write":
                    self.stream.write(data[:2])
                    fail()
                return self.stream.write(data)

            def flush(self):
                fail()

        patch.setattr(os, "fdopen", BrokenStream)
    elif fault in {"file_fsync", "directory_fsync"}:
        real_fsync = os.fsync

        def fsync(descriptor):
            directory = stat.S_ISDIR(os.fstat(descriptor).st_mode)
            if directory == (fault == "directory_fsync"):
                fail()
            return real_fsync(descriptor)

        patch.setattr(os, "fsync", fsync)
    elif fault == "fchmod":
        patch.setattr(os, "fchmod", fail)
    elif fault == "link":
        patch.setattr(os, "link", fail)
    else:
        raise AssertionError("Unknown injected fault")


@pytest.mark.parametrize("target", ["payload", "retrievals", "parses"])
@pytest.mark.parametrize(
    "fault",
    ["mkdir", "mkstemp", "write", "flush", "file_fsync", "directory_fsync", "fchmod", "link"],
)
def test_publication_faults_prevent_success_and_allow_explicit_recovery(
    tmp_path, payload, acquisition, parse_event, monkeypatch, target, fault
):
    archive = LocalRawArchive(tmp_path)
    if target == "parses":
        archive.persist(payload, acquisition)
    before = snapshot(tmp_path)
    original = archive._publish

    def publish(path, data, *, metadata):
        selected = path.name == "payload.bin" if target == "payload" else path.parent.name == target
        if selected:
            with monkeypatch.context() as patch:
                inject_fault(patch, fault)
                return original(path, data, metadata=metadata)
        return original(path, data, metadata=metadata)

    with monkeypatch.context() as patch:
        patch.setattr(archive, "_publish", publish)
        with pytest.raises(ArchiveError) as caught:
            if target == "parses":
                archive.persist_parse(parse_event)
            else:
                archive.persist(payload, acquisition)
    assert caught.value.code is ErrorCode.ARCHIVE_FAILURE
    assert caught.value.reason is (
        FailureReason.ARCHIVE_IO if target == "payload" else FailureReason.METADATA
    )
    assert "synthetic-archive-secret" not in str(caught.value)
    assert_preserved(before)
    assert not list(tmp_path.rglob(".stage-*"))
    # Directory fsync can fail after atomic publication: an exception still
    # prevents success. Explicit recovery verifies and reuses complete objects.
    failed_state = snapshot(tmp_path)
    ref = archive.persist(payload, acquisition)
    archive.persist_parse(parse_event)
    assert_preserved(failed_state)
    assert archive.load(ref) == payload
    assert archive.load_retrieval(ref, EVENT_ID).archive == ref
    assert len(list(tmp_path.rglob("payload.bin"))) == 1
    assert len(list(tmp_path.rglob("retrievals/*.json"))) == 1
    assert len(list(tmp_path.rglob("parses/*.json"))) == 1


@pytest.mark.parametrize("existing_payload", [False, True])
def test_abandoned_staging_is_never_a_complete_object(
    tmp_path, payload, acquisition, parse_event, existing_payload
):
    archive = LocalRawArchive(tmp_path)
    ref = archive_reference(payload.reference)
    path = tmp_path / ref.relative_path
    path.parent.mkdir(parents=True)
    staged = path.parent / ".stage-abandoned"
    staged.write_bytes(payload.content[:2])
    if existing_payload:
        archive.persist(payload, acquisition)
        before = snapshot(tmp_path)
        assert replay(archive, ref, EVENT_ID).payload == payload
        assert_preserved(before)
    else:
        with pytest.raises(ArchiveError) as caught:
            archive.load(ref)
        assert caught.value.reason is FailureReason.MISSING
        with pytest.raises(ArchiveError):
            archive.persist_parse(parse_event)
        assert not list(tmp_path.rglob("*.json"))
    archive.persist(payload, acquisition)
    archive.persist_parse(parse_event)
    assert archive.load(ref) == payload
    assert staged.read_bytes() == payload.content[:2]


def test_interruption_cannot_damage_existing_payload(tmp_path, payload, acquisition, monkeypatch):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    before = snapshot(tmp_path)

    def interrupt(descriptor, data):
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(b"partial")
            raise KeyboardInterrupt()

    with monkeypatch.context() as patch:
        patch.setattr(archive, "_stage_write", interrupt)
        with pytest.raises(KeyboardInterrupt):
            archive.persist(payload, change(acquisition, retrieval_event_id=UUID(int=900)))
    assert_preserved(before)
    assert not list(tmp_path.rglob(".stage-*"))
    assert replay(archive, ref, EVENT_ID).payload == payload
    archive.persist(payload, change(acquisition, retrieval_event_id=UUID(int=900)))


@pytest.mark.parametrize("category", ["retrievals", "parses"])
def test_corrupt_existing_event_is_never_repaired(
    tmp_path, payload, acquisition, parse_event, category
):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    archive.persist_parse(parse_event)
    event_id = EVENT_ID if category == "retrievals" else parse_event.parse_event_id
    path = (tmp_path / ref.relative_path).parent / category / f"{event_id}.json"
    replace_bytes(path, b'{"password":"synthetic-corrupt-secret"')
    before = snapshot(tmp_path)
    with pytest.raises(ArchiveError) as caught:
        if category == "retrievals":
            archive.persist(payload, acquisition)
        else:
            archive.persist_parse(parse_event)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE
    assert "synthetic-corrupt-secret" not in str(caught.value)
    assert_preserved(before)


@pytest.mark.parametrize("mode", ["identical", "independent", "conflicting"])
def test_concurrent_parse_events_are_atomic(
    tmp_path, payload, acquisition, parse_event, monkeypatch, mode
):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    before = snapshot(tmp_path)
    barrier = Barrier(4)
    real_link = os.link

    def racing_link(src, dst, **kwargs):
        if Path(dst).parent.name == "parses":
            barrier.wait(timeout=10)
        return real_link(src, dst, **kwargs)

    monkeypatch.setattr(os, "link", racing_link)

    def write(index):
        updates = {}
        if mode == "independent":
            updates["parse_event_id"] = UUID(int=700 + index)
        elif mode == "conflicting":
            updates["parser_version"] = f"1.0.{index}"
        try:
            archive.persist_parse(change(parse_event, **updates))
            return "success"
        except ArchiveError as error:
            assert error.code is ErrorCode.INTEGRITY_FAILURE
            return "conflict"

    with ThreadPoolExecutor(max_workers=4) as executor:
        outcomes = list(executor.map(write, range(4)))
    assert outcomes.count("success") == (1 if mode == "conflicting" else 4)
    assert len(list(tmp_path.rglob("parses/*.json"))) == (4 if mode == "independent" else 1)
    assert archive.load(ref) == payload
    assert_preserved(before)
    assert not list(tmp_path.rglob(".stage-*"))


def test_simultaneous_changed_content_versions(tmp_path, source, monkeypatch):
    archive = LocalRawArchive(tmp_path)
    barrier = Barrier(4)
    real_link = os.link

    def racing_link(src, dst, **kwargs):
        if Path(dst).name == "payload.bin":
            barrier.wait(timeout=10)
        return real_link(src, dst, **kwargs)

    monkeypatch.setattr(os, "link", racing_link)

    def write(index):
        result = result_for(source, UUID(int=800 + index), ACQUIRED_AT, content=bytes([index]))
        return archive.persist(result.payload, result.provenance)

    with ThreadPoolExecutor(max_workers=4) as executor:
        refs = list(executor.map(write, range(4)))
    assert len(set(refs)) == 4
    for index, ref in enumerate(refs):
        assert replay(archive, ref, UUID(int=800 + index)).payload.content == bytes([index])
    assert len(list(tmp_path.rglob("payload.bin"))) == 4
    assert len(list(tmp_path.rglob("*.json"))) == 4
    assert not list(tmp_path.rglob(".stage-*"))


@pytest.mark.parametrize("field", ["source_id", "report_id", "delivery_date", "archive"])
def test_replay_rejects_wrong_source_or_archive_linkage(tmp_path, payload, acquisition, field):
    archive = LocalRawArchive(tmp_path)
    ref = archive.persist(payload, acquisition)
    event = (tmp_path / ref.relative_path).parent / "retrievals" / f"{EVENT_ID}.json"
    data = json.loads(event.read_bytes())
    if field == "archive":
        data["archive"] = None
    else:
        data["source"]["request"][field] = "2026-10-27" if field == "delivery_date" else "other"
    replace_bytes(event, json.dumps(data).encode())
    before = snapshot(tmp_path)
    with pytest.raises(ReplayError) as caught:
        replay(archive, ref, EVENT_ID)
    assert caught.value.code is ErrorCode.INTEGRITY_FAILURE
    assert_preserved(before)
