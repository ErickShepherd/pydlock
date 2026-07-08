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
import tempfile
from base64 import b64decode
from base64 import b64encode
from base64 import urlsafe_b64encode
from getpass import getpass
from hashlib import sha256

# Third party imports.
from cryptography.exceptions import InternalError
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

# Hard ceilings on the attacker-controlled scrypt parameters read from an
# UNTRUSTED file header. scrypt memory is ~= 128 * n * r bytes, so an
# unbounded n (or r) in a crafted envelope would force the victim's decrypt to
# allocate arbitrary memory (OOM/hang). These bounds sit comfortably above the
# encrypt-time defaults above yet cap the worst case: at the ceilings scrypt
# needs ~= 128 * 2**20 * 32 = 4 GiB, so a header outside them is treated as a
# corrupt/incompatible file, never as a valid instruction to allocate.
SCRYPT_MAX_N   = 2 ** 20               # ceiling on n (must also be a power of two)
SCRYPT_MAX_R   = 32                    # ceiling on the block size r
SCRYPT_MAX_P   = 16                    # ceiling on the parallelisation p
MAX_SALT_BYTES = 1024                  # ceiling on the decoded per-file salt length

# Per-factor ceilings alone are NOT enough: n and r each at their (individually
# legal) ceiling still multiply to a ~4 GiB allocation (128 * 2**20 * 32), and a
# large p at the memory ceiling forces a bounded-but-large CPU burn (scrypt work
# ~ n * r * p). We therefore bound the total COST PRODUCT (128 * n * r * p). The
# encrypt-time default (n=2**15, r=8, p=1) needs ~32 MiB, so a 256 MiB budget
# leaves 8x headroom for a user who deliberately raises the cost while still
# capping the worst case (~256 MiB / ~0.5s). A header exceeding this budget is
# treated as corrupt/incompatible, never as a valid instruction to allocate/burn.
MAX_SCRYPT_MEM_BYTES = 256 * 1024 * 1024   # cost budget on 128 * n * r * p


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


def _validate_scrypt_params(n : object, r : object, p : object,
                            salt : bytes) -> None:

    '''

    Validates and hard-bounds the scrypt parameters read from an UNTRUSTED file
    header BEFORE any key derivation. The parameters must be integers within
    fixed ceilings (``n`` a power of two and ``<= SCRYPT_MAX_N``, ``r <=
    SCRYPT_MAX_R``, ``p <= SCRYPT_MAX_P``) and the decoded salt no longer than
    ``MAX_SALT_BYTES``. The per-factor ceilings are NOT sufficient on their own
    (n and r each at their ceiling still multiply out to a ~4 GiB allocation),
    so the total scrypt COST PRODUCT (128 * n * r * p — folding in p, which
    multiplies CPU work) is additionally bounded by ``MAX_SCRYPT_MEM_BYTES``.
    Anything outside these bounds raises ``ValueError`` and is treated by
    ``decrypt`` as a corrupt/incompatible file, never as a valid instruction to
    allocate arbitrary memory or burn arbitrary CPU.

    '''

    # bool is a subclass of int; reject it so ``true``/``false`` in a crafted
    # header cannot slip through as 1/0.
    for name, value in (("n", n), ("r", r), ("p", p)):

        if not isinstance(value, int) or isinstance(value, bool):

            raise ValueError(f"scrypt parameter {name!r} must be an integer.")

    if n < 2 or n > SCRYPT_MAX_N or (n & (n - 1)) != 0:

        raise ValueError(
            f"scrypt parameter 'n' out of bounds: must be a power of two in "
            f"[2, {SCRYPT_MAX_N}]."
        )

    if r < 1 or r > SCRYPT_MAX_R:

        raise ValueError(
            f"scrypt parameter 'r' out of bounds: must be in [1, {SCRYPT_MAX_R}]."
        )

    if p < 1 or p > SCRYPT_MAX_P:

        raise ValueError(
            f"scrypt parameter 'p' out of bounds: must be in [1, {SCRYPT_MAX_P}]."
        )

    # Bound the total COST, not just the individual factors: n and r each within
    # their per-factor ceiling can still multiply to a multi-GiB allocation, and
    # p (parallelism) multiplies scrypt's CPU work (~ n * r * p) even though peak
    # memory is ~= 128 * n * r. Folding p into the product caps BOTH the memory
    # bomb (p=1) and the CPU-amplification bomb (large p at the memory ceiling).
    # Reject before Scrypt is ever constructed.
    if 128 * n * r * p > MAX_SCRYPT_MEM_BYTES:

        raise ValueError(
            f"scrypt parameters demand too much work: 128 * n * r * p = "
            f"{128 * n * r * p} exceeds the {MAX_SCRYPT_MEM_BYTES} cost budget."
        )

    if len(salt) > MAX_SALT_BYTES:

        raise ValueError(
            f"scrypt salt too long: {len(salt)} bytes exceeds {MAX_SALT_BYTES}."
        )


