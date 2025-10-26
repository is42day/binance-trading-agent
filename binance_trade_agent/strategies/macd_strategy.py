"""
MACD (Moving Average Convergence Divergence) Trading Strategy

Uses MACD indicator to generate buy/sell signals based on line crossovers and histogram
"""
from typing import Dict, List, Any, Tuple
from .base_strategy import BaseStrategy, StrategyResult, SignalType


class MACDStrategy(BaseStrategy):
    """
    MACD-based trading strategy
    
    Generates:
    - BUY signals when MACD line crosses above signal line (bullish crossover)
    - SELL signals when MACD line crosses below signal line (bearish crossover)
    - HOLD signals otherwise
    """
    
    def get_name(self) -> str:
        return "macd"
    
    def get_description(self) -> str:
        return "MACD (Moving Average Convergence Divergence) trend-following strategy"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            'fast_period': {
                'default': 12,
                'type': int,
                'min': 5,
                'max': 50,
                'description': 'Fast EMA period'
            },
            'slow_period': {
                'default': 26,
                'type': int,
                'min': 10,
                'max': 100,
                'description': 'Slow EMA period'
            },
            'signal_period': {
                'default': 9,
                'type': int,
                'min': 3,
                'max': 30,
                'description': 'Signal line EMA period'
            },
            'histogram_threshold': {
                'default': 0.0,
                'type': float,
                'min': -1.0,
                'max': 1.0,
                'description': 'Minimum histogram value for signal confirmation'
            },
            'require_histogram_confirmation': {
                'default': True,
                'type': bool,
                'description': 'Require histogram confirmation for signals'
            }
        }
    
    def requires_minimum_data(self) -> int:
        slow_period = self.get_parameter('slow_period')
        signal_period = self.get_parameter('signal_period')
        return slow_period + signal_period + 5  # Extra buffer for EMA calculation
    
    def analyze(self, market_data: List[Dict[str, Any]], symbol: str = None) -> StrategyResult:
        """
        Analyze market data using MACD strategy
        
        Args:
            market_data: List of OHLCV candles
            symbol: Trading symbol (optional)
            
        Returns:
            StrategyResult with MACD-based signal
        """
        if len(market_data) < self.requires_minimum_data():
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={'error': 'Insufficient data for MACD calculation'}
            )
        
        try:
            # Extract closing prices
            closes = [float(candle['close']) for candle in market_data]
            
            # Calculate MACD components
            macd_line, signal_line, histogram = self._calculate_macd(closes)
            
            # Generate signal
            signal, confidence = self._generate_signal(macd_line, signal_line, histogram)
            
            # Calculate support levels
            current_price = closes[-1]
            price_target, stop_loss, take_profit = self._calculate_levels(
                current_price, signal, histogram
            )
            
            return StrategyResult(
                signal=signal,
                confidence=confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                indicators={
                    'macd_line': macd_line,
                    'signal_line': signal_line,
                    'histogram': histogram,
                    'macd_above_signal': macd_line > signal_line,
                    'histogram_positive': histogram > 0
                },
                metadata={
                    'strategy': self.name,
                    'current_price': current_price,
                    'data_points': len(market_data)
                }
            )
            
        except Exception as e:
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={'error': f'MACD calculation failed: {str(e)}'}
            )
    
    def _calculate_ema(self, data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            raise ValueError(f"Need at least {period} data points for EMA calculation")
        
        k = 2.0 / (period + 1.0)
        ema = [data[0]]  # Start with first value
        
        for price in data[1:]:
            ema.append(price * k + ema[-1] * (1 - k))
        
        return ema
    
    def _calculate_macd(self, closes: List[float]) -> Tuple[float, float, float]:
        """Calculate MACD line, signal line, and histogram"""
        fast_period = self.get_parameter('fast_period')
        slow_period = self.get_parameter('slow_period')
        signal_period = self.get_parameter('signal_period')
        
        # Calculate EMAs
        fast_ema = self._calculate_ema(closes, fast_period)
        slow_ema = self._calculate_ema(closes, slow_period)
        
        # MACD line = Fast EMA - Slow EMA
        # Align arrays (slow EMA starts later)
        start_idx = len(fast_ema) - len(slow_ema)
        macd_values = [fast_ema[i + start_idx] - slow_ema[i] for i in range(len(slow_ema))]
        
        # Signal line = EMA of MACD line
        signal_values = self._calculate_ema(macd_values, signal_period)
        
        # Histogram = MACD line - Signal line
        # Align arrays again
        start_idx = len(macd_values) - len(signal_values)
        histogram_values = [macd_values[i + start_idx] - signal_values[i] for i in range(len(signal_values))]
        
        # Return the most recent values
        return macd_values[-1], signal_values[-1], histogram_values[-1]
    
    def _generate_signal(self, macd_line: float, signal_line: float, histogram: float) -> Tuple[SignalType, float]:
        """Generate trading signal based on MACD values"""
        
        histogram_threshold = self.get_parameter('histogram_threshold')
        require_histogram = self.get_parameter('require_histogram_confirmation')
        
        # Determine basic signal direction
        if macd_line > signal_line:
            base_signal = SignalType.BUY
            signal_strength = macd_line - signal_line
        elif macd_line < signal_line:
            base_signal = SignalType.SELL
            signal_strength = abs(macd_line - signal_line)
        else:
            return SignalType.HOLD, 0.3
        
        # Check histogram confirmation if required
        if require_histogram:
            if base_signal == SignalType.BUY and histogram <= histogram_threshold:
                return SignalType.HOLD, 0.4
            elif base_signal == SignalType.SELL and histogram >= -histogram_threshold:
                return SignalType.HOLD, 0.4
        
        # Calculate confidence based on signal strength and histogram
        base_confidence = min(0.8, signal_strength * 10)  # Scale signal strength
        
        # Boost confidence if histogram confirms the signal strongly
        if abs(histogram) > abs(histogram_threshold) * 2:
            base_confidence = min(0.9, base_confidence * 1.2)
        
        # Ensure minimum confidence
        confidence = max(0.5, base_confidence)
        
        return base_signal, confidence
    
    def _calculate_levels(self, current_price: float, signal: SignalType, histogram: float) -> Tuple:
        """Calculate price target, stop loss, and take profit levels"""
        
        # Use histogram magnitude to determine target distances
        histogram_factor = min(abs(histogram) * 100, 0.05)  # Cap at 5%
        base_target = 0.02  # 2% base target
        
        if signal == SignalType.BUY:
            price_target = current_price * (1 + base_target + histogram_factor)
            stop_loss = current_price * 0.985    # 1.5% stop loss
            take_profit = current_price * (1 + (base_target + histogram_factor) * 2)
        elif signal == SignalType.SELL:
            price_target = current_price * (1 - base_target - histogram_factor)
            stop_loss = current_price * 1.015    # 1.5% stop loss
            take_profit = current_price * (1 - (base_target + histogram_factor) * 2)
        else:
            price_target = None
            stop_loss = None
            take_profit = None
        
        return price_target, stop_loss, take_profit
    
    def get_risk_metrics(self, market_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate MACD-specific risk metrics"""
        base_metrics = super().get_risk_metrics(market_data)
        
        if len(market_data) >= self.requires_minimum_data():
            try:
                closes = [float(candle['close']) for candle in market_data]
                macd_line, signal_line, histogram = self._calculate_macd(closes)
                
                # MACD-based risk assessment
                # Higher divergence between MACD and signal indicates higher volatility
                divergence = abs(macd_line - signal_line)
                normalized_divergence = min(divergence * 100, 1.0)  # Normalize and cap
                
                # Histogram magnitude indicates momentum strength/risk
                histogram_risk = min(abs(histogram) * 50, 1.0)
                
                base_metrics['macd_divergence_risk'] = normalized_divergence
                base_metrics['macd_momentum_risk'] = histogram_risk
                base_metrics['macd_line'] = macd_line
                base_metrics['signal_line'] = signal_line
                base_metrics['histogram'] = histogram
                
            except Exception:
                base_metrics['macd_divergence_risk'] = 0.5
                base_metrics['macd_momentum_risk'] = 0.5
        
        return base_metrics