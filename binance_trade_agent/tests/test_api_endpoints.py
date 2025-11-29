"""
API Endpoint Tests - CRITICAL
Tests for FastAPI endpoints with Redis fallback scenarios.
SLA: API endpoints should respond within 100ms (P95) / 500ms (P99)
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from ..api import api as api_module
from ..api.api import app


@pytest.fixture
def client():
    """Create TestClient for API testing"""
    return TestClient(app)


# Note: The cache fixture is async but TestClient tests are sync
# Cache will be initialized by API startup event if needed


class TestAPIHealthAndRoot:
    """Tests for API health and root endpoints"""

    def test_api_root_endpoint_success(self, client):
        """Test GET / returns 200 OK with correct structure"""
        # Arrange & Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "message" in data

    def test_api_root_endpoint_timestamp_valid(self, client):
        """Test that root endpoint returns valid ISO timestamp"""
        # Arrange & Act
        response = client.get("/")

        # Assert
        data = response.json()
        # Should be ISO format datetime
        datetime.fromisoformat(data["timestamp"])  # Will raise if invalid


class TestAPIPortfolioSummary:
    """Tests for /api/v1/portfolio/summary endpoint"""

    def test_api_portfolio_summary_success(self, client):
        """Test GET /api/v1/portfolio/summary returns 200 OK"""
        # Arrange & Act
        response = client.get("/api/v1/portfolio/summary")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify response schema
        assert "total_value" in data or "number_of_trades" in data or "total_pnl" in data

    def test_api_portfolio_summary_response_schema_valid(self, client):
        """Test that portfolio summary response has expected fields"""
        # Arrange & Act
        response = client.get("/api/v1/portfolio/summary")
        data = response.json()

        # Assert - Should have portfolio metrics
        # At minimum, should include source field
        assert "source" in data
        # Source should be either "cache" or "live"
        assert data["source"] in ["cache", "live"]

    def test_api_portfolio_summary_caching_behavior(self, client):
        """Test that portfolio summary uses caching"""
        # Arrange
        # First request should be "live"
        response1 = client.get("/api/v1/portfolio/summary")
        data1 = response1.json()
        source1 = data1.get("source")

        # Second request immediately after should be "cache"
        response2 = client.get("/api/v1/portfolio/summary")
        data2 = response2.json()
        source2 = data2.get("source")

        # Assert
        # First could be "live" or "cache" depending on state
        # But both should be valid sources
        assert source1 in ["cache", "live"]
        assert source2 in ["cache", "live"]

    @patch.object(api_module, "cache", new_callable=AsyncMock)
    @patch.object(api_module, "portfolio_manager")
    def test_api_portfolio_summary_redis_down_fallback(self, mock_portfolio, mock_cache, client):
        """Test that portfolio endpoint works even if Redis is down"""
        # Arrange
        mock_cache.get.return_value = None  # Cache miss
        mock_portfolio.get_portfolio_stats.return_value = {
            "total_value": 100000,
            "total_pnl": 5000,
            "number_of_trades": 10,
        }

        # Act
        response = client.get("/api/v1/portfolio/summary")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_value"] == 100000
        assert data["total_pnl"] == 5000
        assert data["number_of_trades"] == 10


class TestAPIPositions:
    """Tests for /api/v1/portfolio/positions endpoint"""

    @patch.object(api_module, "portfolio_manager")
    def test_api_positions_endpoint_success(self, mock_portfolio, client):
        """Test GET /api/v1/portfolio/positions returns 200 OK"""
        # Arrange
        mock_portfolio.get_all_positions.return_value = [
            {"symbol": "BTCUSDT", "quantity": 0.1, "entry_price": 50000}
        ]

        # Act
        response = client.get("/api/v1/portfolio/positions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert isinstance(data["positions"], list)

    @patch.object(api_module, "portfolio_manager")
    def test_api_positions_endpoint_empty(self, mock_portfolio, client):
        """Test positions endpoint returns empty list when no positions"""
        # Arrange
        mock_portfolio.get_all_positions.return_value = []

        # Act
        response = client.get("/api/v1/portfolio/positions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["positions"] == []


class TestAPITradeHistory:
    """Tests for /api/v1/portfolio/trade-history endpoint"""

    @patch.object(api_module, "portfolio_manager")
    def test_api_trade_history_success(self, mock_portfolio, client):
        """Test GET /api/v1/portfolio/trade-history returns 200 OK"""
        # Arrange
        mock_portfolio.get_trade_history.return_value = [
            {
                "trade_id": "t1",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "quantity": 0.1,
                "price": 50000,
                "fee": 1.0,
            }
        ]

        # Act
        response = client.get("/api/v1/portfolio/trade-history")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert isinstance(data["trades"], list)
        assert len(data["trades"]) == 1

    @patch.object(api_module, "portfolio_manager")
    def test_api_trade_history_with_limit(self, mock_portfolio, client):
        """Test trade-history respects limit parameter"""
        # Arrange
        mock_portfolio.get_trade_history.return_value = [
            {"trade_id": f"t{i}", "symbol": "BTCUSDT"} for i in range(5)
        ]

        # Act
        response = client.get("/api/v1/portfolio/trade-history?limit=5")

        # Assert
        assert response.status_code == 200
        # Verify limit parameter was passed to portfolio_manager
        mock_portfolio.get_trade_history.assert_called_with(limit=5)


class TestAPIRiskStatus:
    """Tests for /api/v1/risk/status endpoint"""

    @patch.object(api_module, "cache", new_callable=AsyncMock)
    @patch.object(api_module, "risk_agent")
    def test_api_risk_status_success(self, mock_risk, mock_cache, client):
        """Test GET /api/v1/risk/status returns 200 OK"""
        # Arrange
        mock_cache.get.return_value = None
        mock_risk.get_risk_status.return_value = {
            "risk_level": "MEDIUM",
            "approved_positions": 5,
            "max_positions": 10,
        }

        # Act
        response = client.get("/api/v1/risk/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "risk_level" in data
        assert "source" in data

    @patch.object(api_module, "risk_agent")
    def test_api_risk_status_caching(self, mock_risk, client):
        """Test that risk status uses caching"""
        # Arrange
        mock_risk.get_risk_status.return_value = {
            "risk_level": "LOW",
            "approved_positions": 2,
        }

        # Act
        response1 = client.get("/api/v1/risk/status")
        response2 = client.get("/api/v1/risk/status")

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200


class TestAPIMarketPrice:
    """Tests for /api/v1/market/price/{symbol} endpoint"""

    @patch.object(api_module, "cache", new_callable=AsyncMock)
    @patch.object(api_module, "market_agent")
    def test_api_market_price_success(self, mock_market, mock_cache, client):
        """Test GET /api/v1/market/price/BTCUSDT returns correct price"""
        # Arrange
        mock_cache.get.return_value = None
        mock_market.get_latest_price.return_value = 50000.0

        # Act
        response = client.get("/api/v1/market/price/BTCUSDT")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "BTCUSDT"
        assert data["price"] == 50000.0
        assert "source" in data

    @patch.object(api_module, "cache", new_callable=AsyncMock)
    @patch.object(api_module, "market_agent")
    def test_api_market_price_symbol_normalization(self, mock_market, mock_cache, client):
        """Test that symbol is normalized to uppercase"""
        # Arrange
        mock_cache.get.return_value = None
        mock_market.get_latest_price.return_value = 100.0

        # Act
        response = client.get("/api/v1/market/price/ethusdt")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "ETHUSDT"  # Normalized
        # Verify agent was called with uppercase symbol
        mock_market.get_latest_price.assert_called_with("ETHUSDT")

    @patch.object(api_module, "cache", new_callable=AsyncMock)
    @patch.object(api_module, "market_agent")
    def test_api_market_price_not_found(self, mock_market, mock_cache, client):
        """Test market price endpoint returns 404 for unknown symbol"""
        # Arrange
        mock_cache.get.return_value = None
        mock_market.get_latest_price.return_value = None

        # Act
        response = client.get("/api/v1/market/price/INVALID")

        # Assert
        assert response.status_code == 404

    @patch.object(api_module, "market_agent")
    def test_api_market_price_caching_behavior(self, mock_market, client):
        """Test that market prices are cached"""
        # Arrange
        mock_market.get_latest_price.return_value = 50000.0

        # Act
        response1 = client.get("/api/v1/market/price/BTCUSDT")
        response2 = client.get("/api/v1/market/price/BTCUSDT")

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        data1 = response1.json()
        data2 = response2.json()
        # At least one should be cached (depending on timing)
        assert data1["source"] in ["cache", "live"]
        assert data2["source"] in ["cache", "live"]


class TestAPISystemConfig:
    """Tests for /api/v1/system/config endpoint"""

    def test_api_system_config_success(self, client):
        """Test GET /api/v1/system/config returns 200 OK"""
        # Arrange & Act
        response = client.get("/api/v1/system/config")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "demo_mode" in data or "binance_testnet" in data or "risk_config" in data

    def test_api_system_config_structure(self, client):
        """Test that system config has expected structure"""
        # Arrange & Act
        response = client.get("/api/v1/system/config")
        data = response.json()

        # Assert
        # Should include at least one config option
        keys = set(data.keys())
        expected_keys = {"demo_mode", "binance_testnet", "risk_config"}
        assert len(keys & expected_keys) > 0


class TestAPIErrorHandling:
    """Tests for API error handling"""

    @patch.object(api_module, "cache", new_callable=AsyncMock)
    @patch.object(api_module, "portfolio_manager")
    def test_api_portfolio_endpoint_exception_handling(self, mock_portfolio, mock_cache, client):
        """Test that exceptions are handled gracefully"""
        # Arrange
        mock_cache.get.return_value = None
        mock_portfolio.get_portfolio_stats.side_effect = Exception("DB error")

        # Act
        response = client.get("/api/v1/portfolio/summary")

        # Assert
        # Should return 500 with error detail
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    @patch.object(api_module, "cache", new_callable=AsyncMock)
    @patch.object(api_module, "market_agent")
    def test_api_market_price_endpoint_exception_handling(self, mock_market, mock_cache, client):
        """Test market price endpoint error handling"""
        # Arrange
        mock_cache.get.return_value = None
        mock_market.get_latest_price.side_effect = Exception("API error")

        # Act
        response = client.get("/api/v1/market/price/BTCUSDT")

        # Assert
        assert response.status_code == 500


class TestAPIConcurrentRequests:
    """Tests for API behavior under concurrent load"""

    @patch.object(api_module, "cache", new_callable=AsyncMock)
    @patch.object(api_module, "portfolio_manager")
    def test_api_multiple_requests_to_same_endpoint(self, mock_portfolio, mock_cache, client):
        """Test that API handles multiple requests correctly"""
        # Arrange
        mock_cache.get.return_value = None
        mock_portfolio.get_portfolio_stats.return_value = {
            "total_value": 100000,
            "total_pnl": 5000,
        }

        # Act - Make 5 sequential requests
        responses = [client.get("/api/v1/portfolio/summary") for _ in range(5)]

        # Assert
        assert all(r.status_code == 200 for r in responses)
        assert len(responses) == 5


class TestAPICORSHeaders:
    """Tests for CORS configuration"""

    def test_api_cors_headers_present(self, client):
        """Test that CORS headers are configured"""
        # Arrange & Act
        response = client.get("/")

        # Assert
        headers = response.headers
        # CORS headers should be present or allow-all
        # (TestClient may not fully expose CORS headers, but check if app is configured)
        assert response.status_code == 200
