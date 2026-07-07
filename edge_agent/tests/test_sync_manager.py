"""Tests for edge_agent.sync.manager — SyncManager."""
import json
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.config import EdgeAgentConfig
from edge_agent.db.local_db import LocalDB
from edge_agent.sync.manager import SyncManager


@pytest.fixture
def config(tmp_path):
    cfg = EdgeAgentConfig(
        agent_name="test-agent",
        agent_id="agent-001",
        data_dir=str(tmp_path),
    )
    cfg.server.url = "http://localhost:9999"
    cfg.server.api_key = "test-api-key"
    return cfg


@pytest.fixture
def db(tmp_path):
    local_db = LocalDB(str(tmp_path / "test.db"))
    yield local_db
    local_db.close()


@pytest.fixture
def manager(config, db):
    return SyncManager(config, db)


class TestSyncManagerRegister:
    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_register_sends_correct_payload(self, mock_make_client, manager):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"agent_id": "agent-001", "api_key": "new-key"}
        mock_client.post.return_value = mock_resp
        mock_make_client.return_value = mock_client

        result = manager.register(name="Test Agent", jwt_token="jwt-123")
        assert result["agent_id"] == "agent-001"
        call_args = mock_client.post.call_args
        assert "/api/v1/agents" in call_args[0][0]

    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_register_failure_raises(self, mock_make_client, manager):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "bad request"
        mock_client.post.return_value = mock_resp
        mock_make_client.return_value = mock_client

        with pytest.raises(RuntimeError):
            manager.register(name="X", jwt_token="jwt")


class TestSyncManagerHeartbeat:
    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_heartbeat_returns_commands(self, mock_make_client, manager):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "ok",
            "pending_commands": [{"id": "cmd-1", "type": "sync"}],
        }
        mock_client.post.return_value = mock_resp
        mock_make_client.return_value = mock_client

        result = manager.heartbeat()
        assert "pending_commands" in result

    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_heartbeat_failure_returns_empty(self, mock_make_client, manager):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.post.return_value = mock_resp
        mock_make_client.return_value = mock_client

        result = manager.heartbeat()
        assert result == {"pending_commands": []}


class TestSyncManagerSyncFiles:
    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_sync_empty_db(self, mock_make_client, manager):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"accepted": 0, "rejected": 0}
        mock_client.post.return_value = mock_resp
        mock_make_client.return_value = mock_client

        result = manager.sync_files()
        assert result["accepted"] == 0

    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_sync_sends_files(self, mock_make_client, config, db):
        local_db = db
        local_db.upsert_file({
            "local_path": "/tmp/doc.txt",
            "filename": "doc.txt",
            "extension": ".txt",
            "mime_type": "text/plain",
            "size_bytes": 100,
            "content_hash": "sha256:abc",
            "modified_at": 1700000000.0,
            "created_at": 1700000000.0,
            "first_seen_at": "2024-01-01",
        })

        mgr = SyncManager(config, local_db)
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"accepted": 1, "rejected": 0}
        mock_client.post.return_value = mock_resp
        mock_make_client = MagicMock(return_value=mock_client)

        with patch.object(mgr, "_make_client", mock_make_client):
            result = mgr.sync_files()
            assert result["accepted"] == 1
            # Verify file was marked synced
            files = local_db.list_files(synced=1)
            assert len(files) == 1

    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_sync_failure_raises(self, mock_make_client, manager):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "server error"
        mock_client.post.return_value = mock_resp
        mock_make_client.return_value = mock_client

        with pytest.raises(RuntimeError):
            manager.sync_files()


class TestSyncManagerSyncWithRetry:
    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_retry_exhaustion(self, mock_make_client, config, db):
        cfg = EdgeAgentConfig(
            agent_name="test", agent_id="a1",
            data_dir=config.data_dir,
        )
        cfg.server.url = config.server.url
        cfg.server.api_key = config.server.api_key
        cfg.sync.retry_attempts = 2
        cfg.sync.retry_delay_seconds = 0.01

        mgr = SyncManager(cfg, db)
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        mock_client.post.return_value = mock_resp
        mock_make_client.return_value = mock_client

        with pytest.raises(RuntimeError):
            mgr.sync_with_retry()


class TestSyncManagerReportCommand:
    @patch("edge_agent.sync.manager.SyncManager._make_client")
    def test_report_command_result(self, mock_make_client, manager):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_client.post.return_value = mock_resp
        mock_make_client.return_value = mock_client

        result = manager.report_command_result("cmd-123", status="completed", result={"ok": True})
        assert result["status"] == "ok"
