"""
Regression coverage for the event-driven trailing-stop watcher.

Previously, trailing-stop checks only ran once per full trading cycle via
REST polling (core/market_streams.py's WebSocket kline stream existed but
was never consumed anywhere in the trade/stop-loss decision path — only
exposed via a read-only status endpoint). A stop-loss breach could go
unnoticed for up to a full cycle interval (which can be minutes, across
several symbols).

_run_trailing_stop_watcher subscribes to the kline stream for each traded
symbol and reacts to each newly closed candle independently of the main
cycle, using the exact same close-order logic
(_process_trailing_stop_results) as the REST-based path.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from binance_trade_agent.core.autonomous_trading_loop import AutonomousTradingLoop
from binance_trade_agent.core.market_streams import KlineStreamManager


def _kline_msg(t: int, close: float, closed: bool = True) -> dict:
    return {
        "e": "kline",
        "k": {
            "t": t,
            "o": str(close - 1),
            "h": str(close + 1),
            "l": str(close - 2),
            "c": str(close),
            "v": "100.0",
            "x": closed,
        },
    }


def _factory_from_messages(messages: List[dict]):
    async def _factory(symbol, interval) -> AsyncIterator[dict]:
        for msg in messages:
            yield msg
        await asyncio.sleep(3600)  # block until the subscribing task is cancelled

    return _factory


async def _wait_for_candles(
    manager: KlineStreamManager, symbol: str, interval: str, count: int, timeout: float = 3.0
):
    key = (symbol.upper(), interval)
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        state = manager._subscriptions.get(key)
        if state and len(state.buffer) >= count:
            return
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"Timed out waiting for {count} candle(s) on {symbol}@{interval}")
        await asyncio.sleep(0.01)


def _build_bare_loop(symbols):
    loop = AutonomousTradingLoop.__new__(AutonomousTradingLoop)
    loop.logger = logging.getLogger("test-stream-watcher")
    loop.symbols = symbols
    loop.trade_interval = 60
    loop.stop_flag = False
    loop.trades_executed = 0
    loop._stream_last_candle_time = {}
    loop.orchestrator = MagicMock()
    return loop


@pytest.mark.asyncio
class TestCheckTrailingStopViaStream:
    async def test_processes_a_fresh_candle_and_closes_a_triggered_stop(self, monkeypatch):
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages([_kline_msg(1_000, 94.0)])
        )
        monkeypatch.setattr(
            "binance_trade_agent.core.market_streams.get_stream_manager", lambda **_kw: manager
        )

        loop = _build_bare_loop(["BTCUSDT"])
        risk_agent = loop.orchestrator.risk_agent
        risk_agent.update_all_trailing_stops = MagicMock(
            return_value={
                "BTCUSDT": {
                    "stop_triggered": True,
                    "side": "buy",
                    "entry_price": 100.0,
                    "current_stop": 95.0,
                    "current_price": 94.0,
                }
            }
        )
        risk_agent.close_trailing_stop = MagicMock(return_value={"pnl_pct": -0.06})
        loop.orchestrator.execution_agent.place_sell_order = MagicMock(
            return_value={"orderId": "1"}
        )

        await manager.subscribe("BTCUSDT", "1m")
        await _wait_for_candles(manager, "BTCUSDT", "1m", count=1)

        processed = await loop._check_trailing_stop_via_stream("BTCUSDT", "1m")

        assert processed is True
        risk_agent.update_all_trailing_stops.assert_called_once_with({"BTCUSDT": 94.0})
        loop.orchestrator.execution_agent.place_sell_order.assert_called_once()

        await manager.unsubscribe("BTCUSDT", "1m")

    async def test_does_not_reprocess_the_same_candle_twice(self, monkeypatch):
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages([_kline_msg(2_000, 100.0)])
        )
        monkeypatch.setattr(
            "binance_trade_agent.core.market_streams.get_stream_manager", lambda **_kw: manager
        )

        loop = _build_bare_loop(["ETHUSDT"])
        risk_agent = loop.orchestrator.risk_agent
        risk_agent.update_all_trailing_stops = MagicMock(
            return_value={
                "ETHUSDT": {"stop_triggered": False, "current_price": 100.0, "current_stop": 90.0}
            }
        )

        await manager.subscribe("ETHUSDT", "1m")
        await _wait_for_candles(manager, "ETHUSDT", "1m", count=1)

        first = await loop._check_trailing_stop_via_stream("ETHUSDT", "1m")
        second = await loop._check_trailing_stop_via_stream("ETHUSDT", "1m")

        assert first is True
        assert second is False
        risk_agent.update_all_trailing_stops.assert_called_once()

        await manager.unsubscribe("ETHUSDT", "1m")

    async def test_no_data_yet_is_a_safe_no_op(self, monkeypatch):
        manager = KlineStreamManager(stream_factory=_factory_from_messages([]))
        monkeypatch.setattr(
            "binance_trade_agent.core.market_streams.get_stream_manager", lambda **_kw: manager
        )

        loop = _build_bare_loop(["BTCUSDT"])
        processed = await loop._check_trailing_stop_via_stream("BTCUSDT", "1m")

        assert processed is False
        loop.orchestrator.risk_agent.update_all_trailing_stops.assert_not_called()

    async def test_ignores_a_candle_that_closed_before_the_position_was_registered(
        self, monkeypatch
    ):
        """
        A symbol's first tick after register_trailing_stop() must not
        evaluate whatever candle happens to be buffered if that candle
        opened before the position existed — that price action predates the
        entry and isn't a valid trailing-stop signal.
        """
        candle_open_ms = 10_000
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages([_kline_msg(candle_open_ms, 94.0)])
        )
        monkeypatch.setattr(
            "binance_trade_agent.core.market_streams.get_stream_manager", lambda **_kw: manager
        )

        loop = _build_bare_loop(["BTCUSDT"])
        risk_agent = loop.orchestrator.risk_agent

        await manager.subscribe("BTCUSDT", "1m")
        await _wait_for_candles(manager, "BTCUSDT", "1m", count=1)

        # Position registered *after* the buffered candle opened.
        processed = await loop._check_trailing_stop_via_stream(
            "BTCUSDT", "1m", registered_at_ms=candle_open_ms + 5_000
        )

        assert processed is False
        risk_agent.update_all_trailing_stops.assert_not_called()

        await manager.unsubscribe("BTCUSDT", "1m")

    async def test_processes_a_candle_that_opened_after_registration(self, monkeypatch):
        candle_open_ms = 10_000
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages([_kline_msg(candle_open_ms, 94.0)])
        )
        monkeypatch.setattr(
            "binance_trade_agent.core.market_streams.get_stream_manager", lambda **_kw: manager
        )

        loop = _build_bare_loop(["BTCUSDT"])
        risk_agent = loop.orchestrator.risk_agent
        risk_agent.update_all_trailing_stops = MagicMock(
            return_value={
                "BTCUSDT": {"stop_triggered": False, "current_price": 94.0, "current_stop": 90.0}
            }
        )

        await manager.subscribe("BTCUSDT", "1m")
        await _wait_for_candles(manager, "BTCUSDT", "1m", count=1)

        # Position registered *before* the buffered candle opened.
        processed = await loop._check_trailing_stop_via_stream(
            "BTCUSDT", "1m", registered_at_ms=candle_open_ms - 5_000
        )

        assert processed is True
        risk_agent.update_all_trailing_stops.assert_called_once_with({"BTCUSDT": 94.0})

        await manager.unsubscribe("BTCUSDT", "1m")


@pytest.mark.asyncio
class TestTrailingStopWatcherLifecycle:
    async def test_watcher_subscribes_only_its_own_symbols_and_unsubscribes_on_cancel(
        self, monkeypatch
    ):
        manager = KlineStreamManager(stream_factory=_factory_from_messages([]))
        monkeypatch.setattr(
            "binance_trade_agent.core.market_streams.get_stream_manager", lambda **_kw: manager
        )

        loop = _build_bare_loop(["BTCUSDT", "ETHUSDT"])
        loop.orchestrator.risk_agent.get_trailing_stop_info = MagicMock(
            return_value={"positions": {}, "active_stops": 0}
        )

        task = asyncio.create_task(
            loop._run_trailing_stop_watcher(interval="1m", check_every_seconds=0.05)
        )
        await asyncio.sleep(0.1)

        assert ("BTCUSDT", "1m") in manager._subscriptions
        assert ("ETHUSDT", "1m") in manager._subscriptions

        task.cancel()
        await task  # completes normally — cancellation is caught internally to run cleanup

        assert manager._subscriptions == {}

    async def test_watcher_passes_registered_at_from_the_position_through_to_the_check(
        self, monkeypatch
    ):
        manager = KlineStreamManager(stream_factory=_factory_from_messages([]))
        monkeypatch.setattr(
            "binance_trade_agent.core.market_streams.get_stream_manager", lambda **_kw: manager
        )

        loop = _build_bare_loop(["BTCUSDT"])
        loop.orchestrator.risk_agent.get_trailing_stop_info = MagicMock(
            return_value={
                "positions": {"BTCUSDT": {"registered_at": "2026-08-17T12:00:00"}},
                "active_stops": 1,
            }
        )
        seen_calls = []

        async def _fake_check(symbol, interval, registered_at_ms=None):
            seen_calls.append((symbol, interval, registered_at_ms))
            return False

        loop._check_trailing_stop_via_stream = _fake_check

        task = asyncio.create_task(
            loop._run_trailing_stop_watcher(interval="1m", check_every_seconds=0.05)
        )
        await asyncio.sleep(0.1)
        task.cancel()
        await task

        assert seen_calls
        symbol, interval, registered_at_ms = seen_calls[0]
        assert symbol == "BTCUSDT"
        from datetime import datetime

        expected_ms = int(datetime.fromisoformat("2026-08-17T12:00:00").timestamp() * 1000)
        assert registered_at_ms == expected_ms


@pytest.mark.asyncio
class TestRunWiresUpTheWatcher:
    async def test_run_starts_and_cleanly_cancels_the_watcher(self, monkeypatch):
        loop = _build_bare_loop(["BTCUSDT"])
        loop.duration_minutes = 0
        loop.stream_trailing_stop_watcher_enabled = True
        loop.orchestrator.execute_trading_workflow = AsyncMock(side_effect=Exception("n/a"))
        loop._update_trailing_stops = AsyncMock()
        loop._refresh_heartbeat = MagicMock()

        watcher_started = asyncio.Event()
        real_sleep = asyncio.sleep  # capture before patching, to yield real control below

        async def _fake_watcher():
            watcher_started.set()
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                raise

        monkeypatch.setattr(loop, "_run_trailing_stop_watcher", _fake_watcher)

        async def _stop_after_sleep(*_args, **_kwargs):
            # Give the scheduled watcher task a real chance to run before
            # this (mocked, otherwise-instant) sleep lets the main loop
            # finish its single cycle and start tearing the watcher down.
            await real_sleep(0)
            loop.stop_flag = True

        with patch("asyncio.sleep", side_effect=_stop_after_sleep):
            await loop.run()

        assert watcher_started.is_set()

    async def test_run_skips_the_watcher_when_disabled(self, monkeypatch):
        loop = _build_bare_loop(["BTCUSDT"])
        loop.duration_minutes = 0
        loop.stream_trailing_stop_watcher_enabled = False
        loop.orchestrator.execute_trading_workflow = AsyncMock(side_effect=Exception("n/a"))
        loop._update_trailing_stops = AsyncMock()
        loop._refresh_heartbeat = MagicMock()

        called = False

        async def _fake_watcher():
            nonlocal called
            called = True

        monkeypatch.setattr(loop, "_run_trailing_stop_watcher", _fake_watcher)

        async def _stop_after_sleep(*_args, **_kwargs):
            loop.stop_flag = True

        with patch("asyncio.sleep", side_effect=_stop_after_sleep):
            await loop.run()

        assert called is False
