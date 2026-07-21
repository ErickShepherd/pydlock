# SPDX-License-Identifier: MIT

'''

CLI diagnostics (triage stage T4 / A5). Expected operational failures must exit
non-zero with a concise one-line ``pydlock: …`` message on stderr and no
traceback; ``--version`` reports the version.

'''

# Standard library imports.
import os
import sys

# Third party imports.
import pytest

# Local application imports.
import pydlock
from pydlock import __main__ as cli


def _run(monkeypatch, argv):

    '''Runs the CLI with argv; returns the exit code (0 if it returns normally).'''

    monkeypatch.setattr(sys, "argv", ["pydlock", *argv])

    try:

        cli.main()

        return 0

    except SystemExit as exit_error:

        return exit_error.code if isinstance(exit_error.code, int) else 1


def test_version_flag(monkeypatch, capsys):

    with pytest.raises(SystemExit) as exit_info:

        monkeypatch.setattr(sys, "argv", ["pydlock", "--version"])
        cli.main()

    assert exit_info.value.code == 0

    captured = capsys.readouterr()
    assert "pydlock" in captured.out
    assert pydlock.__version__ in captured.out


def test_missing_file_is_friendly(monkeypatch, capsys, tmp_path):

    code = _run(monkeypatch, ["lock", str(tmp_path / "nope.txt")])

    captured = capsys.readouterr()
    assert code == 1
    assert "no such file" in captured.err
    assert "Traceback" not in captured.err


def test_unknown_encoding_is_friendly(monkeypatch, capsys, tmp_path):

    target = tmp_path / "a.txt"
    target.write_bytes(b"x")

    code = _run(monkeypatch, ["lock", str(target), "--encoding", "bogus-enc"])

    captured = capsys.readouterr()
    assert code == 1
    assert "unknown encoding" in captured.err
    assert "Traceback" not in captured.err


def test_symlink_target_is_friendly(monkeypatch, capsys, tmp_path):

    link = tmp_path / "link.txt"

    try:

        os.symlink("target.txt", str(link))

    except (OSError, NotImplementedError, AttributeError):

        pytest.skip("symlinks not supported on this platform/privilege")

    link.unlink()

    target = tmp_path / "target.txt"
    target.write_bytes(b"SYMLINK PLAINTEXT")
    os.symlink(str(target), str(link))

    # Rejected before any password prompt, so this never blocks on getpass.
    code = _run(monkeypatch, ["lock", str(link)])

    captured = capsys.readouterr()
    assert code == 1
    assert "symlink" in captured.err
    assert "Traceback" not in captured.err
    # target untouched
    assert target.read_bytes() == b"SYMLINK PLAINTEXT"
