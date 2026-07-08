# Repo improvement plan — pydlock

**Date:** 2026-07-08
**Author:** Claude (planning session; implementation deferred to a separate Opus session)
**Status:** DRAFT — awaiting owner sign-off on the decisions in §2 before implementation

## 0. Context and goal

`pydlock` is a dead-simple file-encryption CLI + library: `python -m pydlock lock secret.txt`
prompts for a password and encrypts the file in place; `unlock` reverses it. The name is
"padlock" respelled with Python's "py"; the library API is `pydlock.lock()` /
`pydlock.unlock()`. It was written April 2020 (11 commits, last touched then) and is
**already public on PyPI** as `pydlock` (latest `1.2.0.15`) — but the GitHub repo is still
**private**. Encryption uses the `cryptography` library's Fernet (AES-128-CBC + HMAC-SHA256),
which is sound; the defect is entirely in *how the key is derived from the password*.

**Owner's original intent (load-bearing design constraint):** a one-line command that a
person with little or no technical knowledge can use to encrypt/decrypt a file. Trivial UX
is the whole point and must survive every change below — "enter a password" stays the entire
mental model.

**Goal:** make the repo publishable as a hardened **v2.0.0** — fix the weak key-derivation
function (the headline), sanitize git history before it goes public, and bring packaging /
tests / CI to the same modern standard as the two sibling repos being prepared this session
(`cosmic_crunch`, `noaa_esrl_gmd_file_reader` — same playbook, adapted). Because v2 changes
the on-disk format, v1-locked files won't decrypt under the new scheme unaided; the plan
carries an in-tool migration path so no user is stranded and the one-line UX is preserved.

## 1. Current-state assessment (measured 2026-07-08)

### Headline defect: weak, unsalted, single-round KDF

`pydlock/__init__.py::password_prompt` derives the Fernet key as:

```python
digest = sha256(password.encode(encoding)).hexdigest()   # 64 hex chars
key    = urlsafe_b64encode(digest.encode(encoding)[:32])  # first 32 hex chars, b64'd
```

This is a **single, unsalted SHA-256**. Two independent consequences:

- **No salt.** Identical passwords always produce identical keys, so identical plaintext
  encrypted by two users yields correlatable ciphertext, and precomputed
  (rainbow-table) attacks apply. There is no per-file uniqueness.
- **No work factor.** SHA-256 is designed to be *fast*; a single round makes offline
  brute-force / dictionary attack against a captured ciphertext cheap. A password KDF is
  supposed to be deliberately slow and memory-hard.

Fernet itself is fine. The fix is to derive the key with a **salted, tunable password KDF**
— **scrypt** (preferred; memory-hard) or PBKDF2-HMAC-SHA256 as a fallback — from the
`cryptography` library, and to store a small **versioned envelope** with each encrypted file
carrying `{format-version, KDF id, KDF params, random per-file salt}`. Decryption stays
"enter your password" (the tool reads the salt/params from the file), so UX is unchanged and
the format is future-proof. This is a **breaking on-disk change** → **v2.0.0** (see §2 D3/D4,
design doc for the envelope layout and migration). **No custom crypto** — vetted primitives
only.

### History / publication blocker: private email across all commits

Every commit is authored and committed by `Erick Shepherd <<redacted private address>>` — the
owner's **private** gmail. Leak-guard flags this: it must not become public. Before the repo
is made public it must be rewritten across **all** history to the GitHub noreply identity
`24425940+ErickShepherd@users.noreply.github.com`, and the repo-local git config set to the
same, so future commits stay clean. This is a **whole-history rewrite** (every commit SHA
changes) and therefore does *not* fit the normal branch → review → merge mechanic — it is a
dedicated, owner-supervised step that requires a force-push to the private remote
(owner-gated). See Phase 1 and §5. (No secret keys, tokens, or credentials were found
anywhere in history — history is otherwise clean. Note the docstrings' public contact
address `Contact@ErickShepherd.com` is *intended* to be public and stays.)

### License: already MIT (brief's "no LICENSE" finding is stale)

Contrary to the intake note, a `LICENSE` file (MIT) **is present**, and MIT is declared in
every module docstring and in `setup.py`'s classifiers. Unlike the two sibling repos there is
**no AGPL→MIT relicense to do** — MIT is the owner's proportionality choice for small
utilities and is already in place. The only work is metadata hygiene: carry the MIT `LICENSE`
into the `pyproject.toml` build, add an SPDX `license` field, and drop the redundant ~30-line
MIT block duplicated at the top of every source file in favor of a short SPDX header.

### Packaging / quality defects

- **Undeclared runtime dependency (real bug).** `setup.py`'s `SETUP_KWARGS` has **no
  `install_requires`**, yet the package imports `cryptography`. `pip install pydlock` into a
  clean environment does not pull `cryptography` → `ImportError` on first use. v2 must declare
  it.
