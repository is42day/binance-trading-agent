"""
WebSocket Kline Stream Manager — binance_trade_agent/core/market_streams.py

Design:
- Each subscription is a (symbol, interval) pair.
- A background asyncio task per subscription reads messages from a source
  (real Binance WS or an injected async generator for testing).
- Candles are stored in a bounded deque (OHLCV tuples).
- Stale detection: if the last update is older than STREAM_STALE_SECONDS the
  buffer is considered stale and callers must fall back to REST.
- Reconnect: exponential backoff with jitter, capped at MAX_BACKOFF_SECONDS.
- Thread-safe: all mutations via asyncio.Lock inside the event loop; status
  reads return copies.

Usage (production):
    manager = KlineStreamManager()
    await manager.subscribe("BTCUSDT", "1m")
    ohlcv = manager.get_ohlcv("BTCUSDT", "1m")   # returns list or None if stale

Usage (testing — inject a fake message source):
    async def fake_source(symbol, interval):
        for msg in messages:
            yield msg
    manager = KlineStreamManager(stream_factory=fake_source)
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via constructor kwargs or env)
# ---------------------------------------------------------------------------
DEFAULT_STALE_SECONDS: float = 60.0  # Data older than this = stale
DEFAULT_BUFFER_SIZE: int = 500  # Max candles per (symbol, interval)
DEFAULT_MIN_BACKOFF: float = 1.0  # First reconnect delay
DEFAULT_MAX_BACKOFF: float = 60.0  # Cap on reconnect delay
DEFAULT_BACKOFF_FACTOR: float = 2.0  # Exponential multiplier
DEFAULT_JITTER_RANGE: float = 0.25  # ± fraction of current backoff


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

# OHLCV as plain tuple: (open_time_ms, open, high, low, close, volume)
OHLCVCandle = Tuple[int, float, float, float, float, float]


@dataclass
class StreamStatus:
    symbol: str
    interval: str
    connected: bool
    last_update: Optional[float]  # epoch seconds; None if never received
    age_seconds: Optional[float]  # seconds since last_update; None if never
    is_stale: bool
    candle_count: int
    reconnect_attempts: int
    last_error: Optional[str]


@dataclass
class _SubscriptionState:
    symbol: str
    interval: str
    buffer: deque  # deque[OHLCVCandle]
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    connected: bool = False
    last_update: Optional[float] = None
    reconnect_attempts: int = 0
    last_error: Optional[str] = None
    task: Optional[asyncio.Task] = None
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event)


# ---------------------------------------------------------------------------
# Default stream factory (production — connects to Binance WebSocket)
# ---------------------------------------------------------------------------


async def _binance_ws_stream(symbol: str, interval: str) -> AsyncIterator[dict]:
    """
    Real Binance WebSocket kline stream.

    Imports websockets lazily so the module can be imported without websockets
    installed in unit-test environments.
    """
    try:
        import websockets  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "websockets package is required for live WebSocket streams. "
            "Install with: pip install websockets"
        ) from exc
    url = f"wss://stream.binance.com:9443/ws/" f"{symbol.lower()}@kline_{interval}"
    async with websockets.connect(url) as ws:
        async for raw in ws:
            import json

            msg = json.loads(raw)
            yield msg


def _parse_kline_message(msg: dict) -> Optional[OHLCVCandle]:
    """
    Parse a Binance kline WebSocket message.

    Expected shape:
        {"e": "kline", "k": {"t": ms, "o": "...", "h": "...", "l": "...",
                              "c": "...", "v": "...", "x": bool, ...}}

    Returns an OHLCVCandle only when the candle is closed (x=True).
    """
    try:
        k = msg.get("k") or msg.get("kline") or msg
        is_closed = bool(k.get("x", True))  # default True makes fakes simpler
        return (
            (
                int(k["t"]),
                float(k["o"]),
                float(k["h"]),
                float(k["l"]),
                float(k["c"]),
                float(k["v"]),
            )
            if is_closed
            else None
        )
    except (KeyError, TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# KlineStreamManager
# ---------------------------------------------------------------------------


class KlineStreamManager:
    """
    Manages persistent WebSocket kline subscriptions.

    Args:
        stale_seconds:    Age threshold in seconds before a buffer is stale.
        buffer_size:      Max candles kept per subscription.
        min_backoff:      Initial reconnect delay in seconds.
        max_backoff:      Cap on reconnect delay in seconds.
        backoff_factor:   Exponential multiplier per failure.
        stream_factory:   Async callable (symbol, interval) → AsyncIterator[dict].
                          Defaults to real Binance WS.  Inject a fake for testing.
        parse_message:    Callable msg→OHLCVCandle|None.  Defaults to Binance format.
    """

    def __init__(
        self,
        *,
        stale_seconds: float = DEFAULT_STALE_SECONDS,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        min_backoff: float = DEFAULT_MIN_BACKOFF,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        stream_factory: Optional[Callable] = None,
        parse_message: Optional[Callable] = None,
    ):
        self._stale_seconds = stale_seconds
        self._buffer_size = buffer_size
        self._min_backoff = min_backoff
        self._max_backoff = max_backoff
        self._backoff_factor = backoff_factor
        self._stream_factory = stream_factory or _binance_ws_stream
        self._parse_message = parse_message or _parse_kline_message

        # key: (symbol.upper(), interval)
        self._subscriptions: Dict[Tuple[str, str], _SubscriptionState] = {}
        self._global_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def subscribe(self, symbol: str, interval: str) -> None:
        """Start streaming for (symbol, interval) if not already running."""
        key = (symbol.upper(), interval)
        async with self._global_lock:
            if key in self._subscriptions:
                return  # already subscribed
            state = _SubscriptionState(
                symbol=symbol.upper(),
                interval=interval,
                buffer=deque(maxlen=self._buffer_size),
            )
            self._subscriptions[key] = state
        state.task = asyncio.create_task(
            self._run_subscription(state),
            name=f"kline-{symbol}-{interval}",
        )
        logger.info("Subscribed to %s@kline_%s", symbol, interval)

    async def unsubscribe(self, symbol: str, interval: str) -> None:
        """Stop the stream for (symbol, interval)."""
        key = (symbol.upper(), interval)
        async with self._global_lock:
            state = self._subscriptions.pop(key, None)
        if state:
            state._stop_event.set()
            if state.task and not state.task.done():
                state.task.cancel()
                try:
                    await state.task
                except asyncio.CancelledError:
                    pass
            logger.info("Unsubscribed from %s@kline_%s", symbol, interval)

    async def unsubscribe_all(self) -> None:
        """Tear down all subscriptions."""
        keys = list(self._subscriptions.keys())
        for sym, intv in keys:
            await self.unsubscribe(sym, intv)

    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: Optional[int] = None,
    ) -> Optional[List[OHLCVCandle]]:
        """
        Return buffered candles for (symbol, interval).

        Returns None if the subscription does not exist, has never received data,
        or the last update is older than stale_seconds (fail-closed).
        """
        key = (symbol.upper(), interval)
        state = self._subscriptions.get(key)
        if state is None or state.last_update is None:
            return None
        if self._is_stale(state):
            logger.warning(
                "Stream %s@%s is stale (%.1fs); failing closed",
                symbol,
                interval,
                time.time() - state.last_update,
            )
            return None
        candles = list(state.buffer)
        if limit:
            candles = candles[-limit:]
        return candles

    def is_stale(self, symbol: str, interval: str) -> bool:
        """True if data is missing or stale."""
        key = (symbol.upper(), interval)
        state = self._subscriptions.get(key)
        if state is None or state.last_update is None:
            return True
        return self._is_stale(state)

    def get_status(self, symbol: str, interval: str) -> Optional[StreamStatus]:
        """Return health info for a single subscription."""
        key = (symbol.upper(), interval)
        state = self._subscriptions.get(key)
        if state is None:
            return None
        return self._make_status(state)

    def get_all_statuses(self) -> List[StreamStatus]:
        """Return health info for all subscriptions."""
        return [self._make_status(s) for s in self._subscriptions.values()]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_stale(self, state: _SubscriptionState) -> bool:
        if state.last_update is None:
            return True
        return (time.time() - state.last_update) > self._stale_seconds

    def _make_status(self, state: _SubscriptionState) -> StreamStatus:
        now = time.time()
        age = (now - state.last_update) if state.last_update is not None else None
        return StreamStatus(
            symbol=state.symbol,
            interval=state.interval,
            connected=state.connected,
            last_update=state.last_update,
            age_seconds=age,
            is_stale=self._is_stale(state),
            candle_count=len(state.buffer),
            reconnect_attempts=state.reconnect_attempts,
            last_error=state.last_error,
        )

    async def _run_subscription(self, state: _SubscriptionState) -> None:
        """Main reconnect loop for a single subscription."""
        backoff = self._min_backoff

        while not state._stop_event.is_set():
            try:
                state.connected = False
                logger.debug(
                    "Connecting to stream %s@kline_%s (attempt %d)",
                    state.symbol,
                    state.interval,
                    state.reconnect_attempts + 1,
                )
                async for msg in self._stream_factory(state.symbol, state.interval):
                    if state._stop_event.is_set():
                        return

                    candle = self._parse_message(msg)
                    if candle is not None:
                        async with state.lock:
                            state.buffer.append(candle)
                            state.last_update = time.time()
                        state.connected = True
                        backoff = self._min_backoff  # reset on success

            except asyncio.CancelledError:
                return
            except Exception as exc:
                state.last_error = str(exc)
                state.reconnect_attempts += 1
                state.connected = False
                logger.warning(
                    "Stream %s@kline_%s error (attempt %d): %s — retrying in %.1fs",
                    state.symbol,
                    state.interval,
                    state.reconnect_attempts,
                    exc,
                    backoff,
                )

            if state._stop_event.is_set():
                return

            # Exponential backoff with jitter
            jitter = backoff * DEFAULT_JITTER_RANGE * (random.random() * 2 - 1)
            await asyncio.sleep(max(0, backoff + jitter))
            backoff = min(backoff * self._backoff_factor, self._max_backoff)


# ---------------------------------------------------------------------------
# Module-level singleton (lazy-initialised; replaces in tests via monkeypatch)
# ---------------------------------------------------------------------------

_manager: Optional[KlineStreamManager] = None


def get_stream_manager(**kwargs) -> KlineStreamManager:
    """Return the module-level singleton, creating it on first call."""
    global _manager
    if _manager is None:
        _manager = KlineStreamManager(**kwargs)
    return _manager
