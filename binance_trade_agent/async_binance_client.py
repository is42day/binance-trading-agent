import asyncio
import time
import hmac
import hashlib
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode
import httpx
from .config import config


class AsyncBinanceClient:
    """
    Async Binance API client for high-performance non-blocking operations
    Uses httpx for async HTTP requests with connection pooling
    """
    
    def __init__(self):
        self.config = config
        
        # API endpoints
        if self.config.binance_testnet:
            self.base_url = 'https://testnet.binance.vision/api'
            print("🔧 Using Binance Testnet for safe testing (async)")
        else:
            self.base_url = 'https://api.binance.com/api'
            print("🚨 PRODUCTION MODE: Using live Binance API (async) - USE WITH CAUTION!")
        
        # Connection pooling for better performance
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        timeout = httpx.Timeout(10.0, connect=5.0)
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            limits=limits,
            timeout=timeout,
            headers={'X-MBX-APIKEY': self.config.binance_api_key} if not self.config.demo_mode else {}
        )
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for authenticated requests"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.config.binance_api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def get_latest_price(self, symbol: str) -> float:
        """
        Get latest price for a symbol (async)
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            
        Returns:
            Latest price as float
        """
        if self.config.demo_mode:
            # Mock data for demo mode
            mock_prices = {
                'BTCUSDT': 50000.0,
                'ETHUSDT': 3000.0,
                'BNBUSDT': 400.0,
                'ADAUSDT': 0.5,
                'SOLUSDT': 100.0
            }
            await asyncio.sleep(0.01)  # Simulate network latency
            return mock_prices.get(symbol, 100.0)
        
        try:
            response = await self.client.get(
                '/v3/ticker/price',
                params={'symbol': symbol}
            )
            response.raise_for_status()
            data = response.json()
            return float(data['price'])
        except httpx.HTTPStatusError as e:
            raise Exception(f"Binance API error ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get latest price: {str(e)}")
    
    async def get_order_book(self, symbol: str, limit: int = 10) -> Dict[str, List]:
        """
        Get order book for a symbol (async)
        
        Args:
            symbol: Trading symbol
            limit: Number of levels to retrieve (default: 10, max: 5000)
            
        Returns:
            Order book with bids and asks
        """
        if self.config.demo_mode:
            base_price = await self.get_latest_price(symbol)
            await asyncio.sleep(0.01)
            return {
                'bids': [[f"{base_price - i * 0.1:.2f}", f"{10 + i}"] for i in range(min(limit, 5))],
                'asks': [[f"{base_price + i * 0.1:.2f}", f"{10 + i}"] for i in range(min(limit, 5))]
            }
        
        try:
            response = await self.client.get(
                '/v3/depth',
                params={'symbol': symbol, 'limit': limit}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Binance API error ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get order book: {str(e)}")
    
    async def get_balance(self, asset: str) -> float:
        """
        Get balance for an asset (async, requires authentication)
        
        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')
            
        Returns:
            Free balance as float
        """
        if self.config.demo_mode:
            mock_balances = {
                'BTC': 0.5,
                'ETH': 2.0,
                'USDT': 10000.0,
                'BNB': 10.0,
                'ADA': 1000.0,
                'SOL': 50.0
            }
            await asyncio.sleep(0.01)
            return mock_balances.get(asset, 0.0)
        
        try:
            params = {
                'timestamp': int(time.time() * 1000)
            }
            params['signature'] = self._generate_signature(params)
            
            response = await self.client.get(
                '/v3/account',
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # Find the asset balance
            for balance in data.get('balances', []):
                if balance['asset'] == asset:
                    return float(balance['free'])
            
            return 0.0
        except httpx.HTTPStatusError as e:
            raise Exception(f"Binance API error ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get balance: {str(e)}")
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new order (async, requires authentication)
        
        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            order_type: 'LIMIT', 'MARKET', etc.
            quantity: Order quantity
            price: Order price (for LIMIT orders)
            **kwargs: Additional order parameters
            
        Returns:
            Order creation response
        """
        if self.config.demo_mode:
            await asyncio.sleep(0.02)
            return {
                'symbol': symbol,
                'orderId': int(time.time() * 1000),
                'status': 'FILLED',
                'side': side,
                'type': order_type,
                'executedQty': str(quantity),
                'price': str(price) if price else 'N/A'
            }
        
        try:
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'timestamp': int(time.time() * 1000)
            }
            
            if quantity:
                params['quantity'] = quantity
            if price:
                params['price'] = price
            if order_type.upper() == 'LIMIT':
                params['timeInForce'] = kwargs.get('timeInForce', 'GTC')
            
            params.update(kwargs)
            params['signature'] = self._generate_signature(params)
            
            response = await self.client.post(
                '/v3/order',
                data=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Binance API error ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to create order: {str(e)}")
    
    async def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Cancel an existing order (async, requires authentication)
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        if self.config.demo_mode:
            await asyncio.sleep(0.01)
            return {
                'symbol': symbol,
                'orderId': order_id,
                'status': 'CANCELED'
            }
        
        try:
            params = {
                'symbol': symbol,
                'orderId': order_id,
                'timestamp': int(time.time() * 1000)
            }
            params['signature'] = self._generate_signature(params)
            
            response = await self.client.delete(
                '/v3/order',
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Binance API error ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to cancel order: {str(e)}")
    
    async def get_klines(
        self,
        symbol: str,
        interval: str = '1h',
        limit: int = 100
    ) -> List[List]:
        """
        Get candlestick/kline data (async)
        
        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of klines to retrieve (max: 1000)
            
        Returns:
            List of kline data
        """
        if self.config.demo_mode:
            await asyncio.sleep(0.02)
            # Generate mock kline data
            import random
            base_price = await self.get_latest_price(symbol)
            klines = []
            for i in range(limit):
                open_price = base_price + random.uniform(-100, 100)
                close_price = open_price + random.uniform(-50, 50)
                high_price = max(open_price, close_price) + random.uniform(0, 20)
                low_price = min(open_price, close_price) - random.uniform(0, 20)
                volume = random.uniform(100, 1000)
                
                klines.append([
                    int((time.time() - i * 3600) * 1000),  # Open time
                    str(open_price),
                    str(high_price),
                    str(low_price),
                    str(close_price),
                    str(volume)
                ])
            return list(reversed(klines))
        
        try:
            response = await self.client.get(
                '/v3/klines',
                params={
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Binance API error ({e.response.status_code}): {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get klines: {str(e)}")
    
    async def close(self):
        """Close the HTTP client and cleanup resources"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