- **Malformed version string.** `constants.py` renders `__version__` as
  `f"{major}.{minor}.{patch}."` — a **trailing dot** (currently `"1.3.0."`), and `version.json`
  says `{1,3,0}` while PyPI shows `1.2.0.15` and `build.py` documents a *four*-part
  major/minor/maintenance/build scheme. The versioning is internally inconsistent. v2.0.0
  resets this to a clean single-sourced `2.0.0`.
- **Text-mode file I/O corrupts binary files (real bug).** `encrypt`/`decrypt` open files as
  `"r"`/`"w+"` with an `encoding` and `.encode()`/`.decode()` the contents. Fernet works on
  bytes; forcing a text codec means any file that isn't valid text in that codec (images,
  archives, executables) is mangled or errors out. This is precisely the "locking/unlocking
  a Windows executable corrupts it" behavior the README documents as unfixable — it is
  fixable: **read/write bytes** (`"rb"`/`"wb"`).
- **Non-atomic in-place overwrite.** `lock`/`unlock` truncate the original with `"w+"` and
  write; an interruption mid-write destroys the file. v2 writes atomically (temp file +
  `os.replace`).
- **Decrypt-and-execute subcommands (`python`, `run`).** `python()` runs `exec(contents)` on
  the decrypted file; `run()` does `subprocess.run(cmd, shell=True)` on the decrypted path
  then re-locks. These are (a) a security footgun, (b) scope creep well beyond "encrypt a
  file for a non-technical user," and (c) fragile — `run` leaves the file **decrypted on
  disk** if the process is interrupted between unlock and re-lock. Recommend removal (§2 D5).
- **No `install_requires`, no pytest suite, no CI, no `pyproject.toml`, a bespoke
  `build.py`** that shells out to `twine upload` behind `input()` prompts (superseded by the
  OIDC publish workflow in Phase 5). `FUTURE.rst` sketches ambitious directory-zip encryption
  and obfuscate-compile "source protection" chains — explicitly declined as scope creep (§4).
- Minor: `encrypt`'s docstring says "Decrypts"; the dead `arguments` parameter is threaded
  through `lock`/`unlock` but only `run` uses it; `double_password_prompt` names its
  variables `key1/key2` though they are derived keys, not passwords.

### Context worth documenting, not fixing

Fernet is AES-128-CBC + HMAC-SHA256 with authenticated tokens and a timestamp — a sound,
vetted construction. v2 keeps Fernet and fixes only the KDF and the envelope around it; this
is a targeted hardening, not a crypto redesign.

## 2. Decisions required from the owner (blocking)

**D1 — Keep the name `pydlock`? — RECOMMEND KEEP (owner-confirmable).** The package is already
public on PyPI under this name with released versions; the name is an established, memorable
pun (padlock → py-dlock) and the API verbs `lock()`/`unlock()` lean on it. Unlike the sibling
repos (never published, free to rename), renaming here would strand the PyPI project and
existing installs. Recommendation: **keep**.

**D2 — License. — RECOMMEND KEEP MIT (already in place; owner-confirmable).** MIT `LICENSE`
already exists and is the owner's proportionality choice for small utilities. No relicense.
Work is metadata-only (SPDX field + drop duplicated per-file MIT blocks).

**D3 — KDF choice. — RECOMMEND scrypt with a versioned file envelope (owner-confirmable).**
Salted, tunable, memory-hard scrypt (`cryptography` `hazmat` `Scrypt`, e.g. n=2¹⁵, r=8, p=1)
derives the 32-byte key; a per-file random salt and the KDF params are stored in a small
versioned envelope prepended to the Fernet token. PBKDF2-HMAC-SHA256 (~600k iterations) is the
documented fallback for constrained environments. See the design doc for the envelope layout.
Recommendation: **scrypt**.

**D4 — v1 migration path. — RECOMMEND in-tool v1 legacy-decrypt (owner-confirmable).** v2 is a
breaking on-disk change; existing v1-locked files must remain recoverable. Options weighed in
the design doc: (a) **in-tool legacy read** — `unlock` detects a v1 file (no v2 envelope
magic) and transparently decrypts it with the old unsalted-SHA-256 scheme, so the user just
re-`lock`s to upgrade; (b) a documented "install `pydlock<2`, decrypt, upgrade, re-lock"
procedure. Recommendation: **(a)** — it keeps the one-line UX intact and strands no data;
`lock` always writes v2.

