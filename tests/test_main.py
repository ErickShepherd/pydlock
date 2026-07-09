# SPDX-License-Identifier: MIT

'''

Offline tests for the ``python -m pydlock`` CLI entry point (pydlock.__main__).
The lock/unlock functions are monkeypatched so nothing touches real files or
crypto; these pin the arg parsing, the encrypt/decrypt -> lock/unlock alias
map, and the process exit code on a failed unlock.

'''

# Standard library imports.
import os

# Third party imports.
import pytest

# Local application imports.
import pydlock
from pydlock import __main__ as cli


def test_failed_unlock_exits_nonzero(monkeypatch):

    # A failed unlock (wrong password) returns False; the CLI must surface that
    # as a non-zero exit code so scripts/pipelines can detect the failure.
    monkeypatch.setattr(pydlock, "unlock", lambda *a, **k: False)
    monkeypatch.setattr("sys.argv", ["pydlock", "unlock", "secret.txt"])

    with pytest.raises(SystemExit) as excinfo:
        cli.main()

    assert excinfo.value.code == 1


def test_successful_unlock_exits_zero(monkeypatch):

    # A successful unlock returns True; main() must return normally (exit 0).
    monkeypatch.setattr(pydlock, "unlock", lambda *a, **k: True)
    monkeypatch.setattr("sys.argv", ["pydlock", "unlock", "secret.txt"])

    assert cli.main() is None


@pytest.mark.parametrize(
    "verb, expected_fn",
    [
        ("lock",    "lock"),
        ("unlock",  "unlock"),
        ("encrypt", "lock"),    # encrypt is an alias for lock
        ("decrypt", "unlock"),  # decrypt is an alias for unlock
    ],
)
def test_verb_routes_to_expected_function(monkeypatch, verb, expected_fn):

    # Each CLI verb must dispatch to the mapped function; encrypt/decrypt alias
    # lock/unlock. Record which of lock/unlock was called and with what path.
    calls = []

    def record(name, result):
        def fn(path, encoding):
            calls.append((name, path, encoding))
            return result
        return fn

    monkeypatch.setattr(pydlock, "lock",   record("lock", None))
    monkeypatch.setattr(pydlock, "unlock", record("unlock", True))
    monkeypatch.setattr("sys.argv", ["pydlock", verb, "secret.txt"])

    cli.main()

    assert len(calls) == 1
    assert calls[0][0] == expected_fn


def test_file_argument_coerced_to_absolute_path(monkeypatch):

    # The ``file`` argument uses type=os.path.abspath, so a relative path is
    # coerced to an absolute path before it reaches lock/unlock.
    calls = []
    monkeypatch.setattr(pydlock, "lock",
                        lambda path, encoding: calls.append(path))
    monkeypatch.setattr("sys.argv", ["pydlock", "lock", "relative.txt"])

    cli.main()

    assert calls == [os.path.abspath("relative.txt")]


def test_encoding_flag_forwarded(monkeypatch):

    # A non-default --encoding is parsed and forwarded to the task function.
    calls = []
    monkeypatch.setattr(pydlock, "lock",
                        lambda path, encoding: calls.append(encoding))
    monkeypatch.setattr("sys.argv",
                        ["pydlock", "lock", "secret.txt", "--encoding", "latin-1"])

    cli.main()

    assert calls == ["latin-1"]
