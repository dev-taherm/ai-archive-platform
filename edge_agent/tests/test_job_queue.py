"""Tests for edge_agent.core.job_queue — job queue management."""
import pytest

from edge_agent.core.job_queue import JobQueue
from edge_agent.db.local_db import LocalDB


@pytest.fixture
def queue(tmp_path):
    db = LocalDB(str(tmp_path / "test.db"))
    return JobQueue(db)


class TestJobQueue:
    def test_create_job(self, queue):
        jid = queue.create_job("scan_file", {"file_id": "abc"})
        job = queue.get_job(jid)
        assert job["type"] == "scan_file"
        assert job["status"] == "pending"

    def test_start_job(self, queue):
        jid = queue.create_job("test")
        queue.start_job(jid)
        job = queue.get_job(jid)
        assert job["status"] == "running"
        assert job["started_at"] is not None

    def test_complete_job(self, queue):
        jid = queue.create_job("test")
        queue.start_job(jid)
        queue.complete_job(jid, {"ok": True})
        job = queue.get_job(jid)
        assert job["status"] == "completed"
        assert job["result"] == {"ok": True}
        assert job["completed_at"] is not None

    def test_fail_job(self, queue):
        jid = queue.create_job("test")
        queue.start_job(jid)
        queue.fail_job(jid, "Something went wrong")
        job = queue.get_job(jid)
        assert job["status"] == "failed"
        assert "Something went wrong" in job["error"]

    def test_list_jobs_pending(self, queue):
        queue.create_job("a")
        queue.create_job("b")
        jid = queue.create_job("c")
        queue.start_job(jid)
        pending = queue.list_jobs(status="pending", limit=10)
        assert len(pending) == 2

    def test_list_jobs_limit(self, queue):
        for i in range(10):
            queue.create_job(f"job_{i}")
        jobs = queue.list_jobs(limit=3)
        assert len(jobs) == 3

    def test_get_nonexistent(self, queue):
        assert queue.get_job("nonexistent") is None

    def test_complete_without_start(self, queue):
        jid = queue.create_job("test")
        queue.complete_job(jid, {"ok": True})
        job = queue.get_job(jid)
        assert job["status"] == "completed"

    def test_job_round_trip_payload(self, queue):
        payload = {"file_id": "abc", "lang": "en", "priority": 1}
        jid = queue.create_job("scan_file", payload)
        job = queue.get_job(jid)
        assert job["payload"] == payload