def _derive_key(header : dict, password : bytes) -> bytes:

    '''

    Re-derives the Fernet key for a parsed v2 envelope header, dispatching on
    the ``kdf`` identifier. An unknown identifier raises ``ValueError`` rather
    than risking a silent mis-decryption. The dispatch is intentionally left
    open for a documented ``"pbkdf2"`` fallback id. The attacker-controlled
    scrypt parameters are validated and hard-bounded before any key derivation.

    '''

    kdf_id = header.get("kdf")

    if kdf_id == "scrypt":

        n, r, p = header["n"], header["r"], header["p"]
        salt    = b64decode(header["salt"])

        _validate_scrypt_params(n, r, p, salt)

        return _derive_scrypt_key(password, salt, n, r, p)

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
            encoding : str                  = DEFAULT_ENCODING,
            password : str | bytes | None = None) -> bytes:

    '''

    Encrypts the contents of a file and returns the v2 envelope bytes: the
    magic prefix, a JSON header carrying the KDF parameters and per-file salt,
    a newline, and the Fernet token.

    The ``password`` may be passed as ``str`` or ``bytes`` (or omitted, to
    prompt): a ``str`` is encoded to bytes with ``encoding`` at this public API
    boundary, since scrypt operates on bytes.

    '''

    if password is None:

        password = double_password_prompt(encoding)

    # Normalise the password to bytes at the public API boundary: a library
    # caller may pass a str, but scrypt (and the v1 legacy SHA-256 path) needs
    # bytes. The CLI/getpass paths already yield bytes and pass through here
    # unchanged.
    if isinstance(password, str):

        password = password.encode(encoding)

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
            encoding : str                  = DEFAULT_ENCODING,
            password : str | bytes | None = None) -> bytes | None:

    '''

    Decrypts a pydlock file and returns its plaintext bytes. A v2 file (magic
    prefix) is read via the envelope header (key re-derived from the stored
    salt and parameters); a non-magic file is treated as a legacy v1 raw Fernet
    token and read with the old scheme, so no existing file is stranded
    (re-locking rewrites it as v2). Fernet verifies the token, so a wrong
    password or a tampered header/token fails cleanly rather than yielding
    wrong plaintext.

    The ``password`` may be passed as ``str`` or ``bytes`` (or omitted, to
    prompt): a ``str`` is encoded to bytes with ``encoding`` at this public API
    boundary, covering both the v2 scrypt path and the v1 legacy path.

    '''

    if password is None:

        password = password_prompt(encoding)

    # Normalise the password to bytes ONCE, before the v2/v1 branch below, so
    # both the scrypt (v2) and legacy SHA-256 (v1) key derivations receive
    # bytes regardless of whether the caller passed a str or bytes.
    if isinstance(password, str):

        password = password.encode(encoding)

    with open(path, "rb") as file:

        data = file.read()

    # The v2 header decode, parameter validation, key derivation, and Fernet
    # decrypt all share one failure path: a wrong password, a tampered token,
    # OR a malformed/oversized header (bad JSON, missing/mistyped/out-of-bounds
    # scrypt params, non-base64 salt, unknown kdf) returns None cleanly instead
    # of leaking a raw traceback or attempting an attacker-sized allocation.
    try:

        if data.startswith(MAGIC_PREFIX):

            # v2: split off the magic line, then the JSON header line, leaving
            # the token, and re-derive the key from the header's salt and
            # (validated) parameters.
            _, _, remainder        = data.partition(b"\n")
            header_bytes, _, token = remainder.partition(b"\n")
            header = json.loads(header_bytes.decode("utf-8"))

            key = _derive_key(header, password)

        else:

            # v1 legacy: the whole file is a raw Fernet token whose key came
            # from the old unsalted SHA-256-truncation scheme. Read it
            # transparently.
            key   = _derive_legacy_key(password)
            token = data

        return Fernet(key).decrypt(token)

    except (InvalidToken, InvalidSignature):

        print("Incorrect password.")

        return None

    # A malformed or incompatible envelope: json.JSONDecodeError and
    # binascii.Error are both ValueError subclasses; KeyError covers a missing
    # header field; TypeError covers a value of the wrong shape. The scrypt
    # bounds (including the 128*n*r memory product) are enforced (ValueError)
    # BEFORE Scrypt is ever constructed, so a huge allocation never fires.
    # MemoryError and InternalError are caught as defence in depth: even if some
    # param slipped through, a memory failure (or OpenSSL's own N < 2**(16*r)
    # check surfacing) yields the clean sentinel, never a raw traceback.
    except (ValueError, KeyError, TypeError, MemoryError, InternalError):

        print("File is corrupted or incompatible.")

        return None


def lock(path     : str,
         encoding : str                  = DEFAULT_ENCODING,
         password : str | bytes | None = None) -> None:

    '''

    Encrypts a file in place, replacing its contents with the v2 envelope.

    '''

    envelope = encrypt(path, encoding, password)

    _atomic_write(path, envelope)


def unlock(path     : str,
           encoding : str                  = DEFAULT_ENCODING,
           password : str | bytes | None = None) -> bool:

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
