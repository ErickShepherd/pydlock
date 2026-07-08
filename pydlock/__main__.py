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
import os
import sys
from argparse import ArgumentParser

# Local application imports.
import pydlock
from pydlock.constants import DEFAULT_ENCODING

# Dunder definitions.
__author__  = pydlock.__author__
__version__ = pydlock.__version__


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
    parser.add_argument("operation",  choices = function_map.keys())
    parser.add_argument("file",       type    = os.path.abspath)
    parser.add_argument("--encoding", type    = str, default = DEFAULT_ENCODING)
    kwargv = vars(parser.parse_args())

    # Performs the indicated task.
    task     = function_map[kwargv["operation"]]
    path     = kwargv["file"]
    encoding = kwargv["encoding"]

    # Capture the return value: unlock/decrypt return False on failure (e.g. a
    # wrong password). Surface that as a non-zero exit code so scripts and
    # pipelines can detect the failure. lock/encrypt return None on success and
    # must NOT be treated as a failure, so test for False explicitly.
    result = task(path, encoding)

    if result is False:

        sys.exit(1)


if __name__ == "__main__":

    main()
