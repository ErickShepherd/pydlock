#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

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
import json
import os
import subprocess
from base64 import b64decode
from base64 import b64encode
from base64 import urlsafe_b64encode
from getpass import getpass

# Third party imports.
from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# Local application imports.
from pydlock import constants
from pydlock.constants import DEFAULT_ENCODING

# Dunder definitions.
__author__  = constants.__author__
__version__ = constants.__version__

# Envelope + KDF parameters (see the design doc, "The envelope format").
MAGIC_PREFIX = b"PYDLOCK\x02"          # self-identifying v2 marker (vs Fernet's "gA...")
MAGIC_V2     = MAGIC_PREFIX + b"\n"    # full magic line written at the head of a v2 file
SALT_BYTES   = 16                      # per-file random salt, from os.urandom
KEY_LENGTH   = 32                      # derived key length in bytes (pre-base64)
SCRYPT_N     = 2 ** 15                 # scrypt cost parameter (32768); interactive-login-grade
SCRYPT_R     = 8                       # scrypt block size
SCRYPT_P     = 1                       # scrypt parallelisation


def password_prompt(encoding : str = DEFAULT_ENCODING,
                    prompt   : str = "Enter password: ") -> bytes:

    '''

    Prompts the user for a password and returns it encoded as bytes. Key
    derivation is deferred to ``encrypt``/``decrypt``, where the per-file salt
    is available.

    '''

    password = getpass(prompt)

    return password.encode(encoding)


def double_password_prompt(encoding : str = DEFAULT_ENCODING) -> bytes:

    '''

    Prompts and re-prompts the user for a password, returning it encoded as
    bytes. If the two entries do not match, the user is prompted to retry.

    '''

    while True:

        password1 = password_prompt(encoding, "Enter password: ")
        password2 = password_prompt(encoding, "Re-enter password: ")

        if password1 == password2:

            return password1

        print("Password entries do not match. Try again.", end = "\n\n")


def _derive_scrypt_key(password : bytes,
                       salt     : bytes,
                       n        : int,
                       r        : int,
                       p        : int) -> bytes:

    '''

    Derives a URL-safe base64 Fernet key from a password and salt via scrypt.

    '''

    kdf = Scrypt(salt = salt, length = KEY_LENGTH, n = n, r = r, p = p)

    return urlsafe_b64encode(kdf.derive(password))


def _derive_key(header : dict, password : bytes) -> bytes:

    '''

    Re-derives the Fernet key for a parsed v2 envelope header, dispatching on
    the ``kdf`` identifier. An unknown identifier raises ``ValueError`` rather
    than risking a silent mis-decryption. The dispatch is intentionally left
    open for a documented ``"pbkdf2"`` fallback id.

    '''

    kdf_id = header.get("kdf")

    if kdf_id == "scrypt":

        salt = b64decode(header["salt"])

        return _derive_scrypt_key(password, salt,
                                  header["n"], header["r"], header["p"])

    raise ValueError(
        f"Unsupported KDF identifier {kdf_id!r} in pydlock envelope header."
    )


def encrypt(path     : str,
            encoding : str   = DEFAULT_ENCODING,
            password : bytes = None) -> bytes:

    '''

    Encrypts the contents of a file and returns the v2 envelope bytes: the
    magic prefix, a JSON header carrying the KDF parameters and per-file salt,
    a newline, and the Fernet token.

    '''

    if password is None:

        password = double_password_prompt(encoding)

    with open(path, "r", encoding = encoding) as file:

        contents = file.read().encode(encoding)

    # Derives a fresh key from a per-file random salt.
    salt = os.urandom(SALT_BYTES)
    key  = _derive_scrypt_key(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)

    token = Fernet(key).encrypt(contents)

    header = {
        "kdf"  : "scrypt",
        "n"    : SCRYPT_N,
        "r"    : SCRYPT_R,
        "p"    : SCRYPT_P,
        "salt" : b64encode(salt).decode("ascii"),
    }
    header_bytes = json.dumps(header, separators = (",", ":")).encode("utf-8")

    return MAGIC_V2 + header_bytes + b"\n" + token


def decrypt(path     : str,
            encoding : str   = DEFAULT_ENCODING,
            password : bytes = None) -> str:

    '''

    Decrypts a v2 pydlock file and returns its plaintext. Parses the envelope
    header, re-derives the key from the stored salt and parameters, and lets
    Fernet verify the token (a tampered header/token fails the HMAC cleanly
    rather than yielding wrong plaintext).

    '''

    if password is None:

        password = password_prompt(encoding)

    with open(path, "rb") as file:

        data = file.read()

    if not data.startswith(MAGIC_PREFIX):

        # v1 legacy files (no magic) are handled in a later change; for now a
        # non-v2 file is an explicit error, never a silent mis-decrypt.
        raise ValueError("Not a pydlock v2 file (missing envelope magic).")

    # Splits off the magic line, then the JSON header line, leaving the token.
    _, _, remainder        = data.partition(b"\n")
    header_bytes, _, token = remainder.partition(b"\n")
    header = json.loads(header_bytes.decode("utf-8"))

    key = _derive_key(header, password)

    # Attempts to decrypt the token using the derived key.
    try:

        contents = Fernet(key).decrypt(token)

        return contents.decode(encoding)

    except (InvalidToken, InvalidSignature):

        print("Incorrect password.")

        return None


def lock(path      : str,
         arguments : str   = "",
         encoding  : str   = DEFAULT_ENCODING,
         password  : bytes = None) -> None:

    '''

    Encrypts a file in place, replacing its contents with the v2 envelope.

    '''

    envelope = encrypt(path, encoding, password)

    with open(path, "wb") as file:

        file.write(envelope)


def unlock(path      : str,
           arguments : str   = "",
           encoding  : str   = DEFAULT_ENCODING,
           password  : bytes = None) -> bool:

    '''

    Decrypts a file in place. Returns True if decryption was successful, and
    False otherwise.

    '''

    contents = decrypt(path, encoding, password)

    if contents is not None:

        with open(path, "w+", encoding = encoding) as file:

            file.write(contents)

        return True

    else:

        return False


def python(path      : str,
           arguments : str   = "",
           encoding  : str   = DEFAULT_ENCODING,
           password  : bytes = None) -> None:

    '''

    Decrypts and executes the contents of an encrypted Python file.

    '''

    contents = decrypt(path, encoding, password)

    if contents is not None:

        exec(contents)


def run(path      : str,
        arguments : str   = "",
        encoding  : str   = DEFAULT_ENCODING,
        password  : bytes = None) -> None:

    '''

    Temporarily decrypts a program and executes it with the supplied arguments
    before re-encrypting it.

    '''

    if password is None:

        password = password_prompt()

    # Temporarily decrypts the file in order to run it.
    successful_unlock = unlock(path, arguments, encoding, password)

    if successful_unlock:

        # Attempts to run the file with the supplied arguments.
        command = path + " " + arguments
        subprocess.run(command, shell = True)

        # Temporarily re-encrypts the file after the run attempt is completed.
        lock(path, arguments, encoding, password)
