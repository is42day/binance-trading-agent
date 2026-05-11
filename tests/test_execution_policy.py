"""
Tests for the Execution Policy layer (Priority 5 — Tasks 5.1–5.5).

Verifies:
- Wide spread blocks order entry
- High slippage blocks market/maker_first orders
- Limit price is correctly rounded to tick size via validate_order_params
- Filter validation failure blocks the order
- Market mode passes when spread and slippage are within thresholds
- maker_first produces a LIMIT order at the offset price
- Empty order book blocks execution
"""

from unittest.mock import MagicMock, patch

import pytest

from binance_trade_agent.core.execution_policy import ExecutionPolicy, ExecutionPolicyEngine


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_policy(**kwargs) -> ExecutionPolicy:
    defaults = dict(
        execution_mode="market",
        max_spread_pct=0.10,
        max_slippage_pct=0.15,
        limit_price_offset_bps=5,
        stale_order_seconds=60,
        depth_limit=10,
    )
    defaults.update(kwargs)
    return ExecutionPolicy(**defaults)


def _make_client(
    bid=50000.0,
    ask=50001.0,
    slippage_pct=0.05,
    validation_valid=True,
    validation_errors=None,
    normalized_qty=0.001,
    normalized_price=None,
) -> MagicMock:
    """Create a mock BinanceAPIClient with configurable order book and slippage."""
    client = MagicMock()

    # validate_order_params
    client.validate_order_params.return_value = {
        "valid": validation_valid,
        "errors": validation_errors or [],
        "warnings": [],
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "normalized_quantity": normalized_qty,
        "normalized_price": normalized_price,
    }

    # get_order_book
    client.get_order_book.return_value = {
        "bids": [[str(bid), "1.0"]],
        "asks": [[str(ask), "1.0"]],
    }

    # estimate_market_order_slippage
    mid = (bid + ask) / 2
    client.estimate_market_order_slippage.return_value = {
        "slippage_pct": slippage_pct,
        "effective_price": mid * (1 + slippage_pct / 100),
        "mid_price": mid,
        "levels_consumed": 1,
        "unfilled_quantity": 0.0,
    }

    return client


# ---------------------------------------------------------------------------
# Filter validation tests
# ---------------------------------------------------------------------------

class TestFilterValidation:
    def test_invalid_filter_blocks_order(self):
        client = _make_client(validation_valid=False, validation_errors=["Qty below minQty"])
        engine = ExecutionPolicyEngine(client, _make_policy())
        result = engine.evaluate("BTCUSDT", "BUY", 0.00000001)
        assert not result.approved
        assert result.blocked_reason == "filter_validation_failed"
        assert "Qty below minQty" in result.metadata.get("errors", [])

    def test_validation_exception_blocks_order(self):
        client = MagicMock()
        client.validate_order_params.side_effect = RuntimeError("exchange offline")
        engine = ExecutionPolicyEngine(client, _make_policy())
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert not result.approved
        assert result.blocked_reason == "filter_validation_error"


# ---------------------------------------------------------------------------
# Spread tests
# ---------------------------------------------------------------------------

class TestSpreadCheck:
    def test_wide_spread_blocks_entry(self):
        # bid=50000, ask=50200 → spread ≈ 0.40 % > 0.10 %
        client = _make_client(bid=50000.0, ask=50200.0)
        engine = ExecutionPolicyEngine(client, _make_policy(max_spread_pct=0.10))
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert not result.approved
        assert result.blocked_reason == "spread_too_wide"
        assert result.spread_pct is not None
        assert result.spread_pct > 0.10

    def test_acceptable_spread_passes(self):
        # bid=50000, ask=50001 → spread ≈ 0.002 % < 0.10 %
        client = _make_client(bid=50000.0, ask=50001.0)
        engine = ExecutionPolicyEngine(client, _make_policy())
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert result.approved

    def test_empty_order_book_blocks(self):
        client = MagicMock()
        client.validate_order_params.return_value = {
            "valid": True, "errors": [], "warnings": [],
            "symbol": "BTCUSDT", "side": "BUY", "order_type": "MARKET",
            "normalized_quantity": 0.001, "normalized_price": None,
        }
        client.get_order_book.return_value = {"bids": [], "asks": []}
        engine = ExecutionPolicyEngine(client, _make_policy())
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert not result.approved
        assert result.blocked_reason == "order_book_empty"


# ---------------------------------------------------------------------------
# Slippage tests
# ---------------------------------------------------------------------------

