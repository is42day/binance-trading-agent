"""
RSI (Relative Strength Index) Trading Strategy

Uses RSI indicator to generate buy/sell signals based on overbought/oversold conditions
"""
from typing import Dict, List, Any
from .base_strategy import BaseStrategy, StrategyResult, SignalType


class RSIStrategy(BaseStrategy):
    """
    RSI-based trading strategy
    
    Generates:
    - BUY signals when RSI < oversold threshold (default: 30)
    - SELL signals when RSI > overbought threshold (default: 70)
    - HOLD signals otherwise
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        super().__init__(parameters)
        # Only raise ValueError for user-provided parameters that are out of bounds
        params = self.get_parameters()
        if parameters:
            for key, value in parameters.items():
                config = params.get(key)
                if config:
                    if 'min' in config and value < config['min']:
                        raise ValueError(f"Parameter '{key}' below minimum: {value} < {config['min']}")
                    if 'max' in config and value > config['max']:
                        raise ValueError(f"Parameter '{key}' above maximum: {value} > {config['max']}")

    def get_name(self) -> str:
        return "rsi"
    
    def get_description(self) -> str:
        return "RSI (Relative Strength Index) momentum oscillator strategy"
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            'period': {
                'default': 14,
                'type': int,
                'min': 2,
                'max': 50,
                'description': 'RSI calculation period'
            },
            'overbought': {
                'default': 70,
                'type': int,
                'min': 50,
                'max': 95,
                'description': 'RSI overbought threshold'
            },
            'oversold': {
                'default': 30,
                'type': int,
                'min': 5,
                'max': 50,
                'description': 'RSI oversold threshold'
            },
            'extreme_overbought': {
                'default': 80,
                'type': int,
                'min': 70,
                'max': 95,
                'description': 'Extreme overbought threshold for high confidence signals'
            },
            'extreme_oversold': {
                'default': 20,
                'type': int,
                'min': 5,
                'max': 30,
                'description': 'Extreme oversold threshold for high confidence signals'
            }
        }
    
    def requires_minimum_data(self) -> int:
        return self.get_parameter('period') + 1
    
    def analyze(self, market_data: List[Dict[str, Any]], symbol: str = None) -> StrategyResult:
        """
        Analyze market data using RSI strategy
        
        Args:
            market_data: List of OHLCV candles
            symbol: Trading symbol (optional)
            
        Returns:
            StrategyResult with RSI-based signal
        """
        if len(market_data) < self.requires_minimum_data():
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={'error': 'Insufficient data for RSI calculation'}
            )
        
        try:
            # Extract closing prices
            closes = [float(candle['close']) for candle in market_data]
            
            # Calculate RSI
            rsi_value = self._calculate_rsi(closes)
            
            # Get thresholds
            oversold = self.get_parameter('oversold')
            overbought = self.get_parameter('overbought')
            extreme_oversold = self.get_parameter('extreme_oversold')
            extreme_overbought = self.get_parameter('extreme_overbought')
            
            # Generate signal
            signal, confidence = self._generate_signal(
                rsi_value, oversold, overbought, extreme_oversold, extreme_overbought
            )
            
            # Calculate support/resistance levels
            current_price = closes[-1]
            price_target, stop_loss, take_profit = self._calculate_levels(
                current_price, signal, rsi_value
            )
            
            return StrategyResult(
                signal=signal,
                confidence=confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                indicators={
                    'rsi': rsi_value,
                    'rsi_oversold': oversold,
                    'rsi_overbought': overbought
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
                metadata={'error': f'RSI calculation failed: {str(e)}'}
            )
    
    def _calculate_rsi(self, closes: List[float]) -> float:
        """Calculate RSI value"""
        period = self.get_parameter('period')
        
        if len(closes) < period + 1:
            raise ValueError(f"Need at least {period + 1} data points for RSI calculation")
        
        # Calculate price changes
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # Calculate initial average gain and loss
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        # Handle edge case where avg_loss is 0
        if avg_loss == 0:
            return 100.0
        
        # Calculate RSI
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi
    
    def _generate_signal(self, rsi: float, oversold: int, overbought: int, 
                        extreme_oversold: int, extreme_overbought: int) -> tuple:
        """Generate trading signal based on RSI value"""
        # Ensure neutral zone is strictly between oversold and overbought
        if rsi <= extreme_oversold:
            signal = SignalType.BUY
            confidence = min(0.9, (extreme_oversold - rsi) / extreme_oversold + 0.6)
        elif rsi < oversold:
            signal = SignalType.BUY
            confidence = min(0.8, (oversold - rsi) / oversold + 0.4)
        elif rsi > extreme_overbought:
            signal = SignalType.SELL
            confidence = min(0.9, (rsi - extreme_overbought) / (100 - extreme_overbought) + 0.6)
        elif rsi > overbought:
            signal = SignalType.SELL
            confidence = min(0.8, (rsi - overbought) / (100 - overbought) + 0.4)
        else:
            signal = SignalType.HOLD
            confidence = max(0.1, 1.0 - abs(rsi - 50) / 50)
        return signal, confidence
    
    def _calculate_levels(self, current_price: float, signal: SignalType, rsi: float) -> tuple:
        """Calculate price target, stop loss, and take profit levels"""
        
        # Basic percentage-based levels (can be enhanced with more sophisticated logic)
        if signal == SignalType.BUY:
            # For buy signals, set target above current price
            price_target = current_price * 1.02  # 2% target
            stop_loss = current_price * 0.98     # 2% stop loss
            take_profit = current_price * 1.05   # 5% take profit
        elif signal == SignalType.SELL:
            # For sell signals, set target below current price
            price_target = current_price * 0.98  # 2% target
            stop_loss = current_price * 1.02     # 2% stop loss
            take_profit = current_price * 0.95   # 5% take profit
        else:
            # Hold signal - no specific targets
            price_target = None
            stop_loss = None
            take_profit = None
        
        return price_target, stop_loss, take_profit
    
    def get_risk_metrics(self, market_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate RSI-specific risk metrics"""
        base_metrics = super().get_risk_metrics(market_data)
        
        if len(market_data) >= self.requires_minimum_data():
            try:
                closes = [float(candle['close']) for candle in market_data]
                rsi = self._calculate_rsi(closes)
                
                # RSI-based risk assessment
                # Extreme RSI values indicate higher risk of reversal
                if rsi > 80 or rsi < 20:
                    rsi_risk = 0.8  # High risk
                elif rsi > 70 or rsi < 30:
                    rsi_risk = 0.6  # Medium risk
                else:
                    rsi_risk = 0.3  # Low risk
                
                base_metrics['rsi_risk'] = rsi_risk
                base_metrics['rsi_value'] = rsi
                
            except Exception:
                base_metrics['rsi_risk'] = 0.5
                base_metrics['rsi_value'] = 50.0
        
        return base_metrics