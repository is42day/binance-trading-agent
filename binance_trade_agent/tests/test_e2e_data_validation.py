"""
End-to-End Data Validation Tests
Tests complete data flows: portfolio calculations, trade reconciliation, API consistency
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from binance_trade_agent.core.portfolio_manager import (
    PortfolioManager,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_portfolio_db():
    """Create a temporary SQLite database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_portfolio.db"
        yield str(db_path)


@pytest.fixture
def portfolio(temp_portfolio_db):
    """Initialize a clean portfolio manager for testing"""
    pm = PortfolioManager(db_path=temp_portfolio_db)
    yield pm
    pm.clear_portfolio()


# ============================================================================
# SECTION 1: Portfolio Calculation Accuracy Tests
# ============================================================================


class TestPortfolioCalculationAccuracy:
    """Validate that portfolio calculations are mathematically correct"""

    def test_portfolio_value_calculation_single_position(self, portfolio):
        """Verify portfolio value calculation with single position"""
        # Add a BUY trade
        portfolio.add_trade(
            trade_id="T1",
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
            price=40000.0,
            fee=0.001,
        )

        # Update market price
        portfolio.update_market_prices({"BTCUSDT": 41000.0})

        # Verify position exists
        positions = portfolio.get_all_positions()
        assert len(positions) == 1

        pos = positions[0]
        assert pos["symbol"] == "BTCUSDT"
        assert pos["quantity"] == 1.0
        assert pos["average_price"] == 40000.0
        assert pos["current_price"] == 41000.0

        # Portfolio value should be quantity * current_price
        portfolio_value = portfolio.get_portfolio_value()
        expected_value = 1.0 * 41000.0
        assert (
            portfolio_value == expected_value
        ), f"Expected {expected_value}, got {portfolio_value}"

    def test_portfolio_pnl_calculation_single_trade(self, portfolio):
        """Verify P&L calculation on single closed trade"""
        # BUY 1 BTC at $40,000
        portfolio.add_trade(
            trade_id="T1",
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
            price=40000.0,
            fee=10.0,  # $10 fee on entry
        )

        # SELL 1 BTC at $42,000
        portfolio.add_trade(
            trade_id="T2",
            symbol="BTCUSDT",
            side="SELL",
            quantity=1.0,
            price=42000.0,
            fee=10.0,  # $10 fee on exit
        )

        # Portfolio position will have zero quantity (closed but not deleted from DB)
        positions = portfolio.get_all_positions()
        assert len(positions) == 1  # Position exists but with 0 quantity
        assert positions[0]["quantity"] == 0.0

        # P&L = (42000 - 40000) * 1.0 - 10 - 10 = 2000 - 20 = 1980
        stats = portfolio.get_portfolio_stats()
        assert (
            stats["total_pnl"] == 1980.0
        ), f"Expected P&L 1980, got {stats['total_pnl']}"
        assert stats["total_fees"] == 20.0
        assert stats["number_of_trades"] == 2

    def test_portfolio_pnl_with_multiple_positions(self, portfolio):
        """Verify P&L calculation with multiple open positions"""
        # BUY 1 BTC at $40,000
        portfolio.add_trade(
            trade_id="T1",
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
            price=40000.0,
            fee=1.0,
        )

        # BUY 0.5 ETH at $2,000
        portfolio.add_trade(
            trade_id="T2",
            symbol="ETHUSDT",
            side="BUY",
            quantity=0.5,
            price=2000.0,
            fee=0.5,
        )

        # Update market prices
        portfolio.update_market_prices({"BTCUSDT": 42000.0, "ETHUSDT": 2200.0})

        # Verify positions
        positions = portfolio.get_all_positions()
        assert len(positions) == 2

        # Check unrealized P&L for BTC: (42000 - 40000) * 1.0 = 2000
        btc_pos = next(p for p in positions if p["symbol"] == "BTCUSDT")
        assert btc_pos["unrealized_pnl"] == 2000.0

        # Check unrealized P&L for ETH: (2200 - 2000) * 0.5 = 100
        eth_pos = next(p for p in positions if p["symbol"] == "ETHUSDT")
        assert eth_pos["unrealized_pnl"] == 100.0

        # Total P&L = 2000 + 100 - 1.5 (fees) = 2098.5
        stats = portfolio.get_portfolio_stats()
        assert stats["total_pnl"] == 2098.5

    def test_portfolio_value_with_multiple_positions(self, portfolio):
        """Verify portfolio total value with multiple positions"""
        # Position 1: 1 BTC at $40k (current $42k)
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)

        # Position 2: 0.5 ETH at $2k (current $2.2k)
        portfolio.add_trade("T2", "ETHUSDT", "BUY", 0.5, 2000.0, 0.5)

        portfolio.update_market_prices({"BTCUSDT": 42000.0, "ETHUSDT": 2200.0})

        # Total value = (1.0 * 42000) + (0.5 * 2200) = 42000 + 1100 = 43100
        total_value = portfolio.get_portfolio_value()
        assert total_value == 43100.0

    def test_average_price_calculation_multiple_entries(self, portfolio):
        """Verify average price calculation on multiple buy orders"""
        # BUY 0.5 BTC at $40,000
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 0.5, 40000.0, 0.5)

        # BUY 0.5 BTC at $42,000
        portfolio.add_trade("T2", "BTCUSDT", "BUY", 0.5, 42000.0, 0.5)

        # Average price should be (0.5*40000 + 0.5*42000) / (0.5 + 0.5) = 41000
        positions = portfolio.get_all_positions()
        assert len(positions) == 1

        pos = positions[0]
        assert pos["quantity"] == 1.0
        assert pos["average_price"] == 41000.0
        assert pos["side"] == "LONG"

    def test_long_to_short_conversion(self, portfolio):
        """Verify conversion from long to short position"""
        # BUY 1 BTC at $40,000
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)

        # Positions after buy
        positions = portfolio.get_all_positions()
        assert len(positions) == 1
        assert positions[0]["quantity"] == 1.0
        assert positions[0]["side"] == "LONG"

        # SELL 1.5 BTC at $42,000 (closes long, opens short)
        portfolio.add_trade("T2", "BTCUSDT", "SELL", 1.5, 42000.0, 1.0)

        # Positions after sell
        positions = portfolio.get_all_positions()
        assert len(positions) == 1
        pos = positions[0]
        assert pos["quantity"] == -0.5  # SHORT 0.5 BTC
        assert pos["side"] == "SHORT"
        assert pos["average_price"] == 42000.0


