"""Tests for edge_agent.core.migrate — database migration from old format."""
import sqlite3
import json
from pathlib import Path

import pytest

from edge_agent.core.migrate import run_migration
from edge_agent.db.local_db import LocalDB


@pytest.fixture
def old_db_path(tmp_path):
    """Create a realistic old-format database matching the Rust db.rs schema."""
    path = str(tmp_path / "old_desktop.db")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
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
    """)

    conn.execute(
        "INSERT INTO config (key, value) VALUES (?, ?)",
        ("server_url", "http://localhost:8000"),
    )
    conn.execute(
        "INSERT INTO config (key, value) VALUES (?, ?)",
        ("agent_id", "migrated-agent"),
    )
    conn.execute(
        "INSERT INTO folders (path, label, added_at) VALUES (?, ?, ?)",
        ("/tmp/docs", "docs", "2025-01-01T00:00:00"),
    )
    conn.execute(
        """INSERT INTO files (id, local_path, filename, extension, file_hash, size_bytes,
            mime_type, modified_at, processing_status, first_seen_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("file1", "/tmp/docs/a.txt", "a.txt", ".txt", "abc123", 100,
         "text/plain", "2025-01-01T00:00:00", "completed", "2025-01-01T00:00:00", "2025-01-01T00:00:00"),
    )
    conn.commit()
    conn.close()
    return path


class TestMigrate:
    def test_migrate_from_old(self, tmp_path, old_db_path):
        new_db_path = str(tmp_path / "new_agent.db")
        run_migration(old_db_path, new_db_path)

        new_db = LocalDB(new_db_path)
        try:
            config = new_db.get_config()
            assert config.get("server_url") == "http://localhost:8000"
            assert config.get("agent_id") == "migrated-agent"
            assert config.get("migration_done") == "true"

            folders = new_db.get_folders()
            assert len(folders) == 1
            assert folders[0]["path"] == "/tmp/docs"

            files = new_db.get_files()
            assert len(files) == 1
            assert files[0]["filename"] == "a.txt"
            assert files[0]["file_hash"] == "abc123"
        finally:
            new_db.close()

    def test_migrate_no_old_db(self, tmp_path):
        new_db_path = str(tmp_path / "new_agent.db")
        run_migration("/nonexistent/path", new_db_path)
        new_db = LocalDB(new_db_path)
        try:
            config = new_db.get_config()
            assert config.get("migration_done") == "true"
            assert new_db.get_folders() == []
        finally:
            new_db.close()

    def test_migrate_idempotent(self, tmp_path, old_db_path):
        new_db_path = str(tmp_path / "new_agent.db")
        run_migration(old_db_path, new_db_path)
        run_migration(old_db_path, new_db_path)
        new_db = LocalDB(new_db_path)
        try:
            files = new_db.get_files()
            assert len(files) == 1
        finally:
            new_db.close()

    def test_migrate_preserves_old_db(self, old_db_path, tmp_path):
        new_db_path = str(tmp_path / "new_agent.db")
        run_migration(old_db_path, new_db_path)
        old_conn = sqlite3.connect(old_db_path)
        try:
            count = old_conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            assert count == 1
        finally:
            old_conn.close()

    def test_migration_marker_in_config(self, tmp_path):
        new_db_path = str(tmp_path / "new.db")
        run_migration("/nonexistent", new_db_path)
        db = LocalDB(new_db_path)
        try:
            assert db.get_config().get("migration_done") == "true"
        finally:
            db.close()