class TestSlippageCheck:
    def test_high_slippage_blocks_market_order(self):
        # slippage_pct=0.20 > max_slippage_pct=0.15
        client = _make_client(slippage_pct=0.20)
        engine = ExecutionPolicyEngine(client, _make_policy(execution_mode="market", max_slippage_pct=0.15))
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert not result.approved
        assert result.blocked_reason == "slippage_too_high"
        assert result.slippage_pct is not None
        assert result.slippage_pct > 0.15

    def test_acceptable_slippage_passes_market_order(self):
        client = _make_client(slippage_pct=0.05)
        engine = ExecutionPolicyEngine(client, _make_policy(execution_mode="market", max_slippage_pct=0.15))
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert result.approved
        assert result.order_type == "MARKET"
        assert result.limit_price is None

    def test_slippage_check_runs_for_maker_first(self):
        client = _make_client(slippage_pct=0.20)
        engine = ExecutionPolicyEngine(client, _make_policy(execution_mode="maker_first", max_slippage_pct=0.15))
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert not result.approved
        assert result.blocked_reason == "slippage_too_high"

    def test_slippage_check_skipped_for_limit_mode(self):
        """In pure limit mode, slippage check is not applied."""
        client = _make_client(slippage_pct=0.50)  # Very high slippage
        engine = ExecutionPolicyEngine(client, _make_policy(execution_mode="limit", max_slippage_pct=0.10))
        result = engine.evaluate("BTCUSDT", "BUY", 0.001, price=50000.0)
        # Should be approved because limit mode skips slippage check
        assert result.approved
        assert result.order_type == "LIMIT"


# ---------------------------------------------------------------------------
# Limit price rounding tests
# ---------------------------------------------------------------------------

class TestLimitPriceRounding:
    def test_limit_price_uses_normalized_price(self):
        """validate_order_params normalises the limit price; engine must use it."""
        client = _make_client(slippage_pct=0.05, normalized_price=49999.50)
        client.validate_order_params.return_value["normalized_price"] = 49999.50
        engine = ExecutionPolicyEngine(client, _make_policy(execution_mode="limit"))
        result = engine.evaluate("BTCUSDT", "BUY", 0.001, price=50000.0)
        assert result.approved
        assert result.limit_price == 49999.50
        assert result.order_type == "LIMIT"

    def test_maker_first_buy_price_below_mid(self):
        """maker_first BUY limit should be below mid price."""
        mid = 50000.5
        # Provide tick-rounded price from validate_order_params for the secondary call
        def mock_validate(symbol, side, ot, qty, price=None):
            return {
                "valid": True, "errors": [], "warnings": [],
                "symbol": "BTCUSDT", "side": side, "order_type": ot,
                "normalized_quantity": qty, "normalized_price": price,
            }
        client = _make_client(bid=50000.0, ask=50001.0, slippage_pct=0.05)
        client.validate_order_params.side_effect = mock_validate
        engine = ExecutionPolicyEngine(client, _make_policy(
            execution_mode="maker_first",
            limit_price_offset_bps=5,   # 0.05 % below mid for buy
        ))
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert result.approved
        assert result.order_type == "LIMIT"
        # Limit price should be below mid price
        assert result.limit_price < mid

    def test_maker_first_sell_price_above_mid(self):
        """maker_first SELL limit should be above mid price."""
        def mock_validate(symbol, side, ot, qty, price=None):
            return {
                "valid": True, "errors": [], "warnings": [],
                "symbol": "BTCUSDT", "side": side, "order_type": ot,
                "normalized_quantity": qty, "normalized_price": price,
            }
        client = _make_client(bid=50000.0, ask=50001.0, slippage_pct=0.05)
        client.validate_order_params.side_effect = mock_validate
        client.estimate_market_order_slippage.return_value = {
            "slippage_pct": 0.05, "effective_price": 50000.525,
            "mid_price": 50000.5, "levels_consumed": 1, "unfilled_quantity": 0.0,
        }
        engine = ExecutionPolicyEngine(client, _make_policy(
            execution_mode="maker_first", limit_price_offset_bps=5,
        ))
        result = engine.evaluate("BTCUSDT", "SELL", 0.001)
        assert result.approved
        assert result.order_type == "LIMIT"
        mid = 50000.5
        assert result.limit_price > mid


# ---------------------------------------------------------------------------
# Metadata / decision log tests
# ---------------------------------------------------------------------------

class TestDecisionMetadata:
    def test_blocked_result_contains_spread_pct(self):
        client = _make_client(bid=50000.0, ask=50200.0)
        engine = ExecutionPolicyEngine(client, _make_policy(max_spread_pct=0.10))
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert result.spread_pct is not None
        assert result.blocked_reason == "spread_too_wide"

    def test_approved_result_contains_spread_and_slippage(self):
        client = _make_client(slippage_pct=0.05)
        engine = ExecutionPolicyEngine(client, _make_policy())
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        assert result.approved
        assert result.spread_pct is not None
        assert result.slippage_pct is not None

    def test_to_dict_contains_required_fields(self):
        client = _make_client(slippage_pct=0.05)
        engine = ExecutionPolicyEngine(client, _make_policy())
        result = engine.evaluate("BTCUSDT", "BUY", 0.001)
        d = result.to_dict()
        for key in ("approved", "blocked_reason", "spread_pct", "slippage_pct",
                    "order_type", "quantity", "mid_price", "metadata"):
            assert key in d, f"Missing key: {key}"

    def test_policy_to_dict(self):
        policy = _make_policy(execution_mode="limit", max_spread_pct=0.05)
        d = policy.to_dict()
        assert d["execution_mode"] == "limit"
        assert d["max_spread_pct"] == 0.05
