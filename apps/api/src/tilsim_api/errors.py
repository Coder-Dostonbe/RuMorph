"""API errors. Every error the client can see has a stable code (the app's
src/ui/errors.ts maps codes to messages in the interface language)."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers or {}


def bad_request(code: str, message: str) -> ApiError:
    return ApiError(400, code, message)


def unauthorized(message: str = "authentication required") -> ApiError:
    return ApiError(401, "unauthorized", message, {"www-authenticate": "Bearer"})
