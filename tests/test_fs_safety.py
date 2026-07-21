# SPDX-License-Identifier: MIT

'''

Filesystem-safety and race regressions (triage stage T1).

pydlock replaces a file by renaming a fresh inode over the path. That is unsafe
for aliases (a symlink or a hard link) and for a target that changes between the
read and the replace, because it can report a successful lock while plaintext is
still reachable through the other name, or silently overwrite a newer edit.
These tests pin the conservative contract: reject symlinks / non-regular /
multiply-linked files outright, and detect a concurrent edit or a path swap and
refuse to overwrite newer contents.

Symlink and hard-link tests skip where the platform/privilege does not support
them (e.g. Windows without the create-symlink right).

'''

# Standard library imports.
import os
import stat

# Third party imports.
import pytest

# Local application imports.
import pydlock

PASSWORD = b"correct horse battery staple"
MAGIC    = b"PYDLOCK\x02\n"


@pytest.fixture
def require_symlink(tmp_path):

    '''Skips the test unless symlinks can be created here.'''

    probe = tmp_path / "_symlink_probe"

    try:

        os.symlink("nonexistent-target", str(probe))

    except (OSError, NotImplementedError, AttributeError):

        pytest.skip("symlinks not supported on this platform/privilege")

    probe.unlink()


@pytest.fixture
def require_hardlink(tmp_path):

    '''Skips the test unless hard links can be created here.'''

    source = tmp_path / "_hardlink_probe_a"
    source.write_bytes(b"x")
    target = tmp_path / "_hardlink_probe_b"

    try:

        os.link(str(source), str(target))

    except (OSError, NotImplementedError, AttributeError):

        pytest.skip("hard links not supported on this platform")

    target.unlink()
    source.unlink()


# --- symlink rejection: relative/absolute × same-dir/cross-dir ---------------


@pytest.mark.parametrize("absolute", [False, True], ids=["relative", "absolute"])
@pytest.mark.parametrize("cross_dir", [False, True], ids=["same-dir", "cross-dir"])
@pytest.mark.parametrize("operation", ["lock", "unlock"])
def test_symlink_is_rejected(tmp_path, require_symlink, absolute, cross_dir,
                             operation):

    # Build a plaintext target and a symlink pointing at it. Both the link and
    # the target must be untouched, and the operation must fail loudly.
    if cross_dir:

        target_dir = tmp_path / "elsewhere"
        target_dir.mkdir()

    else:

        target_dir = tmp_path

    target        = target_dir / "target.txt"
    target_bytes  = b"SYMLINK PLAINTEXT\n"
    target.write_bytes(target_bytes)

    link       = tmp_path / "link.txt"
    link_value = str(target) if absolute else os.path.relpath(target, tmp_path)
    os.symlink(link_value, str(link))

    run = pydlock.lock if operation == "lock" else pydlock.unlock

    with pytest.raises(pydlock.UnsupportedFileTypeError):

        run(str(link), password=PASSWORD)

    # The symlink still points where it did; the target is still plaintext (no
    # v2 envelope leaked through the alias).
    assert os.path.islink(str(link))
    assert target.read_bytes() == target_bytes
    assert not target.read_bytes().startswith(MAGIC)


# --- hard-link rejection -----------------------------------------------------


def test_hardlinked_file_is_rejected(tmp_path, require_hardlink):

    original      = tmp_path / "a.txt"
    plaintext     = b"HARDLINK PLAINTEXT\n"
    original.write_bytes(plaintext)

    alias = tmp_path / "b.txt"
    os.link(str(original), str(alias))
    assert original.stat().st_nlink == 2

    # Locking either name must fail: the other name would still reach plaintext.
    with pytest.raises(pydlock.UnsupportedFileTypeError):
        pydlock.lock(str(original), password=PASSWORD)

    with pytest.raises(pydlock.UnsupportedFileTypeError):
        pydlock.unlock(str(alias), password=PASSWORD)

    assert original.read_bytes() == plaintext
    assert alias.read_bytes()    == plaintext


# --- non-regular file rejection ----------------------------------------------


def test_directory_is_rejected(tmp_path):

    directory = tmp_path / "a_directory"
    directory.mkdir()

    with pytest.raises(pydlock.UnsupportedFileTypeError):
        pydlock.lock(str(directory), password=PASSWORD)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no os.mkfifo (Windows)")
def test_fifo_is_rejected_without_blocking(tmp_path):

    # Opening a FIFO read-only would block without O_NONBLOCK; the read helper
    # sets it, so this rejects promptly instead of hanging.
    fifo = tmp_path / "a_fifo"
    os.mkfifo(str(fifo))

    with pytest.raises(pydlock.UnsupportedFileTypeError):
        pydlock.lock(str(fifo), password=PASSWORD)


