"""Tilsim domain logic.

Runs unchanged in three places: inside the app's webview through Pyodide
(Windows and Android), on the server in a Cloudflare Python Worker, and under
plain CPython for tests. It therefore imports only the standard library, never
touches the network and never stores data itself: callers pass data in and
get results back. `tests/test_architecture.py` enforces the import rule.
"""

__version__ = "0.1.0"

# Bumped whenever the shape of a bridge request or reply changes, so the app
# can refuse a core it does not understand.
PROTOCOL_VERSION = 1
