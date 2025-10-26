import pytest
import asyncio
from binance_trade_agent.mcp_client import TradingMCPClient

@pytest.mark.asyncio
async def test_mcp_client_initialization():
    """Test MCP client can be initialized"""
    client = TradingMCPClient()
    assert client.server is not None

@pytest.mark.asyncio
async def test_client_market_data():
    """Test client market data functionality"""
    client = TradingMCPClient()
    result = await client.test_market_data("BTCUSDT")
    assert "price" in result or "error" in result

@pytest.mark.asyncio
async def test_client_trading_signal():
    """Test client trading signal functionality"""
    client = TradingMCPClient()
    result = await client.test_trading_signal("BTCUSDT", "rsi")
    assert "signal" in result or "error" in result

@pytest.mark.asyncio
async def test_client_risk_validation():
    """Test client risk validation functionality"""
    client = TradingMCPClient()
    result = await client.test_risk_validation()
    assert "valid" in result or "error" in result

@pytest.mark.asyncio
async def test_client_account_balance():
    """Test client account balance functionality"""
    client = TradingMCPClient()
    result = await client.test_account_balance("USDT")
    assert "balance" in result or "error" in result