# --- a normal one-link regular file still round-trips (relative + absolute) ---


def test_regular_file_round_trip_absolute_and_relative(tmp_path, monkeypatch):

    original = b"a plain singly-linked file must still work\n"

    # absolute path
    abs_path = tmp_path / "abs.txt"
    abs_path.write_bytes(original)
    pydlock.lock(str(abs_path), password=PASSWORD)
    assert abs_path.read_bytes().startswith(MAGIC)
    assert pydlock.unlock(str(abs_path), password=PASSWORD) is True
    assert abs_path.read_bytes() == original

    # relative path (cwd = tmp_path)
    monkeypatch.chdir(tmp_path)
    rel = tmp_path / "rel.txt"
    rel.write_bytes(original)
    pydlock.lock("rel.txt", password=PASSWORD)
    assert rel.read_bytes().startswith(MAGIC)
    assert pydlock.unlock("rel.txt", password=PASSWORD) is True
    assert rel.read_bytes() == original


# --- concurrent edit / path swap detection -----------------------------------


def test_concurrent_edit_is_detected_and_newer_content_wins(tmp_path, monkeypatch):

    path = tmp_path / "race.txt"
    path.write_bytes(b"original content\n")

    newer = b"A NEWER, LONGER version written by another writer\n"
    real  = pydlock._encrypt_contents

    def racing_encrypt(contents, encoding, password):

        # Simulate a concurrent writer replacing the contents AFTER pydlock read
        # the file but BEFORE it revalidates and replaces.
        path.write_bytes(newer)

        return real(contents, encoding, password)

    monkeypatch.setattr(pydlock, "_encrypt_contents", racing_encrypt)

    with pytest.raises(pydlock.ConcurrentModificationError):
        pydlock.lock(str(path), password=PASSWORD)

    # The concurrent writer's contents survive; pydlock did not clobber them.
    assert path.read_bytes() == newer


def test_pathname_swap_to_other_inode_is_detected(tmp_path, monkeypatch):

    path  = tmp_path / "swap.txt"
    path.write_bytes(b"original\n")

    other = tmp_path / "other.txt"
    other_bytes = b"a different inode swapped into place\n"
    other.write_bytes(other_bytes)

    real = pydlock._encrypt_contents

    def swapping_encrypt(contents, encoding, password):

        # Rename a different inode over the path between read and replace.
        os.replace(str(other), str(path))

        return real(contents, encoding, password)

    monkeypatch.setattr(pydlock, "_encrypt_contents", swapping_encrypt)

    with pytest.raises(pydlock.ConcurrentModificationError):
        pydlock.lock(str(path), password=PASSWORD)

    assert path.read_bytes() == other_bytes


def test_pathname_swap_to_symlink_is_detected(tmp_path, monkeypatch, require_symlink):

    path  = tmp_path / "swap2.txt"
    path.write_bytes(b"original\n")

    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere_bytes = b"a symlink target that must not be followed\n"
    elsewhere.write_bytes(elsewhere_bytes)

    real = pydlock._encrypt_contents

    def swapping_encrypt(contents, encoding, password):

        # Swap the path out for a symlink between read and replace.
        path.unlink()
        os.symlink(str(elsewhere), str(path))

        return real(contents, encoding, password)

    monkeypatch.setattr(pydlock, "_encrypt_contents", swapping_encrypt)

    with pytest.raises(pydlock.ConcurrentModificationError):
        pydlock.lock(str(path), password=PASSWORD)

    # The symlink was not followed/overwritten; its target is intact plaintext.
    assert os.path.islink(str(path))
    assert elsewhere.read_bytes() == elsewhere_bytes


def test_identity_snapshot_uses_dev_ino_size_mtime():

    # The snapshot pins exactly the four fields the plan names, so a later change
    # to the tuple shape is caught here rather than silently weakening detection.
    assert pydlock._FileIdentity._fields == (
        "st_dev", "st_ino", "st_size", "st_mtime_ns",
    )


def test_read_helper_rejects_symlink_directly(tmp_path, require_symlink):

    target = tmp_path / "t.txt"
    target.write_bytes(b"x")
    link = tmp_path / "l.txt"
    os.symlink(str(target), str(link))

    with pytest.raises(pydlock.UnsupportedFileTypeError):
        pydlock._open_and_read_regular(str(link))

    # sanity: the underlying regular target reads fine and reports one link
    identity, contents = pydlock._open_and_read_regular(str(target))
    assert contents == b"x"
    assert stat.S_ISREG(os.stat(str(target)).st_mode)
    assert identity.st_size == 1
