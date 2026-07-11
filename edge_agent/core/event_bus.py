"""Thread-safe event bus with observer pattern for WebSocket push."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

# ── Event type constants ─────────────────────────────────────────────────────

EVENT_SCAN_STARTED = "scan_started"
EVENT_SCAN_COMPLETED = "scan_completed"
EVENT_SCAN_FAILED = "scan_failed"
EVENT_FILE_CREATED = "file_created"
EVENT_FILE_DELETED = "file_deleted"
EVENT_FILE_MODIFIED = "file_modified"
EVENT_STATUS_CHANGED = "status_changed"
EVENT_METRICS_UPDATED = "metrics_updated"
EVENT_SYNC_COMPLETED = "sync_completed"

_MAX_BUFFER = 1000


class EventBus:
    """In-memory event bus with observer pattern for real-time push.

    - Thread-safe: all operations use a lock.
    - Observer pattern: ``subscribe(callback)`` / ``unsubscribe(callback)``
      for WebSocket push. Observers are called synchronously in the
      ``publish()`` call site (worker / watcher thread).
    - Cursor-based ``drain(since)`` for backward-compatible polling.
    - Ring buffer: capped at ``_MAX_BUFFER`` events.
    """

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._observers: list[Callable[[dict[str, Any]], None]] = []
        self._lock = threading.Lock()

    # ── Observer pattern ──────────────────────────────────────────────────────

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._observers.append(callback)

    def unsubscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._observers = [o for o in self._observers if o is not callback]

    # ── Publish / drain ───────────────────────────────────────────────────────

    def publish(self, event: dict[str, Any]) -> None:
        event["_timestamp"] = time.time()
        with self._lock:
            self._events.append(event)
            # Trim buffer if too large
            if len(self._events) > _MAX_BUFFER:
                self._events = self._events[-_MAX_BUFFER:]
            observers = list(self._observers)

        # Notify observers outside the lock
        for obs in observers:
            try:
                obs(event)
            except Exception:
                pass  # Don't let observer errors break publish

    def drain(
        self, since: float = 0.0, max_events: int = 100
    ) -> list[dict[str, Any]]:
        """Return events newer than *since* (cursor-based).

        When ``since == 0`` the buffer is cleared (full drain).
        When ``since > 0`` only newer events are returned; the buffer
        is **not** cleared so other consumers can still drain.
        """
        with self._lock:
            if since > 0:
                result = [e for e in self._events if e["_timestamp"] > since]
            else:
                result = list(self._events)
                self._events.clear()
        return result[-max_events:]

    def snapshot(self, max_events: int = 100) -> list[dict[str, Any]]:
        """Return recent events without clearing the buffer."""
        with self._lock:
            return list(self._events[-max_events:])
