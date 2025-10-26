"""
Combined Strategy

Combines multiple indicators (RSI, MACD) to generate more robust trading signals
"""
from typing import Dict, List, Any, Tuple
from .base_strategy import BaseStrategy, StrategyResult, SignalType
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy


class CombinedStrategy(BaseStrategy):
    """
    Combined trading strategy using multiple indicators
    
    Uses RSI and MACD strategies and combines their signals with configurable weights
    and agreement requirements for more robust decision making.
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        # Initialize sub-strategies BEFORE calling super().__init__()
        # because get_parameters() (called by parent) needs these to exist
        try:
            param_dict = parameters or {}
            rsi_params = {k.replace('rsi_', '', 1): v for k, v in param_dict.items() if k.startswith('rsi_')}
            macd_params = {k.replace('macd_', '', 1): v for k, v in param_dict.items() if k.startswith('macd_')}
            
            # Initialize sub-strategies with extracted parameters
            self.rsi_strategy = RSIStrategy(rsi_params if rsi_params else None)
            self.macd_strategy = MACDStrategy(macd_params if macd_params else None)
        except Exception as e:
            # Fallback: always set both sub-strategies to default
            self.rsi_strategy = RSIStrategy()
            self.macd_strategy = MACDStrategy()
        
        # Now call parent init, which will call get_parameters() and _validate_parameters()
        super().__init__(parameters)
    
    def get_name(self) -> str:
        return "combined"
    
    def get_description(self) -> str:
        return "Combined RSI and MACD strategy with configurable weighting and agreement rules"
    
    def get_parameters(self) -> Dict[str, Any]:
        params = {
            # Combination parameters
            'rsi_weight': {
                'default': 0.6,
                'type': float,
                'min': 0.0,
                'max': 1.0,
                'description': 'Weight for RSI signal (MACD weight = 1 - rsi_weight)'
            },
            'min_agreement_threshold': {
                'default': 0.5,
                'type': float,
                'min': 0.0,
                'max': 1.0,
                'description': 'Minimum agreement score to generate non-HOLD signal'
            },
            'require_direction_agreement': {
                'default': True,
                'type': bool,
                'description': 'Require both indicators to agree on BUY/SELL direction'
            },
            'confidence_boost_on_agreement': {
                'default': 0.2,
                'type': float,
                'min': 0.0,
                'max': 0.5,
                'description': 'Confidence boost when indicators agree'
            }
        }
        
        # Add RSI strategy parameters with prefix
        for param_name, param_config in self.rsi_strategy.get_parameters().items():
            params[f'rsi_{param_name}'] = param_config.copy()
            params[f'rsi_{param_name}']['description'] = f"RSI: {param_config['description']}"
        
        # Add MACD strategy parameters with prefix  
        for param_name, param_config in self.macd_strategy.get_parameters().items():
            params[f'macd_{param_name}'] = param_config.copy()
            params[f'macd_{param_name}']['description'] = f"MACD: {param_config['description']}"
        
        return params
    
    def requires_minimum_data(self) -> int:
        return max(self.rsi_strategy.requires_minimum_data(), 
                  self.macd_strategy.requires_minimum_data())
    
    def analyze(self, market_data: List[Dict[str, Any]], symbol: str = None) -> StrategyResult:
        """
        Analyze market data using combined RSI and MACD strategy
        
        Args:
            market_data: List of OHLCV candles
            symbol: Trading symbol (optional)
            
        Returns:
            StrategyResult with combined signal
        """
        if len(market_data) < self.requires_minimum_data():
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={'error': 'Insufficient data for combined strategy calculation'}
            )
        
        try:
            # Get signals from individual strategies
            rsi_result = self.rsi_strategy.analyze(market_data, symbol)
            macd_result = self.macd_strategy.analyze(market_data, symbol)
            
            # Combine signals
            combined_signal, combined_confidence = self._combine_signals(rsi_result, macd_result)
            
            # Combine indicators
            combined_indicators = {
                'rsi': rsi_result.indicators,
                'macd': macd_result.indicators,
                'agreement_score': self._calculate_agreement_score(rsi_result, macd_result)
            }
            
            # Calculate combined levels
            current_price = float(market_data[-1]['close'])
            price_target, stop_loss, take_profit = self._calculate_combined_levels(
                current_price, combined_signal, rsi_result, macd_result
            )
            
            return StrategyResult(
                signal=combined_signal,
                confidence=combined_confidence,
                price_target=price_target,
                stop_loss=stop_loss,
                take_profit=take_profit,
                indicators=combined_indicators,
                metadata={
                    'strategy': self.name,
                    'current_price': current_price,
                    'data_points': len(market_data),
                    'rsi_signal': rsi_result.signal.value,
                    'macd_signal': macd_result.signal.value,
                    'rsi_confidence': rsi_result.confidence,
                    'macd_confidence': macd_result.confidence
                }
            )
            
        except Exception as e:
            return StrategyResult(
                signal=SignalType.HOLD,
                confidence=0.0,
                metadata={'error': f'Combined strategy calculation failed: {str(e)}'}
            )
    
    def _combine_signals(self, rsi_result: StrategyResult, macd_result: StrategyResult) -> Tuple[SignalType, float]:
        """Combine RSI and MACD signals"""
        
        rsi_weight = self.get_parameter('rsi_weight')
        macd_weight = 1.0 - rsi_weight
        min_agreement = self.get_parameter('min_agreement_threshold')
        require_direction_agreement = self.get_parameter('require_direction_agreement')
        confidence_boost = self.get_parameter('confidence_boost_on_agreement')
        
        # Check for direction agreement if required
        if require_direction_agreement:
            if rsi_result.signal != macd_result.signal and rsi_result.signal != SignalType.HOLD and macd_result.signal != SignalType.HOLD:
                # Indicators disagree on direction - return HOLD
                combined_confidence = (rsi_result.confidence * rsi_weight + macd_result.confidence * macd_weight) * 0.5
                return SignalType.HOLD, combined_confidence
        
        # Calculate agreement score
        agreement_score = self._calculate_agreement_score(rsi_result, macd_result)
        
        # If agreement is too low, return HOLD
        if agreement_score < min_agreement:
            combined_confidence = (rsi_result.confidence * rsi_weight + macd_result.confidence * macd_weight) * 0.6
            return SignalType.HOLD, combined_confidence
        
        # Determine final signal based on weighted approach
        if rsi_result.signal == macd_result.signal:
            # Both indicators agree - use that signal
            final_signal = rsi_result.signal
            # Boost confidence when indicators agree
            base_confidence = rsi_result.confidence * rsi_weight + macd_result.confidence * macd_weight
            combined_confidence = min(0.95, base_confidence + confidence_boost)
        else:
            # Indicators disagree or one is HOLD - use weighted approach
            rsi_score = self._signal_to_score(rsi_result.signal) * rsi_result.confidence * rsi_weight
            macd_score = self._signal_to_score(macd_result.signal) * macd_result.confidence * macd_weight
            
            total_score = rsi_score + macd_score
            
            if total_score > 0.1:
                final_signal = SignalType.BUY
            elif total_score < -0.1:
                final_signal = SignalType.SELL
            else:
                final_signal = SignalType.HOLD
            
            # Combined confidence
            combined_confidence = (rsi_result.confidence * rsi_weight + macd_result.confidence * macd_weight) * agreement_score
        
        return final_signal, combined_confidence
    
    def _signal_to_score(self, signal: SignalType) -> float:
        """Convert signal to numeric score"""
        if signal == SignalType.BUY:
            return 1.0
        elif signal == SignalType.SELL:
            return -1.0
        else:  # HOLD
            return 0.0
    
    def _calculate_agreement_score(self, rsi_result: StrategyResult, macd_result: StrategyResult) -> float:
        """Calculate agreement score between indicators"""
        
        # Convert signals to scores
        rsi_score = self._signal_to_score(rsi_result.signal)
        macd_score = self._signal_to_score(macd_result.signal)
        
        # If both are HOLD, moderate agreement
        if rsi_score == 0 and macd_score == 0:
            return 0.6
        
        # If one is HOLD, partial agreement based on the other's confidence
        if rsi_score == 0:
            return 0.5 + macd_result.confidence * 0.3
        if macd_score == 0:
            return 0.5 + rsi_result.confidence * 0.3
        
        # Both have directional signals
        if rsi_score * macd_score > 0:  # Same direction
            # Agreement score based on confidence levels
            min_confidence = min(rsi_result.confidence, macd_result.confidence)
            max_confidence = max(rsi_result.confidence, macd_result.confidence)
            return 0.7 + (min_confidence + max_confidence) * 0.15
        else:  # Opposite directions
            # Disagreement - low score
            return 0.2
    
    def _calculate_combined_levels(self, current_price: float, signal: SignalType, 
                                 rsi_result: StrategyResult, macd_result: StrategyResult) -> Tuple:
        """Calculate combined price target, stop loss, and take profit levels"""
        
        if signal == SignalType.HOLD:
            return None, None, None
        
        rsi_weight = self.get_parameter('rsi_weight')
        macd_weight = 1.0 - rsi_weight
        
        # Weighted average of target prices (if both strategies provide them)
        price_target = None
        stop_loss = None
        take_profit = None
        
        if rsi_result.price_target is not None and macd_result.price_target is not None:
            price_target = (rsi_result.price_target * rsi_weight + 
                          macd_result.price_target * macd_weight)
        elif rsi_result.price_target is not None:
            price_target = rsi_result.price_target
        elif macd_result.price_target is not None:
            price_target = macd_result.price_target
        
        if rsi_result.stop_loss is not None and macd_result.stop_loss is not None:
            stop_loss = (rsi_result.stop_loss * rsi_weight + 
                        macd_result.stop_loss * macd_weight)
        elif rsi_result.stop_loss is not None:
            stop_loss = rsi_result.stop_loss
        elif macd_result.stop_loss is not None:
            stop_loss = macd_result.stop_loss
        
        if rsi_result.take_profit is not None and macd_result.take_profit is not None:
            take_profit = (rsi_result.take_profit * rsi_weight + 
                          macd_result.take_profit * macd_weight)
        elif rsi_result.take_profit is not None:
            take_profit = rsi_result.take_profit
        elif macd_result.take_profit is not None:
            take_profit = macd_result.take_profit
        
        return price_target, stop_loss, take_profit
    
    def get_risk_metrics(self, market_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate combined risk metrics"""
        base_metrics = super().get_risk_metrics(market_data)
        
        if len(market_data) >= self.requires_minimum_data():
            try:
                # Get risk metrics from individual strategies
                rsi_metrics = self.rsi_strategy.get_risk_metrics(market_data)
                macd_metrics = self.macd_strategy.get_risk_metrics(market_data)
                
                # Combine risk metrics
                rsi_weight = self.get_parameter('rsi_weight')
                macd_weight = 1.0 - rsi_weight
                
                combined_risk = (rsi_metrics.get('risk_level', 0.5) * rsi_weight + 
                               macd_metrics.get('risk_level', 0.5) * macd_weight)
                
                base_metrics['combined_risk'] = combined_risk
                base_metrics['rsi_metrics'] = rsi_metrics
                base_metrics['macd_metrics'] = macd_metrics
                
            except Exception:
                base_metrics['combined_risk'] = 0.5
        
        return base_metrics