# SPDX-License-Identifier: MIT

'''

Offline test suite for pydlock v2. Every test is pure local crypto over small
fixtures; nothing touches the network. The API is exercised with an explicit
``password=`` (bytes) so the tests never prompt via getpass.

'''

# Standard library imports.
import json
import os
from base64 import b64decode
from base64 import b64encode
from pathlib import Path

# Third party imports.
import pytest

# Local application imports.
import pydlock

PASSWORD = b"correct horse battery staple"
MAGIC    = b"PYDLOCK\x02\n"
FIXTURES = Path(__file__).parent / "fixtures"


def _header(envelope: bytes) -> dict:

    '''Parses the JSON header out of a v2 envelope.'''

    assert envelope.startswith(MAGIC)
    header_bytes, _, _token = envelope[len(MAGIC):].partition(b"\n")

    return json.loads(header_bytes.decode("utf-8"))


def test_text_round_trip(tmp_path):

    path     = tmp_path / "note.txt"
    original = "hello pydlock\nsecond line\n".encode("utf-8")
    path.write_bytes(original)

    pydlock.lock(str(path), password=PASSWORD)
    assert path.read_bytes().startswith(MAGIC)

    assert pydlock.unlock(str(path), password=PASSWORD) is True
    assert path.read_bytes() == original


def test_binary_round_trip(tmp_path):

    # All 256 byte values incl. NUL bytes — pins the bytes-mode I/O fix.
    path     = tmp_path / "blob.bin"
    original = bytes(range(256)) * 4 + b"\x00\xff\x80\x01"
    path.write_bytes(original)

    pydlock.lock(str(path), password=PASSWORD)
    pydlock.unlock(str(path), password=PASSWORD)

    assert path.read_bytes() == original


def test_wrong_password_fails_cleanly(tmp_path):

    path = tmp_path / "secret.txt"
    path.write_bytes(b"classified\n")
    pydlock.lock(str(path), password=PASSWORD)
    envelope = path.read_bytes()

    # A wrong password returns False (no traceback) and leaves the file as-is.
    assert pydlock.unlock(str(path), password=b"wrong") is False
    assert path.read_bytes() == envelope


def test_per_file_salt_uniqueness(tmp_path):

    path = tmp_path / "dup.txt"
    path.write_bytes(b"same content\n")

    pydlock.lock(str(path), password=PASSWORD)
    first = path.read_bytes()
    pydlock.unlock(str(path), password=PASSWORD)
    pydlock.lock(str(path), password=PASSWORD)
    second = path.read_bytes()

    # Same file + same password, but a fresh random salt each lock.
    assert _header(first)["salt"] != _header(second)["salt"]
    assert first != second


def test_kdf_params_round_trip(tmp_path):

    path = tmp_path / "params.txt"
    path.write_bytes(b"params check\n")
    pydlock.lock(str(path), password=PASSWORD)

    header = _header(path.read_bytes())
    assert header["kdf"] == "scrypt"
    assert header["n"]   == pydlock.SCRYPT_N
    assert header["r"]   == pydlock.SCRYPT_R
    assert header["p"]   == pydlock.SCRYPT_P
    assert len(b64decode(header["salt"])) == pydlock.SALT_BYTES

    # The stored params are actually used: decrypt re-derives from them.
    assert pydlock.unlock(str(path), password=PASSWORD) is True


