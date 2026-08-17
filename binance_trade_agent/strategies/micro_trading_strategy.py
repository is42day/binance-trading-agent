"""
Micro Trading Strategy - Quick profits on volatile altcoins

This strategy uses RSI for entry signals with aggressive profit targets.
Perfect for altcoins with quick 2-3% moves.
"""

from typing import Any, Dict, List

from .base_strategy import BaseStrategy, SignalType, StrategyResult


class MicroTradingStrategy(BaseStrategy):
    """
    Micro trading strategy optimized for altcoins.

    Uses RSI with tighter profit targets (2-3%) and stops (1%) for quick trades.
    """

    def __init__(self, parameters: Dict[str, Any] = None):
        super().__init__(parameters)

    def get_name(self) -> str:
        return "micro_trading"

    def get_description(self) -> str:
        return "Micro Trading - Quick profits on volatile altcoins with 2-3% targets"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "period": {
                "default": 14,
                "type": int,
                "min": 2,
                "max": 50,
                "description": "RSI calculation period",
            },
            "overbought": {
                "default": 65,
                "type": int,
                "min": 50,
                "max": 95,
                "description": "RSI overbought threshold (lower = more signals)",
            },
            "oversold": {
                "default": 35,
                "type": int,
                "min": 5,
                "max": 50,
                "description": "RSI oversold threshold (higher = more signals)",
            },
            "profit_target_pct": {
                "default": 0.025,
                "type": float,
                "description": "Profit target percentage (2.5%)",
            },
            "stop_loss_pct": {
                "default": 0.01,
                "type": float,
                "description": "Stop loss percentage (1%)",
            },
        }

    def requires_minimum_data(self) -> int:
        return self.get_parameter("period") + 1

    def _calculate_rsi(self, closes: List[float]) -> float:
        """Calculate RSI indicator"""
        period = self.get_parameter("period")
        if len(closes) < period + 1:
            return 50.0

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = sum(max(d, 0) for d in deltas[-period:]) / period
        losses = sum(max(-d, 0) for d in deltas[-period:]) / period

        if losses == 0:
            return 100.0 if gains > 0 else 50.0

        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)

    def analyze(self, market_data: List[Dict[str, Any]], symbol: str = None) -> StrategyResult:
        """Analyze using RSI with micro trading parameters"""
        if len(market_data) < self.requires_minimum_data():
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={"reason": "Insufficient data"},
            )

        try:
            closes = [float(candle["close"]) for candle in market_data]
            current_price = closes[-1]

            # Calculate RSI
            rsi = self._calculate_rsi(closes)

            # Get parameters
            oversold = self.get_parameter("oversold")
            overbought = self.get_parameter("overbought")
            profit_target_pct = self.get_parameter("profit_target_pct")
            stop_loss_pct = self.get_parameter("stop_loss_pct")

            # Generate signal
            signal = SignalType.HOLD
            confidence = 0.0

            if rsi < oversold:
                # BUY signal
                confidence = min(0.9, (oversold - rsi) / (100 - oversold) * 0.9)
                signal = SignalType.BUY
                price_target = current_price * (1 + profit_target_pct)
                stop_loss = current_price * (1 - stop_loss_pct)
                take_profit = price_target

            elif rsi > overbought:
                # SELL signal
                confidence = min(0.9, (rsi - overbought) / overbought * 0.9)
                signal = SignalType.SELL
                price_target = current_price * (1 - profit_target_pct)
                stop_loss = current_price * (1 + stop_loss_pct)
                take_profit = price_target

            else:
                # HOLD
                price_target = None
                stop_loss = None
                take_profit = None

            return StrategyResult(
                signal=signal,
                confidence=confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                indicators={"rsi": round(rsi, 2)},
                metadata={
                    "strategy": "micro_trading",
                    "rsi_level": rsi,
                    "profit_target_pct": profit_target_pct * 100,
                    "stop_loss_pct": stop_loss_pct * 100,
                },
            )

        except Exception as e:
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def generate_signal(self, symbol: str, ohlcv_data: list = None) -> dict:
        """
        Generate trading signal for paper trading loop.

        Accepts OHLCV data as list of dicts with 'close', 'open', 'high', 'low', 'volume' keys.
        """
        from datetime import datetime

        if ohlcv_data is None:
            ohlcv_data = []

        # Convert OHLCV dicts to market_data format for analyze()
        market_data = []
        for candle in ohlcv_data:
            if isinstance(candle, dict):
                # Dictionary format from paper trading
                market_data.append(
                    {
                        "close": float(candle.get("close", 0)),
                        "high": float(candle.get("high", 0)),
                        "low": float(candle.get("low", 0)),
                        "open": float(candle.get("open", 0)),
                        "volume": float(candle.get("volume", 0)),
                    }
                )
            else:
                # Array format [time, open, high, low, close, volume]
                market_data.append(
                    {
                        "close": float(candle[4]) if len(candle) > 4 else 0,
                        "high": float(candle[2]) if len(candle) > 2 else 0,
                        "low": float(candle[3]) if len(candle) > 3 else 0,
                        "open": float(candle[1]) if len(candle) > 1 else 0,
                        "volume": float(candle[5]) if len(candle) > 5 else 0,
                    }
                )

        result = self.analyze(market_data, symbol)

        # Convert StrategyResult to dict format expected by paper trading
        signal_map = {
            SignalType.BUY: "BUY",
            SignalType.SELL: "SELL",
            SignalType.HOLD: "HOLD",
        }

        return {
            "action": signal_map[result.signal],
            "confidence": result.confidence,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "price_target": result.price_target,
            "stop_loss": result.stop_loss,
            "take_profit": result.take_profit,
            "indicators": result.indicators,
            "metadata": result.metadata,
        }
