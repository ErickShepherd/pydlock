*********
Changelog
*********

==========================
2020-04-12 - Version 1.0.0
==========================

* Initial build developed and released.

  - Created :code:`pydlock.py`.


==========================
2020-04-13 - Version 1.1.0
==========================

* Added a "re-enter password" prompt when encrypting to avoid lock-out due to
  typos.

* Patched functions emptying files after invalid password entries.


==========================
2020-04-30 - Version 1.2.0
==========================

* Converted pydlock from a :code:`pydlock.py` module to a :code:`pydlock`
  package.

  - Created :code:`setup.py`.

  - Renamed :code:`pydlock.py` to :code:`__init__.py`.

  - Created :code:`__main__.py`.

  - Moved relevant :code:`__main__` namespace code into the new
    :code:`__main__.py` module.

* Single-sourced the :code:`__author__` and :code:`__version__` dunders.

* Changed the README file from Markdown to reStructuredText.

* Changed the package versioning system to include a build number for PyPI
  package management.


==========================
2026-07-08 - Version 2.0.1
==========================

First published release on PyPI. Version 2.0.0 was a pre-release validated
only on TestPyPI and was superseded by this release before publication; its
modernization notes are retained below for the full history.

* **Fixed: a** :code:`str` **password via the public** :code:`password=` **API
  raised** :code:`TypeError`. A library caller doing
  :code:`pydlock.lock(path, password="a string")` crashed inside scrypt
  (:code:`Cannot convert str instance to a buffer`), because the key
  derivation requires bytes. Passwords are now accepted as :code:`str` or
  :code:`bytes` on :code:`lock`/:code:`unlock`/:code:`encrypt`/:code:`decrypt`;
  a :code:`str` is encoded with the selected :code:`encoding` at the public API
  boundary, covering both the v2 scrypt path and the v1 legacy path. The CLI
  (which already supplies bytes via :code:`getpass`) is unaffected.


==========================
2026-07-08 - Version 2.0.0
==========================

*Pre-release, TestPyPI only — never published to production PyPI; superseded by
2.0.1.*

Major release with a **breaking change to the on-disk file format**. Files
locked by pydlock 1.x still decrypt transparently (see "Migrating from v1" in
the README); re-locking upgrades a file to the new format. The final 1.x
release remains installable as :code:`pip install 'pydlock<2'`.

* **Security: salted, memory-hard scrypt key derivation.** The encryption key
  is now derived from the password with scrypt (:code:`n=32768, r=8, p=1`) and
  a fresh per-file random salt, replacing the unsalted single-pass SHA-256
  derivation. The file cipher remains Fernet (AES-128-CBC + HMAC-SHA256); no
  custom cryptography is introduced.

* **New self-identifying on-disk envelope.** Encrypted files begin with a
  :code:`PYDLOCK` magic marker and a JSON header carrying the KDF parameters
  and salt, followed by the Fernet token. The format is versioned and leaves
  room for a documented :code:`pbkdf2` fallback identifier.

* **Transparent v1 legacy decryption.** Non-magic (v1) files are detected and
  decrypted with the old scheme, so no existing files are stranded.

* **Binary files are no longer corrupted.** Files are read and written as raw
  bytes, so binary files and Windows executables round-trip losslessly — this
  fixes the corruption previously documented as "unfixable".

* **Crash-safe atomic writes.** :code:`lock`/:code:`unlock` write to a
  temporary file and atomically replace the original.

* **Removed the** :code:`python` **and** :code:`run` **subcommands.**
  Decrypt-and-execute (:code:`exec` / :code:`subprocess` with
  :code:`shell=True`) was a security footgun and has been removed.

* **Added** :code:`encrypt` **/** :code:`decrypt` **CLI aliases** for
  :code:`lock`/:code:`unlock`, plus a :code:`pydlock` console entry point.

* **Packaging and tooling.** Migrated to :code:`pyproject.toml` (hatchling),
  declared the previously-missing :code:`cryptography` runtime dependency,
  single-sourced the version as :code:`2.0.0`, and added an offline pytest
  suite, ruff linting, a CI matrix (Python 3.10-3.13), and OIDC Trusted
  Publishing.
