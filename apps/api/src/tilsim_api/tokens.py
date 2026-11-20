"""Access tokens (JWT, HS256, standard library only) and refresh tokens (opaque).

Access tokens are short-lived and never stored. Refresh tokens are random
strings; only their SHA-256 hash is stored (refresh_tokens.token_hash).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass

from .errors import unauthorized

REFRESH_PREFIX = "rt_"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


_HEADER = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())


@dataclass(frozen=True)
class AccessClaims:
    user_id: str
    role: str
    device_id: str
    issued_at: int
    expires_at: int


def issue_access_token(secret: bytes, *, user_id: str, role: str, device_id: str, now: int, ttl: int) -> str:
    payload = {"sub": user_id, "role": role, "did": device_id, "iat": now, "exp": now + ttl, "typ": "access"}
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{_HEADER}.{body}".encode("ascii")
    signature = _b64url(hmac.new(secret, signing_input, hashlib.sha256).digest())
    return f"{_HEADER}.{body}.{signature}"


def verify_access_token(secret: bytes, token: str, *, now: int) -> AccessClaims:
    try:
        header, body, signature = token.split(".")
    except ValueError:
        raise unauthorized("malformed token") from None
    if header != _HEADER:
        # Only our own header is accepted, which rules out "alg": "none" and algorithm confusion.
        raise unauthorized("unsupported token")
    expected = _b64url(hmac.new(secret, f"{header}.{body}".encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise unauthorized("invalid token signature")
    try:
        payload = json.loads(_b64url_decode(body))
        claims = AccessClaims(
            user_id=str(payload["sub"]),
            role=str(payload["role"]),
            device_id=str(payload["did"]),
            issued_at=int(payload["iat"]),
            expires_at=int(payload["exp"]),
        )
        if payload.get("typ") != "access":
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise unauthorized("malformed token") from None
    if claims.expires_at <= now:
        raise unauthorized("token expired")
    return claims


def new_refresh_token() -> str:
    return REFRESH_PREFIX + secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()
