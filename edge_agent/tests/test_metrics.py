"""Tests for edge_agent.core.metrics — thread-safe counters."""
import pytest
from edge_agent.core.metrics import Metrics


class TestMetrics:
    def test_defaults(self):
        m = Metrics()
        assert m.files_scanned == 0
        assert m.parse_errors == 0
        assert m.sync_events == 0

    def test_increment(self):
        m = Metrics()
        m.files_scanned += 1
        assert m.files_scanned == 1

    def test_multiple_increments(self):
        m = Metrics()
        for i in range(5):
            m.files_scanned += 1
            m.parse_time_total_ms += 100
        assert m.files_scanned == 5
        assert m.parse_time_total_ms == 500.0

    def test_parse_errors(self):
        m = Metrics()
        m.parse_errors += 1
        m.parse_errors += 1
        assert m.parse_errors == 2

    def test_sync_events_and_files(self):
        m = Metrics()
        m.sync_events += 1
        m.sync_files += 10
        assert m.sync_events == 1
        assert m.sync_files == 10

    def test_heartbeat_count(self):
        m = Metrics()
        m.heartbeat_count += 1
        m.heartbeat_count += 1
        m.heartbeat_count += 1
        assert m.heartbeat_count == 3

    def test_memory_mb(self):
        m = Metrics()
        mb = m.memory_mb
        assert isinstance(mb, float)
        assert mb > 0

    def test_thread_safety(self):
        import threading
        m = Metrics()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    m.files_scanned += 1
                    m.parse_time_total_ms += 10
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert m.files_scanned == 1000
        assert m.parse_time_total_ms == 10000.0
        assert len(errors) == 0


class TestGetMetrics:
    def test_default_instance(self):
        m1 = Metrics()
        m2 = Metrics()
        assert m1.files_scanned == 0
        assert isinstance(m2.parse_errors, int)
