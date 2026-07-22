#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

'''

A package for encrypting files with a password.

Software:      Pydlock
Author:        Erick Edward Shepherd
E-mail:        dev@erickshepherd.com
GitHub:        https://www.github.com/ErickShepherd/pydlock
PyPI:          https://pypi.org/project/pydlock/
Date created:  2020-04-12
Last modified: 2026-07-08


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

'''


# Standard library imports.
import json
import os
import shutil
import stat
import sys
import tempfile
from base64 import b64decode
from base64 import b64encode
from base64 import urlsafe_b64decode
from base64 import urlsafe_b64encode
from getpass import getpass
from hashlib import sha256
from typing import NamedTuple

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

# Ceiling on the raw JSON header bytes read from an UNTRUSTED envelope, enforced
# BEFORE json.loads. A well-formed header is ~100 bytes; this generous bound
# rejects a pathologically large header (memory) as a corrupt/incompatible file
# rather than feeding it to the parser. Note this alone does NOT stop a deeply
# NESTED-but-small header (a few KiB of nested brackets already exceeds the
# interpreter's recursion limit), so decrypt additionally catches RecursionError.
MAX_HEADER_BYTES = 64 * 1024               # ceiling on the raw JSON header length

# True on POSIX, where os.open can refuse to traverse a final-component symlink
# atomically. Absent on Windows, where we fall back to an explicit (racy)
# os.path.islink pre-check and document the reduced guarantee.
_HAS_O_NOFOLLOW = hasattr(os, "O_NOFOLLOW")


class PydlockError(Exception):

    '''Base class for pydlock operational errors surfaced to a caller/CLI.'''


class UnsupportedFileTypeError(PydlockError):

    '''

    Raised when a target is not a plain, singly-linked regular file: a symlink,
    a directory/device/FIFO, or a file with more than one hard link. pydlock
    replaces a file by atomically renaming a new inode over the path, which
    would silently leave plaintext reachable through the OTHER alias (the symlink
    target, or a second hard-link name). Rather than guess which name the caller
    meant, pydlock refuses these targets outright.

    '''


class ConcurrentModificationError(PydlockError):

    '''

    Raised when the target changed between the moment pydlock read it and the
    moment it was about to be replaced (a concurrent writer, or a path swap).
    pydlock aborts WITHOUT replacing so a newer version is never overwritten.

    '''


class _FileIdentity(NamedTuple):

    '''

    A snapshot of the identity + content-metadata of the file pydlock read,
    captured from the SAME open file descriptor it read from. Compared against a
    fresh ``lstat`` of the path immediately before replacement to detect a
    concurrent edit (``st_size``/``st_mtime_ns`` change) or a path swap
    (``st_dev``/``st_ino`` change).

    '''

    st_dev      : int
    st_ino      : int
    st_size     : int
    st_mtime_ns : int


def _read_all(file_descriptor : int) -> bytes:

    '''Reads an open file descriptor to EOF and returns its bytes.'''

    chunks = []

    while True:

        chunk = os.read(file_descriptor, 1 << 20)

        if not chunk:

            break

        chunks.append(chunk)

    return b"".join(chunks)


def _read_decrypt_input(file_descriptor : int) -> bytes:

    '''

    Reads a prospective pydlock file without first accepting an unbounded v2
    header into memory. Legacy v1 tokens still require a whole-file read, as do
    valid v2 Fernet tokens, but a file beginning with the v2 magic is consumed
    only through ``MAX_HEADER_BYTES + 1`` header bytes until its separator is
    found. A malformed magic line or oversized/missing-separator header is
    returned in its bounded form for ``_decrypt_data`` to reject cleanly.

    '''

    prefix = bytearray()

    while len(prefix) < len(MAGIC_PREFIX):

        chunk = os.read(file_descriptor, len(MAGIC_PREFIX) - len(prefix))

        if not chunk:

            break

        prefix.extend(chunk)

    if bytes(prefix) != MAGIC_PREFIX:

        return bytes(prefix) + _read_all(file_descriptor)

    magic_terminator = os.read(file_descriptor, 1)

    if magic_terminator != b"\n":

        return bytes(prefix) + magic_terminator

    header = bytearray()

    while len(header) <= MAX_HEADER_BYTES:

        remaining = MAX_HEADER_BYTES + 1 - len(header)
        chunk = os.read(file_descriptor, min(1 << 12, remaining))

        if not chunk:

            return MAGIC_V2 + bytes(header)

        separator_at = chunk.find(b"\n")

        if separator_at >= 0:

            header.extend(chunk[:separator_at])
            token_prefix = chunk[separator_at + 1:]

            return (MAGIC_V2 + bytes(header) + b"\n" + token_prefix
                    + _read_all(file_descriptor))

        header.extend(chunk)

    return MAGIC_V2 + bytes(header)


