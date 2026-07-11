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
