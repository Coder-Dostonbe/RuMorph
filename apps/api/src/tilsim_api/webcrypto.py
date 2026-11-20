"""PBKDF2 through the platform's Web Crypto (crypto.subtle), for Pyodide.

Used by the Worker (src/entry.py). Importing this module outside Pyodide is
fine; calling `derive` there is not (there is no `js` module).
"""

from __future__ import annotations

from . import passwords


async def derive(password: bytes, salt: bytes, iterations: int) -> bytes:
    from js import Object, Uint8Array, crypto  # Pyodide only
    from pyodide.ffi import to_js

    key = await crypto.subtle.importKey(
        "raw", to_js(password), to_js({"name": "PBKDF2"}, dict_converter=Object.fromEntries), False,
        to_js(["deriveBits"]),
    )
    params = to_js(
        {"name": "PBKDF2", "hash": "SHA-256", "salt": to_js(salt), "iterations": iterations},
        dict_converter=Object.fromEntries,
    )
    bits = await crypto.subtle.deriveBits(params, key, passwords.KEY_BYTES * 8)
    return bytes(Uint8Array.new(bits).to_py())
