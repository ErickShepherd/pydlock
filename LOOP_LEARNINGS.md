# Loop learnings — pydlock v2 (ralph-loop, checklist anchor)

Append-only. Advisory memory for a fresh context each iteration: dead ends, gotchas,
decisions-and-why. **Not** a status mirror (the `IMPLEMENTATION_PLAN.md` checkbox count is the
progress signal) and **never** a done-signal.

---

<!-- Append a dated `## 2026-… — item N (short title)` block after each pass. -->

## 2026-07-08 — item 1 (packaging: pyproject.toml)

- **Version single-sourcing (reversible/internal fork, resolved autonomously):** followed the
  owner's `../cosmic_crunch` pattern — `dynamic = ["version"]` + `[tool.hatch.version]`. Unlike
  cosmic (which points hatchling at `__init__.py`), pydlock's version has always lived in
  `constants.py` and item 1 explicitly says to fix it there, so `path = "pydlock/constants.py"`
  with a literal `__version__ = "2.0.0"`. `pydlock/__init__.py` already re-exports it via
  `__version__ = constants.__version__`, so no change needed there.
- **cryptography floor (reversible/internal fork, resolved autonomously):** `>=43.0` — a
  sensible baseline that supports the full 3.10–3.13 CI matrix (item 8) and has the `hazmat`
  `Scrypt` primitive item 3 needs. Followed cosmic's convention of a comment noting the floor
  tracks the CI matrix and loosening is an out-of-loop decision. Neither fork needed a `DECIDE:`
  item (both reversible + internal blast radius per the reversibility rubric).
- **No-behavior-change kept:** `main()` extracted in `__main__.py` for the console entry point,
  but the CLI still exposes `{lock,unlock,python,run}` and still writes v1 format — removing
  `python`/`run` and adding `encrypt`/`decrypt` is item 6, not here. Both `pydlock` (entry point)
  and `python -m pydlock` verified working.
- **`build.py` was a no-op stub** (empty `github()`/`pypi()`); deleted with `setup.py` +
  `version.json` as the plan directs.
- **Gotcha for later items:** left `license`/`license-files` OUT of `pyproject.toml` — that plus
  the per-file SPDX headers is item 2, kept separate to keep commits focused. `[tool.ruff]` and
  `[tool.pytest.ini_options]` likewise deferred to items 8 and 7.
- Verify (`pip install -e .` + version assert) passed in a clean venv; build deps resolved
  offline (hatchling + cryptography already cached in this env).

## 2026-07-08 — item 2 (metadata hygiene: SPDX license)

- **PEP 639 license fields** (`license = "MIT"` + `license-files = ["LICENSE"]`) matching
  `../cosmic_crunch`. Verified the built dist emits `License-Expression: MIT`. No relicense
  (design D2 — LICENSE was already MIT).
- **MANIFEST.in deleted, not "refreshed".** It is a setuptools-only artifact and is **inert
  under hatchling** (its only consumer, `setup.py`, was removed in item 1); the reference
  hatchling repo `../cosmic_crunch` has none. So the correct hygiene was to delete the (empty)
  file, not update it. Reversible/internal fork, resolved autonomously — build-artifact
  ignoring lives in `.gitignore`, which is where the plan's `dist/`, `*.egg-info/`,
  `.pytest_cache/` list actually belongs.
- **Per-file MIT block removal done with a deterministic Python regex transform** (in
  scratchpad `spdx.py`), not fragile Edit string-matching — the docstrings had trailing
  whitespace on "blank" lines. Pattern removed `Copyright:`→`...DEALINGS IN THE SOFTWARE.` and
  inserted `# SPDX-License-Identifier: MIT` after the coding line. Kept each file's short
  authorship/contact docstring (incl. the intended public `Contact@ErickShepherd.com`).
- **In scope only:** left `__main__.py`'s stale "Notes: Windows executables corrupt" docstring
  and the `python`/`run` usage text untouched — the corruption fix is item 4, the CLI reduction
  + docstring-typo fix is item 6. Did not touch them here.
