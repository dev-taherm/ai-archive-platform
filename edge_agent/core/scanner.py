"""File scanner — fingerprinting and folder scanning.

Standalone extraction from core/infrastructure/services/file_scanner.py.
No Django dependencies.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import mimetypes
from collections.abc import Iterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_IGNORE_PATTERNS: list[str] = [
    ".git", ".svn", ".hg", "__pycache__", "node_modules",
    ".DS_Store", "Thumbs.db", "*.pyc", "*.pyo", "*.swp",
    "*.swo", "*~",
]


class FileScanner:
    """Local filesystem scanner with fingerprinting."""

    def __init__(self, ignore_patterns: list[str] | None = None, max_file_size_mb: int = 100) -> None:
        self._ignore_patterns = ignore_patterns or DEFAULT_IGNORE_PATTERNS
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def _should_ignore(self, name: str) -> bool:
        return any(fnmatch.fnmatch(name, p) for p in self._ignore_patterns)

    def _matches_patterns(self, name: str, patterns: list[str] | None) -> bool:
        if not patterns:
            return True
        return any(fnmatch.fnmatch(name, p) for p in patterns)

    def compute_fingerprint(self, filepath: str) -> dict[str, str]:
        """Compute SHA-256 hash + magic bytes + MIME type for a file."""
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
        """Scan a folder and yield file metadata dicts."""
        root = Path(path).resolve()
        if not root.exists():
            logger.warning("Scan target does not exist: %s", path)
            return
        if not root.is_dir():
            logger.warning("Scan target is not a directory: %s", path)
            return

        effective_ignore = list(self._ignore_patterns)
        if ignore_patterns:
            effective_ignore.extend(ignore_patterns)

        if recursive:
            entries = sorted(root.rglob("*"), key=lambda p: (p.is_file(), p.name))
        else:
            entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))

        for entry in entries:
            if self._should_ignore(entry.name):
                continue

            if entry.is_file():
                rel_parts = entry.relative_to(root).parts
                if any(self._should_ignore(part) for part in rel_parts[:-1]):
                    continue

            if entry.is_dir():
                if not recursive:
                    continue
                continue

            if not self._matches_patterns(entry.name, patterns):
                continue

            stat = entry.stat()

            if stat.st_size > self._max_file_size_bytes:
                logger.debug("Skipping large file: %s (%d bytes)", entry, stat.st_size)
                continue

            if stat.st_size == 0:
                continue

            fingerprint = self.compute_fingerprint(str(entry))

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

    def scan_single(self, file_path: str) -> dict[str, Any] | None:
        """Scan a single file and return its metadata."""
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return None

        stat = path.stat()
        if stat.st_size > self._max_file_size_bytes or stat.st_size == 0:
            return None

        fingerprint = self.compute_fingerprint(str(path))

        return {
            "path": str(path),
            "relative_path": path.name,
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_at": stat.st_mtime,
            "created_at": stat.st_ctime,
            "is_file": True,
            "is_symlink": path.is_symlink(),
            "content_hash": fingerprint["content_hash"],
            "magic_bytes": fingerprint["magic_bytes"],
            "mime_type": fingerprint["mime_type"],
        }
