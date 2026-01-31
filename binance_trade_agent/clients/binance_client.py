"""
Binance API Client with Production-Ready Features:
- Request timeouts to prevent hanging
- Circuit breaker pattern for fault tolerance
- Retry logic with exponential backoff
"""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException

from ..common.config import config

logger = logging.getLogger(__name__)


# =============================================================================
# Circuit Breaker Implementation
# =============================================================================


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API calls.
    
    Prevents cascading failures by:
    1. Tracking consecutive failures
    2. Opening circuit after threshold reached
    3. Periodically testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3,
    ):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = Lock()
        
        logger.info(
            f"Circuit breaker initialized: threshold={failure_threshold}, "
            f"recovery={recovery_timeout}s"
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery timeout"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info("Circuit breaker: OPEN -> HALF_OPEN (testing recovery)")
            return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self._last_failure_time is None:
            return True
        return datetime.now() > self._last_failure_time + timedelta(seconds=self.recovery_timeout)
    
    def record_success(self):
        """Record a successful call"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    logger.info("Circuit breaker: HALF_OPEN -> CLOSED (service recovered)")
            else:
                self._failure_count = 0
    
    def record_failure(self):
        """Record a failed call"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                # Failed during recovery test - back to open
                self._state = CircuitState.OPEN
                logger.warning("Circuit breaker: HALF_OPEN -> OPEN (recovery failed)")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker: CLOSED -> OPEN (failures: {self._failure_count})"
                )
    
    def can_execute(self) -> bool:
        """Check if requests are allowed"""
        current_state = self.state  # This also checks for recovery
        
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            with self._lock:
                return self._half_open_calls < self.half_open_max_calls
    
    def get_status(self) -> dict:
        """Get circuit breaker status for monitoring"""
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
        }


# =============================================================================
# Timeout and Retry Decorator
# =============================================================================