- **`.gitignore` now exists** (mirrors cosmic's: `__pycache__/`, `*.py[cod]`, `.pytest_cache/`,
  `build/`, `dist/`, `*.egg-info/`, venvs). This fixes the item-1 gotcha where `git add -A`
  swept in `__pycache__/*.pyc` (had to amend); `git add -A` is now safe.

## 2026-07-08 — item 3 (scrypt KDF + versioned envelope)

- **Derivation model change is the crux:** `password_prompt`/`double_password_prompt` now
  return the *password as bytes* (not a pre-derived Fernet key). The key is derived inside
  `encrypt`/`decrypt` where the per-file salt exists. The `key=` parameter on
  encrypt/decrypt/lock/unlock/python/run was renamed `password=` to match (CLI in `__main__.py`
  passes only 3 positional args, so no `__main__` change was needed).
- **Envelope layout implemented exactly per design:** `b"PYDLOCK\x02\n"` + compact UTF-8 JSON
  header `{"kdf":"scrypt","n":32768,"r":8,"p":1,"salt":"<std-b64>"}` + `b"\n"` + Fernet token.
  Detection on the 8-byte prefix `b"PYDLOCK\x02"`; parse via two `partition(b"\n")` splits.
- **Scope kept tight (do NOT redo in later items):**
  - *Ciphertext* I/O is bytes-mode here (the magic byte forces it) — `lock` writes `wb`,
    `decrypt` reads `rb`. But *plaintext* I/O is still text-mode/encoding-coupled
    (`encrypt` reads `"r"`, `unlock` writes `"w+"`) — the binary-file corruption bug is
    **still present** and is **item 4** (bytes-mode plaintext + atomic writes).
  - Non-v2 (no-magic) file → explicit `ValueError` for now; the **v1 legacy-decrypt path is
    item 5**, which will replace that error branch (and re-add the `sha256` import I removed
    here as now-unused).
  - `python`/`run` kept (rewritten only for the `password` rename); their **removal +
    `encrypt`/`decrypt` aliases + full type-hint pass + docstring-typo fix is item 6**.
- **kdf dispatch left open, pbkdf2 NOT implemented** (reversible/internal call): `_derive_key`
  handles `"scrypt"`; any other id (incl. a future `"pbkdf2"`) raises `ValueError` — no
  speculative untested crypto. The design documents pbkdf2 as a *carried* fallback id, not a
  required writer path, so "leave the dispatch open + clear error on unknown" satisfies item 3.
