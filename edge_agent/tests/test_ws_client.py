"""Tests for edge_agent.core.ws_client — SaaS WebSocket client."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from edge_agent.core.ws_client import SaaSWebSocketClient


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.count_completed_files.return_value = 42
    db.get_job_stats.return_value = {"pending_jobs": 0, "total_jobs": 5}
    db.get_config.return_value = {
        "server_url": "http://localhost:8000",
        "agent_id": "test-agent",
        "api_key": "ak_test123",
        "watched_folders": ["/home/user/docs"],
    }
    db.get_pending_sync.return_value = []
    return db


@pytest.fixture
def mock_sync_engine(mock_db):
    engine = MagicMock()
    engine.get_credentials.return_value = {
        "server_url": "http://localhost:8000",
        "agent_id": "test-agent",
        "api_key": "ak_test123",
    }
    return engine


@pytest.fixture
def ws_client(mock_db, mock_sync_engine):
    return SaaSWebSocketClient(
        db=mock_db,
        sync_engine=mock_sync_engine,
        event_bus=None,
        command_handler=None,
    )


class TestSaaSWebSocketClient:
    def test_init(self, ws_client):
        assert not ws_client._connected
        assert ws_client._ws is None
        assert ws_client._last_heartbeat == 0.0
        assert ws_client._last_sync == 0.0
        assert not ws_client._running

    def test_is_connected_default(self, ws_client):
        assert ws_client.is_connected is False

    def test_start_stop(self, ws_client):
        ws_client.start()
        assert ws_client._running is True
        assert ws_client._thread is not None
        ws_client.stop()
        assert ws_client._running is False

    def test_not_registered_skips_connection(self, ws_client):
        ws_client._sync_engine.get_credentials.return_value = {
            "server_url": "",
            "agent_id": "",
            "api_key": "",
        }
        ws_client._running = True
        # _run_connection should sleep and return without connecting
        import asyncio
        asyncio.get_event_loop().run_until_complete(ws_client._run_connection())
        assert ws_client._connected is False

    @pytest.mark.asyncio
    async def test_handle_message_heartbeat_ack(self, ws_client):
        ws_client._command_handler = MagicMock()
        msg = json.dumps({
            "type": "heartbeat_ack",
            "status": "ok",
            "pending_commands": [
                {"command_id": "cmd-1", "command_type": "restart", "payload": {}}
            ],
        })
        await ws_client._handle_message(msg)
        ws_client._command_handler.assert_called_once_with("restart", {})

    @pytest.mark.asyncio
    async def test_handle_message_sync_ack(self, ws_client):
        msg = json.dumps({
            "type": "sync_ack",
            "accepted": 5,
            "rejected": 1,
            "document_ids": ["doc-1", "doc-2"],
        })
        # Should not raise
        await ws_client._handle_message(msg)

    @pytest.mark.asyncio
    async def test_handle_message_command(self, ws_client):
        ws_client._send_command_result = AsyncMock()
        msg = json.dumps({
            "type": "command",
            "command_id": "cmd-2",
            "command_type": "config_update",
            "payload": {"max_file_size_mb": 200},
        })
        await ws_client._handle_message(msg)
        ws_client._db.set_config.assert_called_with("max_file_size_mb", "200")

    @pytest.mark.asyncio
    async def test_handle_message_config_update(self, ws_client):
        msg = json.dumps({
            "type": "config_update",
            "config": {"ocr_lang": "ar"},
        })
        await ws_client._handle_message(msg)
        ws_client._db.set_config.assert_called_with("ocr_lang", "ar")

    @pytest.mark.asyncio
    async def test_handle_message_ping(self, ws_client):
        ws_client._ws = AsyncMock()
        msg = json.dumps({"type": "ping"})
        await ws_client._handle_message(msg)
        ws_client._ws.send.assert_called_once_with(json.dumps({"type": "pong"}))

    @pytest.mark.asyncio
    async def test_handle_message_error(self, ws_client):
        msg = json.dumps({"type": "error", "message": "Something went wrong"})
        # Should not raise
        await ws_client._handle_message(msg)

    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self, ws_client):
        # Should not raise
        await ws_client._handle_message("not json {{{")

    @pytest.mark.asyncio
    async def test_handle_command_restart(self, ws_client):
        handler = MagicMock()
        ws_client._command_handler = handler
        ws_client._send_command_result = AsyncMock()

        cmd = {"command_id": "c1", "command_type": "restart", "payload": {}}
        await ws_client._handle_command(cmd)
        handler.assert_called_once_with("restart", {})

    @pytest.mark.asyncio
    async def test_handle_command_shutdown(self, ws_client):
        handler = MagicMock()
        ws_client._command_handler = handler
        ws_client._send_command_result = AsyncMock()

        cmd = {"command_id": "c2", "command_type": "shutdown", "payload": {}}
        await ws_client._handle_command(cmd)
        handler.assert_called_once_with("shutdown", {})

    @pytest.mark.asyncio
    async def test_handle_command_sync(self, ws_client):
        ws_client._send_command_result = AsyncMock()
        cmd = {"command_id": "c3", "command_type": "sync", "payload": {}}
        await ws_client._handle_command(cmd)
        ws_client._sync_engine.sync_files.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_scan(self, ws_client):
        ws_client._send_command_result = AsyncMock()
        cmd = {"command_id": "c4", "command_type": "scan", "payload": {"file_id": "f1"}}
        with patch("edge_agent.core.ws_client.SaaSWebSocketClient._queue_scan") as mock_queue:
            await ws_client._handle_command(cmd)
            mock_queue.assert_called_once_with("f1")

    @pytest.mark.asyncio
    async def test_handle_command_scan_no_file_id(self, ws_client):
        ws_client._send_command_result = AsyncMock()
        cmd = {"command_id": "c5", "command_type": "scan", "payload": {}}
        await ws_client._handle_command(cmd)
        # Should send failed result
        ws_client._send_command_result.assert_called_once()
        result = ws_client._send_command_result.call_args[0][1]
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_handle_command_unknown(self, ws_client):
        ws_client._send_command_result = AsyncMock()
        cmd = {"command_id": "c6", "command_type": "nonexistent", "payload": {}}
        await ws_client._handle_command(cmd)
        result = ws_client._send_command_result.call_args[0][1]
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_send_heartbeat_payload(self, ws_client):
        ws_client._ws = AsyncMock()
        ws_client._connected = True
        ws_client._start_time = 1000.0

        with patch("time.time", return_value=2000.0):
            await ws_client._send_heartbeat()

        ws_client._ws.send.assert_called_once()
        sent = json.loads(ws_client._ws.send.call_args[0][0])
        assert sent["type"] == "heartbeat"
        assert sent["status"] == "online"
        assert sent["files_count"] == 42
        assert sent["uptime_seconds"] == 1000

    @pytest.mark.asyncio
    async def test_send_heartbeat_skipped_when_disconnected(self, ws_client):
        ws_client._connected = False
        ws_client._ws = AsyncMock()
        await ws_client._send_heartbeat()
        ws_client._ws.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_sync_marks_synced(self, ws_client):
        ws_client._db.get_pending_sync.return_value = [
            {
                "local_path": "/tmp/test.txt",
                "file_hash": "abc123",
                "size_bytes": 100,
                "mime_type": "text/plain",
                "modified_at": 1000.0,
                "extracted_text": "hello world",
                "markdown": "hello world",
                "language": "en",
                "word_count": 2,
                "char_count": 11,
                "page_count": 1,
                "content_blocks": "[]",
                "tables": "[]",
                "images": "[]",
            }
        ]
        ws_client._ws = AsyncMock()
        ws_client._connected = True

        await ws_client._send_sync()

        ws_client._ws.send.assert_called_once()
        ws_client._db.mark_synced.assert_called_once_with(["abc123"])

    @pytest.mark.asyncio
    async def test_send_sync_empty_skipped(self, ws_client):
        ws_client._db.get_pending_sync.return_value = []
        ws_client._ws = AsyncMock()
        ws_client._connected = True

        await ws_client._send_sync()

        ws_client._ws.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_command_result(self, ws_client):
        ws_client._ws = AsyncMock()
        ws_client._connected = True

        await ws_client._send_command_result("cmd-1", {"status": "completed"})

        ws_client._ws.send.assert_called_once()
        sent = json.loads(ws_client._ws.send.call_args[0][0])
        assert sent["type"] == "command_result"
        assert sent["command_id"] == "cmd-1"
        assert sent["status"] == "completed"

    def test_get_monitored_folders(self, ws_client):
        folders = ws_client._get_monitored_folders()
        assert folders == ["/home/user/docs"]

    def test_get_monitored_folders_empty(self, ws_client):
        ws_client._db.get_config.return_value = {}
        folders = ws_client._get_monitored_folders()
        assert folders == []

    def test_get_monitored_folders_json_string(self, ws_client):
        ws_client._db.get_config.return_value = {
            "watched_folders": '["/tmp/a", "/tmp/b"]'
        }
        folders = ws_client._get_monitored_folders()
        assert folders == ["/tmp/a", "/tmp/b"]
