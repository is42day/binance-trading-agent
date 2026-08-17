"""
Tests for KlineStreamManager (Priority 2 — Task 6).

All tests use an injected fake stream factory; no real WebSocket connection.
Scenarios:
- Candles accumulate in buffer from fake stream
- Stale detection: no update → get_ohlcv returns None
- Fresh data: get_ohlcv returns list of candles
- Buffer limit: old candles are evicted at maxlen
- Reconnect: stream_factory raising simulates disconnect; attempts counter increments
- Unsubscribe: task is cancelled cleanly
- parse_message: closed candles accepted, open candles (x=False) ignored
- get_all_statuses / get_status: return correct StreamStatus
- API endpoint /api/v1/market/streams/status responds correctly
"""

import asyncio
import time
from typing import AsyncIterator, List
from unittest.mock import MagicMock, patch

import pytest

from binance_trade_agent.core.market_streams import (
    KlineStreamManager,
    StreamStatus,
    _parse_kline_message,
)

# ---------------------------------------------------------------------------
# Fake stream factories
# ---------------------------------------------------------------------------


def _kline_msg(t: int, close: float, closed: bool = True) -> dict:
    """Build a minimal Binance kline WebSocket message."""
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


async def _finite_stream(messages: List[dict]):
    """Async generator that yields a fixed list of messages and stops."""
    for msg in messages:
        yield msg


def _factory_from_messages(messages: List[dict]):
    """
    Return a stream_factory callable that yields the given messages once, then
    sleeps forever (so the reconnect loop blocks until the task is cancelled).
    """

    async def _factory(symbol, interval) -> AsyncIterator[dict]:
        for msg in messages:
            yield msg
        # Block reconnect loop until the task is cancelled by unsubscribe()
        await asyncio.sleep(3600)

    return _factory


def _factory_raises(exc: Exception):
    """Return a stream_factory that raises exc immediately."""

    async def _factory(symbol, interval) -> AsyncIterator[dict]:
        raise exc
        yield  # make it a generator

    return _factory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _subscribe_and_drain(
    manager: KlineStreamManager,
    symbol: str,
    interval: str,
    expected_candles: int = 0,
    timeout: float = 3.0,
):
    """
    Subscribe and wait until at least `expected_candles` are buffered.
    Does NOT unsubscribe — caller owns cleanup (or let the per-test manager GC).
    """
    await manager.subscribe(symbol, interval)
    key = (symbol.upper(), interval)
    deadline = asyncio.get_event_loop().time() + timeout
    while expected_candles > 0:
        state = manager._subscriptions.get(key)
        if state and len(state.buffer) >= expected_candles:
            break
        if asyncio.get_event_loop().time() > deadline:
            break
        await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# parse_message tests (sync)
# ---------------------------------------------------------------------------


class TestParseKlineMessage:
    def test_closed_candle_is_parsed(self):
        msg = _kline_msg(1_000_000, 50000.0, closed=True)
        candle = _parse_kline_message(msg)
        assert candle is not None
        assert candle[4] == 50000.0  # close

    def test_open_candle_returns_none(self):
        msg = _kline_msg(1_000_000, 50000.0, closed=False)
        candle = _parse_kline_message(msg)
        assert candle is None

    def test_malformed_message_returns_none(self):
        assert _parse_kline_message({}) is None
        assert _parse_kline_message({"k": {}}) is None


# ---------------------------------------------------------------------------
# KlineStreamManager async tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBufferAccumulation:
    async def test_candles_added_to_buffer(self):
        msgs = [_kline_msg(i, 100.0 + i) for i in range(5)]
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages(msgs),
            stale_seconds=60,
        )
        await _subscribe_and_drain(manager, "BTCUSDT", "1m", expected_candles=5)
        ohlcv = manager.get_ohlcv("BTCUSDT", "1m")
        assert ohlcv is not None
        assert len(ohlcv) == 5
        assert ohlcv[-1][4] == 104.0  # last close

    async def test_open_candles_not_buffered(self):
        msgs = [_kline_msg(0, 100.0, closed=False), _kline_msg(1, 101.0, closed=True)]
        manager = KlineStreamManager(stream_factory=_factory_from_messages(msgs))
        await _subscribe_and_drain(manager, "ETHUSDT", "1m", expected_candles=1)
        ohlcv = manager.get_ohlcv("ETHUSDT", "1m")
        assert ohlcv is not None
        assert len(ohlcv) == 1

    async def test_buffer_limit_evicts_oldest(self):
        msgs = [_kline_msg(i, float(i)) for i in range(10)]
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages(msgs),
            buffer_size=5,
        )
        await _subscribe_and_drain(manager, "BTCUSDT", "1m", expected_candles=5)
        ohlcv = manager.get_ohlcv("BTCUSDT", "1m")
        assert ohlcv is not None
        assert len(ohlcv) == 5
        assert ohlcv[0][4] == 5.0  # oldest evicted