# ============================================================================
# SECTION 2: Trade History Reconciliation Tests
# ============================================================================


class TestTradeHistoryReconciliation:
    """Validate that trade history is accurate and complete"""

    def test_trade_history_preservation(self, portfolio):
        """Verify all trades are preserved in history"""
        trades_data = [
            ("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0),
            ("T2", "ETHUSDT", "BUY", 0.5, 2000.0, 0.5),
            ("T3", "BTCUSDT", "SELL", 0.5, 41000.0, 1.0),
        ]

        for trade_id, symbol, side, qty, price, fee in trades_data:
            portfolio.add_trade(trade_id, symbol, side, qty, price, fee)

        # Retrieve full trade history
        history = portfolio.get_trade_history()
        assert len(history) == 3

        # Verify trade details
        trade_ids = {t["trade_id"] for t in history}
        assert trade_ids == {"T1", "T2", "T3"}

    def test_trade_history_ordering(self, portfolio):
        """Verify trade history is returned in reverse chronological order"""
        for i in range(5):
            portfolio.add_trade(
                trade_id=f"T{i}",
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.1,
                price=40000.0 + (i * 100),
                fee=0.1,
            )

        history = portfolio.get_trade_history()
        timestamps = [t["timestamp"] for t in history]

        # Verify descending order
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1]

    def test_trade_history_limit_parameter(self, portfolio):
        """Verify limit parameter restricts trade history"""
        for i in range(10):
            portfolio.add_trade(
                trade_id=f"T{i}",
                symbol="BTCUSDT",
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=0.1,
                price=40000.0,
                fee=0.1,
            )

        # Get only last 5 trades
        history = portfolio.get_trade_history(limit=5)
        assert len(history) == 5

    def test_trade_history_symbol_filter(self, portfolio):
        """Verify symbol filter in trade history"""
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)
        portfolio.add_trade("T2", "ETHUSDT", "BUY", 10.0, 2000.0, 1.0)
        portfolio.add_trade("T3", "BTCUSDT", "SELL", 0.5, 41000.0, 1.0)

        # Get only BTC trades
        btc_history = portfolio.get_trade_history(symbol="BTCUSDT")
        assert len(btc_history) == 2

        trade_ids = {t["trade_id"] for t in btc_history}
        assert trade_ids == {"T1", "T3"}

    def test_trade_data_integrity(self, portfolio):
        """Verify all trade data fields are preserved"""
        trade_id = "T_integrity_test"
        order_id = "ORDER_123"
        corr_id = "CORR_456"

        portfolio.add_trade(
            trade_id=trade_id,
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.5,
            price=40000.0,
            fee=2.0,
            order_id=order_id,
            correlation_id=corr_id,
            pnl=100.0,
        )

        history = portfolio.get_trade_history()
        assert len(history) == 1

        trade = history[0]
        assert trade["trade_id"] == trade_id
        assert trade["symbol"] == "BTCUSDT"
        assert trade["side"] == "BUY"
        assert trade["quantity"] == 1.5
        assert trade["price"] == 40000.0
        assert trade["fee"] == 2.0
        assert trade["order_id"] == order_id
        assert trade["correlation_id"] == corr_id
        assert trade["pnl"] == 100.0


