<p align="center">
  <img src="brand/pydlock-logo.png" alt="pydlock logo — a padlock formed by an ouroboros serpent" width="200">
</p>

# pydlock

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21288807-blue)](https://doi.org/10.5281/zenodo.21288807)

## Description

**pydlock** is a dead-simple tool for password-encrypting and decrypting files.
Lock a file with one command, unlock it with another — that is the whole
product. It can be used from the command line or imported as a Python package.

As of **2.0** your password is protected with a salted, memory-hard **scrypt**
key derivation, files of *any* kind (including binaries and Windows executables)
round-trip losslessly, and writes are crash-safe.

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
  writes are crash-safe (atomic replace).

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
usage: pydlock [-h] [--encoding ENCODING] {lock,unlock,encrypt,decrypt} file

positional arguments:
    {lock,unlock,encrypt,decrypt}
    file

options:
    -h, --help           show this help message and exit
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
file untouched.

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
- **Crash-safe writes.** Locking and unlocking write to a temporary file and
  atomically replace the original, so an interrupted operation can never leave a
  truncated or half-written file.
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
Because the token is authenticated, a wrong password or any tampering with the
file is detected and rejected — pydlock never returns silently-wrong plaintext.
pydlock adds no custom cryptography of its own.

## Copyright and License

Pydlock - A Python file encryption tool.

Copyright (c) 2020 of Erick Edward Shepherd, all rights reserved.

Released under the MIT License. See the `LICENSE` file for the full text. Built by
[Erick Shepherd](https://erickshepherd.com).
