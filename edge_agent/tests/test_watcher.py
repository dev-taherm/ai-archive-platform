"""Tests for edge_agent.core.watcher — folder monitoring."""
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.core.job_queue import JobQueue
from edge_agent.core.watcher import FolderWatcher
from edge_agent.db.local_db import LocalDB


@pytest.fixture
def db(tmp_path):
    d = LocalDB(str(tmp_path / "test.db"))
    d.add_folder(str(tmp_path))
    return d


class TestFolderWatcher:
    def test_start_stop(self, tmp_path, db):
        w = FolderWatcher(db, debounce_seconds=0.5)
        assert not w.is_running
        folders = db.get_folders()
        w.start([f["path"] for f in folders])
        assert w.is_running
        w.stop()
        assert not w.is_running

    def test_double_start(self, tmp_path, db):
        w = FolderWatcher(db)
        folders = db.get_folders()
        w.start([f["path"] for f in folders])
        w.start([f["path"] for f in folders])
        w.stop()

    def test_detect_new_file(self, tmp_path, db):
        w = FolderWatcher(db, debounce_seconds=0.3)
        w._scan_and_enqueue = MagicMock()
        folders = db.get_folders()
        w.start([f["path"] for f in folders])
        try:
            new_file = tmp_path / "new.txt"
            new_file.write_text("hello")
            time.sleep(1)
            assert w._scan_and_enqueue.called
        finally:
            w.stop()

    @pytest.mark.skip(reason="Uses polling loop timing")
    def test_folder_count(self, tmp_path, db):
        w = FolderWatcher(db)
        folders = db.get_folders()
        w.start([f["path"] for f in folders])
        try:
            assert w.folder_count >= 1
        finally:
            w.stop()

    def test_scan_and_enqueue(self, tmp_path, db):
        w = FolderWatcher(db)
        original_count = len(db.get_files())
        (tmp_path / "scan_me.txt").write_text("data")
        w._scan_and_enqueue([str(tmp_path)])
        files = db.get_files()
        assert len(files) >= original_count + 1
