"""Tests for edge_agent.db.local_db — SQLite local database."""
import json
import tempfile
from pathlib import Path

import pytest

from edge_agent.db.local_db import LocalDB


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    local_db = LocalDB(db_path)
    yield local_db
    local_db.close()


@pytest.fixture
def sample_file():
    return {
        "local_path": "/tmp/test.pdf",
        "filename": "test.pdf",
        "extension": ".pdf",
        "mime_type": "application/pdf",
        "size_bytes": 1024,
        "content_hash": "sha256:abc123",
        "modified_at": 1700000000.0,
        "created_at": 1700000000.0,
        "first_seen_at": "2024-01-01T00:00:00",
    }


class TestLocalDBUpsertFile:
    def test_upsert_creates_file(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        assert file_id
        fetched = db.get_file(file_id)
        assert fetched is not None
        assert fetched["filename"] == "test.pdf"

    def test_upsert_idempotent_by_hash(self, db, sample_file):
        id1 = db.upsert_file(sample_file)
        id2 = db.upsert_file(sample_file)
        assert id1 == id2

    def test_upsert_returns_string_id(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        assert isinstance(file_id, str)


class TestLocalDBGetFile:
    def test_get_file_existing(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        assert db.get_file(file_id) is not None

    def test_get_file_nonexistent(self, db):
        assert db.get_file("nonexistent-id") is None

    def test_get_file_by_hash(self, db, sample_file):
        db.upsert_file(sample_file)
        result = db.get_file_by_hash("sha256:abc123")
        assert result is not None

    def test_get_file_by_path(self, db, sample_file):
        db.upsert_file(sample_file)
        result = db.get_file_by_path("/tmp/test.pdf")
        assert result is not None


class TestLocalDBUpdateFile:
    def test_update_file_status(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        db.update_file(file_id, processing_status="completed")
        result = db.get_file(file_id)
        assert result["processing_status"] == "completed"

    def test_update_file_text(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        db.update_file(file_id, extracted_text="hello world")
        result = db.get_file(file_id)
        assert result["extracted_text"] == "hello world"

    def test_update_json_field(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        db.update_file(file_id, content_blocks='[{"type": "text"}]')
        result = db.get_file(file_id)
        assert result["content_blocks"] == '[{"type": "text"}]'


class TestLocalDBListFiles:
    def test_list_files_empty(self, db):
        assert db.list_files() == []

    def test_list_files_with_data(self, db, sample_file):
        db.upsert_file(sample_file)
        files = db.list_files()
        assert len(files) == 1

    def test_list_files_filter_status(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        db.update_file(file_id, processing_status="completed")
        pending = db.list_files(status="pending")
        assert len(pending) == 0
        completed = db.list_files(status="completed")
        assert len(completed) == 1


class TestLocalDBSync:
    def test_pending_sync(self, db, sample_file):
        db.upsert_file(sample_file)
        pending = db.get_pending_sync()
        assert len(pending) == 1

    def test_mark_synced(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        db.mark_synced([file_id])
        pending = db.get_pending_sync()
        assert len(pending) == 0
        result = db.get_file(file_id)
        assert result["synced"] == 1


class TestLocalDBStats:
    def test_empty_stats(self, db):
        stats = db.get_stats()
        assert stats["total"] == 0

    def test_stats_with_files(self, db, sample_file):
        db.upsert_file(sample_file)
        stats = db.get_stats()
        assert stats["total"] == 1
        assert stats["pending"] == 1


class TestLocalDBDelete:
    def test_delete_file(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        assert db.delete_file(file_id) is True
        assert db.get_file(file_id) is None

    def test_delete_nonexistent(self, db):
        assert db.delete_file("nonexistent") is False


class TestLocalDBEntities:
    def test_save_and_get_entities(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        entities = [
            {"entity_type": "person", "name": "John", "context": "CEO", "confidence": 0.9},
            {"entity_type": "org", "name": "Acme", "context": "Company", "confidence": 0.85},
        ]
        db.save_entities(file_id, entities)
        result = db.get_entities(file_id)
        assert len(result) == 2

    def test_save_entities_replaces(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        db.save_entities(file_id, [{"entity_type": "person", "name": "A", "context": "", "confidence": None}])
        db.save_entities(file_id, [{"entity_type": "org", "name": "B", "context": "", "confidence": None}])
        result = db.get_entities(file_id)
        assert len(result) == 1
        assert result[0]["name"] == "B"

    def test_entity_stats(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        db.save_entities(file_id, [
            {"entity_type": "person", "name": "A", "context": "", "confidence": None},
            {"entity_type": "person", "name": "B", "context": "", "confidence": None},
            {"entity_type": "org", "name": "C", "context": "", "confidence": None},
        ])
        stats = db.get_entity_stats()
        assert stats["person"] == 2
        assert stats["org"] == 1

    def test_get_all_entities(self, db, sample_file):
        file_id = db.upsert_file(sample_file)
        db.save_entities(file_id, [{"entity_type": "person", "name": "X", "context": "", "confidence": None}])
        all_ents = db.get_all_entities()
        assert len(all_ents) == 1
