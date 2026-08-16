"""
Adaptive Core Micro Strategy — Production candidate.

Design principle: default to HOLD. Trade only when two independent conditions
are simultaneously satisfied:

  1. **Core gate** — Higher-timeframe (4h) trend is positive for BTC/ETH.
     Trend is defined as: close > EMA(50) computed from 4h candles.

  2. **Micro gate** — The strategy validation gate artifact is fresh,
     overall_pass=True, and the specific symbol passes the gate.

If either condition is missing or negative the strategy returns HOLD with
a metadata dict explaining the precise reason.  Every signal — including
HOLDs — carries a ``component`` field naming which component fired the
decision and a ``hold_reason`` when applicable.

This strategy is CONSERVATIVE by design and suitable as a production candidate.
``buy_strategy_aggressive`` is NOT used here.  See ``buy_strategy_aggressive.py``
for its testnet/paper-only designation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..core.decision_journal import DecisionJournal, get_decision_journal
from ..core.strategy_validation_gate import ValidationGate, get_validation_gate
from .base_strategy import BaseStrategy, SignalType, StrategyResult

logger = logging.getLogger(__name__)

# Symbols covered by the long-term core component (BTC and ETH only)
_CORE_SYMBOLS = {"BTCUSDT", "ETHUSDT"}

# Minimum EMA window for higher-TF trend determination
_HTF_EMA_WINDOW = 50


def _compute_ema(closes: List[float], window: int) -> Optional[float]:
    """Return the final EMA value or None if not enough data."""
    if len(closes) < window:
        return None
    k = 2.0 / (window + 1)
    ema = closes[0]
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)
    return ema


class AdaptiveCoreMicroStrategy(BaseStrategy):
    """
    Production-grade adaptive strategy.

    Parameters (all optional, passed via ``parameters`` dict):
        htf_ema_window:       EMA window for higher-TF trend (default 50).
        gate_path:            Path to strategy validation gate JSON.
        core_symbols:         Set of symbols eligible for the core component.
        record_decisions:     Whether to persist decisions to the journal (default True).
    """

    def __init__(
        self,
        market_data_agent=None,
        gate: Optional[ValidationGate] = None,
        journal: Optional[DecisionJournal] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.market_data_agent = market_data_agent
        self._gate = gate  # injected for testing; if None, loaded lazily
        self._journal = journal  # injected for testing; if None, loaded lazily
        super().__init__(parameters or {})

    # ------------------------------------------------------------------
    # BaseStrategy contract
    # ------------------------------------------------------------------

    def get_name(self) -> str:
        return "adaptive_core_micro"

    def get_description(self) -> str:
        return (
            "Adaptive core + micro strategy. Default HOLD. "
            "Trades BTC/ETH when higher-TF trend is positive AND "
            "micro validation gate is fresh and positive."
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "htf_ema_window": {
                "default": _HTF_EMA_WINDOW,
                "type": int,
                "description": "EMA window for higher-timeframe trend confirmation",
            },
            "gate_path": {
                "default": None,
                "type": str,
                "description": "Path to strategy validation gate JSON",
            },
            "core_symbols": {
                "default": list(_CORE_SYMBOLS),
                "type": list,
                "description": "Symbols eligible for the core (long-TF) component",
            },
            "record_decisions": {
                "default": True,
                "type": bool,
                "description": "Persist every decision to the decision journal",
            },
        }

    # ------------------------------------------------------------------
    # Main analysis method
    # ------------------------------------------------------------------

    def analyze(
        self,
        ohlcv_data: List[Any],
        symbol: str,
        htf_ohlcv_data: Optional[List[Any]] = None,
    ) -> StrategyResult:
        """
        Evaluate both gates and return a signal with full metadata.

        Args:
            ohlcv_data:      OHLCV candles for the trading timeframe (list of
                             [open_time, open, high, low, close, volume, ...]).
            symbol:          Trading pair e.g. "BTCUSDT".
            htf_ohlcv_data:  Optional higher-timeframe (4h) candles for the core
                             component.  If None the core gate uses ohlcv_data.

        Returns:
            StrategyResult with signal BUY, SELL, or HOLD.
        """
        symbol = symbol.upper()
        htf_data = htf_ohlcv_data or ohlcv_data

        # ---------------------------------------------------------------
        # Step 1: Micro validation gate
        # ---------------------------------------------------------------
        micro_gate_result = self._check_micro_gate(symbol)
        if not micro_gate_result["cleared"]:
            return self._hold(
                symbol=symbol,
                component="micro_gate",
                hold_reason=micro_gate_result["reason"],
                metadata={
                    "micro_gate": micro_gate_result,
                    "core_gate": None,
                },
                ohlcv_data=ohlcv_data,
            )

        # ---------------------------------------------------------------
        # Step 2: Core long-term trend gate (BTC/ETH only)
        # ---------------------------------------------------------------
        core_gate_result = self._check_core_trend(symbol, htf_data)
        if not core_gate_result["cleared"]:
            return self._hold(
                symbol=symbol,
                component="core_gate",
                hold_reason=core_gate_result["reason"],
                metadata={
                    "micro_gate": micro_gate_result,
                    "core_gate": core_gate_result,
                },
                ohlcv_data=ohlcv_data,
            )

        # ---------------------------------------------------------------
        # Step 3: Both gates cleared — produce a signal
        # ---------------------------------------------------------------
        signal = self._compute_signal(ohlcv_data)
        current_price = self._last_close(ohlcv_data)

        result = StrategyResult(
            signal=signal,
            confidence=0.6 if signal != SignalType.HOLD else 0.0,
            metadata={
                "component": "adaptive_core_micro",
                "micro_gate": micro_gate_result,
                "core_gate": core_gate_result,
                "signal_source": "rsi_micro",
                "current_price": current_price,
            },
        )

        self._maybe_record(symbol, result)
        return result

    # ------------------------------------------------------------------
    # Gate helpers
    # ------------------------------------------------------------------

    def _check_micro_gate(self, symbol: str) -> Dict[str, Any]:
        gate = self._gate or get_validation_gate(self.parameters.get("gate_path"))
        gate_result = gate.check(symbol)
        return {
            "cleared": gate_result.cleared,
            "reason": gate_result.reason,
            "age_seconds": gate_result.age_seconds,
            "gate_data": gate_result.gate_data,
        }

    def _check_core_trend(self, symbol: str, htf_data: List[Any]) -> Dict[str, Any]:
        core_symbols = set(self.parameters.get("core_symbols", _CORE_SYMBOLS))
        if symbol not in core_symbols:
            # Non-core symbols skip the trend gate — micro gate is sufficient
            return {"cleared": True, "reason": None, "ema": None, "close": None}

        closes = self._extract_closes(htf_data)
        window = int(self.parameters.get("htf_ema_window", _HTF_EMA_WINDOW))
        ema = _compute_ema(closes, window)

        if ema is None:
            return {
                "cleared": False,
                "reason": "insufficient_htf_data",
                "ema": None,
                "close": closes[-1] if closes else None,
            }

        last_close = closes[-1]
        trend_positive = last_close > ema

        if not trend_positive:
            return {
                "cleared": False,
                "reason": "htf_trend_negative",
                "ema": round(ema, 8),
                "close": round(last_close, 8),
            }

        return {
            "cleared": True,
            "reason": None,
            "ema": round(ema, 8),
            "close": round(last_close, 8),
        }

    # ------------------------------------------------------------------
    # Signal computation (micro RSI component)
    # ------------------------------------------------------------------

    def _compute_signal(self, ohlcv_data: List[Any]) -> SignalType:
        """Simple RSI-based micro signal (same thresholds as micro_grid validator)."""
        closes = self._extract_closes(ohlcv_data)
        if len(closes) < 15:
            return SignalType.HOLD

        rsi = self._rsi(closes)
        if rsi is None:
            return SignalType.HOLD
        if rsi < 32:
            return SignalType.BUY
        if rsi > 68:
            return SignalType.SELL
        return SignalType.HOLD

    @staticmethod
    def _rsi(closes: List[float], period: int = 14) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(d, 0) for d in deltas[-period:]]
        losses = [max(-d, 0) for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # ------------------------------------------------------------------
    # Helper constructors
    # ------------------------------------------------------------------

    def _hold(
        self,
        symbol: str,
        component: str,
        hold_reason: str,
        metadata: Dict[str, Any],
        ohlcv_data: List[Any],
    ) -> StrategyResult:
        result = StrategyResult(
            signal=SignalType.HOLD,
            confidence=0.0,
            metadata={
                "component": component,
                "hold_reason": hold_reason,
                **metadata,
                "current_price": self._last_close(ohlcv_data),
            },
        )
        self._maybe_record(symbol, result)
        return result

    def _maybe_record(self, symbol: str, result: StrategyResult) -> None:
        if not self.parameters.get("record_decisions", True):
            return
        try:
            journal = self._journal or get_decision_journal()
            hold_reason = result.metadata.get("hold_reason")
            journal.record(
                symbol=symbol,
                signal=result.signal.value,
                strategy=self.get_name(),
                confidence=result.confidence,
                blocked_reason=hold_reason,
                metadata=result.metadata,
            )
        except Exception:
            logger.warning("Could not record decision for %s", symbol, exc_info=True)

    @staticmethod
    def _extract_closes(ohlcv_data: List[Any]) -> List[float]:
        closes = []
        for candle in ohlcv_data:
            if isinstance(candle, (list, tuple)) and len(candle) >= 5:
                closes.append(float(candle[4]))
            elif isinstance(candle, dict):
                closes.append(float(candle.get("close", candle.get("c", 0))))
        return closes

    @staticmethod
    def _last_close(ohlcv_data: List[Any]) -> Optional[float]:
        if not ohlcv_data:
            return None
        c = ohlcv_data[-1]
        if isinstance(c, (list, tuple)) and len(c) >= 5:
            return float(c[4])
        if isinstance(c, dict):
            return float(c.get("close", c.get("c", 0)))
        return None