def _open_and_read_regular(path   : str,
                           reader = _read_all) -> tuple[_FileIdentity, bytes]:

    '''

    Opens ``path``, enforces the filesystem-safety contract, reads it with
    ``reader``, and returns ``(_FileIdentity, contents)``. The identity is taken
    from the SAME descriptor the contents are read from, so there is no re-open
    race between the type/link checks and the read. The default reader consumes
    the whole file; decrypt/unlock supply ``_read_decrypt_input`` so an invalid
    v2 header is bounded before the whole Fernet token is read.

    Rejections (all raise ``UnsupportedFileTypeError``):

      * a symlink — on POSIX ``O_NOFOLLOW`` makes ``os.open`` fail atomically; on
        Windows a best-effort ``os.path.islink`` pre-check is used instead (a
        small TOCTOU window remains — the strongest available equivalent, see the
        module docs / README security-boundary section);
      * a non-regular file (directory, device, FIFO, socket);
      * a file with ``st_nlink != 1`` (a hard-linked inode reachable by another
        name that the atomic replace would not cover).

    '''

    # Windows lacks O_NOFOLLOW and rejects opening a directory with EACCES before
    # fstat can classify it. Use one best-effort lstat preflight there for both
    # cases; the descriptor-based authoritative regular-file/link-count checks
    # below still protect the object that was actually opened.
    if not _HAS_O_NOFOLLOW:

        preliminary = os.lstat(path)

        if stat.S_ISLNK(preliminary.st_mode):

            raise UnsupportedFileTypeError(
                f"{path!r} is a symlink; refusing to operate through it."
            )

        if not stat.S_ISREG(preliminary.st_mode):

            raise UnsupportedFileTypeError(
                f"{path!r} is not a regular file; refusing to operate on it."
            )

    # O_BINARY: no newline translation on Windows. O_NONBLOCK: opening a FIFO or
    # device read-only would otherwise BLOCK waiting for a peer; with it the open
    # returns and the fstat below rejects the non-regular file instead of hanging
    # (O_NONBLOCK is a no-op on a regular file).
    open_flags = (os.O_RDONLY
                  | getattr(os, "O_BINARY", 0)
                  | getattr(os, "O_NONBLOCK", 0))

    if _HAS_O_NOFOLLOW:

        open_flags |= os.O_NOFOLLOW

    try:

        file_descriptor = os.open(path, open_flags)

    except OSError as error:

        # With O_NOFOLLOW a symlink final component fails with ELOOP; translate
        # that one case into the clear domain error, and re-raise anything else
        # (ENOENT, EACCES, …) unchanged for the caller/CLI to report.
        if _HAS_O_NOFOLLOW and os.path.islink(path):

            raise UnsupportedFileTypeError(
                f"{path!r} is a symlink; refusing to operate through it."
            ) from error

        raise

    try:

        info = os.fstat(file_descriptor)

        if not stat.S_ISREG(info.st_mode):

            raise UnsupportedFileTypeError(
                f"{path!r} is not a regular file; refusing to operate on it."
            )

        if info.st_nlink != 1:

            raise UnsupportedFileTypeError(
                f"{path!r} has {info.st_nlink} hard links; refusing to encrypt "
                f"one name while the plaintext stays reachable through another."
            )

        contents = reader(file_descriptor)

        identity = _FileIdentity(info.st_dev, info.st_ino,
                                 info.st_size, info.st_mtime_ns)

        return identity, contents

    finally:

        os.close(file_descriptor)


