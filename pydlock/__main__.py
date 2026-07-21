#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

'''

A command line utility for the Pydlock package.

Software:      Pydlock
Author:        Erick Edward Shepherd
E-mail:        Contact@ErickShepherd.com
GitHub:        https://www.github.com/ErickShepherd/pydlock
PyPI:          https://pypi.org/project/pydlock/
Date created:  2020-04-30
Last modified: 2026-07-08


Description:

    A command line utility for the Pydlock package, which lets users encrypt
    and decrypt files in place with a password.


Usage:

    This module may be executed from the command line as a Python script:

        python -m pydlock <operation> <file> [--encoding ENCODING]

    or, once installed, via the ``pydlock`` console entry point:

        pydlock <operation> <file> [--encoding ENCODING]

    Supported operations:

        lock:    Encrypts a file in place.
        unlock:  Decrypts a file in place.
        encrypt: Alias for lock.
        decrypt: Alias for unlock.

    Example:

        pydlock lock example.txt

'''

# Standard library imports.
import codecs
import os
import sys
from argparse import ArgumentParser

# Local application imports.
import pydlock
from pydlock.constants import DEFAULT_ENCODING

# Dunder definitions.
__author__  = pydlock.__author__
__version__ = pydlock.__version__


def _fail(message : str) -> None:

    '''Prints a concise one-line diagnostic to stderr and exits non-zero.'''

    print(f"pydlock: {message}", file = sys.stderr)

    sys.exit(1)


def main() -> None:

    # Maps each CLI verb to its function; encrypt/decrypt alias lock/unlock.
    function_map = {
        "lock"    : pydlock.lock,
        "unlock"  : pydlock.unlock,
        "encrypt" : pydlock.lock,
        "decrypt" : pydlock.unlock,
    }

    # Parses command-line arguments from the user.
    parser = ArgumentParser()
    parser.add_argument("--version", action  = "version",
                        version = f"pydlock {pydlock.__version__}")
    parser.add_argument("operation",  choices = function_map.keys())
    parser.add_argument("file",       type    = os.path.abspath)
    parser.add_argument("--encoding", type    = str, default = DEFAULT_ENCODING)
    kwargv = vars(parser.parse_args())

    # Performs the indicated task.
    task     = function_map[kwargv["operation"]]
    path     = kwargv["file"]
    encoding = kwargv["encoding"]

    # Non-racy user-facing preflight BEFORE prompting for a password, so a common
    # mistake fails fast with a friendly message instead of after two password
    # entries. The authoritative, race-resistant checks stay in the core
    # (_open_and_read_regular), which runs before the prompt and rejects a
    # symlink / non-regular / hard-linked target even if it appears here.
    try:

        codecs.lookup(encoding)

    except LookupError:

        _fail(f"unknown encoding: {encoding!r}")

    if not os.path.exists(path):

        _fail(f"no such file: {path}")

    # Run the operation, mapping EXPECTED operational failures to a concise
    # stderr line + non-zero exit (never a traceback). Unexpected programmer
    # errors are left to raise so tests still catch them.
    try:

        result = task(path, encoding)

    except pydlock.PydlockError as error:

        # symlink / non-regular / hard-linked target, or a concurrent-edit /
        # path-swap abort — the message is already user-facing.
        _fail(str(error))

    except (ValueError, LookupError) as error:

        # e.g. an empty password on encryption, or an encoding error at prompt.
        _fail(str(error))

    except PermissionError:

        _fail(f"permission denied: {path}")

    except OSError as error:

        _fail(f"{error.strerror or error}: {path}")

    # Capture the return value: unlock/decrypt return False on failure (e.g. a
    # wrong password). Surface that as a non-zero exit code so scripts and
    # pipelines can detect the failure. lock/encrypt return None on success and
    # must NOT be treated as a failure, so test for False explicitly.
    if result is False:

        sys.exit(1)


if __name__ == "__main__":

    main()
