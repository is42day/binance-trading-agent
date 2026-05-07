"""
Edge Strategy - Contrarian signals with statistical backing

This strategy focuses on signals that have documented edge:
1. Funding Rate Extremes - Mean reversion when perp funding is extreme
2. Fear & Greed Index - Contrarian at extremes (<25 = buy, >75 = sell)
3. Open Interest Changes - Large OI drops often precede reversals
4. Volume Anomalies - Unusual volume without price movement = accumulation/distribution
5. Liquidation Magnet - Price tends to hunt liquidity

Philosophy: Don't trade WITH the crowd at extremes, trade AGAINST them.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import requests

from .base_strategy import BaseStrategy, SignalType, StrategyResult

logger = logging.getLogger(__name__)


class EdgeStrategy(BaseStrategy):
    """
    Contrarian edge strategy using alternative data sources.

    Key insight: Markets overreact at extremes. When everyone is fearful,
    buy. When everyone is greedy and funding is sky-high, sell.
    """

    def __init__(self, market_data_agent=None, parameters: dict = None):
        self.market_data_agent = market_data_agent
        self._name = "edge_contrarian"
        super().__init__(parameters)

        # Thresholds calibrated from historical data
        self.fear_greed_buy_threshold = 25    # Extreme fear = buy
        self.fear_greed_sell_threshold = 75   # Extreme greed = sell

        # Funding rate thresholds (annualized)
        self.funding_extreme_high = 0.1       # 0.1% per 8h = very high
        self.funding_extreme_low = -0.05      # Negative funding = shorts paying

        # Volume anomaly detection
        self.volume_spike_multiplier = 2.5    # Volume > 2.5x average

        # Cache for API calls (avoid rate limits)
        self._fear_greed_cache = {"value": None, "timestamp": None}
        self._funding_cache = {}

    def _get_fear_greed_index(self) -> Optional[int]:
        """
        Fetch Fear & Greed Index from Alternative.me

        Returns value 0-100:
        - 0-25: Extreme Fear (BUY signal)
        - 25-45: Fear
        - 45-55: Neutral
        - 55-75: Greed
        - 75-100: Extreme Greed (SELL signal)
        """
        # Check cache (update every 30 minutes)
        if self._fear_greed_cache["timestamp"]:
            age = datetime.now() - self._fear_greed_cache["timestamp"]
            if age < timedelta(minutes=30):
                return self._fear_greed_cache["value"]

        try:
            response = requests.get(
                "https://api.alternative.me/fng/",
                timeout=5
            )
            data = response.json()
            value = int(data["data"][0]["value"])

            self._fear_greed_cache = {
                "value": value,
                "timestamp": datetime.now()
            }

            logger.info(f"Fear & Greed Index: {value}")
            return value

        except Exception as e:
            logger.warning(f"Failed to fetch Fear & Greed: {e}")
            return None

    def _get_funding_rate(self, symbol: str) -> Optional[float]:
        """
        Get current funding rate for perpetual futures.

        Binance funding rate is paid every 8 hours.
        Positive = longs pay shorts (bullish sentiment, often tops)
        Negative = shorts pay longs (bearish sentiment, often bottoms)
        """
        # Check cache (update every 5 minutes)
        cache_key = symbol
        if cache_key in self._funding_cache:
            cache_entry = self._funding_cache[cache_key]
            age = datetime.now() - cache_entry["timestamp"]
            if age < timedelta(minutes=5):
                return cache_entry["value"]

        try:
            # Convert spot symbol to futures symbol
            futures_symbol = symbol  # BTCUSDT works for both

            response = requests.get(
                "https://fapi.binance.com/fapi/v1/fundingRate",
                params={"symbol": futures_symbol, "limit": 1},
                timeout=5
            )
            data = response.json()

            if data and len(data) > 0:
                funding_rate = float(data[0]["fundingRate"])

                self._funding_cache[cache_key] = {
                    "value": funding_rate,
                    "timestamp": datetime.now()
                }

                logger.info(f"Funding rate {symbol}: {funding_rate:.4%}")
                return funding_rate

        except Exception as e:
            logger.warning(f"Failed to fetch funding rate: {e}")

        return None

    def _detect_volume_anomaly(self, ohlcv_data: list) -> dict:
        """
        Detect unusual volume patterns.

        High volume + small price move = accumulation/distribution
        This often precedes big moves.
        """
        if len(ohlcv_data) < 20:
            return {"detected": False}

        recent = ohlcv_data[-1]
        historical = ohlcv_data[-21:-1]  # Last 20 candles excluding current

        avg_volume = sum(c["volume"] for c in historical) / len(historical)
        current_volume = recent["volume"]

        # Calculate price move
        price_change_pct = abs(
            (recent["close"] - recent["open"]) / recent["open"] * 100
        )

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # High volume + small price move = accumulation/distribution
        if volume_ratio > self.volume_spike_multiplier and price_change_pct < 1.0:
            # Determine direction by close position in candle
            candle_body = recent["close"] - recent["open"]
            candle_range = recent["high"] - recent["low"]

            if candle_range > 0:
                close_position = (recent["close"] - recent["low"]) / candle_range
            else:
                close_position = 0.5

            return {
                "detected": True,
                "volume_ratio": volume_ratio,
                "type": "accumulation" if close_position > 0.6 else "distribution",
                "signal": "bullish" if close_position > 0.6 else "bearish"
            }

        return {"detected": False, "volume_ratio": volume_ratio}

    def _calculate_liquidation_levels(self, current_price: float, ohlcv_data: list) -> dict:
        """
        Estimate where liquidation clusters might be.

        Theory: Price tends to hunt liquidity. If there's been a strong
        move, stops/liquidations cluster at recent highs/lows.
        """
        if len(ohlcv_data) < 50:
            return {"levels": []}

        recent_data = ohlcv_data[-50:]

        # Find recent swing highs and lows
        highs = [c["high"] for c in recent_data]
        lows = [c["low"] for c in recent_data]

        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])

        # Estimate liquidation zones (common leverage points)
        # 10x leverage liquidates at ~10% move against position
        # 20x liquidates at ~5% move

        levels = {
            "long_liquidations_10x": current_price * 0.90,  # 10% below
            "long_liquidations_20x": current_price * 0.95,  # 5% below
            "short_liquidations_10x": current_price * 1.10,  # 10% above
            "short_liquidations_20x": current_price * 1.05,  # 5% above
            "recent_high": recent_high,
            "recent_low": recent_low,
        }

        # Check if price is near liquidation zones (potential magnets)
        distance_to_short_liq = (levels["short_liquidations_20x"] - current_price) / current_price
        distance_to_long_liq = (current_price - levels["long_liquidations_20x"]) / current_price

        return {
            "levels": levels,
            "near_short_liquidations": distance_to_short_liq < 0.02,
            "near_long_liquidations": distance_to_long_liq < 0.02,
        }

    def generate_signal(self, symbol: str, ohlcv_data: list = None) -> dict:
        """
        Generate trading signal based on contrarian edge factors.

        Signal strength is based on confluence of multiple edge factors.
        """
        if ohlcv_data is None:
            ohlcv_data = self._fetch_ohlcv(symbol)

        if not ohlcv_data or len(ohlcv_data) < 50:
            return self._create_signal("HOLD", 0.0, {"error": "Insufficient data"})

        current_price = ohlcv_data[-1]["close"]

        # Collect all edge signals
        signals = {
            "fear_greed": {"signal": "neutral", "strength": 0},
            "funding": {"signal": "neutral", "strength": 0},
            "volume": {"signal": "neutral", "strength": 0},
            "liquidation": {"signal": "neutral", "strength": 0},
        }

        # 1. Fear & Greed Index (weight: 35%)
        fear_greed = self._get_fear_greed_index()
        if fear_greed is not None:
            if fear_greed <= self.fear_greed_buy_threshold:
                # Extreme fear - contrarian BUY
                # Stronger signal when fear is more extreme (0-10 = max strength)
                if fear_greed <= 10:
                    strength = 1.0  # Extreme fear
                elif fear_greed <= 15:
                    strength = 0.85  # Very high fear
                elif fear_greed <= 20:
                    strength = 0.7  # High fear
                else:
                    strength = 0.5  # Moderate fear
                signals["fear_greed"] = {
                    "signal": "bullish",
                    "strength": strength,
                    "value": fear_greed,
                    "interpretation": f"Fear Index {fear_greed} - Contrarian Buy"
                }
            elif fear_greed >= self.fear_greed_sell_threshold:
                # Extreme greed - contrarian SELL
                if fear_greed >= 90:
                    strength = 1.0  # Extreme greed
                elif fear_greed >= 85:
                    strength = 0.85  # Very high greed
                elif fear_greed >= 80:
                    strength = 0.7  # High greed
                else:
                    strength = 0.5  # Moderate greed
                signals["fear_greed"] = {
                    "signal": "bearish",
                    "strength": strength,
                    "value": fear_greed,
                    "interpretation": f"Greed Index {fear_greed} - Contrarian Sell"
                }
            else:
                signals["fear_greed"]["value"] = fear_greed

        # 2. Funding Rate (weight: 30%)
        funding = self._get_funding_rate(symbol)
        if funding is not None:
            if funding >= self.funding_extreme_high:
                # Very high funding - longs are crowded, expect reversal DOWN
                strength = min((funding - self.funding_extreme_high) / 0.1, 1.0)
                signals["funding"] = {
                    "signal": "bearish",
                    "strength": strength,
                    "value": funding,
                    "interpretation": f"High funding ({funding:.4%}) - Longs crowded"
                }
            elif funding <= self.funding_extreme_low:
                # Negative funding - shorts are crowded, expect reversal UP
                strength = min((self.funding_extreme_low - funding) / 0.05, 1.0)
                signals["funding"] = {
                    "signal": "bullish",
                    "strength": strength,
                    "value": funding,
                    "interpretation": f"Negative funding ({funding:.4%}) - Shorts crowded"
                }
            else:
                signals["funding"]["value"] = funding

        # 3. Volume Anomaly (weight: 20%)
        volume_analysis = self._detect_volume_anomaly(ohlcv_data)
        if volume_analysis["detected"]:
            signals["volume"] = {
                "signal": "bullish" if volume_analysis["type"] == "accumulation" else "bearish",
                "strength": min((volume_analysis["volume_ratio"] - 2) / 3, 1.0),
                "type": volume_analysis["type"],
                "volume_ratio": volume_analysis["volume_ratio"],
                "interpretation": f"{volume_analysis['type'].title()} detected (volume {volume_analysis['volume_ratio']:.1f}x avg)"
            }

        # 4. Liquidation Levels (weight: 15%)
        liq_analysis = self._calculate_liquidation_levels(current_price, ohlcv_data)
        if liq_analysis.get("near_short_liquidations"):
            signals["liquidation"] = {
                "signal": "bullish",
                "strength": 0.6,
                "interpretation": "Near short liquidation zone - potential squeeze"
            }
        elif liq_analysis.get("near_long_liquidations"):
            signals["liquidation"] = {
                "signal": "bearish",
                "strength": 0.6,
                "interpretation": "Near long liquidation zone - potential cascade"
            }

        # Calculate weighted signal
        weights = {
            "fear_greed": 0.35,
            "funding": 0.30,
            "volume": 0.20,
            "liquidation": 0.15,
        }

        bullish_score = 0
        bearish_score = 0

        for factor, data in signals.items():
            weight = weights[factor]
            strength = data.get("strength", 0)

            if data["signal"] == "bullish":
                bullish_score += weight * strength
            elif data["signal"] == "bearish":
                bearish_score += weight * strength

        # Determine final signal
        net_score = bullish_score - bearish_score

        # Require minimum conviction - lowered to allow single strong factor
        min_conviction = 0.15  # Need at least 15% weighted signal

        if net_score >= min_conviction:
            action = "BUY"
            confidence = min(net_score * 1.5 + 0.3, 1.0)  # Scale with boost
        elif net_score <= -min_conviction:
            action = "SELL"
            confidence = min(abs(net_score) * 1.5 + 0.3, 1.0)
        else:
            action = "HOLD"
            confidence = 0.5

        return self._create_signal(
            action=action,
            confidence=confidence,
            metadata={
                "strategy": self.name,
                "symbol": symbol,
                "price": current_price,
                "bullish_score": round(bullish_score, 3),
                "bearish_score": round(bearish_score, 3),
                "net_score": round(net_score, 3),
                "factors": signals,
                "edge_factors_active": sum(
                    1 for s in signals.values()
                    if s.get("strength", 0) > 0
                ),
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
            "Contrarian edge strategy using Fear & Greed Index, funding rates, "
            "and volume anomalies to identify market extremes for mean reversion trades."
        )

    def get_parameters(self) -> dict:
        """Return strategy parameters"""
        return {
            "fear_greed_buy_threshold": {
                "default": 25,
                "description": "Fear & Greed value below which to generate BUY signals",
            },
            "fear_greed_sell_threshold": {
                "default": 75,
                "description": "Fear & Greed value above which to generate SELL signals",
            },
            "funding_extreme_high": {
                "default": 0.1,
                "description": "Funding rate above which longs are crowded (bearish)",
            },
            "funding_extreme_low": {
                "default": -0.05,
                "description": "Funding rate below which shorts are crowded (bullish)",
            },
        }

    def analyze(self, market_data: list, symbol: str = None) -> StrategyResult:
        """Analyze market data - wrapper for generate_signal"""
        signal = self.generate_signal(symbol or "BTCUSDT", market_data)
        action = signal.get("action", "HOLD")
        try:
            signal_type = SignalType[action.upper()]
        except KeyError:
            signal_type = SignalType.HOLD

        metadata = {key: value for key, value in signal.items() if key not in {"action", "confidence"}}
        return StrategyResult(
            signal=signal_type,
            confidence=float(signal.get("confidence", 0.0)),
            metadata=metadata,
        )
