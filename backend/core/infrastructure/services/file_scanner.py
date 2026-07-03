from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from core.application.interfaces.services import FileScanner

logger = logging.getLogger(__name__)

# Default patterns to ignore
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

    Recursively scans directories, computes file metadata and fingerprints,
    and supports optional glob-based filtering.
    """

    def __init__(self) -> None:
        self._watching: dict[str, bool] = {}
        self._callbacks: dict[str, Callable | None] = {}

    def _should_ignore(self, name: str, ignore_patterns: list[str]) -> bool:
        """Check if a filename or directory name matches any ignore pattern."""
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _matches_patterns(self, name: str, patterns: list[str] | None) -> bool:
        """Check if a filename matches any of the include patterns."""
        if not patterns:
            return True
        return any(fnmatch.fnmatch(name, p) for p in patterns)

    def _compute_fingerprint(self, filepath: str) -> dict[str, str]:
        """Compute a SHA-256 content hash and detect magic bytes."""
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

    async def scan_folder(
        self,
        path: str,
        *,
        recursive: bool = True,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Scan a folder and yield file metadata for each discovered file."""
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

        loop = asyncio.get_event_loop()

        if recursive:
            entries = await loop.run_in_executor(
                None,
                lambda: sorted(root.rglob("*"), key=lambda p: (p.is_file(), p.name)),
            )
        else:
            entries = await loop.run_in_executor(
                None,
                lambda: sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name)),
            )

        for entry in entries:
            if entry.name in effective_ignore or self._should_ignore(entry.name, effective_ignore):
                continue

            # Skip directories in non-recursive mode or if entry is a dir
            if entry.is_dir():
                if not recursive:
                    continue
                continue  # skip directories in recursive mode too

            if not self._matches_patterns(entry.name, patterns):
                continue

            stat = await loop.run_in_executor(None, entry.stat)
            fingerprint = await loop.run_in_executor(
                None, self._compute_fingerprint, str(entry)
            )

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

    async def watch_folder(
        self,
        path: str,
        *,
        recursive: bool = True,
        callback: Callable | None = None,
    ) -> None:
        """Begin watching a folder for changes.

        NOTE: This is a simplified polling-based watcher. For production,
        consider using watchdog (pip install watchdog) for OS-native events.
        """
        resolved = str(Path(path).resolve())
        self._watching[resolved] = True
        self._callbacks[resolved] = callback
        logger.info("Started watching folder: %s", resolved)

        # In a real implementation this would start an event loop or thread
        # that monitors the directory for file system events and invokes
        # the callback with (event_type, filepath) tuples.

    async def stop_watching(self, path: str) -> None:
        resolved = str(Path(path).resolve())
        self._watching.pop(resolved, None)
        self._callbacks.pop(resolved, None)
        logger.info("Stopped watching folder: %s", resolved)

    def is_watching(self, path: str) -> bool:
        resolved = str(Path(path).resolve())
        return self._watching.get(resolved, False)