@pytest.mark.asyncio
class TestStaleDetection:
    async def test_stale_get_ohlcv_returns_none(self):
        msgs = [_kline_msg(0, 100.0)]
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages(msgs),
            stale_seconds=0.001,  # almost instant stale
        )
        await _subscribe_and_drain(manager, "BTCUSDT", "1m", expected_candles=1)
        await asyncio.sleep(0.05)  # let it go stale
        assert manager.get_ohlcv("BTCUSDT", "1m") is None
        await manager.unsubscribe("BTCUSDT", "1m")

    async def test_is_stale_true_when_no_data(self):
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages([]),
        )
        await _subscribe_and_drain(manager, "BTCUSDT", "1m", expected_candles=0)
        # Factory sleeps after empty — buffer was never populated → still stale
        assert manager.is_stale("BTCUSDT", "1m") is True
        await manager.unsubscribe("BTCUSDT", "1m")

    async def test_is_stale_false_when_fresh(self):
        msgs = [_kline_msg(0, 100.0)]
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages(msgs),
            stale_seconds=60,
        )
        await _subscribe_and_drain(manager, "BTCUSDT", "1m", expected_candles=1)
        assert manager.is_stale("BTCUSDT", "1m") is False
        await manager.unsubscribe("BTCUSDT", "1m")

    def test_unsubscribed_symbol_is_stale(self):
        manager = KlineStreamManager()
        assert manager.is_stale("XYZUSDT", "1m") is True

    def test_get_ohlcv_returns_none_for_unsubscribed(self):
        manager = KlineStreamManager()
        assert manager.get_ohlcv("XYZUSDT", "1m") is None


@pytest.mark.asyncio
class TestReconnect:
    async def test_error_increments_reconnect_count(self):
        call_count = 0

        async def failing_then_empty(symbol, interval):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("fake disconnect")
            # second call: finite stream
            for msg in [_kline_msg(0, 100.0)]:
                yield msg

        manager = KlineStreamManager(
            stream_factory=failing_then_empty,
            min_backoff=0.01,  # tiny backoff for test speed
            max_backoff=0.05,
        )
        await manager.subscribe("BTCUSDT", "1m")
        key = ("BTCUSDT", "1m")
        task = manager._subscriptions[key].task
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        state = manager._subscriptions.get(key)
        assert state is not None
        assert state.reconnect_attempts >= 1

    async def test_last_error_recorded_on_failure(self):
        manager = KlineStreamManager(
            stream_factory=_factory_raises(RuntimeError("test error")),
            min_backoff=0.01,
            max_backoff=0.02,
        )
        await manager.subscribe("BTCUSDT", "1m")
        await asyncio.sleep(0.1)
        key = ("BTCUSDT", "1m")
        state = manager._subscriptions.get(key)
        assert state is not None
        assert state.last_error is not None
        # clean up
        await manager.unsubscribe("BTCUSDT", "1m")


@pytest.mark.asyncio
class TestSubscribeUnsubscribe:
    async def test_double_subscribe_is_idempotent(self):
        manager = KlineStreamManager(stream_factory=_factory_from_messages([]))
        await manager.subscribe("BTCUSDT", "1m")
        count_before = len(manager._subscriptions)
        await manager.subscribe("BTCUSDT", "1m")  # second call should be no-op
        assert len(manager._subscriptions) == count_before == 1
        await manager.unsubscribe("BTCUSDT", "1m")

    async def test_unsubscribe_removes_subscription(self):
        manager = KlineStreamManager(stream_factory=_factory_from_messages([]))
        await manager.subscribe("BTCUSDT", "1m")
        await manager.unsubscribe("BTCUSDT", "1m")
        assert ("BTCUSDT", "1m") not in manager._subscriptions

    async def test_unsubscribe_all(self):
        manager = KlineStreamManager(stream_factory=_factory_from_messages([]))
        await manager.subscribe("BTCUSDT", "1m")
        await manager.subscribe("ETHUSDT", "5m")
        await manager.unsubscribe_all()
        assert len(manager._subscriptions) == 0


