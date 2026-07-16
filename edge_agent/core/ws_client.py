"""
SaaS WebSocket client for the edge agent.

Runs a persistent WebSocket connection to the SaaS backend, replacing
the HTTP heartbeat/polling pattern with a push-based channel.

Features:
- Persistent connection with automatic reconnect + exponential backoff
- Heartbeat → status update (replaces HTTP POST /heartbeat)
- File sync (replaces HTTP POST /sync)
- Server-push commands (replaces HTTP GET /commands)
- Thread-safe: runs in its own daemon thread with a dedicated asyncio loop

Usage:
    ws_client = SaaSWebSocketClient(db, sync_engine, event_bus)
    ws_client.start()
    # ... later ...
    ws_client.stop()
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from edge_agent.core.sync_engine import SyncEngine
    from edge_agent.db.local_db import LocalDB

logger = logging.getLogger(__name__)

# Backoff: start at 1s, double each attempt, cap at 30s
_BACKOFF_INITIAL = 1.0
_BACKOFF_MAX = 30.0
_BACKOFF_FACTOR = 2.0

# Heartbeat interval in seconds (sent to SaaS as JSON message, not HTTP)
_HEARTBEAT_INTERVAL = 60

# How often to check for pending syncs to send
_SYNC_INTERVAL = 300


class SaaSWebSocketClient:
    """Manages a persistent WebSocket connection to the SaaS backend."""

    def __init__(
        self,
        db: LocalDB,
        sync_engine: SyncEngine,
        event_bus: Any | None = None,
        command_handler: Any | None = None,
    ) -> None:
        self._db = db
        self._sync_engine = sync_engine
        self._event_bus = event_bus
        self._command_handler = command_handler

        self._running = False
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        # State
        self._connected = False
        self._ws: Any = None  # websockets.WebSocketClientProtocol
        self._last_heartbeat: float = 0.0
        self._last_sync: float = 0.0

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the WebSocket client in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="ws-client"
        )
        self._thread.start()
        logger.info("SaaS WebSocket client started")

    def stop(self) -> None:
        """Stop the WebSocket client."""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("SaaS WebSocket client stopped")

    # ── Main event loop (runs in background thread) ───────────────────────────

    def _run_loop(self) -> None:
        """Entry point for the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception:
            logger.exception("WebSocket client loop crashed")
        finally:
            self._loop.close()

    async def _connect_loop(self) -> None:
        """Reconnection loop — restarts the connection on failures."""
        backoff = _BACKOFF_INITIAL

        while self._running:
            try:
                await self._run_connection()
            except Exception as e:
                if not self._running:
                    break
                logger.warning(
                    "WebSocket connection lost: %s — reconnecting in %.1fs",
                    e, backoff,
                )
                self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(backoff * _BACKOFF_FACTOR, _BACKOFF_MAX)
            else:
                # Clean disconnect — reset backoff
                backoff = _BACKOFF_INITIAL

    async def _run_connection(self) -> None:
        """Single connection lifecycle — connect, run, then return to reconnect."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets library not installed — WS client disabled")
            await asyncio.sleep(60)
            return

        creds = self._sync_engine.get_credentials()
        if not all(creds.values()):
            logger.debug("Not registered — skipping WS connection")
            await asyncio.sleep(10)
            return

        server_url = creds["server_url"].rstrip("/")
        api_key = creds["api_key"]

        # Convert HTTP(S) → WS(S)
        ws_url = server_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws/agent/"
        if api_key:
            ws_url = f"{ws_url}?api_key={api_key}"

        logger.info("Connecting to SaaS WebSocket: %s", ws_url)

        async with websockets.connect(
            ws_url,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            self._ws = ws
            self._connected = True
            logger.info("Connected to SaaS WebSocket")

            # Send initial heartbeat
            await self._send_heartbeat()

            # Run the receive loop (which also does periodic tasks)
            await self._receive_loop(ws)

    async def _receive_loop(self, ws: Any) -> None:
        """Main receive loop — handles incoming messages and periodic tasks."""
        import websockets

        last_periodic = time.time()

        while self._running:
            try:
                # Use asyncio.wait_for to allow periodic tasks between messages
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                await self._handle_message(msg)
            except asyncio.TimeoutError:
                # No message received — run periodic tasks
                pass
            except websockets.ConnectionClosed as e:
                logger.warning("WebSocket closed: %s", e)
                self._connected = False
                raise
            except Exception as e:
                logger.warning("WebSocket receive error: %s", e)
                self._connected = False
                raise

            # Periodic tasks (every cycle while idle)
            now = time.time()
            if now - last_periodic >= 1.0:
                last_periodic = now
                await self._periodic_tasks()

        self._connected = False

    # ── Message handling ──────────────────────────────────────────────────────

    async def _handle_message(self, raw: str) -> None:
        """Process a message from the SaaS backend."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from SaaS: %s", raw[:200])
            return

        msg_type = data.get("type")

        if msg_type == "heartbeat_ack":
            logger.debug("Heartbeat acknowledged")
            pending_commands = data.get("pending_commands", [])
            if pending_commands:
                await self._handle_commands(pending_commands)

        elif msg_type == "sync_ack":
            logger.info(
                "Sync acknowledged: accepted=%s rejected=%s",
                data.get("accepted", 0),
                data.get("rejected", 0),
            )
            # Mark synced files in local DB
            document_ids = data.get("document_ids", [])
            if document_ids:
                logger.info("Sync produced %d documents", len(document_ids))

        elif msg_type == "command":
            await self._handle_command(data)

        elif msg_type == "config_update":
            config = data.get("config", {})
            if config:
                for key, value in config.items():
                    self._db.set_config(key, str(value))
                logger.info("Config updated via WebSocket: %s", list(config.keys()))

        elif msg_type == "error":
            logger.warning("SaaS error: %s", data.get("message"))

        elif msg_type == "ping":
            # Server keepalive — respond with pong
            await self._ws.send(json.dumps({"type": "pong"}))

    async def _handle_commands(self, commands: list[dict[str, Any]]) -> None:
        """Handle pending commands received via heartbeat_ack."""
        for cmd in commands:
            await self._handle_command(cmd)

    async def _handle_command(self, cmd: dict[str, Any]) -> None:
        """Dispatch a single command from the server."""
        command_type = cmd.get("command_type", "")
        command_id = cmd.get("command_id", "")
        payload = cmd.get("payload", {})
        logger.info("Received command: %s (id=%s)", command_type, command_id)

        result: dict[str, Any] = {"status": "completed"}

        try:
            if command_type == "sync":
                self._sync_engine.sync_files()
            elif command_type == "scan":
                file_id = payload.get("file_id")
                if file_id:
                    self._queue_scan(file_id)
                else:
                    result = {"status": "failed", "error": "No file_id in payload"}
            elif command_type == "config_update":
                for key, value in payload.items():
                    self._db.set_config(key, str(value))
            elif command_type == "restart":
                # Will be handled by the command handler
                if self._command_handler:
                    self._command_handler("restart", payload)
            elif command_type == "shutdown":
                if self._command_handler:
                    self._command_handler("shutdown", payload)
            elif command_type in ("start_scan", "stop_scan"):
                if self._command_handler:
                    self._command_handler(command_type, payload)
            elif command_type == "delete":
                file_ids = payload.get("file_ids", [])
                results = []
                for fid in file_ids:
                    record = self._db.get_file_by_id(fid)
                    if record is None:
                        results.append({"file_id": fid, "status": "not_found"})
                        continue
                    src = Path(record["local_path"])
                    if not src.exists():
                        self._db.delete_file_record(fid)
                        results.append({"file_id": fid, "status": "ok", "note": "already missing"})
                        continue
                    from edge_agent.config import get_config
                    config = get_config()
                    trash_dir = Path(config.data_dir) / "trash"
                    trash_dir.mkdir(parents=True, exist_ok=True)
                    size = src.stat().st_size
                    trash_id = self._db.add_to_trash(str(src), fid, size)
                    trash_subdir = trash_dir / trash_id
                    trash_subdir.mkdir(parents=True, exist_ok=True)
                    dest = trash_subdir / src.name
                    os.rename(str(src), str(dest))
                    self._db.delete_file_record(fid)
                    results.append({"file_id": fid, "status": "ok", "trash_id": trash_id})
                result = {"status": "completed", "results": results}
            else:
                result = {"status": "failed", "error": f"Unknown command: {command_type}"}
        except Exception as e:
            logger.exception("Command %s failed", command_type)
            result = {"status": "failed", "error": str(e)}

        # Report result back to server
        await self._send_command_result(command_id, result)

    def _queue_scan(self, file_id: str) -> None:
        """Queue a scan job from a server command."""
        try:
            from edge_agent.api.server import get_worker
            worker = get_worker()
            worker.queue.create_job("scan_file", {"file_id": file_id})
            logger.info("Queued scan for file %s from server command", file_id)
        except Exception:
            logger.exception("Failed to queue scan for %s", file_id)

    # ── Periodic tasks ────────────────────────────────────────────────────────

    async def _periodic_tasks(self) -> None:
        """Run periodic tasks (heartbeat, sync) via the WS connection."""
        now = time.time()

        if now - self._last_heartbeat >= _HEARTBEAT_INTERVAL:
            await self._send_heartbeat()
            self._last_heartbeat = now

        if now - self._last_sync >= _SYNC_INTERVAL:
            await self._send_sync()
            self._last_sync = now

    async def _send_heartbeat(self) -> None:
        """Send heartbeat to SaaS via WebSocket."""
        if not self._connected or not self._ws:
            return

        try:
            hostname = os.uname().nodename if hasattr(os, "uname") else "unknown"
            completed = self._db.count_completed_files()
            pending_stats = self._db.get_job_stats()

            import platform
            msg = {
                "type": "heartbeat",
                "status": "online",
                "platform": sys.platform,
                "hostname": hostname,
                "agent_version": "0.1.0",
                "files_count": completed,
                "total_size_bytes": 0,
                "uptime_seconds": int(time.time() - self._start_time) if hasattr(self, "_start_time") else 0,
                "folders_monitored": self._get_monitored_folders(),
            }
            await self._ws.send(json.dumps(msg))
            logger.debug("Heartbeat sent via WebSocket")
        except Exception:
            logger.exception("Failed to send heartbeat via WebSocket")

    async def _send_sync(self) -> None:
        """Send file sync to SaaS via WebSocket."""
        if not self._connected or not self._ws:
            return

        try:
            pending = self._db.get_pending_sync(limit=50)
            if not pending:
                return

            from edge_agent.core.sync_engine import build_files_payload

            files_payload = build_files_payload(pending)

            if not files_payload:
                return

            msg = {"type": "sync_files", "files": files_payload, "stats": {}}
            await self._ws.send(json.dumps(msg))
            logger.info("Sync sent via WebSocket: %d files", len(files_payload))

            # Mark as synced locally (optimistic — server will confirm)
            synced_hashes = [e["file_hash"] for e in files_payload if e.get("file_hash")]
            if synced_hashes:
                self._db.mark_synced(synced_hashes)
        except Exception:
            logger.exception("Failed to send sync via WebSocket")

    async def _send_command_result(
        self, command_id: str, result: dict[str, Any]
    ) -> None:
        """Report command result back to the SaaS backend."""
        if not self._connected or not self._ws:
            return

        try:
            msg = {
                "type": "command_result",
                "command_id": command_id,
                "status": result.get("status", "completed"),
                "result": result,
            }
            await self._ws.send(json.dumps(msg))
        except Exception:
            logger.exception("Failed to send command result")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_monitored_folders(self) -> list[str]:
        """Get list of monitored folder paths from the DB."""
        try:
            cfg = self._db.get_config()
            folders = cfg.get("watched_folders", [])
            if isinstance(folders, str):
                import json as _json
                folders = _json.loads(folders) if folders else []
            return folders if isinstance(folders, list) else []
        except Exception:
            return []
