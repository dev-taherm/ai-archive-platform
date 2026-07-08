"""FastAPI local HTTP server for the Edge Agent.

Provides a REST API on localhost:8420 for the Tauri desktop app
to communicate with the Python edge agent.
"""

from __future__ import annotations

from .server import create_app

__all__ = ["create_app"]
