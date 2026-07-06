"""Local SQLite database — stores file records and sync state.

No Django dependency — uses stdlib sqlite3.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    local_path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL DEFAULT '',
    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT NOT NULL DEFAULT '',
    modified_at REAL NOT NULL DEFAULT 0,
    created_at REAL NOT NULL DEFAULT 0,
    first_seen_at TEXT NOT NULL,
    extracted_text TEXT NOT NULL DEFAULT '',
    markdown TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    classification TEXT NOT NULL DEFAULT '{}',
    summary TEXT NOT NULL DEFAULT '',
    processing_status TEXT NOT NULL DEFAULT 'pending',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    synced INTEGER NOT NULL DEFAULT 0,
    synced_at TEXT,
    last_error TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_files_hash ON files(content_hash);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(processing_status);
CREATE INDEX IF NOT EXISTS idx_files_synced ON files(synced);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(local_path);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_batch_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    response TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX IF NOT EXISTS idx_sync_log_batch ON sync_log(sync_batch_id);
"""


class LocalDB:
    """SQLite database for local file tracking and sync state."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def upsert_file(self, file_info: dict[str, Any]) -> str:
        """Insert or update a file record. Returns the file ID."""
        file_id = str(uuid.uuid5(uuid.NAMESPACE_URL, file_info["content_hash"]))
        now = self._now()
        existing = self._conn.execute("SELECT id FROM files WHERE content_hash = ?", (file_info["content_hash"],)).fetchone()
        if existing:
            file_id = existing["id"]
            self._conn.execute("""
                UPDATE files SET local_path=?, filename=?, extension=?, mime_type=?,
                    size_bytes=?, modified_at=?, updated_at=?
                WHERE id=?
            """, (
                file_info["path"], file_info["filename"], file_info.get("extension", ""),
                file_info.get("mime_type", ""), file_info.get("size_bytes", 0),
                file_info.get("modified_at", 0), now, file_id,
            ))
        else:
            self._conn.execute("""
                INSERT INTO files (id, local_path, filename, extension, mime_type,
                    size_bytes, content_hash, modified_at, created_at, first_seen_at,
                    updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, file_info["path"], file_info["filename"],
                file_info.get("extension", ""), file_info.get("mime_type", ""),
                file_info.get("size_bytes", 0), file_info.get("content_hash", ""),
                file_info.get("modified_at", 0), file_info.get("created_at", 0),
                now, now,
            ))
        self._conn.commit()
        return file_id

    def update_file(self, file_id: str, **kwargs: Any) -> None:
        """Update specific fields on a file record."""
        allowed = {
            "extracted_text", "markdown", "metadata", "classification",
            "summary", "processing_status", "chunk_count", "synced",
            "synced_at", "last_error",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        updates["updated_at"] = self._now()
        if "metadata" in updates and isinstance(updates["metadata"], dict):
            updates["metadata"] = json.dumps(updates["metadata"])
        if "classification" in updates and isinstance(updates["classification"], dict):
            updates["classification"] = json.dumps(updates["classification"])
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [file_id]
        self._conn.execute(f"UPDATE files SET {set_clause} WHERE id=?", values)
        self._conn.commit()

    def get_file(self, file_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
        return dict(row) if row else None

    def get_file_by_hash(self, content_hash: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM files WHERE content_hash=?", (content_hash,)).fetchone()
        return dict(row) if row else None

    def get_file_by_path(self, local_path: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM files WHERE local_path=?", (local_path,)).fetchone()
        return dict(row) if row else None

    def list_files(self, status: str | None = None, synced: int | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        query = "SELECT * FROM files WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND processing_status=?"
            params.append(status)
        if synced is not None:
            query += " AND synced=?"
            params.append(synced)
        query += " ORDER BY first_seen_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self._conn.execute(query, params).fetchall()]

    def get_pending_sync(self, batch_size: int = 50) -> list[dict[str, Any]]:
        return self.list_files(synced=0, limit=batch_size)

    def mark_synced(self, file_ids: list[str]) -> None:
        now = self._now()
        self._conn.executemany(
            "UPDATE files SET synced=1, synced_at=? WHERE id=?",
            [(now, fid) for fid in file_ids],
        )
        self._conn.commit()

    def get_stats(self) -> dict[str, int]:
        total = self._conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        synced = self._conn.execute("SELECT COUNT(*) FROM files WHERE synced=1").fetchone()[0]
        pending = self._conn.execute("SELECT COUNT(*) FROM files WHERE processing_status='pending'").fetchone()[0]
        processing = self._conn.execute("SELECT COUNT(*) FROM files WHERE processing_status='processing'").fetchone()[0]
        completed = self._conn.execute("SELECT COUNT(*) FROM files WHERE processing_status='completed'").fetchone()[0]
        failed = self._conn.execute("SELECT COUNT(*) FROM files WHERE processing_status='failed'").fetchone()[0]
        return {"total": total, "synced": synced, "pending": pending, "processing": processing, "completed": completed, "failed": failed}

    def delete_file(self, file_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM files WHERE id=?", (file_id,))
        self._conn.commit()
        return cursor.rowcount > 0
