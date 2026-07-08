# pydlock v2.0.0 — implementation checklist (ralph-loop anchor)

**Spec:** `docs/plans/2026-07-08-repo-improvement-plan.md` (phases, DoD) +
`docs/design/2026-07-08-pydlock-v2.md` (decisions, rationale, envelope layout — the Open
questions are resolved in "Key decisions (Stage-0, owner-confirmed)"; do **not** re-open
them). Re-read both every iteration before picking an item.

**Loop discipline (binding):** one item per iteration, top-most unchecked first. Work on
THIS branch (`loop/v2-implementation`) only — the plan's phase-per-branch →
pre-merge-review → merge cadence is replaced, for this unattended run, by focused commits on
this single branch; **the whole branch gets exactly ONE out-of-loop `pre-merge-review` after
the loop stops** (not per phase, not per item). Never merge, never push, never make the repo
public, never force-push, never touch `master`. This loop runs under `CLAUDE_LOOP_GUARD=1`
(conservative stop-and-surface): it builds CODE only, commits on this branch, and when it can
advance no further it **stops and surfaces** the branch for the owner / out-of-loop reviewer —
it never performs the irreversible tail. If an item is blocked, or a fork appears that the
spec + design don't already pin, add a `- [ ] DECIDE:` item and move on; if nothing can
advance, stop-and-surface. **Search before writing:** `pydlock/__init__.py`,
`pydlock/__main__.py`, and `pydlock/constants.py` contain the v1 logic being hardened —
**port and fix, don't reinvent**; keep Fernet (the cipher is sound, the KDF is the defect).
Append learnings to `LOOP_LEARNINGS.md` each pass (append-only advisory memory — not a
status mirror, never a done-signal).

**Owner-gated tail is OUT of this checklist.** The git-history author/committer email rewrite
(`filter-branch`/`filter-repo`), the force-push, making the repo public, tagging, and the
actual PyPI publish are **not loop-buildable** and appear nowhere below. They are captured in
`docs/release-checklist.md` (written as the final item) for the owner to run after merge.

**Network policy:** pydlock is **pure local crypto — there is no network anywhere**. Every
item runs fully offline; the test suite never touches the network.

**Conventional commits:** each commit ends with
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`; message subject cites the item,
e.g. `feat: scrypt KDF + versioned envelope (item 3)`.

## Phase A — packaging + metadata (mechanical; port, no behavior change yet)

- [x] 1. Add `pyproject.toml` (hatchling; `requires-python = ">=3.10"`; **declare the missing
  `cryptography` runtime dependency** with a sensible floor — the real bug: current `setup.py`
  has no `install_requires` so `pip install pydlock` breaks on first use, plan §1). Single-source
  `__version__ = "2.0.0"` (kill the trailing-dot f-string in `pydlock/constants.py` and the
  `1.2.0.15`/`"1.3.0."`/four-part scheme). Add a `pydlock` console entry point plus a `main()`
  in `pydlock/__main__.py` for it to target (keep `python -m pydlock` working). **Delete
  `version.json`, `setup.py`, and `build.py`.** No behavior change (still v1 format, still has
  `python`/`run` — those go in Phase B).
  `verify: pip install -e . && python -c "import pydlock; assert pydlock.__version__ == '2.0.0'"`
- [x] 2. Metadata hygiene (plan §License, design D2 — MIT is already present, **no relicense**):
  add SPDX `license = "MIT"` in `pyproject.toml`; keep the MIT `LICENSE` file; replace the
  duplicated ~30-line MIT block atop each source file (`__init__.py`, `__main__.py`,
  `constants.py`) with a one-line `# SPDX-License-Identifier: MIT` header (keep the short
  authorship/contact docstring — the public `Contact@ErickShepherd.com` is intended and stays).
  Refresh `.gitignore` / `MANIFEST.in` for build artifacts (`dist/`, `*.egg-info/`,
  `.pytest_cache/`). `verify: pip install -e . && python -c "import pydlock"`

## Phase B — core v2 behavior (the fix; v2.0.0)

- [x] 3. **scrypt KDF + versioned envelope** (design §The envelope format, §Key decisions D3).
  Move key derivation out of the password prompt and into `encrypt`/`decrypt` where the salt is
  available. On `encrypt`: generate a fresh 16-byte `os.urandom` salt, derive
  `key = urlsafe_b64encode(Scrypt(salt, length=32, n=2**15, r=8, p=1).derive(password_bytes))`,
  and write the envelope: magic `b"PYDLOCK\x02\n"` + a UTF-8 JSON header
  `{"kdf":"scrypt","n":32768,"r":8,"p":1,"salt":"<base64>"}` + newline + the Fernet token. On
  `decrypt`: parse the header, re-derive the key from the stored salt/params. Leave the `kdf`
  dispatch open to a documented `"pbkdf2"` fallback id (unknown id → clear error, not a silent
  mis-decrypt). No custom crypto — Fernet is unchanged.
