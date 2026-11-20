"""Cloudflare Python Worker entry point: adapts the Workers request and
environment to tilsim_api.app.handle. All logic lives in tilsim_api."""

import asyncpg
from workers import Response as WorkerResponse
from workers import WorkerEntrypoint

from tilsim_api.app import Context, handle
from tilsim_api.config import ConfigError, Settings
from tilsim_api.http import MAX_BODY_BYTES, Request


def _headers(request) -> dict[str, str]:
    return {str(name).lower(): str(value) for name, value in request.headers.items()}


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        headers = _headers(request)
        body = b""
        if request.method in ("POST", "PUT"):
            declared = int(headers.get("content-length") or 0)
            if declared <= MAX_BODY_BYTES:
                body = (await request.text()).encode("utf-8")
            else:
                body = b"x" * (MAX_BODY_BYTES + 1)  # rejected as too large by Request.json()

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
            Context(settings=settings, connect=connect, config_error=config_error),
        )
        return WorkerResponse(response.body, status=response.status, headers=response.headers)
