"""Password hashing: PBKDF2-HMAC-SHA256.

Stored format: pbkdf2_sha256$<iterations>$<salt, base64>$<hash, base64>.

The key derivation itself is passed in (`derive`), because Python Workers run
on Pyodide, whose hashlib has no pbkdf2_hmac (it needs OpenSSL). In the Worker
the derivation runs in Web Crypto (webcrypto.py); in tests and scripts on
CPython it runs in hashlib. Both compute the same PBKDF2, so hashes made by one
verify with the other (tests/js/webcrypto.test.mjs checks this).

Iterations: Cloudflare's Web Crypto allows at most 100 000 PBKDF2 iterations,
so that is the default. The count is stored with each hash, so it can be
raised later; needs_rehash() then upgrades a hash at the next sign-in.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from collections.abc import Awaitable, Callable

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 100_000
MIN_LENGTH = 10
MAX_LENGTH = 200
KEY_BYTES = 32

Derive = Callable[[bytes, bytes, int], Awaitable[bytes]]


async def stdlib_derive(password: bytes, salt: bytes, iterations: int) -> bytes:
    if not hasattr(hashlib, "pbkdf2_hmac"):
        raise RuntimeError("hashlib.pbkdf2_hmac is unavailable here (Pyodide); pass webcrypto.derive instead")
    return hashlib.pbkdf2_hmac("sha256", password, salt, iterations, KEY_BYTES)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


async def hash_password(password: str, iterations: int, derive: Derive = stdlib_derive) -> str:
    salt = os.urandom(16)
    digest = await derive(password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${_b64(salt)}${_b64(digest)}"


async def verify_password(password: str, stored: str, derive: Derive = stdlib_derive) -> bool:
    try:
        algorithm, iterations, salt, digest = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = base64.b64decode(digest, validate=True)
        salt_bytes = base64.b64decode(salt, validate=True)
        count = int(iterations)
    except (ValueError, TypeError):
        return False
    actual = await derive(password.encode("utf-8"), salt_bytes, count)
    return hmac.compare_digest(actual, expected)


def needs_rehash(stored: str, iterations: int) -> bool:
    parts = stored.split("$")
    try:
        return len(parts) != 4 or parts[0] != ALGORITHM or int(parts[1]) < iterations
    except ValueError:
        return True


# Verifying against this when the email is unknown makes both cases take the same time.
_DUMMY: dict[int, str] = {}


async def dummy_verify(password: str, iterations: int, derive: Derive = stdlib_derive) -> None:
    if iterations not in _DUMMY:
        _DUMMY[iterations] = await hash_password("dummy-password-for-timing", iterations, derive)
    await verify_password(password, _DUMMY[iterations], derive)
