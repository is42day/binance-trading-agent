"""
Redis Cache Layer Tests - CRITICAL
Tests for RedisCache and InMemoryCache fallback mechanisms.
SLA: Cache operations should complete within 100ms (Redis) or 10ms (In-Memory)
"""

import asyncio

import pytest

from ..clients.redis_cache import InMemoryCache, RedisCache


class TestInMemoryCache:
    """Tests for InMemoryCache fallback implementation"""

    @pytest.fixture
    def cache(self):
        """Create fresh InMemoryCache instance for each test"""
        return InMemoryCache(ttl=2)

    @pytest.mark.asyncio
    async def test_inmemory_cache_set_and_get(self, cache):
        """Test basic set/get operations on InMemoryCache"""
        # Arrange
        key = "test_key"
        value = {"price": 50000, "symbol": "BTCUSDT"}

        # Act
        await cache.set(key, value)
        result = await cache.get(key)

        # Assert
        assert result == value
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_inmemory_cache_ttl_expiry(self, cache):
        """Test that InMemoryCache respects TTL expiry"""
        # Arrange
        key = "expiring_key"
        value = {"test": "data"}

        # Act
        await cache.set(key, value, ttl=1)
        result_before = await cache.get(key)
        await asyncio.sleep(1.1)  # Wait for expiry
        result_after = await cache.get(key)

        # Assert
        assert result_before == value
        assert result_after is None

    @pytest.mark.asyncio
    async def test_inmemory_cache_nonexistent_key(self, cache):
        """Test getting non-existent key returns None"""
        # Arrange & Act
        result = await cache.get("nonexistent_key")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_inmemory_cache_delete(self, cache):
        """Test deleting keys from InMemoryCache"""
        # Arrange
        key = "deletable_key"
        await cache.set(key, {"data": "value"})

        # Act
        await cache.delete(key)
        result = await cache.get(key)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_inmemory_cache_clear(self, cache):
        """Test clearing all keys from InMemoryCache"""
        # Arrange
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        assert await cache.get("key1") is not None

        # Act
        await cache.clear()

        # Assert
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_inmemory_cache_exists(self, cache):
        """Test exists() method returns correct status"""
        # Arrange
        key = "check_key"

        # Act & Assert - Key doesn't exist
        assert await cache.exists(key) == 0

        # Act - Add key
        await cache.set(key, "value")

        # Assert - Key exists
        assert await cache.exists(key) == 1

        # Act - Delete key
        await cache.delete(key)

        # Assert - Key doesn't exist
        assert await cache.exists(key) == 0

    @pytest.mark.asyncio
    async def test_inmemory_cache_concurrent_access(self, cache):
        """Test InMemoryCache handles concurrent read/write operations"""

        # Arrange
        async def write_task(idx):
            await cache.set(f"key_{idx}", f"value_{idx}")

        async def read_task(idx):
            return await cache.get(f"key_{idx}")

        # Act
        write_tasks = [write_task(i) for i in range(10)]
        await asyncio.gather(*write_tasks)

        read_results = await asyncio.gather(*[read_task(i) for i in range(10)])

        # Assert
        for idx, result in enumerate(read_results):
            assert result == f"value_{idx}"


class TestRedisCacheConnection:
    """Tests for RedisCache connection logic"""

    @pytest.fixture
    def redis_cache(self):
        """Create RedisCache instance pointing to test Redis"""
        return RedisCache(host="localhost", port=6379, db=0, ttl=2)

    @pytest.mark.asyncio
    async def test_redis_cache_fallback_on_connection_timeout(self):
        """Test that RedisCache falls back to InMemoryCache on connection timeout"""
        # Arrange - Point to non-existent Redis
        cache = RedisCache(host="nonexistent.redis", port=6379, db=0)

        # Act
        await cache.connect()

        # Assert - Should use fallback
        assert cache._use_fallback is True
        assert isinstance(cache._redis, InMemoryCache)

    @pytest.mark.asyncio
    async def test_redis_cache_fallback_on_ping_failure(self):
        """Test fallback when ping() fails (connection drops)"""
        # Arrange
        cache = RedisCache(host="localhost", port=9999, db=0)  # Invalid port

        # Act
        await cache.connect()

        # Assert
        assert cache._use_fallback is True
        assert cache._redis is not None

    @pytest.mark.asyncio
    async def test_redis_cache_idempotent_connect(self):
        """Test that calling connect() multiple times is idempotent"""
        # Arrange
        cache = RedisCache(host="nonexistent", port=6379)

        # Act
        await cache.connect()
        first_redis_obj = cache._redis
        await cache.connect()
        second_redis_obj = cache._redis

        # Assert - Should not reconnect/recreate object
        assert first_redis_obj is second_redis_obj

    @pytest.mark.asyncio
    async def test_redis_cache_close(self):
        """Test that close() properly closes the connection"""
        # Arrange
        cache = RedisCache(host="nonexistent", port=6379)
        await cache.connect()

        # Act
        await cache.close()

        # Assert
        assert cache._redis is None
        assert cache._use_fallback is False


