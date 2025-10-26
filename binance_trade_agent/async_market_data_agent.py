"""
Async Market Data Agent - High-performance market data retrieval with async operations
"""
import asyncio
from typing import List, Dict, Any, Optional
from .async_binance_client import AsyncBinanceClient


class AsyncMarketDataAgent:
    """
    Async agent for retrieving market data from Binance
    Supports concurrent data fetching for multiple symbols
    """
    
    def __init__(self, binance_client: Optional[AsyncBinanceClient] = None):
        """
        Initialize AsyncMarketDataAgent
        
        Args:
            binance_client: Optional AsyncBinanceClient instance for connection pooling
        """
        self.client = binance_client or AsyncBinanceClient()
        self._owns_client = binance_client is None
    
    async def fetch_price(self, symbol: str) -> float:
        """
        Get latest price for a symbol (async)
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            
        Returns:
            Latest price
        """
        return await self.client.get_latest_price(symbol)
    
    async def fetch_prices_batch(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get latest prices for multiple symbols concurrently
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            Dictionary mapping symbols to prices
        """
        tasks = [self.fetch_price(symbol) for symbol in symbols]
        prices = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for symbol, price in zip(symbols, prices):
            if isinstance(price, Exception):
                print(f"Error fetching price for {symbol}: {price}")
                result[symbol] = None
            else:
                result[symbol] = price
        
        return result
    
    async def fetch_order_book(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get order book for a symbol (async)
        
        Args:
            symbol: Trading symbol
            limit: Depth limit
            
        Returns:
            Order book data
        """
        return await self.client.get_order_book(symbol, limit)
    
    async def fetch_order_books_batch(
        self,
        symbols: List[str],
        limit: int = 10
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get order books for multiple symbols concurrently
        
        Args:
            symbols: List of trading symbols
            limit: Depth limit for each order book
            
        Returns:
            Dictionary mapping symbols to order book data
        """
        tasks = [self.fetch_order_book(symbol, limit) for symbol in symbols]
        order_books = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for symbol, order_book in zip(symbols, order_books):
            if isinstance(order_book, Exception):
                print(f"Error fetching order book for {symbol}: {order_book}")
                result[symbol] = None
            else:
                result[symbol] = order_book
        
        return result
    
    async def fetch_klines(
        self,
        symbol: str,
        interval: str = '1h',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get candlestick/kline data (async)
        
        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of klines to retrieve
            
        Returns:
            List of kline data formatted as dicts
        """
        klines = await self.client.get_klines(symbol, interval, limit)
        
        # Format klines as dictionaries for easier processing
        formatted_klines = []
        for kline in klines:
            formatted_klines.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        
        return formatted_klines
    
    async def fetch_klines_batch(
        self,
        symbols: List[str],
        interval: str = '1h',
        limit: int = 100
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get klines for multiple symbols concurrently
        
        Args:
            symbols: List of trading symbols
            interval: Kline interval
            limit: Number of klines per symbol
            
        Returns:
            Dictionary mapping symbols to their kline data
        """
        tasks = [
            self.fetch_klines(symbol, interval, limit)
            for symbol in symbols
        ]
        klines_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for symbol, klines in zip(symbols, klines_list):
            if isinstance(klines, Exception):
                print(f"Error fetching klines for {symbol}: {klines}")
                result[symbol] = None
            else:
                result[symbol] = klines
        
        return result
    
    async def close(self):
        """Close the client if we own it"""
        if self._owns_client:
            await self.client.close()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
