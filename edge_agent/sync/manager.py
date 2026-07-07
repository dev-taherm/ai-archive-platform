"""Sync manager — pushes local file metadata to the SaaS platform.

Uses httpx for HTTP requests with retry logic.
"""

from __future__ import annotations

import logging
import platform
import time
import uuid
from typing import Any

import httpx

from edge_agent.config import EdgeAgentConfig
from edge_agent.db.local_db import LocalDB

logger = logging.getLogger(__name__)


class SyncManager:
    """Syncs local file records to the remote SaaS platform."""

    def __init__(self, config: EdgeAgentConfig, db: LocalDB) -> None:
        self._config = config
        self._db = db
        self._client = self._make_client(api_key=config.server.api_key)

    def _make_client(self, *, api_key: str | None = None, jwt_token: str | None = None) -> httpx.Client:
        """Create an httpx client with the right auth header."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        elif jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"
        return httpx.Client(base_url=self._config.server.url, headers=headers, timeout=60.0)

    def register(self, name: str | None = None, jwt_token: str | None = None) -> dict[str, Any]:
        """Register this agent with the platform. Returns agent info + API key.

        Registration requires JWT auth (the user's login token).
        """
        if not jwt_token:
            raise ValueError("jwt_token is required for registration")
        agent_id = self._config.agent_id or str(uuid.uuid4())
        client = self._make_client(jwt_token=jwt_token)
        try:
            resp = client.post("/api/v1/agents", json={
                "agent_id": agent_id,
                "name": name or self._config.agent_name,
                "platform": platform.system().lower(),
                "hostname": platform.node(),
                "agent_version": "0.1.0",
                "capabilities": ["scan", "ocr", "parse", "embed"],
                "sync_interval_minutes": self._config.sync.interval_minutes,
                "push_original_files": self._config.sync.push_original_files,
            })
            resp.raise_for_status()
            data = resp.json()
            logger.info("Registered agent: %s", data.get("id"))
            return data
        finally:
            client.close()

    def heartbeat(self) -> dict[str, Any]:
        """Send heartbeat. Returns pending commands + config."""
        stats = self._db.get_stats()
        resp = self._client.post(f"/api/v1/agents/{self._config.agent_id}/heartbeat", json={
            "status": "online",
            "files_count": stats["total"],
            "folders_monitored": self._config.folders,
        })
        resp.raise_for_status()
        return resp.json()

    def sync_files(self, batch_size: int | None = None) -> dict[str, Any]:
        """Push pre-processed file data to the platform. No chunks or embeddings."""
        batch = self._db.get_pending_sync(batch_size=batch_size or self._config.sync.batch_size)
        if not batch:
            return {"synced": 0, "message": "Nothing to sync"}

        files_payload = []
        for f in batch:
            entry = {
                "local_path": f["local_path"],
                "file_hash": f["content_hash"],
                "file_size": f["size_bytes"],
                "mime_type": f.get("mime_type", "application/octet-stream"),
                "modified_at": f["modified_at"],
                "metadata": _safe_json(f.get("metadata", "{}")),
                "extracted_text": f.get("extracted_text", ""),
                "markdown": f.get("markdown", ""),
                "content_blocks": f.get("content_blocks", []),
                "tables": f.get("tables", []),
                "images": f.get("images", []),
                "language": f.get("language", "unknown"),
                "word_count": f.get("word_count", 0),
                "char_count": f.get("char_count", 0),
                "page_count": f.get("page_count", 0),
                "ocr_used": f.get("ocr_used", False),
                "agent_version": f.get("agent_version", ""),
                "processing_version": f.get("processing_version", ""),
                "parser_version": f.get("parser_version", ""),
                "ocr_engine": f.get("ocr_engine", ""),
            }
            files_payload.append(entry)

        resp = self._client.post(f"/api/v1/agents/{self._config.agent_id}/sync", json={
            "files": files_payload,
        })
        resp.raise_for_status()
        result = resp.json()

        file_ids = [f["id"] for f in batch]
        self._db.mark_synced(file_ids)
        logger.info("Synced %d files", len(file_ids))
        return result

    def sync_with_retry(self) -> dict[str, Any]:
        """Sync with retry logic."""
        last_error = None
        for attempt in range(self._config.sync.retry_attempts):
            try:
                return self.sync_files()
            except Exception as e:
                last_error = e
                logger.warning("Sync attempt %d failed: %s", attempt + 1, e)
                if attempt < self._config.sync.retry_attempts - 1:
                    time.sleep(self._config.sync.retry_delay_seconds)
        raise RuntimeError(f"Sync failed after {self._config.sync.retry_attempts} attempts: {last_error}")

    def close(self) -> None:
        self._client.close()


def _safe_json(value: str | dict | None) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        import json
        return json.loads(value)
    except Exception:
        return {}
