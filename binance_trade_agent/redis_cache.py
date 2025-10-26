"""
Async Redis caching service for market data with TTL support.
"""
import aioredis
import asyncio
import json
from typing import Any, Optional

class RedisCache:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, ttl: int = 2):
        self.host = host
        self.port = port
        self.db = db
        self.ttl = ttl
        self._redis = None

    async def connect(self):
        if not self._redis:
            self._redis = await aioredis.from_url(f"redis://{self.host}:{self.port}/{self.db}", encoding="utf-8", decode_responses=True)

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        await self.connect()
        value = await self._redis.get(key)
        if value is not None:
            try:
                return json.loads(value)
            except Exception:
                return value
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        await self.connect()
        ttl = ttl if ttl is not None else self.ttl
        value_str = json.dumps(value)
        await self._redis.set(key, value_str, ex=ttl)

    async def delete(self, key: str):
        await self.connect()
        await self._redis.delete(key)

    async def clear(self, pattern: str = "*"):
        await self.connect()
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)

    async def exists(self, key: str) -> bool:
        await self.connect()
        return await self._redis.exists(key) > 0

# Example usage:
# cache = RedisCache(ttl=2)
# await cache.set('BTCUSDT_price', {'price': 50000}, ttl=2)
# price = await cache.get('BTCUSDT_price')