def _verify_unchanged(path : str, expected : _FileIdentity) -> None:

    '''

    Raises ``ConcurrentModificationError`` unless ``path`` still names the same,
    unchanged regular file that was read (identity ``expected``). Called
    immediately before ``os.replace`` so a concurrent edit or a path swap — a
    rename over the path, or a symlink/hard link swapped in — is detected and the
    replace is aborted, never overwriting newer contents. A tiny window remains
    between this check and the replace (no portable rename-if-unchanged exists);
    the check shrinks it to near-zero, the conservative contract in the plan.

    '''

    # lstat (not stat) so a symlink swapped in over the path is caught here
    # rather than silently followed.
    current = os.lstat(path)

    if stat.S_ISLNK(current.st_mode):

        raise ConcurrentModificationError(
            f"{path!r} was replaced by a symlink after it was read; "
            f"refusing to overwrite."
        )

    if not stat.S_ISREG(current.st_mode) or current.st_nlink != 1:

        raise ConcurrentModificationError(
            f"{path!r} changed type/link-count after it was read; "
            f"refusing to overwrite."
        )

    now = _FileIdentity(current.st_dev, current.st_ino,
                        current.st_size, current.st_mtime_ns)

    if now != expected:

        raise ConcurrentModificationError(
            f"{path!r} changed on disk between read and write; refusing to "
            f"overwrite newer contents."
        )


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

        if password1 != password2:

            print("Password entries do not match. Try again.", end = "\n\n")

            continue

        # An empty password gives no protection (see _encrypt_contents); re-ask
        # rather than accept it and fail later.
        if password1 == b"":

            print("Password must not be empty. Try again.", end = "\n\n")

            continue

        return password1


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


def _strict_b64decode(text : str | bytes, *, urlsafe : bool) -> bytes:

    '''

    Decodes base64 STRICTLY: rejects any input that is not the exact canonical
    encoding of the bytes it decodes to. The stdlib decoders default to
    ``validate=False``, which silently DISCARDS characters outside the base64
    alphabet — so appended garbage (e.g. ``b"!!!"`` after a Fernet token) would
    decode to the same bytes and pass unnoticed. Requiring ``encode(decode(x))
    == x`` rejects trailing garbage, embedded non-alphabet bytes, and
    non-canonical padding. Raises ``ValueError`` (incl. ``binascii.Error`` and
    ``UnicodeEncodeError``, both ``ValueError`` subclasses) on any deviation.

    '''

    raw = text.encode("ascii") if isinstance(text, str) else text

    decoder = urlsafe_b64decode if urlsafe else b64decode
    encoder = urlsafe_b64encode if urlsafe else b64encode

    decoded = decoder(raw)

    if encoder(decoded) != raw:

        raise ValueError("non-canonical base64 (trailing garbage or padding).")

    return decoded


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

        # Strict standard base64 (rejects noncanonical/garbage), and require the
        # exact per-file salt length the v2 format promises — a wrong length is a
        # corrupt/incompatible file, not a valid instruction.
        salt = _strict_b64decode(header["salt"], urlsafe = False)

        if len(salt) != SALT_BYTES:

            raise ValueError(
                f"pydlock v2 salt must be exactly {SALT_BYTES} bytes, "
                f"got {len(salt)}."
            )

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


def _fsync_directory(directory : str) -> bool:

    '''

    Fsyncs a directory entry so a rename into it is durable across a power loss
    (POSIX). Returns ``True`` when the directory was fsynced, ``False`` when the
    platform cannot do it — Windows has no directory file descriptor to fsync,
    and some filesystems reject ``fsync`` on a directory. In the ``False`` case
    ONLY atomic replacement is established, not full power-loss durability; the
    caller/docs must not overstate the guarantee. This is a best-effort durability
    step and never raises: an inability to fsync the directory does not undo the
    (already completed) atomic replace.

    '''

    # Windows has no O_DIRECTORY / directory-fd fsync; fail honestly.
    if not hasattr(os, "O_DIRECTORY"):

        return False

    try:

        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)

    except OSError:

        return False

    try:

        os.fsync(directory_fd)

    except OSError:

        # Some filesystems don't support directory fsync (returns EINVAL, …).
        return False

    finally:

        os.close(directory_fd)

    return True


