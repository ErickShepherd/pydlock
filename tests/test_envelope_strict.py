# SPDX-License-Identifier: MIT

'''

Strict v2 envelope + password validation regressions (triage stage T2).

The v2 parser used to detect a file by the magic PREFIX and split on the first
two newlines, and Fernet's base64 decoder silently discards non-alphabet bytes.
Together that accepted noncanonical/modified envelopes: bytes inserted on the
magic line, and trailing garbage after the token, both still decrypted. These
tests reproduce those two probes and pin the strict grammar: exact framing, one
separator each, canonical base64 for the salt and token, the promised salt
length, a non-empty token, and empty-password rejection on NEW encryption (while
recovery of a pre-existing empty-password file still works).

'''

# Standard library imports.
import json
import os
from base64 import b64encode

# Third party imports.
import pytest
from cryptography.fernet import Fernet

# Local application imports.
import pydlock

PASSWORD = b"correct horse battery staple"
MAGIC    = b"PYDLOCK\x02\n"
N, R, P  = pydlock.SCRYPT_N, pydlock.SCRYPT_R, pydlock.SCRYPT_P


def _real_envelope(tmp_path, plaintext=b"secret data\n") -> bytes:

    '''Produces a genuine pydlock v2 envelope by locking a scratch file.'''

    path = tmp_path / "src.txt"
    path.write_bytes(plaintext)
    pydlock.lock(str(path), password=PASSWORD)

    return path.read_bytes()


def _parts(envelope: bytes) -> tuple[bytes, bytes]:

    '''Splits a genuine envelope into (header_bytes, token).'''

    assert envelope.startswith(MAGIC)
    header, _, token = envelope[len(MAGIC):].partition(b"\n")

    return header, token


def _v2_from(header: dict, token: bytes) -> bytes:

    body = json.dumps(header, separators=(",", ":")).encode("utf-8")

    return MAGIC + body + b"\n" + token


def _write_and_decrypt(tmp_path, envelope: bytes):

    path = tmp_path / "candidate.locked"
    path.write_bytes(envelope)

    return path, pydlock.decrypt(str(path), password=PASSWORD)


# --- reproduced probes from the review --------------------------------------


def test_positive_control_real_envelope_decrypts(tmp_path):

    envelope = _real_envelope(tmp_path, b"round trip\n")
    _, plaintext = _write_and_decrypt(tmp_path, envelope)

    assert plaintext == b"round trip\n"


def test_inserted_bytes_on_magic_line_rejected(tmp_path):

    # Probe 1: `IGNORED` between the version byte and its newline used to be
    # ignored; exact framing must now reject it.
    envelope        = _real_envelope(tmp_path)
    header, token   = _parts(envelope)
    tampered        = b"PYDLOCK\x02" + b"IGNORED" + b"\n" + header + b"\n" + token

    _, plaintext = _write_and_decrypt(tmp_path, tampered)

    assert plaintext is None


def test_trailing_garbage_after_token_rejected(tmp_path):

    # Probe 2: appending `!!!` after the token used to decrypt because Fernet
    # discards non-alphabet bytes; strict base64 must now reject it.
    envelope = _real_envelope(tmp_path)

    _, plaintext = _write_and_decrypt(tmp_path, envelope + b"!!!")

    assert plaintext is None


# --- structural framing ------------------------------------------------------


def test_missing_header_token_separator_rejected(tmp_path):

    envelope      = _real_envelope(tmp_path)
    header, token = _parts(envelope)

    # No newline between header and token.
    _, plaintext = _write_and_decrypt(tmp_path, MAGIC + header + token)

    assert plaintext is None


def test_extra_separator_rejected(tmp_path):

    envelope      = _real_envelope(tmp_path)
    header, token = _parts(envelope)

    # A blank line before the token puts a newline inside the token line.
    _, plaintext = _write_and_decrypt(tmp_path, MAGIC + header + b"\n" + b"\n" + token)

    assert plaintext is None


def test_empty_token_rejected(tmp_path):

    envelope    = _real_envelope(tmp_path)
    header, _   = _parts(envelope)

    _, plaintext = _write_and_decrypt(tmp_path, MAGIC + header + b"\n")

    assert plaintext is None


# --- encoded-field validation ------------------------------------------------


def test_wrong_salt_length_rejected(tmp_path):

    # A canonical token (so the failure is attributable to the salt length),
    # but the salt is 8 bytes rather than the promised 16.
    salt   = os.urandom(8)
    key    = pydlock._derive_scrypt_key(PASSWORD, salt, N, R, P)
    token  = Fernet(key).encrypt(b"x")
    header = {"kdf": "scrypt", "n": N, "r": R, "p": P,
              "salt": b64encode(salt).decode("ascii")}

    _, plaintext = _write_and_decrypt(tmp_path, _v2_from(header, token))

    assert plaintext is None


def test_noncanonical_salt_rejected(tmp_path):

    envelope      = _real_envelope(tmp_path)
    header_bytes, token = _parts(envelope)
    header        = json.loads(header_bytes.decode("utf-8"))

    # Append a discarded space: decodes to the same bytes but is not canonical.
    header["salt"] = header["salt"] + " "

    _, plaintext = _write_and_decrypt(tmp_path, _v2_from(header, token))

    assert plaintext is None


def test_noncanonical_token_padding_rejected(tmp_path):

    envelope = _real_envelope(tmp_path)

    _, plaintext = _write_and_decrypt(tmp_path, envelope + b"==")

    assert plaintext is None


# --- decrypt failure never mutates the input ---------------------------------


def test_decrypt_failure_never_modifies_input(tmp_path):

    envelope      = _real_envelope(tmp_path)
    header, token = _parts(envelope)
    tampered      = b"PYDLOCK\x02" + b"IGNORED" + b"\n" + header + b"\n" + token

    path = tmp_path / "immutable.locked"
    path.write_bytes(tampered)

    assert pydlock.unlock(str(path), password=PASSWORD) is False
    assert path.read_bytes() == tampered   # unchanged


# --- empty-password rejection on encryption; recovery preserved --------------


@pytest.mark.parametrize("empty", [b"", ""], ids=["bytes", "str"])
def test_lock_rejects_empty_password(tmp_path, empty):

    path = tmp_path / "plain.txt"
    path.write_bytes(b"still plaintext")

    with pytest.raises(ValueError):
        pydlock.lock(str(path), password=empty)

    # The file was not encrypted with the empty password.
    assert path.read_bytes() == b"still plaintext"


def test_encrypt_function_rejects_empty_password(tmp_path):

    path = tmp_path / "plain.txt"
    path.write_bytes(b"data")

    with pytest.raises(ValueError):
        pydlock.encrypt(str(path), password="")


def test_decrypt_still_recovers_a_preexisting_empty_password_file(tmp_path):

    # An empty-password file could already exist (created before this rule).
    # Recovery must still work — the rule is encrypt-only. Build one directly,
    # bypassing the encrypt-time guard.
    plaintext = b"an empty-password file from before the rule\n"
    salt      = os.urandom(pydlock.SALT_BYTES)
    key       = pydlock._derive_scrypt_key(b"", salt, N, R, P)
    token     = Fernet(key).encrypt(plaintext)
    header    = {"kdf": "scrypt", "n": N, "r": R, "p": P,
                 "salt": b64encode(salt).decode("ascii")}

    path = tmp_path / "empty_pw.locked"
    path.write_bytes(_v2_from(header, token))

    assert pydlock.decrypt(str(path), password=b"") == plaintext
    assert pydlock.unlock(str(path), password=b"") is True
    assert path.read_bytes() == plaintext
