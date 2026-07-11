from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from edge_agent.config import EdgeAgentConfig, load_config
from edge_agent.db.local_db import LocalDB
from edge_agent.core.migrate import run_migration
from edge_agent.core.plugin_loader import PluginRegistry
from edge_agent.core.event_bus import EventBus

if TYPE_CHECKING:
    from edge_agent.core.sync_engine import SyncEngine
    from edge_agent.core.worker import Worker
    from edge_agent.core.watcher import FolderWatcher

logger = logging.getLogger("edge_agent.api")

_config: EdgeAgentConfig | None = None
_db: LocalDB | None = None
_worker: Worker | None = None
_watcher: FolderWatcher | None = None
_sync_engine: SyncEngine | None = None
_metrics: Any | None = None
_log_handler: Any | None = None
_registry: PluginRegistry | None = None
_event_bus: EventBus | None = None
_start_time: float = 0.0


def get_plugin_registry() -> PluginRegistry:
    global _registry
    assert _registry is not None, "Plugin registry not initialized"
    return _registry


def get_config() -> EdgeAgentConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_db() -> LocalDB:
    global _db
    assert _db is not None, "DB not initialized (lifespan not started)"
    return _db


def get_worker() -> Worker:
    global _worker
    assert _worker is not None, "Worker not initialized"
    return _worker


def get_watcher() -> FolderWatcher:
    global _watcher
    assert _watcher is not None, "Watcher not initialized"
    return _watcher


def get_sync_engine() -> SyncEngine:
    global _sync_engine
    assert _sync_engine is not None, "SyncEngine not initialized"
    return _sync_engine


def get_metrics() -> Any:
    global _metrics
    assert _metrics is not None, "Metrics not initialized"
    return _metrics


def get_event_bus() -> EventBus:
    global _event_bus
    assert _event_bus is not None, "EventBus not initialized"
    return _event_bus


def get_log_handler() -> Any:
    global _log_handler
    return _log_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _db, _worker, _watcher, _sync_engine, _registry, _event_bus, _metrics, _start_time
    _config = load_config()
    Path(_config.data_dir).mkdir(parents=True, exist_ok=True)
    _db = LocalDB(_config.db_path)
    run_migration(_config.db_path)
    _start_time = time.time()

    _registry = PluginRegistry()
    _registry.discover_plugins(_config.plugin_dir)
    if _registry.list_capabilities():
        logger.info("Plugins loaded: %s", _registry.list_capabilities())

    from edge_agent.core.sync_engine import SyncEngine
    from edge_agent.core.worker import Worker
    from edge_agent.core.watcher import FolderWatcher
    from edge_agent.core.metrics import Metrics
    from edge_agent.core.log_capture import RingBufferLogHandler

    _metrics = Metrics()
    _event_bus = EventBus()

    global _log_handler
    _log_handler = RingBufferLogHandler(1000)
    _log_handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(_log_handler)

    _sync_engine = SyncEngine(_db, _config, metrics=_metrics)
    _worker = Worker(_db, _sync_engine, metrics=_metrics, event_bus=_event_bus)
    _worker.start()

    if _config.watcher.enabled:
        _watcher = FolderWatcher(_db, debounce_seconds=_config.watcher.debounce_seconds, event_bus=_event_bus)
        _watcher.start(_config.folders)
        logger.info("Watcher started for %d folders", len(_config.folders))

    logger.info("Edge Agent started (DB: %s)", _config.db_path)

    yield

    if _watcher:
        _watcher.stop()
    if _worker:
        _worker.stop()
    _db.close()
    logger.info("Edge Agent shutting down")


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
