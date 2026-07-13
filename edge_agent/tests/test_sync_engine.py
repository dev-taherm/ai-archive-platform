"""Tests for edge_agent.core.sync_engine — SaaS communication."""
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.core.sync_engine import SyncEngine, _sanitize_text, _sanitize_json_recursive
from edge_agent.db.local_db import LocalDB


@pytest.fixture
def db(tmp_path):
    d = LocalDB(str(tmp_path / "test.db"))
    d.seed_default_config({"server_url": "http://localhost:8000", "api_key": "test"})
    return d


@pytest.fixture
def config():
    cfg = MagicMock()
    cfg.agent_version = "0.1.0"
    return cfg


class TestSyncEngine:
    def test_init(self, db, config):
        engine = SyncEngine(db, config)
        assert engine._config is config
        assert engine.db is db

    def test_get_credentials(self, db, config):
        db.set_config("server_url", "http://server.test")
        db.set_config("agent_id", "agent-1")
        db.set_config("api_key", "ak_test")
        engine = SyncEngine(db, config)
        creds = engine.get_credentials()
        assert creds["server_url"] == "http://server.test"
        assert creds["agent_id"] == "agent-1"
        assert creds["api_key"] == "ak_test"

    def test_get_credentials_missing(self, db, config):
        engine = SyncEngine(db, config)
        creds = engine.get_credentials()
        # Credentials not set — agent_id and api_key missing
        assert not all(creds.values())

    @patch("urllib.request.urlopen")
    def test_register_success(self, mock_urlopen, db, config):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"agent_id": "new-id", "api_key": "new-key", "is_new": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        engine = SyncEngine(db, config)
        result = engine.register("http://server.test", "token123")
        assert result["agent_id"] == "new-id"
        assert db.get_config().get("agent_id") == "new-id"

    @patch("urllib.request.urlopen")
    def test_register_api_error(self, mock_urlopen, db, config):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        engine = SyncEngine(db, config)
        with pytest.raises(RuntimeError, match="Registration failed"):
            engine.register("http://server.test", "token123")

    @patch("urllib.request.urlopen")
    def test_register_http_error(self, mock_urlopen, db, config):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://server.test", code=401, msg="Unauthorized",
            hdrs=None, fp=MagicMock(read=MagicMock(return_value=b"unauthorized"))
        )

        engine = SyncEngine(db, config)
        with pytest.raises(RuntimeError, match="Registration returned 401"):
            engine.register("http://server.test", "bad-token")

    @patch("urllib.request.urlopen")
    def test_sync_files(self, mock_urlopen, db, config):
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

        engine = SyncEngine(db, config)
        result = engine.sync_files()
        assert result["status"] == "ok"

    def test_sync_no_files(self, db, config):
        db.set_config("agent_id", "test-agent")
        db.set_config("api_key", "test-key")
        engine = SyncEngine(db, config)
        result = engine.sync_files()
        assert result["status"] == "ok"
        assert result["synced"] == 0

    def test_sync_not_registered(self, db, config):
        engine = SyncEngine(db, config)
        result = engine.sync_files()
        assert result["status"] == "skipped"


class TestSanitize:
    def test_sanitize_text_strips_control_chars(self):
        assert _sanitize_text("hello\x00world") == "helloworld"
        assert _sanitize_text("bell\x07here") == "bellhere"
        assert _sanitize_text("clean text") == "clean text"

    def test_sanitize_text_preserves_whitespace(self):
        # Tab, newline, carriage return are intentionally kept
        assert _sanitize_text("tab\there") == "tab\there"
        assert _sanitize_text("line\nhere") == "line\nhere"

    def test_sanitize_json_recursive_string(self):
        assert _sanitize_json_recursive("hello\x00world") == "helloworld"

    def test_sanitize_json_recursive_int_passthrough(self):
        assert _sanitize_json_recursive(42) == 42
        assert _sanitize_json_recursive(3.14) == 3.14

    def test_sanitize_json_recursive_list(self):
        result = _sanitize_json_recursive(["a\x00b", "c\x01d"])
        assert result == ["ab", "cd"]

    def test_sanitize_json_recursive_dict(self):
        result = _sanitize_json_recursive({"key": "val\x00ue"})
        assert result == {"key": "value"}

    def test_sanitize_json_recursive_nested(self):
        """Simulates a real content_blocks structure with null bytes."""
        data = {
            "type": "text",
            "content": "\ufffdPNG \u001a \x00\x00binary garbage",
            "metadata": {"page": 1},
            "children": [{"text": "hello\x00world"}],
        }
        result = _sanitize_json_recursive(data)
        assert "\x00" not in result["content"]
        assert result["metadata"] == {"page": 1}
        assert result["children"][0]["text"] == "helloworld"

    def test_sanitize_json_recursive_empty(self):
        assert _sanitize_json_recursive({}) == {}
        assert _sanitize_json_recursive([]) == []
        assert _sanitize_json_recursive("") == ""
