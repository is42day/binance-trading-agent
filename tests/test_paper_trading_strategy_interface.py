"""
Regression coverage for PaperTradingLoop._process_symbol calling a strategy
interface it doesn't actually implement.

Only the "edge" strategy family (EdgeStrategy, SmartEntryStrategy,
CombinedEdgeStrategy, ...) implements generate_signal(symbol, ohlcv_data)
-> dict. Every other BaseStrategy subclass (CombinedStrategy, RSIStrategy,
MACDStrategy, BollingerStrategy, ...) — including "combined", the default
strategy selectable from the UI and the API — only implements the standard
analyze(market_data, symbol) -> StrategyResult contract. Calling
generate_signal() unconditionally meant every non-edge strategy raised
AttributeError on every single iteration, silently swallowed by
_process_symbol's broad except, and never produced a signal or a trade —
this was the actual root cause of "paper trading doesn't run or trigger
enough transactions."

Also covers a second bug found alongside it: _fetch_ohlcv's fixed
limit=100 starved CombinedStrategy's 200-period trend filter into
permanent "Insufficient data" HOLDs even once analyze() was being called
correctly.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from binance_trade_agent.core.paper_trading_loop import PaperTradingLoop
from binance_trade_agent.strategies.base_strategy import SignalType, StrategyResult

_SAMPLE_CANDLES = [
    {"timestamp": i, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1.0}
    for i in range(250)
]


def _build_bare_loop() -> PaperTradingLoop:
    loop = PaperTradingLoop.__new__(PaperTradingLoop)
    loop.symbols = ["BTCUSDT"]
    loop.strategy_name = "combined"
    loop.kline_interval = "5m"
    loop.position_size_pct = 0.25
    loop.data_client = MagicMock()
    loop.paper_engine = MagicMock()
    loop.paper_engine.portfolio.open_positions = {}
    return loop


class _AnalyzeOnlyStrategy:
    """Stands in for CombinedStrategy/RSIStrategy/etc: analyze() only, no generate_signal."""

    def __init__(self, result: StrategyResult, min_data: int = 200):
        self._result = result
        self._min_data = min_data
        self.analyze_calls = []

    def analyze(self, market_data, symbol=None):
        self.analyze_calls.append((market_data, symbol))
        return self._result

    def requires_minimum_data(self) -> int:
        return self._min_data


@pytest.mark.asyncio
async def test_process_symbol_falls_back_to_analyze_when_generate_signal_is_missing():
    loop = _build_bare_loop()
    loop.strategy = _AnalyzeOnlyStrategy(
        StrategyResult(signal=SignalType.BUY, confidence=0.8, metadata={})
    )
    loop._fetch_ohlcv = MagicMock(return_value=_SAMPLE_CANDLES)
    loop._calculate_position_size = MagicMock(return_value=1.0)
    loop.paper_engine.execute_paper_trade.return_value = {"success": True}

    await loop._process_symbol("BTCUSDT")

    assert len(loop.strategy.analyze_calls) == 1
    loop.paper_engine.execute_paper_trade.assert_called_once()
    call_kwargs = loop.paper_engine.execute_paper_trade.call_args.kwargs
    assert call_kwargs["side"] == "BUY"


@pytest.mark.asyncio
async def test_process_symbol_prefers_generate_signal_when_available():
    """Edge-family strategies keep their richer generate_signal() output untouched."""
    loop = _build_bare_loop()
    loop.strategy = MagicMock()
    loop.strategy.requires_minimum_data.return_value = 1
    loop.strategy.generate_signal.return_value = {"action": "HOLD", "confidence": 0}
    loop._fetch_ohlcv = MagicMock(return_value=_SAMPLE_CANDLES)

    await loop._process_symbol("BTCUSDT")

    loop.strategy.generate_signal.assert_called_once_with("BTCUSDT", _SAMPLE_CANDLES)


@pytest.mark.asyncio
async def test_fetch_limit_covers_the_strategys_minimum_data_requirement():
    """CombinedStrategy needs 200 candles for its trend filter; the old fixed
    limit=100 silently starved it into permanent 'Insufficient data' HOLDs."""
    loop = _build_bare_loop()
    loop.strategy = _AnalyzeOnlyStrategy(
        StrategyResult(signal=SignalType.HOLD, confidence=0.0, metadata={}), min_data=200
    )
    loop._fetch_ohlcv = MagicMock(return_value=_SAMPLE_CANDLES)

    await loop._process_symbol("BTCUSDT")

    loop._fetch_ohlcv.assert_called_once_with("BTCUSDT", interval="5m", limit=210)