- [x] 4. **Bytes-mode I/O + atomic writes** (plan §1, design §Key decisions D6). Read/write
  files as `"rb"`/`"wb"` so binary files and Windows executables round-trip losslessly (fixes
  the corruption the README documents as "unfixable" — it *is* fixable); drop the file-content
  `encoding` coupling (password encoding stays). Make `lock`/`unlock` writes atomic: write to a
  temp file then `os.replace` (no more `"w+"` truncate-in-place → crash-safe).
- [x] 5. **In-tool v1 legacy-decrypt** (design D4). `unlock`/`decrypt` auto-detect a
  **non-magic** (v1) file — a raw Fernet token, no `b"PYDLOCK\x02"` prefix — and decrypt it with
  the old scheme byte-for-byte:
  `key = urlsafe_b64encode(sha256(password).hexdigest()[:32].encode())`. `lock` **always writes
  v2**, so re-locking a v1 file upgrades it. Strand no data; the one-line UX is unchanged.
- [x] 6. **Remove `python`/`run`; add `encrypt`/`decrypt` aliases** (design Stage-0). Delete the
  `python()` (`exec`) and `run()` (`subprocess … shell=True`) functions from
  `pydlock/__init__.py` and drop the now-dead `arguments` parameter threaded through
  `lock`/`unlock`. In `pydlock/__main__.py`, reduce the CLI to `{lock, unlock, encrypt, decrypt}`
  where `encrypt`→`lock` and `decrypt`→`unlock`. Fix the docstring typo (`encrypt` says
  "Decrypts") and the `double_password_prompt` `key1/key2` naming. First full type-hint pass.
  `verify: grep -rn "exec(\|shell=True" pydlock/ ; test $? -eq 1`

## Phase C — tests (offline)

- [x] 7. pytest suite, **all offline**, over small fixtures (plan §Phase 4, design §Key
  decisions): encrypt→decrypt **round-trip for a text file AND a binary file** (the binary case
  pins the bytes-mode fix); **wrong password fails cleanly** (clear message/return, original file
  untouched, no traceback); **per-file salt uniqueness** (locking the same file+password twice
  yields different salts and different ciphertext); **v1 legacy-decrypt** (a committed v1 fixture
  — file + known password — decrypts, and re-`lock` produces a v2 envelope); **KDF params
  round-trip** (params written into the header are read back and used; a tampered header/token
  fails Fernet's HMAC → clean failure, never silent wrong-plaintext); **atomic write** (an
  interrupted lock leaves the original intact). Commit the v1 fixture with a provenance note.
  `verify: python -m pytest -q`

## Phase D — CI

- [ ] 8. GitHub Actions `.github/workflows/ci.yml`: **ruff** + **pytest matrix (3.10–3.13)** +
  `python -m build` + `twine check dist/*` (proves publish-readiness). Add a permissive ruff
  config; run `ruff check .` and fix findings. Dormant until pushed (local-only rule).
  `verify: ruff check .`

## Phase E — README + release prep

- [ ] 9. Refresh `README.rst` for v2 (plan §Phase 5): keep the **dead-simple one-liner
  `pydlock lock file` / `pydlock unlock file` front-and-center** — the trivial UX is the selling
  point. Document the **v2.0.0 breaking change** (new on-disk envelope), the **migration** (v1
  files decrypt transparently; re-`lock` to upgrade; `pydlock<2` as the documented fallback), a
  short **"how your password is protected now"** note (salted scrypt), the **binary-file fix**,
  the **removal of `python`/`run`**, and the new **`encrypt`/`decrypt` aliases**.
- [ ] 10. Add `CHANGELOG` **v2.0.0** entry (convert `CHANGELOG.rst` to Markdown or keep RST;
  backfill prior entries + the v2 breaking-change/migration notes), a `CITATION.cff`, and
  `.github/workflows/publish.yml` — **OIDC Trusted Publishing**, approval-gated `pypi` /
  `testpypi` GitHub Environments, triggered on `release: [released]` + `workflow_dispatch`.
  **Copy the pattern from `../cosmic_crunch/.github/workflows/publish.yml`** (adapt the project
  name to `pydlock`). No stored token — never commit any secret.
- [ ] 11. Write `docs/release-checklist.md` for the **owner-gated tail** (plan §5, design
  §Rollout): the git-history author/committer email rewrite
  (`erickeshepherd@gmail.com` → `24425940+ErickShepherd@users.noreply.github.com`, display name
  kept; `git filter-repo --mailmap` or `filter-branch --env-filter` over all history; set
  repo-local `git config` to match; re-run leak-guard) → **force-push** the rewritten history to
  the private remote → **make the repo public** → merge (after the out-of-loop
  `pre-merge-review`) → tag `v2.0.0` on the merged default branch → cut the GitHub Release →
  gated `publish.yml` → PyPI (republish over the existing project). Model it on
  `../cosmic_crunch/docs/release-checklist.md`, adding the history-rewrite + force-push steps
  (which cosmic did not have). **Tag nothing and publish nothing here** — this item only
  *documents* the tail; every step in it is performed by the owner, outside the loop.
