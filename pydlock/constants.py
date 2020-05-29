#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

Defines package constants.

Software:      Pydlock
Author:        Erick Edward Shepherd
E-mail:        Contact@ErickShepherd.com
GitHub:        https://www.github.com/ErickShepherd/pydlock
PyPI:          https://pypi.org/project/pydlock/
Date created:  2020-04-30
Last modified: 2020-04-31


Description:
    
    Defines constant values shared across the package.


Copyright:
    
    Pydlock - A Python file encryption tool.
    
    Copyright (c) 2020 of Erick Edward Shepherd, all rights reserved.


License:
    
    This file is part of "Pydlock" (the "Software").
    
    MIT License

    Copyright (c) 2020 Erick Edward Shepherd

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the right to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

'''

# Standard library imports.
import json
import os

# Constant definitions.
_MODULE_PATH = os.path.dirname(os.path.realpath(__file__))
PACKAGE_NAME = "pydlock"
VERSION_FILE = os.path.join(_MODULE_PATH, "version.json")

with open(VERSION_FILE, "r") as file:
    
    # Versioning system: SemVer
    #  - MAJOR: Incremented for incompatible API changes.
    #  - MINOR: Incremented for new backwards compatible functionality.
    #  - PATCH: Incremented for make backwards compatible bug fixes.
    # For more info: https://semver.org/
    AUTHOR  = "Erick Edward Shepherd"
    VERSION = json.load(file)

DEFAULT_ENCODING = "utf-8"

# Module dunder definitions.
__author__  = AUTHOR
__version__ = (
    f"{VERSION['major']}."
    f"{VERSION['minor']}."
    f"{VERSION['patch']}."
)
