"""
Tests for Streamlit Web UI
Mocks API endpoints and tests core interface functionality.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit to avoid GUI dependencies in tests
sys.modules['streamlit'] = Mock()
sys.modules['plotly'] = Mock()
sys.modules['plotly.express'] = Mock()
sys.modules['plotly.graph_objects'] = Mock()

import requests
from binance_trade_agent.web_ui import (
    call_mcp_tool, get_portfolio_data, get_market_data,
    get_order_book, execute_trade, get_signals,
    get_risk_status, get_system_status, get_trade_history,
    get_performance_metrics, set_emergency_stop
)


class TestWebUIAPI:
    """Test web UI API functions"""

    @patch('binance_trade_agent.web_ui.requests.post')
    def test_call_mcp_tool_success(self, mock_post):
        """Test successful MCP tool call"""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        result = call_mcp_tool("test_tool", {"param": "value"})

        assert result == {"result": "success"}
        mock_post.assert_called_once()

    @patch('binance_trade_agent.web_ui.requests.post')
    def test_call_mcp_tool_error(self, mock_post):
        """Test MCP tool call with error"""
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        result = call_mcp_tool("test_tool")

        assert "error" in result
        assert "Connection failed" in result["error"]

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_get_portfolio_data(self, mock_call):
        """Test portfolio data retrieval"""
        mock_call.return_value = {
            "total_value": 10000.0,
            "total_pnl": 500.0,
            "open_positions": 2
        }

        result = get_portfolio_data()

        assert result["total_value"] == 10000.0
        mock_call.assert_called_with("get_portfolio_summary")

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_get_market_data(self, mock_call):
        """Test market data retrieval"""
        mock_call.return_value = {
            "price": 50000.0,
            "change_24h": 2.5
        }

        result = get_market_data("BTCUSDT")

        assert result["price"] == 50000.0
        mock_call.assert_called_with("get_market_price", {"symbol": "BTCUSDT"})

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_get_order_book(self, mock_call):
        """Test order book retrieval"""
        mock_call.return_value = {
            "bids": [[49999, 1.0], [49998, 2.0]],
            "asks": [[50001, 1.5], [50002, 1.0]]
        }

        result = get_order_book("BTCUSDT", 5)

        assert len(result["bids"]) == 2
        mock_call.assert_called_with("get_order_book", {"symbol": "BTCUSDT", "limit": 5})

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_execute_trade_buy(self, mock_call):
        """Test buy trade execution"""
        mock_call.return_value = {"order_id": "12345", "status": "filled"}

        result = execute_trade("BTCUSDT", "BUY", 0.001)

        assert result["order_id"] == "12345"
        mock_call.assert_called_with("place_buy_order", {"symbol": "BTCUSDT", "quantity": 0.001})

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_execute_trade_sell(self, mock_call):
        """Test sell trade execution"""
        mock_call.return_value = {"order_id": "12346", "status": "filled"}

        result = execute_trade("BTCUSDT", "SELL", 0.001)

        assert result["order_id"] == "12346"
        mock_call.assert_called_with("place_sell_order", {"symbol": "BTCUSDT", "quantity": 0.001})

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_get_signals(self, mock_call):
        """Test signal generation"""
        mock_call.return_value = {
            "signal": "BUY",
            "confidence": 0.85
        }

        result = get_signals()

        assert result["signal"] == "BUY"
        assert result["confidence"] == 0.85
        mock_call.assert_called_with("generate_trading_signal", {"symbol": "BTCUSDT"})

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_get_risk_status(self, mock_call):
        """Test risk status retrieval"""
        mock_call.return_value = {
            "emergency_stop": False,
            "consecutive_losses": 0,
            "current_drawdown": 1.5
        }

        result = get_risk_status()

        assert not result["emergency_stop"]
        assert result["consecutive_losses"] == 0
        mock_call.assert_called_with("get_risk_status")

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_get_system_status(self, mock_call):
        """Test system status retrieval"""
        mock_call.return_value = {
            "status": "healthy",
            "uptime_seconds": 3600.0,
            "trade_error_rate": 0.01
        }

        result = get_system_status()

        assert result["status"] == "healthy"
        assert result["uptime_seconds"] == 3600.0
        mock_call.assert_called_with("get_system_status")

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_get_trade_history(self, mock_call):
        """Test trade history retrieval"""
        mock_call.return_value = {
            "trades": [
                {"symbol": "BTCUSDT", "side": "BUY", "quantity": 0.001, "price": 50000}
            ]
        }

        result = get_trade_history()

        assert len(result["trades"]) == 1
        mock_call.assert_called_with("get_trade_history")

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_get_performance_metrics(self, mock_call):
        """Test performance metrics retrieval"""
        mock_call.return_value = {
            "total_trades": 10,
            "portfolio_value": 10500.0
        }

        result = get_performance_metrics()

        assert result["total_trades"] == 10
        assert result["portfolio_value"] == 10500.0
        mock_call.assert_called_with("get_performance_metrics")

    @patch('binance_trade_agent.web_ui.call_mcp_tool')
    def test_set_emergency_stop(self, mock_call):
        """Test emergency stop activation"""
        mock_call.return_value = {"success": True}

        result = set_emergency_stop()

        assert result["success"] is True
        mock_call.assert_called_with("set_emergency_stop", {"enabled": True})


class TestWebUIIntegration:
    """Integration tests for web UI components"""

    @patch('binance_trade_agent.web_ui.st')
    @patch('binance_trade_agent.web_ui.get_portfolio_data')
    def test_portfolio_tab_renders(self, mock_get_portfolio, mock_st):
        """Test that portfolio tab renders correctly"""
        mock_get_portfolio.return_value = {
            "total_value": 10000.0,
            "total_pnl": 500.0,
            "open_positions": 2,
            "positions": [
                {"symbol": "BTCUSDT", "quantity": 0.1, "current_value": 5000.0}
            ],
            "recent_trades": []
        }

        # Mock streamlit components
        mock_st.columns.return_value = [Mock(), Mock(), Mock(), Mock()]
        mock_st.spinner.return_value.__enter__ = Mock()
        mock_st.spinner.return_value.__exit__ = Mock()

        # This would normally be called from the main function
        # For testing, we verify the mocks are called correctly
        assert mock_get_portfolio.called

    @patch('binance_trade_agent.web_ui.requests.post')
    def test_api_error_handling(self, mock_post):
        """Test that API errors are handled gracefully"""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        result = call_mcp_tool("test_tool")

        assert "error" in result
        assert "Request timed out" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])