# SPDX-License-Identifier: MIT

'''

Atomicity + durability regressions (triage stage T3).

The write sequence was atomic (an interrupted write never surfaces a partial
file) but not fully durable, and it applied metadata AFTER the file fsync. These
tests pin the corrected ordering — metadata before the final fsync, replace only
after the prepared file is durable, then a parent-directory fsync — plus the
honest platform fallback where directory fsync is unavailable, and retain the
interruption / no-temp-leak coverage.

'''

# Standard library imports.
import os
import shutil

# Third party imports.
import pytest

# Local application imports.
import pydlock

PASSWORD = b"correct horse battery staple"
MAGIC    = b"PYDLOCK\x02\n"


def test_write_ordering_metadata_fsync_replace_dirfsync(tmp_path, monkeypatch):

    # Record the order of the durability-relevant operations during a lock over
    # an EXISTING file (so metadata preservation runs) and assert the sequence.
    path     = tmp_path / "ordered.txt"
    original = b"some contents to encrypt\n"
    path.write_bytes(original)
    os.chmod(path, 0o644)

    events        = []
    real_fsync    = os.fsync
    real_replace  = os.replace
    real_copystat = shutil.copystat

    def record_copystat(source, destination, *args, **kwargs):
        events.append("metadata")
        return real_copystat(source, destination, *args, **kwargs)

    def record_fsync(file_descriptor):
        # Only the FILE fsync reaches os.fsync here; the directory fsync is
        # stubbed below so it does not also land in this recorder.
        events.append("file_fsync")
        return real_fsync(file_descriptor)

    def record_replace(source, destination):
        events.append("replace")
        return real_replace(source, destination)

    def record_dir_fsync(directory):
        events.append("dir_fsync")
        return True

    monkeypatch.setattr(shutil, "copystat", record_copystat)
    monkeypatch.setattr(os, "fsync", record_fsync)
    monkeypatch.setattr(os, "replace", record_replace)
    monkeypatch.setattr(pydlock, "_fsync_directory", record_dir_fsync)

    pydlock.lock(str(path), password=PASSWORD)

    # Each stage present exactly once, in the required order.
    for stage in ("metadata", "file_fsync", "replace", "dir_fsync"):
        assert stage in events, f"{stage} never happened: {events}"

    assert events.index("metadata")   < events.index("file_fsync")
    assert events.index("file_fsync") < events.index("replace")
    assert events.index("replace")    < events.index("dir_fsync")

    # dir fsync is the final durability step.
    assert events[-1] == "dir_fsync"


def test_fsync_directory_succeeds_on_this_platform(tmp_path):

    if not hasattr(os, "O_DIRECTORY"):
        pytest.skip("platform has no directory fsync (e.g. Windows)")

    assert pydlock._fsync_directory(str(tmp_path)) is True


def test_fsync_directory_is_honest_when_it_cannot(tmp_path):

    # A nonexistent directory cannot be fsynced; the helper reports False rather
    # than raising, so it can never claim a durability it did not achieve.
    missing = tmp_path / "no-such-directory"

    assert pydlock._fsync_directory(str(missing)) is False


def test_interrupted_replace_leaves_original_and_no_temp_leak(tmp_path, monkeypatch):

    # Retained interruption coverage: a crash at the replace step leaves the
    # original intact, leaks no temp file, and never reaches the directory fsync.
    path     = tmp_path / "atomic.txt"
    original = b"ORIGINAL must survive an interrupted lock\n"
    path.write_bytes(original)

    reached_dir_fsync = []
    monkeypatch.setattr(pydlock, "_fsync_directory",
                        lambda directory: reached_dir_fsync.append(directory))

    def boom(source, destination):
        raise RuntimeError("simulated crash at the atomic swap")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(RuntimeError):
        pydlock.lock(str(path), password=PASSWORD)

    assert path.read_bytes() == original
    assert list(tmp_path.glob(".pydlock-*")) == []
    assert reached_dir_fsync == [], "dir fsync must not run when replace failed"


def test_round_trip_still_durable_and_correct(tmp_path):

    # End-to-end: the reordered, directory-fsyncing write still round-trips.
    path     = tmp_path / "rt.txt"
    original = bytes(range(256)) + b"\n"
    path.write_bytes(original)

    pydlock.lock(str(path), password=PASSWORD)
    assert path.read_bytes().startswith(MAGIC)
    assert pydlock.unlock(str(path), password=PASSWORD) is True
    assert path.read_bytes() == original
