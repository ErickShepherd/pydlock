# SPDX-License-Identifier: MIT

'''

Standing invariants for the release tooling (triage stage T5). These keep the
version single-source honest between releases: the package version and the
citation metadata must always agree, and the consistency checker must flag a
mismatched tag. If ``tools/`` is absent (installed sdist), they skip.

'''

# Standard library imports.
import importlib.util
from pathlib import Path

# Third party imports.
import pytest

_REPO_ROOT   = Path(__file__).resolve().parent.parent
_CHECK_PATH  = _REPO_ROOT / "tools" / "check_release_consistency.py"


def _load_checker():

    if not _CHECK_PATH.is_file():

        pytest.skip("tools/check_release_consistency.py not present (sdist)")

    spec   = importlib.util.spec_from_file_location("check_release", _CHECK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_package_and_citation_versions_agree():

    checker = _load_checker()

    assert checker._package_version() == checker._citation_version(), (
        "pydlock/constants.py __version__ and CITATION.cff version disagree"
    )


def test_checker_flags_a_mismatched_tag():

    checker = _load_checker()

    # A deliberately wrong tag must fail (exit 1), skipping the artifact check.
    exit_code = checker.main(["--tag", "v0.0.0-not-real", "--no-artifacts"])

    assert exit_code == 1


def test_checker_accepts_the_matching_tag():

    checker = _load_checker()

    good = f"v{checker._package_version()}"
    exit_code = checker.main(["--tag", good, "--no-artifacts"])

    assert exit_code == 0


def test_checker_ignores_workflow_dispatch_branch_ref(monkeypatch):

    checker = _load_checker()
    monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
    monkeypatch.setenv("GITHUB_REF_NAME", "fix/v2.0.7-release-ready")

    assert checker.main(["--no-artifacts"]) == 0