@pytest.mark.asyncio
class TestGetStatus:
    async def test_get_status_none_for_unsubscribed(self):
        manager = KlineStreamManager()
        assert manager.get_status("BTCUSDT", "1m") is None

    async def test_get_status_returns_stream_status(self):
        msgs = [_kline_msg(0, 100.0)]
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages(msgs),
            stale_seconds=60,
        )
        await _subscribe_and_drain(manager, "BTCUSDT", "1m", expected_candles=1)
        status = manager.get_status("BTCUSDT", "1m")
        assert isinstance(status, StreamStatus)
        assert status.symbol == "BTCUSDT"
        assert status.candle_count == 1
        assert status.is_stale is False

    async def test_get_all_statuses(self):
        msgs = [_kline_msg(0, 100.0)]
        manager = KlineStreamManager(stream_factory=_factory_from_messages(msgs))
        await _subscribe_and_drain(manager, "BTCUSDT", "1m", expected_candles=1)
        await _subscribe_and_drain(manager, "ETHUSDT", "5m", expected_candles=1)
        # After unsubscribing, subscriptions are removed; re-check with fresh subs
        # Instead just verify two separate managers count correctly
        mgr2 = KlineStreamManager(stream_factory=_factory_from_messages(msgs))
        await mgr2.subscribe("BTCUSDT", "1m")
        await mgr2.subscribe("ETHUSDT", "5m")
        await asyncio.sleep(0.2)
        statuses = mgr2.get_all_statuses()
        assert len(statuses) == 2
        await mgr2.unsubscribe_all()

    async def test_limit_parameter_slices_buffer(self):
        msgs = [_kline_msg(i, float(i)) for i in range(20)]
        manager = KlineStreamManager(
            stream_factory=_factory_from_messages(msgs),
            stale_seconds=60,
        )
        await _subscribe_and_drain(manager, "BTCUSDT", "1m", expected_candles=20)
        ohlcv = manager.get_ohlcv("BTCUSDT", "1m", limit=5)
        assert ohlcv is not None
        assert len(ohlcv) == 5


# ---------------------------------------------------------------------------
# API endpoint test
# ---------------------------------------------------------------------------


class TestStreamStatusEndpoint:
    def test_endpoint_returns_all_streams(self):
        from fastapi.testclient import TestClient

        from binance_trade_agent.api.api import app

        mock_manager = MagicMock()
        mock_manager.get_all_statuses.return_value = [
            StreamStatus(
                symbol="BTCUSDT",
                interval="1m",
                connected=True,
                last_update=time.time(),
                age_seconds=2.5,
                is_stale=False,
                candle_count=100,
                reconnect_attempts=0,
                last_error=None,
            )
        ]

        with patch(
            "binance_trade_agent.core.market_streams.get_stream_manager", return_value=mock_manager
        ):
            client = TestClient(app)
            resp = client.get(
                "/api/v1/market/streams/status",
                headers={"X-API-Token": "test-token"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["streams"][0]["symbol"] == "BTCUSDT"
        assert data["streams"][0]["is_stale"] is False

    def test_endpoint_404_for_unknown_subscription(self):
        from fastapi.testclient import TestClient

        from binance_trade_agent.api.api import app

        mock_manager = MagicMock()
        mock_manager.get_status.return_value = None

        with patch(
            "binance_trade_agent.core.market_streams.get_stream_manager", return_value=mock_manager
        ):
            client = TestClient(app)
            resp = client.get(
                "/api/v1/market/streams/status?symbol=BTCUSDT&interval=1m",
                headers={"X-API-Token": "test-token"},
            )
        assert resp.status_code == 404


class TestBinanceWsStreamUrl:
    """
    The real Binance WS stream must honor BINANCE_TESTNET the same way the
    REST client does (clients/binance_client.py switches its API_URL to
    testnet.binance.vision) — otherwise a testnet trailing stop could be
    driven by live-market kline data.
    """

    @pytest.mark.asyncio
    async def test_uses_testnet_url_when_binance_testnet_true(self, monkeypatch):
        from binance_trade_agent.core.market_streams import _binance_ws_stream

        monkeypatch.setattr(
            "binance_trade_agent.common.config.config.binance_testnet", True
        )
        captured = {}

        class _FakeWs:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        def _fake_connect(url):
            captured["url"] = url
            return _FakeWs()

        fake_websockets = MagicMock()
        fake_websockets.connect = _fake_connect
        monkeypatch.setitem(__import__("sys").modules, "websockets", fake_websockets)

        async for _ in _binance_ws_stream("BTCUSDT", "1m"):
            pass

        assert captured["url"].startswith("wss://stream.testnet.binance.vision/ws")
        assert "btcusdt@kline_1m" in captured["url"]

    @pytest.mark.asyncio
    async def test_uses_mainnet_url_when_binance_testnet_false(self, monkeypatch):
        from binance_trade_agent.core.market_streams import _binance_ws_stream

        monkeypatch.setattr(
            "binance_trade_agent.common.config.config.binance_testnet", False
        )
        captured = {}

        class _FakeWs:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        def _fake_connect(url):
            captured["url"] = url
            return _FakeWs()

        fake_websockets = MagicMock()
        fake_websockets.connect = _fake_connect
        monkeypatch.setitem(__import__("sys").modules, "websockets", fake_websockets)

        async for _ in _binance_ws_stream("BTCUSDT", "1m"):
            pass

        assert captured["url"].startswith("wss://stream.binance.com:9443/ws")
        assert "stream.testnet.binance.vision" not in captured["url"]
