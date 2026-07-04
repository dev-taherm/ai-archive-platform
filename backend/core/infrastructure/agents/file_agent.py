from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

from core.infrastructure.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class FileAgent(BaseAgent):
    """Agent responsible for file system operations.

    Supported actions:
        - move:       Move files to a destination directory.
        - rename:     Rename a file using a pattern.
        - organize:   Organize files into subdirectories by type/extension.
        - delete_duplicates: Remove duplicate files based on content hash.
    """

    def __init__(self) -> None:
        super().__init__(name="FileAgent")

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if not action:
            return self._error("Missing required field: action")

        try:
            if action == "move":
                return await self._move(task)
            if action == "rename":
                return await self._rename(task)
            if action == "organize":
                return await self._organize(task)
            if action == "delete_duplicates":
                return await self._delete_duplicates(task)
            return self._error(f"Unknown action: {action}")
        except Exception as exc:
            logger.exception("FileAgent action=%s failed", action)
            return self._error(str(exc))

    # ── move ──────────────────────────────────────────────────────
    async def _move(self, task: dict[str, Any]) -> dict[str, Any]:
        src = task.get("source")
        dest = task.get("destination")
        if not src or not dest:
            return self._error("source and destination are required for move")

        src_path = Path(src)
        dest_path = Path(dest)

        if not src_path.exists():
            return self._error(f"Source not found: {src}")

        dest_path.mkdir(parents=True, exist_ok=True)
        target = dest_path / src_path.name

        if target.exists() and not task.get("overwrite", False):
            return self._error(f"Destination already exists: {target}")

        shutil.move(str(src_path), str(target))
        logger.info("Moved %s -> %s", src, target)
        return self._ok(message=f"Moved {src_path.name} to {dest_path}")

    # ── rename ────────────────────────────────────────────────────
    async def _rename(self, task: dict[str, Any]) -> dict[str, Any]:
        src = task.get("source")
        new_name = task.get("new_name")
        if not src or not new_name:
            return self._error("source and new_name are required for rename")

        src_path = Path(src)
        if not src_path.exists():
            return self._error(f"Source not found: {src}")

        target = src_path.parent / new_name
        if target.exists():
            return self._error(f"Target already exists: {target}")

        src_path.rename(target)
        logger.info("Renamed %s -> %s", src, target)
        return self._ok(message=f"Renamed to {new_name}")

    # ── organize ──────────────────────────────────────────────────
    async def _organize(self, task: dict[str, Any]) -> dict[str, Any]:
        directory = task.get("directory")
        if not directory:
            return self._error("directory is required for organize")

        root = Path(directory)
        if not root.is_dir():
            return self._error(f"Not a directory: {directory}")

        ext_map: dict[str, str] = {
            ".pdf": "Documents/PDFs",
            ".txt": "Documents/Text",
            ".md": "Documents/Text",
            ".doc": "Documents/Word",
            ".docx": "Documents/Word",
            ".xls": "Documents/Spreadsheets",
            ".xlsx": "Documents/Spreadsheets",
            ".csv": "Documents/Spreadsheets",
            ".png": "Images",
            ".jpg": "Images",
            ".jpeg": "Images",
            ".gif": "Images",
            ".svg": "Images",
            ".webp": "Images",
            ".mp4": "Media/Video",
            ".mkv": "Media/Video",
            ".avi": "Media/Video",
            ".mp3": "Media/Audio",
            ".wav": "Media/Audio",
            ".flac": "Media/Audio",
            ".zip": "Archives",
            ".tar": "Archives",
            ".gz": "Archives",
            ".rar": "Archives",
            ".py": "Code",
            ".js": "Code",
            ".ts": "Code",
            ".java": "Code",
            ".go": "Code",
            ".rs": "Code",
        }

        moved = 0
        skipped = 0
        for entry in root.iterdir():
            if entry.is_dir():
                continue
            category = ext_map.get(entry.suffix.lower(), "Other")
            target_dir = root / category
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / entry.name
            if target.exists():
                skipped += 1
                continue
            shutil.move(str(entry), str(target))
            moved += 1

        logger.info("Organized %d files (%d skipped) in %s", moved, skipped, directory)
        return self._ok(
            data={"moved": moved, "skipped": skipped},
            message=f"Organized {moved} files in {directory}",
        )

    # ── delete_duplicates ─────────────────────────────────────────
    async def _delete_duplicates(self, task: dict[str, Any]) -> dict[str, Any]:
        directory = task.get("directory")
        if not directory:
            return self._error("directory is required for delete_duplicates")

        root = Path(directory)
        if not root.is_dir():
            return self._error(f"Not a directory: {directory}")

        dry_run = task.get("dry_run", True)
        hash_groups: dict[str, list[Path]] = {}

        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            try:
                h = hashlib.sha256(entry.read_bytes()).hexdigest()
                hash_groups.setdefault(h, []).append(entry)
            except OSError:
                continue

        deleted = 0
        kept = 0
        duplicates: list[dict[str, Any]] = []

        for group in hash_groups.values():
            if len(group) < 2:
                continue
            original = group[0]
            for dup in group[1:]:
                if not dry_run:
                    dup.unlink()
                    deleted += 1
                duplicates.append(
                    {"original": str(original), "duplicate": str(dup)}
                )
            kept += 1

        logger.info(
            "Duplicate detection: %d duplicates found, %d deleted (dry_run=%s)",
            len(duplicates),
            deleted,
            dry_run,
        )
        return self._ok(
            data={
                "total_groups": kept,
                "duplicates": duplicates,
                "deleted": deleted,
                "dry_run": dry_run,
            },
            message=f"Found {len(duplicates)} duplicates, deleted {deleted}",
        )
