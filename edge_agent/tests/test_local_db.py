"""Tests for edge_agent.db.local_db — SQLite CRUD operations."""
import json
import uuid
from pathlib import Path

import pytest

from edge_agent.db.local_db import LocalDB


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    return LocalDB(path)


class TestConfig:
    def test_get_config_empty(self, db):
        assert db.get_config() == {}

    def test_set_and_get(self, db):
        db.set_config("key1", "value1")
        cfg = db.get_config()
        assert cfg["key1"] == "value1"

    def test_set_batch(self, db):
        db.set_config_batch({"a": "1", "b": "2"})
        cfg = db.get_config()
        assert cfg == {"a": "1", "b": "2"}

    def test_update_existing(self, db):
        db.set_config("key", "old")
        db.set_config("key", "new")
        assert db.get_config()["key"] == "new"

    def test_seed_defaults(self, db):
        db.seed_default_config({"key": "val"})
        assert db.get_config()["key"] == "val"
        # Second seed should not overwrite
        db.seed_default_config({"other": "val2"})
        assert db.get_config()["key"] == "val"

    def test_seed_empty_on_existing(self, db):
        db.set_config("existing", "yes")
        db.seed_default_config({"new": "no"})
        cfg = db.get_config()
        assert "new" not in cfg


class TestFolders:
    def test_add_and_list(self, db):
        db.add_folder("/tmp/test")
        folders = db.get_folders()
        assert len(folders) == 1
        assert folders[0]["path"] == "/tmp/test"

    def test_add_duplicate(self, db):
        db.add_folder("/tmp/a")
        db.add_folder("/tmp/a")
        assert len(db.get_folders()) == 1

    def test_remove(self, db):
        db.add_folder("/tmp/a")
        db.remove_folder("/tmp/a")
        assert len(db.get_folders()) == 0

    def test_get_folders_exists(self, db, tmp_path):
        db.add_folder(str(tmp_path))
        folders = db.get_folders()
        assert folders[0]["exists"] is True

    def test_get_folders_not_exists(self, db):
        db.add_folder("/nonexistent/path")
        folders = db.get_folders()
        assert folders[0]["exists"] is False


class TestFiles:
    def test_upsert_and_get(self, db):
        files = [{"local_path": "/tmp/a.txt", "filename": "a.txt", "extension": ".txt"}]
        db.upsert_files(files)
        result = db.get_files()
        assert len(result) == 1
        assert result[0]["filename"] == "a.txt"

    def test_upsert_updates_existing(self, db):
        f1 = {"local_path": "/tmp/a.txt", "filename": "old.txt", "extension": ".txt"}
        f2 = {"local_path": "/tmp/a.txt", "filename": "new.txt", "extension": ".txt"}
        db.upsert_files([f1])
        db.upsert_files([f2])
        result = db.get_files()
        assert result[0]["filename"] == "new.txt"

    def test_get_by_id(self, db):
        f = {"local_path": "/tmp/a.txt", "filename": "a.txt", "extension": ".txt"}
        db.upsert_files([f])
        file_id = db.get_files()[0]["id"]
        found = db.get_file_by_id(file_id)
        assert found is not None
        assert found["filename"] == "a.txt"

    def test_get_by_id_not_found(self, db):
        assert db.get_file_by_id("nonexistent") is None

    def test_mark_file_failed(self, db):
        db.upsert_files([{"local_path": "/tmp/a.txt", "filename": "a.txt"}])
        file_id = db.get_files()[0]["id"]
        db.mark_file_failed(file_id)
        assert db.get_file_by_id(file_id)["processing_status"] == "failed"

    def test_update_file_after_scan(self, db):
        db.upsert_files([{"local_path": "/tmp/a.txt", "filename": "a.txt"}])
        file_id = db.get_files()[0]["id"]
        db.update_file_after_scan(file_id, "markdown", "[]", "[]", "[]", "en", 10, 50, 1)
        updated = db.get_file_by_id(file_id)
        assert updated["markdown"] == "markdown"
        assert updated["language"] == "en"
        assert updated["processing_status"] == "completed"

    def test_get_files_by_status(self, db):
        db.upsert_files([{"local_path": "/tmp/a.txt", "filename": "a.txt"}])
        db.upsert_files([{"local_path": "/tmp/b.txt", "filename": "b.txt"}])
        files = db.get_files(status="pending", limit=10)
        assert len(files) == 2

    def test_mark_synced(self, db):
        db.upsert_files([{"local_path": "/tmp/a.txt", "filename": "a.txt", "file_hash": "abc"}])
        db.mark_synced(["abc"])
        files = db.get_files()
        assert files[0]["synced"] is True

    def test_get_stats(self, db):
        db.upsert_files([{"local_path": "/tmp/a.txt", "filename": "a.txt"}])
        db.upsert_files([{"local_path": "/tmp/b.txt", "filename": "b.txt"}])
        file_id = db.get_files()[0]["id"]
        db.mark_file_failed(file_id)
        stats = db.get_stats()
        assert stats["total"] == 2
        assert stats["failed"] == 1


class TestJobs:
    def test_create_and_get(self, db):
        jid = db.create_job("scan_file", {"file_id": "abc"})
        job = db.get_job(jid)
        assert job is not None
        assert job["type"] == "scan_file"
        assert job["status"] == "pending"

    def test_list_jobs(self, db):
        db.create_job("type_a")
        db.create_job("type_b")
        jobs = db.list_jobs(limit=10)
        assert len(jobs) == 2

    def test_list_jobs_filtered(self, db):
        jid = db.create_job("type_a")
        db.update_job(jid, status="running")
        db.create_job("type_b")
        jobs = db.list_jobs(status="running", limit=10)
        assert len(jobs) == 1

    def test_update_job(self, db):
        jid = db.create_job("test")
        db.update_job(jid, status="running", progress=0.5)
        job = db.get_job(jid)
        assert job["status"] == "running"
        assert job["progress"] == 0.5

    def test_get_nonexistent_job(self, db):
        assert db.get_job("nonexistent") is None

    def test_complete_job(self, db):
        jid = db.create_job("scan_file")
        db.update_job(jid, status="completed", result='{"ok": true}')
        job = db.get_job(jid)
        assert job["status"] == "completed"
        assert job["result"] == '{"ok": true}'
        assert job["completed_at"] is not None


class TestSyncQueue:
    def test_add_and_list(self, db):
        db.upsert_files([{"local_path": "/tmp/a.txt", "filename": "a.txt"}])
        file_id = db.get_files()[0]["id"]
        eid = db.add_to_sync_queue(file_id)
        entries = db.get_pending_sync_queue(limit=10)
        assert len(entries) == 1
        assert entries[0]["file_id"] == file_id

    def test_empty_queue(self, db):
        assert db.get_pending_sync_queue(limit=10) == []


class TestTrash:
    def test_add_and_list(self, db):
        db.add_to_trash("/tmp/a.txt", "abc", 100)
        entries = db.list_trash()
        assert len(entries) == 1
        assert entries[0]["original_path"] == "/tmp/a.txt"

    def test_get_trash_entry(self, db):
        tid = db.add_to_trash("/tmp/a.txt", "abc", 100)
        entry = db.get_trash_entry(tid)
        assert entry is not None
        assert entry["original_path"] == "/tmp/a.txt"

    def test_remove_from_trash(self, db):
        tid = db.add_to_trash("/tmp/a.txt", "abc", 100)
        db.remove_from_trash(tid)
        assert db.get_trash_entry(tid) is None

    def test_empty_trash(self, db):
        assert db.list_trash() == []
