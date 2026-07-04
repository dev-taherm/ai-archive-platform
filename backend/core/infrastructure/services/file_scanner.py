from __future__ import annotations

import fnmatch
import hashlib
import logging
import mimetypes
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable

from core.application.interfaces.services import FileScanner

logger = logging.getLogger(__name__)

DEFAULT_IGNORE_PATTERNS: list[str] = [
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "node_modules",
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
    "*.swp",
    "*.swo",
    "*~",
]


class FileScannerService(FileScanner):
    """Local filesystem implementation of FileScanner ABC.

    Supports folder scanning with fingerprinting and real-time
    filesystem monitoring via watchdog.
    """

    def __init__(self) -> None:
        self._watching: dict[str, bool] = {}
        self._callbacks: dict[str, Callable | None] = {}
        self._observers: dict[str, Any] = {}

    def _should_ignore(self, name: str, ignore_patterns: list[str]) -> bool:
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _matches_patterns(self, name: str, patterns: list[str] | None) -> bool:
        if not patterns:
            return True
        return any(fnmatch.fnmatch(name, p) for p in patterns)

    def _compute_fingerprint(self, filepath: str) -> dict[str, str]:
        sha256 = hashlib.sha256()
        magic_bytes = b""
        with open(filepath, "rb") as f:
            first_chunk = True
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256.update(chunk)
                if first_chunk:
                    magic_bytes = chunk[:16]
                    first_chunk = False

        magic_hex = magic_bytes.hex()[:32]
        mime_type, _ = mimetypes.guess_type(filepath)

        return {
            "content_hash": f"sha256:{sha256.hexdigest()}",
            "magic_bytes": magic_hex,
            "mime_type": mime_type or "application/octet-stream",
        }

    def scan_folder(
        self,
        path: str,
        *,
        recursive: bool = True,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        root = Path(path).resolve()
        if not root.exists():
            logger.warning("Scan target does not exist: %s", path)
            return
        if not root.is_dir():
            logger.warning("Scan target is not a directory: %s", path)
            return

        effective_ignore = list(DEFAULT_IGNORE_PATTERNS)
        if ignore_patterns:
            effective_ignore.extend(ignore_patterns)

        if recursive:
            entries = sorted(root.rglob("*"), key=lambda p: (p.is_file(), p.name))
        else:
            entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))

        for entry in entries:
            if entry.name in effective_ignore or self._should_ignore(
                entry.name, effective_ignore
            ):
                continue

            if entry.is_dir():
                if not recursive:
                    continue
                continue

            if not self._matches_patterns(entry.name, patterns):
                continue

            stat = entry.stat()
            fingerprint = self._compute_fingerprint(str(entry))

            yield {
                "path": str(entry),
                "relative_path": str(entry.relative_to(root)),
                "filename": entry.name,
                "extension": entry.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
                "created_at": stat.st_ctime,
                "is_file": True,
                "is_symlink": entry.is_symlink(),
                "content_hash": fingerprint["content_hash"],
                "magic_bytes": fingerprint["magic_bytes"],
                "mime_type": fingerprint["mime_type"],
            }

    def watch_folder(
        self,
        path: str,
        *,
        recursive: bool = True,
        callback: Callable | None = None,
    ) -> None:
        """Begin watching a folder for changes using watchdog.

        Calls the callback with (event_type, path) tuples when files change.
        """
        resolved = str(Path(path).resolve())
        self._watching[resolved] = True
        self._callbacks[resolved] = callback

        try:
            from watchdog.events import FileSystemEvent, FileSystemEventHandler
            from watchdog.observers import Observer

            class _ArchiveEventHandler(FileSystemEventHandler):
                """Routes watchdog events to the registered callback."""

                def __init__(self, cb: Callable | None) -> None:
                    super().__init__()
                    self._cb = cb

                def on_created(self, event: FileSystemEvent) -> None:
                    if not event.is_directory and self._cb:
                        self._cb("created", event.src_path)

                def on_modified(self, event: FileSystemEvent) -> None:
                    if not event.is_directory and self._cb:
                        self._cb("modified", event.src_path)

                def on_deleted(self, event: FileSystemEvent) -> None:
                    if not event.is_directory and self._cb:
                        self._cb("deleted", event.src_path)

                def on_moved(self, event: FileSystemEvent) -> None:
                    if not event.is_directory and self._cb:
                        self._cb("moved", event.src_path)

            handler = _ArchiveEventHandler(callback)
            observer = Observer()
            observer.schedule(handler, resolved, recursive=recursive)
            observer.daemon = True
            observer.start()
            self._observers[resolved] = observer
            logger.info("Started watching folder: %s", resolved)
        except ImportError:
            logger.warning(
                "watchdog not installed — folder watching disabled. "
                "Install with: pip install watchdog"
            )
        except Exception:
            logger.exception("Failed to start watching folder: %s", resolved)

    def stop_watching(self, path: str) -> None:
        """Stop watching a folder for changes."""
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
        logger.info("Stopped watching folder: %s", resolved)

    def is_watching(self, path: str) -> bool:
        resolved = str(Path(path).resolve())
        return self._watching.get(resolved, False)