**D5 — Remove the `python` and `run` subcommands? — RECOMMEND REMOVE (owner-confirmable; this
is the main judgment call).** They decrypt-and-execute arbitrary code (`exec` /
`shell=True`), which is a security footgun and sits far outside "encrypt a file for a
non-technical user." Removing them shrinks the attack surface and the CLI to the two verbs
that *are* the point (`lock`/`unlock`). Alternative: keep them behind a loud warning. This is
a breaking CLI change either way → fits v2.0.0. Recommendation: **remove** (revisit later if a
real user asks). See §4 and design Open Questions.

**D6 — Bytes-mode file I/O. — RECOMMEND yes (owner-confirmable).** Read/write files as bytes so
binary files (and Windows executables) round-trip losslessly, fixing the documented
corruption. The `encoding` parameter for *file contents* goes away (password encoding stays).
Strictly-better behavior; part of v2.0.0.

**D7 — PyPI publication. — RECOMMEND publish-ready in CI; actual publish owner-gated.** Same as
the siblings: CI proves publish-readiness (`python -m build` + `twine check`, and a
`publish.yml` wired for OIDC Trusted Publishing); the actual release, the force-push of
rewritten history, and making the repo public all stay owner-gated, outside every phase (§5).

## 3. Planned work (phased; each phase = one branch → pre-merge-review → merge)

> **Phase 1 is special:** a whole-history email rewrite cannot be a normal mergeable feature
> branch (it re-SHAs every commit). It is a dedicated owner-supervised operation; the
> remaining phases (2–5) follow the standard branch → `pre-merge-review` → merge cadence and
> build on the rewritten history.

### Phase 1 — History hygiene (prerequisite for going public; special step)
- Rewrite author **and** committer email across the entire history,
  `<redacted private address>` → `24425940+ErickShepherd@users.noreply.github.com`
  (keep the display name `Erick Shepherd`). Prefer `git filter-repo --mailmap` (or
  `git filter-branch --env-filter` as a dependency-free fallback) over the full commit range.
- Set repo-local `git config user.email`/`user.name` to the noreply identity so future
  commits stay clean.
- Verify no private gmail remains anywhere in the tree (the docstrings' public
  `Contact@ErickShepherd.com` is intended and stays); re-run leak-guard to confirm clean.
- **Gate:** leak-guard clean over the rewritten history; owner acknowledges the rewrite
  requires a force-push to the private remote (that push stays in the owner-gated tail, §5).

### Phase 2 — Packaging + metadata (mechanical, no behavior change)
- Add `pyproject.toml` (hatchling); single-source `__version__ = "2.0.0"`; **delete
  `version.json`, `setup.py`, and `build.py`** (the four-part/trailing-dot scheme and the
  interactive `twine` uploader all go).
- **Declare the `cryptography` dependency** (the missing `install_requires`) with a sensible
  floor; `requires-python = ">=3.9"`.
- Console entry point `pydlock` (so `pydlock lock file` works alongside `python -m pydlock`);
  keep `python -m pydlock` working via `__main__`.
- SPDX `license = "MIT"`; keep the MIT `LICENSE`; replace the duplicated ~30-line MIT block
  atop each source file with a one-line SPDX header.
- First type-hint pass; no behavior change (KDF/envelope land in Phase 3).

### Phase 3 — The KDF + envelope (v2.0.0 behavior; the headline)
- Move key derivation out of the prompt and into `encrypt`/`decrypt` where the salt is
  available: capture the password, generate a random salt (encrypt) or read it from the
  envelope (decrypt), then run the KDF.
- **scrypt** KDF (per D3) producing the 32-byte Fernet key; per-file random salt.
- **Versioned envelope** prepended to the Fernet token carrying
  `{magic/version, kdf id, n, r, p, salt}` (layout in the design doc); `lock` always writes
  v2.
- **In-tool v1 legacy-decrypt** (per D4): `unlock` detects a v1 file (no v2 magic) and
  decrypts with the old `urlsafe_b64encode(sha256(pw).hexdigest()[:32])` scheme; re-`lock`
  upgrades it to v2.
- **Bytes-mode I/O** (per D6) and **atomic writes** (temp file + `os.replace`).
- Apply D5 (remove `python`/`run`, or gate them) — the CLI reduces to `lock`/`unlock`
  (+ optional `encrypt`/`decrypt` aliases, see Open Questions).
- Docstring/typo cleanups; drop the dead `arguments` parameter as its consumer disappears.

### Phase 4 — Tests + CI
- pytest, no network, over small fixtures:
  - encrypt → decrypt **round-trip** for a text file **and a binary file** (the binary case
    pins the bytes-mode fix);
  - **wrong password fails cleanly** (clear message / return value, original file untouched,
    no traceback);
  - **per-file salt uniqueness** — locking the same plaintext+password twice yields different
    salts and different ciphertext;
  - **v1 legacy-decrypt** — a fixture locked with the v1 scheme + known password decrypts, and
    re-locking produces a v2 envelope;
  - **KDF params honored** — params written into the envelope are read back and used; a
    tampered envelope/token fails authentication rather than silently mis-decrypting;
  - **atomic write** — an interrupted lock leaves the original intact.
