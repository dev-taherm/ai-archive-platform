"""Tests for edge_agent.core.log_capture — ring buffer log handler."""
import logging
import pytest
from edge_agent.core.log_capture import RingBufferLogHandler
from datetime import datetime, timezone


@pytest.fixture
def handler():
    return RingBufferLogHandler(capacity=10)


class TestRingBufferLogHandler:
    def test_empty(self, handler):
        assert handler.get_records() == []

    def test_capture_single(self, handler):
        logger = logging.getLogger("test")
        logger.addHandler(handler)
        logger.info("hello")
        records = handler.get_records()
        assert len(records) == 1
        assert records[0]["message"] == "hello"
        assert records[0]["level"] == "INFO"
        assert records[0]["logger"] == "test"

    def test_capture_multiple(self, handler):
        logger = logging.getLogger("test")
        logger.addHandler(handler)
        for i in range(5):
            logger.info(f"msg {i}")
        assert len(handler.get_records()) == 5

    def test_capacity(self, handler):
        logger = logging.getLogger("test")
        logger.addHandler(handler)
        for i in range(15):
            logger.info(f"msg {i}")
        assert len(handler.get_records()) == 10

    def test_filter_by_level(self, handler):
        logger = logging.getLogger("test")
        logger.addHandler(handler)
        logger.info("info msg")
        logger.error("error msg")
        logger.warning("warn msg")
        errors = handler.get_records(level="ERROR")
        assert len(errors) == 1
        assert errors[0]["message"] == "error msg"

    def test_filter_by_level_include_lower(self, handler):
        logger = logging.getLogger("test")
        logger.addHandler(handler)
        logger.warning("warn msg")
        logger.error("error msg")
        errors = handler.get_records(level="ERROR")
        assert len(errors) == 1

    def test_limit_results(self, handler):
        logger = logging.getLogger("test")
        logger.addHandler(handler)
        for i in range(10):
            logger.info(f"msg {i}")
        records = handler.get_records(limit=3)
        assert len(records) == 3

    def test_since_timestamp(self, handler):
        logger = logging.getLogger("test")
        logger.addHandler(handler)
        logger.info("before")
        import time
        time.sleep(0.01)
        before = datetime.now(timezone.utc).isoformat()
        time.sleep(0.01)
        logger.info("after")
        records = handler.get_records(since=before)
        assert len(records) == 1
        assert records[0]["message"] == "after"

    def test_emit_no_logger_name(self, handler):
        record = logging.LogRecord(
            name="", level=logging.INFO, pathname="", lineno=0,
            msg="no logger", args=(), exc_info=None,
        )
        handler.emit(record)
        records = handler.get_records()
        assert records[0]["logger"] == "root"
