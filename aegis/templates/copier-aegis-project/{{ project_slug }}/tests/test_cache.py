"""
Tests for CacheService.
"""

import time

from app.core.cache import CacheService


class TestCacheService:
    def test_set_and_get(self) -> None:
        cache = CacheService()
        cache.set("key1", {"data": 42})
        assert cache.get("key1") == {"data": 42}

    def test_get_missing_key_returns_none(self) -> None:
        cache = CacheService()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self) -> None:
        cache = CacheService()
        cache.set("key1", "value", ttl=0)
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_default_ttl(self) -> None:
        cache = CacheService(default_ttl=1)
        cache.set("key1", "value")
        assert cache.get("key1") == "value"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_invalidate(self) -> None:
        cache = CacheService()
        cache.set("key1", "value")
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_invalidate_missing_key_no_error(self) -> None:
        cache = CacheService()
        cache.invalidate("nonexistent")  # should not raise

    def test_clear(self) -> None:
        cache = CacheService()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite_existing_key(self) -> None:
        cache = CacheService()
        cache.set("key1", "old")
        cache.set("key1", "new")
        assert cache.get("key1") == "new"

    def test_custom_ttl_overrides_default(self) -> None:
        cache = CacheService(default_ttl=300)
        cache.set("key1", "value", ttl=0)
        time.sleep(0.01)
        assert cache.get("key1") is None
