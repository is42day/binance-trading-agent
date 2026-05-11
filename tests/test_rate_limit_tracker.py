"""
Tests for RateLimitTracker (Priority 3 — Task 7).

Scenarios:
- Repeated calls accumulate weight correctly
- Budget exhaustion raises RateLimitExceeded
- Order-rate exhaustion raises RateLimitExceeded
- Window reset clears weight after window_seconds
- 429 activates hold-off; calls during hold-off raise RateLimitExceeded
- 429 with explicit Retry-After respects the duration
- get_status() returns correct snapshot
- API endpoint /api/v1/system/rate-limits responds
- BinanceAPIClient integrates tracker (demo mode — no real network)
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from binance_trade_agent.clients.rate_limit_tracker import (
    RateLimitTracker,
    RateLimitExceeded,
    ENDPOINT_WEIGHTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tracker(**kwargs) -> RateLimitTracker:
    """Create a fresh tracker with defaults overrideable via kwargs."""
    defaults = {
        "weight_budget": 100,
        "safety_margin": 0.80,   # threshold = 80
        "order_budget_per_sec": 5,
        "window_seconds": 60.0,
    }
    defaults.update(kwargs)
    return RateLimitTracker(**defaults)


# ---------------------------------------------------------------------------
# Weight accumulation
# ---------------------------------------------------------------------------

class TestWeightAccumulation:
    def test_single_call_consumes_weight(self):
        t = _tracker()
        w = t.check_and_consume("ticker_price")
        assert w == ENDPOINT_WEIGHTS["ticker_price"]
        assert t.get_status()["weight_used"] == ENDPOINT_WEIGHTS["ticker_price"]

    def test_repeated_calls_accumulate(self):
        t = _tracker()
        for _ in range(5):
            t.check_and_consume("ticker_price")
        assert t.get_status()["weight_used"] == 5 * ENDPOINT_WEIGHTS["ticker_price"]

    def test_unknown_endpoint_uses_default_weight(self):
        t = _tracker()
        t.check_and_consume("some_new_endpoint")
        assert t.get_status()["weight_used"] == ENDPOINT_WEIGHTS["unknown"]

    def test_different_endpoint_weights(self):
        t = _tracker()
        t.check_and_consume("account_balance")
        assert t.get_status()["weight_used"] == ENDPOINT_WEIGHTS["account_balance"]

    def test_total_calls_increments(self):
        t = _tracker()
        t.check_and_consume("ticker_price")
        t.check_and_consume("ticker_price")
        assert t.get_status()["total_calls"] == 2


# ---------------------------------------------------------------------------
# Budget exhaustion
# ---------------------------------------------------------------------------

class TestBudgetExhaustion:
    def test_near_threshold_raises_rate_limit_exceeded(self):
        # budget=10, margin=0.8 → threshold=8; ticker_price weight=1
        t = RateLimitTracker(weight_budget=10, safety_margin=0.8)
        for _ in range(8):
            t.check_and_consume("ticker_price")
        with pytest.raises(RateLimitExceeded):
            t.check_and_consume("ticker_price")

    def test_blocked_count_increments(self):
        t = RateLimitTracker(weight_budget=10, safety_margin=0.8)
        for _ in range(8):
            t.check_and_consume("ticker_price")
        try:
            t.check_and_consume("ticker_price")
        except RateLimitExceeded:
            pass
        assert t.get_status()["total_blocked"] == 1

    def test_heavy_endpoint_can_trigger_threshold_in_one_call(self):
        # budget=15, threshold=12; account_balance=10 → first call ok, second blocked
        t = RateLimitTracker(weight_budget=15, safety_margin=0.8)
        t.check_and_consume("account_balance")
        with pytest.raises(RateLimitExceeded):
            t.check_and_consume("account_balance")


# ---------------------------------------------------------------------------
# Order rate limiting
# ---------------------------------------------------------------------------

class TestOrderRateLimit:
    def test_order_calls_count_against_order_budget(self):
        t = _tracker(order_budget_per_sec=2)
        t.check_and_consume("create_order", is_order=True)
        t.check_and_consume("create_order", is_order=True)
        with pytest.raises(RateLimitExceeded) as exc_info:
            t.check_and_consume("create_order", is_order=True)
        assert "order rate" in str(exc_info.value).lower()

    def test_non_order_calls_not_counted_against_order_budget(self):
        t = _tracker(order_budget_per_sec=2)
        # Should not raise even after many calls
        for _ in range(5):
            t.check_and_consume("ticker_price", is_order=False)


# ---------------------------------------------------------------------------
# Window reset
# ---------------------------------------------------------------------------

class TestWindowReset:
    def test_weight_resets_after_window(self):
        t = RateLimitTracker(weight_budget=10, safety_margin=0.8, window_seconds=0.05)
        for _ in range(7):
            t.check_and_consume("ticker_price")
        time.sleep(0.06)  # Wait for window to expire
        # After reset, should allow calls again
        t.check_and_consume("ticker_price")
        assert t.get_status()["weight_used"] == 1


# ---------------------------------------------------------------------------
# 429 / Retry-After handling
# ---------------------------------------------------------------------------

class Test429Handling:
    def test_record_429_activates_holdoff(self):
        t = _tracker()
        t.record_429(retry_after_seconds=60.0)
        with pytest.raises(RateLimitExceeded) as exc_info:
            t.check_and_consume("ticker_price")
        assert "hold-off" in str(exc_info.value).lower()

    def test_holdoff_expires_after_delay(self):
        t = _tracker()
        t.record_429(retry_after_seconds=0.05)
        time.sleep(0.06)
        # Should succeed now
        t.check_and_consume("ticker_price")

    def test_retry_after_remaining_in_status(self):
        t = _tracker()
        t.record_429(retry_after_seconds=30.0)
        status = t.get_status()
        assert status["in_holdoff"] is True
        assert status["retry_after_remaining"] is not None
        assert status["retry_after_remaining"] > 0

    def test_default_holdoff_60s_when_no_retry_after(self):
        t = _tracker()
        t.record_429()   # No retry_after argument
        status = t.get_status()
        assert status["in_holdoff"] is True
        assert status["retry_after_remaining"] > 55  # 60s minus tiny elapsed


# ---------------------------------------------------------------------------
# get_status()
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_status_fields_present(self):
        t = _tracker()
        status = t.get_status()
        required = {
            "weight_used", "weight_budget", "weight_utilization_pct",
            "safety_threshold", "window_seconds", "window_age_seconds",
            "orders_this_second", "order_budget_per_sec",
            "retry_after_remaining", "in_holdoff",
            "total_calls", "total_weight", "total_blocked",
        }
        assert required.issubset(set(status.keys()))

    def test_utilization_pct_updates(self):
        t = RateLimitTracker(weight_budget=100, safety_margin=1.0)
        t.check_and_consume("account_balance")   # weight=10
        status = t.get_status()
        assert status["weight_utilization_pct"] == 10.0


# ---------------------------------------------------------------------------
# BinanceAPIClient integration (demo mode — no real network)
# ---------------------------------------------------------------------------

class TestBinanceClientIntegration:
    def test_get_rate_limit_status_available(self):
        from binance_trade_agent.clients.binance_client import BinanceAPIClient
        client = BinanceAPIClient()
        status = client.get_rate_limit_status()
        assert "weight_used" in status
        assert "weight_budget" in status

    def test_demo_mode_does_not_consume_weight(self):
        """Demo mode short-circuits before _api_call_with_retry — weight stays 0."""
        from binance_trade_agent.clients.binance_client import BinanceAPIClient
        client = BinanceAPIClient()
        assert client.config.demo_mode is True
        client.get_latest_price("BTCUSDT")
        # Demo path bypasses _api_call_with_retry, so weight_used stays 0
        assert client.get_rate_limit_status()["weight_used"] == 0


# ---------------------------------------------------------------------------
# API endpoint test
# ---------------------------------------------------------------------------

class TestRateLimitEndpoint:
    def test_endpoint_returns_rate_limit_status(self):
        from fastapi.testclient import TestClient
        from binance_trade_agent.api.api import app

        client = TestClient(app)
        resp = client.get(
            "/api/v1/system/rate-limits",
            headers={"X-API-Token": "test-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "weight_used" in data
        assert "in_holdoff" in data
