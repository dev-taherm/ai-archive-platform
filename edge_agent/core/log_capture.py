from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any


class RingBufferLogHandler(logging.Handler):
    def __init__(self, capacity: int = 1000) -> None:
        super().__init__()
        self.capacity = capacity
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self.format(record),
        }
        with self._lock:
            if len(self._buffer) >= self.capacity:
                self._buffer.pop(0)
            self._buffer.append(entry)

    def get_records(
        self,
        level: str | None = None,
        limit: int = 50,
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        min_level = levels.get(level.upper(), 0) if level else 0

        with self._lock:
            results = [
                r
                for r in self._buffer
                if (not level or levels.get(r["level"], 0) >= min_level)
                and (not since or r["timestamp"] >= since)
            ]
        return results[-limit:]
