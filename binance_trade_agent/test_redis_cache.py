"""
Test script for Redis caching integration with MarketDataAgent.
"""
import asyncio
from binance_trade_agent.market_data_agent import MarketDataAgent

async def main():
    agent = MarketDataAgent()
    symbol = "BTCUSDT"
    print("Testing price caching for:", symbol)

    # First fetch (should hit API and cache)
    price1 = await agent.fetch_price_async(symbol)
    print("First fetch (API):", price1)

    # Second fetch (should hit cache)
    price2 = await agent.fetch_price_async(symbol)
    print("Second fetch (cache):", price2)

    # Test order book
    ob1 = await agent.fetch_order_book_async(symbol, limit=5)
    print("Order book (API/cache):", ob1)

    # Test OHLCV
    ohlcv1 = await agent.fetch_ohlcv_async(symbol, interval='1h', limit=2)
    print("OHLCV (API/cache):", ohlcv1)

    # Wait for cache to expire and fetch again
    print("Waiting for cache to expire...")
    await asyncio.sleep(3)
    price3 = await agent.fetch_price_async(symbol)
    print("After TTL (API):", price3)

if __name__ == "__main__":
    asyncio.run(main())
