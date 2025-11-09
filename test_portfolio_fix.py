#!/usr/bin/env python3
"""Test script to verify portfolio data loading works"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from binance_trade_agent.portfolio_manager import PortfolioManager

def test_portfolio_loading():
    """Test that portfolio data can be loaded without errors"""
    print("Testing portfolio data loading...")

    try:
        # Initialize portfolio manager
        portfolio = PortfolioManager("/app/data/web_portfolio.db")
        print("✓ Portfolio manager initialized")

        # Test get_portfolio_stats
        stats = portfolio.get_portfolio_stats()
        print(f"✓ Portfolio stats loaded: {len(stats)} fields")

        # Test get_all_positions
        positions = portfolio.get_all_positions()
        print(f"✓ Positions loaded: {len(positions)} positions")

        # Test get_trade_history
        trades = portfolio.get_trade_history(limit=10)
        print(f"✓ Trade history loaded: {len(trades)} trades")

        print("✅ All portfolio data loading tests passed!")
        return True

    except Exception as e:
        print(f"❌ Error loading portfolio data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_portfolio_loading()
    sys.exit(0 if success else 1)