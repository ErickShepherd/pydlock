#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

A package for encrypting files with a password.

Software:      Pydlock
Author:        Erick Edward Shepherd
E-mail:        Contact@ErickShepherd.com
GitHub:        https://www.github.com/ErickShepherd/pydlock
PyPI:          https://pypi.org/project/pydlock/
Date created:  2020-04-12
Last modified: 2020-04-30


Description:
    
    A package for encrypting files with a password.


Usage:

    This package may be imported for use in other Python modules.
    
    Example:
    
        import pydlock
        
        filename = "secret.txt"
                
        with open(filename, "w+") as file:
            
            print("Shh! It's a secret!", file = file)
            
        pydlock.lock(filename)
    

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
import subprocess
from base64 import urlsafe_b64encode
from getpass import getpass
from hashlib import sha256

# Third party imports.
from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

# Local application imports.
from pydlock import constants
from pydlock.constants import DEFAULT_ENCODING

# Dunder definitions.
#  - Versioning system: major.minor[.maintenance[.build]]
__author__  = constants.__author__
__version__ = constants.__version__


def password_prompt(encoding : str = DEFAULT_ENCODING,
                    prompt   : str = "Enter password: ") -> str:
    
    '''
    
    Prompts the user for a password and uses the input to generate a Fernet
    cryptographic key.
    
    '''
    
    # Accepts a string password from the user, converts it into an SHA 256-bit
    # hex digest, truncates the result to 32 characters, and encodes it into a
    # URL-safe base-64 bytes object, which is then used as the cipher key.
    password = getpass(prompt)
    digest   = sha256(password.encode(encoding)).hexdigest()
    key      = urlsafe_b64encode(digest.encode(encoding)[:32])
    
    return key


def double_password_prompt(encoding : str = DEFAULT_ENCODING) -> str:
    
    '''
    
    Prompts and re-prompts the user for a password and uses the input to
    generate a Fernet cryptographic key. If the passwords do not match, the
    user is prompted to retry.
    
    '''
    
    key1 = "default1"
    key2 = "default2"
        
    while key1 != key2:
        
        key1 = password_prompt(encoding, "Enter password: ")
        key2 = password_prompt(encoding, "Re-enter password: ")
        
        if key1 != key2:
            
            print("Password entries do not match. Try again.", end = "\n\n")
     
    return key1
            

def encrypt(path     : str,
            encoding : str   = DEFAULT_ENCODING,
            key      : bytes = None) -> str:
    
    '''
    
    Decrypts the contents of a file.
    
    '''
    
    if key is None:
        
        key = double_password_prompt(encoding)
    
    with open(path, "r", encoding = encoding) as file:
        
        contents = file.read().encode(encoding)
    
    token = Fernet(key).encrypt(contents)
    token = token.decode(encoding)
    
    return token


def decrypt(path     : str,
            encoding : str   = DEFAULT_ENCODING,
            key      : bytes = None) -> str:
    
    '''
    
    Decrypts the contents of a file.
    
    '''
    
    if key is None:
    
        key = password_prompt(encoding)
    
    with open(path, "r", encoding = encoding) as file:
        
        token = file.read().encode(encoding)
    
    # Attempts to decrypt the token using the supplied key.
    try:
    
        contents = Fernet(key).decrypt(token)
        contents = contents.decode(encoding)
        
        return contents
            
    except (InvalidToken, InvalidSignature):
        
        print("Incorrect password.")
        
        return None


def lock(path      : str,
         arguments : str   = "",
         encoding  : str   = DEFAULT_ENCODING,
         key       : bytes = None) -> None:
    
    '''
    
    Encrypts a file.
    
    '''
    
    token = encrypt(path, encoding, key)
    
    with open(path, "w+", encoding = encoding) as file:
        
        file.write(token)
        
        
def unlock(path      : str,
           arguments : str   = "",
           encoding  : str   = DEFAULT_ENCODING,
           key       : bytes = None) -> bool:
    
    '''
    
    Decrypts a file. Returns True if decryption was successful, and False
    otherwise.
    
    '''
    
    contents = decrypt(path, encoding, key)
    
    if contents is not None:
    
        with open(path, "w+", encoding = encoding) as file:
        
            file.write(contents)
            
        return True
    
    else:
        
        return False


def python(path      : str,
           arguments : str   = "",
           encoding  : str   = DEFAULT_ENCODING,
           key       : bytes = None) -> None:
    
    '''
    
    Decrypts and executes the contents of an encrypted Python file.
    
    '''
    
    contents = decrypt(path, encoding, key)
    
    if contents is not None:
    
        exec(contents)


def run(path      : str,
        arguments : str   = "",
        encoding  : str   = DEFAULT_ENCODING,
        key       : bytes = None) -> None:
    
    '''
    
    Temporarily decrypts a program and executes it with the supplied arguments
    before re-encrypting it.
    
    '''
    
    if key is None:
        
        key = password_prompt()
    
    # Temporarily decrypts the file in order to run it.
    successful_unlock = unlock(path, arguments, encoding, key)
    
    if successful_unlock:
    
        # Attempts to run the file with the supplied arguments.
        command = path + " " + arguments
        subprocess.run(command, shell = True)

        # Temporarily re-encrypts the file after the run attempt is completed.
        lock(path, arguments, encoding, key)
