"""Tests for edge_agent.core.event_bus — thread-safe event bus with observer pattern."""
import threading
import time

import pytest

from edge_agent.core.event_bus import (
    EventBus,
    EVENT_SCAN_STARTED,
    EVENT_SCAN_COMPLETED,
    EVENT_SCAN_FAILED,
    EVENT_FILE_CREATED,
    EVENT_FILE_DELETED,
    EVENT_FILE_MODIFIED,
    EVENT_STATUS_CHANGED,
    EVENT_METRICS_UPDATED,
    EVENT_SYNC_COMPLETED,
    _MAX_BUFFER,
)


class TestEventBus:
    """Tests for the EventBus class."""

    def test_publish_adds_timestamp(self):
        bus = EventBus()
        bus.publish({"type": "test"})
        events = bus.drain(since=0)
        assert len(events) == 1
        assert "_timestamp" in events[0]
        assert events[0]["type"] == "test"

    def test_subscribe_receives_events(self):
        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))
        bus.publish({"type": "ping"})
        assert len(received) == 1
        assert received[0]["type"] == "ping"

    def test_unsubscribe_stops_events(self):
        bus = EventBus()
        received = []
        cb = lambda e: received.append(e)
        bus.subscribe(cb)
        bus.publish({"type": "first"})
        assert len(received) == 1

        bus.unsubscribe(cb)
        bus.publish({"type": "second"})
        assert len(received) == 1  # no new event received

    def test_drain_returns_since_cursor(self):
        bus = EventBus()
        t0 = time.time()
        bus.publish({"type": "a"})
        time.sleep(0.05)
        t1 = time.time()
        bus.publish({"type": "b"})

        # Drain only events after t1
        events = bus.drain(since=t1)
        assert len(events) == 1
        assert events[0]["type"] == "b"

    def test_drain_clears_buffer_when_zero(self):
        bus = EventBus()
        bus.publish({"type": "a"})
        bus.publish({"type": "b"})
        bus.drain(since=0)
        # Buffer should be empty now
        remaining = bus.drain(since=0)
        assert len(remaining) == 0

    def test_drain_preserves_buffer_when_cursor(self):
        bus = EventBus()
        bus.publish({"type": "a"})
        time.sleep(0.05)
        t0 = time.time()
        bus.publish({"type": "b"})

        # Drain with cursor — returns events after t0, buffer unchanged
        events = bus.drain(since=t0, max_events=100)
        assert len(events) == 1
        assert events[0]["type"] == "b"

        # Full drain clears buffer — should still have 'a' and 'b'
        remaining = bus.drain(since=0, max_events=100)
        assert len(remaining) == 2

    def test_snapshot_does_not_clear(self):
        bus = EventBus()
        bus.publish({"type": "a"})
        bus.publish({"type": "b"})

        snap = bus.snapshot()
        assert len(snap) == 2

        # Buffer still has events
        remaining = bus.drain(since=0)
        assert len(remaining) == 2

    def test_ring_buffer_cap(self):
        bus = EventBus()
        for i in range(_MAX_BUFFER + 100):
            bus.publish({"type": "event", "i": i})

        events = bus.drain(since=0, max_events=_MAX_BUFFER + 200)
        assert len(events) == _MAX_BUFFER
        # Oldest events should have been evicted
        assert events[0]["i"] == 100

    def test_publish_thread_safety(self):
        bus = EventBus()
        errors = []

        def publisher(n):
            try:
                for i in range(50):
                    bus.publish({"type": "thread_event", "thread": n, "i": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=publisher, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == []
        events = bus.drain(since=0, max_events=1000)
        assert len(events) == 500  # 10 threads * 50 events

    def test_observer_error_doesnt_break_publish(self):
        bus = EventBus()
        good_received = []

        def bad_observer(e):
            raise RuntimeError("I always fail")

        def good_observer(e):
            good_received.append(e)

        bus.subscribe(bad_observer)
        bus.subscribe(good_observer)
        bus.publish({"type": "test"})

        assert len(good_received) == 1  # good observer still fires

    def test_multiple_observers(self):
        bus = EventBus()
        results = {"a": [], "b": [], "c": []}

        bus.subscribe(lambda e: results["a"].append(e))
        bus.subscribe(lambda e: results["b"].append(e))
        bus.subscribe(lambda e: results["c"].append(e))

        bus.publish({"type": "broadcast"})

        for key in ("a", "b", "c"):
            assert len(results[key]) == 1
            assert results[key][0]["type"] == "broadcast"

    def test_event_type_constants_are_distinct(self):
        constants = [
            EVENT_SCAN_STARTED,
            EVENT_SCAN_COMPLETED,
            EVENT_SCAN_FAILED,
            EVENT_FILE_CREATED,
            EVENT_FILE_DELETED,
            EVENT_FILE_MODIFIED,
            EVENT_STATUS_CHANGED,
            EVENT_METRICS_UPDATED,
            EVENT_SYNC_COMPLETED,
        ]
        assert len(constants) == len(set(constants))
        assert all(isinstance(c, str) for c in constants)

    def test_drain_max_events_limit(self):
        bus = EventBus()
        for i in range(200):
            bus.publish({"type": "event", "i": i})

        events = bus.drain(since=0, max_events=50)
        assert len(events) == 50

    def test_empty_bus_drain(self):
        bus = EventBus()
        events = bus.drain(since=0)
        assert events == []

    def test_empty_bus_snapshot(self):
        bus = EventBus()
        snap = bus.snapshot()
        assert snap == []

    def test_unsubscribe_nonexistent_is_safe(self):
        bus = EventBus()
        bus.unsubscribe(lambda e: None)  # should not raise
