from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

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
            job_id = self.job_queue.create_job("scan_file", {"file_id": meta["id"]})
            logger.debug("Enqueued scan for %s", fpath)
            if self.event_bus:
                self.event_bus.publish({
                    "type": "file_created",
                    "local_path": fpath,
                    "file_id": meta["id"],
                    "job_id": job_id,
                })

    def _check_deleted(self) -> None:
        with self._lock:
            gone = [p for p in self._known if not os.path.exists(p)]
            for path in gone:
                del self._known[path]
        for path in gone:
            self.db.conn.execute("DELETE FROM files WHERE local_path=?", (path,))
            self.db.conn.commit()
            logger.debug("Removed deleted file record: %s", path)
            if self.event_bus:
                self.event_bus.publish({
                    "type": "file_deleted",
                    "local_path": path,
                })

    def _loop(self) -> None:
        while self._running:
            try:
                self._check_deleted()
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
                                if self.event_bus:
                                    self.event_bus.publish({
                                        "type": "file_modified",
                                        "local_path": full,
                                    })
                            self._upsert_and_enqueue(full)
            except Exception:
                logger.exception("Watcher loop error")
            time.sleep(self.debounce_seconds)
