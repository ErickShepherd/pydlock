# Test fixture provenance

## `v1_legacy.locked`

A file encrypted with the **pre-2.0 (v1) pydlock scheme**, committed so the v2
in-tool legacy-decrypt path (`pydlock.decrypt` on a non-magic file) cannot
silently regress.

- **Password:** `legacy-password` (test-only; not a real secret).
- **Plaintext:**
  ```
  This file was encrypted by pydlock v1.
  It must still decrypt under v2.
  ```
- **Scheme (v1, byte-for-byte):** the whole file is a raw Fernet token whose
  key was derived as

  ```python
  key = urlsafe_b64encode(sha256(password.encode("utf-8")).hexdigest().encode("utf-8")[:32])
  token = Fernet(key).encrypt(plaintext)
  ```

  i.e. an unsalted SHA-256 hex digest truncated to 32 characters — the weak KDF
  that pydlock v2 replaces with salted scrypt. There is no `PYDLOCK\x02` magic
  prefix (a v1 token begins with Fernet's `gAAAAA…`), which is exactly how the
  v2 reader distinguishes a legacy file.

The in-tool counterpart of this derivation is `pydlock._derive_legacy_key`.
Regenerate with the snippet above if ever needed (the Fernet token embeds a
random IV + timestamp, so the exact bytes will differ but will still decrypt).
