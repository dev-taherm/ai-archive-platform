from __future__ import annotations

import functools
import hashlib
import json
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-backed cache with get/set/delete/clear_pattern and JSON serialization."""

    def __init__(self, default_ttl: int = 300, prefix: str = "") -> None:
        self._default_ttl = default_ttl
        self._prefix = prefix
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import redis
            from django.conf import settings

            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            self._client = redis.from_url(redis_url, decode_responses=True)
        except (ImportError, Exception) as e:
            logger.warning("Redis unavailable, caching disabled: %s", e)
            self._client = None
        return self._client

    @staticmethod
    def make_key(*args: Any, **kwargs: Any) -> str:
        """Generate a deterministic cache key from positional and keyword arguments."""
        raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def full_key(self, key: str) -> str:
        """Return the prefixed cache key."""
        return f"{self._prefix}{key}" if self._prefix else key

    def get(self, key: str) -> Any | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            value = client.get(self.full_key(key))
            if value is not None:
                return json.loads(value)
        except Exception:
            logger.exception("Cache get failed for key=%s", key)
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            ttl = ttl or self._default_ttl
            client.setex(self.full_key(key), ttl, json.dumps(value, default=str))
        except Exception:
            logger.exception("Cache set failed for key=%s", key)

    def delete(self, key: str) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            client.delete(self.full_key(key))
        except Exception:
            logger.exception("Cache delete failed for key=%s", key)

    def clear_pattern(self, pattern: str) -> int:
        client = self._get_client()
        if client is None:
            return 0
        try:
            full = self.full_key(pattern)
            keys = client.keys(full)
            if keys:
                return client.delete(*keys)
        except Exception:
            logger.exception("Cache clear_pattern failed for pattern=%s", pattern)
        return 0


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    cache_instance: RedisCache | None = None,
) -> Callable:
    """Decorator that caches a function's return value in Redis.

    Usage:
        @cached(ttl=600, key_prefix="user")
        def get_user(user_id: int) -> dict:
            ...

    The cache key is derived from the function's qualified name plus all
    arguments via ``RedisCache.make_key``.
    """

    def decorator(func: Callable) -> Callable:
        _cache = cache_instance or RedisCache(default_ttl=ttl, prefix=key_prefix)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = f"{func.__module__}.{func.__qualname__}:{RedisCache.make_key(*args, **kwargs)}"
            result = _cache.get(cache_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl=ttl)
            return result

        def invalidate(*args: Any, **kwargs: Any) -> None:
            """Manually invalidate a cached call."""
            cache_key = f"{func.__module__}.{func.__qualname__}:{RedisCache.make_key(*args, **kwargs)}"
            _cache.delete(cache_key)

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator


cache = RedisCache()
