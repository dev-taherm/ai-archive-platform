from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any


class LRUCache:
    def __init__(self, max_size: int = 100, ttl_seconds: float | None = None) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, value = entry
        if self._ttl is not None and (time.monotonic() - ts) > self._ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = (time.monotonic(), value)

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
