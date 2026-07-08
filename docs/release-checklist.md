# Release checklist — pydlock v2.0.1

The **owner-gated tail** of the v2 effort. Everything in the implementation
plan (`IMPLEMENTATION_PLAN.md`, items 1–10) is done on the
`loop/v2-implementation` branch; the steps below are performed **by the owner,
outside the implementation loop**. The loop never merges, pushes, rewrites
history, changes repository visibility, tags, or publishes.

> **This document only *describes* the tail.** Nothing in it is executed by the
> automation. Each step is a manual, owner-authorized action.

---

## The critical invariant (read first)

Every commit in this repository — including the v2 commits made on
`loop/v2-implementation` — currently carries the owner's **private** email
(`erickeshepherd@gmail.com`) in its author/committer fields. **That address must
never appear in public history.** Therefore:

- The history rewrite (§3) must cover **all** history, including the merged v2
  commits — so the **merge happens *before* the rewrite**, and the rewrite +
  leak-guard confirmation happen **before** the repository is made public (§5).
- This is why the ordering below differs slightly from the one-line summary in
  the plan: the plan lists the tail's *components*; the safe *sequence* is
  merge → rewrite → confirm → force-push → public → tag → release → publish, so
  no private email is ever exposed.

Recommended order:

| # | Phase | Owner-gated? |
|---|-------|--------------|
| 0 | Pre-merge review + merge to `master` | no (normal workflow) |
| 1 | Local verification of merged `master` | no |
| 2 | Full backup mirror clone | yes |
| 3 | Rewrite author/committer email across all history | yes |
| 4 | Force-push rewritten history to the private remote | yes |
| 5 | Make the repository public | yes |
| 6 | Tag `v2.0.1` + GitHub Release | yes |
| 7 | Publish to PyPI (OIDC) | yes |

---

## 0. Pre-merge (normal branch workflow — not owner-gated)

- [ ] `loop/v2-implementation` passes an independent `pre-merge-review` (a fresh,
      read-only, highest-capability reviewer over the full diff vs `master`).
- [ ] Address any CHANGES-REQUESTED findings on the branch; re-review until
      SIGN-OFF.
- [ ] Merge to `master` with `git merge --no-ff loop/v2-implementation`.

## 1. Local verification (clean checkout of merged `master`)

- [ ] `pip install -e ".[test]"`
- [ ] `python -m pytest -q` — the offline suite is green (9 tests).
- [ ] `ruff check .` — clean.
- [ ] `python -m build` — sdist + wheel build.
- [ ] `twine check dist/*` — both distributions PASS.
- [ ] In a fresh venv, `pip install dist/pydlock-2.0.1-py3-none-any.whl`, then
      `python -c "import pydlock; assert pydlock.__version__ == '2.0.1'"` and a
      `pydlock lock` / `pydlock unlock` round-trip on a scratch file.
- [ ] Smoke-test the legacy path: `pydlock unlock` a copy of
      `tests/fixtures/v1_legacy.locked` with password `legacy-password`.

## 2. Back up before rewriting history (owner-gated)

- [ ] Make a full mirror backup so the rewrite is reversible:
      `git clone --mirror . ../pydlock-backup.git` (keep it until the release is
      confirmed good). History rewriting re-SHAs every commit and cannot be
      cleanly undone without this.

## 3. Rewrite author/committer email across all history (owner-gated)

Scrub the private email from **all** history, keeping the display name. Target:

```
erickeshepherd@gmail.com  ->  24425940+ErickShepherd@users.noreply.github.com
"Erick Shepherd" (display name)  ->  unchanged
```

- [ ] Set the repo-local identity so future commits use the public address:
      ```
      git config user.name  "Erick Shepherd"
      git config user.email "24425940+ErickShepherd@users.noreply.github.com"
      ```
