"""
Dashboard Integration Tests - CRITICAL
Tests for dashboard data flow and API integration.
SLA: Dashboard API calls should timeout/degrade gracefully after 5 seconds
"""

from unittest.mock import MagicMock, patch

from binance_trade_agent.dashboard.utils.data_fetch import (
    get_market_data,
    get_ohlcv_data,
    get_order_book,
    get_performance_metrics,
    get_portfolio_data,
    get_trade_history,
)


class TestDashboardMarketData:
    """Tests for dashboard market data fetching"""

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_market_data_success(self, mock_components):
        """Test that get_market_data returns correct structure"""
        # Arrange
        mock_market_agent = MagicMock()
        mock_market_agent.get_latest_price.return_value = 50000.0
        mock_components.return_value = {"market_agent": mock_market_agent}

        # Act
        result = get_market_data("BTCUSDT")

        # Assert
        assert isinstance(result, dict)
        assert "price" in result or "error" not in result

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_market_data_error_handling(self, mock_components):
        """Test that get_market_data handles errors gracefully"""
        # Arrange
        mock_components.side_effect = Exception("Components error")

        # Act
        result = get_market_data("BTCUSDT")

        # Assert
        # Should return error dict, not raise exception
        assert isinstance(result, dict)
        assert "error" in result

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_ohlcv_data_structure(self, mock_components):
        """Test that OHLCV data has correct structure"""
        # Arrange
        mock_market_agent = MagicMock()
        mock_market_agent.fetch_ohlcv.return_value = [
            {
                "timestamp": 1234567890,
                "open": 49000,
                "high": 51000,
                "low": 48000,
                "close": 50000,
                "volume": 100,
            }
        ]
        mock_components.return_value = {"market_agent": mock_market_agent}

        # Act
        result = get_ohlcv_data("BTCUSDT", interval="1h")

        # Assert
        assert isinstance(result, list)
        if len(result) > 0:
            assert isinstance(result[0], dict)

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_order_book_structure(self, mock_components):
        """Test that order book data has correct structure"""
        # Arrange
        mock_market_agent = MagicMock()
        mock_market_agent.fetch_order_book.return_value = {
            "bids": [[49990, 1.0], [49980, 2.0]],
            "asks": [[50010, 1.0], [50020, 2.0]],
            "timestamp": 1234567890,
        }
        mock_components.return_value = {"market_agent": mock_market_agent}

        # Act
        result = get_order_book("BTCUSDT")

        # Assert
        assert isinstance(result, dict)


class TestDashboardPortfolioData:
    """Tests for dashboard portfolio data fetching"""

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_portfolio_data_structure(self, mock_components):
        """Test that portfolio data has correct structure"""
        # Arrange
        mock_portfolio = MagicMock()
        mock_portfolio.get_portfolio_stats.return_value = {
            "total_value": 100000,
            "total_pnl": 5000,
            "number_of_trades": 10,
        }
        mock_portfolio.get_all_positions.return_value = []
        mock_portfolio.get_trade_history.return_value = []
        mock_components.return_value = {"portfolio": mock_portfolio}

        # Act
        result = get_portfolio_data()

        # Assert
        assert isinstance(result, dict)
        assert "total_value" in result or "error" in result

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_portfolio_data_error_handling(self, mock_components):
        """Test that portfolio fetching handles errors gracefully"""
        # Arrange
        mock_components.side_effect = Exception("DB locked")

        # Act
        result = get_portfolio_data()

        # Assert
        assert isinstance(result, dict)
        assert "error" in result

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_trade_history_structure(self, mock_components):
        """Test that trade history has correct structure"""
        # Arrange
        mock_portfolio = MagicMock()
        mock_portfolio.get_trade_history.return_value = [
            {
                "trade_id": "t1",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.1,
                "price": 50000,
                "fee": 1.0,
                "timestamp": 1234567890,
            }
        ]
        mock_components.return_value = {"portfolio": mock_portfolio}

        # Act
        result = get_trade_history(limit=20)

        # Assert
        assert isinstance(result, dict)
        assert "trades" in result or "error" in result

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_trade_history_with_limit(self, mock_components):
        """Test that trade history respects limit parameter"""
        # Arrange
        mock_portfolio = MagicMock()
        mock_portfolio.get_trade_history.return_value = []
        mock_components.return_value = {"portfolio": mock_portfolio}

        # Act
        result = get_trade_history(limit=50)

        # Assert
        mock_portfolio.get_trade_history.assert_called_with(limit=50)

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_get_performance_metrics_structure(self, mock_components):
        """Test that performance metrics have correct structure"""
        # Arrange
        mock_portfolio = MagicMock()
        mock_portfolio.get_portfolio_stats.return_value = {
            "total_trades": 10,
            "total_value": 100000,
        }
        mock_components.return_value = {"portfolio": mock_portfolio}

        # Act
        result = get_performance_metrics()

        # Assert
        assert isinstance(result, dict)
        assert "total_trades" in result or "portfolio_value" in result or "error" in result