def test_tampered_token_fails_never_wrong_plaintext(tmp_path):

    path     = tmp_path / "tamper.txt"
    original = b"do not silently corrupt\n"
    path.write_bytes(original)
    pydlock.lock(str(path), password=PASSWORD)

    # Flip the last byte of the Fernet token: HMAC must reject it cleanly.
    envelope     = bytearray(path.read_bytes())
    envelope[-1] ^= 0x01
    path.write_bytes(bytes(envelope))

    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_tampered_header_fails_never_wrong_plaintext(tmp_path):

    path     = tmp_path / "tamper_header.txt"
    original = b"header integrity\n"
    path.write_bytes(original)
    pydlock.lock(str(path), password=PASSWORD)

    raw                    = path.read_bytes()
    header_bytes, _, token = raw[len(MAGIC):].partition(b"\n")
    header                 = json.loads(header_bytes.decode("utf-8"))

    # Corrupt the stored salt (still valid base64): the re-derived key is wrong,
    # so Fernet rejects the token rather than returning wrong plaintext.
    salt    = bytearray(b64decode(header["salt"]))
    salt[0] ^= 0xFF
    header["salt"] = b64encode(bytes(salt)).decode("ascii")

    tampered = MAGIC + json.dumps(header, separators=(",", ":")).encode("utf-8") + b"\n" + token
    path.write_bytes(tampered)

    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_atomic_write_interrupt_leaves_original(tmp_path, monkeypatch):

    path     = tmp_path / "atomic.txt"
    original = b"ORIGINAL - must survive an interrupted lock\n"
    path.write_bytes(original)

    def boom(source, destination):
        raise RuntimeError("simulated crash before the atomic swap")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(RuntimeError):
        pydlock.lock(str(path), password=PASSWORD)

    # The original file is untouched and no temp file was left behind.
    assert path.read_bytes() == original
    assert list(tmp_path.glob(".pydlock-*")) == []


# --- str password via the public API (regression: v2.0.1) --------------------
#
# Every test above drives the API with a *bytes* password, which is exactly how
# the v2.0.0 str-password crash slipped through: pydlock.lock(path,
# password="a string") reached scrypt as a str and raised
# ``TypeError: Cannot convert str instance to a buffer``. These exercise the
# PUBLIC API with a str and pin that str and bytes are interchangeable.

STR_PASSWORD = "correct horse battery staple"   # the str form of PASSWORD


def test_str_password_text_round_trip(tmp_path):

    path     = tmp_path / "note.txt"
    original = "hello pydlock\nsecond line\n".encode("utf-8")
    path.write_bytes(original)

    # The crashing call: a plain str password through the public API.
    pydlock.lock(str(path), password=STR_PASSWORD)
    assert path.read_bytes().startswith(MAGIC)

    assert pydlock.unlock(str(path), password=STR_PASSWORD) is True
    assert path.read_bytes() == original


def test_str_password_binary_round_trip(tmp_path):

    path     = tmp_path / "blob.bin"
    original = bytes(range(256)) * 4 + b"\x00\xff\x80\x01"
    path.write_bytes(original)

    pydlock.lock(str(path), password=STR_PASSWORD)
    assert pydlock.unlock(str(path), password=STR_PASSWORD) is True

    assert path.read_bytes() == original


def test_wrong_str_password_fails_cleanly(tmp_path):

    path = tmp_path / "secret.txt"
    path.write_bytes(b"classified\n")
    pydlock.lock(str(path), password=STR_PASSWORD)
    envelope = path.read_bytes()

    # A wrong str password returns False (no traceback) and leaves the file as-is.
    assert pydlock.unlock(str(path), password="wrong string") is False
    assert path.read_bytes() == envelope


def test_str_and_bytes_passwords_are_interchangeable(tmp_path):

    # A file locked with a str password unlocks with the equivalent bytes, and
    # vice versa: normalisation is a pure str.encode(encoding), so the two forms
    # derive the same key. This also pins that bytes passwords do NOT regress.
    path     = tmp_path / "mix.txt"
    original = b"str and bytes agree\n"
    path.write_bytes(original)

    pydlock.lock(str(path), password=STR_PASSWORD)          # locked with str
    assert pydlock.unlock(str(path), password=PASSWORD) is True   # unlocked with bytes
    assert path.read_bytes() == original

    pydlock.lock(str(path), password=PASSWORD)              # locked with bytes
    assert pydlock.unlock(str(path), password=STR_PASSWORD) is True  # unlocked with str
    assert path.read_bytes() == original


