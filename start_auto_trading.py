#!/usr/bin/env python3
"""
Automated Trading Loop - Run trading agent in background

This script starts the autonomous trading agent with a specified strategy.
It continuously monitors market data and executes trades based on signals.

Usage:
    python start_auto_trading.py [--strategy STRATEGY] [--symbols SYMBOL1,SYMBOL2] [--interval SECONDS]

Examples:
    python start_auto_trading.py                          # Default: combined strategy, BTCUSDT, 60s
    python start_auto_trading.py --strategy rsi           # RSI strategy
    python start_auto_trading.py --strategy macd          # MACD strategy
    python start_auto_trading.py --symbols BTCUSDT,ETHUSDT --interval 30
"""

import argparse
import asyncio
import logging
import os
import signal
from datetime import datetime
from typing import List

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "auto_trading.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
)
logger = logging.getLogger(__name__)


class AutomatedTradingAgent:
    """Runs automated trading loop with specified strategy"""

    def __init__(self, strategy: str = "combined", symbols: List[str] = None, interval: int = 60):
        """
        Initialize automated trading agent

        Args:
            strategy: Strategy name ('rsi', 'macd', 'combined')
            symbols: List of symbols to trade (default: ['BTCUSDT'])
            interval: Seconds between trading cycles
        """
        from binance_trade_agent.common.config import config
        from binance_trade_agent.core.orchestrator import TradingOrchestrator
        from binance_trade_agent.core.portfolio_manager import PortfolioManager

        self.strategy = strategy
        self.symbols = symbols or ["BTCUSDT"]
        self.interval = interval
        self.config = config
        self.orchestrator = TradingOrchestrator(strategy_name=strategy)

        # Use same portfolio DB as dashboard so trades show up in real-time
        self.portfolio = PortfolioManager("/app/data/web_portfolio.db")

        self.running = False
        self.trades_executed = 0
        self.errors = 0

        logger.info("Initialized AutomatedTradingAgent")
        logger.info(f"  Strategy: {strategy}")
        logger.info(f"  Symbols: {', '.join(self.symbols)}")
        logger.info(f"  Interval: {interval}s")

    async def run(self):
        """Main trading loop"""
        self.running = True
        logger.info("Starting automated trading loop...")

        while self.running:
            try:
                for symbol in self.symbols:
                    try:
                        await self._trade_symbol(symbol)
                    except Exception as e:
                        self.errors += 1
                        logger.error(f"Error trading {symbol}: {str(e)}")
                        import traceback

                        traceback.print_exc()

                # Wait before next cycle
                logger.debug(f"Waiting {self.interval}s until next cycle...")
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                logger.info("Trading loop cancelled")
                break
            except Exception as e:
                self.errors += 1
                logger.error(f"Unexpected error in trading loop: {str(e)}")
                await asyncio.sleep(self.interval)

    async def _trade_symbol(self, symbol: str):
        """Execute trading workflow for a symbol"""
        try:
            quantity = self.config.get_default_quantity(symbol)

            logger.info(f"Executing trading workflow for {symbol} ({quantity} units)")

            trade_decision = await self.orchestrator.execute_trading_workflow(
                symbol=symbol, quantity=quantity, strategy_name=self.strategy
            )

            if trade_decision.executed:
                self.trades_executed += 1
                logger.info(
                    f"Trade executed: {symbol} {trade_decision.signal_type} "
                    f"@ {trade_decision.execution_price} "
                    f"(Order: {trade_decision.order_id})"
                )
            else:
                logger.debug(f"No trade signal or risk rejected: {symbol}")

        except Exception as e:
            logger.error(f"Error in trading workflow for {symbol}: {str(e)}")
            raise

    def stop(self):
        """Stop the trading loop"""
        logger.info("Stopping trading loop...")
        self.running = False
        logger.info(f"Summary: {self.trades_executed} trades, {self.errors} errors")


async def main():
    parser = argparse.ArgumentParser(
        description="Automated Trading Agent",
        epilog="Examples:\n"
        "  python start_auto_trading.py\n"
        "  python start_auto_trading.py --strategy rsi --interval 30\n"
        "  python start_auto_trading.py --symbols BTCUSDT,ETHUSDT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strategy",
        default="combined",
        help="Strategy: rsi, macd, combined (default: combined)",
    )
    parser.add_argument(
        "--symbols",
        default="BTCUSDT",
        help="Comma-separated symbols (default: BTCUSDT)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Seconds between trading cycles (default: 60)",
    )

    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")]

    logger.info("=" * 70)
    logger.info("AUTOMATED TRADING AGENT STARTED")
    logger.info("=" * 70)
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Interval: {args.interval}s")
    logger.info(f"Logs: {log_file}")
    logger.info("=" * 70)

    agent = AutomatedTradingAgent(strategy=args.strategy, symbols=symbols, interval=args.interval)

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        agent.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        logger.info("=" * 70)
        logger.info("AUTOMATED TRADING AGENT STOPPED")
        logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
