#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

A package for encrypting files with a password.

Software:      Pydlock
Author:        Erick Edward Shepherd
E-mail:        Contact@ErickShepherd.com
GitHub:        https://www.github.com/ErickShepherd/pydlock
PyPI:          https://pypi.org/project/pydlock/
Date created:  2020-04-30
Last modified: 2020-04-31


Description:
    
    Installs Pydlock and its dependencies.


Copyright:
    
    Pydlock - A Python file encryption tool.
    
    Copyright (c) 2020 of Erick Edward Shepherd, all rights reserved.


License:
    
    This file is part of Pydlock (the "Software").
    
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

# Third party imports.
import setuptools

# Local application imports.
import pydlock

# Module dunder definitions.
__author__  = pydlock.__author__
__version__ = pydlock.__version__

# Constant definitions.
DESCRIPTION = __doc__.strip().split("\n")[0]

with open("README.rst", "r") as file:
    
    LONG_DESCRIPTION = file.read()

CLASSIFIERS = [
    "Intended Audience :: Developers",
    "Intended Audience :: End Users/Desktop",
    "Topic :: Security",
    "Environment :: Console",
    "Development Status :: 5 - Production/Stable",
    "Natural Language :: English",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "License :: OSI Approved :: MIT License",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX",
    "Operating System :: Unix",
    "Operating System :: MacOS"
]

PLATFORMS = ["Windows", "Linux", "Solaris", "Mac OS-X", "Unix"]

SETUP_KWARGS = dict(
    name                 = "pydlock",
    version              = __version__,
    description          = DESCRIPTION,
    long_description     = LONG_DESCRIPTION,
    classifiers          = CLASSIFIERS,
    author               = __author__,
    author_email         = "Contact@ErickShepherd.com",
    maintainer           = __author__,
    maintainer_email     = "Contact@ErickShepherd.com",
    license              = "MIT",
    platforms            = PLATFORMS,
    python_requires      = ">=3.7",
    packages             = setuptools.find_packages(),
    url                  = "https://www.github.com/ErickShepherd/pydlock",
    download_url         = "https://pypi.org/project/pydlock/",
    project_urls         = {
        "Bug Tracker" :
            "https://github.com/ErickShepherd/pydlock/issues",
        
        "Source Code" :
            "https://github.com/ErickShepherd/pydlock",
        
        "Documentation" :
            "https://github.com/ErickShepherd/pydlock/blob/master/README.rst"
    }
)

if __name__ == "__main__":

    setuptools.setup(**SETUP_KWARGS)