def test_str_password_decrypts_v1_legacy(tmp_path):

    # The str normalisation must also cover the v1 legacy (SHA-256) path, not
    # just v2 scrypt: a str password decrypts a committed v1 fixture.
    fixture = (FIXTURES / "v1_legacy.locked").read_bytes()
    path    = tmp_path / "legacy.locked"
    path.write_bytes(fixture)

    assert pydlock.decrypt(str(path), password=V1_PASSWORD.decode("utf-8")) == V1_PLAINTEXT


# --- malicious / malformed v2 envelope rejection (security regression) -------


def _v2_envelope(header: dict, token: bytes = b"not-a-real-token") -> bytes:

    '''Hand-builds a v2 envelope: MAGIC + crafted JSON header + arbitrary token.'''

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")

    return MAGIC + header_bytes + b"\n" + token


def _good_salt() -> str:

    return b64encode(os.urandom(pydlock.SALT_BYTES)).decode("ascii")


def test_oversized_scrypt_n_rejected_without_allocation(tmp_path):

    # A crafted header requesting n = 2**30 would demand ~= 128 * 2**30 * 8
    # bytes (~1 TiB). Validation must reject it BEFORE Scrypt is constructed, so
    # this returns the clean failure sentinel fast and never allocates.
    path = tmp_path / "bomb.locked"
    header = {"kdf": "scrypt", "n": 2 ** 30, "r": 8, "p": 1, "salt": _good_salt()}
    path.write_bytes(_v2_envelope(header))

    assert pydlock.decrypt(str(path), password=PASSWORD) is None
    assert pydlock.unlock(str(path), password=PASSWORD) is False


def test_oversized_scrypt_r_rejected(tmp_path):

    path = tmp_path / "bomb_r.locked"
    header = {"kdf": "scrypt", "n": 2 ** 15, "r": 1024, "p": 1, "salt": _good_salt()}
    path.write_bytes(_v2_envelope(header))

    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_non_power_of_two_n_rejected(tmp_path):

    path = tmp_path / "npot.locked"
    header = {"kdf": "scrypt", "n": 2 ** 15 + 1, "r": 8, "p": 1, "salt": _good_salt()}
    path.write_bytes(_v2_envelope(header))

    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_unknown_kdf_rejected(tmp_path):

    path = tmp_path / "kdf.locked"
    header = {"kdf": "argon2id", "n": 2 ** 15, "r": 8, "p": 1, "salt": _good_salt()}
    path.write_bytes(_v2_envelope(header))

    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_malformed_header_bad_json(tmp_path):

    path = tmp_path / "badjson.locked"
    path.write_bytes(MAGIC + b"{not valid json" + b"\n" + b"token")

    # Must hit the clean failure path, not raise JSONDecodeError.
    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_malformed_header_missing_n(tmp_path):

    path = tmp_path / "missing_n.locked"
    header = {"kdf": "scrypt", "r": 8, "p": 1, "salt": _good_salt()}
    path.write_bytes(_v2_envelope(header))

    # Missing 'n' would be a KeyError; must be caught cleanly.
    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_malformed_header_n_as_string(tmp_path):

    path = tmp_path / "str_n.locked"
    header = {"kdf": "scrypt", "n": "32768", "r": 8, "p": 1, "salt": _good_salt()}
    path.write_bytes(_v2_envelope(header))

    # A string 'n' must be rejected by the type check, not passed to Scrypt.
    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_malformed_header_non_base64_salt(tmp_path):

    path = tmp_path / "badsalt.locked"
    header = {"kdf": "scrypt", "n": 2 ** 15, "r": 8, "p": 1, "salt": "!!!not base64!!!"}
    path.write_bytes(_v2_envelope(header))

    # binascii.Error (a ValueError subclass) must be caught cleanly.
    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_oversized_salt_rejected(tmp_path):

    path = tmp_path / "bigsalt.locked"
    big  = b64encode(b"\x00" * (pydlock.MAX_SALT_BYTES + 1)).decode("ascii")
    header = {"kdf": "scrypt", "n": 2 ** 15, "r": 8, "p": 1, "salt": big}
    path.write_bytes(_v2_envelope(header))

    assert pydlock.decrypt(str(path), password=PASSWORD) is None


