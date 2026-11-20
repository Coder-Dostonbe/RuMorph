"""Password hashing: PBKDF2-HMAC-SHA256 from the standard library.

Stored format: pbkdf2_sha256$<iterations>$<salt, base64>$<hash, base64>.
The iteration count is part of the stored value, so it can be raised later and
old hashes still verify (needs_rehash tells when to upgrade on next login).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

ALGORITHM = "pbkdf2_sha256"
MIN_LENGTH = 10
MAX_LENGTH = 200


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str, iterations: int) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def needs_rehash(stored: str, iterations: int) -> bool:
    parts = stored.split("$")
    return len(parts) != 4 or parts[0] != ALGORITHM or int(parts[1]) < iterations


# Verifying against this when the email is unknown makes both cases take the same time.
_DUMMY = {}


def dummy_verify(password: str, iterations: int) -> None:
    if iterations not in _DUMMY:
        _DUMMY[iterations] = hash_password("dummy-password-for-timing", iterations)
    verify_password(password, _DUMMY[iterations])
