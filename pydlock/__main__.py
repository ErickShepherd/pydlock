#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

A command line utility for the Pydlock package.

Software:      Pydlock
Author:        Erick Edward Shepherd
E-mail:        Contact@ErickShepherd.com
GitHub:        https://www.github.com/ErickShepherd/pydlock
PyPI:          https://pypi.org/project/pydlock/
Date created:  2020-04-30
Last modified: 2020-04-30


Description:
    
    A command line utility for the Pydlock package, which allows users to lock
    and unlock files with a password, or run Python scripts locked by Pydlock.


Usage:

    This module may be executed from the command line as a Python script:
    
        python -m pydlock
    
    Running the script without any arguments will display the usage:
    
        usage: pydlock.py [-h] [--arguments ARGUMENTS] [--encoding ENCODING]
                          {lock,unlock,python,run} file
    
    Supported operations include:
    
        lock:   Encrypts a file in-place.
        unlock: Decrypts a file in-place.
        python: Decrypts and runs the contents of a Python file.
        run:    Temporarily decrypts, runs, and re-encrypts an arbitrary file.
    
    Example:
    
        python -m pydlock lock example.txt --encoding=utf-8
    

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


Notes:
    
    Issues with use on Windows executables:
    
        Because the files are modified, locking and unlocking executables on
        Windows does not preserve their checksum. Consequently, after locking
        and unlocking an executable on Windows, when an execution is attempted,
        the system raises an error for security purposes:
    
            "This version of <file> is not compatible with the version of
            Windows you're running. Check your computer's system information
            and then contact the software publisher."
        
        There does not appear to be a simple resolution for this issue, and the
        files effectively become corrupted.

'''

# Standard library imports.
import os
from argparse import ArgumentParser

# Local application imports.
import pydlock
# Local application imports.
from pydlock.constants import DEFAULT_ENCODING

# Dunder definitions.
__author__  = pydlock.__author__
__version__ = pydlock.__version__

if __name__ == "__main__":
    
    # Maps function names to the respective function.
    function_map = {
        "lock"    : pydlock.lock,
        "unlock"  : pydlock.unlock,
        "python"  : pydlock.python,
        "run"     : pydlock.run
    }
    
    # Parses command-line arguments from the user.
    parser = ArgumentParser()
    parser.add_argument("operation",   choices = function_map.keys())
    parser.add_argument("file",        type = os.path.abspath)
    parser.add_argument("--arguments", type = str, default = "")
    parser.add_argument("--encoding",  type = str, default = DEFAULT_ENCODING)
    kwargv = vars(parser.parse_args())
    
    # Aliases parsed command-line arguments for brevity.
    task      = function_map[kwargv["operation"]]
    path      = kwargv["file"]
    arguments = kwargv["arguments"]
    encoding  = kwargv["encoding"]
    
    # Performs the indicated task.
    task(path, arguments, encoding)