def test_deeply_nested_header_rejected_without_recursionerror(tmp_path):

    # A crafted header whose JSON nests far deeper than the interpreter's
    # recursion limit makes json.loads raise RecursionError (a RuntimeError
    # subclass) — NOT in decrypt's caught tuple, so unpatched it escapes as a
    # raw traceback on hostile input, violating the "fails cleanly" guarantee.
    # It must instead return the clean sentinel (None), fast, no traceback.
    path   = tmp_path / "nested.locked"
    nested = ("[" * 30000) + ("]" * 30000)
    header = ('{"kdf":' + nested + "}").encode("utf-8")
    path.write_bytes(MAGIC + header + b"\n" + b"token")

    import time
    start = time.monotonic()
    assert pydlock.decrypt(str(path), password=PASSWORD) is None
    assert pydlock.unlock(str(path), password=PASSWORD) is False
    assert time.monotonic() - start < 1.0, "must reject fast, no deep recursion"


def test_validation_accepts_memory_product_ceiling():

    # A genuinely-derivable set that lands exactly ON the memory-product cap
    # (128 * 2**18 * 8 == 256 MiB == MAX_SCRYPT_MEM_BYTES) with a max-length
    # salt is valid and must NOT raise: the product bound is inclusive, and the
    # cap does not reject legitimate strong-but-bounded parameters. Checked
    # directly so no multi-GiB derivation is attempted. NB the FACTOR ceilings
    # (SCRYPT_MAX_N, SCRYPT_MAX_R) together now EXCEED the product cap by design
    # (see test_in_factor_bounds_but_over_memory_product_rejected), so they can
    # no longer be asserted acceptable as a combined set.
    n, r, p = 2 ** 18, 8, 1
    assert 128 * n * r == pydlock.MAX_SCRYPT_MEM_BYTES
    salt = b"\x00" * pydlock.MAX_SALT_BYTES
    assert pydlock._validate_scrypt_params(n, r, p, salt) is None


def test_validation_rejects_just_over_ceiling():

    # The next power of two above the ceiling is rejected (proves strict '>').
    with pytest.raises(ValueError):
        pydlock._validate_scrypt_params(pydlock.SCRYPT_MAX_N * 2, 8, 1, b"salt")


def test_in_factor_bounds_but_over_memory_product_rejected(tmp_path):

    # The residual DoS: n and r each sit at their (individually legal) per-factor
    # ceiling, yet 128 * n * r == 128 * 2**20 * 32 == 4 GiB, far over the 256 MiB
    # product cap. Unbounded this hangs the victim (>2 min) or throws an uncaught
    # MemoryError; the product check must reject it BEFORE Scrypt is constructed.
    n, r, p = pydlock.SCRYPT_MAX_N, pydlock.SCRYPT_MAX_R, 1
    assert 128 * n * r > pydlock.MAX_SCRYPT_MEM_BYTES   # in-factor-bounds, over-product

    # (a) rejected directly by the validator, before any allocation.
    with pytest.raises(ValueError):
        pydlock._validate_scrypt_params(n, r, p, os.urandom(pydlock.SALT_BYTES))

    # (b) rejected via the REAL decrypt() path on a crafted v2 file: clean
    #     sentinel, FAST (well under a second), no allocation/hang.
    path   = tmp_path / "mem_bomb.locked"
    header = {"kdf": "scrypt", "n": n, "r": r, "p": p, "salt": _good_salt()}
    path.write_bytes(_v2_envelope(header))

    import time
    start = time.monotonic()
    assert pydlock.decrypt(str(path), password=PASSWORD) is None
    assert pydlock.unlock(str(path), password=PASSWORD) is False
    assert time.monotonic() - start < 1.0, "product check must reject before Scrypt runs"


