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
