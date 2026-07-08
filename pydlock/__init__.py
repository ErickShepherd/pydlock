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
import tempfile
from base64 import b64decode
from base64 import b64encode
from base64 import urlsafe_b64encode
from getpass import getpass
from hashlib import sha256

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


def _derive_legacy_key(password : bytes) -> bytes:

    '''

    Re-derives the v1 (pre-2.0) Fernet key from a password, byte-for-byte with
    the old scheme: an unsalted SHA-256 hex digest truncated to 32 characters.
    Used only to transparently read legacy files; ``lock`` never writes it.

    '''

    digest = sha256(password).hexdigest()

    return urlsafe_b64encode(digest[:32].encode())


def _atomic_write(path : str, data : bytes) -> None:

    '''

    Writes bytes to a path atomically: the data is written to a temp file in
    the same directory, flushed to disk, then swapped into place with
    ``os.replace``. An interrupted write can never leave a partially written
    or truncated file (unlike the previous in-place ``"w+"`` truncate).

    '''

    directory       = os.path.dirname(os.path.abspath(path))
    file_descriptor, temporary_path = tempfile.mkstemp(dir    = directory,
                                                       prefix = ".pydlock-",
                                                       suffix = ".tmp")

    try:

        with os.fdopen(file_descriptor, "wb") as file:

            file.write(data)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, path)

    except BaseException:

        # Best-effort cleanup of the temp file on any failure.
        try:

            os.remove(temporary_path)

        except OSError:

            pass

        raise


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

    # Reads the plaintext as raw bytes so binary files (and Windows
    # executables) round-trip losslessly; only the password uses ``encoding``.
    with open(path, "rb") as file:

        contents = file.read()

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
            password : bytes = None) -> bytes:

    '''

    Decrypts a pydlock file and returns its plaintext bytes. A v2 file (magic
    prefix) is read via the envelope header (key re-derived from the stored
    salt and parameters); a non-magic file is treated as a legacy v1 raw Fernet
    token and read with the old scheme, so no existing file is stranded
    (re-locking rewrites it as v2). Fernet verifies the token, so a wrong
    password or a tampered header/token fails cleanly rather than yielding
    wrong plaintext.

    '''

    if password is None:

        password = password_prompt(encoding)

    with open(path, "rb") as file:

        data = file.read()

    if data.startswith(MAGIC_PREFIX):

        # v2: split off the magic line, then the JSON header line, leaving the
        # token, and re-derive the key from the header's salt and parameters.
        _, _, remainder        = data.partition(b"\n")
        header_bytes, _, token = remainder.partition(b"\n")
        header = json.loads(header_bytes.decode("utf-8"))

        key = _derive_key(header, password)

    else:

        # v1 legacy: the whole file is a raw Fernet token whose key came from
        # the old unsalted SHA-256-truncation scheme. Read it transparently.
        key   = _derive_legacy_key(password)
        token = data

    # Attempts to decrypt the token using the derived key.
    try:

        return Fernet(key).decrypt(token)

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

    _atomic_write(path, envelope)


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

        _atomic_write(path, contents)

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
