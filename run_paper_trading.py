"""
Run Paper Trading - Test strategies with REAL market data, NO real money

This script uses REAL Binance mainnet data but executes simulated trades.
Perfect for validating strategies before risking real capital.

Usage:
    python run_paper_trading.py
    python run_paper_trading.py --strategy edge_conservative --balance 100
"""

import argparse
import logging
import os
import sys

# Ensure proper path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from binance_trade_agent.core.paper_trading_loop import run_paper_trading


def main():
    parser = argparse.ArgumentParser(
        description="Paper Trading with Real Market Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_paper_trading.py
      Run with defaults (BTCUSDT, combined_edge strategy, $100)
  
  python run_paper_trading.py --symbols BTCUSDT ETHUSDT --balance 500
      Trade BTC and ETH with $500
  
  python run_paper_trading.py --strategy edge_conservative --interval 300
      Use conservative strategy, check every 5 minutes

Available Strategies:
  - combined_edge      : Recommended - Edge + Smart Entry + TA confirmation
  - edge_conservative  : More selective, fewer trades
  - edge               : Contrarian signals only
  - smart_entry        : Entry timing optimization
  - combined           : Traditional TA combination
  - rsi                : RSI only
  - macd               : MACD only
  - bollinger          : Bollinger Bands only
        """
    )
    
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT"],
        help="Trading symbols (default: BTCUSDT)"
    )
    parser.add_argument(
        "--strategy",
        default="combined_edge",
        help="Strategy to use (default: combined_edge)"
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=100.0,
        help="Starting balance in USDT (default: 100)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Check interval in seconds (default: 120)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧪 PAPER TRADING MODE")
    print("=" * 60)
    print(f"  📊 Data Source:  REAL Binance Mainnet")
    print(f"  💰 Execution:    SIMULATED (no real money)")
    print(f"  📈 Strategy:     {args.strategy}")
    print(f"  🎯 Symbols:      {', '.join(args.symbols)}")
    print(f"  💵 Balance:      ${args.balance:.2f}")
    print(f"  ⏱️  Interval:     {args.interval}s")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")
    
    # Create data directory
    os.makedirs("data/paper_trading", exist_ok=True)
    
    run_paper_trading(
        symbols=args.symbols,
        strategy=args.strategy,
        balance=args.balance,
        interval=args.interval,
    )


if __name__ == "__main__":
    main()
