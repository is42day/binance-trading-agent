"""
Tests for AdaptiveCoreMicroStrategy (Task 5).

Scenarios covered:
- Missing gate file → HOLD (gate_missing)
- Stale gate → HOLD (gate_stale)
- Gate fail for symbol → HOLD (negative_daily_eur / drawdown_exceeded)
- Gate pass but HTF trend negative for BTC/ETH → HOLD (htf_trend_negative)
- Insufficient HTF data → HOLD (insufficient_htf_data)
- Gate pass + trend positive → BUY/SELL/HOLD from RSI
- Non-core symbol (e.g. SOLUSDT) skips trend gate
- Decision journal records are written (or skipped when record_decisions=False)
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from binance_trade_agent.core.decision_journal import DecisionJournal
from binance_trade_agent.core.strategy_validation_gate import ValidationGate
from binance_trade_agent.strategies.adaptive_core_micro import AdaptiveCoreMicroStrategy
from binance_trade_agent.strategies.base_strategy import SignalType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def gate_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _write_gate(directory: Path, symbols: dict, ttl: int = 86400) -> ValidationGate:
    artifact = {
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ttl_seconds": ttl,
        "gate_strategy": "micro_grid",
        "max_drawdown_threshold_pct": 10.0,
        "assumptions": {},
        "symbols": symbols,
        "overall_pass": all(s.get("gate_pass") for s in symbols.values()),
    }
    p = directory / "latest.json"
    p.write_text(json.dumps(artifact), encoding="utf-8")
    return ValidationGate(str(p))


def _pass_symbol(daily_eur=5.0, max_dd=2.0):
    return {
        "gate_pass": True,
        "gate_reason": "positive_after_fees",
        "strategy": "micro_grid",
        "daily_eur": daily_eur,
        "max_drawdown_pct": max_dd,
        "trades": 40,
        "win_rate": 0.62,
    }


def _fail_symbol(reason="negative_daily_eur"):
    return {
        "gate_pass": False,
        "gate_reason": reason,
        "strategy": "micro_grid",
        "daily_eur": -1.0,
        "max_drawdown_pct": 5.0,
        "trades": 10,
        "win_rate": 0.4,
    }


def _null_journal():
    """A DecisionJournal that does nothing."""
    journal = MagicMock(spec=DecisionJournal)
    journal.record.return_value = "test-uuid"
    return journal


# ---------------------------------------------------------------------------
# OHLCV helpers
# ---------------------------------------------------------------------------


def _candles(closes: List[float]) -> List[list]:
    """Build minimal OHLCV candles from a list of close prices."""
    return [[i, c - 1, c + 1, c - 2, c, 1000] for i, c in enumerate(closes)]


def _trend_positive_candles(n: int = 60, start: float = 100.0) -> List[list]:
    """60 candles with steadily rising price (current > EMA50)."""
    closes = [start + i * 0.5 for i in range(n)]
    return _candles(closes)


def _trend_negative_candles(n: int = 60, start: float = 130.0) -> List[list]:
    """60 candles with steadily falling price (current < EMA50)."""
    closes = [start - i * 0.5 for i in range(n)]
    return _candles(closes)


def _rsi_oversold_candles() -> List[list]:
    """Candles whose RSI < 32 to trigger BUY."""
    # 5 up, then 15 consecutive drops
    closes = [100.0 + i for i in range(5)] + [105.0 - i * 3 for i in range(20)]
    return _candles(closes)


def _rsi_overbought_candles() -> List[list]:
    """Candles whose RSI > 68 to trigger SELL."""
    closes = [100.0] + [100.0 + i * 3 for i in range(24)]
    return _candles(closes)


def _neutral_candles() -> List[list]:
    """25 flat candles → RSI ~50 → HOLD."""
    import math

    closes = [100.0 + math.sin(i * 0.4) for i in range(25)]
    return _candles(closes)


# ---------------------------------------------------------------------------
# Tests: Micro gate blocks
# ---------------------------------------------------------------------------


class TestMicroGateBlocks:
    def test_missing_gate_returns_hold(self, gate_dir):
        gate = ValidationGate(str(gate_dir / "nonexistent.json"))
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        result = strat.analyze(_trend_positive_candles(), "BTCUSDT")
        assert result.signal == SignalType.HOLD
        assert result.metadata["component"] == "micro_gate"
        assert result.metadata["hold_reason"] == "gate_missing"

    def test_stale_gate_returns_hold(self, gate_dir):
        from datetime import timedelta

        old_time = (datetime.now(tz=timezone.utc) - timedelta(hours=3)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        artifact = {
            "generated_at": old_time,
            "ttl_seconds": 3600,
            "gate_strategy": "micro_grid",
            "max_drawdown_threshold_pct": 10.0,
            "assumptions": {},
            "symbols": {"BTCUSDT": _pass_symbol()},
            "overall_pass": True,
        }
        p = gate_dir / "stale.json"
        p.write_text(json.dumps(artifact), encoding="utf-8")
        gate = ValidationGate(str(p))
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        result = strat.analyze(_trend_positive_candles(), "BTCUSDT")
        assert result.signal == SignalType.HOLD
        assert result.metadata["hold_reason"] == "gate_stale"

    def test_symbol_not_in_gate_returns_hold(self, gate_dir):
        gate = _write_gate(gate_dir, {"ETHUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        result = strat.analyze(_trend_positive_candles(), "BTCUSDT")
        assert result.signal == SignalType.HOLD
        assert result.metadata["hold_reason"] == "symbol_not_in_gate"

    def test_negative_gate_returns_hold(self, gate_dir):
        gate = _write_gate(gate_dir, {"BTCUSDT": _fail_symbol("negative_daily_eur")})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        result = strat.analyze(_trend_positive_candles(), "BTCUSDT")
        assert result.signal == SignalType.HOLD
        assert result.metadata["hold_reason"] == "negative_daily_eur"

    def test_drawdown_gate_returns_hold(self, gate_dir):
        gate = _write_gate(gate_dir, {"BTCUSDT": _fail_symbol("drawdown_exceeded")})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        result = strat.analyze(_trend_positive_candles(), "BTCUSDT")
        assert result.signal == SignalType.HOLD
        assert result.metadata["hold_reason"] == "drawdown_exceeded"


# ---------------------------------------------------------------------------
# Tests: Core trend gate blocks
# ---------------------------------------------------------------------------


class TestCoreTrendGateBlocks:
    def test_negative_htf_trend_returns_hold(self, gate_dir):
        gate = _write_gate(gate_dir, {"BTCUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        result = strat.analyze(
            _rsi_oversold_candles(), "BTCUSDT", htf_ohlcv_data=_trend_negative_candles()
        )
        assert result.signal == SignalType.HOLD
        assert result.metadata["component"] == "core_gate"
        assert result.metadata["hold_reason"] == "htf_trend_negative"

    def test_insufficient_htf_data_returns_hold(self, gate_dir):
        gate = _write_gate(gate_dir, {"BTCUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        # Only 10 candles — not enough for EMA50
        tiny = _candles([100.0 + i for i in range(10)])
        result = strat.analyze(_rsi_oversold_candles(), "BTCUSDT", htf_ohlcv_data=tiny)
        assert result.signal == SignalType.HOLD
        assert result.metadata["hold_reason"] == "insufficient_htf_data"


# ---------------------------------------------------------------------------
# Tests: Both gates cleared — signal generation
# ---------------------------------------------------------------------------


class TestBothGatesCleared:
    def test_oversold_rsi_produces_buy(self, gate_dir):
        gate = _write_gate(gate_dir, {"BTCUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        result = strat.analyze(
            _rsi_oversold_candles(), "BTCUSDT", htf_ohlcv_data=_trend_positive_candles()
        )
        assert result.signal == SignalType.BUY
        assert result.confidence > 0
        assert result.metadata["component"] == "adaptive_core_micro"
        assert result.metadata["micro_gate"]["cleared"] is True
        assert result.metadata["core_gate"]["cleared"] is True

    def test_overbought_rsi_produces_sell(self, gate_dir):
        gate = _write_gate(gate_dir, {"BTCUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        result = strat.analyze(
            _rsi_overbought_candles(), "BTCUSDT", htf_ohlcv_data=_trend_positive_candles()
        )
        assert result.signal == SignalType.SELL

    def test_neutral_rsi_produces_hold(self, gate_dir):
        gate = _write_gate(gate_dir, {"BTCUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        # Candles too short for RSI computation → HOLD
        short = _candles([100.0 + i for i in range(10)])
        result = strat.analyze(short, "BTCUSDT", htf_ohlcv_data=_trend_positive_candles())
        assert result.signal == SignalType.HOLD


# ---------------------------------------------------------------------------
# Tests: Non-core symbol skips trend gate
# ---------------------------------------------------------------------------


class TestNonCoreSymbol:
    def test_sol_skips_trend_gate(self, gate_dir):
        gate = _write_gate(gate_dir, {"SOLUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=_null_journal())
        # Deliberately pass trend-negative data — should NOT block SOLUSDT
        result = strat.analyze(
            _rsi_oversold_candles(), "SOLUSDT", htf_ohlcv_data=_trend_negative_candles()
        )
        # Gate cleared (SOLUSDT not in core symbols) so signal from RSI
        assert result.metadata["core_gate"]["cleared"] is True
        assert result.signal == SignalType.BUY

    def test_custom_core_symbols_respected(self, gate_dir):
        gate = _write_gate(gate_dir, {"SOLUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(
            gate=gate,
            journal=_null_journal(),
            parameters={"core_symbols": ["SOLUSDT"]},
        )
        # SOLUSDT is now in core symbols, negative HTF should block
        result = strat.analyze(
            _rsi_oversold_candles(), "SOLUSDT", htf_ohlcv_data=_trend_negative_candles()
        )
        assert result.signal == SignalType.HOLD
        assert result.metadata["hold_reason"] == "htf_trend_negative"


# ---------------------------------------------------------------------------
# Tests: Decision journal integration
# ---------------------------------------------------------------------------


class TestDecisionJournalIntegration:
    def test_journal_record_called_on_hold(self, gate_dir):
        journal = _null_journal()
        gate = ValidationGate(str(gate_dir / "missing.json"))
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=journal)
        strat.analyze(_trend_positive_candles(), "BTCUSDT")
        journal.record.assert_called_once()
        call_kwargs = journal.record.call_args.kwargs
        assert call_kwargs["signal"] == "HOLD"
        assert call_kwargs["symbol"] == "BTCUSDT"

    def test_journal_record_called_on_buy(self, gate_dir):
        journal = _null_journal()
        gate = _write_gate(gate_dir, {"BTCUSDT": _pass_symbol()})
        strat = AdaptiveCoreMicroStrategy(gate=gate, journal=journal)
        strat.analyze(_rsi_oversold_candles(), "BTCUSDT", htf_ohlcv_data=_trend_positive_candles())
        journal.record.assert_called_once()

    def test_journal_skipped_when_disabled(self, gate_dir):
        journal = _null_journal()
        gate = ValidationGate(str(gate_dir / "missing.json"))
        strat = AdaptiveCoreMicroStrategy(
            gate=gate,
            journal=journal,
            parameters={"record_decisions": False},
        )
        strat.analyze(_trend_positive_candles(), "BTCUSDT")
        journal.record.assert_not_called()
