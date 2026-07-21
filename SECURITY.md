# Security Policy

## Supported versions

Only the latest released version of pydlock on PyPI receives security fixes.
Please upgrade to the newest release before reporting an issue.

| Version | Supported |
|---------|-----------|
| latest  | ✅        |
| older   | ❌        |

## Reporting a vulnerability

Please report security vulnerabilities **privately**, not in a public issue.

- Preferred: open a report through GitHub **Private Vulnerability Reporting** at
  <https://github.com/ErickShepherd/pydlock/security/advisories/new>.
- Alternatively, email **dev@erickshepherd.com**.

Please include a description, affected version(s), and a minimal reproduction if
possible. You can expect an initial acknowledgement within a few days. Fixes are
released as a new PyPI version with a `CHANGELOG.md` entry crediting the reporter
if desired.

## Scope

pydlock encrypts a file's contents with a password (scrypt + Fernet). Its
security boundary — what is and is not guaranteed (envelope authentication,
symlink/hard-link rejection, concurrent-edit detection, atomic vs power-loss
durability, and the metadata Fernet exposes) — is documented in the
"Security boundaries" section of the README.