- [ ] Rewrite history. Preferred (`git filter-repo`), via a mailmap file
      mapping the old address to the new:
      ```
      # mailmap:  Erick Shepherd <24425940+ErickShepherd@users.noreply.github.com> <erickeshepherd@gmail.com>
      git filter-repo --mailmap mailmap
      ```
      Or, without `filter-repo`, `git filter-branch --env-filter` rewriting
      `GIT_AUTHOR_EMAIL` / `GIT_COMMITTER_EMAIL` when they equal the old address.
- [ ] Confirm no private address remains anywhere in history:
      ```
      git log --all --format='%ae%n%ce' | sort -u   # expect only the noreply address
      ```
- [ ] Re-run the `leak-guard` skill over the rewritten repository to confirm no
      private email, key, or other secret remains in any commit.

## 4. Force-push the rewritten history to the private remote (owner-gated)

- [ ] `git push --force-with-lease origin master` (and any other kept refs).
- [ ] Note: every commit is re-SHA'd, so any existing clones must be re-cloned.
      Do this while the repository is **still private**.

## 5. Make the repository public (owner-gated)

- [ ] Only after §3 + §4 confirm the history is clean.
- [ ] GitHub → repo **Settings** → **Change visibility** → **Public**.
- [ ] Confirm the remote slug is `github.com/ErickShepherd/pydlock` (the
      `CITATION.cff` and `pyproject.toml` URLs assume it).

## 6. Tag the release + GitHub Release (owner-gated) — after merge + rewrite

- [ ] Confirm `pydlock/constants.py` `__version__ == "2.0.1"` and the
      `CHANGELOG.rst` `2.0.1` entry is accurate and dated.
- [ ] Annotated tag on the rewritten `master` HEAD:
      `git tag -a v2.0.1 -m "pydlock v2.0.1"`.
- [ ] `git push origin v2.0.1`.
- [ ] Verify GitHub Actions CI (`.github/workflows/ci.yml`) runs green on the
      pushed commit (ruff + pytest matrix 3.10–3.13 + build/twine).
- [ ] Create a GitHub Release from the `v2.0.1` tag, pasting the `CHANGELOG.rst`
      `2.0.1` section as the release notes.

## 7. Publish to PyPI (owner-gated, OIDC) — republish over the existing project

`pydlock` already exists on PyPI, so this republishes v2.0.1 over the existing
project as its owner. Publishing is automated via **PyPI Trusted Publishing
(OIDC)** — `.github/workflows/publish.yml` uploads with **no stored token**.

One-time setup (owner, web UI):

- [ ] **TestPyPI** (test.pypi.org) → Account → Publishing → add a *pending
      publisher*: project `pydlock`, owner `ErickShepherd`, repository
      `pydlock`, workflow `publish.yml`, environment `testpypi`.
- [ ] **PyPI** (pypi.org) → the project's *Publishing* settings → add the same
      trusted publisher, environment `pypi`.
- [ ] GitHub repo → **Settings → Environments** → create `testpypi` and `pypi`,
      each with yourself as a **required reviewer** (the approval gate).

Per release:

- [ ] Dry run: Actions → "Publish to PyPI" → Run workflow → target `testpypi`;
      approve the prompt; then
      `pip install -i https://test.pypi.org/simple/ pydlock` in a clean venv and
      smoke-test.
- [ ] Production: publishing the GitHub Release auto-runs the workflow to PyPI
      (or dispatch with target `pypi`); approve the `pypi` environment prompt.
- [ ] Verify `pip install pydlock` from PyPI resolves to `2.0.1` in a clean venv
      and `pydlock lock` / `unlock` work.

---

## Notes

- **Nothing above is done by the loop.** The implementation loop stops at
  "branch complete, committed, and surfaced". Merge, history rewrite, force-push,
  visibility change, tag, and publish are all human/owner decisions.
- **Secrets never enter the repo.** PyPI uploads use short-lived OIDC identities;
  no API token is stored in the repository or in GitHub secrets.
- **The rewrite is the point of no return.** Keep the §2 backup until
  `pip install pydlock` from PyPI is confirmed working.
