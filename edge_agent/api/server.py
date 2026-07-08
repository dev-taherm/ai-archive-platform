"""FastAPI local server for the Edge Agent.

Runs on localhost:8420. Provides REST endpoints for the Tauri desktop app
to control the Python edge agent (scan, process, sync, watch, etc.).
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from edge_agent.config import EdgeAgentConfig, load_config
from edge_agent.db.local_db import LocalDB

logger = logging.getLogger("edge_agent.api")

_config: EdgeAgentConfig | None = None
_db: LocalDB | None = None
_start_time: float = 0.0
_watcher_active: bool = False


def get_config() -> EdgeAgentConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_db() -> LocalDB:
    global _db
    if _db is None:
        _db = LocalDB(get_config().db_path)
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _db, _start_time
    _config = load_config()
    Path(_config.data_dir).mkdir(parents=True, exist_ok=True)
    _db = LocalDB(_config.db_path)
    _start_time = time.time()
    logger.info("Edge Agent API started on localhost:8420")
    yield
    logger.info("Edge Agent API shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Basirah Edge Agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .routes import router
    app.include_router(router, prefix="/api")

    return app
