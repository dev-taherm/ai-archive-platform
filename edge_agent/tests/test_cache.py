"""Tests for edge_agent.core.cache — LRU cache."""
import time
import pytest
from edge_agent.core.cache import LRUCache


class TestLRUCache:
    def test_set_and_get(self):
        c = LRUCache(maxsize=10)
        c.set("k1", "v1")
        assert c.get("k1") == "v1"

    def test_get_missing(self):
        c = LRUCache(maxsize=10)
        assert c.get("missing") is None

    def test_eviction(self):
        c = LRUCache(maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        assert c.get("a") is None
        assert c.get("b") == 2
        assert c.get("c") == 3

    def test_update_refreshes_lru(self):
        c = LRUCache(maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.get("a")
        c.set("c", 3)
        assert c.get("a") == 1
        assert c.get("b") is None

    def test_contains(self):
        c = LRUCache(maxsize=10)
        c.set("k", "v")
        assert "k" in c
        assert "missing" not in c

    def test_len(self):
        c = LRUCache(maxsize=10)
        assert len(c) == 0
        c.set("a", 1)
        c.set("b", 2)
        assert len(c) == 2

    def test_clear(self):
        c = LRUCache(maxsize=10)
        c.set("a", 1)
        c.clear()
        assert len(c) == 0

    def test_delete(self):
        c = LRUCache(maxsize=10)
        c.set("k", "v")
        c.delete("k")
        assert c.get("k") is None

    def test_ttl_expiry(self):
        c = LRUCache(maxsize=10, ttl=0.1)
        c.set("k", "v")
        assert c.get("k") == "v"
        time.sleep(0.15)
        assert c.get("k") is None

    def test_ttl_no_expiry_within(self):
        c = LRUCache(maxsize=10, ttl=60)
        c.set("k", "v")
        assert c.get("k") == "v"

    def test_zero_maxsize(self):
        c = LRUCache(maxsize=0)
        c.set("k", "v")
        assert c.get("k") is None
