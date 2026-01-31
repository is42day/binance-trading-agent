"""
Smart Entry Strategy - Optimizing entry timing for better fills

This strategy focuses on WHEN to enter, not just IF to enter.
Key concepts:
1. Support/Resistance proximity - Enter near levels, not in no-man's land
2. Volatility compression - Low volatility often precedes big moves
3. Order flow imbalance - Who's actually buying vs selling
4. Time-based patterns - Crypto has predictable volatility windows
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class SmartEntryStrategy(BaseStrategy):
    """
    Strategy focused on optimal entry timing.
    
    Even a good trade idea can lose money with bad timing.
    This strategy waits for high-probability entry points.
    """
    
    def __init__(self, market_data_agent=None, parameters: dict = None):
        self.market_data_agent = market_data_agent
        self._name = "smart_entry"
        super().__init__(parameters)
        
        # Volatility parameters
        self.volatility_lookback = 20
        self.volatility_compression_threshold = 0.6  # Current vol < 60% of avg
        
        # Support/Resistance parameters
        self.sr_lookback = 100
        self.sr_proximity_pct = 0.02  # Within 2% of S/R level
        
        # Order book imbalance threshold
        self.imbalance_threshold = 0.65  # 65% on one side
        
    def _calculate_volatility_compression(self, ohlcv_data: list) -> dict:
        """
        Detect volatility compression (Bollinger Band squeeze).
        
        When volatility contracts significantly, it often precedes
        an explosive move. Trade in the direction of the breakout.
        """
        if len(ohlcv_data) < self.volatility_lookback * 2:
            return {"compressed": False}
        
        closes = [c["close"] for c in ohlcv_data]
        
        # Calculate rolling ATR
        atrs = []
        for i in range(len(ohlcv_data) - self.volatility_lookback, len(ohlcv_data)):
            if i < 1:
                continue
            tr = max(
                ohlcv_data[i]["high"] - ohlcv_data[i]["low"],
                abs(ohlcv_data[i]["high"] - ohlcv_data[i-1]["close"]),
                abs(ohlcv_data[i]["low"] - ohlcv_data[i-1]["close"])
            )
            atrs.append(tr)
        
        if len(atrs) < 5:
            return {"compressed": False}
        
        current_atr = np.mean(atrs[-5:])  # Recent 5 periods
        historical_atr = np.mean(atrs)     # Full lookback
        
        compression_ratio = current_atr / historical_atr if historical_atr > 0 else 1
        
        # Calculate Bollinger Band width
        recent_closes = closes[-20:]
        bb_std = np.std(recent_closes)
        bb_mean = np.mean(recent_closes)
        bb_width = (2 * bb_std / bb_mean) * 100 if bb_mean > 0 else 0
        
        is_compressed = compression_ratio < self.volatility_compression_threshold
        
        return {
            "compressed": is_compressed,
            "compression_ratio": round(compression_ratio, 3),
            "current_atr": round(current_atr, 2),
            "bb_width_pct": round(bb_width, 2),
            "interpretation": "Volatility squeeze - expecting breakout" if is_compressed else "Normal volatility"
        }
    
    def _find_support_resistance(self, ohlcv_data: list) -> dict:
        """
        Identify key support and resistance levels.
        
        Use pivot points, recent swing highs/lows, and volume-weighted levels.
        """
        if len(ohlcv_data) < self.sr_lookback:
            return {"levels": [], "current_zone": "unknown"}
        
        data = ohlcv_data[-self.sr_lookback:]
        current_price = data[-1]["close"]
        
        # Find swing highs and lows
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(data) - 2):
            # Swing high: higher than 2 candles before and after
            if (data[i]["high"] > data[i-1]["high"] and 
                data[i]["high"] > data[i-2]["high"] and
                data[i]["high"] > data[i+1]["high"] and 
                data[i]["high"] > data[i+2]["high"]):
                swing_highs.append(data[i]["high"])
            
            # Swing low: lower than 2 candles before and after
            if (data[i]["low"] < data[i-1]["low"] and 
                data[i]["low"] < data[i-2]["low"] and
                data[i]["low"] < data[i+1]["low"] and 
                data[i]["low"] < data[i+2]["low"]):
                swing_lows.append(data[i]["low"])
        
        # Cluster nearby levels
        def cluster_levels(levels, threshold_pct=0.01):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = [[levels[0]]]
            for level in levels[1:]:
                if (level - clusters[-1][-1]) / clusters[-1][-1] < threshold_pct:
                    clusters[-1].append(level)
                else:
                    clusters.append([level])
            return [sum(c) / len(c) for c in clusters]
        
        resistance_levels = cluster_levels(swing_highs)
        support_levels = cluster_levels(swing_lows)
        
        # Find nearest levels
        nearest_resistance = None
        nearest_support = None
        
        for level in sorted(resistance_levels):
            if level > current_price:
                nearest_resistance = level
                break
        
        for level in sorted(support_levels, reverse=True):
            if level < current_price:
                nearest_support = level
                break
        
        # Calculate proximity
        resistance_proximity = None
        support_proximity = None
        
        if nearest_resistance:
            resistance_proximity = (nearest_resistance - current_price) / current_price
        if nearest_support:
            support_proximity = (current_price - nearest_support) / current_price
        
        # Determine current zone
        if support_proximity and support_proximity < self.sr_proximity_pct:
            zone = "near_support"
            zone_signal = "bullish"
        elif resistance_proximity and resistance_proximity < self.sr_proximity_pct:
            zone = "near_resistance"
            zone_signal = "bearish"
        else:
            zone = "no_mans_land"
            zone_signal = "neutral"
        
        return {
            "nearest_resistance": nearest_resistance,
            "nearest_support": nearest_support,
            "resistance_proximity_pct": round(resistance_proximity * 100, 2) if resistance_proximity else None,
            "support_proximity_pct": round(support_proximity * 100, 2) if support_proximity else None,
            "current_zone": zone,
            "zone_signal": zone_signal,
            "interpretation": f"Price in {zone} - {zone_signal} bias"
        }
    
    def _analyze_order_flow(self, ohlcv_data: list) -> dict:
        """
        Analyze order flow using candle structure.
        
        Buying pressure: Close near high, long lower wicks
        Selling pressure: Close near low, long upper wicks
        """
        if len(ohlcv_data) < 10:
            return {"imbalance": 0, "direction": "neutral"}
        
        recent = ohlcv_data[-10:]
        
        buying_pressure = 0
        selling_pressure = 0
        
        for candle in recent:
            high = candle["high"]
            low = candle["low"]
            open_p = candle["open"]
            close = candle["close"]
            volume = candle["volume"]
            
            candle_range = high - low
            if candle_range == 0:
                continue
            
            # Calculate where close is relative to range
            close_position = (close - low) / candle_range
            
            # Weight by volume
            if close_position > 0.6:  # Close in upper 40%
                buying_pressure += volume * close_position
            elif close_position < 0.4:  # Close in lower 40%
                selling_pressure += volume * (1 - close_position)
        
        total_pressure = buying_pressure + selling_pressure
        if total_pressure == 0:
            return {"imbalance": 0, "direction": "neutral"}
        
        buy_ratio = buying_pressure / total_pressure
        
        if buy_ratio > self.imbalance_threshold:
            direction = "bullish"
            imbalance = buy_ratio
        elif buy_ratio < (1 - self.imbalance_threshold):
            direction = "bearish"
            imbalance = 1 - buy_ratio
        else:
            direction = "neutral"
            imbalance = 0.5
        
        return {
            "imbalance": round(imbalance, 3),
            "direction": direction,
            "buy_ratio": round(buy_ratio, 3),
            "interpretation": f"Order flow {direction} (buy ratio: {buy_ratio:.1%})"
        }
    
    def _check_time_factors(self) -> dict:
        """
        Check time-based factors that affect trading.
        
        - Avoid major news times (FOMC, etc.)
        - Crypto is more volatile during certain hours
        - Monday opens and Friday closes have patterns
        """
        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday
        
        # High volatility periods (UTC)
        # US market open: 13:30-15:00 UTC
        # US market close: 20:00-21:00 UTC
        # Asian open: 00:00-02:00 UTC
        
        is_high_volatility_window = (
            (13 <= hour <= 15) or  # US open
            (20 <= hour <= 21) or  # US close
            (0 <= hour <= 2)       # Asian open
        )
        
        # Weekend effect - often lower liquidity
        is_weekend = weekday >= 5
        
        # Monday morning dump/pump pattern
        is_monday_open = weekday == 0 and hour < 6
        
        # Avoid trading right before major time windows
        is_pre_volatility = (
            (12 <= hour <= 13) or   # Before US open
            (19 <= hour <= 20)      # Before US close
        )
        
        timing_score = 1.0
        if is_weekend:
            timing_score *= 0.8  # Reduce confidence
        if is_pre_volatility:
            timing_score *= 0.7
        if is_high_volatility_window:
            timing_score *= 1.1  # Slight boost for volatility
        
        return {
            "hour_utc": hour,
            "weekday": weekday,
            "is_weekend": is_weekend,
            "is_high_volatility_window": is_high_volatility_window,
            "timing_score": round(timing_score, 2),
            "interpretation": (
                "High volatility window - good for momentum" if is_high_volatility_window
                else "Low volatility period - wait or reduce size" if is_weekend
                else "Normal trading hours"
            )
        }
    
    def generate_signal(self, symbol: str, ohlcv_data: list = None) -> dict:
        """
        Generate smart entry signal.
        
        This strategy acts as a FILTER - it helps time entries
        for signals from other strategies.
        """
        if ohlcv_data is None:
            ohlcv_data = self._fetch_ohlcv(symbol)
        
        if not ohlcv_data or len(ohlcv_data) < self.sr_lookback:
            return self._create_signal("HOLD", 0.0, {"error": "Insufficient data"})
        
        current_price = ohlcv_data[-1]["close"]
        
        # Analyze all factors
        volatility = self._calculate_volatility_compression(ohlcv_data)
        sr_levels = self._find_support_resistance(ohlcv_data)
        order_flow = self._analyze_order_flow(ohlcv_data)
        timing = self._check_time_factors()
        
        # Scoring system
        entry_score = 0
        direction_bias = 0  # Positive = bullish, negative = bearish
        
        # 1. S/R Proximity (important for entry timing)
        if sr_levels["current_zone"] == "near_support":
            entry_score += 0.3
            direction_bias += 0.3
        elif sr_levels["current_zone"] == "near_resistance":
            entry_score += 0.3
            direction_bias -= 0.3
        else:
            # In no-man's land - reduce entry quality
            entry_score -= 0.2
        
        # 2. Volatility Compression (potential for big move)
        if volatility["compressed"]:
            entry_score += 0.25
            # Direction determined by other factors
        
        # 3. Order Flow (confirms direction)
        if order_flow["direction"] == "bullish":
            direction_bias += 0.25
            entry_score += 0.15
        elif order_flow["direction"] == "bearish":
            direction_bias -= 0.25
            entry_score += 0.15
        
        # 4. Timing (modifies confidence)
        entry_score *= timing["timing_score"]
        
        # Determine action
        if entry_score >= 0.4:
            if direction_bias > 0.2:
                action = "BUY"
                confidence = min(entry_score + direction_bias, 1.0)
            elif direction_bias < -0.2:
                action = "SELL"
                confidence = min(entry_score + abs(direction_bias), 1.0)
            else:
                action = "HOLD"
                confidence = 0.5
        else:
            action = "HOLD"
            confidence = 0.4
        
        return self._create_signal(
            action=action,
            confidence=confidence,
            metadata={
                "strategy": self.name,
                "symbol": symbol,
                "price": current_price,
                "entry_score": round(entry_score, 3),
                "direction_bias": round(direction_bias, 3),
                "volatility": volatility,
                "support_resistance": sr_levels,
                "order_flow": order_flow,
                "timing": timing,
            }
        )
    
    def _create_signal(self, action: str, confidence: float, metadata: dict) -> dict:
        """Create standardized signal response"""
        return {
            "action": action,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            **metadata
        }
    
    def get_name(self) -> str:
        """Return strategy name"""
        return self._name
    
    def get_description(self) -> str:
        """Return strategy description"""
        return (
            "Smart entry strategy that optimizes entry timing using support/resistance "
            "proximity, volatility compression, order flow analysis, and time-based patterns."
        )
    
    def get_parameters(self) -> dict:
        """Return strategy parameters"""
        return {
            "volatility_lookback": {
                "default": 20,
                "description": "Number of candles for volatility calculation",
            },
            "volatility_compression_threshold": {
                "default": 0.6,
                "description": "Threshold for detecting volatility compression",
            },
            "sr_proximity_pct": {
                "default": 0.02,
                "description": "Percentage proximity to S/R level",
            },
        }
    
    def analyze(self, market_data: list, symbol: str = None) -> dict:
        """Analyze market data - wrapper for generate_signal"""
        return self.generate_signal(symbol or "BTCUSDT", market_data)
