"""
Async Redis caching service for market data with TTL support.
Falls back to in-memory cache if Redis is not available.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class InMemoryCache:
    """Fallback in-memory cache when Redis is unavailable."""

    def __init__(self, ttl: int = 2):
        self.ttl = ttl
        self._cache = {}
        self._expiry = {}

    async def connect(self):
        pass

    async def close(self):
        pass

    async def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            if key in self._expiry and self._expiry[key] < datetime.now():
                del self._cache[key]
                del self._expiry[key]
                return None
            return self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        ttl = ttl if ttl is not None else self.ttl
        self._cache[key] = value
        self._expiry[key] = datetime.now() + timedelta(seconds=ttl)

    async def delete(self, key: str):
        if key in self._cache:
            del self._cache[key]
            del self._expiry[key]

    async def clear(self, pattern: str = "*"):
        self._cache.clear()
        self._expiry.clear()

    async def exists(self, key: str) -> int:
        """Check if key exists. Returns 1 if exists, 0 otherwise."""
        if key in self._cache:
            if key in self._expiry and self._expiry[key] < datetime.now():
                del self._cache[key]
                del self._expiry[key]
                return 0
            return 1
        return 0


class RedisCache:
    def __init__(
        self, host: str = "localhost", port: int = 6379, db: int = 0, ttl: int = 2
    ):
        self.host = host
        self.port = port
        self.db = db
        self.ttl = ttl
        self._redis = None
        self._use_fallback = False

    async def connect(self):
        if not self._redis and not self._use_fallback:
            logger.debug(
                f"Attempting to connect to Redis at {self.host}:{self.port}/{self.db}"
            )
            try:
                redis_client = await asyncio.wait_for(
                    aioredis.from_url(
                        f"redis://{self.host}:{self.port}/{self.db}",
                        encoding="utf-8",
                        decode_responses=True,
                    ),
                    timeout=2,
                )
                # Test the connection with a ping
                await asyncio.wait_for(redis_client.ping(), timeout=2)
                self._redis = redis_client
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(
                    f"Failed to connect to Redis ({self.host}:{self.port}): {type(e).__name__}: {e}. Using in-memory cache fallback."
                )
                self._use_fallback = True
                self._redis = InMemoryCache(self.ttl)
                logger.info("Fallback initialized. Using in-memory cache.")

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._use_fallback = False

    async def get(self, key: str) -> Optional[Any]:
        await self.connect()
        logger.debug(
            f"Getting key '{key}' from {'in-memory' if self._use_fallback else 'Redis'} cache"
        )
        try:
            value = await self._redis.get(key)
            if value is not None and not self._use_fallback:
                try:
                    return json.loads(value) if isinstance(value, str) else value
                except Exception:
                    return value
            return value
        except Exception as e:
            logger.error(
                f"Error getting key '{key}' from cache: {type(e).__name__}: {e}"
            )
            raise

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        await self.connect()
        ttl = ttl if ttl is not None else self.ttl
        if self._use_fallback:
            await self._redis.set(key, value, ttl)
        else:
            value_str = json.dumps(value)
            await self._redis.set(key, value_str, ex=ttl)

    async def delete(self, key: str):
        await self.connect()
        await self._redis.delete(key)

    async def clear(self, pattern: str = "*"):
        await self.connect()
        await self._redis.clear(pattern)

    async def exists(self, key: str) -> bool:
        await self.connect()
        return await self._redis.exists(key) > 0


# Example usage:
# cache = RedisCache(ttl=2)
# await cache.set('BTCUSDT_price', {'price': 50000}, ttl=2)
# price = await cache.get('BTCUSDT_price')