def with_timeout_and_retry(
    timeout: float = 10.0,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
    circuit_breaker: Optional[CircuitBreaker] = None,
):
    """
    Decorator that adds timeout, retry logic, and circuit breaker to API calls.
    
    Args:
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        circuit_breaker: Optional circuit breaker instance
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Check circuit breaker
            if circuit_breaker and not circuit_breaker.can_execute():
                raise BinanceAPIException(
                    None, 
                    -1, 
                    "Circuit breaker OPEN - Binance API temporarily unavailable"
                )
            
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    # Note: python-binance doesn't support per-request timeout
                    # We use the client's built-in timeout set during initialization
                    result = func(*args, **kwargs)
                    
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    
                    return result
                    
                except BinanceAPIException as e:
                    last_exception = e
                    
                    # Don't retry on client errors (4xx)
                    if e.status_code and 400 <= e.status_code < 500:
                        if circuit_breaker:
                            circuit_breaker.record_failure()
                        raise
                    
                    logger.warning(
                        f"Binance API error (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"API call failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                
                # Wait before retry with exponential backoff
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
                    logger.debug(f"Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
            
            # All retries exhausted
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            raise last_exception or Exception("API call failed after all retries")
        
        return wrapper
    return decorator


# =============================================================================
# Binance API Client
# =============================================================================


class BinanceAPIClient:
    """
    Production-ready Binance API wrapper with:
    - Request timeouts (10 seconds default)
    - Circuit breaker pattern
    - Retry with exponential backoff
    - Demo mode for testing
    """

    # Default timeout for API requests (seconds)
    DEFAULT_TIMEOUT = 10
    
    def __init__(self, timeout: float = None):
        """
        Initialize Binance client.
        
        Args:
            timeout: Request timeout in seconds (default: 10)
        """
        self.config = config
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        
        # Initialize circuit breaker
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            half_open_max_calls=3,
        )

        if self.config.demo_mode:
            print(
                "⚠️  WARNING: Running in DEMO MODE with mock data. "
                "Set BINANCE_API_KEY and BINANCE_API_SECRET for live trading."
            )
            self.client = None
        else:
            # Create client with timeout
            self.client = Client(
                self.config.binance_api_key, 
                self.config.binance_api_secret,
                requests_params={"timeout": self.timeout}
            )
            
            # Use testnet for safety unless explicitly disabled
            if self.config.binance_testnet:
                self.client.API_URL = "https://testnet.binance.vision/api"
                print(f"🔧 Using Binance Testnet (timeout: {self.timeout}s)")
            else:
                print(
                    f"🚨 PRODUCTION MODE: Using live Binance API - USE WITH CAUTION! "
                    f"(timeout: {self.timeout}s)"
                )

    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status for monitoring"""
        return self._circuit_breaker.get_status()

    def _api_call_with_retry(self, func: Callable, *args, max_retries: int = 3, **kwargs) -> Any:
        """
        Execute API call with retry logic and circuit breaker.
        
        Args:
            func: API function to call
            max_retries: Maximum retry attempts
            *args, **kwargs: Arguments for the API function
            
        Returns:
            API response
        """
        if not self._circuit_breaker.can_execute():
            raise Exception("Circuit breaker OPEN - Binance API temporarily unavailable")
        
        last_exception = None
        backoff = 1.0
        
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                self._circuit_breaker.record_success()
                return result
            except BinanceAPIException as e:
                last_exception = e
                # Don't retry on 4xx client errors
                if e.status_code and 400 <= e.status_code < 500:
                    self._circuit_breaker.record_failure()
                    raise
                logger.warning(f"Binance API error (attempt {attempt + 1}/{max_retries}): {e}")
            except Exception as e:
                last_exception = e
                logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(backoff)
                backoff *= 1.5
        
        self._circuit_breaker.record_failure()
        raise last_exception or Exception("API call failed after all retries")

    def get_latest_price(self, symbol: str) -> float:
        """
        Get latest price for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            Current price as float
        """
        if self.config.demo_mode:
            mock_prices = {
                "BTCUSDT": 50000.0,
                "ETHUSDT": 3000.0,
                "BNBUSDT": 400.0,
                "ADAUSDT": 0.5,
                "SOLUSDT": 100.0,
            }
            return mock_prices.get(symbol, 100.0)

        response = self._api_call_with_retry(
            self.client.get_symbol_ticker, symbol=symbol
        )
        return float(response["price"])

    def get_order_book(self, symbol: str, limit: int = 10):
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading pair
            limit: Number of price levels
            
        Returns:
            Order book dict with 'bids' and 'asks'
        """
        if self.config.demo_mode:
            base_price = self.get_latest_price(symbol)
            return {
                "bids": [
                    [f"{base_price - i * 0.1:.2f}", f"{10 + i}"] for i in range(min(limit, 5))
                ],
                "asks": [
                    [f"{base_price + i * 0.1:.2f}", f"{10 + i}"] for i in range(min(limit, 5))
                ],
            }

        return self._api_call_with_retry(
            self.client.get_order_book, symbol=symbol, limit=limit
        )

    def get_balance(self, asset: str) -> float:
        """
        Get balance for an asset.
        
        Args:
            asset: Asset symbol (e.g., 'BTC', 'USDT')
            
        Returns:
            Free balance as float
        """
        if self.config.demo_mode:
            mock_balances = {
                "BTC": 0.5,
                "ETH": 2.0,
                "USDT": 10000.0,
                "BNB": 10.0,
                "ADA": 1000.0,
                "SOL": 50.0,
            }
            return mock_balances.get(asset, 0.0)

        balances = self._api_call_with_retry(
            self.client.get_asset_balance, asset=asset
        )
        if balances:
            return float(balances["free"])
        else:
            logger.warning(f"No balance found for asset {asset}")
            return 0.0

    def get_24h_ticker(self, symbol: str):
        """
        Get 24-hour ticker price change statistics.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dict with 24h statistics
        """
        if self.config.demo_mode:
            base_price = self.get_latest_price(symbol)
            price_change = (base_price * 0.02) * (1 if symbol.startswith("BTC") else -1)
            price_change_percent = (price_change / (base_price - price_change)) * 100

            return {
                "symbol": symbol,
                "priceChange": f"{price_change:.2f}",
                "priceChangePercent": f"{price_change_percent:.2f}",
                "weightedAvgPrice": f"{base_price:.2f}",
                "prevClosePrice": f"{base_price - price_change:.2f}",
                "lastPrice": f"{base_price:.2f}",
                "lastQty": "0.00100000",
                "bidPrice": f"{base_price - 0.01:.2f}",
                "bidQty": "10.00000000",
                "askPrice": f"{base_price + 0.01:.2f}",
                "askQty": "10.00000000",
                "openPrice": f"{base_price - price_change:.2f}",
                "highPrice": f"{base_price + price_change * 0.5:.2f}",
                "lowPrice": f"{base_price - price_change * 0.5:.2f}",
                "volume": "1000.00000000",
                "quoteVolume": f"{base_price * 1000:.2f}",
                "openTime": str(int(time.time() * 1000) - 86400000),
                "closeTime": str(int(time.time() * 1000)),
                "firstId": 1,
                "lastId": 1000,
                "count": 1000,
            }

        return self._api_call_with_retry(
            self.client.get_ticker, symbol=symbol
        )

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100):
        """
        Get klines (OHLCV candlestick data).
        
        Args:
            symbol: Trading pair
            interval: Candlestick interval ('1m', '5m', '1h', '4h', '1d', etc.)
            limit: Number of candles to fetch
            
        Returns:
            List of kline arrays
        """
        if self.config.demo_mode:
            import random

            now = int(time.time() * 1000)
            klines = []
            interval_ms_map = {
                "1m": 60_000,
                "5m": 5 * 60_000,
                "15m": 15 * 60_000,
                "1h": 60 * 60_000,
                "4h": 4 * 60 * 60_000,
                "1d": 24 * 60 * 60_000,
            }
            step = interval_ms_map.get(interval, 60 * 60_000)
            base_price = self.get_latest_price(symbol)
            
            for i in range(limit):
                open_time = now - (limit - i) * step
                open_p = base_price + random.uniform(-1.0, 1.0)
                high_p = open_p + random.uniform(0.0, 2.0)
                low_p = open_p - random.uniform(0.0, 2.0)
                close_p = open_p + random.uniform(-0.5, 0.5)
                volume = round(random.uniform(1.0, 100.0), 6)
                close_time = open_time + step - 1
                klines.append([
                    open_time,
                    f"{open_p:.8f}",
                    f"{high_p:.8f}",
                    f"{low_p:.8f}",
                    f"{close_p:.8f}",
                    f"{volume:.6f}",
                    close_time,
                    "0", "0", "0", "0", "0",
                ])
            return klines

        return self._api_call_with_retry(
            self.client.get_klines, symbol=symbol, interval=interval, limit=limit
        )

    def create_order(self, symbol: str, side: str, order_type: str, quantity: float, price=None):
        """
        Create a new order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            order_type: 'MARKET' or 'LIMIT'
            quantity: Order quantity
            price: Limit price (required for LIMIT orders)
            
        Returns:
            Order response dict
        """
        if self.config.demo_mode:
            order_id = int(time.time() * 1000)
            return {
                "symbol": symbol,
                "orderId": order_id,
                "orderListId": -1,
                "clientOrderId": f"mock_{order_id}",
                "transactTime": int(time.time() * 1000),
                "price": str(price) if price else "0.00000000",
                "origQty": str(quantity),
                "executedQty": str(quantity),
                "cummulativeQuoteQty": "0.00000000",
                "status": "FILLED",
                "timeInForce": "GTC",
                "type": order_type,
                "side": side,
            }

        if order_type == "MARKET":
            return self._api_call_with_retry(
                self.client.create_order,
                symbol=symbol, side=side, type=order_type, quantity=quantity,
                max_retries=2  # Fewer retries for orders
            )
        elif order_type == "LIMIT":
            if price is None:
                raise ValueError("Limit orders require price")
            return self._api_call_with_retry(
                self.client.create_order,
                symbol=symbol,
                side=side,
                type=order_type,
                timeInForce="GTC",
                quantity=quantity,
                price=str(price),
                max_retries=2
            )
        else:
            raise ValueError("Unsupported order type")

    def cancel_order(self, symbol: str, order_id: int):
        """
        Cancel an existing order.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to cancel
            
        Returns:
            Cancel response dict
        """
        if self.config.demo_mode:
            return {
                "symbol": symbol,
                "origClientOrderId": f"mock_{order_id}",
                "orderId": order_id,
                "orderListId": -1,
                "clientOrderId": f"mock_{order_id}",
                "price": "0.00000000",
                "origQty": "0.00000000",
                "executedQty": "0.00000000",
                "cummulativeQuoteQty": "0.00000000",
                "status": "CANCELED",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "side": "BUY",
            }

        return self._api_call_with_retry(
            self.client.cancel_order, symbol=symbol, orderId=order_id,
            max_retries=2
        )
