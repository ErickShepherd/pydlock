<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ErickShepherd/pydlock/main/brand/pydlock-lockup-dark.png">
    <img alt="pydlock" src="https://raw.githubusercontent.com/ErickShepherd/pydlock/main/brand/pydlock-lockup.png" width="460">
  </picture>
</p>

# pydlock

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21288807-blue)](https://doi.org/10.5281/zenodo.21288807)

## Description

**pydlock** is a dead-simple tool for password-encrypting and decrypting files.
Lock a file with one command, unlock it with another — that is the whole
product. It can be used from the command line or imported as a Python package.

As of **2.0** your password is protected with a salted, memory-hard **scrypt**
key derivation, files of *any* kind (including binaries and Windows executables)
round-trip losslessly, and writes are atomic — an interrupted lock or unlock
never leaves a truncated or half-written file (see
[Security boundaries](#security-boundaries) for the precise durability and
integrity guarantees).

## Problems this solves

Reach for pydlock if you are trying to:

- **Password-encrypt a file from the command line** — one command to lock, one
  to unlock, nothing else to configure.
- **Encrypt and decrypt a file in Python** with a two-function API
  (`pydlock.lock` / `pydlock.unlock`) instead of wiring up a crypto library
  yourself.
- **Protect a file with a strong password-derived key** without designing your
  own scheme — pydlock uses salted, memory-hard **scrypt** and authenticated
  **Fernet** (AES-128-CBC + HMAC-SHA256), and adds no custom cryptography.
- **Encrypt binaries safely** — files of any kind round-trip byte-for-byte, and
  writes are atomic (a fresh file is prepared and swapped into place, so an
  interrupted operation never truncates your data).

## Installation

**pydlock** is available on the Python Package Index (PyPI) at
<https://pypi.org/project/pydlock>. Install it with `pip`:

```console
pip install pydlock
```

## Quick start

Encrypt a file in place:

```console
pydlock lock secret.txt
```

Decrypt it again:

```console
pydlock unlock secret.txt
```

That is the entire everyday workflow. You are prompted for a password (twice when
locking); nothing else is required.

## Usage

### From the command line

The `pydlock` console command (installed with the package) and
`python -m pydlock` are equivalent:

```console
user@computer:~$ pydlock -h
usage: pydlock [-h] [--version] [--encoding ENCODING] {lock,unlock,encrypt,decrypt} file

positional arguments:
    {lock,unlock,encrypt,decrypt}
    file

options:
    -h, --help           show this help message and exit
    --version            show the version and exit
    --encoding ENCODING
```

Supported operations:

- `lock` — encrypt a file in place.
- `unlock` — decrypt a file in place.
- `encrypt` — alias for `lock`.
- `decrypt` — alias for `unlock`.

A short example:

```console
user@computer:~$ cat secret.txt
Shh! It's a secret!

user@computer:~$ pydlock lock secret.txt
Enter password:
Re-enter password:

user@computer:~$ pydlock unlock secret.txt
Enter password:

user@computer:~$ cat secret.txt
Shh! It's a secret!
```

An entered-but-wrong password fails cleanly — pydlock prints
`Could not decrypt (wrong password or corrupt file).` and leaves the encrypted
file untouched. Other expected problems (a missing file, a symlink or
hard-linked target, a permission error) print a one-line `pydlock: …` diagnostic
and exit non-zero, without a traceback.

### In other Python modules

```python
import pydlock

filename = "secret.txt"

with open(filename, "wb") as file:

    file.write(b"Shh! It's a secret!")

pydlock.lock(filename)      # prompts for a password, then encrypts in place
pydlock.unlock(filename)    # prompts for the password, then decrypts
```

## What's new in 2.0

Version 2.0 is a **breaking change to the on-disk format**. Files are now written
as a small self-identifying *envelope* — a `PYDLOCK` magic marker, a JSON header
carrying the key-derivation parameters and a per-file random salt, and then the
encrypted token — instead of a bare token.

Highlights:

- **Stronger password protection.** The key is derived with a salted,
  memory-hard **scrypt** KDF (see below), replacing the previous unsalted
  single-pass SHA-256 derivation.
- **Binary files are safe.** Files are read and written as raw bytes, so binary
  files and Windows executables round-trip losslessly. Earlier versions
  corrupted them; that bug is fixed.
- **Atomic writes.** Locking and unlocking write to a temporary file and
  atomically replace the original, so an interrupted operation can never leave a
  truncated or half-written file. On POSIX the file and its parent directory are
  fsynced so the replacement is also durable across a power loss; see
  [Security boundaries](#security-boundaries) for the per-platform guarantee.
- **`encrypt` / `decrypt` aliases** for `lock` / `unlock`.
- **`python` and `run` removed.** The old decrypt-and-execute subcommands were a
  security footgun (arbitrary code execution) and outside the scope of a
  file-encryption tool; they have been removed.

## Migrating from v1

**You do not need to do anything special.** Files locked with pydlock 1.x are
detected automatically and decrypted transparently:

```console
user@computer:~$ pydlock unlock old_v1_file.txt
Enter password:
```

Re-locking an unlocked file rewrites it in the new v2 format, so a file is
upgraded simply by unlocking and locking it again.

If you ever need the old behavior explicitly, the final 1.x release remains
installable as a documented fallback:

```console
pip install 'pydlock<2'
```

## How your password is protected

When you lock a file, pydlock generates a fresh 16-byte random salt and derives
the encryption key from your password with **scrypt** (parameters `n = 32768`,
`r = 8`, `p = 1`), a memory-hard function designed to make brute-force and
hardware-accelerated guessing expensive. The salt and parameters are stored in
the file's header so the key can be re-derived when you unlock it — a different
salt each time means locking the same file twice never produces the same
ciphertext.

The file itself is encrypted with
[Fernet](https://cryptography.io/en/latest/fernet/) (AES-128 in CBC mode with an
HMAC-SHA256 authentication tag) from the well-vetted `cryptography` library.
Because the token is authenticated, a wrong password, a corrupted token, or any
modification of the encrypted contents is detected and rejected — pydlock never
returns silently-wrong plaintext. pydlock adds no custom cryptography of its own.

Use a strong passphrase: scrypt makes guessing expensive, but it cannot add
entropy to a weak or empty one. pydlock refuses to encrypt with an empty
password.

## Security boundaries

pydlock is deliberately small. Knowing exactly what it does and does not
guarantee lets you use it safely.

- **What is authenticated.** The plaintext and the ciphertext are authenticated
  by Fernet's HMAC, and the v2 envelope is parsed strictly (exact framing,
  canonical base64, the promised salt length), so a wrong password or a modified
  token/header is rejected rather than returning wrong plaintext. This is *not* a
  byte-for-byte signature over an arbitrary presentation of the file: Fernet has
  no additional-authenticated-data channel, so pydlock authenticates the
  plaintext and ciphertext and validates the envelope grammar, rather than
  claiming every possible byte layout is signed.
- **Regular files only; no aliases.** `lock` and `unlock` operate only on an
  existing, singly-linked regular file. A **symlink**, a **hard-linked** file
  (`st_nlink != 1`), or a non-regular file (directory, device, FIFO) is
  **rejected** with a non-zero exit, because pydlock replaces a file by renaming
  a new inode over the path — which would encrypt one name while leaving the
  plaintext reachable through the other. Resolve the symlink yourself and pass the
  real target if that is what you meant.
- **Concurrent edits are not clobbered.** pydlock snapshots the file's identity
  when it reads it and revalidates immediately before replacing it. If the file
  changed on disk in between (a concurrent writer, or a path swap), the operation
  aborts without overwriting the newer contents. A small time window between the
  check and the replace is unavoidable; pydlock is not a substitute for a file
  lock in a heavily concurrent workflow.
- **Atomic everywhere; durable on POSIX.** The replace is atomic on every
  platform (no truncated/partial file). Full **power-loss durability**
  additionally requires fsyncing the parent directory, which pydlock does on
  POSIX; on Windows and on filesystems that do not support directory fsync, only
  atomic replacement is guaranteed, not durability across a sudden power loss.
- **Metadata Fernet exposes.** A Fernet token embeds the **creation timestamp in
  cleartext** (it is authenticated, not hidden), so an observer can read when a
  file was locked. The ciphertext length also reveals the approximate plaintext
  size. pydlock does not pad or hide either.
- **Whole-file, in-memory.** pydlock reads the entire file into memory and Fernet
  requires the whole message at once, so inputs must fit comfortably in RAM.
  Fernet is not intended for very large files; a streaming format is explicitly
  out of scope for pydlock.

## Copyright and License

Pydlock - A Python file encryption tool.

Copyright (c) 2020 of Erick Edward Shepherd, all rights reserved.

Released under the MIT License. See the `LICENSE` file for the full text. Built by
[Erick Shepherd](https://erickshepherd.com).