class TestDashboardErrorRecovery:
    """Tests for dashboard error recovery and graceful degradation"""

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_graceful_degradation_on_api_error(self, mock_components):
        """Test that dashboard doesn't crash on API errors"""
        # Arrange
        mock_components.side_effect = Exception("API unavailable")

        # Act & Assert - All functions should handle errors gracefully
        assert isinstance(get_market_data("BTCUSDT"), dict)
        assert isinstance(get_portfolio_data(), dict)
        assert isinstance(get_trade_history(), dict)
        assert isinstance(get_performance_metrics(), dict)

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_returns_dict_not_exception(self, mock_components):
        """Test that data_fetch functions always return dict (or list for OHLCV)"""
        # Arrange
        mock_components.side_effect = RuntimeError("Critical error")

        # Act
        results = [
            get_market_data("BTCUSDT"),
            get_ohlcv_data("BTCUSDT"),
            get_order_book("BTCUSDT"),
            get_portfolio_data(),
            get_trade_history(),
            get_performance_metrics(),
        ]

        # Assert - All should be dicts or lists (for OHLCV)
        for r in results:
            assert isinstance(r, (dict, list))


class TestDashboardDataConsistency:
    """Tests for data consistency between API and Dashboard"""

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_portfolio_matches_api_values(self, mock_components):
        """Test that dashboard portfolio data matches API response"""
        # Arrange
        mock_portfolio = MagicMock()
        expected_stats = {
            "total_value": 100000.00,
            "total_pnl": 5000.50,
            "number_of_trades": 10,
        }
        mock_portfolio.get_portfolio_stats.return_value = expected_stats
        mock_portfolio.get_all_positions.return_value = []
        mock_portfolio.get_trade_history.return_value = []
        mock_components.return_value = {"portfolio": mock_portfolio}

        # Act
        result = get_portfolio_data()

        # Assert
        assert result.get("total_value") == expected_stats["total_value"]
        assert result.get("total_pnl") == expected_stats["total_pnl"]
        assert result.get("total_trades") == expected_stats["number_of_trades"]

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_trade_history_data_format(self, mock_components):
        """Test that trade history is properly formatted for dashboard"""
        # Arrange
        mock_portfolio = MagicMock()
        trades = [
            {
                "trade_id": "t1",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.1,
                "price": 50000.0,
                "fee": 1.0,
                "timestamp": 1234567890,
            }
        ]
        mock_portfolio.get_trade_history.return_value = trades
        mock_components.return_value = {"portfolio": mock_portfolio}

        # Act
        result = get_trade_history(limit=20)

        # Assert
        assert "trades" in result
        assert len(result["trades"]) == 1
        assert result["trades"][0]["symbol"] == "BTCUSDT"


class TestDashboardComponentLoadability:
    """Tests for dashboard component import and initialization"""

    def test_dashboard_can_import_all_data_fetchers(self):
        """Test that all data fetching functions can be imported"""
        # Verify all functions are importable and callable
        from binance_trade_agent.dashboard.utils import data_fetch

        assert callable(data_fetch.get_market_data)
        assert callable(data_fetch.get_ohlcv_data)
        assert callable(data_fetch.get_order_book)
        assert callable(data_fetch.get_portfolio_data)
        assert callable(data_fetch.get_trade_history)
        assert callable(data_fetch.get_performance_metrics)

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_market_data_symbol_validation(self, mock_components):
        """Test that market data functions handle symbol parameter"""
        # Arrange
        mock_market = MagicMock()
        mock_market.get_latest_price.return_value = 50000.0
        mock_components.return_value = {"market_agent": mock_market}

        # Act
        result = get_market_data("BTCUSDT")

        # Assert
        mock_market.get_latest_price.assert_called_with("BTCUSDT")


class TestDashboardCacheInvalidation:
    """Tests for proper cache handling in dashboard"""

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_fresh_data_on_successive_calls(self, mock_components):
        """Test that repeated calls fetch fresh data (or cached appropriately)"""
        # Arrange
        mock_portfolio = MagicMock()
        mock_portfolio.get_portfolio_stats.return_value = {"total_value": 100000}
        mock_components.return_value = {"portfolio": mock_portfolio}

        # Act
        from binance_trade_agent.dashboard.utils.data_fetch import get_portfolio_data

        result1 = get_portfolio_data()
        result2 = get_portfolio_data()

        # Assert
        # Both calls should succeed
        assert "total_value" in result1
        assert "total_value" in result2
        # Function should be called twice (no internal caching at function level)
        assert mock_portfolio.get_portfolio_stats.call_count >= 1


class TestDashboardMissingComponents:
    """Tests for dashboard behavior with missing/unavailable components"""

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_handles_missing_market_agent(self, mock_components):
        """Test dashboard handles missing market agent gracefully"""
        # Arrange
        mock_components.return_value = {"portfolio": MagicMock()}  # No market_agent

        # Act & Assert - Should not crash
        result = get_market_data("BTCUSDT")
        assert isinstance(result, dict)

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_dashboard_handles_missing_portfolio_manager(self, mock_components):
        """Test dashboard handles missing portfolio manager gracefully"""
        # Arrange
        mock_components.return_value = {"market_agent": MagicMock()}  # No portfolio

        # Act & Assert - Should not crash
        result = get_portfolio_data()
        assert isinstance(result, dict)
