#!/usr/bin/env python3
"""
Simple MCP Trading Demo
Quick demonstration of trading agent capabilities
"""
import asyncio
import json
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/app')

from mcp_server import server

async def demo_trading_agent():
    """Demo all trading agent capabilities"""
    print("🤖 Binance Trading Agent Demo")
    print("=" * 40)
    
    # 1. Market Data
    print("\n1️⃣ Market Data Test")
    market_data = await server.get_market_data("BTCUSDT", 5)
    print(f"Current BTCUSDT Price: ${market_data.get('price', 'N/A')}")
    
    # 2. Trading Signal
    print("\n2️⃣ Trading Signal Test")
    signal = await server.compute_trading_signal("BTCUSDT", "rsi", 20)
    print(f"RSI Signal: {signal.get('signal', 'N/A')} (Confidence: {signal.get('confidence', 'N/A')})")
    
    # 3. Account Balance
    print("\n3️⃣ Account Balance Test")
    balance = await server.get_account_balance("USDT")
    print(f"USDT Balance: {balance.get('balance', 'N/A')}")
    
    # 4. Risk Validation
    print("\n4️⃣ Risk Management Test")
    test_signal = {"symbol": "BTCUSDT", "side": "BUY", "quantity": 0.001}
    test_portfolio = {"positions": {}, "active_trades": [], "max_position": 10, "drawdown": 0.05, "max_drawdown": 0.2}
    test_market = {"price": 45000.0}
    
    validation = await server.validate_trade(test_signal, test_portfolio, test_market)
    print(f"Trade Valid: {validation.get('valid', 'N/A')}")
    
    print("\n✅ Demo completed!")

if __name__ == "__main__":
    asyncio.run(demo_trading_agent())