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
