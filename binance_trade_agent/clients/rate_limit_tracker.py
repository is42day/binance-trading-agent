"""
Rate-limit tracker for the Binance REST API.

Binance enforces two independent limits per rolling 1-minute window:
  - Request weight budget:  default 1 200 / min (spot)
  - Order count budget:     default 10 / sec, 100 000 / 24 h (spot)

This tracker keeps a local approximate count and blocks order placement
when the estimated weight is within a configurable safety margin of the
budget.  It is NOT a replacement for Binance's server-side enforcement;
it is a local guard that catches runaway loops before a 429 arrives.

Weight table (Binance spot REST, typical values — verifiable in exchange info):
  ticker price          1
  order book depth 5   1 / depth-level bucket
  order book depth 10  1
  exchange info        10
  klines              1..2  (1 per 500 candles)
  account balance      10
  create order         1
  cancel order         1
  get order            2

Design:
  - Thread-safe (Lock around all mutations).
  - Sliding window: weight is reset at the start of each new minute.
  - 429 handling: records Retry-After if provided and refuses calls until expiry.
  - Trading block: `check_and_consume(endpoint, is_order=False)` raises
    `RateLimitExceeded` if budget is near exhaustion.
"""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Endpoint weight table (approximate Binance spot weights)
# ---------------------------------------------------------------------------

ENDPOINT_WEIGHTS: Dict[str, int] = {
    "ticker_price": 1,
    "order_book_5": 1,
    "order_book_10": 1,
    "order_book_50": 5,
    "order_book_100": 10,
    "exchange_info": 10,
    "klines": 2,
    "account_balance": 10,
    "create_order": 1,
    "create_oco_order": 1,
    "cancel_order": 1,
    "cancel_oco_order": 1,
    "get_order": 2,
    "get_open_orders": 3,
    "get_all_orders": 10,
    "unknown": 1,
}

# Default safety thresholds
DEFAULT_WEIGHT_BUDGET: int = 1_200  # per 1-minute window
DEFAULT_WEIGHT_SAFETY_MARGIN: float = 0.85  # block at 85 % utilization
DEFAULT_ORDER_BUDGET_1S: int = 10  # orders per second
DEFAULT_WINDOW_SECONDS: float = 60.0