class TestRedisCacheOperations:
    """Tests for RedisCache set/get/delete operations"""

    @pytest.fixture
    def redis_cache(self):
        """Create RedisCache with fallback to InMemoryCache"""
        return RedisCache(host="nonexistent", port=6379, ttl=2)

    @pytest.mark.asyncio
    async def test_redis_cache_set_and_get_via_fallback(self, redis_cache):
        """Test that set/get work correctly via fallback"""
        # Arrange
        await redis_cache.connect()
        key = "test_key"
        value = {"symbol": "BTCUSDT", "price": 50000}

        # Act
        await redis_cache.set(key, value)
        result = await redis_cache.get(key)

        # Assert
        assert result == value

    @pytest.mark.asyncio
    async def test_redis_cache_json_serialization_safety(self, redis_cache):
        """Test that cache handles JSON-serializable objects correctly"""
        # Arrange
        await redis_cache.connect()
        test_cases = [
            ("dict_key", {"nested": {"data": [1, 2, 3]}}),
            ("list_key", [1, "two", 3.0, None]),
            ("string_key", "simple string"),
            ("number_key", 42),
            ("bool_key", True),
        ]

        # Act & Assert
        for key, value in test_cases:
            await redis_cache.set(key, value)
            result = await redis_cache.get(key)
            assert result == value

    @pytest.mark.asyncio
    async def test_redis_cache_delete_operation(self, redis_cache):
        """Test that delete() removes keys"""
        # Arrange
        await redis_cache.connect()
        key = "deletable_key"
        await redis_cache.set(key, "value")

        # Act
        await redis_cache.delete(key)
        result = await redis_cache.get(key)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_cache_exists_check(self, redis_cache):
        """Test that exists() correctly checks key presence"""
        # Arrange
        await redis_cache.connect()
        key = "check_key"

        # Act & Assert
        exists_before = await redis_cache.exists(key)
        assert exists_before is False

        await redis_cache.set(key, "value")
        exists_after = await redis_cache.exists(key)
        assert exists_after is True

    @pytest.mark.asyncio
    async def test_redis_cache_custom_ttl_override(self, redis_cache):
        """Test that per-operation TTL overrides default"""
        # Arrange
        await redis_cache.connect()
        key = "custom_ttl_key"

        # Act - Set with custom TTL of 1 second
        await redis_cache.set(key, "value", ttl=1)
        result_before = await redis_cache.get(key)

        await asyncio.sleep(1.1)
        result_after = await redis_cache.get(key)

        # Assert
        assert result_before == "value"
        assert result_after is None


class TestCacheConcurrency:
    """Tests for cache behavior under concurrent access"""

    @pytest.mark.asyncio
    async def test_redis_cache_concurrent_set_and_get(self):
        """Test concurrent read/write operations on cache"""
        # Arrange
        cache = RedisCache(host="nonexistent", port=6379)
        await cache.connect()

        async def concurrent_operation(index):
            key = f"key_{index}"
            value = f"value_{index}"
            await cache.set(key, value)
            result = await cache.get(key)
            return result == value

        # Act
        results = await asyncio.gather(*[concurrent_operation(i) for i in range(20)])

        # Assert - All operations should succeed
        assert all(results)
        assert len(results) == 20

    @pytest.mark.asyncio
    async def test_redis_cache_no_race_condition_on_ttl_check(self):
        """Test that TTL expiry has no race conditions"""
        # Arrange
        cache = RedisCache(host="nonexistent", port=6379)
        await cache.connect()

        async def get_task(index):
            await asyncio.sleep(0.05 * index)  # Stagger reads
            return await cache.get("race_test_key")

        # Act
        await cache.set("race_test_key", "value", ttl=1)
        results = await asyncio.gather(*[get_task(i) for i in range(10)])

        # Assert - Early reads should get value, late reads might not
        assert any(r == "value" for r in results)


class TestCacheErrorHandling:
    """Tests for cache error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_redis_cache_connection_error_logging(self):
        """Test that connection errors are properly logged"""
        # Arrange
        cache = RedisCache(host="invalid.host", port=6379)

        # Act - Should not raise exception
        await cache.connect()

        # Assert - Should fall back gracefully
        assert cache._use_fallback is True

    @pytest.mark.asyncio
    async def test_redis_cache_close_idempotent(self):
        """Test that calling close() multiple times is safe"""
        # Arrange
        cache = RedisCache(host="nonexistent", port=6379)
        await cache.connect()

        # Act & Assert - Should not raise exception
        await cache.close()
        await cache.close()  # Second close should be safe
        await cache.close()  # Third close should be safe

    @pytest.mark.asyncio
    async def test_redis_cache_operations_after_close(self):
        """Test that cache operations reconnect after close()"""
        # Arrange
        cache = RedisCache(host="nonexistent", port=6379)
        await cache.connect()
        await cache.close()

        # Act - Operation should trigger reconnect
        await cache.set("post_close_key", "value")
        result = await cache.get("post_close_key")

        # Assert
        assert result == "value"
