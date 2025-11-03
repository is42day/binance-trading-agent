# binance_trade_agent/market_data_agent.py


from binance_trade_agent.binance_client import BinanceAPIClient
from binance_trade_agent.redis_cache import RedisCache
from binance_trade_agent.config import Config
import asyncio

class MarketDataAgent:
    """
    Agent for retrieving market data from Binance. Can be extended to implement
    prompt-driven or scheduled data pulls in an AI pipeline.
    """

    def __init__(self, binance_client=None, redis_cache=None, config=None):
        self.client = binance_client or BinanceAPIClient()
        self.config = config or Config()
        self.cache = redis_cache or RedisCache(
            host=self.config.redis_host,
            port=self.config.redis_port,
            db=self.config.redis_db,
            ttl=self.config.redis_ttl_prices
        )

    def fetch_price(self, symbol: str) -> float:
        """
        Get latest price for a symbol, with Redis cache fallback.
        """
        key = f"price:{symbol}"
        
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context but this is a sync function - not ideal
            # Fall through to create new loop
            raise RuntimeError("Need new loop for sync call")
        except RuntimeError:
            # No event loop or need new one - create and use it
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                cached = loop.run_until_complete(self.cache.get(key))
                if cached is not None:
                    return cached
                price = self.client.get_latest_price(symbol)
                loop.run_until_complete(self.cache.set(key, price, ttl=self.config.redis_ttl_prices))
                return price
            finally:
                loop.close()

    async def fetch_price_async(self, symbol: str) -> float:
        key = f"price:{symbol}"
        cached = await self.cache.get(key)
        if cached is not None:
            return cached
        price = self.client.get_latest_price(symbol)
        await self.cache.set(key, price, ttl=self.config.redis_ttl_prices)
        return price

    def fetch_order_book(self, symbol: str, limit=10):
        """
        Get order book for a symbol, with Redis cache fallback.
        """
        key = f"orderbook:{symbol}:{limit}"
        
        # Create new event loop for sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            cached = loop.run_until_complete(self.cache.get(key))
            if cached is not None:
                return cached
            ob = self.client.get_order_book(symbol, limit=limit)
            loop.run_until_complete(self.cache.set(key, ob, ttl=self.config.redis_ttl_orderbook))
            return ob
        finally:
            loop.close()

    async def fetch_order_book_async(self, symbol: str, limit=10):
        key = f"orderbook:{symbol}:{limit}"
        cached = await self.cache.get(key)
        if cached is not None:
            return cached
        ob = self.client.get_order_book(symbol, limit=limit)
        await self.cache.set(key, ob, ttl=self.config.redis_ttl_orderbook)
        return ob

    def fetch_balance(self, asset: str) -> float:
        """
        Get balance for specific asset.
        """
        return self.client.get_balance(asset)

    def get_latest_price(self, symbol: str) -> float:
        """
        Alias for fetch_price to support orchestrator compatibility.
        """
        return self.fetch_price(symbol)

    def fetch_ohlcv(self, symbol: str, interval: str = '1h', limit: int = 100):
        """
        Fetch OHLCV (candlestick) data for technical analysis, with Redis cache fallback.
        """
        key = f"ohlcv:{symbol}:{interval}:{limit}"
        
        # Create new event loop for sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            cached = loop.run_until_complete(self.cache.get(key))
            if cached is not None:
                return cached
            klines = self.client.get_klines(symbol, interval, limit)
            ohlcv_data = []
            for kline in klines:
                ohlcv_data.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            loop.run_until_complete(self.cache.set(key, ohlcv_data, ttl=self.config.redis_ttl_ohlcv))
            return ohlcv_data
        finally:
            loop.close()

    async def fetch_ohlcv_async(self, symbol: str, interval: str = '1h', limit: int = 100):
        key = f"ohlcv:{symbol}:{interval}:{limit}"
        cached = await self.cache.get(key)
        if cached is not None:
            return cached
        klines = self.client.get_klines(symbol, interval, limit)
        ohlcv_data = []
        for kline in klines:
            ohlcv_data.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        await self.cache.set(key, ohlcv_data, ttl=self.config.redis_ttl_ohlcv)
        return ohlcv_data

    def fetch_24h_ticker(self, symbol: str):
        """
        Fetch 24-hour ticker statistics including price change, volume, etc.
        """
        return self.client.get_24h_ticker(symbol)

# Example usage (for manual/debug test, not run in production agent loop):
if __name__ == "__main__":
    agent = MarketDataAgent()
    price = agent.fetch_price("BTCUSDT")
    print("BTCUSDT Latest Price:", price)
    order_book = agent.fetch_order_book("BTCUSDT")
    print("BTCUSDT Order Book:", order_book)
    balance = agent.fetch_balance("USDT")
    print("USDT balance:", balance)
