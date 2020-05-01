#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

Builds the source distribution.

Software:      Pydlock
Author:        Erick Edward Shepherd
E-mail:        Contact@ErickShepherd.com
GitHub:        https://www.github.com/ErickShepherd/pydlock
Date created:  2020-04-30
Last modified: 2020-04-30


Description:
    
    Builds the source distribution.


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

# Standard library imports.
import os
import pathlib
import shutil
import subprocess

# Local application imports.
import pydlock

# Module dunder definitions.
__author__  = pydlock.__author__
__version__ = pydlock.__version__

# Constant definitions.
PACKAGE_NAME      = "pydlock"
PACKAGE_PATH      = os.path.abspath(pathlib.Path(__file__).parent)
BUILD_DIRECTORIES = ["build", "dist", PACKAGE_NAME + ".egg-info"]


def clean_package() -> None:
    
    '''
    
    Removes source distribution files and Python compiled files.
    
    '''

    for directory in BUILD_DIRECTORIES:
        
        path = os.path.join(PACKAGE_PATH, directory)
        
        if os.path.exists(path):
            
            print(f"\tDeleting directory and contents: {path}")
            
            shutil.rmtree(path)
            
        else:
            
            print(f"\tDirectory not found: {path}")
            
    for root, directories, files in os.walk(PACKAGE_PATH):
        
        for directory in directories:
                        
            if directory == "__pycache__":
                
                path = os.path.join(root, directory)
                
                print(f"\tDeleting directory and contents: {path}")
                
                shutil.rmtree(path)


if __name__ == "__main__":
    
    print("-" * 79, end = "\n\n")
    print("Beginning to build the source distribution...")
    print("\n" + "-" * 79, end = "\n\n")
    
    os.chdir(PACKAGE_PATH)
    
    print("Cleaning up old source distribution files...", end = "\n\n")
    clean_package()
    
    print("\n" + "-" * 79, end = "\n\n")
    print("Generating source distribution...", end = "\n\n")
    subprocess.run("python setup.py sdist bdist_wheel")
    
    print("\n" + "-" * 79, end = "\n\n")
    print("Checking source distribution...", end = "\n\n")
    subprocess.run("python -m twine check dist/*")
    
    print("\n" + "-" * 79, end = "\n\n")
    prompt = input("Upload to Test PyPI? [y/n]: ")
    
    if prompt.lower() in ["y", "yes", "1", "true"]:
        
        print("")
        subprocess.run(("python -m twine upload --repository-url "
                        "https://test.pypi.org/legacy/ dist/*"))
    
    print("\n" + "-" * 79, end = "\n\n")
    prompt = input("Upload to PyPI? [y/n]: ")
    
    if prompt.lower() in ["y", "yes", "1", "true"]:
        
        print("")
        subprocess.run("python -m twine upload dist/*")
    
    print("\n" + "-" * 79, end = "\n\n")
    print("Cleaning up source distribution files...", end = "\n\n")
    clean_package()
