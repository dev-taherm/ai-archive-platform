"""Folder watcher — monitors directories for file changes via watchdog.

Standalone extraction from the watch_folder method in file_scanner.py.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FolderWatcher:
    """Watches folders for file system changes using watchdog."""

    def __init__(self, debounce_seconds: float = 2.0) -> None:
        self._debounce = debounce_seconds
        self._observers: dict[str, Any] = {}
        self._watching: dict[str, bool] = {}
        self._callbacks: dict[str, Callable | None] = {}
        self._pending: dict[str, float] = {}

    def watch(
        self,
        path: str,
        *,
        recursive: bool = True,
        callback: Callable | None = None,
    ) -> None:
        """Start watching a folder. Calls callback with (event_type, path) tuples."""
        resolved = str(Path(path).resolve())
        self._watching[resolved] = True
        self._callbacks[resolved] = callback

        try:
            from watchdog.events import FileSystemEvent, FileSystemEventHandler
            from watchdog.observers import Observer

            watcher = self  # capture for closure

            class _Handler(FileSystemEventHandler):
                def _debounced(self, event: FileSystemEvent) -> None:
                    if event.is_directory:
                        return
                    now = time.monotonic()
                    last = watcher._pending.get(event.src_path, 0)
                    if now - last < watcher._debounce:
                        return
                    watcher._pending[event.src_path] = now
                    cb = watcher._callbacks.get(resolved)
                    if cb:
                        cb(event.event_type, event.src_path)

                def on_created(self, event: FileSystemEvent) -> None:
                    self._debounced(event)

                def on_modified(self, event: FileSystemEvent) -> None:
                    self._debounced(event)

                def on_deleted(self, event: FileSystemEvent) -> None:
                    self._debounced(event)

                def on_moved(self, event: FileSystemEvent) -> None:
                    self._debounced(event)

            handler = _Handler()
            observer = Observer()
            observer.schedule(handler, resolved, recursive=recursive)
            observer.daemon = True
            observer.start()
            self._observers[resolved] = observer
            logger.info("Started watching: %s", resolved)
        except ImportError:
            logger.warning("watchdog not installed — folder watching disabled. pip install watchdog")
        except Exception:
            logger.exception("Failed to start watching: %s", resolved)

    def stop(self, path: str) -> None:
        resolved = str(Path(path).resolve())
        observer = self._observers.pop(resolved, None)
        if observer:
            try:
                observer.stop()
                observer.join(timeout=5)
            except Exception:
                logger.exception("Error stopping observer for %s", resolved)
        self._watching.pop(resolved, None)
        self._callbacks.pop(resolved, None)
        logger.info("Stopped watching: %s", resolved)

    def stop_all(self) -> None:
        for path in list(self._observers.keys()):
            self.stop(path)

    def is_watching(self, path: str) -> bool:
        return self._watching.get(str(Path(path).resolve()), False)

    @property
    def watched_paths(self) -> list[str]:
        return [p for p, w in self._watching.items() if w]
