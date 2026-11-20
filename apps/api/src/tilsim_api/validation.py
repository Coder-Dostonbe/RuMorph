"""Input validation for request bodies. Each function returns a clean value or
raises ApiError(400) with a code the app understands."""

from __future__ import annotations

import re
import uuid
from typing import Any

from . import passwords
from .errors import ApiError, bad_request

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
PLATFORMS = ("windows", "android", "browser")


def email(value: Any) -> str:
    if not isinstance(value, str):
        raise bad_request("invalid_email", "email must be a string")
    cleaned = value.strip().lower()
    if len(cleaned) > 254 or not _EMAIL.match(cleaned):
        raise bad_request("invalid_email", "email address is not valid")
    return cleaned


def new_password(value: Any) -> str:
    if not isinstance(value, str):
        raise bad_request("weak_password", "password must be a string")
    if len(value) < passwords.MIN_LENGTH:
        raise bad_request("weak_password", f"password must have at least {passwords.MIN_LENGTH} characters")
    if len(value) > passwords.MAX_LENGTH:
        raise bad_request("invalid_password", f"password must have at most {passwords.MAX_LENGTH} characters")
    return value


def given_password(value: Any) -> str:
    # At sign-in, a wrong-length password is simply wrong; it must not reveal the rules.
    if not isinstance(value, str) or not value or len(value) > passwords.MAX_LENGTH:
        raise ApiError(401, "invalid_credentials", "wrong email or password")
    return value


def optional_text(value: Any, field: str, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise bad_request("invalid_field", f"{field} must be a string")
    cleaned = " ".join(value.split())
    if len(cleaned) > max_length:
        raise bad_request("invalid_field", f"{field} must have at most {max_length} characters")
    return cleaned or None


def device(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise bad_request("invalid_device", "device must be an object")
    try:
        client_id = str(uuid.UUID(str(value.get("id"))))
    except ValueError:
        raise bad_request("invalid_device", "device.id must be a UUID") from None
    platform = value.get("platform")
    if platform not in PLATFORMS:
        raise bad_request("invalid_device", f"device.platform must be one of {', '.join(PLATFORMS)}")
    name = optional_text(value.get("name"), "device.name", 80) or platform.capitalize()
    return {"client_id": client_id, "platform": platform, "name": name}


def refresh_token(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("rt_") or len(value) > 200:
        raise ApiError(401, "unauthorized", "invalid refresh token")
    return value
