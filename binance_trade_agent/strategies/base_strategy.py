"""
IMPORTANT: Always import SignalType directly from this file, not from the strategies package.
"""

"""
Base Strategy Interface

Defines the contract that all trading strategies must implement
"""
from abc import ABC, abstractmethod  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import datetime  # noqa: E402
from enum import Enum  # noqa: E402
from typing import Any, Dict, List, Optional, Tuple  # noqa: E402


class SignalType(Enum):
    """Trading signal types"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategyResult:
    """Result of strategy analysis"""

    signal: SignalType
    confidence: float  # 0.0 to 1.0
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    indicators: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.indicators is None:
            self.indicators = {}
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "signal": self.signal.value,
            "confidence": self.confidence,
            "price_target": self.price_target,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "indicators": self.indicators,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies

    All strategies must implement:
    - analyze(): Main strategy logic
    - get_name(): Strategy identifier
    - get_description(): Human readable description
    - get_parameters(): Strategy configuration parameters
    """

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy with parameters

        Args:
            parameters: Strategy-specific configuration parameters
        """
        self.parameters = parameters or {}
        self.name = self.get_name()
        self.description = self.get_description()

        # Validate parameters on initialization
        self._validate_parameters()

    @abstractmethod
    def analyze(self, market_data: List[Dict[str, Any]], symbol: str = None) -> StrategyResult:
        """
        Analyze market data and generate trading signal

        Args:
            market_data: List of OHLCV candles with keys: open, high, low, close, volume
            symbol: Trading symbol (optional, for symbol-specific logic)

        Returns:
            StrategyResult with signal, confidence, and supporting data
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return unique strategy name"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return human-readable strategy description"""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return strategy parameters with defaults and descriptions"""
        pass

    def _validate_parameters(self):
        """Validate strategy parameters"""
        required_params = self.get_parameters()
        for param_name, param_config in required_params.items():
            if param_config.get("required", False) and param_name not in self.parameters:
                raise ValueError(
                    f"Required parameter '{param_name}' missing for strategy '{self.name}'"
                )

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get parameter value with fallback to default"""
        param_config = self.get_parameters().get(name, {})
        return self.parameters.get(name, param_config.get("default", default))

    def set_parameter(self, name: str, value: Any):
        """Set parameter value with validation"""
        param_config = self.get_parameters().get(name)
        if param_config is None:
            raise ValueError(f"Unknown parameter '{name}' for strategy '{self.name}'")

        # Type validation if specified
        expected_type = param_config.get("type")
        if expected_type and not isinstance(value, expected_type):
            try:
                value = expected_type(value)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Parameter '{name}' must be of type {expected_type.__name__}"
                ) from e

        # Range validation if specified
        min_val = param_config.get("min")
        max_val = param_config.get("max")
        if min_val is not None and value < min_val:
            raise ValueError(f"Parameter '{name}' must be >= {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"Parameter '{name}' must be <= {max_val}")

        self.parameters[name] = value

    def requires_minimum_data(self) -> int:
        """Return minimum number of candles required for analysis"""
        return 1

    def supports_symbol(self, symbol: str) -> bool:
        """Check if strategy supports given symbol"""
        return True  # Default: support all symbols

    def check_volume_confirmation(
        self,
        market_data: List[Dict[str, Any]],
        volume_multiplier: float = 1.5,
        lookback_period: int = 20
    ) -> Tuple[bool, float]:
        """
        Check if current volume confirms the signal.

        Higher volume = more reliable signals
        Returns (is_confirmed, volume_ratio)

        Args:
            market_data: OHLCV candle data
            volume_multiplier: Minimum ratio vs average (default 1.5x)
            lookback_period: Periods for average calculation

        Returns:
            Tuple of (confirmation_status, volume_ratio)
        """
        if not market_data or len(market_data) < lookback_period:
            return True, 1.0  # Not enough data, don't block

        try:
            # Extract volumes
            volumes = []
            for candle in market_data:
                vol = candle.get("volume") or candle.get("vol") or candle.get("v")
                if vol is not None:
                    volumes.append(float(vol))

            if len(volumes) < lookback_period:
                return True, 1.0  # Not enough volume data

            current_volume = volumes[-1]
            avg_volume = sum(volumes[-lookback_period-1:-1]) / lookback_period

            if avg_volume == 0:
                return True, 1.0

            volume_ratio = current_volume / avg_volume
            is_confirmed = volume_ratio >= volume_multiplier

            return is_confirmed, volume_ratio

        except Exception:
            return True, 1.0  # On error, don't block

    def calculate_atr(
        self,
        market_data: List[Dict[str, Any]],
        period: int = 14
    ) -> float:
        """
        Calculate Average True Range (ATR) for volatility-based stops.

        ATR measures volatility by decomposing the entire range of an asset price
        for a given period. Used for dynamic stop-loss placement.

        Args:
            market_data: OHLCV candle data
            period: ATR period (default 14)

        Returns:
            ATR value
        """
        if len(market_data) < period + 1:
            return 0.0

        try:
            true_ranges = []

            for i in range(1, len(market_data)):
                high = float(market_data[i].get("high", market_data[i]["close"]))
                low = float(market_data[i].get("low", market_data[i]["close"]))
                prev_close = float(market_data[i-1]["close"])

                # True Range = max(high-low, |high-prev_close|, |low-prev_close|)
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)

            # ATR is the moving average of True Range
            if len(true_ranges) < period:
                return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

            return sum(true_ranges[-period:]) / period

        except Exception:
            return 0.0

    def calculate_atr_stops(
        self,
        current_price: float,
        atr: float,
        signal: "SignalType",
        atr_multiplier: float = 2.0,
        take_profit_multiplier: float = 3.0
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate ATR-based stop loss and take profit levels.

        Args:
            current_price: Current asset price
            atr: ATR value
            signal: Trading signal (BUY/SELL)
            atr_multiplier: Multiplier for stop loss distance (default 2x ATR)
            take_profit_multiplier: Multiplier for take profit (default 3x ATR)

        Returns:
            Tuple of (stop_loss, take_profit) or (None, None) for HOLD
        """
        if signal.value == "HOLD" or atr == 0:
            return None, None

        if signal.value == "BUY":
            stop_loss = current_price - (atr * atr_multiplier)
            take_profit = current_price + (atr * take_profit_multiplier)
        else:  # SELL
            stop_loss = current_price + (atr * atr_multiplier)
            take_profit = current_price - (atr * take_profit_multiplier)

        return stop_loss, take_profit

    def get_risk_metrics(self, market_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate risk metrics for the strategy"""
        if not market_data:
            return {"volatility": 0.0, "risk_level": 0.5}

        # Calculate simple volatility
        closes = [float(candle["close"]) for candle in market_data[-20:]]  # Last 20 periods
        if len(closes) < 2:
            return {"volatility": 0.0, "risk_level": 0.5}

        # Simple volatility calculation
        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
        volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5

        # Risk level based on volatility
        risk_level = min(volatility * 10, 1.0)  # Scale and cap at 1.0

        return {"volatility": volatility, "risk_level": risk_level}

    def calculate_ema(
        self,
        market_data: List[Dict[str, Any]],
        period: int = 20
    ) -> Optional[float]:
        """
        Calculate Exponential Moving Average.

        Args:
            market_data: OHLCV candle data
            period: EMA period

        Returns:
            EMA value or None if insufficient data
        """
        if len(market_data) < period:
            return None

        try:
            closes = [float(candle["close"]) for candle in market_data]

            # Calculate EMA using the standard formula
            multiplier = 2 / (period + 1)

            # Start with SMA for first EMA value
            ema = sum(closes[:period]) / period

            # Calculate EMA for remaining values
            for i in range(period, len(closes)):
                ema = (closes[i] * multiplier) + (ema * (1 - multiplier))

            return ema

        except Exception:
            return None

    def calculate_ema_series(
        self,
        market_data: List[Dict[str, Any]],
        period: int = 20
    ) -> List[float]:
        """
        Calculate EMA series for all data points.

        Args:
            market_data: OHLCV candle data
            period: EMA period

        Returns:
            List of EMA values
        """
        if len(market_data) < period:
            return []

        try:
            closes = [float(candle["close"]) for candle in market_data]
            multiplier = 2 / (period + 1)

            # Start with SMA
            ema_values = []
            ema = sum(closes[:period]) / period
            ema_values.extend([ema] * period)  # Fill initial values with first EMA

            # Calculate EMA for remaining values
            for i in range(period, len(closes)):
                ema = (closes[i] * multiplier) + (ema * (1 - multiplier))
                ema_values.append(ema)

            return ema_values

        except Exception:
            return []

    def get_trend_filter(
        self,
        market_data: List[Dict[str, Any]],
        fast_period: int = 50,
        slow_period: int = 200
    ) -> Dict[str, Any]:
        """
        Calculate trend filter using EMA crossover (50/200 EMA).

        A classic trend-following filter:
        - BULLISH: 50 EMA > 200 EMA (uptrend)
        - BEARISH: 50 EMA < 200 EMA (downtrend)
        - NEUTRAL: Not enough data or EMAs are very close

        Args:
            market_data: OHLCV candle data
            fast_period: Fast EMA period (default 50)
            slow_period: Slow EMA period (default 200)

        Returns:
            Dict with trend info:
            - trend: "BULLISH", "BEARISH", or "NEUTRAL"
            - ema_fast: Current fast EMA value
            - ema_slow: Current slow EMA value
            - trend_strength: How far apart the EMAs are (as % of price)
            - allows_buy: True if trend allows buying
            - allows_sell: True if trend allows selling
        """
        if len(market_data) < slow_period:
            return {
                "trend": "NEUTRAL",
                "ema_fast": None,
                "ema_slow": None,
                "trend_strength": 0.0,
                "allows_buy": True,  # Allow both when no trend data
                "allows_sell": True,
                "reason": "Insufficient data for trend analysis"
            }

        try:
            ema_fast = self.calculate_ema(market_data, fast_period)
            ema_slow = self.calculate_ema(market_data, slow_period)

            if ema_fast is None or ema_slow is None:
                return {
                    "trend": "NEUTRAL",
                    "ema_fast": None,
                    "ema_slow": None,
                    "trend_strength": 0.0,
                    "allows_buy": True,
                    "allows_sell": True,
                    "reason": "EMA calculation failed"
                }

            current_price = float(market_data[-1]["close"])

            # Calculate trend strength as percentage difference
            trend_strength = abs(ema_fast - ema_slow) / current_price * 100

            # Determine trend direction
            # Using a small threshold (0.1%) to avoid noise
            threshold = current_price * 0.001  # 0.1% of price

            if ema_fast > ema_slow + threshold:
                trend = "BULLISH"
                allows_buy = True
                allows_sell = False  # Don't short in uptrend
            elif ema_fast < ema_slow - threshold:
                trend = "BEARISH"
                allows_buy = False  # Don't buy in downtrend
                allows_sell = True
            else:
                trend = "NEUTRAL"
                allows_buy = True
                allows_sell = True

            return {
                "trend": trend,
                "ema_fast": round(ema_fast, 2),
                "ema_slow": round(ema_slow, 2),
                "trend_strength": round(trend_strength, 3),
                "allows_buy": allows_buy,
                "allows_sell": allows_sell,
                "reason": f"50 EMA {'above' if ema_fast > ema_slow else 'below'} 200 EMA"
            }

        except Exception as e:
            return {
                "trend": "NEUTRAL",
                "ema_fast": None,
                "ema_slow": None,
                "trend_strength": 0.0,
                "allows_buy": True,
                "allows_sell": True,
                "reason": f"Error: {str(e)}"
            }

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', parameters={self.parameters})>"