def _atomic_write(path             : str,
                  data             : bytes,
                  expected_identity : _FileIdentity | None = None) -> None:

    '''

    Writes bytes to a path atomically and — where the platform supports it —
    durably. The sequence is:

      1. write the data to a temp file in the same directory;
      2. apply the target's metadata (mode, then best-effort owner/group) to the
         temp BEFORE the final fsync, so the durable inode already carries them;
      3. ``fsync`` the temp so the prepared file (data + metadata) is durable;
      4. revalidate identity (see ``_verify_unchanged``) and ``os.replace`` —
         the replace happens only after the prepared file is durable;
      5. ``fsync`` the parent directory so the rename itself is durable.

    Atomicity (an interrupted write never leaves a truncated/partial file) holds
    on every platform. Full power-loss DURABILITY additionally requires steps 3
    and 5; step 5 is unavailable on Windows and on some filesystems
    (``_fsync_directory`` returns ``False`` there), where only atomic replacement
    is guaranteed. The docs state this precisely rather than claiming uniform
    crash-safety.

    If ``expected_identity`` is supplied, the destination is revalidated against
    it immediately before the replace: a concurrent edit or a path swap aborts
    the write WITHOUT replacing, so newer contents are never overwritten.

    '''

    directory       = os.path.dirname(os.path.abspath(path))
    file_descriptor, temporary_path = tempfile.mkstemp(dir    = directory,
                                                       prefix = ".pydlock-",
                                                       suffix = ".tmp")

    try:

        with os.fdopen(file_descriptor, "wb") as file:

            file.write(data)
            file.flush()

            # Apply metadata BEFORE the final fsync so the durable inode already
            # carries it. mkstemp creates the temp 0600, so without this the
            # atomic swap would silently tighten a 0644 target on every
            # round-trip. chown runs FIRST (a non-privileged chown can clear the
            # setuid/setgid bits), then copystat sets the mode LAST so those bits
            # survive. A fresh target keeps the safe 0600 default.
            if os.path.exists(path):

                try:

                    original = os.stat(path)
                    os.chown(temporary_path, original.st_uid, original.st_gid)

                except (OSError, AttributeError):

                    # chown typically requires privilege (and os.chown is absent
                    # on Windows); preserving owner/group is best-effort only.
                    pass

                shutil.copystat(path, temporary_path)

            # Final fsync AFTER data + metadata: the prepared temp is now durable.
            os.fsync(file.fileno())

        # Revalidate the destination is still the same unchanged object we read
        # (T1): a concurrent edit or path swap is detected here and aborts the
        # write before any replace, so newer contents are never lost.
        if expected_identity is not None:

            _verify_unchanged(path, expected_identity)

        # Replace only after the prepared file is durable.
        os.replace(temporary_path, path)

        # Make the rename itself durable where supported (POSIX). On platforms
        # without directory fsync this is a no-op returning False and only atomic
        # replacement is guaranteed — the post-replace bytes are already in
        # place, so this best-effort step never raises.
        _fsync_directory(directory)

    except BaseException:

        # Best-effort cleanup of the temp file on any failure.
        try:

            os.remove(temporary_path)

        except OSError:

            pass

        raise


def _normalise_password(password : str | bytes, encoding : str) -> bytes:

    '''

    Normalises a password to bytes at the public API boundary. A library caller
    may pass a ``str``, but scrypt (and the v1 legacy SHA-256 path) needs bytes;
    a ``str`` is encoded with ``encoding``, while bytes pass through unchanged.

    '''

    if isinstance(password, str):

        return password.encode(encoding)

    return password


def _encrypt_contents(contents : bytes,
                      encoding : str,
                      password : str | bytes | None) -> bytes:

    '''

    Pure transform: encrypts plaintext bytes into v2 envelope bytes (magic line,
    JSON header with the KDF parameters and a fresh per-file salt, newline, then
    the Fernet token). No file I/O — the caller supplies the plaintext and takes
    the envelope. Prompts for a password when one is not supplied.

    '''

    if password is None:

        password = double_password_prompt(encoding)

    # Normalise the password to bytes at the public API boundary (see
    # _normalise_password). The CLI/getpass paths already yield bytes.
    password = _normalise_password(password, encoding)

    # Reject an empty password on NEW encryption (T2 / A1). scrypt makes guessing
    # expensive but cannot add entropy to an empty, universally-known password —
    # encrypting with it is protection in name only. The prompt loop already
    # re-asks on an empty entry; this also covers the library ``password=""`` /
    # ``password=b""`` path. Recovery (decrypt/unlock) still ACCEPTS an empty
    # password so a pre-existing empty-password file is never stranded.
    if password == b"":

        raise ValueError(
            "refusing to encrypt with an empty password; a password is required."
        )

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


