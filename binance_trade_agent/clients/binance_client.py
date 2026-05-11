"""
Binance API Client with Production-Ready Features:
- Request timeouts to prevent hanging
- Circuit breaker pattern for fault tolerance
- Retry logic with exponential backoff
"""

import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException

from ..common.config import config
from .rate_limit_tracker import RateLimitTracker, RateLimitExceeded, ENDPOINT_WEIGHTS

logger = logging.getLogger(__name__)


# =============================================================================
# Circuit Breaker Implementation
# =============================================================================


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
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
                logger.warning(f"Circuit breaker: CLOSED -> OPEN (failures: {self._failure_count})")

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
            "last_failure": (
                self._last_failure_time.isoformat() if self._last_failure_time else None
            ),
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
                    None, -1, "Circuit breaker OPEN - Binance API temporarily unavailable"
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

                    # 429 is a transient rate-limit response; back off and retry.
                    if e.status_code == 429:
                        logger.warning("Binance rate limit hit (429); backing off before retry")
                    # Don't retry on other client errors (4xx)
                    elif e.status_code and 400 <= e.status_code < 500:
                        if circuit_breaker:
                            circuit_breaker.record_failure()
                        raise

                    logger.warning(f"Binance API error (attempt {attempt + 1}/{max_retries}): {e}")

                except Exception as e:
                    last_exception = e
                    logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")

                # Wait before retry with exponential backoff
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
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
        self._rate_limiter = RateLimitTracker()

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
            # Create client with timeout - disable initial ping to avoid startup failures
            try:
                self.client = Client(
                    self.config.binance_api_key,
                    self.config.binance_api_secret,
                    requests_params={"timeout": self.timeout},
                    testnet=self.config.binance_testnet,
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
            except Exception as e:
                print(f"⚠️  WARNING: Failed to connect to Binance API: {e}. Running in DEMO MODE.")
                self.client = None
                self.config.demo_mode = True

    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status for monitoring"""
        return self._circuit_breaker.get_status()

    def get_rate_limit_status(self) -> dict:
        """Return current rate-limit tracker snapshot."""
        return self._rate_limiter.get_status()

    def _api_call_with_retry(
        self, func: Callable, *args,
        max_retries: int = 3,
        endpoint: str = "unknown",
        is_order: bool = False,
        **kwargs,
    ) -> Any:
        """
        Execute API call with rate-limit check, retry logic, and circuit breaker.

        Args:
            func:        API function to call.
            max_retries: Maximum retry attempts.
            endpoint:    Key from ENDPOINT_WEIGHTS for weight accounting.
            is_order:    True for order-creating calls.
            *args, **kwargs: Forwarded to func.

        Returns:
            API response
        """
        if not self._circuit_breaker.can_execute():
            raise Exception("Circuit breaker OPEN - Binance API temporarily unavailable")

        # Check rate-limit budget before making the network call
        self._rate_limiter.check_and_consume(endpoint, is_order=is_order)

        last_exception = None
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                self._circuit_breaker.record_success()
                return result
            except BinanceAPIException as e:
                last_exception = e
                if e.status_code == 429:
                    # Try to honour Retry-After header if available
                    retry_after = None
                    if hasattr(e, "response") and e.response is not None:
                        ra = e.response.headers.get("Retry-After")
                        if ra:
                            try:
                                retry_after = float(ra)
                            except ValueError:
                                pass
                    self._rate_limiter.record_429(retry_after)
                    logger.warning(
                        "Binance 429 received (attempt %d/%d); retry_after=%s",
                        attempt + 1, max_retries, retry_after,
                    )
                # Don't retry on other 4xx client errors
                elif e.status_code and 400 <= e.status_code < 500:
                    self._circuit_breaker.record_failure()
                    raise
                logger.warning(f"Binance API error (attempt {attempt + 1}/{max_retries}): {e}")
            except RateLimitExceeded:
                # Re-raise immediately — no retry makes sense here
                raise
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
            self.client.get_symbol_ticker, symbol=symbol, endpoint="ticker_price"
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
            self.client.get_order_book, symbol=symbol, limit=limit, endpoint="order_book_10"
        )

    def get_exchange_info(self, symbol: str | None = None) -> dict:
        """Fetch exchange metadata, optionally for a single symbol."""
        if self.config.demo_mode:
            symbols = [self._demo_symbol_info(symbol or "BTCUSDT")]
            return {"timezone": "UTC", "serverTime": int(time.time() * 1000), "symbols": symbols}

        if symbol:
            return self._api_call_with_retry(
                self.client.get_symbol_info, symbol=symbol.upper(), endpoint="exchange_info"
            )

        return self._api_call_with_retry(self.client.get_exchange_info, endpoint="exchange_info")

    def _demo_symbol_info(self, symbol: str) -> dict:
        """Demo exchange filters shaped like Binance exchangeInfo responses."""
        return {
            "symbol": symbol.upper(),
            "status": "TRADING",
            "baseAsset": symbol[:-4] if symbol.endswith("USDT") else symbol,
            "quoteAsset": "USDT" if symbol.endswith("USDT") else "",
            "filters": [
                {
                    "filterType": "PRICE_FILTER",
                    "minPrice": "0.01000000",
                    "maxPrice": "10000000.00000000",
                    "tickSize": "0.01000000",
                },
                {
                    "filterType": "LOT_SIZE",
                    "minQty": "0.00001000",
                    "maxQty": "9000.00000000",
                    "stepSize": "0.00001000",
                },
                {
                    "filterType": "MIN_NOTIONAL",
                    "minNotional": "5.00000000",
                    "applyToMarket": True,
                },
            ],
        }

    def get_symbol_rules(self, symbol: str) -> dict:
        """Return normalized exchange filters used for pre-trade validation."""
        info = self.get_exchange_info(symbol)
        if info and "symbols" in info:
            symbol_info = next(
                (item for item in info.get("symbols", []) if item.get("symbol") == symbol.upper()),
                None,
            )
        else:
            symbol_info = info

        if not symbol_info:
            raise ValueError(f"Symbol not found: {symbol}")

        filters = {item.get("filterType"): item for item in symbol_info.get("filters", [])}
        min_notional_filter = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL") or {}
        return {
            "symbol": symbol_info.get("symbol", symbol.upper()),
            "status": symbol_info.get("status"),
            "base_asset": symbol_info.get("baseAsset"),
            "quote_asset": symbol_info.get("quoteAsset"),
            "price_filter": filters.get("PRICE_FILTER", {}),
            "lot_size": filters.get("LOT_SIZE", {}),
            "min_notional": min_notional_filter,
            "raw_filters": filters,
        }

    def validate_order_params(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
    ) -> dict:
        """Validate and normalize an order against Binance symbol filters."""
        symbol = symbol.upper()
        side = side.upper()
        order_type = order_type.upper()
        errors = []
        warnings = []

        rules = self.get_symbol_rules(symbol)
        price_filter = rules.get("price_filter", {})
        lot_size = rules.get("lot_size", {})
        min_notional_filter = rules.get("min_notional", {})

        normalized_quantity = self._round_step(quantity, lot_size.get("stepSize"))
        normalized_price = None
        reference_price = price

        if normalized_quantity <= 0:
            errors.append("Quantity must be greater than zero")

        min_qty = self._to_decimal(lot_size.get("minQty"))
        max_qty = self._to_decimal(lot_size.get("maxQty"))
        quantity_decimal = self._to_decimal(normalized_quantity)
        if min_qty is not None and quantity_decimal < min_qty:
            errors.append(f"Quantity {normalized_quantity} is below minQty {min_qty}")
        if max_qty is not None and quantity_decimal > max_qty:
            errors.append(f"Quantity {normalized_quantity} is above maxQty {max_qty}")

        if order_type == "LIMIT":
            if price is None:
                errors.append("Limit orders require price")
            else:
                normalized_price = self._round_step(price, price_filter.get("tickSize"))
                reference_price = normalized_price
                min_price = self._to_decimal(price_filter.get("minPrice"))
                max_price = self._to_decimal(price_filter.get("maxPrice"))
                price_decimal = self._to_decimal(normalized_price)
                if min_price is not None and price_decimal < min_price:
                    errors.append(f"Price {normalized_price} is below minPrice {min_price}")
                if max_price is not None and price_decimal > max_price:
                    errors.append(f"Price {normalized_price} is above maxPrice {max_price}")
        elif order_type == "MARKET":
            if reference_price is None:
                reference_price = self.get_latest_price(symbol)
        else:
            errors.append(f"Unsupported order type: {order_type}")

        notional = None
        if reference_price is not None:
            notional = float(
                self._to_decimal(normalized_quantity) * self._to_decimal(reference_price)
            )
            min_notional = self._to_decimal(
                min_notional_filter.get("minNotional") or min_notional_filter.get("notional")
            )
            if min_notional is not None and self._to_decimal(notional) < min_notional:
                errors.append(f"Notional {notional:.8f} is below minimum {min_notional}")
        else:
            warnings.append("Unable to calculate notional without a reference price")

        if float(normalized_quantity) != float(quantity):
            warnings.append(f"Quantity rounded down from {quantity} to {normalized_quantity}")
        if normalized_price is not None and float(normalized_price) != float(price):
            warnings.append(f"Price rounded down from {price} to {normalized_price}")

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "normalized_quantity": normalized_quantity,
            "normalized_price": normalized_price,
            "reference_price": reference_price,
            "notional": notional,
            "rules": rules,
        }

    def estimate_market_order_slippage(
        self, symbol: str, side: str, quantity: float, limit: int = 50
    ) -> dict:
        """Estimate effective fill price and slippage for a market order from the order book."""
        symbol = symbol.upper()
        side = side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        book = self.get_order_book(symbol, limit=limit)
        bids = [(float(price), float(qty)) for price, qty in book.get("bids", [])]
        asks = [(float(price), float(qty)) for price, qty in book.get("asks", [])]
        levels = asks if side == "BUY" else bids
        if not bids or not asks or not levels:
            raise ValueError("Order book is empty")

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2

        remaining = float(quantity)
        filled = 0.0
        quote_total = 0.0
        levels_consumed = 0
        fills = []

        for level_price, level_qty in levels:
            if remaining <= 0:
                break
            fill_qty = min(remaining, level_qty)
            quote_total += fill_qty * level_price
            filled += fill_qty
            remaining -= fill_qty
            levels_consumed += 1
            fills.append({"price": level_price, "quantity": fill_qty})

        effective_price = quote_total / filled if filled else None
        if effective_price is None:
            raise ValueError("Unable to fill any quantity from order book")

        if side == "BUY":
            slippage_pct = (effective_price - mid_price) / mid_price * 100
        else:
            slippage_pct = (mid_price - effective_price) / mid_price * 100

        return {
            "symbol": symbol,
            "side": side,
            "requested_quantity": float(quantity),
            "filled_quantity": filled,
            "unfilled_quantity": max(remaining, 0.0),
            "effective_price": effective_price,
            "mid_price": mid_price,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "slippage_pct": slippage_pct,
            "levels_consumed": levels_consumed,
            "fills": fills,
            "order_book_limit": limit,
        }

    def _to_decimal(self, value) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def _round_step(self, value, step) -> float:
        value_decimal = self._to_decimal(value)
        step_decimal = self._to_decimal(step)
        if value_decimal is None:
            return 0.0
        if not step_decimal or step_decimal == 0:
            return float(value_decimal)
        return float(
            (value_decimal / step_decimal).to_integral_value(rounding=ROUND_DOWN) * step_decimal
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
            self.client.get_asset_balance, asset=asset, endpoint="account_balance"
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

        return self._api_call_with_retry(self.client.get_ticker, symbol=symbol)

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
                klines.append(
                    [
                        open_time,
                        f"{open_p:.8f}",
                        f"{high_p:.8f}",
                        f"{low_p:.8f}",
                        f"{close_p:.8f}",
                        f"{volume:.6f}",
                        close_time,
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                    ]
                )
            return klines

        return self._api_call_with_retry(
            self.client.get_klines, symbol=symbol, interval=interval, limit=limit,
            endpoint="klines",
        )

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price=None,
        client_order_id: str | None = None,
    ):
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
            validation = self.validate_order_params(symbol, side, order_type, quantity, price)
            if not validation["valid"]:
                return {"error": "Order failed validation", "validation": validation}
            quantity = validation["normalized_quantity"]
            if validation["normalized_price"] is not None:
                price = validation["normalized_price"]
            order_id = int(time.time() * 1000)
            return {
                "symbol": symbol,
                "orderId": order_id,
                "orderListId": -1,
                "clientOrderId": client_order_id or f"mock_{order_id}",
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

        validation = self.validate_order_params(symbol, side, order_type, quantity, price)
        if not validation["valid"]:
            return {"error": "Order failed validation", "validation": validation}
        quantity = validation["normalized_quantity"]
        if validation["normalized_price"] is not None:
            price = validation["normalized_price"]

        # Live-trading arming gate: refuse live orders unless fully armed
        if self.config.runtime_mode != "live_armed":
            raise ValueError(
                f"Live order placement refused: runtime_mode is '{self.config.runtime_mode}'. "
                "Set BINANCE_TESTNET=false, DEMO_MODE=false, LIVE_TRADING_ENABLED=true, "
                "and LIVE_TRADING_ACK=I_ACCEPT_LIVE_BINANCE_SPOT_RISK to arm live trading."
            )

        if order_type == "MARKET":
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
            }
            if client_order_id:
                params["newClientOrderId"] = client_order_id
            return self._api_call_with_retry(
                self.client.create_order, **params, max_retries=1,
                endpoint="create_order", is_order=True
            )
        elif order_type == "LIMIT":
            if price is None:
                raise ValueError("Limit orders require price")
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "timeInForce": "GTC",
                "quantity": quantity,
                "price": str(price),
            }
            if client_order_id:
                params["newClientOrderId"] = client_order_id
            return self._api_call_with_retry(
                self.client.create_order, **params, max_retries=1,
                endpoint="create_order", is_order=True
            )
        else:
            raise ValueError("Unsupported order type")

    def get_order(
        self, symbol: str, order_id: int | None = None, client_order_id: str | None = None
    ):
        """
        Get an order by exchange order ID or original client order ID.
        """
        if self.config.demo_mode:
            now = int(time.time() * 1000)
            return {
                "symbol": symbol,
                "orderId": order_id or now,
                "orderListId": -1,
                "clientOrderId": client_order_id or f"mock_{order_id or now}",
                "price": "0.00000000",
                "origQty": "0.00100000",
                "executedQty": "0.00100000",
                "cummulativeQuoteQty": "50.00000000",
                "status": "FILLED",
                "timeInForce": "GTC",
                "type": "MARKET",
                "side": "BUY",
                "time": now,
                "updateTime": now,
            }

        params = {"symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise ValueError("order_id or client_order_id is required")

        return self._api_call_with_retry(self.client.get_order, **params, endpoint="get_order")

    def get_account_trades(self, symbol: str, order_id: int | None = None, limit: int = 100):
        """
        Get account trade fills, optionally filtered by order ID.
        """
        if self.config.demo_mode:
            return []

        params = {"symbol": symbol, "limit": limit}
        if order_id:
            params["orderId"] = order_id

        return self._api_call_with_retry(self.client.get_my_trades, **params)

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
            max_retries=2, endpoint="cancel_order",
        )

    def create_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        stop_limit_price: float,
        client_order_id: str | None = None,
        stop_client_order_id: str | None = None,
    ) -> dict:
        """
        Place an OCO (One-Cancels-the-Other) order.

        An OCO pairs a limit order with a stop-limit order on the same symbol.
        If either leg triggers, the exchange cancels the other automatically.

        Args:
            symbol: Trading pair (e.g. 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Quantity for both legs
            price: Limit-order price
            stop_price: Stop trigger price
            stop_limit_price: Stop-limit price (limit price after trigger)
            client_order_id: Optional client ID for the limit leg
            stop_client_order_id: Optional client ID for the stop-limit leg

        Returns:
            Binance OCO response dict with orderReports list
        """
        if self.config.demo_mode:
            now = int(time.time() * 1000)
            base_id = now
            return {
                "orderListId": base_id,
                "contingencyType": "OCO",
                "listStatusType": "EXEC_STARTED",
                "listOrderStatus": "EXECUTING",
                "listClientOrderId": client_order_id or f"mock_oco_{base_id}",
                "transactionTime": now,
                "symbol": symbol,
                "orders": [
                    {"symbol": symbol, "orderId": base_id,
                     "clientOrderId": client_order_id or f"mock_lmt_{base_id}"},
                    {"symbol": symbol, "orderId": base_id + 1,
                     "clientOrderId": stop_client_order_id or f"mock_stp_{base_id}"},
                ],
                "orderReports": [
                    {
                        "symbol": symbol, "orderId": base_id,
                        "clientOrderId": client_order_id or f"mock_lmt_{base_id}",
                        "price": str(price), "origQty": str(quantity),
                        "executedQty": "0.00000000", "status": "NEW",
                        "type": "LIMIT_MAKER", "side": side,
                    },
                    {
                        "symbol": symbol, "orderId": base_id + 1,
                        "clientOrderId": stop_client_order_id or f"mock_stp_{base_id}",
                        "price": str(stop_limit_price), "stopPrice": str(stop_price),
                        "origQty": str(quantity),
                        "executedQty": "0.00000000", "status": "NEW",
                        "type": "STOP_LOSS_LIMIT", "side": side,
                    },
                ],
            }

        # Live-trading arming gate
        if self.config.runtime_mode != "live_armed":
            raise ValueError(
                f"Live OCO order refused: runtime_mode is '{self.config.runtime_mode}'."
            )

        params: dict = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": str(price),
            "stopPrice": str(stop_price),
            "stopLimitPrice": str(stop_limit_price),
            "stopLimitTimeInForce": "GTC",
        }
        if client_order_id:
            params["listClientOrderId"] = client_order_id
        if stop_client_order_id:
            params["stopClientOrderId"] = stop_client_order_id

        return self._api_call_with_retry(
            self.client.create_oco_order, **params,
            max_retries=1, endpoint="create_oco_order", is_order=True,
        )
