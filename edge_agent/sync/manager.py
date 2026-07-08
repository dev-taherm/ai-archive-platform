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

    def update_api_key(self, api_key: str) -> None:
        """Replace the current HTTP client with one using the new API key."""
        self._client.close()
        self._client = self._make_client(api_key=api_key)

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

        Uses the auto-register endpoint which reuses existing agents on the same
        hostname (same user) or creates new ones (different user/device).

        Registration requires JWT auth (the user's login token).
        """
        if not jwt_token:
            raise ValueError("jwt_token is required for registration")
        client = self._make_client(jwt_token=jwt_token)
        try:
            payload = {
                "hostname": platform.node(),
                "platform": platform.system().lower(),
                "agent_version": "0.1.0",
                "name": name or self._config.agent_name,
            }
            logger.debug("auto-register payload: %s", payload)
            resp = client.post("/api/v1/agents/auto-register", json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                "Registered agent: %s (is_new=%s)",
                data.get("agent_id"), data.get("is_new"),
            )
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
                "summary": f.get("summary", ""),
                "entities": self._get_entities_for_file(f["id"]),
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

    def _get_entities_for_file(self, file_id: str) -> list[dict[str, Any]]:
        """Get extracted entities for a file from the local DB."""
        try:
            entities = self._db.get_entities(file_id)
            return [
                {
                    "entity_type": e.get("entity_type", ""),
                    "name": e.get("name", ""),
                    "context": e.get("context", ""),
                    "confidence": e.get("confidence"),
                    "source": e.get("source", "agent"),
                }
                for e in entities
            ]
        except Exception:
            return []

    def report_command_result(
        self,
        command_id: str,
        *,
        status: str = "completed",
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Report the result of a command execution back to the platform."""
        payload: dict[str, Any] = {
            "command_id": command_id,
            "status": status,
        }
        if result is not None:
            payload["result"] = result

        resp = self._client.post(
            f"/api/v1/agents/{self._config.agent_id}/commands",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


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