- **Salt stored as standard base64** in the header (`b64encode`); the derived *key* uses
  `urlsafe_b64encode` (Fernet's required key format). Both JSON-safe; not a fork worth an item.
- Verified in a venv: round-trip (text), envelope format + param read-back, per-file salt
  uniqueness, wrong-password → clean `False` with file untouched, tampered token → clean
  `False` (Fernet HMAC), unknown-kdf → `ValueError`. The committed pytest suite is **item 7**
  (this functional check was throwaway, not committed).

## 2026-07-08 — item 4 (bytes-mode I/O + atomic writes)

- **Completes item 3's deferred plaintext I/O.** `encrypt` now reads the plaintext as `"rb"`
  (raw bytes, no `.encode(encoding)`), `decrypt` returns `bytes` (dropped `.decode(encoding)`;
  annotation `-> str` → `-> bytes`). This is the actual fix for the README's "unfixable"
  binary/Windows-exe corruption — verified lossless round-trip over all 256 byte values incl.
  NULs, and CRLF/NUL preserved (bytes-mode = no newline translation).
- **`encoding` is now password-only** (design D6 "password encoding stays"): still passed to
  `password_prompt`/`double_password_prompt`, no longer touches file contents. Left the param in
  place on all functions — signature/type-hint cleanup is item 6.
- **Atomic writes via a shared `_atomic_write(path, data: bytes)` helper**: `tempfile.mkstemp`
  in the *same directory* (required for `os.replace` to be atomic — cross-fs replace fails),
  write + `flush` + `os.fsync`, then `os.replace`; `except BaseException` best-effort removes
  the temp file and re-raises. Both `lock` and `unlock` use it (no more in-place `"w+"`
  truncate). Verified: a simulated interruption (patched `os.replace` to raise) leaves the
  ORIGINAL file intact and leaks no `.pydlock-*.tmp`.
- **No fork.** rb/wb and temp+os.replace are spec-pinned; same-dir temp + fsync are the
  standard robust implementation, not a choice worth a DECIDE item.
- Item 3's throwaway checks still pass (round-trip, salt uniqueness, wrong-pw/tamper clean-fail).
  Committed pytest suite covering binary round-trip + interrupted-write is still **item 7**.

## 2026-07-08 — item 5 (in-tool v1 legacy-decrypt)

- **Replaced item 3's non-magic `ValueError` branch** with a transparent v1 read; re-added the
  `sha256` import item 3 had removed as unused.
- **Legacy key derivation byte-for-byte** (`_derive_legacy_key`):
  `urlsafe_b64encode(sha256(password).hexdigest()[:32].encode())`. Since `password` is already
  bytes (encoded in `password_prompt`), `sha256(password)` matches the original v1
  `sha256(pw_str.encode(encoding))`; the hex digest is ASCII so `[:32].encode()` (design form)
  equals v1's `.encode(encoding)[:32]` (encode-then-truncate) exactly. Confirmed by generating a
  v1 fixture with an *independent* reimplementation of the old scheme and decrypting it.
- **Detection is unambiguous:** v1 tokens are Fernet base64 starting `gAAAAA…`, never
  `PYDLOCK\x02`. Non-magic file → whole file is the raw token, key from `_derive_legacy_key`;
  same try/except so a wrong password / garbage file fails cleanly (`None`), never silent wrong
  plaintext.
- **No special "upgrade" code needed:** `lock` always writes v2, so the documented "re-lock
  upgrades a v1 file" is just unlock(v1)→plaintext then lock→v2. Verified end-to-end.
- **For item 7:** the committed v1 fixture (file + known password + provenance note) must be
  produced with this exact old scheme — the independent generator in scratchpad `t5.py`
  (`v1_key`) is the reference. `_derive_legacy_key` is the in-tool counterpart.
- No fork — derivation + detection are spec-pinned verbatim.

## 2026-07-08 — item 6 (remove python/run; encrypt/decrypt aliases; type hints)

- **Two sub-tasks were already done in item 3's rewrite:** the `encrypt` docstring typo (it no
  longer says "Decrypts") and the `double_password_prompt` `key1/key2` → `password1/password2`
  naming. Verified by grep before starting; nothing to redo.
- **Deleted `python()` (`exec`) and `run()` (`subprocess … shell=True`)** — the security
  footguns — by truncating `__init__.py` at `def python(`. Removed the now-unused
  `import subprocess`. The item's `verify:` oracle
  (`grep -rn "exec(\|shell=True" pydlock/ ; test $? -eq 1`) passes (exit 1, none found).
- **Dropped the dead `arguments` parameter** from `lock`/`unlock` (only python/run used it).
  Signatures are now `(path, encoding, password)`; verified via `inspect.signature`.
- **CLI reduced to `{lock, unlock, encrypt, decrypt}`** in `__main__.py`, with `encrypt`→`lock`
  and `decrypt`→`unlock` aliases in `function_map` (the CLI verbs map to the *file-writing*
  `lock`/`unlock`, NOT the module-level `encrypt`/`decrypt` which return bytes). Dropped the
  now-dead `--arguments` flag; dispatch is `task(path, encoding)`. CLI round-trip verified end
  to end (encrypt then decrypt alias recovers the plaintext).
- **First full type-hint pass:** `password : bytes | None = None` everywhere (py>=3.10 union
  syntax, no `typing` import); `decrypt -> bytes | None` (returns None on bad password).
- **Also refreshed `__main__.py`'s module docstring** to match the reduced CLI and removed the
  now-false "Windows executables corrupt / unfixable" Notes block (item 4 fixed that). This is
  in-scope for "reduce the CLI"; user-facing README is item 9.
- Phase B (items 3-6, the v2 behavior) is now complete. No fork.

