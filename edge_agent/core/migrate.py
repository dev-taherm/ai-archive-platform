from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_MIGRATION_KEY = "_migrated_from_desktop_db"
_OLD_DB_PATH = Path.home() / ".basirah" / "desktop.db"


def run_migration(db_path: str) -> None:
    """Copy data from ~/.basirah/desktop.db (Rust legacy DB) into the agent's SQLite.

    Idempotent — checks the config table for a migration marker before running.
    Leaves the old database untouched for one release cycle (rollback option).
    """
    dest_conn = sqlite3.connect(db_path)

    already = dest_conn.execute(
        "SELECT value FROM config WHERE key=?", (_MIGRATION_KEY,)
    ).fetchone()
    if already and already[0] == "done":
        logger.info("Migration already completed, skipping")
        dest_conn.close()
        return

    if not _OLD_DB_PATH.exists():
        logger.info("No legacy DB found at %s, nothing to migrate", _OLD_DB_PATH)
        dest_conn.close()
        return

    # Drop any stale tables from old Python agent DB to avoid schema conflicts
    for table in ("files", "sync_log", "entities"):
        dest_conn.execute(f"DROP TABLE IF EXISTS {table}")
    dest_conn.commit()

    # Recreate tables with current schema via LocalDB init
    from edge_agent.db.local_db import LocalDB
    LocalDB.__init__.__globals__  # ensure module is loaded
    dest_conn.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY, local_path TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL, extension TEXT NOT NULL DEFAULT '',
            file_hash TEXT NOT NULL DEFAULT '', size_bytes INTEGER NOT NULL DEFAULT 0,
            mime_type TEXT NOT NULL DEFAULT '', modified_at TEXT NOT NULL DEFAULT '',
            processing_status TEXT NOT NULL DEFAULT 'pending',
            extracted_text TEXT NOT NULL DEFAULT '', markdown TEXT NOT NULL DEFAULT '',
            content_blocks TEXT NOT NULL DEFAULT '[]', tables TEXT NOT NULL DEFAULT '[]',
            images TEXT NOT NULL DEFAULT '[]', language TEXT NOT NULL DEFAULT 'unknown',
            word_count INTEGER NOT NULL DEFAULT 0, char_count INTEGER NOT NULL DEFAULT 0,
            page_count INTEGER NOT NULL DEFAULT 0, synced INTEGER NOT NULL DEFAULT 0,
            first_seen_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_files_status ON files(processing_status);
        CREATE INDEX IF NOT EXISTS idx_files_synced ON files(synced);
        CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash);
        CREATE INDEX IF NOT EXISTS idx_files_path ON files(local_path);
    """)
    dest_conn.commit()

    logger.info("Migrating from legacy DB: %s", _OLD_DB_PATH)
    src_conn = sqlite3.connect(str(_OLD_DB_PATH))

    tables = {
        "config": ("key", "value"),
        "folders": ("path", "label", "added_at"),
        "files": (
            "id", "local_path", "filename", "extension", "file_hash",
            "size_bytes", "mime_type", "modified_at", "processing_status",
            "extracted_text", "markdown", "content_blocks", "tables", "images",
            "language", "word_count", "char_count", "page_count",
            "synced", "first_seen_at", "updated_at",
        ),
    }

    for table, columns in tables.items():
        _migrate_table(src_conn, dest_conn, table, columns)

    src_conn.close()

    dest_conn.execute(
        "INSERT INTO config (key, value) VALUES (?, ?)",
        (_MIGRATION_KEY, "done"),
    )
    dest_conn.commit()
    dest_conn.close()

    logger.info("Migration complete (legacy DB preserved at %s)", _OLD_DB_PATH)


def _migrate_table(
    src: sqlite3.Connection,
    dst: sqlite3.Connection,
    table: str,
    columns: tuple[str, ...],
) -> None:
    try:
        rows = src.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
    except sqlite3.OperationalError:
        logger.warning("Table %s not found in legacy DB, skipping", table)
        return

    if not rows:
        logger.info("Table %s is empty in legacy DB, skipping", table)
        return

    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    insert_sql = (
        f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"
    )

    try:
        dst.executemany(insert_sql, rows)
        dst.commit()
        logger.info("Migrated %d rows from %s.%s", len(rows), table)
    except sqlite3.IntegrityError as e:
        # Fall back to row-by-row insert
        for row in rows:
            try:
                dst.execute(insert_sql, row)
            except sqlite3.IntegrityError:
                pass
        dst.commit()
        logger.warning("Migrated %s with some conflicts: %s", table, e)
