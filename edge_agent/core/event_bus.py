"""Simple thread-safe event bus for WebSocket push."""

from __future__ import annotations

import threading
import time
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def publish(self, event: dict[str, Any]) -> None:
        event["_timestamp"] = time.time()
        with self._lock:
            self._events.append(event)

    def drain(
        self, since: float = 0.0, max_events: int = 100
    ) -> list[dict[str, Any]]:
        with self._lock:
            if since > 0:
                self._events[:] = [e for e in self._events if e["_timestamp"] <= since]
                result = [e for e in self._events if e["_timestamp"] > since]
            else:
                result = list(self._events)
                self._events.clear()
        return result[-max_events:]
