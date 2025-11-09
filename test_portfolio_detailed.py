#!/usr/bin/env python3
"""Detailed test script to debug portfolio data loading"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from binance_trade_agent.portfolio_manager import PortfolioManager
from datetime import datetime

def test_portfolio_in_detail():
    """Test portfolio loading with detailed error reporting"""
    print("\n" + "="*80)
    print("PORTFOLIO MANAGER DETAILED TEST")
    print("="*80 + "\n")

    try:
        # Test 1: Initialize portfolio manager
        print("[1/5] Testing PortfolioManager initialization...")
        portfolio = PortfolioManager("/app/data/web_portfolio.db")
        print("✓ PortfolioManager initialized successfully\n")

        # Test 2: Get portfolio stats
        print("[2/5] Testing get_portfolio_stats()...")
        stats = portfolio.get_portfolio_stats()
        print(f"✓ Stats retrieved: {stats}\n")

        # Test 3: Get all positions
        print("[3/5] Testing get_all_positions()...")
        positions = portfolio.get_all_positions()
        print(f"✓ Positions retrieved: {len(positions)} items")
        if positions:
            print(f"  First position: {positions[0]}\n")
        else:
            print("  (No positions)\n")

        # Test 4: Get trade history
        print("[4/5] Testing get_trade_history()...")
        trades = portfolio.get_trade_history(limit=5)
        print(f"✓ Trades retrieved: {len(trades)} items")
        if trades:
            print(f"  First trade: {trades[0]}\n")
        else:
            print("  (No trades)\n")

        # Test 5: Simulate get_portfolio_data()
        print("[5/5] Testing portfolio data construction (simulating web_ui.get_portfolio_data)...")
        try:
            total_value = stats.get('total_value', 0)
            total_pnl = stats.get('total_pnl', 0)
            total_pnl_percent = (total_pnl / max(total_value - total_pnl, 1)) * 100 if total_value else 0
            
            positions_formatted = [
                {
                    "symbol": pos['symbol'],
                    "quantity": pos['quantity'],
                    "average_price": pos['average_price'],
                    "current_value": pos['market_value'],
                    "unrealized_pnl": pos['unrealized_pnl']
                } for pos in positions
            ]
            
            trades_formatted = [
                {
                    "symbol": trade['symbol'],
                    "side": trade['side'],
                    "quantity": trade['quantity'],
                    "price": trade['price'],
                    "timestamp": trade['timestamp'],
                    "pnl": trade.get('pnl') or 0
                } for trade in trades
            ]
            
            portfolio_data = {
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_percent,
                "open_positions": len(positions),
                "total_trades": stats.get('number_of_trades', 0),
                "positions": positions_formatted,
                "recent_trades": trades_formatted
            }
            
            print("✓ Portfolio data constructed successfully")
            print(f"  Total Value: ${total_value:,.2f}")
            print(f"  Total P&L: ${total_pnl:,.2f} ({total_pnl_percent:+.2f}%)")
            print(f"  Open Positions: {len(positions)}")
            print(f"  Total Trades: {stats.get('number_of_trades', 0)}\n")
            
            return True
            
        except Exception as e:
            print(f"✗ Error constructing portfolio data: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_portfolio_in_detail()
    print("\n" + "="*80)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ TESTS FAILED")
    print("="*80 + "\n")
    sys.exit(0 if success else 1)
