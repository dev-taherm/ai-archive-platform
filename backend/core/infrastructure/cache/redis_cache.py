from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class CacheService:
    """Simple Redis-backed cache for expensive queries."""

    def __init__(self, default_ttl: int = 300) -> None:
        self._default_ttl = default_ttl
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

    def get(self, key: str) -> Any | None:
        client = self._get_client()
        if client is None:
            return None
        try:
            value = client.get(key)
            if value:
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
            client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            logger.exception("Cache set failed for key=%s", key)

    def delete(self, key: str) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            client.delete(key)
        except Exception:
            logger.exception("Cache delete failed for key=%s", key)

    def clear_pattern(self, pattern: str) -> int:
        client = self._get_client()
        if client is None:
            return 0
        try:
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
        except Exception:
            logger.exception("Cache clear_pattern failed for pattern=%s", pattern)
        return 0


cache = CacheService()