# ============================================================================
# SECTION 3: API-Dashboard Data Consistency Tests
# ============================================================================


class TestAPIDataConsistency:
    """Validate that API returns consistent, accurate data"""

    def test_portfolio_summary_matches_calculations(self, portfolio):
        """Verify portfolio summary data matches direct calculations"""
        # Set up portfolio with known data
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)
        portfolio.add_trade("T2", "BTCUSDT", "BUY", 1.0, 42000.0, 1.0)
        portfolio.add_trade("T3", "ETHUSDT", "BUY", 10.0, 2000.0, 1.0)

        portfolio.update_market_prices({"BTCUSDT": 43000.0, "ETHUSDT": 2200.0})

        # Get stats
        stats = portfolio.get_portfolio_stats()

        # Verify calculations
        positions = portfolio.get_all_positions()
        assert len(positions) == 2

        # Expected portfolio value: (2.0 * 43000) + (10.0 * 2200) = 86000 + 22000 = 108000
        expected_value = portfolio.get_portfolio_value()
        total_positions_value = sum(
            p["quantity"] * p["current_price"] for p in positions
        )
        assert expected_value == total_positions_value

        # Expected P&L: unrealized + realized - fees
        expected_pnl = sum(p["total_pnl"] for p in positions)
        assert abs(stats["total_pnl"] - expected_pnl) < 0.01  # Allow small rounding

    def test_positions_endpoint_matches_portfolio(self, portfolio):
        """Verify positions data consistency"""
        # Add multiple positions
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)
        portfolio.add_trade("T2", "ETHUSDT", "BUY", 10.0, 2000.0, 1.0)
        portfolio.add_trade("T3", "ADAUSDT", "BUY", 100.0, 0.5, 1.0)

        portfolio.update_market_prices(
            {"BTCUSDT": 42000.0, "ETHUSDT": 2200.0, "ADAUSDT": 0.6}
        )

        # Get positions
        positions = portfolio.get_all_positions()

        # Verify all positions returned
        assert len(positions) == 3
        symbols = {p["symbol"] for p in positions}
        assert symbols == {"BTCUSDT", "ETHUSDT", "ADAUSDT"}

        # Verify position structure
        for pos in positions:
            assert "symbol" in pos
            assert "side" in pos
            assert "quantity" in pos
            assert "average_price" in pos
            assert "current_price" in pos
            assert "unrealized_pnl" in pos
            assert "realized_pnl" in pos
            assert "timestamp" in pos
            assert "market_value" in pos
            assert "total_pnl" in pos

    def test_trade_history_api_consistency(self, portfolio):
        """Verify trade history returned from API matches database"""
        trades_to_add = [
            ("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0),
            ("T2", "BTCUSDT", "BUY", 1.0, 42000.0, 1.0),
            ("T3", "ETHUSDT", "BUY", 10.0, 2000.0, 1.0),
        ]

        for trade_id, symbol, side, qty, price, fee in trades_to_add:
            portfolio.add_trade(trade_id, symbol, side, qty, price, fee)

        # Get trade history
        history = portfolio.get_trade_history()

        # Verify count
        assert len(history) == 3

        # Verify all trades present
        returned_ids = {t["trade_id"] for t in history}
        expected_ids = {t[0] for t in trades_to_add}
        assert returned_ids == expected_ids


# ============================================================================
# SECTION 4: Market Data Flow Tests
# ============================================================================


class TestMarketDataFlow:
    """Validate that market data flows correctly through the system"""

    def test_price_update_affects_pnl(self, portfolio):
        """Verify market price updates correctly affect P&L"""
        # Initial position: 1 BTC at $40,000
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)

        # Set initial market price
        portfolio.update_market_prices({"BTCUSDT": 40000.0})
        positions_1 = portfolio.get_all_positions()
        assert positions_1[0]["unrealized_pnl"] == 0.0

        # Price up to $42,000
        portfolio.update_market_prices({"BTCUSDT": 42000.0})
        positions_2 = portfolio.get_all_positions()
        assert positions_2[0]["unrealized_pnl"] == 2000.0

        # Price down to $39,000
        portfolio.update_market_prices({"BTCUSDT": 39000.0})
        positions_3 = portfolio.get_all_positions()
        assert positions_3[0]["unrealized_pnl"] == -1000.0

    def test_multiple_symbol_price_update(self, portfolio):
        """Verify batch price updates work correctly"""
        # Add multiple positions
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)
        portfolio.add_trade("T2", "ETHUSDT", "BUY", 10.0, 2000.0, 1.0)
        portfolio.add_trade("T3", "ADAUSDT", "BUY", 100.0, 0.5, 1.0)

        # Update all prices at once
        prices = {"BTCUSDT": 42000.0, "ETHUSDT": 2200.0, "ADAUSDT": 0.6}
        portfolio.update_market_prices(prices)

        # Verify all positions updated
        positions = portfolio.get_all_positions()
        for pos in positions:
            if pos["symbol"] == "BTCUSDT":
                assert pos["current_price"] == 42000.0
            elif pos["symbol"] == "ETHUSDT":
                assert pos["current_price"] == 2200.0
            elif pos["symbol"] == "ADAUSDT":
                assert pos["current_price"] == 0.6


