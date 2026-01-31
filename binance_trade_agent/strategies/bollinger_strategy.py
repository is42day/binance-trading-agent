"""
Bollinger Bands Trading Strategy

Uses Bollinger Bands for mean reversion trading:
- BUY when price touches/crosses below lower band (oversold)
- SELL when price touches/crosses above upper band (overbought)
- Enhanced with RSI confirmation for higher accuracy
"""

from typing import Any, Dict, List, Tuple

from .base_strategy import BaseStrategy, SignalType, StrategyResult


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands mean reversion strategy
    
    Generates:
    - BUY signals when price is at/below lower band AND RSI confirms oversold
    - SELL signals when price is at/above upper band AND RSI confirms overbought
    - HOLD signals when price is within bands
    
    Best used in ranging/sideways markets (60-70% of crypto trading time)
    """

    def get_name(self) -> str:
        return "bollinger"

    def get_description(self) -> str:
        return "Bollinger Bands mean reversion strategy with RSI confirmation"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "period": {
                "default": 20,
                "type": int,
                "min": 10,
                "max": 50,
                "description": "SMA period for middle band",
            },
            "std_dev_multiplier": {
                "default": 2.0,
                "type": float,
                "min": 1.0,
                "max": 3.0,
                "description": "Standard deviation multiplier for bands",
            },
            "rsi_period": {
                "default": 14,
                "type": int,
                "min": 7,
                "max": 21,
                "description": "RSI period for confirmation",
            },
            "rsi_oversold": {
                "default": 30,
                "type": int,
                "min": 20,
                "max": 40,
                "description": "RSI oversold threshold for BUY confirmation",
            },
            "rsi_overbought": {
                "default": 70,
                "type": int,
                "min": 60,
                "max": 80,
                "description": "RSI overbought threshold for SELL confirmation",
            },
            "require_rsi_confirmation": {
                "default": True,
                "type": bool,
                "description": "Require RSI to confirm band touch signals",
            },
            "band_touch_threshold": {
                "default": 0.001,
                "type": float,
                "min": 0.0,
                "max": 0.02,
                "description": "How close to band counts as 'touch' (% of price)",
            },
        }

    def requires_minimum_data(self) -> int:
        return max(self.get_parameter("period"), self.get_parameter("rsi_period")) + 5

    def analyze(self, market_data: List[Dict[str, Any]], symbol: str = None) -> StrategyResult:
        """
        Analyze market data using Bollinger Bands strategy
        """
        if len(market_data) < self.requires_minimum_data():
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={"error": "Insufficient data for Bollinger Bands calculation"},
            )

        try:
            closes = [float(candle["close"]) for candle in market_data]
            highs = [float(candle.get("high", candle["close"])) for candle in market_data]
            lows = [float(candle.get("low", candle["close"])) for candle in market_data]
            
            current_price = closes[-1]
            
            # Calculate Bollinger Bands
            upper_band, middle_band, lower_band = self._calculate_bollinger_bands(closes)
            
            # Calculate RSI for confirmation
            rsi = self._calculate_rsi(closes)
            
            # Calculate %B (where price is relative to bands)
            percent_b = self._calculate_percent_b(current_price, upper_band, lower_band)
            
            # Calculate bandwidth (volatility indicator)
            bandwidth = (upper_band - lower_band) / middle_band
            
            # Generate signal
            signal, confidence = self._generate_signal(
                current_price, upper_band, lower_band, rsi, percent_b
            )
            
            # Calculate levels
            price_target, stop_loss, take_profit = self._calculate_levels(
                current_price, signal, middle_band, upper_band, lower_band
            )
            
            return StrategyResult(
                signal=signal,
                confidence=confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                indicators={
                    "upper_band": upper_band,
                    "middle_band": middle_band,
                    "lower_band": lower_band,
                    "percent_b": percent_b,
                    "bandwidth": bandwidth,
                    "rsi": rsi,
                    "price_position": self._get_price_position(current_price, upper_band, lower_band),
                },
                metadata={
                    "strategy": self.name,
                    "current_price": current_price,
                    "data_points": len(market_data),
                },
            )

        except Exception as e:
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={"error": f"Bollinger calculation failed: {str(e)}"},
            )

    def _calculate_bollinger_bands(self, closes: List[float]) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands (upper, middle, lower)"""
        period = self.get_parameter("period")
        std_multiplier = self.get_parameter("std_dev_multiplier")
        
        # Middle band = SMA
        recent_closes = closes[-period:]
        middle_band = sum(recent_closes) / period
        
        # Standard deviation
        variance = sum((x - middle_band) ** 2 for x in recent_closes) / period
        std_dev = variance ** 0.5
        
        # Upper and lower bands
        upper_band = middle_band + (std_multiplier * std_dev)
        lower_band = middle_band - (std_multiplier * std_dev)
        
        return upper_band, middle_band, lower_band

    def _calculate_rsi(self, closes: List[float]) -> float:
        """Calculate RSI value"""
        period = self.get_parameter("rsi_period")
        
        if len(closes) < period + 1:
            return 50.0  # Neutral RSI if not enough data
        
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _calculate_percent_b(self, price: float, upper: float, lower: float) -> float:
        """
        Calculate %B indicator
        %B = (Price - Lower Band) / (Upper Band - Lower Band)
        
        %B < 0: Price below lower band (oversold)
        %B > 1: Price above upper band (overbought)
        %B = 0.5: Price at middle band
        """
        band_width = upper - lower
        if band_width == 0:
            return 0.5
        return (price - lower) / band_width

    def _get_price_position(self, price: float, upper: float, lower: float) -> str:
        """Get descriptive price position relative to bands"""
        percent_b = self._calculate_percent_b(price, upper, lower)
        
        if percent_b <= 0:
            return "below_lower_band"
        elif percent_b < 0.2:
            return "near_lower_band"
        elif percent_b < 0.4:
            return "lower_half"
        elif percent_b < 0.6:
            return "middle"
        elif percent_b < 0.8:
            return "upper_half"
        elif percent_b < 1.0:
            return "near_upper_band"
        else:
            return "above_upper_band"

    def _generate_signal(
        self,
        price: float,
        upper_band: float,
        lower_band: float,
        rsi: float,
        percent_b: float,
    ) -> Tuple[SignalType, float]:
        """Generate trading signal based on Bollinger Bands and RSI"""
        
        require_rsi = self.get_parameter("require_rsi_confirmation")
        rsi_oversold = self.get_parameter("rsi_oversold")
        rsi_overbought = self.get_parameter("rsi_overbought")
        touch_threshold = self.get_parameter("band_touch_threshold")
        
        # Check for lower band touch (potential BUY)
        lower_touch = percent_b <= touch_threshold
        
        # Check for upper band touch (potential SELL)
        upper_touch = percent_b >= (1.0 - touch_threshold)
        
        # RSI confirmation
        rsi_confirms_buy = rsi <= rsi_oversold
        rsi_confirms_sell = rsi >= rsi_overbought
        
        # Generate signals
        if lower_touch:
            if require_rsi and not rsi_confirms_buy:
                # Band touch but RSI doesn't confirm - weak signal
                return SignalType.HOLD, 0.4
            
            # Strong BUY signal: lower band touch + RSI confirms
            confidence = 0.7 if rsi_confirms_buy else 0.55
            # Boost confidence if price is actually below band
            if percent_b < 0:
                confidence = min(0.9, confidence + 0.15)
            return SignalType.BUY, confidence
        
        elif upper_touch:
            if require_rsi and not rsi_confirms_sell:
                # Band touch but RSI doesn't confirm - weak signal
                return SignalType.HOLD, 0.4
            
            # Strong SELL signal: upper band touch + RSI confirms
            confidence = 0.7 if rsi_confirms_sell else 0.55
            # Boost confidence if price is actually above band
            if percent_b > 1.0:
                confidence = min(0.9, confidence + 0.15)
            return SignalType.SELL, confidence
        
        else:
            # Price within bands - HOLD
            # Confidence based on how centered the price is
            distance_from_center = abs(percent_b - 0.5)
            confidence = 0.5 + (0.3 * (1 - distance_from_center * 2))
            return SignalType.HOLD, confidence

    def _calculate_levels(
        self,
        current_price: float,
        signal: SignalType,
        middle_band: float,
        upper_band: float,
        lower_band: float,
    ) -> Tuple[float, float, float]:
        """Calculate price target, stop loss, and take profit"""
        
        if signal == SignalType.BUY:
            # Target middle band (mean reversion)
            price_target = middle_band
            # Stop loss below lower band
            stop_loss = lower_band * 0.99
            # Take profit at or above middle band
            take_profit = middle_band + (middle_band - lower_band) * 0.5
            
        elif signal == SignalType.SELL:
            # Target middle band (mean reversion)
            price_target = middle_band
            # Stop loss above upper band
            stop_loss = upper_band * 1.01
            # Take profit at or below middle band
            take_profit = middle_band - (upper_band - middle_band) * 0.5
            
        else:
            price_target = None
            stop_loss = None
            take_profit = None
        
        return price_target, stop_loss, take_profit

    def get_risk_metrics(self, market_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate Bollinger-specific risk metrics"""
        base_metrics = super().get_risk_metrics(market_data)
        
        if len(market_data) >= self.requires_minimum_data():
            try:
                closes = [float(candle["close"]) for candle in market_data]
                upper, middle, lower = self._calculate_bollinger_bands(closes)
                
                # Bandwidth indicates volatility
                bandwidth = (upper - lower) / middle
                
                # Narrow bands often precede breakouts (higher risk)
                # Wide bands indicate high volatility
                base_metrics["bandwidth"] = bandwidth
                base_metrics["volatility_risk"] = min(bandwidth * 10, 1.0)
                
                # %B indicates extreme positions
                percent_b = self._calculate_percent_b(closes[-1], upper, lower)
                if percent_b < 0 or percent_b > 1:
                    base_metrics["extreme_position_risk"] = 0.8
                elif percent_b < 0.1 or percent_b > 0.9:
                    base_metrics["extreme_position_risk"] = 0.5
                else:
                    base_metrics["extreme_position_risk"] = 0.2
                    
            except Exception:
                pass
        
        return base_metrics
