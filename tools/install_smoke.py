#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

'''

Clean-environment install smoke test for a BUILT artifact.

CI (and the release runbook) build a wheel and an sdist, then run this against
each: it installs the artifact into a fresh, isolated virtual environment (so the
test exercises exactly what a user would `pip install`, not the editable
checkout) and verifies

  1. the public API imports;
  2. ``pydlock.__version__`` matches the version in ``pydlock/constants.py``;
  3. the installed ``pydlock`` console entry point reports that version; and
  4. a noninteractive lock -> unlock round-trip returns the original bytes.

Cross-platform: it resolves the venv's interpreter path for POSIX and Windows.

Usage:

    python tools/install_smoke.py --artifact wheel   # or: sdist
    python tools/install_smoke.py --artifact sdist --dist-dir dist

Exits 0 on success, 1 on any check failure, 2 on a usage/environment error.

'''

# Standard library imports.
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

_REPO_ROOT     = Path(__file__).resolve().parent.parent
_CONSTANTS     = _REPO_ROOT / "pydlock" / "constants.py"

_ARTIFACT_GLOB = {
    "wheel": "pydlock-*.whl",
    "sdist": "pydlock-*.tar.gz",
}


def _expected_version() -> str:

    '''The single-source version from pydlock/constants.py.'''

    text  = _CONSTANTS.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)

    if not match:

        print("install_smoke: could not read __version__ from constants.py",
              file=sys.stderr)

        raise SystemExit(2)

    return match.group(1)


def _venv_python(venv_dir: Path) -> Path:

    '''The interpreter inside a freshly created venv, POSIX or Windows.'''

    if os.name == "nt":

        return venv_dir / "Scripts" / "python.exe"

    return venv_dir / "bin" / "python"


def _find_artifact(dist_dir: Path, artifact: str) -> Path:

    matches = sorted(glob.glob(str(dist_dir / _ARTIFACT_GLOB[artifact])))

    if not matches:

        print(f"install_smoke: no {artifact} found in {dist_dir}", file=sys.stderr)

        raise SystemExit(2)

    if len(matches) > 1:

        print(f"install_smoke: multiple {artifact} artifacts: {matches}",
              file=sys.stderr)

        raise SystemExit(2)

    return Path(matches[0])


def _run(python: Path, code: str) -> str:

    '''Runs a snippet in the target interpreter and returns stripped stdout.'''

    result = subprocess.run([str(python), "-c", code],
                            capture_output=True, text=True, check=True)

    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:

    parser = argparse.ArgumentParser(description="Clean-env install smoke test.")
    parser.add_argument("--artifact", choices=sorted(_ARTIFACT_GLOB),
                        required=True)
    parser.add_argument("--dist-dir", default="dist")
    arguments = parser.parse_args(argv)

    expected = _expected_version()
    artifact = _find_artifact(Path(arguments.dist_dir), arguments.artifact)

    print(f"install_smoke: {arguments.artifact} = {artifact.name} "
          f"(expecting version {expected})")

    with tempfile.TemporaryDirectory(prefix="pydlock-smoke-") as workspace:

        venv_dir = Path(workspace) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python = _venv_python(venv_dir)

        # Install the built artifact (and its declared runtime deps) — NOT the
        # working tree.
        subprocess.run([str(python), "-m", "pip", "install", "--quiet",
                        "--upgrade", "pip"], check=True)
        subprocess.run([str(python), "-m", "pip", "install", "--quiet",
                        str(artifact)], check=True)

        # 1 + 2: import and version.
        imported = _run(python, "import pydlock; print(pydlock.__version__)")

        if imported != expected:

            print(f"install_smoke: FAILED — imported version {imported!r} != "
                  f"expected {expected!r}", file=sys.stderr)

            return 1

        # 3: console entry point reports the version.
        entry = subprocess.run([str(python), "-m", "pydlock", "--version"],
                               capture_output=True, text=True, check=True)

        if expected not in entry.stdout:

            print(f"install_smoke: FAILED — `pydlock --version` = "
                  f"{entry.stdout.strip()!r} lacks {expected!r}", file=sys.stderr)

            return 1

        # 4: noninteractive lock -> unlock round-trip in the installed env.
        sample = Path(workspace) / "secret.bin"
        sample.write_bytes(bytes(range(256)) + b"\npydlock smoke\n")

        round_trip = _run(python, (
            "import pydlock, sys\n"
            f"p = {str(sample)!r}\n"
            "original = open(p, 'rb').read()\n"
            "pydlock.lock(p, password=b'smoke-test-password')\n"
            "assert open(p, 'rb').read().startswith(b'PYDLOCK\\x02\\n')\n"
            "assert pydlock.unlock(p, password=b'smoke-test-password') is True\n"
            "print('OK' if open(p, 'rb').read() == original else 'MISMATCH')\n"
        ))

        if round_trip != "OK":

            print(f"install_smoke: FAILED — round-trip result {round_trip!r}",
                  file=sys.stderr)

            return 1

    print(f"install_smoke: OK — {arguments.artifact} installs, imports, "
          f"reports {expected}, and round-trips.")

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
