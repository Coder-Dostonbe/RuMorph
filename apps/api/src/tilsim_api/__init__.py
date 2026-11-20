"""Tilsim API. Framework-free: `app.handle` takes a plain Request and returns a
plain Response, so the same code runs in the Cloudflare Python Worker
(src/entry.py) and in tests against a real PostgreSQL."""

__version__ = "0.1.0"
SERVICE = "tilsim-api"
