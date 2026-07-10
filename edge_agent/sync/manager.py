"""Sync manager — builds local sync payloads for the desktop app to relay.

No direct SaaS communication. The desktop app (Tauri Rust) handles all HTTP
calls to the backend. This module just builds the payload and manages local
sync state.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from edge_agent.config import EdgeAgentConfig
from edge_agent.db.local_db import LocalDB

logger = logging.getLogger(__name__)


class SyncManager:
    """Builds sync payloads from local file records."""

    def __init__(self, config: EdgeAgentConfig, db: LocalDB) -> None:
        self._config = config
        self._db = db

    def build_sync_payload(self, batch_size: int = 50) -> dict[str, Any]:
        """Build sync payload from pending files. Returns None if nothing to sync."""
        batch = self._db.get_pending_sync(batch_size=batch_size)
        if not batch:
            return {"files": [], "count": 0}

        files_payload = []
        for f in batch:
            text = _strip_nulls(f.get("extracted_text", ""))
            md = _strip_nulls(f.get("markdown", ""))
            summary = _strip_nulls(f.get("summary", ""))
            entry = {
                "local_path": f["local_path"],
                "file_hash": f["content_hash"],
                "file_size": f["size_bytes"],
                "mime_type": f.get("mime_type", "application/octet-stream"),
                "modified_at": f["modified_at"],
                "metadata": _safe_json(f.get("metadata", "{}")),
                "extracted_text": text,
                "markdown": md,
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
                "summary": summary,
                "entities": self._get_entities_for_file(f["id"]),
            }
            files_payload.append(entry)

        return {"files": files_payload, "count": len(files_payload)}

    def mark_synced(self, file_hashes: list[str]) -> int:
        """Mark files as synced by content_hash. Returns count marked."""
        if not file_hashes:
            return 0
        return self._db.mark_synced_by_hashes(file_hashes)

    def _get_entities_for_file(self, file_id: str) -> list[dict[str, Any]]:
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


def _safe_json(value: str | dict | None) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def _strip_nulls(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\0", "")
