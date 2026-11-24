"""Plain request / response types and JSON helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .errors import ApiError

MAX_BODY_BYTES = 64 * 1024


@dataclass
class Request:
    method: str
    url: str
    headers: dict[str, str]          # lower-cased names
    body: bytes = b""
    ip: str | None = None

    @property
    def path(self) -> str:
        return urlsplit(self.url).path or "/"

    def header(self, name: str) -> str | None:
        return self.headers.get(name.lower())

    def query(self, name: str) -> str | None:
        values = parse_qs(urlsplit(self.url).query).get(name)
        return values[0] if values else None

    def json(self, max_bytes: int = MAX_BODY_BYTES) -> dict[str, Any]:
        if len(self.body) > max_bytes:
            raise ApiError(413, "payload_too_large", "request body is too large")
        content_type = (self.header("content-type") or "").split(";")[0].strip().lower()
        if content_type != "application/json":
            raise ApiError(415, "unsupported_media_type", "send the body as application/json")
        try:
            data = json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, "invalid_json", "the body is not valid JSON") from None
        if not isinstance(data, dict):
            raise ApiError(400, "invalid_json", "the body must be a JSON object")
        return data


@dataclass
class Response:
    status: int
    body: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        return json.loads(self.body) if self.body else None


def json_response(status: int, data: Any, headers: dict[str, str] | None = None) -> Response:
    return Response(
        status=status,
        body=json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str),
        headers={"content-type": "application/json; charset=utf-8", "cache-control": "no-store", **(headers or {})},
    )


def error_response(error: ApiError) -> Response:
    return json_response(error.status, {"error": {"code": error.code, "message": error.message}}, error.headers)
