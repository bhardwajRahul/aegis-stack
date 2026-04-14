"""
Application cache service.

In-memory TTL cache with a clean interface that can be swapped
to Redis or another backend without changing consumer code.
"""

import time
from typing import Any

from app.core.log import logger


class CacheService:
    """Simple TTL cache. Swap internals to Redis when needed."""

    def __init__(self, default_ttl: int = 300) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get a cached value. Returns None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            logger.debug("cache.expired", key=key)
            return None
        logger.debug("cache.hit", key=key)
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value with TTL (seconds). Uses default_ttl if not specified."""
        expires_at = time.time() + (ttl if ttl is not None else self._default_ttl)
        self._store[key] = (value, expires_at)
        logger.debug("cache.set", key=key, ttl=ttl or self._default_ttl)

    def invalidate(self, key: str) -> None:
        """Remove a specific key."""
        self._store.pop(key, None)
        logger.debug("cache.invalidate", key=key)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()
        logger.debug("cache.clear")


# Singleton instance
cache = CacheService()


def get_cache() -> CacheService:
    """Dependency provider for CacheService."""
    return cache
