"""Tests for edge_agent.core.sync_engine — SaaS communication."""
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.core.sync_engine import SyncEngine
from edge_agent.db.local_db import LocalDB


@pytest.fixture
def db(tmp_path):
    d = LocalDB(str(tmp_path / "test.db"))
    d.seed_default_config({"server_url": "http://localhost:8000", "api_key": "test"})
    return d


class TestSyncEngine:
    def test_init(self, db):
        engine = SyncEngine(db)
        assert engine.server_url == "http://localhost:8000"

    def test_init_no_config(self, tmp_path):
        db = LocalDB(str(tmp_path / "empty.db"))
        engine = SyncEngine(db)
        assert engine.server_url is None

    @patch("urllib.request.urlopen")
    def test_register_success(self, mock_urlopen, db):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"agent_id": "new-id", "api_key": "new-key", "is_new": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        engine = SyncEngine(db)
        result = engine.register("http://server.test", "token123")
        assert result["agent_id"] == "new-id"
        assert db.get_config().get("agent_id") == "new-id"

    @patch("urllib.request.urlopen")
    def test_register_api_error(self, mock_urlopen, db):
        mock_urlopen.side_effect = Exception("Connection refused")

        engine = SyncEngine(db)
        result = engine.register("http://server.test", "token123")
        assert "error" in result

    @patch("urllib.request.urlopen")
    def test_heartbeat(self, mock_urlopen, db):
        db.set_config("agent_id", "test-agent")
        db.set_config("api_key", "test-key")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        engine = SyncEngine(db)
        result = engine.heartbeat()
        assert result["status"] == "ok"

    def test_heartbeat_no_credentials(self, db):
        engine = SyncEngine(db)
        engine.agent_id = None
        result = engine.heartbeat()
        assert "error" in result

    @patch("urllib.request.urlopen")
    def test_sync_files(self, mock_urlopen, db):
        db.set_config("agent_id", "test-agent")
        db.set_config("api_key", "test-key")
        db.upsert_files([{
            "id": "file1",
            "local_path": "/tmp/test.txt",
            "filename": "test.txt",
            "processing_status": "completed",
            "synced": False,
        }])
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"accepted": 1, "rejected": 0, "errors": []}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        engine = SyncEngine(db)
        result = engine.sync_files()
        assert result["status"] == "ok"
