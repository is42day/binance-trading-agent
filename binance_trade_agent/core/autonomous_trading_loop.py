#!/usr/bin/env python3
"""
Autonomous Trading Loop - Continuous trading with configurable intervals
Executes trading workflow repeatedly until time limit or manual stop
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

# Add the parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance_trade_agent.common.config import config
from binance_trade_agent.common.logging_config import get_logger, setup_logging
from binance_trade_agent.core.exchange_reconciliation import ExchangeReconciliationService
from binance_trade_agent.core.orchestrator import TradingOrchestrator
from binance_trade_agent.core.performance_analytics import get_performance_analytics
from binance_trade_agent.core.portfolio_manager import PortfolioManager

# Setup structured logging for trading loop
setup_logging(
    service_name="trading-agent",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    use_json=os.getenv("LOG_FORMAT", "plain").lower() == "json",
)

logger = get_logger(__name__)

HEARTBEAT_SERVICE_NAME = "trading-agent"


class DuplicateTradingLoopError(RuntimeError):
    """Raised when a live trading-agent heartbeat indicates another instance is already running."""


class AutonomousTradingLoop:
    """
    Continuous autonomous trading loop
    """

    def __init__(
        self,
        symbols: list = None,
        trade_interval_seconds: int = 120,
        duration_minutes: int = 60,
        strategy_name: str = None,
        strategy_parameters: dict = None,
    ):
        """
        Initialize the autonomous trading loop

        Args:
            symbols: List of symbols to trade (default: from config.supported_symbols)
            trade_interval_seconds: Seconds between trades (minimum 60 for testnet)
            duration_minutes: Total duration to run (0 = infinite)
            strategy_name: Trading strategy to use
            strategy_parameters: Custom strategy parameters
        """
        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Use configured symbols if not specified
        self.symbols = symbols or config.supported_symbols
        self.trade_interval = max(trade_interval_seconds, 60)  # Min 60 seconds for testnet
        self.duration_minutes = duration_minutes
        self.strategy_name = strategy_name or "combined_default"
        self.strategy_parameters = strategy_parameters

        # Refuse to start a second instance trading against the same portfolio
        # (e.g. an accidental scale-out or a stale container left over from a
        # redeploy). Must run before the orchestrator/execution agent stand up
        # their own client connections.
        self.heartbeat_stale_after_seconds = max(self.trade_interval * 3, 180)
        self._heartbeat_portfolio = PortfolioManager("/app/data/web_portfolio.db")
        self._check_no_concurrent_instance()

        # Initialize orchestrator
        self.orchestrator = TradingOrchestrator(
            strategy_name=self.strategy_name,
            strategy_parameters=self.strategy_parameters,
        )

        self.logger.info(
            f"AutonomousTradingLoop initialized:\n"
            f"  Symbols: {self.symbols}\n"
            f"  Interval: {self.trade_interval}s\n"
            f"  Duration: {self.duration_minutes} min\n"
            f"  Strategy: {self.strategy_name}"
        )

        # Tracking
        self.trades_executed = 0
        self.start_time = None
        self.stop_flag = False

        # Set (in addition to stop_flag) by an external stop request — e.g.
        # main.py's SIGTERM handler — to interrupt an in-progress
        # end-of-cycle wait immediately, rather than leaving the loop
        # blocked in a plain asyncio.sleep(trade_interval) for up to
        # trade_interval seconds before it next checks stop_flag. Under
        # Docker's default ~10s stop grace period, that meant a routine
        # `docker stop`/restart almost always got SIGKILLed mid-sleep,
        # skipping release_heartbeat() and leaving the concurrent-instance
        # guard blocking the replacement container for
        # heartbeat_stale_after_seconds.
        self._stop_event = asyncio.Event()

        # Tracks the last kline open_time (ms) processed per symbol by the
        # stream-driven trailing-stop watcher, to avoid re-evaluating the
        # same closed candle on every check tick.
        self._stream_last_candle_time: dict[str, int] = {}
        self.stream_trailing_stop_watcher_enabled = os.getenv(
            "ENABLE_STREAM_TRAILING_STOP_WATCHER", "true"
        ).lower() in {"true", "1", "yes", "on"}

        if os.getenv("EXCHANGE_RECONCILE_ON_START", "true").lower() in {
            "true",
            "1",
            "yes",
            "on",
        }:
            self._reconcile_exchange_orders()

    def _check_no_concurrent_instance(self):
        """
        Refuse to start if another trading-agent instance's heartbeat is still
        fresh, to prevent two loops trading against the same portfolio
        concurrently (e.g. an accidental scale-out or a stale container left
        running after a redeploy).

        Claims the lease atomically (a single UPDATE...WHERE / INSERT, not a
        separate read-then-write) so two instances starting at the same time
        can't both observe "no live heartbeat" and both proceed.
        """
        claimed = self._heartbeat_portfolio.try_claim_heartbeat(
            HEARTBEAT_SERVICE_NAME,
            stale_after_seconds=self.heartbeat_stale_after_seconds,
            status="starting",
            details={"pid": os.getpid()},
        )
        if not claimed:
            raise DuplicateTradingLoopError(
                "Refusing to start: another trading-agent instance appears to be "
                "running (heartbeat lease is live, considered stale after "
                f"{self.heartbeat_stale_after_seconds}s). If you're certain no "
                "other instance is running, wait for the heartbeat to go stale "
                "or clear the 'trading-agent' row in the heartbeat table."
            )

    def _refresh_heartbeat(self, status: str = "healthy", details: dict | None = None):
        """Record that this instance is the live trading-agent."""
        try:
            self._heartbeat_portfolio.update_heartbeat(
                HEARTBEAT_SERVICE_NAME,
                status=status,
                details={"pid": os.getpid(), **(details or {})},
            )
        except Exception as exc:
            self.logger.warning(f"Failed to refresh trading-agent heartbeat: {exc}")

    def release_heartbeat(self):
        """
        Mark this instance's heartbeat lease as released.

        Callers that stop the loop from outside (e.g. the dashboard's
        stop_agent(), which cancels the run() task without awaiting it)
        should call this directly rather than relying on run() reaching its
        own "final summary" section — task.cancel() delivers CancelledError
        at whatever await point the loop happens to be at, which can skip
        past that section entirely, leaving a live-looking heartbeat behind
        that then blocks a restart until it goes stale.
        """
        self._refresh_heartbeat(status="stopped")

    def _reconcile_exchange_orders(self):
        """Reconcile locally tracked exchange orders before trading resumes."""
        try:
            service = ExchangeReconciliationService(
                client=self.orchestrator.execution_agent.client,
                portfolio=self.orchestrator.execution_agent.portfolio,
            )
            result = service.reconcile_open_orders()
            self.logger.info(
                "Exchange reconciliation complete: "
                f"checked={result['checked']}, "
                f"updated={result['updated']}, "
                f"booked_trades={result['booked_trades']}, "
                f"errors={len(result['errors'])}"
            )
        except Exception as exc:
            if os.getenv("EXCHANGE_RECONCILE_REQUIRED", "true").lower() in {
                "true",
                "1",
                "yes",
                "on",
            }:
                raise
            self.logger.warning(f"Exchange reconciliation failed but startup will continue: {exc}")

    async def _update_trailing_stops(self):
        """
        Update trailing stops for all active positions using REST prices.

        This is the periodic, cycle-bound fallback — it runs once per
        trading cycle regardless of whether the stream-driven watcher
        (_run_trailing_stop_watcher) is active, so a stop is never left
        unchecked for longer than one full cycle even if streaming is
        unavailable.

        Skips entirely while emergency stop is active — a triggered trailing
        stop otherwise places a real order directly via the execution agent,
        bypassing risk_agent.validate_trade.
        """
        risk_agent = self.orchestrator.risk_agent

        if risk_agent._shared_emergency_stop_enabled():
            self.logger.warning(
                "🛑 Emergency stop is ACTIVE — skipping trailing stop updates/closes this cycle."
            )
            return

        trailing_info = risk_agent.get_trailing_stop_info()

        if not trailing_info.get("positions"):
            return

        self.logger.info(f"\n🎯 Checking {trailing_info['active_stops']} trailing stop(s)...")

        # Get current prices for all tracked symbols
        prices = {}
        for symbol in trailing_info["positions"].keys():
            try:
                price = self.orchestrator.market_agent.get_latest_price(symbol)
                prices[symbol] = price
            except Exception as e:
                self.logger.error(f"   Failed to get price for {symbol}: {e}")

        results = risk_agent.update_all_trailing_stops(prices)
        await self._process_trailing_stop_results(results)

    async def _process_trailing_stop_results(self, results: dict):
        """
        Given per-symbol results from risk_agent.update_all_trailing_stops(),
        close any triggered stops and log status for the rest.

        Shared between the REST-cycle path (_update_trailing_stops) and the
        stream-driven watcher (_check_trailing_stop_via_stream) so both use
        the exact same close-order logic.
        """
        risk_agent = self.orchestrator.risk_agent

        for symbol, result in results.items():
            if result.get("stop_triggered"):
                # Emergency stop is cross-process shared state — it can be
                # activated by another process between the check at the top
                # of this method and this specific order placement, so
                # re-check immediately before each order rather than relying
                # on the once-per-call check above.
                if risk_agent._shared_emergency_stop_enabled():
                    self.logger.warning(
                        f"   🛑 Emergency stop activated mid-cycle — skipping {symbol} stop order."
                    )
                    continue

                self.logger.warning(f"   ⚠️ {symbol} trailing stop TRIGGERED!")
                self.logger.info(
                    f"      Entry: ${result['entry_price']:,.2f}, "
                    f"Stop: ${result['current_stop']:,.2f}, "
                    f"Current: ${result['current_price']:,.2f}"
                )

                # Execute the stop order
                try:
                    side = result["side"]
                    # Opposite order to close position
                    close_side = "sell" if side == "buy" else "buy"

                    # Get quantity (for now, use default - in production, would track position size)
                    quantity = config.get_default_quantity(symbol)

                    if close_side == "sell":
                        order = self.orchestrator.execution_agent.place_sell_order(symbol, quantity)
                    else:
                        order = self.orchestrator.execution_agent.place_buy_order(symbol, quantity)

                    self.logger.info(
                        f"      ✅ Stop order executed: {close_side.upper()} {quantity} {symbol}"
                    )
                    self.trades_executed += 1

                    # Close the trailing stop tracking
                    close_result = risk_agent.close_trailing_stop(
                        symbol, close_price=result["current_price"]
                    )
                    pnl_pct = close_result.get("pnl_pct", 0) * 100
                    self.logger.info(f"      PnL: {pnl_pct:+.2f}%")

                    # Record trade exit in performance analytics
                    try:
                        analytics = get_performance_analytics(config.portfolio_initial_value)
                        analytics.record_trade_exit(
                            symbol=symbol,
                            exit_price=result["current_price"],
                            notes="Trailing stop triggered",
                        )
                    except Exception as ae:
                        self.logger.warning(f"Failed to record trade exit in analytics: {ae}")

                except Exception as e:
                    self.logger.error(f"      ❌ Failed to execute stop order: {e}")
            else:
                # Log trailing stop status
                profit_pct = result.get("profit_pct", 0) * 100
                self.logger.info(
                    f"   {symbol}: Price ${result['current_price']:,.2f}, "
                    f"Stop ${result['current_stop']:,.2f}, "
                    f"P&L: {profit_pct:+.2f}%"
                )

    async def _check_trailing_stop_via_stream(
        self, symbol: str, interval: str, registered_at_ms: Optional[int] = None
    ) -> bool:
        """
        Check one symbol's trailing stop against the latest closed candle
        from the WebSocket kline stream, if fresh data is available.

        Returns True if a new candle was processed (regardless of whether a
        stop triggered), so the caller can track per-symbol last-seen candle
        time and avoid re-evaluating the same candle repeatedly.
        """
        from .market_streams import get_stream_manager

        manager = get_stream_manager()
        candles = manager.get_ohlcv(symbol, interval, limit=1)
        if not candles:
            return False

        open_time_ms, _open, _high, _low, close, _volume = candles[-1]
        last_seen = self._stream_last_candle_time.get(symbol)
        if last_seen is None and registered_at_ms is not None:
            # First tick for this symbol since it was (re-)registered — a
            # candle that opened before the position existed reflects
            # pre-entry price action, not something the trailing stop should
            # react to (e.g. it could falsely trigger a stop or seed the
            # trailing level off a price the position was never exposed to).
            last_seen = registered_at_ms - 1
        if last_seen is not None and open_time_ms <= last_seen:
            self._stream_last_candle_time[symbol] = last_seen
            return False  # already processed, or predates the position
        self._stream_last_candle_time[symbol] = open_time_ms

        results = self.orchestrator.risk_agent.update_all_trailing_stops({symbol: close})
        if results:
            await self._process_trailing_stop_results(results)
        return True

    async def _run_trailing_stop_watcher(
        self, interval: str = "1m", check_every_seconds: float = 5.0
    ):
        """
        Background task: react to trailing-stop breaches as soon as a new
        kline closes on the WebSocket stream, instead of waiting for the
        next full trading cycle (which can be minutes away with several
        symbols and a long trade_interval).

        This is additive, not a replacement for _update_trailing_stops — if
        streaming is unavailable (package missing, network issue, symbol not
        subscribed yet), get_ohlcv returns None/stale and this tick is
        skipped; the REST-based per-cycle check remains the reliable
        fallback regardless of whether this watcher is running at all.
        """
        from .market_streams import get_stream_manager

        manager = get_stream_manager()
        subscribed = []
        for symbol in self.symbols:
            try:
                await manager.subscribe(symbol, interval)
                subscribed.append(symbol)
            except Exception as exc:
                self.logger.warning(
                    f"Trailing-stop watcher: failed to subscribe to {symbol}@{interval}: {exc}"
                )

        try:
            while not self.stop_flag:
                risk_agent = self.orchestrator.risk_agent
                trailing_info = risk_agent.get_trailing_stop_info()
                positions = trailing_info.get("positions", {})
                for symbol, position in list(positions.items()):
                    try:
                        registered_at_ms = None
                        registered_at = position.get("registered_at")
                        if registered_at:
                            registered_at_ms = int(
                                datetime.fromisoformat(registered_at).timestamp() * 1000
                            )
                        await self._check_trailing_stop_via_stream(
                            symbol, interval, registered_at_ms=registered_at_ms
                        )
                    except Exception as exc:
                        self.logger.warning(
                            f"Trailing-stop watcher: error checking {symbol}: {exc}"
                        )
                await asyncio.sleep(check_every_seconds)
        except asyncio.CancelledError:
            pass
        finally:
            # get_stream_manager() is a shared, process-wide singleton — only
            # unsubscribe the (symbol, interval) pairs this watcher itself
            # subscribed, not every subscription in the process (e.g. ones
            # held for the /api/v1/market/streams/status endpoint).
            for symbol in subscribed:
                try:
                    await manager.unsubscribe(symbol, interval)
                except Exception as exc:
                    self.logger.warning(
                        f"Trailing-stop watcher: failed to unsubscribe {symbol}@{interval}: {exc}"
                    )

    async def run(self):
        """
        Run the autonomous trading loop
        """
        self.start_time = datetime.now()
        end_time = (
            self.start_time + timedelta(minutes=self.duration_minutes)
            if self.duration_minutes > 0
            else None
        )

        self.logger.info("🚀 Starting autonomous trading loop...")
        if end_time:
            self.logger.info(f"   Will run until: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.logger.info("   Running indefinitely (press Ctrl+C to stop)")

        watcher_task = None
        if self.stream_trailing_stop_watcher_enabled:
            watcher_task = asyncio.create_task(
                self._run_trailing_stop_watcher(), name="trailing-stop-watcher"
            )

        cycle = 0
        while not self.stop_flag:
            # Check if time limit reached
            if end_time and datetime.now() >= end_time:
                self.logger.info("⏰ Time limit reached. Stopping autonomous trading.")
                break

            cycle += 1
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"Trading Cycle #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
            self.logger.info(f"{'='*70}")

            emergency_stop_active = self.orchestrator.risk_agent._shared_emergency_stop_enabled()
            if emergency_stop_active:
                self.logger.warning(
                    "🛑 Emergency stop is ACTIVE — skipping trade execution this cycle. "
                    "Resume trading to continue."
                )

            # Renew the lease at the top of every cycle, before the
            # per-symbol loop below — which is the only other place that
            # refreshes it, and is skipped entirely while emergency stop is
            # active. Without this, a process left halted-but-alive for
            # longer than heartbeat_stale_after_seconds lets its own
            # heartbeat go stale, so the concurrent-instance guard would
            # wrongly let a second instance start once this one resumes.
            self._refresh_heartbeat(status="healthy", details={"cycle": cycle})

            # Execute trades for each symbol
            for symbol in self.symbols:
                if self.stop_flag or emergency_stop_active:
                    break

                try:
                    self.logger.info(f"\n📊 Processing {symbol}...")

                    # Get default quantity
                    quantity = config.get_default_quantity(symbol)

                    # Execute trading workflow
                    decision = await self.orchestrator.execute_trading_workflow(
                        symbol=symbol, quantity=quantity
                    )

                    # Log decision
                    self.logger.info(
                        f"  Signal: {decision.signal_type.upper()}\n"
                        f"  Confidence: {decision.confidence:.1%}\n"
                        f"  Price: ${decision.price:,.2f}\n"
                        f"  Risk Approved: {decision.risk_approved}"
                    )

                    if decision.executed:
                        self.trades_executed += 1
                        exec_price = (
                            f"${decision.execution_price:,.2f}"
                            if decision.execution_price
                            else "N/A"
                        )
                        exec_time = (
                            decision.execution_time.strftime("%H:%M:%S")
                            if decision.execution_time
                            else "N/A"
                        )
                        self.logger.info(
                            f"  ✅ TRADE EXECUTED!\n"
                            f"     Order ID: {decision.order_id}\n"
                            f"     Fill Price: {exec_price}\n"
                            f"     Time: {exec_time}"
                        )
                    else:
                        self.logger.info("  ⏸️ Trade not executed (risk check failed)")

                except Exception as e:
                    self.logger.error(f"  ❌ Error processing {symbol}: {str(e)}", exc_info=True)

                # Renew the lease after each symbol, not just once per cycle —
                # a cycle covering many symbols (or a slow one) could
                # otherwise let the heartbeat go stale before the next
                # top-of-cycle refresh, letting another instance start while
                # this one is still live and trading.
                self._refresh_heartbeat(
                    status="healthy", details={"cycle": cycle, "symbol": symbol}
                )

            # Check and update trailing stops for all active positions
            await self._update_trailing_stops()

            # Log cycle summary
            elapsed = datetime.now() - self.start_time
            self.logger.info("\n📈 Cycle Summary:")
            self.logger.info(f"   Cycles completed: {cycle}")
            self.logger.info(f"   Trades executed: {self.trades_executed}")
            self.logger.info(f"   Time elapsed: {elapsed}")

            # Wait before next cycle (unless it's the last iteration)
            if not self.stop_flag:
                if end_time and datetime.now() >= end_time:
                    break

                self.logger.info(f"\n⏳ Waiting {self.trade_interval} seconds before next cycle...")
                try:
                    # Races the normal interval sleep against _stop_event,
                    # so a SIGTERM handler setting the event interrupts the
                    # wait immediately instead of leaving the loop blocked
                    # for up to trade_interval seconds. Under Docker's
                    # default ~10s stop grace period, that meant a routine
                    # `docker stop`/restart almost always got SIGKILLed
                    # mid-sleep, skipping release_heartbeat() and leaving
                    # the concurrent-instance guard blocking the
                    # replacement container until the lease went stale.
                    sleep_task = asyncio.ensure_future(asyncio.sleep(self.trade_interval))
                    stop_task = asyncio.ensure_future(self._stop_event.wait())
                    done, pending = await asyncio.wait(
                        {sleep_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
                    if stop_task in done:
                        self.logger.info("Wait interrupted by stop request")
                except asyncio.CancelledError:
                    self.logger.info("Interrupted by user during sleep")
                    self.stop_flag = True

        if watcher_task is not None:
            watcher_task.cancel()
            try:
                await watcher_task
            except asyncio.CancelledError:
                pass

        # Final summary
        elapsed = datetime.now() - self.start_time
        self.logger.info(f"\n{'='*70}")
        self.logger.info("🏁 TRADING SESSION COMPLETE")
        self.logger.info(f"{'='*70}")
        self.logger.info(f"Total cycles: {cycle}")
        self.logger.info(f"Total trades executed: {self.trades_executed}")
        self.logger.info(f"Total time: {elapsed}")
        self.logger.info(
            f"Average trades per minute: {(self.trades_executed / elapsed.total_seconds() * 60):.2f}"
        )
        # Mark the heartbeat "stopped" on a clean exit so a restart doesn't have
        # to wait out the staleness window unnecessarily.
        self._refresh_heartbeat(status="stopped", details={"cycle": cycle})


async def main():
    """
    Main entry point
    """
    # Get configuration from environment or config
    # If TRADING_SYMBOLS is set, use it, otherwise use config.supported_symbols
    symbols_env = os.getenv("TRADING_SYMBOLS")
    symbols = symbols_env.split(",") if symbols_env else config.supported_symbols
    interval = int(os.getenv("TRADING_INTERVAL_SECONDS", "120"))
    duration = int(os.getenv("TRADING_DURATION_MINUTES", "60"))
    strategy = os.getenv("STRATEGY_NAME", "combined_default")

    # Create and run loop
    loop = AutonomousTradingLoop(
        symbols=symbols,
        trade_interval_seconds=interval,
        duration_minutes=duration,
        strategy_name=strategy,
    )

    try:
        await loop.run()
    except KeyboardInterrupt:
        print("\n\n⛔ Interrupted by user. Shutting down gracefully...")
        loop.stop_flag = True


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run
    asyncio.run(main())
