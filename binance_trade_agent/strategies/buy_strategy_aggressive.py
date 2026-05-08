"""
BUY Strategy - Ultra-aggressive entry to force trades

This strategy generates BUY signals on normal market conditions,
allowing us to build positions and see trading results.
"""

from typing import Any, Dict, List

from .base_strategy import BaseStrategy, SignalType, StrategyResult


class BuyStrategyAggressive(BaseStrategy):
    """
    Ultra-aggressive BUY strategy that generates signals in normal market conditions.
    
    Uses momentum-based entry to build positions quickly for testing and evaluation.
    """

    def __init__(self, parameters: Dict[str, Any] = None):
        super().__init__(parameters)

    def get_name(self) -> str:
        return "buy_aggressive"

    def get_description(self) -> str:
        return "Ultra-Aggressive BUY Strategy - Forces position entry for testing"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "period": {
                "default": 5,
                "type": int,
                "min": 2,
                "max": 50,
                "description": "RSI calculation period (shorter = faster signals)",
            },
            "buy_threshold": {
                "default": 60,
                "type": int,
                "min": 30,
                "max": 80,
                "description": "RSI threshold for BUY (lower = more buys)",
            },
            "sell_threshold": {
                "default": 75,
                "type": int,
                "min": 50,
                "max": 95,
                "description": "RSI threshold for SELL",
            },
            "momentum_factor": {
                "default": 0.02,
                "type": float,
                "description": "Price momentum window (2%)",
            },
            "profit_target_pct": {
                "default": 0.015,
                "type": float,
                "description": "Profit target percentage (1.5%)",
            },
            "stop_loss_pct": {
                "default": 0.01,
                "type": float,
                "description": "Stop loss percentage (1%)",
            },
        }

    def requires_minimum_data(self) -> int:
        return self.get_parameter("period") + 5

    def _calculate_rsi(self, closes: List[float]) -> float:
        """Calculate RSI indicator"""
        period = self.get_parameter("period")
        if len(closes) < period + 1:
            return 50.0

        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = sum(max(d, 0) for d in deltas[-period:]) / period
        losses = sum(max(-d, 0) for d in deltas[-period:]) / period

        if losses == 0:
            return 100.0 if gains > 0 else 50.0

        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)

    def _calculate_momentum(self, closes: List[float]) -> float:
        """Calculate price momentum (% change)"""
        if len(closes) < 2:
            return 0.0
        return (closes[-1] - closes[-2]) / closes[-2]

    def analyze(self, market_data: List[Dict[str, Any]], symbol: str = None) -> StrategyResult:
        """Generate BUY signals on upward momentum, SELL on downward"""
        if len(market_data) < self.requires_minimum_data():
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={"reason": "Insufficient data"},
            )

        try:
            closes = [float(candle["close"]) for candle in market_data]
            current_price = closes[-1]

            # Calculate indicators
            rsi = self._calculate_rsi(closes)
            momentum = self._calculate_momentum(closes)

            # Get parameters
            buy_threshold = self.get_parameter("buy_threshold")
            sell_threshold = self.get_parameter("sell_threshold")
            momentum_factor = self.get_parameter("momentum_factor")
            profit_target_pct = self.get_parameter("profit_target_pct")
            stop_loss_pct = self.get_parameter("stop_loss_pct")

            # Generate signal - ultra-aggressive on momentum
            signal = SignalType.HOLD
            confidence = 0.0

            if momentum > 0:
                # Upward momentum - ALWAYS BUY regardless of RSI
                # Higher confidence if also low RSI
                base_confidence = min(0.9, abs(momentum) * 10)  # momentum 0.02 = 0.2 confidence
                rsi_bonus = max(0, (buy_threshold - rsi) / buy_threshold * 0.3) if rsi < buy_threshold else 0.1
                confidence = min(0.95, base_confidence + rsi_bonus + 0.3)
                signal = SignalType.BUY
                price_target = current_price * (1 + profit_target_pct)
                stop_loss = current_price * (1 - stop_loss_pct)
                take_profit = price_target
            elif momentum < -0.001:  # Slight downward momentum
                # Only sell on strong overbought or downward momentum
                if rsi > sell_threshold:
                    confidence = min(0.8, (rsi - sell_threshold) / 25 + 0.4)
                    signal = SignalType.SELL
                    price_target = current_price * (1 - profit_target_pct)
                    stop_loss = current_price * (1 + stop_loss_pct)
                    take_profit = price_target
                else:
                    # Weak downward momentum - still might buy on dips
                    if rsi < buy_threshold:
                        confidence = 0.5
                        signal = SignalType.BUY
                        price_target = current_price * (1 + profit_target_pct)
                        stop_loss = current_price * (1 - stop_loss_pct)
                        take_profit = price_target
                    else:
                        price_target = None
                        stop_loss = None
                        take_profit = None
            else:
                # No momentum - use RSI only
                if rsi < buy_threshold:
                    confidence = min(0.7, (buy_threshold - rsi) / buy_threshold + 0.3)
                    signal = SignalType.BUY
                    price_target = current_price * (1 + profit_target_pct)
                    stop_loss = current_price * (1 - stop_loss_pct)
                    take_profit = price_target
                elif rsi > sell_threshold:
                    confidence = min(0.7, (rsi - sell_threshold) / 25 + 0.2)
                    signal = SignalType.SELL
                    price_target = current_price * (1 - profit_target_pct)
                    stop_loss = current_price * (1 + stop_loss_pct)
                    take_profit = price_target
                else:
                    price_target = None
                    stop_loss = None
                    take_profit = None

            return StrategyResult(
                signal=signal,
                confidence=confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                indicators={"rsi": round(rsi, 2), "momentum": round(momentum, 4)},
                metadata={
                    "strategy": "buy_aggressive",
                    "rsi_level": rsi,
                    "momentum": momentum,
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
        """Generate trading signal for paper trading loop"""
        from datetime import datetime
        
        if ohlcv_data is None:
            ohlcv_data = []
        
        # Convert OHLCV dicts to market_data format
        market_data = []
        for candle in ohlcv_data:
            if isinstance(candle, dict):
                market_data.append({
                    "close": float(candle.get("close", 0)),
                    "high": float(candle.get("high", 0)),
                    "low": float(candle.get("low", 0)),
                    "open": float(candle.get("open", 0)),
                    "volume": float(candle.get("volume", 0)),
                })
            else:
                market_data.append({
                    "close": float(candle[4]) if len(candle) > 4 else 0,
                    "high": float(candle[2]) if len(candle) > 2 else 0,
                    "low": float(candle[3]) if len(candle) > 3 else 0,
                    "open": float(candle[1]) if len(candle) > 1 else 0,
                    "volume": float(candle[5]) if len(candle) > 5 else 0,
                })
        
        result = self.analyze(market_data, symbol)
        
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