## 2026-07-08 — item 7 (offline pytest suite + v1 fixture)

- **`tests/test_pydlock.py`** — 9 tests, all offline, driven with explicit `password=` bytes so
  nothing prompts via getpass: text round-trip, binary round-trip (all 256 byte values + NULs —
  pins the bytes-mode fix), wrong-password → clean `False` + file untouched, per-file salt
  uniqueness, KDF params read-back + used, tampered-token → `None`, tampered-header (corrupt
  salt) → `None` (never wrong plaintext), atomic-write interrupt leaves original intact (patch
  `os.replace` to raise; assert no `.pydlock-*` temp leak), and v1 legacy decrypt + upgrade.
- **Committed v1 fixture `tests/fixtures/v1_legacy.locked`** (+ `PROVENANCE.md`): built with the
  exact pre-2.0 scheme (`urlsafe_b64encode(sha256(pw).hexdigest()[:32].encode())` → raw Fernet
  token, password `legacy-password`). The test copies it into `tmp_path` before mutating —
  **never** mutate the committed fixture.
- **pyproject:** added `[project.optional-dependencies] test = ["pytest"]` and
  `[tool.pytest.ini_options] testpaths = ["tests"]` (matches cosmic). Ruff config is **item 8**.
- **Gotcha:** the atomic-write test patches `os.replace` (the module-global that
  `_atomic_write` calls), and asserts a `RuntimeError` propagates — confirms the helper doesn't
  swallow write failures and cleans up its temp file.
- `python -m pytest -q` (the item's verify oracle) → **9 passed**. No fork.

## 2026-07-08 — item 8 (CI workflow + ruff config)

- **`.github/workflows/ci.yml`** adapted from `../cosmic_crunch` (three jobs): `lint` (ruff on
  3.12), `test` (pytest matrix 3.10-3.13, installs `.[test]`, offline), `build` (`python -m
  build` + `twine check dist/*` to prove publish-readiness). Triggers on push to main/master,
  PR, and workflow_dispatch. **Dormant until pushed** — the loop commits it but never pushes
  (local-only rule / stop-and-surface).
- **Permissive ruff config** copied from cosmic: `target-version = "py310"`, `line-length = 100`,
  and ruff's *default* lint set only (pyflakes `F` + pycodestyle `E4/E7/E9`) — deliberately
  does not enforce E1/E2 spacing or E501, so pydlock's aligned-assignment / blank-line-after-def
  style is left alone.
- **`ruff check .` → All checks passed** (0 findings) — the code was already clean under the
  permissive set (no unused imports etc.). The item's verify oracle passes.
- **Verified the build job locally too** (not just ruff): `python -m build` produced
  `pydlock-2.0.0` sdist + wheel and `twine check` PASSED both — confirms the hatchling packaging
  from items 1-2 is actually publish-ready. Build artifacts are gitignored (item 2).
- No fork. Phase D done.

## 2026-07-08 — item 9 (README v2 refresh)

- Rewrote `README.rst` (kept RST — item 10 decides Markdown vs RST for the *changelog* only,
  README stays .rst). Leads with the `pydlock lock file` / `pydlock unlock file` one-liner
  (the console entry point from item 1) as the selling point. Covers all required v2 topics:
  breaking on-disk envelope, transparent v1 migration + `pip install 'pydlock<2'` fallback,
  "how your password is protected" (salted scrypt n=32768/r=8/p=1 + Fernet unchanged),
  binary-file fix, `python`/`run` removal (security), and `encrypt`/`decrypt` aliases.
- **Prose item, no `verify:` oracle** → out-of-loop review discharges it. But since
  `pyproject` sets `readme = "README.rst"`, `twine check` validates the RST renders: ran
  `python -m build` + `twine check` → both dists PASSED, so the long-description won't break on
  PyPI. Also grep-confirmed no stray `python -m pydlock python` / `--arguments` / old CLI refs.
- Removed the old README's stale bits: `{lock,unlock,python,run}` help block, the
  `python -m pydlock python` example, and the full inline MIT text (now points at the LICENSE
  file). No fork.
