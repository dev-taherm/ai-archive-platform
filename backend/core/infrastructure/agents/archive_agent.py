from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from core.infrastructure.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ArchiveAgent(BaseAgent):
    """Agent responsible for archive retention policies and lifecycle management.

    Supported actions:
        - apply_retention:   Move or delete files older than a retention period.
        - archive_old:       Move old files to an archive directory.
        - get_stats:         Return archive statistics for a directory.
        - purge_expired:     Permanently delete files past their retention window.
    """

    def __init__(self) -> None:
        super().__init__(name="ArchiveAgent")

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if not action:
            return self._error("Missing required field: action")

        try:
            if action == "apply_retention":
                return await self._apply_retention(task)
            if action == "archive_old":
                return await self._archive_old(task)
            if action == "get_stats":
                return await self._get_stats(task)
            if action == "purge_expired":
                return await self._purge_expired(task)
            return self._error(f"Unknown action: {action}")
        except Exception as exc:
            logger.exception("ArchiveAgent action=%s failed", action)
            return self._error(str(exc))

    # ── helpers ───────────────────────────────────────────────────
    @staticmethod
    def _is_old_enough(mtime: float, days: int) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        file_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        return file_dt < cutoff

    # ── actions ───────────────────────────────────────────────────
    async def _apply_retention(self, task: dict[str, Any]) -> dict[str, Any]:
        directory = task.get("directory")
        if not directory:
            return self._error("directory is required for apply_retention")

        retention_days = task.get("retention_days", 90)
        archive_dir = task.get("archive_dir")
        dry_run = task.get("dry_run", True)

        root = Path(directory)
        if not root.is_dir():
            return self._error(f"Not a directory: {directory}")

        moved = 0
        kept = 0
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            if not self._is_old_enough(entry.stat().st_mtime, retention_days):
                kept += 1
                continue

            if archive_dir:
                target = Path(archive_dir) / entry.relative_to(root)
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(entry), str(target))
                moved += 1
            elif not dry_run:
                entry.unlink()
                moved += 1

        logger.info(
            "Retention policy applied: %d moved/deleted, %d kept (dry_run=%s)",
            moved,
            kept,
            dry_run,
        )
        return self._ok(
            data={"moved": moved, "kept": kept, "retention_days": retention_days, "dry_run": dry_run},
            message=f"Retention applied: {moved} files processed, {kept} kept",
        )

    async def _archive_old(self, task: dict[str, Any]) -> dict[str, Any]:
        directory = task.get("directory")
        archive_dir = task.get("archive_dir")
        if not directory or not archive_dir:
            return self._error("directory and archive_dir are required for archive_old")

        days = task.get("days", 30)
        dry_run = task.get("dry_run", True)
        root = Path(directory)
        archive_root = Path(archive_dir)

        if not root.is_dir():
            return self._error(f"Not a directory: {directory}")

        moved = 0
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            if not self._is_old_enough(entry.stat().st_mtime, days):
                continue

            target = archive_root / entry.relative_to(root)
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(entry), str(target))
            moved += 1

        logger.info("Archived %d files older than %d days (dry_run=%s)", moved, days, dry_run)
        return self._ok(
            data={"archived": moved, "days": days, "dry_run": dry_run},
            message=f"Archived {moved} files older than {days} days",
        )

    async def _get_stats(self, task: dict[str, Any]) -> dict[str, Any]:
        directory = task.get("directory")
        if not directory:
            return self._error("directory is required for get_stats")

        root = Path(directory)
        if not root.is_dir():
            return self._error(f"Not a directory: {directory}")

        total_files = 0
        total_size = 0
        oldest_mtime: float | None = None
        newest_mtime: float | None = None
        ext_counts: dict[str, int] = {}

        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            total_files += 1
            stat = entry.stat()
            total_size += stat.st_size
            ext = entry.suffix.lower() or "(no ext)"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

            if oldest_mtime is None or stat.st_mtime < oldest_mtime:
                oldest_mtime = stat.st_mtime
            if newest_mtime is None or stat.st_mtime > newest_mtime:
                newest_mtime = stat.st_mtime

        return self._ok(
            data={
                "directory": directory,
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_file": datetime.fromtimestamp(oldest_mtime, tz=timezone.utc).isoformat() if oldest_mtime else None,
                "newest_file": datetime.fromtimestamp(newest_mtime, tz=timezone.utc).isoformat() if newest_mtime else None,
                "extension_breakdown": ext_counts,
            },
            message=f"Stats for {directory}: {total_files} files, {total_size / (1024*1024):.1f} MB",
        )

    async def _purge_expired(self, task: dict[str, Any]) -> dict[str, Any]:
        directory = task.get("directory")
        if not directory:
            return self._error("directory is required for purge_expired")

        max_age_days = task.get("max_age_days", 365)
        dry_run = task.get("dry_run", True)
        root = Path(directory)
        if not root.is_dir():
            return self._error(f"Not a directory: {directory}")

        deleted = 0
        kept = 0
        for entry in root.rglob("*"):
            if not entry.is_file():
                continue
            if self._is_old_enough(entry.stat().st_mtime, max_age_days):
                if not dry_run:
                    entry.unlink()
                deleted += 1
            else:
                kept += 1

        logger.info("Purged %d expired files (dry_run=%s)", deleted, dry_run)
        return self._ok(
            data={"deleted": deleted, "kept": kept, "max_age_days": max_age_days, "dry_run": dry_run},
            message=f"Purged {deleted} expired files (>{max_age_days} days)",
        )
