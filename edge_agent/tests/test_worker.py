"""Tests for edge_agent.core.worker — background job worker."""
import time
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.core.job_queue import JobQueue
from edge_agent.core.worker import Worker
from edge_agent.db.local_db import LocalDB


@pytest.fixture
def db(tmp_path):
    return LocalDB(str(tmp_path / "test.db"))


@pytest.fixture
def queue(db):
    return JobQueue(db)


class TestWorker:
    def test_start_stop(self, db):
        w = Worker(db)
        assert not w.is_running
        w.start()
        assert w.is_running
        w.stop()
        assert not w.is_running

    def test_double_start(self, db):
        w = Worker(db)
        w.start()
        w.start()
        w.stop()

    @patch("edge_agent.core.worker.ParserRouter")
    @patch("edge_agent.core.worker.OCREngine")
    def test_wait_for_job_completed(self, mock_ocr, mock_parser, db, tmp_path):
        from edge_agent.core.models import ParsedDocument

        mock_parser.return_value.parse.return_value = ParsedDocument(
            markdown="parsed content"
        )

        f = tmp_path / "test.txt"
        f.write_text("hello world")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "test.txt"}])

        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "file1"})
            result = w.wait_for_job(jid, timeout=10.0)
            assert result is not None
            assert result["status"] == "completed"
        finally:
            w.stop()

    def test_wait_for_job_timeout(self, db):
        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "nonexistent"})
            result = w.wait_for_job(jid, timeout=2.0)
            assert result is not None
            assert result["status"] == "failed"
        finally:
            w.stop()

    def test_unknown_job_type(self, db):
        w = Worker(db)
        w.start()
        try:
            jid = db.create_job("unknown_type", {})
            result = w.wait_for_job(jid, timeout=5.0)
            assert result is not None
            assert result["status"] == "failed"
        finally:
            w.stop()

    def test_pause_resume(self, db):
        w = Worker(db)
        w.start()
        try:
            assert not w._paused
            w.pause()
            assert w._paused
            w.resume()
            assert not w._paused
        finally:
            w.stop()

    def test_paused_does_not_process(self, db):
        w = Worker(db)
        w.start()
        w.pause()
        try:
            jid = db.create_job("scan_file", {"file_id": "nonexistent"})
            time.sleep(2)
            job = db.get_job(jid)
            assert job["status"] == "pending"
        finally:
            w.stop()

    def test_processing_count(self, db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "test.txt"}])

        w = Worker(db)
        assert w.processing_count == 0
        w.start()
        try:
            jid = db.create_job("scan_file", {"file_id": "file1"})
            w.wait_for_job(jid, timeout=10.0)
        finally:
            w.stop()

    def test_restart(self, db):
        w = Worker(db)
        w.start()
        time.sleep(0.2)
        w.restart()
        assert w.is_running
        w.stop()