- GitHub Actions: ruff + pytest on 3.9–3.13; `python -m build` + `twine check` job proving
  publish-readiness. Dormant until pushed (local-only rule).

### Phase 5 — README + release prep + publish workflow
- README refresh (keep the **one-line `lock`/`unlock` example front-and-center** — the UX is
  the selling point): add the v2.0.0 breaking-change + migration note (v1 files transparently
  decrypt, re-lock to upgrade), a short "how the password is protected now" security note
  (salted scrypt), the binary-file fix, and the removal of `python`/`run` if adopted.
- `CHANGELOG` (convert to Markdown or keep RST; add the 2.0.0 entry), `CITATION.cff`,
  `.github/workflows/publish.yml` (OIDC Trusted Publishing, approval-gated `pypi`/`testpypi`
  environments, triggered on `release: [released]` + `workflow_dispatch` — reused from the
  sibling repos), local `v2.0.0` tag, and an owner checklist for the gated tail.

### Ordering rationale
History hygiene first because it is a prerequisite for *any* public exposure and is a
whole-history operation that later branches must build on. Packaging (mechanical) is kept in a
separate diff from the KDF/envelope behavior change so review can reason about each cleanly.
Stop-anywhere is safe after Phase 3 (the tool encrypts correctly with the hardened KDF); Phases
4–5 are quality and release scaffolding.

## 4. Explicitly out of scope
- **Directory / archive encryption**, obfuscate-compile "source protection" chains, and the
  other `FUTURE.rst` ambitions — scope creep against the "tiny single-purpose tool" intent.
- **Key files, asymmetric (public-key) crypto, keyrings** — password-in, password-out stays
  the entire model.
- **The `python`/`run` execute-after-decrypt features** — recommended for removal (D5), not
  extension.
- **Rewriting Fernet / rolling any custom crypto** — vetted primitives only.
- **Publishing to PyPI, force-pushing rewritten history, or making the repo public** —
  owner-gated, outside all phases (§5, D7).

## 5. Owner-gated tail (outside all phases)
1. **Force-push the rewritten history** to the private remote (Phase 1 re-SHAs everything;
   this overwrites the remote — owner-run, one time).
2. **Make the GitHub repo public.**
3. **Cut the GitHub release** (`v2.0.0`) → triggers the gated `publish.yml` → PyPI. Because
   `pydlock` already exists on PyPI, this *republishes* the project at 2.0.0.

## 6. Risks
- **Data loss during history rewrite / force-push.** Mitigated: take a full backup clone
  before Phase 1; the rewrite is mechanical (email only) and verifiable (`git log --format`
  diff before/after); force-push is a deliberate owner step.
- **A user cannot recover a v1 file after upgrading.** Mitigated by the in-tool legacy-decrypt
  path (D4) plus the documented `pydlock<2` fallback; a legacy fixture in the test suite pins
  the behavior.
- **scrypt unavailable / too memory-hungry in some environment.** Mitigated: params are stored
  per-file so they're tunable, and PBKDF2 is a documented fallback KDF id the envelope can
  carry.
- **Breaking CLI change (removing `python`/`run`) surprises an existing user.** Low — niche
  features; the CHANGELOG calls it out, and D5 is owner-confirmable (keep-with-warning is the
  alternative).

## 7. Definition of done (per phase, gated by `pre-merge-review` except P1)
- **P1:** all-history author/committer email is the noreply identity (verified via
  `git log --format='%ae %ce'`); repo git config set; leak-guard clean; owner briefed on the
  force-push. (Not a mergeable PR — a supervised rewrite.)
- **P2:** `pip install -e .` works and **pulls `cryptography`**; `pydlock --help` and
  `python -m pydlock --help` both work; `pydlock.__version__ == "2.0.0"`; `version.json` /
  `setup.py` / `build.py` gone; behavior unchanged from v1 (round-trip still works, still v1
  format).
- **P3:** files lock with a salted scrypt envelope; two locks of the same input differ; a v1
  fixture still unlocks; a binary file round-trips; `grep -rn "exec(\|shell=True" pydlock/`
  is empty if D5 = remove.
- **P4:** pytest green offline (round-trip incl. binary, wrong-password, salt-uniqueness,
  v1-legacy, tamper-fails); CI workflows valid; build + twine-check green locally.
- **P5:** README leads with the one-liner and documents the v2 migration; `publish.yml`
  present and OIDC-wired; `CITATION.cff` + CHANGELOG 2.0.0; `v2.0.0` tagged locally; owner
  checklist for the gated tail written.
