from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any


def _generate_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS folders (
    path TEXT PRIMARY KEY,
    label TEXT NOT NULL DEFAULT '',
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    local_path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL DEFAULT '',
    file_hash TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    mime_type TEXT NOT NULL DEFAULT '',
    modified_at TEXT NOT NULL DEFAULT '',
    processing_status TEXT NOT NULL DEFAULT 'pending',
    extracted_text TEXT NOT NULL DEFAULT '',
    markdown TEXT NOT NULL DEFAULT '',
    content_blocks TEXT NOT NULL DEFAULT '[]',
    tables TEXT NOT NULL DEFAULT '[]',
    images TEXT NOT NULL DEFAULT '[]',
    language TEXT NOT NULL DEFAULT 'unknown',
    word_count INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0,
    page_count INTEGER NOT NULL DEFAULT 0,
    synced INTEGER NOT NULL DEFAULT 0,
    first_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_files_status ON files(processing_status);
CREATE INDEX IF NOT EXISTS idx_files_synced ON files(synced);
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(local_path);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    payload TEXT NOT NULL DEFAULT '{}',
    progress REAL NOT NULL DEFAULT 0.0,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS sync_queue (
    id TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    retries INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 5,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status);

CREATE TABLE IF NOT EXISTS trash (
    id TEXT PRIMARY KEY,
    original_path TEXT NOT NULL,
    original_file_id TEXT NOT NULL DEFAULT '',
    deleted_at TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0
);
"""


class LocalDB:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        conn = self._get_conn()
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(_SCHEMA_SQL)

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.execute("PRAGMA busy_timeout=30000")
            self._local.conn = conn
        return self._local.conn

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_conn()

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ── Config ────────────────────────────────────────────────────────────────

    def get_config(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM config").fetchall()
        return dict(rows)

    def set_config(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    def set_config_batch(self, config: dict[str, str]) -> None:
        for key, value in config.items():
            self.set_config(key, value)

    def seed_default_config(self, defaults: dict[str, str]) -> None:
        existing = self.conn.execute("SELECT COUNT(*) FROM config").fetchone()[0]
        if existing == 0:
            for key, value in defaults.items():
                self.conn.execute(
                    "INSERT INTO config (key, value) VALUES (?, ?)", (key, value)
                )
            self.conn.commit()

    # ── Folders ───────────────────────────────────────────────────────────────

    def add_folder(self, path: str) -> None:
        label = Path(path).name or ""
        now = _now()
        self.conn.execute(
            "INSERT OR IGNORE INTO folders (path, label, added_at) VALUES (?, ?, ?)",
            (path, label, now),
        )
        self.conn.commit()

    def remove_folder(self, path: str) -> None:
        self.conn.execute("DELETE FROM folders WHERE path=?", (path,))
        self.conn.execute("DELETE FROM files WHERE local_path LIKE ?", (f"{path}%",))
        self.conn.commit()

    def get_folders(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT path, label FROM folders ORDER BY path"
        ).fetchall()
        return [
            {"path": row[0], "label": row[1], "exists": Path(row[0]).exists()}
            for row in rows
        ]

    # ── Files ─────────────────────────────────────────────────────────────────

    def _file_row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row[0],
            "local_path": row[1],
            "filename": row[2],
            "extension": row[3],
            "file_hash": row[4],
            "size_bytes": row[5],
            "mime_type": row[6],
            "modified_at": row[7],
            "processing_status": row[8],
            "extracted_text": row[9],
            "markdown": row[10],
            "content_blocks": row[11],
            "tables": row[12],
            "images": row[13],
            "language": row[14],
            "word_count": row[15],
            "char_count": row[16],
            "page_count": row[17],
            "synced": bool(row[18]),
            "first_seen_at": row[19],
            "updated_at": row[20],
        }

    def upsert_files(self, files: list[dict[str, Any]]) -> int:
        count = 0
        now = _now()
        for f in files:
            self.conn.execute(
                """INSERT INTO files (id, local_path, filename, extension, file_hash,
                    size_bytes, mime_type, modified_at, first_seen_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(local_path) DO UPDATE SET
                    filename=excluded.filename, extension=excluded.extension,
                    file_hash=excluded.file_hash, size_bytes=excluded.size_bytes,
                    mime_type=excluded.mime_type, modified_at=excluded.modified_at,
                    updated_at=excluded.updated_at""",
                (
                    f.get("id", _generate_id()),
                    f["local_path"],
                    f.get("filename", ""),
                    f.get("extension", ""),
                    f.get("file_hash", ""),
                    f.get("size_bytes", 0),
                    f.get("mime_type", ""),
                    f.get("modified_at", ""),
                    now,
                    now,
                ),
            )
            count += 1
        self.conn.commit()
        return count

    def update_file_after_scan(
        self,
        file_id: str,
        markdown: str,
        content_blocks: str,
        tables: str,
        images: str,
        language: str,
        word_count: int,
        char_count: int,
        page_count: int,
        **_kwargs: Any,
    ) -> None:
        extracted_text = markdown[:10000]
        now = _now()
        self.conn.execute(
            """UPDATE files SET extracted_text=?, markdown=?, content_blocks=?, tables=?,
                images=?, language=?, word_count=?, char_count=?, page_count=?,
                processing_status='completed', updated_at=?
            WHERE id=?""",
            (
                extracted_text, markdown, content_blocks, tables, images,
                language, word_count, char_count, page_count, now, file_id,
            ),
        )
        self.conn.commit()

    def mark_file_failed(self, file_id: str) -> None:
        now = _now()
        self.conn.execute(
            "UPDATE files SET processing_status='failed', updated_at=? WHERE id=?",
            (now, file_id),
        )
        self.conn.commit()

    def get_files(
        self, status: str | None = None, limit: int = 1000, folder: str | None = None
    ) -> list[dict[str, Any]]:
        query = """SELECT id, local_path, filename, extension, file_hash, size_bytes,
            mime_type, modified_at, processing_status, extracted_text, markdown,
            content_blocks, tables, images, language, word_count, char_count, page_count,
            synced, first_seen_at, updated_at FROM files WHERE 1=1"""
        params: list[Any] = []
        if status:
            query += " AND processing_status=?"
            params.append(status)
        if folder:
            query += " AND local_path LIKE ?"
            params.append(f"{folder}%")
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [self._file_row_to_dict(row) for row in rows]

    def get_file_by_id(self, file_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """SELECT id, local_path, filename, extension, file_hash, size_bytes,
                mime_type, modified_at, processing_status, extracted_text, markdown,
                content_blocks, tables, images, language, word_count, char_count, page_count,
                synced, first_seen_at, updated_at FROM files WHERE id=?""",
            (file_id,),
        ).fetchone()
        return self._file_row_to_dict(row) if row else None

    def mark_synced(self, file_hashes: list[str]) -> int:
        if not file_hashes:
            return 0
        now = _now()
        placeholders = ",".join("?" for _ in file_hashes)
        query = f"UPDATE files SET synced=1, updated_at=? WHERE file_hash IN ({placeholders})"
        self.conn.execute(query, (now, *file_hashes))
        self.conn.commit()
        return len(file_hashes)

    def get_pending_sync(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.get_files(status="completed", limit=limit)

    def get_stats(self) -> dict[str, Any]:
        total = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        pending = self.conn.execute(
            "SELECT COUNT(*) FROM files WHERE processing_status='pending'"
        ).fetchone()[0]
        completed = self.conn.execute(
            "SELECT COUNT(*) FROM files WHERE processing_status='completed'"
        ).fetchone()[0]
        failed = self.conn.execute(
            "SELECT COUNT(*) FROM files WHERE processing_status='failed'"
        ).fetchone()[0]
        synced = self.conn.execute(
            "SELECT COUNT(*) FROM files WHERE synced=1"
        ).fetchone()[0]
        return {
            "total": total,
            "pending": pending,
            "completed": completed,
            "failed": failed,
            "synced": synced,
        }

    # ── Jobs ──────────────────────────────────────────────────────────────────

    def create_job(self, job_type: str, payload: dict[str, Any] | None = None) -> str:
        job_id = _generate_id()
        now = _now()
        self.conn.execute(
            "INSERT INTO jobs (id, type, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, job_type, json.dumps(payload or {}), now, now),
        )
        self.conn.commit()
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """SELECT id, type, status, payload, progress, result, error,
                created_at, updated_at, started_at, completed_at FROM jobs WHERE id=?""",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "type": row[1],
            "status": row[2],
            "payload": json.loads(row[3]),
            "progress": row[4],
            "result": json.loads(row[5]) if row[5] else None,
            "error": row[6],
            "created_at": row[7],
            "updated_at": row[8],
            "started_at": row[9],
            "completed_at": row[10],
        }

    def list_jobs(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        query = """SELECT id, type, status, payload, progress, result, error,
            created_at, updated_at, started_at, completed_at FROM jobs"""
        params: list[Any] = []
        if status:
            query += " WHERE status=?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [
            {
                "id": r[0],
                "type": r[1],
                "status": r[2],
                "payload": json.loads(r[3]),
                "progress": r[4],
                "result": json.loads(r[5]) if r[5] else None,
                "error": r[6],
                "created_at": r[7],
                "updated_at": r[8],
                "started_at": r[9],
                "completed_at": r[10],
            }
            for r in rows
        ]

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        now = _now()
        fields = {"updated_at": now, **kwargs}
        sets = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values())
        values.append(job_id)
        self.conn.execute(
            f"UPDATE jobs SET {sets} WHERE id=?", values
        )
        self.conn.commit()

    # ── Trash ─────────────────────────────────────────────────────────────────

    def add_to_trash(self, original_path: str, original_file_id: str, size_bytes: int = 0) -> str:
        entry_id = _generate_id()
        now = _now()
        self.conn.execute(
            "INSERT INTO trash (id, original_path, original_file_id, deleted_at, size_bytes) VALUES (?, ?, ?, ?, ?)",
            (entry_id, original_path, original_file_id, now, size_bytes),
        )
        self.conn.commit()
        return entry_id

    def get_trash_entry(self, trash_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT id, original_path, original_file_id, deleted_at, size_bytes FROM trash WHERE id=?",
            (trash_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "original_path": row[1],
            "original_file_id": row[2],
            "deleted_at": row[3],
            "size_bytes": row[4],
        }

    def list_trash(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, original_path, original_file_id, deleted_at, size_bytes FROM trash ORDER BY deleted_at DESC"
        ).fetchall()
        return [
            {
                "id": r[0],
                "original_path": r[1],
                "original_file_id": r[2],
                "deleted_at": r[3],
                "size_bytes": r[4],
            }
            for r in rows
        ]

    def remove_from_trash(self, trash_id: str) -> None:
        self.conn.execute("DELETE FROM trash WHERE id=?", (trash_id,))
        self.conn.commit()

    # ── File Operations ───────────────────────────────────────────────────────

    def update_file_path(self, file_id: str, local_path: str, filename: str, extension: str) -> None:
        now = _now()
        self.conn.execute(
            "UPDATE files SET local_path=?, filename=?, extension=?, updated_at=? WHERE id=?",
            (local_path, filename, extension, now, file_id),
        )
        self.conn.commit()

    def delete_file_record(self, file_id: str) -> None:
        self.conn.execute("DELETE FROM files WHERE id=?", (file_id,))
        self.conn.commit()

    def delete_file_records_by_ids(self, file_ids: list[str]) -> None:
        if not file_ids:
            return
        placeholders = ",".join("?" for _ in file_ids)
        self.conn.execute(
            f"DELETE FROM files WHERE id IN ({placeholders})", file_ids
        )
        self.conn.commit()

    # ── Sync Queue ────────────────────────────────────────────────────────────

    def add_to_sync_queue(self, file_id: str) -> str:
        entry_id = _generate_id()
        now = _now()
        self.conn.execute(
            "INSERT INTO sync_queue (id, file_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (entry_id, file_id, now, now),
        )
        self.conn.commit()
        return entry_id

    def get_pending_sync_queue(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT id, file_id, status, retries, max_retries, error,
                created_at, updated_at FROM sync_queue
            WHERE status='pending' ORDER BY created_at ASC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "file_id": r[1],
                "status": r[2],
                "retries": r[3],
                "max_retries": r[4],
                "error": r[5],
                "created_at": r[6],
                "updated_at": r[7],
            }
            for r in rows
        ]
