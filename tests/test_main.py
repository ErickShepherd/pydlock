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
