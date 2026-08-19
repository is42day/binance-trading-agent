"""
Regression coverage for PaperTradingLoop's configurable kline_interval.

_process_symbol previously always fetched 1h candles regardless of how
often the loop polled (trade_interval_seconds) — re-evaluating the same
signal on unchanged hourly data made paper trading look idle over any
observation window shorter than an hour. kline_interval decouples "how
often we check" from "how often new data actually exists," and defaults
to "1h" to preserve prior behavior.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from binance_trade_agent.core.paper_trading_loop import PaperTradingLoop


def _build_bare_loop(kline_interval: str = "1h") -> PaperTradingLoop:
    loop = PaperTradingLoop.__new__(PaperTradingLoop)
    loop.symbols = ["BTCUSDT"]
    loop.strategy_name = "combined_edge"
    loop.kline_interval = kline_interval
    loop.position_size_pct = 0.25
    loop.data_client = MagicMock()
    loop.strategy = MagicMock()
    loop.paper_engine = MagicMock()
    loop.paper_engine.portfolio.open_positions = {}
    return loop


_SAMPLE_CANDLE = [
    {"timestamp": 1, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1.0}
]


@pytest.mark.asyncio
async def test_process_symbol_fetches_with_the_configured_kline_interval():
    loop = _build_bare_loop(kline_interval="5m")
    loop.strategy.generate_signal.return_value = {"action": "HOLD", "confidence": 0}
    loop._fetch_ohlcv = MagicMock(return_value=_SAMPLE_CANDLE)

    await loop._process_symbol("BTCUSDT")

    loop._fetch_ohlcv.assert_called_once_with("BTCUSDT", interval="5m")


@pytest.mark.asyncio
async def test_process_symbol_defaults_to_1h_kline_interval():
    loop = _build_bare_loop()  # default kline_interval="1h"
    loop.strategy.generate_signal.return_value = {"action": "HOLD", "confidence": 0}
    loop._fetch_ohlcv = MagicMock(return_value=_SAMPLE_CANDLE)

    await loop._process_symbol("BTCUSDT")

    loop._fetch_ohlcv.assert_called_once_with("BTCUSDT", interval="1h")
