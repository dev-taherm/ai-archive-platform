"""Tests for edge_agent.api.routes — HTTP API endpoints."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from edge_agent.api.server import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        db_path=str(tmp_path / "test.db"),
        config_overrides={"ocr": {"engine": "tesseract"}},
    )
    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_status(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_name" in data
        assert "uptime_seconds" in data

    def test_capabilities(self, client):
        resp = client.get("/api/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_version" in data
        assert "platform" in data


class TestConfig:
    def test_get_config(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_update_config(self, client):
        resp = client.put("/api/config", json={"config": {"test_key": "test_val"}})
        assert resp.status_code == 200
        resp2 = client.get("/api/config")
        assert resp2.json().get("test_key") == "test_val"


class TestFolders:
    def test_add_and_list(self, client, tmp_path):
        resp = client.post("/api/folders", json={"path": str(tmp_path)})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        resp2 = client.get("/api/folders")
        assert resp2.status_code == 200
        folders = resp2.json()
        assert any(f["path"] == str(tmp_path) for f in folders)

    def test_remove(self, client, tmp_path):
        client.post("/api/folders", json={"path": str(tmp_path)})
        resp = client.delete(f"/api/folders", params={"path": str(tmp_path)})
        assert resp.status_code == 200

    def test_rescan(self, client, tmp_path):
        client.post("/api/folders", json={"path": str(tmp_path)})
        (tmp_path / "test.txt").write_text("hello")
        resp = client.post("/api/folders/rescan", json={"path": str(tmp_path)})
        assert resp.status_code == 200
        assert resp.json()["discovered"] >= 1


class TestFiles:
    def test_list_empty(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_nonexistent(self, client):
        resp = client.get("/api/files/nonexistent")
        assert resp.status_code == 404


class TestParse:
    def test_parse_nonexistent(self, client):
        resp = client.post("/api/parse-file", json={"file_path": "/nonexistent.txt"})
        assert resp.status_code == 400

    def test_parse_directory(self, client, tmp_path):
        resp = client.post("/api/parse-file", json={"file_path": str(tmp_path)})
        assert resp.status_code == 400


class TestJobs:
    def test_create_and_list(self, client):
        resp = client.post("/api/jobs", json={"type": "test", "payload": {}})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        resp2 = client.get(f"/api/jobs/{job_id}")
        assert resp2.status_code == 200
        assert resp2.json()["type"] == "test"

    def test_list_jobs(self, client):
        client.post("/api/jobs", json={"type": "a"})
        client.post("/api/jobs", json={"type": "b"})
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_nonexistent_job(self, client):
        resp = client.get("/api/jobs/nonexistent")
        assert resp.status_code == 404


class TestLogs:
    def test_logs_empty(self, client):
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_logs_with_params(self, client):
        resp = client.get("/api/logs", params={"level": "ERROR", "limit": 5})
        assert resp.status_code == 200
        assert len(resp.json()) <= 5


class TestMetrics:
    def test_metrics(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "files_scanned" in data
        assert "memory_mb" in data


class TestAgentControl:
    def test_pause_resume(self, client):
        resp = client.post("/api/agent/pause")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

        resp2 = client.post("/api/agent/resume")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "resumed"

    def test_restart(self, client):
        resp = client.post("/api/agent/restart")
        assert resp.status_code == 200
