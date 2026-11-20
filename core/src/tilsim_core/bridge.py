"""JSON bridge between the TypeScript app and tilsim_core.

The app sends one request at a time as a JSON string and gets one JSON string
back, the same way ArabMorph's desktop shell talks to its sidecar. Under
Pyodide the request arrives from a Web Worker; on the server the API calls
`dispatch` directly.

Request:  {"id": <str|int>, "op": <str>, "args": {...}}
Reply:    {"id": ..., "ok": true,  "result": ...}
       or {"id": ..., "ok": false, "error": {"code": <str>, "message": <str>}}

Every request is validated here rather than trusted. An unexpected exception
never leaks a traceback to the caller: the reply says "internal" and the
traceback goes to stderr, where the host can log it.
"""

from __future__ import annotations

import json
import platform
import sys
import traceback
from collections.abc import Callable
from typing import Any

from . import PROTOCOL_VERSION, __version__

MAX_REQUEST_BYTES = 1_000_000


class BridgeError(Exception):
    """An error the caller can act on; its code and message are returned as they are."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _op_version(args: dict[str, Any]) -> dict[str, Any]:
    _expect_no_args(args)
    return {
        "core": __version__,
        "protocol": PROTOCOL_VERSION,
        "python": platform.python_version(),
        # "emscripten" under Pyodide (app), "linux" / "win32" / … under CPython.
        "platform": sys.platform,
    }


def _op_echo(args: dict[str, Any]) -> dict[str, Any]:
    """Round-trip check used by the app's start-up self test."""
    text = args.get("text")
    if not isinstance(text, str):
        raise BridgeError("invalid_args", "'text' must be a string")
    if len(text) > 1000:
        raise BridgeError("invalid_args", "'text' is longer than 1000 characters")
    return {"text": text}


def _expect_no_args(args: dict[str, Any]) -> None:
    if args:
        raise BridgeError("invalid_args", f"unexpected arguments: {', '.join(sorted(args))}")


OPS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "version": _op_version,
    "echo": _op_echo,
}


def dispatch(op: str, args: dict[str, Any] | None = None) -> Any:
    """Run one operation and return its result, raising BridgeError for caller errors."""
    handler = OPS.get(op)
    if handler is None:
        raise BridgeError("unknown_op", f"unknown operation: {op!r}")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise BridgeError("invalid_args", "'args' must be an object")
    return handler(args)


def handle(raw: str) -> str:
    """Handle one JSON request string and return the JSON reply string."""
    request_id: Any = None
    try:
        if not isinstance(raw, str):
            raise BridgeError("invalid_request", "the request must be a JSON string")
        if len(raw.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise BridgeError("invalid_request", "the request is too large")
        try:
            request = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BridgeError("invalid_request", f"the request is not valid JSON: {exc.msg}") from None
        if not isinstance(request, dict):
            raise BridgeError("invalid_request", "the request must be a JSON object")
        request_id = request.get("id")
        if not isinstance(request_id, (str, int)) or isinstance(request_id, bool):
            request_id = None
            raise BridgeError("invalid_request", "'id' must be a string or an integer")
        op = request.get("op")
        if not isinstance(op, str):
            raise BridgeError("invalid_request", "'op' must be a string")
        result = dispatch(op, request.get("args"))
        reply: dict[str, Any] = {"id": request_id, "ok": True, "result": result}
    except BridgeError as exc:
        reply = {"id": request_id, "ok": False, "error": {"code": exc.code, "message": exc.message}}
    except Exception:  # noqa: BLE001 — the boundary must never raise
        traceback.print_exc(file=sys.stderr)
        reply = {"id": request_id, "ok": False,
                 "error": {"code": "internal", "message": "internal error in tilsim_core"}}
    return json.dumps(reply, ensure_ascii=False)
