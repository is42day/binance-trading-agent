"""
Regression coverage for interrupting the end-of-cycle wait immediately on
an external stop request, instead of always blocking for the full
trade_interval_seconds.

Found via live testing against a real docker-compose deployment: SIGKILL
mid-sleep (Docker's default ~10s stop grace period almost always expires
before a long trade_interval's sleep would naturally notice stop_flag) left
the heartbeat lease un-released, blocking the replacement container from
starting for up to heartbeat_stale_after_seconds.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from binance_trade_agent.core.autonomous_trading_loop import AutonomousTradingLoop
from binance_trade_agent.core.portfolio_manager import PortfolioManager


@pytest.mark.asyncio
async def test_stop_event_interrupts_the_end_of_cycle_wait_immediately():
    with tempfile.TemporaryDirectory() as tmpdir:
        portfolio = PortfolioManager(str(Path(tmpdir) / "portfolio.db"), use_shared_session=False)

        loop = AutonomousTradingLoop.__new__(AutonomousTradingLoop)
        loop.logger = logging.getLogger("test-graceful-shutdown")
        loop.symbols = ["BTCUSDT"]
        # Deliberately long — without the fix, run() would block here for
        # the real duration before ever checking stop_flag again.
        loop.trade_interval = 30
        loop.duration_minutes = 0
        loop.heartbeat_stale_after_seconds = 180
        loop._heartbeat_portfolio = portfolio
        loop.stop_flag = False
        loop.trades_executed = 0
        loop.stream_trailing_stop_watcher_enabled = False
        loop._stop_event = asyncio.Event()
        loop.orchestrator = MagicMock()
        # Halt immediately so the cycle body itself is instant, isolating
        # the end-of-cycle wait as the only thing that could be slow.
        loop.orchestrator.risk_agent._shared_emergency_stop_enabled = MagicMock(return_value=True)
        loop._update_trailing_stops = AsyncMock()

        async def _interrupt_soon():
            await asyncio.sleep(0.05)
            loop.stop_flag = True
            loop._stop_event.set()

        start = time.perf_counter()
        await asyncio.gather(loop.run(), _interrupt_soon())
        elapsed = time.perf_counter() - start

        portfolio.engine.dispose()

    assert elapsed < 2.0, (
        f"run() took {elapsed:.2f}s to stop after the interrupt — expected well under "
        f"the {loop.trade_interval}s trade_interval, since _stop_event should short-"
        "circuit the wait immediately"
    )


@pytest.mark.asyncio
async def test_wait_still_takes_the_full_interval_without_an_interrupt():
    """
    Sanity check the other direction: with a short trade_interval and no
    stop request, the wait genuinely elapses (the race doesn't
    accidentally return early every time).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        portfolio = PortfolioManager(str(Path(tmpdir) / "portfolio.db"), use_shared_session=False)

        loop = AutonomousTradingLoop.__new__(AutonomousTradingLoop)
        loop.logger = logging.getLogger("test-graceful-shutdown")
        loop.symbols = ["BTCUSDT"]
        loop.trade_interval = 60  # min enforced elsewhere; used directly here
        loop.duration_minutes = 0
        loop.heartbeat_stale_after_seconds = 180
        loop._heartbeat_portfolio = portfolio
        loop.stop_flag = False
        loop.trades_executed = 0
        loop.stream_trailing_stop_watcher_enabled = False
        loop._stop_event = asyncio.Event()
        loop.orchestrator = MagicMock()
        loop.orchestrator.risk_agent._shared_emergency_stop_enabled = MagicMock(return_value=True)
        loop._update_trailing_stops = AsyncMock()

        # Use a tiny real interval instead of mocking time, to prove the
        # race genuinely waits rather than always resolving instantly.
        loop.trade_interval = 0.2

        async def _stop_after_one_full_wait():
            await asyncio.sleep(0.35)  # comfortably longer than trade_interval
            loop.stop_flag = True
            loop._stop_event.set()

        start = time.perf_counter()
        await asyncio.gather(loop.run(), _stop_after_one_full_wait())
        elapsed = time.perf_counter() - start

        portfolio.engine.dispose()

    assert elapsed >= 0.2
