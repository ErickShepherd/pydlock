# pydlock release runbook (version-neutral)

> **Internal** operational runbook. It is excluded from the source distribution
> (see the sdist allowlist in `pyproject.toml`) and is **not** a user document.
> It replaces the earlier v2.0.1-specific checklist, which referred to `master`,
> an obsolete tag/version, and a `git push --force` step that current fleet
> policy forbids for a released package.

## Purpose

Cut a new pydlock release (PyPI + GitHub Release + Zenodo DOI) reproducibly, with
every quality/privacy/consistency gate green **before** anything leaves the
machine. Replace `X.Y.Z` with the target version throughout.

## Policy guardrails (read first)

- **Never rewrite published history.** pydlock is public and released; a history
  rewrite orphans release tags, invalidates hashes, and breaks clones and cannot
  retract already-downloaded artifacts. History rewrites are an explicit,
  owner-gated exception only.
- **SemVer + an annotated `vX.Y.Z` tag + a GitHub Release** per release
  (repo-best-practices §4). `/en/stable/` docs and the `Changelog → /releases`
  link depend on the tag and Release existing.
- **Trusted Publishing (OIDC)** only — no API tokens. The publish workflow's
  Actions are **SHA-pinned**; keep them so (Dependabot advances the SHAs).
- Push, tag, GitHub Release, PyPI upload, repository-settings, and PVR changes
  are **owner-gated** and happen only at the end.

## Prerequisites

- A clean working tree on the default branch (`git status --short` empty).
- An isolated environment with `pytest`, `ruff`, `bandit`, `build`, `twine`,
  `sphinx` (+ the docs requirements), and `cryptography>=43`.
- Local Python interpreters for as many supported versions as available (the
  full matrix is covered by CI).

## Steps

1. **Land all behavioral/doc changes** on their own reviewed branches and merge
   them. Do **not** combine them with the version bump.
2. **Bump the version mechanically**, in its own commit, once every gate below is
   green:
   - `pydlock/constants.py` → `__version__ = "X.Y.Z"`;
   - `CITATION.cff` → `version:` and `date-released:`;
   - `.zenodo.json` if release metadata changed;
   - add a `CHANGELOG.md` entry describing behavior changes and valid-file
     compatibility.
3. **Run the full verification gate** from a clean checkout (see below). All must
   pass.
4. **Inspect both archive file lists** (`tar -tzf dist/*.tar.gz`,
   `python -m zipfile -l dist/*.whl`): only the intentional source-release set,
   no internal plans/audits/loop-records/brand sources.
5. **Confirm** `git status --short` is empty and the version is consistent
   (`python tools/check_release_consistency.py --tag vX.Y.Z`).
6. **Owner-gated publish** (only after CI is green on the merge):
   - push the default branch;
   - create the annotated tag: `git tag -a vX.Y.Z -m "pydlock X.Y.Z"` and push it;
   - create the GitHub Release (generated notes + a curated summary); this
     triggers the OIDC publish workflow to PyPI;
   - confirm the Zenodo archive registers the DOI;
   - verify `pip install pydlock==X.Y.Z` in a clean environment.

## Verification gate (run from a clean checkout)

```console
python -m pytest -q
ruff check .
bandit -q -r pydlock
python -m build
twine check dist/*
sphinx-build -W -b html docs docs/_build/html
python tools/privacy_scan.py                       # tracked tree
python tools/privacy_scan.py --paths <extracted-sdist-and-wheel>
python tools/install_smoke.py --artifact wheel
python tools/install_smoke.py --artifact sdist
python tools/check_release_consistency.py --tag vX.Y.Z
```

Then additionally run the targeted symlink, hard-link, concurrent-edit,
malformed-envelope, empty-password, binary, permission, atomic-interruption, and
v1-migration tests (they are part of the suite above; run them explicitly when
spot-checking a specific fix).

## Rollback

- **Before push/tag/Release/upload:** discard the version-bump commit
  (`git reset --hard HEAD~1` on the release branch) — nothing external changed.
- **After a bad PyPI upload:** you cannot delete-and-reuse a version on PyPI.
  Yank the bad release on PyPI and publish a new patch version with the fix; do
  **not** rewrite history or re-tag.
- **After a bad GitHub Release/tag:** delete the Release and, if the tag was
  never referenced by an external clone/DOI, delete and recreate the tag;
  otherwise cut a new patch version.
