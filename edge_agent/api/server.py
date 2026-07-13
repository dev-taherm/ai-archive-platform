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


class AppState:
    """Encapsulates all global application state."""
    def __init__(self) -> None:
        self.config: EdgeAgentConfig | None = None
        self.db: LocalDB | None = None
        self.worker: Worker | None = None
        self.watcher: FolderWatcher | None = None
        self.sync_engine: SyncEngine | None = None
        self.metrics: Any | None = None
        self.log_handler: Any | None = None
        self.registry: PluginRegistry | None = None
        self.event_bus: EventBus | None = None
        self.ws_client: Any | None = None
        self.start_time: float = 0.0


_app_state = AppState()


def get_plugin_registry() -> PluginRegistry:
    assert _app_state.registry is not None, "Plugin registry not initialized"
    return _app_state.registry


def get_config() -> EdgeAgentConfig:
    if _app_state.config is None:
        _app_state.config = load_config()
    return _app_state.config


def get_db() -> LocalDB:
    assert _app_state.db is not None, "DB not initialized (lifespan not started)"
    return _app_state.db


def get_worker() -> Worker:
    assert _app_state.worker is not None, "Worker not initialized"
    return _app_state.worker


def get_watcher() -> FolderWatcher:
    assert _app_state.watcher is not None, "Watcher not initialized"
    return _app_state.watcher


def get_sync_engine() -> SyncEngine:
    assert _app_state.sync_engine is not None, "SyncEngine not initialized"
    return _app_state.sync_engine


def get_metrics() -> Any:
    assert _app_state.metrics is not None, "Metrics not initialized"
    return _app_state.metrics


def get_event_bus() -> EventBus:
    assert _app_state.event_bus is not None, "EventBus not initialized"
    return _app_state.event_bus


def get_log_handler() -> Any:
    return _app_state.log_handler


def get_ws_client() -> Any:
    return _app_state.ws_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    _app_state.config = load_config()
    Path(_app_state.config.data_dir).mkdir(parents=True, exist_ok=True)
    _app_state.db = LocalDB(_app_state.config.db_path)
    run_migration(_app_state.config.db_path)
    _app_state.start_time = time.time()

    # Seed frontend_url into SQLite so the desktop app can read it before registration
    if _app_state.config.server.web_url:
        existing_cfg = _app_state.db.get_config()
        if not existing_cfg.get("frontend_url"):
            _app_state.db.set_config("frontend_url", _app_state.config.server.web_url)

    _app_state.registry = PluginRegistry()
    _app_state.registry.discover_plugins(_app_state.config.plugin_dir)
    if _app_state.registry.list_capabilities():
        logger.info("Plugins loaded: %s", _app_state.registry.list_capabilities())

    from edge_agent.core.sync_engine import SyncEngine
    from edge_agent.core.worker import Worker
    from edge_agent.core.watcher import FolderWatcher
    from edge_agent.core.metrics import Metrics
    from edge_agent.core.log_capture import RingBufferLogHandler

    _app_state.metrics = Metrics()
    _app_state.event_bus = EventBus()

    _app_state.log_handler = RingBufferLogHandler(1000)
    _app_state.log_handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(_app_state.log_handler)

    _app_state.sync_engine = SyncEngine(_app_state.db, _app_state.config, metrics=_app_state.metrics)
    _app_state.worker = Worker(_app_state.db, _app_state.sync_engine, metrics=_app_state.metrics, event_bus=_app_state.event_bus)
    _app_state.worker.start()

    # Start SaaS WebSocket client (replaces HTTP heartbeat polling)
    from edge_agent.core.ws_client import SaaSWebSocketClient
    _app_state.ws_client = SaaSWebSocketClient(
        db=_app_state.db,
        sync_engine=_app_state.sync_engine,
        event_bus=_app_state.event_bus,
        command_handler=_app_state.worker.handle_command,
    )
    _app_state.ws_client._start_time = _app_state.start_time
    _app_state.ws_client.start()

    if _app_state.config.watcher.enabled:
        _app_state.watcher = FolderWatcher(_app_state.db, debounce_seconds=_app_state.config.watcher.debounce_seconds, event_bus=_app_state.event_bus)
        _app_state.watcher.start(_app_state.config.folders)
        logger.info("Watcher started for %d folders", len(_app_state.config.folders))

    logger.info("Edge Agent started (DB: %s)", _app_state.config.db_path)

    yield

    if _app_state.watcher:
        _app_state.watcher.stop()
    if _app_state.ws_client:
        _app_state.ws_client.stop()
    if _app_state.worker:
        _app_state.worker.stop()
    _app_state.db.close()
    logger.info("Edge Agent shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Basirah Edge Agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    allowed_origins = _app_state.config.server.cors_origins if _app_state.config and hasattr(_app_state.config.server, 'cors_origins') else ["http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .routes import router
    app.include_router(router, prefix="/api")

    return app
