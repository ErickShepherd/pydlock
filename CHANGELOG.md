# Changelog

## 2020-04-12 - Version 1.0.0

- Initial build developed and released.

  - Created `pydlock.py`.

## 2020-04-13 - Version 1.1.0

- Added a "re-enter password" prompt when encrypting to avoid lock-out due to
  typos.

- Patched functions emptying files after invalid password entries.

## 2020-04-30 - Version 1.2.0

- Converted pydlock from a `pydlock.py` module to a `pydlock` package.

  - Created `setup.py`.

  - Renamed `pydlock.py` to `__init__.py`.

  - Created `__main__.py`.

  - Moved relevant `__main__` namespace code into the new `__main__.py` module.

- Single-sourced the `__author__` and `__version__` dunders.

- Changed the README file from Markdown to reStructuredText.

- Changed the package versioning system to include a build number for PyPI
  package management.

## 2026-07-08 - Version 2.0.1

First published release on PyPI. Version 2.0.0 was a pre-release validated only on
TestPyPI and was superseded by this release before publication; its modernization
notes are retained below for the full history.

- **Fixed: a `str` password via the public `password=` API raised `TypeError`.**
  A library caller doing `pydlock.lock(path, password="a string")` crashed inside
  scrypt (`Cannot convert str instance to a buffer`), because the key derivation
  requires bytes. Passwords are now accepted as `str` or `bytes` on
  `lock`/`unlock`/`encrypt`/`decrypt`; a `str` is encoded with the selected
  `encoding` at the public API boundary, covering both the v2 scrypt path and the
  v1 legacy path. The CLI (which already supplies bytes via `getpass`) is
  unaffected.

## 2026-07-08 - Version 2.0.2

Audit remediation release (whole-file `audit-repo` pass, 2026-07-08). No on-disk
format change; every fix is backward compatible.

- **Security: a malformed envelope always fails cleanly.** A crafted, deeply
  nested JSON header made `json.loads` recurse past the interpreter limit and
  raise an uncaught `RecursionError`, leaking a traceback on hostile input.
  `decrypt` now bounds the raw header length before parsing and catches
  `RecursionError` in the malformed-envelope handler, so such a file returns the
  clean `None` sentinel, fast, with no traceback. A valid-JSON but non-object
  header (e.g. a bare number or list) is likewise rejected as corrupt via an
  `isinstance` guard, closing an adjacent `AttributeError` on the same
  untrusted-input path.

- **CLI: a failed unlock now exits non-zero.** The CLI discarded the
  `lock`/`unlock` return value, so a failed `unlock` (wrong password) exited `0`
  and scripts could not detect the failure. It now exits `1` on failure.

- **File permissions are preserved across a round-trip.** The atomic write created
  its temp file `0600` and swapped it into place, silently tightening a `0644`
  file to owner-only on every lock/unlock. The original file's mode (and
  best-effort owner/group) is now copied onto the temp before the swap; a newly
  created file keeps the safe `0600` default.

- **Diagnostics go to stderr with one honest message.** Decrypt diagnostics
  printed to stdout (where decrypted plaintext may be piped) and
  `"Incorrect password."` mislabelled genuine corruption/tamper. Both failure
  paths now print a single
  `"Could not decrypt (wrong password or corrupt file)."` to stderr.

- **Tests and internals.** Added a CLI test module covering `__main__` (verb
  dispatch, the encrypt/decrypt aliases, abspath coercion, encoding forwarding,
  and the failure exit code) plus regression tests for each fix above, and
  extracted a shared `_normalise_password` helper. Refreshed stale header dates.

## 2026-07-09 - Version 2.0.3

Docs/packaging only — no code changes.

- **README discoverability.** Added a "Problems this solves" section mapping
  common natural-language queries (password-encrypting a file from the CLI or
  Python, scrypt + Fernet file encryption) to the tool, and corrected the quoted
  wrong-password message to match the actual output
  (`Could not decrypt (wrong password or corrupt file).`).

- **Packaging metadata.** Added the previously-missing PyPI trove classifiers
  (`Topic :: Security :: Cryptography`, `Topic :: Utilities`, and the supported
  Python versions) and expanded keywords.

- **Removed a stale docstring note** that claimed locking Windows executables
  corrupts them; the v2 raw-bytes path round-trips them losslessly.

## 2026-07-10 - Version 2.0.4

Citation metadata only — no code changes.

- **Zenodo/citation metadata.** Added a `.zenodo.json` and an author ORCID in
  `CITATION.cff`, so a Zenodo release archive registers a citable DOI with correct
  software metadata.

## 2026-07-10 - Version 2.0.5

Documentation site + metadata polish — no code changes. An independent
review of the source and metadata this cycle returned "no change
warranted".

