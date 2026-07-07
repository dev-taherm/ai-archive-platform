"""Tests for edge_agent.watcher.monitor — FolderWatcher."""
import time
import tempfile
from pathlib import Path

import pytest

from edge_agent.watcher.monitor import FolderWatcher


class TestFolderWatcher:
    def test_init(self):
        watcher = FolderWatcher(debounce_seconds=0.1)
        assert watcher.watched_paths == []

    def test_is_watching_unknown_path(self):
        watcher = FolderWatcher()
        assert watcher.is_watching("/nonexistent/path") is False

    def test_stop_all_empty(self):
        watcher = FolderWatcher()
        watcher.stop_all()  # Should not raise

    def test_watched_paths_empty(self):
        watcher = FolderWatcher()
        assert watcher.watched_paths == []

    def test_watch_and_stop(self, tmp_path):
        d = tmp_path / "watch_dir"
        d.mkdir()
        events = []
        watcher = FolderWatcher(debounce_seconds=0.05)
        watcher.watch(str(d), recursive=False, callback=lambda et, p: events.append((et, p)))
        assert watcher.is_watching(str(d))
        assert str(d) in watcher.watched_paths

        watcher.stop(str(d))
        assert not watcher.is_watching(str(d))

    def test_stop_all_clears(self, tmp_path):
        d1 = tmp_path / "dir1"
        d2 = tmp_path / "dir2"
        d1.mkdir()
        d2.mkdir()
        watcher = FolderWatcher(debounce_seconds=0.05)
        watcher.watch(str(d1))
        watcher.watch(str(d2))
        assert len(watcher.watched_paths) == 2
        watcher.stop_all()
        assert len(watcher.watched_paths) == 0

    def test_debounce_suppresses(self, tmp_path):
        d = tmp_path / "debounce_dir"
        d.mkdir()
        events = []
        watcher = FolderWatcher(debounce_seconds=10.0)  # Long debounce
        watcher.watch(str(d), callback=lambda et, p: events.append((et, p)))

        # Create a file twice quickly
        (d / "test.txt").write_text("first")
        time.sleep(0.01)
        (d / "test.txt").write_text("second")

        time.sleep(0.1)  # Let watchdog process
        watcher.stop(str(d))
        # Due to debounce, should only see one event per unique path