def _decrypt_data(data     : bytes,
                  encoding : str,
                  password : str | bytes | None) -> bytes | None:

    '''

    Pure transform: decrypts pydlock file bytes into plaintext, or returns the
    clean ``None`` sentinel on any wrong-password/corrupt-file condition (with a
    single stderr diagnostic). No file I/O — the caller supplies the bytes.

    A v2 file (magic prefix) is read via the envelope header (key re-derived from
    the stored salt and parameters); a non-magic file is treated as a legacy v1
    raw Fernet token and read with the old scheme, so no existing file is
    stranded (re-locking rewrites it as v2). Fernet verifies the token, so a
    wrong password or a tampered header/token fails cleanly rather than yielding
    wrong plaintext.

    '''

    if password is None:

        password = password_prompt(encoding)

    # Normalise the password to bytes ONCE, before the v2/v1 branch below, so
    # both the scrypt (v2) and legacy SHA-256 (v1) key derivations receive bytes
    # regardless of whether the caller passed a str or bytes (see
    # _normalise_password).
    password = _normalise_password(password, encoding)

    # The v2 header decode, parameter validation, key derivation, and Fernet
    # decrypt all share one failure path: a wrong password, a tampered token,
    # OR a malformed/oversized header (bad JSON, missing/mistyped/out-of-bounds
    # scrypt params, non-base64 salt, unknown kdf) returns None cleanly instead
    # of leaking a raw traceback or attempting an attacker-sized allocation.
    try:

        if data.startswith(MAGIC_PREFIX):

            # v2: require EXACT framing, not merely the magic prefix. The magic
            # LINE must be precisely MAGIC_V2 (``PYDLOCK\x02\n``) — extra bytes
            # between the version byte and its newline (e.g. an inserted
            # ``IGNORED``) make this a non-conforming file, not a valid envelope.
            if not data.startswith(MAGIC_V2):

                raise ValueError("pydlock v2 magic line is not exactly framed.")

            remainder = data[len(MAGIC_V2):]

            # Exactly one separator between the JSON header line and the token.
            # A missing separator (no newline) is a malformed envelope.
            header_bytes, separator, token = remainder.partition(b"\n")

            if separator != b"\n":

                raise ValueError(
                    "pydlock v2 envelope is missing the header/token separator."
                )

            # Bound the raw header BEFORE parsing so a pathologically large
            # header is rejected as corrupt rather than fed to json.loads.
            if len(header_bytes) > MAX_HEADER_BYTES:

                raise ValueError(
                    f"pydlock header too long: {len(header_bytes)} bytes "
                    f"exceeds {MAX_HEADER_BYTES}."
                )

            header = json.loads(header_bytes.decode("utf-8"))

            # json.loads happily returns non-objects (int/list/str/null/…); a
            # non-dict header would make _derive_key's header.get(...) raise an
            # uncaught AttributeError on this same untrusted-input path. Reject
            # it as corrupt so decrypt still fails cleanly.
            if not isinstance(header, dict):

                raise ValueError("pydlock header must be a JSON object.")

            # The token must be present and be canonical URL-safe base64. Fernet
            # base64-decodes with the discard-non-alphabet default, so WITHOUT
            # this an empty token or trailing garbage (``token + b"!!!"``) would
            # decode to a valid token and pass. Validate before the (expensive)
            # key derivation, and re-check that the whole line is a single
            # separator-free token (an extra ``\n`` puts a newline in the token,
            # which strict base64 rejects).
            if not token:

                raise ValueError("pydlock v2 envelope has an empty token.")

            _strict_b64decode(token, urlsafe = True)

            key = _derive_key(header, password)

        else:

            # v1 legacy: the whole file is a raw Fernet token whose key came
            # from the old unsalted SHA-256-truncation scheme. Read it
            # transparently.
            key   = _derive_legacy_key(password)
            token = data

        return Fernet(key).decrypt(token)

    # Every failure mode shares one clean sentinel and one diagnostic. Fernet's
    # InvalidToken/InvalidSignature cover BOTH a wrong password and a
    # tampered/corrupt token indistinguishably, so a single "wrong password or
    # corrupt file" message avoids mislabelling genuine corruption as a bad
    # password. The malformed-envelope classes: json.JSONDecodeError and
    # binascii.Error are ValueError subclasses; KeyError covers a missing header
    # field; TypeError a value of the wrong shape. The scrypt bounds (incl. the
    # 128*n*r memory product) are enforced (ValueError) BEFORE Scrypt is ever
    # constructed, so a huge allocation never fires. MemoryError and
    # InternalError are defence in depth (a memory failure, or OpenSSL's own
    # N < 2**(16*r) check surfacing). RecursionError (a RuntimeError subclass,
    # NOT covered by the classes above) catches a deeply-nested-but-small
    # crafted JSON header that makes json.loads recurse past the limit. The
    # diagnostic goes to stderr, never stdout, since decrypted plaintext may be
    # piped to stdout.
    except (InvalidToken, InvalidSignature, ValueError, KeyError, TypeError,
            MemoryError, InternalError, RecursionError):

        print("Could not decrypt (wrong password or corrupt file).",
              file = sys.stderr)

        return None


