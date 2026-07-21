# SPDX-License-Identifier: MIT

'''

Tests for the privacy guard (tools/privacy_scan.py). These pin two things:

  1. the Gmail-address detector matches the pattern (a synthetic address) while
     leaving the intentional public/domain address and noreply identities alone;
  2. the current tracked tree is clean.

Neither the forbidden private address NOR any literal ``@gmail.com`` string is
written in this file: the synthetic positive-case addresses are ASSEMBLED from
fragments at runtime, so the guard scanning this very file (it ships in the
sdist and is git-tracked) never trips on the test that exercises it. If
``tools/`` is absent (e.g. running from an installed sdist, which excludes it),
the module-dependent tests skip rather than fail.

'''

# Standard library imports.
import importlib.util
from pathlib import Path

# Third party imports.
import pytest

_REPO_ROOT    = Path(__file__).resolve().parent.parent
_SCANNER_PATH = _REPO_ROOT / "tools" / "privacy_scan.py"

# The provider domain is assembled from parts so this source file contains no
# literal, scannable Gmail address (mirroring how the guard itself never stores
# one). ``_addr`` builds a full synthetic address at runtime.
_PROVIDER = b"gmail" + b".com"


def _addr(local: bytes) -> bytes:

    return local + b"@" + _PROVIDER


def _load_scanner():

    '''Imports tools/privacy_scan.py by path, or skips if it is not present.'''

    if not _SCANNER_PATH.is_file():

        pytest.skip("tools/privacy_scan.py not present (e.g. sdist install)")

    spec   = importlib.util.spec_from_file_location("privacy_scan", _SCANNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_detects_a_gmail_address():

    scanner = _load_scanner()

    # A synthetic Gmail address (NOT the forbidden one) must be detected.
    haystack = b"contact me at " + _addr(b"someone.example") + b" please"
    matches  = scanner.scan_bytes(haystack)

    assert len(matches) == 1
    assert matches[0].lower().endswith(b"@" + _PROVIDER)


def test_ignores_public_domain_and_noreply_addresses():

    scanner = _load_scanner()

    benign = (
        b"Contact@ErickShepherd.com\n"
        b"24425940+ErickShepherd@users.noreply.github.com\n"
        b"dev@erickshepherd.com\n"
        b"noreply@github.com\n"
    )

    assert scanner.scan_bytes(benign) == []


def test_case_insensitive_provider():

    scanner = _load_scanner()

    assert scanner.scan_bytes(_addr(b"Person").upper()) != []


def test_tracked_tree_is_clean():

    scanner = _load_scanner()

    files = scanner._iter_tracked_files()
    hits  = scanner.scan_files(files)

    assert hits == 0, "a Gmail address leaked into the tracked tree"