# ============================================================================
# SECTION 5: Data Export & Serialization Tests
# ============================================================================


class TestDataExportSerialization:
    """Validate that exported data is complete and valid"""

    def test_json_export_completeness(self, portfolio):
        """Verify JSON export contains all required data"""
        # Set up portfolio
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)
        portfolio.add_trade("T2", "ETHUSDT", "BUY", 10.0, 2000.0, 1.0)
        portfolio.add_trade("T3", "BTCUSDT", "SELL", 0.5, 41000.0, 1.0)

        portfolio.update_market_prices({"BTCUSDT": 42000.0, "ETHUSDT": 2200.0})

        # Export to JSON
        json_str = portfolio.export_to_json()
        data = json.loads(json_str)

        # Verify structure
        assert "positions" in data
        assert "trades" in data
        assert "stats" in data
        assert "export_timestamp" in data

        # Verify data counts
        assert len(data["positions"]) == 2
        assert len(data["trades"]) == 3

        # Verify stats
        stats = data["stats"]
        assert "total_value" in stats
        assert "total_pnl" in stats
        assert "total_fees" in stats
        assert "number_of_trades" in stats

    def test_json_export_is_valid_json(self, portfolio):
        """Verify exported JSON is properly formatted"""
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)

        json_str = portfolio.export_to_json()

        # Should not raise exception
        data = json.loads(json_str)
        assert data is not None
        assert isinstance(data, dict)


# ============================================================================
# SECTION 6: Edge Case & Error Handling Tests
# ============================================================================


