"""Tests for edge_agent.cli — CLI commands."""
import json
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.cli import main


def _run_cli(args: list[str]):
    """Run CLI with given args, capturing exit code."""
    try:
        main(args)
        return 0
    except SystemExit as e:
        return e.code


class TestCLIHealth:
    def test_health_success(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"status": "healthy"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["health"])
            assert code == 0

    def test_health_failure(self):
        with patch("urllib.request.urlopen") as mock:
            mock.side_effect = Exception("Connection refused")
            code = _run_cli(["health"])
            assert code == 1


class TestCLIStatus:
    def test_status(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"agent_name": "test"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["status"])
            assert code == 0


class TestCLIConfig:
    def test_config_get(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"key": "val"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["config", "get"])
            assert code == 0

    def test_config_set(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"status": "ok"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["config", "set", "key", "val"])
            assert code == 0


class TestCLIScan:
    def test_scan(self):
        code = _run_cli(["scan", "/tmp/test.txt"])
        assert code == 0

    def test_scan_no_path(self):
        code = _run_cli(["scan"])
        assert code != 0


class TestCLISync:
    def test_sync(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"status": "ok"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["sync"])
            assert code == 0


class TestCLIPauseResume:
    def test_pause(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"status": "paused"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["pause"])
            assert code == 0

    def test_resume(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"status": "resumed"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["resume"])
            assert code == 0


class TestCLIMetrics:
    def test_metrics(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"files_scanned": 10}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["metrics"])
            assert code == 0


class TestCLIFiles:
    def test_files(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'[]'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["files"])
            assert code == 0


class TestCLIFolders:
    def test_folders(self):
        with patch("urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.read.return_value = b'[]'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            code = _run_cli(["folders"])
            assert code == 0
