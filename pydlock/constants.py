#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

'''

Defines package constants.

Software:      Pydlock
Author:        Erick Edward Shepherd
E-mail:        Contact@ErickShepherd.com
GitHub:        https://www.github.com/ErickShepherd/pydlock
PyPI:          https://pypi.org/project/pydlock/
Date created:  2020-04-30
Last modified: 2026-07-08


Description:
    
    Defines constant values shared across the package.


'''

# Constant definitions.
PACKAGE_NAME = "pydlock"
AUTHOR       = "Erick Edward Shepherd"

DEFAULT_ENCODING = "utf-8"

# Module dunder definitions.
__author__  = AUTHOR

# Single source of truth for the package version (SemVer, https://semver.org/).
# Read at runtime as ``pydlock.__version__`` and at build time by hatchling
# (``[tool.hatch.version] path = "pydlock/constants.py"`` in pyproject.toml).
__version__ = "2.0.5"
