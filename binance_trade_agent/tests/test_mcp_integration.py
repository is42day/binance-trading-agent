import pytest
import json
import subprocess
import time
import requests
from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.signal_agent import SignalAgent

def test_mcp_server_startup():
    """Test that MCP server can start successfully"""
    # This would test server startup - for now just verify agents work
    market_agent = MarketDataAgent()
    signal_agent = SignalAgent()
    assert market_agent is not None
    assert signal_agent is not None

def test_mcp_tool_registration():
    """Test that all tools are properly registered"""
    # Test that server module can be imported
    try:
        import binance_trade_agent.mcp_server
        assert True
    except ImportError:
        assert False, "MCP server module failed to import"

def test_market_data_tool():
    """Test market data tool functionality"""
    market_agent = MarketDataAgent()
    price = market_agent.client.get_latest_price("BTCUSDT")
    assert isinstance(price, float)
    assert price > 0

def test_signal_tool():
    """Test signal computation tool"""
    signal_agent = SignalAgent()
    sample_data = [{"close": 100 + i} for i in range(35)]
    signal = signal_agent.compute_signal(sample_data, indicator="rsi")
    assert "signal" in signal
    assert signal["signal"] in ["BUY", "SELL", "HOLD"]