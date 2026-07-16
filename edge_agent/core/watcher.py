from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

from edge_agent.core.event_bus import (
    EVENT_FILE_CREATED,
    EVENT_FILE_DELETED,
    EVENT_FILE_MODIFIED,
)
from edge_agent.core.job_queue import JobQueue
from edge_agent.db.local_db import LocalDB

logger = logging.getLogger(__name__)


class FolderWatcher:
    def __init__(self, db: LocalDB, debounce_seconds: float = 2.0, event_bus: Any | None = None) -> None:
        self.db = db
        self.job_queue = JobQueue(db)
        self.event_bus = event_bus
        self.debounce_seconds = debounce_seconds
        self._running = False
        self._thread: threading.Thread | None = None
        self._known: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def folder_count(self) -> int:
        return len(self.db.get_folders())

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, folders: list[str]) -> None:
        if self._running:
            return
        self._scan_and_enqueue(folders)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="watcher")
        self._thread.start()
        logger.info("Watcher started for %d folders", len(folders))

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Watcher stopped")

    # ── Event publishing helper ───────────────────────────────────────────────

    def _publish_event(self, event: dict[str, Any]) -> None:
        if self.event_bus:
            try:
                self.event_bus.publish(event)
            except Exception:
                logger.exception("Failed to publish event")

    # ── Initial scan ──────────────────────────────────────────────────────────

    def _scan_and_enqueue(self, folders: list[str]) -> None:
        from edge_agent.core.scanner import scan_single

        for folder in folders:
            if not os.path.isdir(folder):
                continue
            for root, dirs, files in os.walk(folder, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for fname in files:
                    if fname.startswith("."):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        st = os.stat(fpath)
                        mtime = st.st_mtime
                        with self._lock:
                            prev = self._known.get(fpath)
                            if prev and prev[0] == str(mtime):
                                continue
                            self._known[fpath] = (str(mtime), st.st_size)
                        self._upsert_and_enqueue(fpath)
                    except (PermissionError, OSError):
                        continue

    def _upsert_and_enqueue(self, fpath: str) -> None:
        from edge_agent.core.scanner import scan_single

        meta = scan_single(fpath)
        if not meta:
            return
        count = self.db.upsert_files([meta])
        if count > 0:
            # Use the actual stored ID (may differ from meta["id"] on re-scan)
            record = self.db.get_file_by_path(fpath)
            file_id = record["id"] if record else meta["id"]
            job_id = self.job_queue.create_job("scan_file", {"file_id": file_id})
            logger.debug("Enqueued scan for %s", fpath)
            self._publish_event({
                "type": EVENT_FILE_CREATED,
                "local_path": fpath,
                "file_id": file_id,
                "job_id": job_id,
            })

    # ── Deleted file detection ────────────────────────────────────────────────

    def _check_deleted(self) -> None:
        with self._lock:
            gone = [p for p in self._known if not os.path.exists(p)]
            for path in gone:
                del self._known[path]
        for path in gone:
            self.db.delete_files_by_path(path)
            logger.debug("Removed deleted file record: %s", path)
            self._publish_event({
                "type": EVENT_FILE_DELETED,
                "local_path": path,
            })

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._check_deleted()
                dismissed = self.db.get_dismissed_paths()
                folders = self.db.get_folders()
                for folder in folders:
                    fpath = folder["path"]
                    if not os.path.isdir(fpath):
                        continue
                    for root, dirs, files in os.walk(fpath, followlinks=False):
                        dirs[:] = [d for d in dirs if not d.startswith(".")]
                        for fname in files:
                            if fname.startswith("."):
                                continue
                            full = os.path.join(root, fname)
                            if full in dismissed:
                                continue
                            try:
                                st = os.stat(full)
                                mtime = str(st.st_mtime)
                                size = st.st_size
                            except (PermissionError, OSError):
                                continue
                            with self._lock:
                                prev = self._known.get(full)
                                if prev and prev[0] == mtime and prev[1] == size:
                                    continue
                                self._known[full] = (mtime, size)
                            if prev:
                                logger.info("Detected change: %s", full)
                                self._publish_event({
                                    "type": EVENT_FILE_MODIFIED,
                                    "local_path": full,
                                })
                            self._upsert_and_enqueue(full)
            except Exception:
                logger.exception("Watcher loop error")
            time.sleep(self.debounce_seconds)
