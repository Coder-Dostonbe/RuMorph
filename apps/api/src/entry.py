"""Cloudflare Python Worker entry point: adapts the Workers request and
environment to tilsim_api.app.handle. All logic lives in tilsim_api."""

import asyncpg
from workers import Response as WorkerResponse
from workers import WorkerEntrypoint
from workers import fetch as worker_fetch

from tilsim_api.app import SYNC_BODY_BYTES, Context, handle
from tilsim_api.config import ConfigError, Settings
from tilsim_api.http import Request
from tilsim_api.webcrypto import derive


# Wikimedia asks every client for a descriptive User-Agent.
USER_AGENT = "ZabonAPI/1.0 (https://github.com/Coder-Dostonbe/RuMorph)"


async def fetch_bytes(url: str) -> tuple[int, str, bytes]:
    response = await worker_fetch(url, headers={"user-agent": USER_AGENT})
    if response.status != 200:
        return response.status, "", b""
    return response.status, response.headers.get("content-type", ""), await response.bytes()


def _headers(request) -> dict[str, str]:
    return {str(name).lower(): str(value) for name, value in request.headers.items()}


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        headers = _headers(request)
        body = b""
        if request.method in ("POST", "PUT"):
            # The largest body any route takes; each route checks its own limit in Request.json().
            declared = int(headers.get("content-length") or 0)
            if declared <= SYNC_BODY_BYTES:
                body = (await request.text()).encode("utf-8")
            else:
                body = b"x" * (SYNC_BODY_BYTES + 1)  # rejected as too large by Request.json()

        try:
            settings, config_error = Settings.from_env(self.env), None
        except ConfigError as exc:
            settings, config_error = None, str(exc)

        env = self.env

        async def connect():
            return await asyncpg.connect(env.HYPERDRIVE.connectionString)

        response = await handle(
            Request(method=request.method, url=str(request.url), headers=headers, body=body,
                    ip=headers.get("cf-connecting-ip")),
            Context(settings=settings, connect=connect, config_error=config_error, derive=derive,
                    fetch_bytes=fetch_bytes),
        )
        return WorkerResponse(response.body, status=response.status, headers=response.headers)
