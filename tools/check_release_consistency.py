#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

'''

Release-consistency gate: fail unless the release tag, the package version, the
citation metadata, and the built artifact versions all agree.

A release cuts a tag ``vX.Y.Z`` and ships artifacts named ``pydlock-X.Y.Z*``.
Those must match ``pydlock.__version__`` (single-sourced in
``pydlock/constants.py``) and the ``version:`` in ``CITATION.cff``, or the
published release is internally inconsistent (a tag pointing at the wrong code, a
DOI citing the wrong version). This runs in the publish workflow before upload.

Usage:

    # tag from an explicit flag or from $GITHUB_REF_NAME (e.g. a release run)
    python tools/check_release_consistency.py --tag v2.0.7
    python tools/check_release_consistency.py            # reads GITHUB_REF_NAME

    # skip the artifact check when no dist/ is present (e.g. a pre-build check)
    python tools/check_release_consistency.py --tag v2.0.7 --no-artifacts

Exits 0 when everything agrees, 1 on any mismatch, 2 on a usage/environment error.

'''

# Standard library imports.
import argparse
import glob
import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONSTANTS = _REPO_ROOT / "pydlock" / "constants.py"
_CITATION  = _REPO_ROOT / "CITATION.cff"


def _package_version() -> str:

    text  = _CONSTANTS.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)

    if not match:

        print("check_release: no __version__ in constants.py", file=sys.stderr)

        raise SystemExit(2)

    return match.group(1)


def _citation_version() -> str:

    text  = _CITATION.read_text(encoding="utf-8")
    # A top-level `version: "X.Y.Z"` line (quotes optional).
    match = re.search(r'(?m)^version:\s*"?([^"\n]+?)"?\s*$', text)

    if not match:

        print("check_release: no version in CITATION.cff", file=sys.stderr)

        raise SystemExit(2)

    return match.group(1).strip()


def _artifact_versions(dist_dir: Path) -> dict[str, str]:

    '''Maps each dist artifact filename to the version parsed from its name.'''

    versions: dict[str, str] = {}

    for pattern in ("pydlock-*.whl", "pydlock-*.tar.gz"):

        for path in glob.glob(str(dist_dir / pattern)):

            name    = Path(path).name
            # pydlock-2.0.7-py3-none-any.whl  /  pydlock-2.0.7.tar.gz
            match   = re.match(r"pydlock-([0-9][^-]*?)(?:-py3|\.tar\.gz)", name)

            if match:

                versions[name] = match.group(1)

    return versions


def main(argv: list[str] | None = None) -> int:

    parser = argparse.ArgumentParser(description="Release-consistency gate.")
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME", ""))
    parser.add_argument("--dist-dir", default="dist")
    parser.add_argument("--no-artifacts", action="store_true",
                        help="skip the built-artifact version check")
    arguments = parser.parse_args(argv)

    package  = _package_version()
    citation = _citation_version()

    problems: list[str] = []

    if citation != package:

        problems.append(f"CITATION.cff version {citation!r} != package "
                        f"{package!r}")

    # The tag is optional (a plain CI run has none); when present it must be
    # exactly v<package-version>.
    tag = arguments.tag.strip()

    if tag:

        expected_tag = f"v{package}"

        if tag != expected_tag:

            problems.append(f"tag {tag!r} != expected {expected_tag!r}")

    if not arguments.no_artifacts:

        artifacts = _artifact_versions(Path(arguments.dist_dir))

        if not artifacts:

            problems.append(f"no artifacts found in {arguments.dist_dir} "
                            f"(use --no-artifacts to skip)")

        for name, version in artifacts.items():

            if version != package:

                problems.append(f"artifact {name} is version {version!r} != "
                                f"package {package!r}")

    if problems:

        print("check_release: FAILED", file=sys.stderr)

        for problem in problems:

            print(f"  - {problem}", file=sys.stderr)

        return 1

    summary = f"package={package} citation={citation}"

    if tag:

        summary += f" tag={tag}"

    print(f"check_release: OK — {summary}")

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
