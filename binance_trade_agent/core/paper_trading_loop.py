"""
Paper Trading Loop - Run strategies with real data, simulated execution

This is the recommended way to test strategies before going live.
Uses REAL Binance mainnet data but doesn't execute real trades.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import List

from binance_trade_agent.agents.market_data_agent import MarketDataAgent
from binance_trade_agent.core.paper_trading import get_paper_trading_engine
from binance_trade_agent.strategies import (
    EdgeStrategy,
    SmartEntryStrategy,
    StrategyManager,
    create_balanced_edge_strategy,
    create_conservative_edge_strategy,
)

logger = logging.getLogger(__name__)


class MainnetDataClient:
    """
    Client that ALWAYS fetches from Binance mainnet.
    Used for paper trading to get real market data.
    """

    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self._session = None

    def get_latest_price(self, symbol: str) -> float:
        """Get real price from mainnet"""
        import requests

        response = requests.get(
            f"{self.base_url}/ticker/price",
            params={"symbol": symbol},
            timeout=5,
        )
        return float(response.json()["price"])

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> list:
        """Get real OHLCV data from mainnet"""
        import requests

        response = requests.get(
            f"{self.base_url}/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=10,
        )
        return response.json()

    def get_order_book(self, symbol: str, limit: int = 10) -> dict:
        """Get real order book from mainnet"""
        import requests

        response = requests.get(
            f"{self.base_url}/depth",
            params={"symbol": symbol, "limit": limit},
            timeout=5,
        )
        return response.json()


class PaperTradingLoop:
    """
    Run paper trading with real market data.

    This loop:
    1. Fetches REAL data from Binance mainnet
    2. Runs strategy signals
    3. Executes paper trades (simulated)
    4. Tracks performance
    """

    def __init__(
        self,
        symbols: List[str] = None,
        strategy_name: str = "combined_edge",
        initial_balance: float = 100.0,  # Match user's €100 test
        trade_interval_seconds: int = 120,
        position_size_pct: float = 0.25,  # 25% per trade max
        max_iterations: int = 0,
        reset: bool = False,
    ):
        self.symbols = symbols or ["BTCUSDT"]
        self.strategy_name = strategy_name
        self.trade_interval = trade_interval_seconds
        self.position_size_pct = position_size_pct
        self.max_iterations = max_iterations

        # Use mainnet data client
        self.data_client = MainnetDataClient()

        # Create market agent with mainnet client
        self.market_agent = MarketDataAgent(binance_client=self.data_client)

        # Initialize strategy
        self.strategy = self._create_strategy(strategy_name)

        # Paper trading engine
        self.paper_engine = get_paper_trading_engine(initial_balance=initial_balance)
        if reset:
            self.paper_engine.reset(initial_balance=initial_balance)

        # Control flags
        self.stop_flag = False
        self.is_running = False

        logger.info(
            f"Paper trading loop initialized: "
            f"symbols={symbols}, strategy={strategy_name}, "
            f"balance=${initial_balance:.2f}"
        )

    def _create_strategy(self, name: str):
        """Create strategy instance"""
        if name == "combined_edge":
            return create_balanced_edge_strategy(self.market_agent)
        elif name == "edge_conservative":
            return create_conservative_edge_strategy(self.market_agent)
        elif name == "edge":
            return EdgeStrategy(self.market_agent)
        elif name == "smart_entry":
            return SmartEntryStrategy(self.market_agent)
        else:
            # Fallback to strategy manager
            manager = StrategyManager()
            return manager.strategies.get(name, create_balanced_edge_strategy(self.market_agent))

    def _fetch_ohlcv(self, symbol: str, interval: str = "1h", limit: int = 100) -> list:
        """Fetch OHLCV data from mainnet"""
        try:
            klines = self.data_client.get_klines(symbol, interval, limit)
            ohlcv_data = []
            for kline in klines:
                ohlcv_data.append(
                    {
                        "timestamp": int(kline[0]),
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5]),
                    }
                )
            return ohlcv_data
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return []

    def _calculate_position_size(self, symbol: str, price: float) -> float:
        """Calculate position size based on portfolio and settings"""
        stats = self.paper_engine.get_portfolio_summary()
        available_balance = stats["current_balance"]

        # Don't trade if we already have a position
        if symbol in self.paper_engine.portfolio.open_positions:
            return 0.0

        # Calculate position value
        position_value = available_balance * self.position_size_pct

        # Convert to quantity
        quantity = position_value / price

        # Round to appropriate precision
        if "BTC" in symbol:
            quantity = round(quantity, 6)
        elif "ETH" in symbol:
            quantity = round(quantity, 5)
        else:
            quantity = round(quantity, 4)

        return quantity

    async def _process_symbol(self, symbol: str):
        """Process a single symbol for trading signals"""
        try:
            # Fetch real data
            ohlcv_data = self._fetch_ohlcv(symbol)
            if not ohlcv_data:
                return

            current_price = ohlcv_data[-1]["close"]

            # Generate signal
            signal = self.strategy.generate_signal(symbol, ohlcv_data)

            action = signal.get("action", "HOLD")
            confidence = signal.get("confidence", 0)
            rejection_reason = signal.get("rejection_reason")

            # Log signal
            self.paper_engine.log_signal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                strategy=self.strategy_name,
                metadata=signal,
                executed=False,  # Will update if executed
                rejection_reason=rejection_reason,
            )

            # Print signal info
            timestamp = datetime.now().strftime("%H:%M:%S")
            if action != "HOLD":
                logger.info(
                    f"[{timestamp}] {symbol}: {action} signal " f"(confidence: {confidence:.2f})"
                )
                if rejection_reason:
                    logger.info(f"    [!] Not executed: {rejection_reason}")

            # Execute paper trade if signal is actionable
            if action == "BUY" and confidence >= 0.1:  # Lower threshold for paper trading
                quantity = self._calculate_position_size(symbol, current_price)
                if quantity > 0:
                    result = self.paper_engine.execute_paper_trade(
                        symbol=symbol,
                        side="BUY",
                        quantity=quantity,
                        strategy=self.strategy_name,
                        signal_confidence=confidence,
                        signal_metadata=signal,
                    )
                    if result["success"]:
                        logger.info(
                            f"    [+] Paper BUY executed: {quantity} {symbol} @ ${current_price:.2f}"
                        )
                    else:
                        logger.warning(f"    [-] Paper BUY failed: {result.get('error')}")

            elif action == "SELL" and symbol in self.paper_engine.portfolio.open_positions:
                position = self.paper_engine.portfolio.open_positions[symbol]
                result = self.paper_engine.execute_paper_trade(
                    symbol=symbol,
                    side="SELL",
                    quantity=position.quantity,
                    strategy=self.strategy_name,
                    signal_confidence=confidence,
                    signal_metadata=signal,
                )
                if result["success"]:
                    pnl = result.get("pnl", 0)
                    marker = "[WIN]" if pnl > 0 else "[LOSS]"
                    logger.info(
                        f"    {marker} Paper SELL executed: P&L ${pnl:.2f} ({result.get('pnl_percent', 0):.2f}%)"
                    )

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")

    async def run(self):
        """Run the paper trading loop"""
        self.is_running = True
        self.stop_flag = False

        logger.info("=" * 60)
        logger.info("PAPER TRADING MODE - Using REAL mainnet data")
        logger.info("=" * 60)
        logger.info(f"Strategy: {self.strategy_name}")
        logger.info(f"Symbols: {', '.join(self.symbols)}")
        logger.info(f"Interval: {self.trade_interval}s")

        stats = self.paper_engine.get_portfolio_summary()
        logger.info(f"Starting balance: ${stats['current_balance']:.2f}")
        logger.info("=" * 60)

        iteration = 0
        while not self.stop_flag:
            iteration += 1

            logger.info(
                f"\n--- Iteration {iteration} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
            )

            # Process each symbol
            for symbol in self.symbols:
                await self._process_symbol(symbol)
                await asyncio.sleep(1)  # Small delay between symbols

            # Always save portfolio state so the status endpoint shows "active"
            try:
                self.paper_engine._save_state()
            except Exception as e:
                logger.warning(f"Could not save portfolio state: {e}")

            # Print portfolio summary every 5 iterations
            if iteration % 5 == 0:
                self._print_summary()

            if self.max_iterations and iteration >= self.max_iterations:
                logger.info("Max paper-trading iterations reached. Stopping.")
                break

            # Wait for next iteration
            await asyncio.sleep(self.trade_interval)

        self.is_running = False
        logger.info("Paper trading loop stopped")
        self._print_summary()

    def _print_summary(self):
        """Print portfolio summary"""
        stats = self.paper_engine.get_portfolio_summary()

        logger.info("\n" + "=" * 40)
        logger.info("PAPER TRADING SUMMARY")
        logger.info("=" * 40)
        logger.info(f"Balance: ${stats['current_balance']:.2f}")
        logger.info(f"Total P&L: ${stats['total_pnl']:.2f} ({stats['total_pnl_percent']:.2f}%)")
        logger.info(
            f"Trades: {stats['total_trades']} (W:{stats['winning_trades']} L:{stats['losing_trades']})"
        )
        logger.info(f"Win Rate: {stats['win_rate']:.1f}%")
        logger.info(
            f"Max Drawdown: ${stats['max_drawdown']:.2f} ({stats['max_drawdown_percent']:.1f}%)"
        )

        if stats["open_positions"] > 0:
            logger.info("\nOpen Positions:")
            for symbol, pos in stats.get("position_values", {}).items():
                marker = "[+]" if pos["unrealized_pnl"] > 0 else "[-]"
                logger.info(
                    f"  {marker} {symbol}: ${pos['value']:.2f} "
                    f"(P&L: ${pos['unrealized_pnl']:.2f})"
                )
        logger.info("=" * 40 + "\n")

    def stop(self):
        """Stop the paper trading loop"""
        self.stop_flag = True


def run_paper_trading(
    symbols: List[str] = None,
    strategy: str = "combined_edge",
    balance: float = 100.0,
    interval: int = 120,
    max_iterations: int = 0,
    reset: bool = False,
):
    """
    Run paper trading from command line.

    Usage:
        python -m binance_trade_agent.core.paper_trading_loop
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("data/paper_trading/paper_trading.log"),
        ],
    )

    symbols = symbols or ["BTCUSDT"]

    loop = PaperTradingLoop(
        symbols=symbols,
        strategy_name=strategy,
        initial_balance=balance,
        trade_interval_seconds=interval,
        max_iterations=max_iterations,
        reset=reset,
    )

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        logger.info("\nStopping paper trading...")
        loop.stop()

    signal.signal(signal.SIGINT, signal_handler)

    # Run the loop
    asyncio.run(loop.run())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run paper trading with real data")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT"], help="Symbols to trade")
    parser.add_argument("--strategy", default="combined_edge", help="Strategy name")
    parser.add_argument("--balance", type=float, default=100.0, help="Initial balance in USDT")
    parser.add_argument("--interval", type=int, default=120, help="Trading interval in seconds")
    parser.add_argument("--iterations", type=int, default=0, help="Stop after N iterations")
    parser.add_argument("--reset", action="store_true", help="Reset paper portfolio before running")

    args = parser.parse_args()

    run_paper_trading(
        symbols=args.symbols,
        strategy=args.strategy,
        balance=args.balance,
        interval=args.interval,
        max_iterations=args.iterations,
        reset=args.reset,
    )
