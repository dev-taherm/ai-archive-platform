from __future__ import annotations

import os
import threading
from typing import Any


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.files_scanned: int = 0
        self.parse_time_total_ms: float = 0.0
        self.parse_errors: int = 0
        self.sync_events: int = 0
        self.sync_files: int = 0
        self.heartbeat_count: int = 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "files_scanned": self.files_scanned,
                "parse_time_total_ms": self.parse_time_total_ms,
                "parse_errors": self.parse_errors,
                "sync_events": self.sync_events,
                "sync_files": self.sync_files,
                "heartbeat_count": self.heartbeat_count,
                "memory_mb": self._get_memory_mb(),
            }

    # ── Thread-safe increment helpers ─────────────────────────────────────────

    def increment_scanned(self) -> None:
        with self._lock:
            self.files_scanned += 1

    def add_parse_time(self, ms: float) -> None:
        with self._lock:
            self.parse_time_total_ms += ms

    def increment_errors(self) -> None:
        with self._lock:
            self.parse_errors += 1

    def increment_sync_events(self) -> None:
        with self._lock:
            self.sync_events += 1

    def increment_sync_files(self, count: int = 1) -> None:
        with self._lock:
            self.sync_files += count

    def increment_heartbeat(self) -> None:
        with self._lock:
            self.heartbeat_count += 1

    @property
    def memory_mb(self) -> float:
        return self._get_memory_mb()

    def _get_memory_mb(self) -> float:
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        kb = int(line.split()[1])
                        return round(kb / 1024, 1)
        except (FileNotFoundError, IOError, ValueError):
            pass
        return 0.0
