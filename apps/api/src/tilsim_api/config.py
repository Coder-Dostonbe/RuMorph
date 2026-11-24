"""Settings read from the Worker environment (vars and secrets)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MIN_SECRET_LENGTH = 32


class ConfigError(Exception):
    """The deployment is misconfigured; requests get a 500 and the log says why."""


@dataclass(frozen=True)
class Settings:
    jwt_secret: bytes
    allow_registration: bool = False
    cors_origins: frozenset[str] = frozenset()
    access_ttl: int = 15 * 60                  # seconds
    refresh_ttl: int = 30 * 24 * 60 * 60       # seconds
    # Cloudflare's Web Crypto allows at most 100 000 PBKDF2 iterations (see passwords.py).
    pbkdf2_iterations: int = 100_000
    max_failed_logins: int = 5                 # per email, per window
    failed_login_window: int = 15 * 60         # seconds
    max_registrations_per_ip: int = 5          # new accounts per network address, per window
    registration_window: int = 60 * 60         # seconds

    @classmethod
    def from_env(cls, env: Any) -> Settings:
        def get(name: str, default: str | None = None) -> str | None:
            value = getattr(env, name, None)
            return default if value is None else str(value)

        secret = get("JWT_SECRET")
        if not secret or len(secret) < MIN_SECRET_LENGTH:
            raise ConfigError(f"JWT_SECRET must be set to at least {MIN_SECRET_LENGTH} characters")
        origins = {o.strip() for o in (get("CORS_ORIGINS", "") or "").split(",") if o.strip()}
        return cls(
            jwt_secret=secret.encode("utf-8"),
            allow_registration=(get("ALLOW_REGISTRATION", "false") or "").lower() == "true",
            cors_origins=frozenset(origins),
        )
