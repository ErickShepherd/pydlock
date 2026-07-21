#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

'''

Privacy guard: fail if a private Gmail address has leaked into the repository
tree or a built distribution artifact.

The check exists because pydlock's history once carried the owner's private
Gmail address in internal prose, and the default source distribution shipped
those internal files. This scanner is the recurrence guard: it rejects any
tracked file (or any file inside an extracted sdist/wheel) that contains a
``…@gmail.com`` address.

Crucially, the forbidden address is NEVER embedded in this repository. The
scanner matches the *pattern* of a Gmail address, not a specific literal, so the
guard itself does not reintroduce the leak it defends against. The public
contact address on the owned domain (``Contact@ErickShepherd.com``) and GitHub
noreply commit identities are deliberately not matched.

Usage:

    # scan the tracked working tree (git ls-files); default mode
    python tools/privacy_scan.py

    # scan an extracted distribution (a directory) or explicit files
    python tools/privacy_scan.py --paths dist/extracted

Exits 0 when clean, 1 when any match is found (with a redacted report), and 2
on a usage/environment error.

'''

# Standard library imports.
import argparse
import re
import subprocess
import sys
from pathlib import Path

# A Gmail address: local-part @ gmail.com, matched case-insensitively. Only the
# provider half is a fixed literal; the local part is a pattern, so the private
# address is never stored here.
GMAIL_PATTERN = re.compile(rb"[A-Za-z0-9._%+-]+@gmail\.com", re.IGNORECASE)

# Files that are legitimately binary or otherwise not worth scanning as text.
# Binary content is skipped anyway (a NUL byte short-circuits the read), but
# skipping by suffix avoids the read entirely for large assets.
SKIP_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".ttf", ".otf", ".woff",
    ".woff2", ".zip", ".gz", ".tar", ".whl", ".locked", ".pyc",
})


def _redact(match: bytes) -> str:

    '''Renders a matched address for the report WITHOUT echoing the local part.'''

    return "<redacted-local-part>@gmail.com"


def _iter_tracked_files() -> list[Path]:

    '''Returns the git-tracked files of the current repository.'''

    try:

        output = subprocess.run(
            ["git", "ls-files", "-z"],
            capture_output=True, check=True,
        ).stdout

    except (OSError, subprocess.CalledProcessError) as error:

        print(f"privacy_scan: could not list tracked files: {error}",
              file=sys.stderr)

        raise SystemExit(2) from error

    return [Path(name.decode("utf-8"))
            for name in output.split(b"\x00") if name]


def _iter_path_files(paths: list[str]) -> list[Path]:

    '''Expands the given files/directories into a flat list of files.'''

    files: list[Path] = []

    for raw in paths:

        path = Path(raw)

        if path.is_dir():

            files.extend(child for child in path.rglob("*") if child.is_file())

        elif path.is_file():

            files.append(path)

        else:

            print(f"privacy_scan: no such file or directory: {path}",
                  file=sys.stderr)

            raise SystemExit(2)

    return files


def scan_bytes(data: bytes) -> list[bytes]:

    '''Returns every Gmail-address match in a byte string (possibly empty).'''

    return GMAIL_PATTERN.findall(data)


def scan_files(files: list[Path]) -> int:

    '''

    Scans each file and reports (redacted) any Gmail address found. Returns the
    number of files that contained at least one match.

    '''

    hits = 0

    for path in files:

        if path.suffix.lower() in SKIP_SUFFIXES:

            continue

        try:

            data = path.read_bytes()

        except OSError:

            continue

        # Treat a NUL byte as a binary file and skip it.
        if b"\x00" in data:

            continue

        matches = scan_bytes(data)

        if matches:

            hits += 1

            for match in matches:

                print(f"LEAK: {path}: {_redact(match)}", file=sys.stderr)

    return hits


def main(argv: list[str] | None = None) -> int:

    parser = argparse.ArgumentParser(
        description="Fail if a private Gmail address leaked into the tree or a "
                    "built artifact (the address itself is never stored here).",
    )
    parser.add_argument(
        "--paths", nargs="+", metavar="PATH",
        help="files/directories to scan instead of the git-tracked tree "
             "(e.g. an extracted sdist or wheel).",
    )
    arguments = parser.parse_args(argv)

    files = (_iter_path_files(arguments.paths) if arguments.paths
             else _iter_tracked_files())

    hits = scan_files(files)

    if hits:

        print(f"privacy_scan: FAILED — {hits} file(s) contain a Gmail address.",
              file=sys.stderr)

        return 1

    print(f"privacy_scan: OK — {len(files)} file(s) scanned, no Gmail address.")

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