- **Read the Docs site.** Added a Sphinx documentation site
  (<https://pydlock.readthedocs.io/>) with the API reference generated from
  the docstrings (`lock`/`unlock`, `encrypt`/`decrypt`, and the prompt
  helpers), and a `Documentation` URL in the PyPI project links. Shipping
  the docs configuration in a tag also fixes RTD's tag-based "stable"
  build.

- **Docs/metadata polish.** Markdown README and prose docs (render on PyPI
  as `text/markdown`), shields.io DOI badge, `erickshepherd.com` backlink,
  and `main` as the default branch.

## 2026-07-13 - Version 2.0.6

Branding and packaging-metadata polish — no code changes.

- **Project logo.** Added a brand mark — a padlock formed by an ouroboros
  serpent (Python + padlock + a sealed loop) — under `brand/`: a light/dark
  README lockup (`<picture>` theme-swap), the mark tile, and black/white
  transparent mono variants. The wordmark uses Sora (SIL OFL 1.1), vendored
  with its full license.

- **Docs logo.** The Read the Docs sidebar now shows the mark (furo
  light/dark logo).

- **Project URLs.** Standardized the PyPI project links: `Documentation`
  now points at the released docs (`/en/stable/` rather than `/en/latest/`),
  added a `Changelog` link to the GitHub releases, and renamed `Bug Tracker`
  to `Issues`.

## 2026-07-21 - Version 2.0.7

Security and release-compliance patch. **No on-disk format change** — files
locked by pydlock 2.0.x and the legacy v1 format still decrypt byte-for-byte.

- **Security: reject symlinks, hard links, and non-regular files.** `lock` and
  `unlock` now operate only on an existing, singly-linked regular file. A symlink
  or hard-linked target used to be replaced by renaming a fresh inode over the
  path, leaving the plaintext reachable through the other name and reporting
  success; these are now rejected with a clear, non-zero error.

- **Security: never overwrite a concurrent edit.** The file's identity is
  snapshotted when it is read and revalidated immediately before the atomic
  replace, so a concurrent write or a path swap aborts the operation instead of
  clobbering newer contents.

- **Security: strict v2 envelope parsing.** Exact magic-line framing, exactly one
  header/token separator, canonical base64 for the salt and token, the promised
  salt length, and a non-empty token are now required. Two modified-envelope
  inputs that previously decrypted — bytes inserted on the magic line, and
  trailing garbage after the token — are now rejected. Fernet still authenticates
  the plaintext/ciphertext; full byte-authentication of an arbitrary envelope
  layout is a possible format-v3 question, not part of this patch.

- **Security: reject empty passwords on encryption.** `lock`/`encrypt` refuse an
  empty password (which adds no protection); decryption still accepts an empty
  password so a pre-existing empty-password file can be recovered.

- **Durability: complete the write sequence.** Metadata is applied before the
  final file fsync, the replace happens only after the prepared file is durable,
  and the parent directory is fsynced after the replace on POSIX. On platforms
  without directory fsync (e.g. Windows) only atomic replacement is guaranteed;
  the docs now state atomicity vs power-loss durability precisely instead of a
  blanket "crash-safe".

- **Docs: honest security boundary.** A new "Security boundaries" section in the
  README corrects the tamper-detection, link/concurrency, durability, Fernet
  creation-timestamp / ciphertext-size metadata, and whole-file-in-memory claims.

- **CLI: friendly errors and `--version`.** Expected failures (missing file, a
  symlink/hard-linked/non-regular target, a permission error, an unknown
  encoding, an empty password) now print a one-line `pydlock: …` diagnostic and
  exit non-zero without a traceback. Added `--version`.

- **Release/privacy hardening.** Redacted a private address from tracked internal
  prose (published history intentionally not rewritten); restricted the source
  distribution to the intentional source-release set; added a privacy guard,
  SHA-pinned the publish workflow's GitHub Actions, added Dependabot, clean-install
  smoke tests for the wheel and sdist, a release tag/version/citation/artifact
  agreement check, Windows + macOS CI coverage, and a `SECURITY.md`.

## 2026-07-08 - Version 2.0.0

*Pre-release, TestPyPI only — never published to production PyPI; superseded by
2.0.1.*

Major release with a **breaking change to the on-disk file format**. Files locked
by pydlock 1.x still decrypt transparently (see "Migrating from v1" in the
README); re-locking upgrades a file to the new format. The final 1.x release
remains installable as `pip install 'pydlock<2'`.

- **Security: salted, memory-hard scrypt key derivation.** The encryption key is
  now derived from the password with scrypt (`n=32768, r=8, p=1`) and a fresh
  per-file random salt, replacing the unsalted single-pass SHA-256 derivation. The
  file cipher remains Fernet (AES-128-CBC + HMAC-SHA256); no custom cryptography
  is introduced.

- **New self-identifying on-disk envelope.** Encrypted files begin with a
  `PYDLOCK` magic marker and a JSON header carrying the KDF parameters and salt,
  followed by the Fernet token. The format is versioned and leaves room for a
  documented `pbkdf2` fallback identifier.

- **Transparent v1 legacy decryption.** Non-magic (v1) files are detected and
  decrypted with the old scheme, so no existing files are stranded.

- **Binary files are no longer corrupted.** Files are read and written as raw
  bytes, so binary files and Windows executables round-trip losslessly — this
  fixes the corruption previously documented as "unfixable".

- **Crash-safe atomic writes.** `lock`/`unlock` write to a temporary file and
  atomically replace the original.

- **Removed the `python` and `run` subcommands.** Decrypt-and-execute (`exec` /
  `subprocess` with `shell=True`) was a security footgun and has been removed.

- **Added `encrypt` / `decrypt` CLI aliases** for `lock`/`unlock`, plus a
  `pydlock` console entry point.

- **Packaging and tooling.** Migrated to `pyproject.toml` (hatchling), declared
  the previously-missing `cryptography` runtime dependency, single-sourced the
  version as `2.0.0`, and added an offline pytest suite, ruff linting, a CI matrix
  (Python 3.10-3.13), and OIDC Trusted Publishing.