class RateLimitExceeded(Exception):
    """Raised when the local rate-limit guard would be breached."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# RateLimitTracker
# ---------------------------------------------------------------------------


class RateLimitTracker:
    """
    Thread-safe sliding-window weight tracker.

    Args:
        weight_budget:          Total weight allowed per window.
        safety_margin:          Fraction of budget at which calls are blocked.
        order_budget_per_sec:   Order calls allowed per second.
        window_seconds:         Length of the weight window in seconds.
    """

    def __init__(
        self,
        weight_budget: int = DEFAULT_WEIGHT_BUDGET,
        safety_margin: float = DEFAULT_WEIGHT_SAFETY_MARGIN,
        order_budget_per_sec: int = DEFAULT_ORDER_BUDGET_1S,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ):
        self._weight_budget = weight_budget
        self._safety_threshold = int(weight_budget * safety_margin)
        self._order_budget_per_sec = order_budget_per_sec
        self._window_seconds = window_seconds

        self._lock = Lock()

        # Weight window
        self._window_start: float = time.time()
        self._weight_used: int = 0

        # Order rate (per second)
        self._order_second_start: float = time.time()
        self._orders_this_second: int = 0

        # 429 hold-off
        self._retry_after_until: Optional[float] = None

        # Totals for observability
        self._total_calls: int = 0
        self._total_weight: int = 0
        self._total_blocked: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_consume(
        self,
        endpoint: str,
        is_order: bool = False,
    ) -> int:
        """
        Check whether the call is within budget and record the weight.

        Args:
            endpoint: One of the keys in ENDPOINT_WEIGHTS (or "unknown").
            is_order: True for order-creating calls (counted against order budget too).

        Returns:
            Weight consumed for this call.

        Raises:
            RateLimitExceeded: if weight budget is near exhaustion, retry-after
                               period hasn't expired, or order rate exceeded.
        """
        weight = ENDPOINT_WEIGHTS.get(endpoint, ENDPOINT_WEIGHTS["unknown"])

        with self._lock:
            now = time.time()
            self._maybe_reset_window(now)
            self._maybe_reset_order_second(now)

            # 1. Retry-After hold
            if self._retry_after_until and now < self._retry_after_until:
                remaining = self._retry_after_until - now
                self._total_blocked += 1
                raise RateLimitExceeded(
                    f"Binance 429 hold-off active; {remaining:.1f}s remaining",
                    retry_after=remaining,
                )

            # 2. Weight budget
            if self._weight_used + weight > self._safety_threshold:
                self._total_blocked += 1
                raise RateLimitExceeded(
                    f"Weight budget near limit: {self._weight_used}/{self._weight_budget} "
                    f"(threshold {self._safety_threshold}). Blocked call to '{endpoint}'."
                )

            # 3. Order rate
            if is_order and self._orders_this_second >= self._order_budget_per_sec:
                self._total_blocked += 1
                raise RateLimitExceeded(
                    f"Order rate limit: {self._orders_this_second} orders in current second "
                    f"(budget {self._order_budget_per_sec})."
                )

            # Consume
            self._weight_used += weight
            self._total_weight += weight
            self._total_calls += 1
            if is_order:
                self._orders_this_second += 1

        logger.debug(
            "RateLimit: endpoint=%s weight=%d used=%d/%d",
            endpoint,
            weight,
            self._weight_used,
            self._weight_budget,
        )
        return weight

    def record_429(self, retry_after_seconds: Optional[float] = None) -> None:
        """
        Record a 429 response from Binance and activate hold-off.

        Args:
            retry_after_seconds: Value from Retry-After header (seconds).
                                 Defaults to 60s if not provided.
        """
        hold = retry_after_seconds if retry_after_seconds is not None else 60.0
        with self._lock:
            self._retry_after_until = time.time() + hold
            logger.warning("Binance 429 received. Rate-limit hold-off for %.0fs", hold)

    def get_status(self) -> dict:
        """Return a snapshot of current rate-limit state (safe to call anytime)."""
        with self._lock:
            now = time.time()
            self._maybe_reset_window(now)
            retry_after_remaining = (
                max(0.0, self._retry_after_until - now)
                if self._retry_after_until and now < self._retry_after_until
                else None
            )
            window_age = now - self._window_start
            return {
                "weight_used": self._weight_used,
                "weight_budget": self._weight_budget,
                "weight_utilization_pct": round(self._weight_used / self._weight_budget * 100, 1),
                "safety_threshold": self._safety_threshold,
                "window_seconds": self._window_seconds,
                "window_age_seconds": round(window_age, 1),
                "orders_this_second": self._orders_this_second,
                "order_budget_per_sec": self._order_budget_per_sec,
                "retry_after_remaining": (
                    round(retry_after_remaining, 1) if retry_after_remaining else None
                ),
                "in_holdoff": retry_after_remaining is not None,
                "total_calls": self._total_calls,
                "total_weight": self._total_weight,
                "total_blocked": self._total_blocked,
            }

    # ------------------------------------------------------------------
    # Internal helpers (must be called under lock)
    # ------------------------------------------------------------------

    def _maybe_reset_window(self, now: float) -> None:
        if now - self._window_start >= self._window_seconds:
            self._window_start = now
            self._weight_used = 0

    def _maybe_reset_order_second(self, now: float) -> None:
        if now - self._order_second_start >= 1.0:
            self._order_second_start = now
            self._orders_this_second = 0


# ---------------------------------------------------------------------------
# Module singleton
# ---------------------------------------------------------------------------

_tracker: Optional[RateLimitTracker] = None


def get_rate_limit_tracker(**kwargs) -> RateLimitTracker:
    """Return the module-level singleton, creating it on first call."""
    global _tracker
    if _tracker is None:
        _tracker = RateLimitTracker(**kwargs)
    return _tracker