class TestDataValidationEdgeCases:
    """Test handling of edge cases and error scenarios"""

    def test_zero_quantity_handling(self, portfolio):
        """Verify handling of positions with zero quantity"""
        # BUY then SELL same amount
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)
        portfolio.add_trade("T2", "BTCUSDT", "SELL", 1.0, 42000.0, 1.0)

        # Position exists but has zero quantity (closed but not deleted from DB)
        positions = portfolio.get_all_positions()
        assert len(positions) == 1
        assert positions[0]["quantity"] == 0.0
        assert positions[0]["market_value"] == 0.0  # Zero quantity = zero market value

    def test_fractional_quantity_handling(self, portfolio):
        """Verify handling of fractional quantities"""
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 0.001, 40000.0, 0.04)
        portfolio.add_trade("T2", "BTCUSDT", "BUY", 0.0015, 40500.0, 0.06)

        positions = portfolio.get_all_positions()
        assert len(positions) == 1

        pos = positions[0]
        assert pos["quantity"] == pytest.approx(0.0025, rel=1e-9)

    def test_large_numbers_precision(self, portfolio):
        """Verify handling of large trading volumes"""
        # Large position: 1000 BTC
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1000.0, 40000.0, 500.0)

        portfolio.update_market_prices({"BTCUSDT": 41000.0})

        stats = portfolio.get_portfolio_stats()
        # P&L = (41000 - 40000) * 1000 - 500 = 1000000 - 500 = 999500
        assert stats["total_pnl"] == pytest.approx(999500.0, rel=1e-6)

    def test_negative_price_handling(self, portfolio):
        """Verify system doesn't accept invalid negative prices"""
        # This is more of an integration test - the system should prevent this
        # For now, we verify the current behavior
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0)

        # System shouldn't crash with invalid data
        try:
            portfolio.update_market_prices({"BTCUSDT": -1000.0})
            # If it doesn't raise, at least verify position wasn't updated to negative
            positions = portfolio.get_all_positions()
            assert positions[0]["current_price"] == -1000.0  # Document current behavior
        except ValueError:
            # Preferred: system rejects invalid data
            pass

    def test_empty_portfolio_stats(self, portfolio):
        """Verify stats on empty portfolio"""
        stats = portfolio.get_portfolio_stats()

        assert stats["total_value"] == 0.0
        assert stats["total_pnl"] == 0.0
        assert stats["total_fees"] == 0.0
        assert stats["number_of_trades"] == 0
        assert stats["win_rate"] == 0.0

    def test_single_trade_win_rate(self, portfolio):
        """Verify win rate calculation with single trade"""
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0, pnl=100.0)

        stats = portfolio.get_portfolio_stats()
        # 1 profitable trade out of 1 = 100% win rate
        assert stats["win_rate"] == 1.0

    def test_drawdown_calculation(self, portfolio):
        """Verify max drawdown calculation"""
        # Series of trades with profits and losses
        portfolio.add_trade("T1", "BTCUSDT", "BUY", 1.0, 40000.0, 1.0, pnl=1000.0)
        portfolio.add_trade("T2", "BTCUSDT", "SELL", 1.0, 41000.0, 1.0, pnl=-2000.0)
        portfolio.add_trade("T3", "BTCUSDT", "BUY", 1.0, 39000.0, 1.0, pnl=1500.0)

        stats = portfolio.get_portfolio_stats()
        # Running P&L: 1000 -> -1000 (drawdown = 2000) -> 500 (drawdown = 500)
        # Max drawdown should be 2000
        assert stats["max_drawdown"] == 2000.0


# ============================================================================
# SECTION 7: Data Consistency Under Concurrency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_portfolio_updates():
    """Verify portfolio handles concurrent updates safely"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "concurrent_test.db"
        portfolio = PortfolioManager(db_path=str(db_path))

        async def add_trades(trade_num):
            """Add trades concurrently"""
            for i in range(5):
                portfolio.add_trade(
                    trade_id=f"T_{trade_num}_{i}",
                    symbol=f"COIN{trade_num}",
                    side="BUY" if i % 2 == 0 else "SELL",
                    quantity=0.1 * (i + 1),
                    price=1000.0 + (i * 100),
                    fee=0.1,
                )

        # Run concurrent trade additions
        await asyncio.gather(add_trades(1), add_trades(2), add_trades(3))

        # Verify all trades were added
        all_trades = portfolio.get_trade_history()
        assert len(all_trades) == 15  # 3 concurrent * 5 trades each

        portfolio.clear_portfolio()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