def test_high_p_cpu_bomb_rejected(tmp_path):

    # The p-inclusive residual: n and r sit AT the memory-product ceiling (128 *
    # n * r == 256 MiB, so a memory-only bound would ACCEPT it), but p=16
    # multiplies scrypt's CPU work ~16x (128 * n * r * p == 4 GiB-equivalent) —
    # a bounded-but-large CPU burn. The cost bound folds p in, so it must reject.
    n, r, p = 2 ** 18, 8, pydlock.SCRYPT_MAX_P
    assert 128 * n * r <= pydlock.MAX_SCRYPT_MEM_BYTES        # a memory-only bound would pass this
    assert 128 * n * r * p > pydlock.MAX_SCRYPT_MEM_BYTES     # the cost bound (with p) rejects it

    # (a) rejected directly by the validator, before any derivation.
    with pytest.raises(ValueError):
        pydlock._validate_scrypt_params(n, r, p, os.urandom(pydlock.SALT_BYTES))

    # (b) rejected via the REAL decrypt() path, fast, no CPU burn.
    path   = tmp_path / "cpu_bomb.locked"
    header = {"kdf": "scrypt", "n": n, "r": r, "p": p, "salt": _good_salt()}
    path.write_bytes(_v2_envelope(header))

    import time
    start = time.monotonic()
    assert pydlock.decrypt(str(path), password=PASSWORD) is None
    assert time.monotonic() - start < 1.0, "cost check must reject before Scrypt runs"


def test_above_default_params_round_trip(tmp_path):

    # A legitimate strong file (n above the encrypt-time default, still within
    # bounds) round-trips: validation does not reject valid-but-strong files.
    path     = tmp_path / "strong.txt"
    original = b"strong but bounded\n"
    path.write_bytes(original)

    n, r, p = 2 ** 16, 8, 1   # above the encrypt-time default n=2**15, well in bounds
    salt = os.urandom(pydlock.SALT_BYTES)
    key  = pydlock._derive_scrypt_key(PASSWORD, salt, n, r, p)
    from cryptography.fernet import Fernet
    token  = Fernet(key).encrypt(original)
    header = {"kdf": "scrypt", "n": n, "r": r, "p": p,
              "salt": b64encode(salt).decode("ascii")}
    path.write_bytes(_v2_envelope(header, token))

    assert pydlock.decrypt(str(path), password=PASSWORD) == original


# --- v1 legacy support (committed fixture; see tests/fixtures/PROVENANCE.md) ---

V1_PASSWORD  = b"legacy-password"
V1_PLAINTEXT = (
    b"This file was encrypted by pydlock v1.\n"
    b"It must still decrypt under v2.\n"
)


def test_v1_legacy_decrypt_and_upgrade(tmp_path):

    fixture = (FIXTURES / "v1_legacy.locked").read_bytes()
    assert not fixture.startswith(b"PYDLOCK\x02"), "fixture must be a non-magic v1 token"

    # Work on a copy so the committed fixture is never mutated.
    path = tmp_path / "legacy.locked"
    path.write_bytes(fixture)

    # Transparent v1 decrypt.
    assert pydlock.decrypt(str(path), password=V1_PASSWORD) == V1_PLAINTEXT

    # Unlock writes the plaintext; re-locking upgrades it to a v2 envelope.
    assert pydlock.unlock(str(path), password=V1_PASSWORD) is True
    assert path.read_bytes() == V1_PLAINTEXT

    pydlock.lock(str(path), password=V1_PASSWORD)
    assert path.read_bytes().startswith(MAGIC)
    assert pydlock.unlock(str(path), password=V1_PASSWORD) is True
    assert path.read_bytes() == V1_PLAINTEXT