def encrypt(path     : str,
            encoding : str                  = DEFAULT_ENCODING,
            password : str | bytes | None = None) -> bytes:

    '''

    Encrypts the contents of a file and returns the v2 envelope bytes: the
    magic prefix, a JSON header carrying the KDF parameters and per-file salt,
    a newline, and the Fernet token.

    The file must be an existing, singly-linked regular file: a symlink, a
    non-regular file, or a hard-linked inode is rejected with
    ``UnsupportedFileTypeError`` (see ``_open_and_read_regular``). The plaintext
    is read as raw bytes so binary files (and Windows executables) round-trip
    losslessly; only the password uses ``encoding``.

    The ``password`` may be passed as ``str`` or ``bytes`` (or omitted, to
    prompt): a ``str`` is encoded to bytes with ``encoding`` at this public API
    boundary, since scrypt operates on bytes.

    '''

    _, contents = _open_and_read_regular(path)

    return _encrypt_contents(contents, encoding, password)


def decrypt(path     : str,
            encoding : str                  = DEFAULT_ENCODING,
            password : str | bytes | None = None) -> bytes | None:

    '''

    Decrypts a pydlock file and returns its plaintext bytes, or ``None`` on a
    wrong password / corrupt file.

    The file must be an existing, singly-linked regular file (a symlink,
    non-regular file, or hard-linked inode is rejected with
    ``UnsupportedFileTypeError``). The ``password`` may be passed as ``str`` or
    ``bytes`` (or omitted, to prompt), covering both the v2 scrypt path and the
    v1 legacy path.

    '''

    _, data = _open_and_read_regular(path, _read_decrypt_input)

    return _decrypt_data(data, encoding, password)


def lock(path     : str,
         encoding : str                  = DEFAULT_ENCODING,
         password : str | bytes | None = None) -> None:

    '''

    Encrypts a file in place, replacing its contents with the v2 envelope.

    The file is opened, validated (regular, singly-linked, not a symlink), and
    read ONCE; its identity is snapshotted from that same descriptor and
    revalidated immediately before the atomic replace, so a concurrent edit or a
    path swap aborts the write rather than overwriting newer contents (see
    ``_open_and_read_regular`` / ``_verify_unchanged``).

    '''

    identity, contents = _open_and_read_regular(path)

    envelope = _encrypt_contents(contents, encoding, password)

    _atomic_write(path, envelope, identity)


def unlock(path     : str,
           encoding : str                  = DEFAULT_ENCODING,
           password : str | bytes | None = None) -> bool:

    '''

    Decrypts a file in place. Returns True if decryption was successful, and
    False otherwise.

    Like ``lock``, the file is validated and read once and its identity is
    revalidated immediately before the atomic replace, so a concurrent edit or a
    path swap aborts the write rather than overwriting newer contents.

    '''

    identity, data = _open_and_read_regular(path, _read_decrypt_input)

    contents = _decrypt_data(data, encoding, password)

    if contents is not None:

        _atomic_write(path, contents, identity)

        return True

    else:

        return False
