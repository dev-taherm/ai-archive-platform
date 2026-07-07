"""Tests for edge_agent.cli — CLI commands and dispatch."""
import argparse
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.cli import (
    build_parser,
    cmd_extract,
    cmd_process,
    cmd_register,
    cmd_scan,
    cmd_status,
    cmd_sync,
    dispatch_commands,
)
from edge_agent.config import EdgeAgentConfig


@pytest.fixture
def config(tmp_path):
    cfg = EdgeAgentConfig(
        agent_name="test-agent",
        agent_id="agent-001",
        data_dir=str(tmp_path),
    )
    cfg.server.url = "http://localhost:9999"
    cfg.server.api_key = "test-key"
    return cfg


class TestBuildParser:
    def test_parser_has_all_commands(self):
        parser = build_parser()
        assert parser.prog == "edge-agent"
        subparsers = [a.dest for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        assert len(subparsers) == 1

    def test_parser_version(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])


class TestCmdRegister:
    @patch("edge_agent.cli.SyncManager")
    def test_register_calls_sync(self, mock_sync_cls, config):
        mock_sync = MagicMock()
        mock_sync.register.return_value = {"agent_id": "agent-001"}
        mock_sync_cls.return_value = mock_sync

        args = argparse.Namespace(jwt_token="jwt-123", name="Test Agent")
        cmd_register(args, config)
        mock_sync.register.assert_called_once_with(name="Test Agent", jwt_token="jwt-123")

    @patch("edge_agent.cli.SyncManager")
    def test_register_stores_agent_id(self, mock_sync_cls, config):
        mock_sync = MagicMock()
        mock_sync.register.return_value = {"agent_id": "new-id-123"}
        mock_sync_cls.return_value = mock_sync

        args = argparse.Namespace(jwt_token="jwt", name="Agent")
        cmd_register(args, config)
        assert config.agent_id == "new-id-123"


class TestCmdStatus:
    @patch("edge_agent.cli.LocalDB")
    def test_status_empty(self, mock_db_cls, config):
        mock_db = MagicMock()
        mock_db.get_stats.return_value = {"total": 0, "synced": 0, "pending": 0}
        mock_db.get_entity_stats.return_value = {}
        mock_db_cls.return_value = mock_db

        args = argparse.Namespace()
        cmd_status(args, config)  # Should not raise


class TestCmdSync:
    @patch("edge_agent.cli.SyncManager")
    @patch("edge_agent.cli.LocalDB")
    def test_sync_calls_sync_files(self, mock_db_cls, mock_sync_cls, config):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_sync = MagicMock()
        mock_sync.sync_files.return_value = {"accepted": 5}
        mock_sync_cls.return_value = mock_sync

        args = argparse.Namespace()
        cmd_sync(args, config)
        mock_sync.sync_files.assert_called_once()


class TestCmdExtract:
    @patch("edge_agent.cli.LLMClient")
    @patch("edge_agent.cli.LocalDB")
    def test_extract_empty_db(self, mock_db_cls, mock_llm_cls, config):
        mock_db = MagicMock()
        mock_db.get_pending_sync.return_value = []
        mock_db_cls.return_value = mock_db
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm

        args = argparse.Namespace(batch=10, force=False)
        result = cmd_extract(args, config)
        assert result["extracted"] == 0


class TestDispatchCommands:
    def test_dispatch_empty(self):
        result = dispatch_commands([], None, None, None, None, None)
        assert result == []

    def test_dispatch_shutdown(self):
        result = dispatch_commands([{"id": "c1", "command_type": "shutdown"}], None, None, None, None, None)
        assert len(result) == 1
        assert result[0]["status"] == "completed"

    def test_dispatch_unknown_command(self):
        result = dispatch_commands([{"id": "c1", "command_type": "unknown_thing"}], None, None, None, None, None)
        assert result[0]["status"] == "failed"
        assert "Unknown" in result[0]["result"]["error"]

    def test_dispatch_scan(self):
        mock_scanner = MagicMock()
        mock_scanner.scan_folder.return_value = []
        result = dispatch_commands(
            [{"id": "c1", "command_type": "scan", "payload": {"path": "/tmp"}}],
            None, mock_scanner, None, None, None,
        )
        assert result[0]["status"] == "completed"
