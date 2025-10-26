"""
Strategy Manager

Manages multiple trading strategies, handles strategy selection, execution, and comparison
"""
from typing import Dict, List, Any, Optional, Type
import json
import logging
from datetime import datetime
from .base_strategy import BaseStrategy, StrategyResult, SignalType
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy
from .combined_strategy import CombinedStrategy


class StrategyManager:
    """
    Manages multiple trading strategies with support for:
    - Strategy registration and discovery
    - Strategy execution and comparison
    - Performance tracking
    - Dynamic strategy switching
    """
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_classes: Dict[str, Type[BaseStrategy]] = {
            'rsi': RSIStrategy,
            'macd': MACDStrategy,
            'combined': CombinedStrategy
        }
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Default strategies with standard parameters
        self._initialize_default_strategies()
    
    def _initialize_default_strategies(self):
        """Initialize default strategy instances"""
        try:
            self.register_strategy('rsi_default', RSIStrategy())
        except Exception as e:
            self.logger.error(f"Failed to register rsi_default: {str(e)}")
        try:
            self.register_strategy('macd_default', MACDStrategy())
        except Exception as e:
            self.logger.error(f"Failed to register macd_default: {str(e)}")
        try:
            self.register_strategy('combined_default', CombinedStrategy())
        except Exception as e:
            self.logger.error(f"Failed to register combined_default: {str(e)}")
        try:
            self.register_strategy('rsi_aggressive', RSIStrategy({
                'overbought': 65,
                'oversold': 35,
                'extreme_overbought': 75,
                'extreme_oversold': 25
            }))
        except Exception as e:
            self.logger.error(f"Failed to register rsi_aggressive: {str(e)}")
        try:
            self.register_strategy('rsi_conservative', RSIStrategy({
                'overbought': 75,
                'oversold': 25,
                'extreme_overbought': 85,
                'extreme_oversold': 15
            }))
        except Exception as e:
            self.logger.error(f"Failed to register rsi_conservative: {str(e)}")
        self.logger.info(f"Initialized {len(self.strategies)} default strategies")
    
    def register_strategy(self, name: str, strategy: BaseStrategy) -> bool:
        """
        Register a strategy instance
        
        Args:
            name: Unique strategy name
            strategy: Strategy instance
            
        Returns:
            True if registered successfully
        """
        try:
            if not isinstance(strategy, BaseStrategy):
                raise ValueError(f"Strategy must inherit from BaseStrategy")
            
            self.strategies[name] = strategy
            self.performance_history[name] = []
            
            self.logger.info(f"Registered strategy: {name} ({strategy.get_name()})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register strategy {name}: {str(e)}")
            return False
    
    def create_strategy(self, strategy_type: str, name: str, parameters: Dict[str, Any] = None) -> bool:
        """
        Create and register a new strategy instance
        
        Args:
            strategy_type: Type of strategy ('rsi', 'macd', 'combined')
            name: Unique name for this strategy instance
            parameters: Strategy parameters
            
        Returns:
            True if created successfully
        """
        try:
            if strategy_type not in self.strategy_classes:
                raise ValueError(f"Unknown strategy type: {strategy_type}")
            
            strategy_class = self.strategy_classes[strategy_type]
            strategy = strategy_class(parameters or {})
            
            return self.register_strategy(name, strategy)
            
        except Exception as e:
            self.logger.error(f"Failed to create strategy {name}: {str(e)}")
            return False
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get strategy by name"""
        return self.strategies.get(name)
    
    def list_strategies(self) -> Dict[str, Dict[str, Any]]:
        """List all registered strategies with their information"""
        return {
            name: {
                'type': strategy.get_name(),
                'description': strategy.get_description(),
                'parameters': strategy.parameters,
                'min_data_required': strategy.requires_minimum_data(),
                'performance_records': len(self.performance_history.get(name, []))
            }
            for name, strategy in self.strategies.items()
        }
    
    def analyze_with_strategy(self, strategy_name: str, market_data: List[Dict[str, Any]], 
                            symbol: str = None) -> Optional[StrategyResult]:
        """
        Analyze market data with a specific strategy
        
        Args:
            strategy_name: Name of registered strategy
            market_data: Market data for analysis
            symbol: Trading symbol
            
        Returns:
            StrategyResult or None if strategy not found/failed
        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            self.logger.error(f"Strategy not found: {strategy_name}")
            return None
        
        try:
            result = strategy.analyze(market_data, symbol)
            
            # Record performance
            self._record_performance(strategy_name, result, market_data, symbol)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Strategy {strategy_name} analysis failed: {str(e)}")
            return None
    
    def analyze_with_all_strategies(self, market_data: List[Dict[str, Any]], 
                                  symbol: str = None) -> Dict[str, StrategyResult]:
        """
        Analyze market data with all registered strategies
        
        Args:
            market_data: Market data for analysis
            symbol: Trading symbol
            
        Returns:
            Dictionary mapping strategy names to their results
        """
        results = {}
        
        for strategy_name in self.strategies:
            result = self.analyze_with_strategy(strategy_name, market_data, symbol)
            if result:
                results[strategy_name] = result
        
        return results
    
    def compare_strategies(self, market_data: List[Dict[str, Any]], 
                         symbol: str = None) -> Dict[str, Any]:
        """
        Compare all strategies and provide analysis summary
        
        Args:
            market_data: Market data for analysis
            symbol: Trading symbol
            
        Returns:
            Comparison summary with recommendations
        """
        results = self.analyze_with_all_strategies(market_data, symbol)
        
        if not results:
            return {'error': 'No strategy results available'}
        
        # Analyze consensus
        signals = [result.signal for result in results.values()]
        confidences = [result.confidence for result in results.values()]
        
        buy_votes = sum(1 for s in signals if s == SignalType.BUY)
        sell_votes = sum(1 for s in signals if s == SignalType.SELL)
        hold_votes = sum(1 for s in signals if s == SignalType.HOLD)
        
        # Determine consensus
        total_votes = len(signals)
        if buy_votes > sell_votes and buy_votes > hold_votes:
            consensus = SignalType.BUY
            consensus_strength = buy_votes / total_votes
        elif sell_votes > buy_votes and sell_votes > hold_votes:
            consensus = SignalType.SELL
            consensus_strength = sell_votes / total_votes
        else:
            consensus = SignalType.HOLD
            consensus_strength = hold_votes / total_votes
        
        # Best strategy by confidence
        best_strategy = max(results.items(), key=lambda x: x[1].confidence)
        
        return {
            'consensus': {
                'signal': consensus.value,
                'strength': consensus_strength,
                'votes': {'buy': buy_votes, 'sell': sell_votes, 'hold': hold_votes}
            },
            'best_strategy': {
                'name': best_strategy[0],
                'signal': best_strategy[1].signal.value,
                'confidence': best_strategy[1].confidence
            },
            'average_confidence': sum(confidences) / len(confidences),
            'strategy_results': {name: result.to_dict() for name, result in results.items()},
            'recommendation': self._generate_recommendation(consensus, consensus_strength, best_strategy)
        }
    
    def get_best_strategy(self, market_data: List[Dict[str, Any]], 
                         symbol: str = None) -> Optional[str]:
        """
        Get the name of the best performing strategy for current market conditions
        
        Args:
            market_data: Market data for analysis
            symbol: Trading symbol
            
        Returns:
            Name of best strategy or None
        """
        results = self.analyze_with_all_strategies(market_data, symbol)
        
        if not results:
            return None
        
        # Find strategy with highest confidence for non-HOLD signals
        non_hold_results = {name: result for name, result in results.items() 
                           if result.signal != SignalType.HOLD}
        
        if non_hold_results:
            best_strategy = max(non_hold_results.items(), key=lambda x: x[1].confidence)
            return best_strategy[0]
        
        # If all strategies suggest HOLD, return the one with highest confidence
        best_strategy = max(results.items(), key=lambda x: x[1].confidence)
        return best_strategy[0]
    
    def _record_performance(self, strategy_name: str, result: StrategyResult, 
                          market_data: List[Dict[str, Any]], symbol: str):
        """Record strategy performance for tracking"""
        try:
            performance_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'signal': result.signal.value,
                'confidence': result.confidence,
                'current_price': float(market_data[-1]['close']) if market_data else None,
                'data_points': len(market_data),
                'indicators': result.indicators,
                'metadata': result.metadata
            }
            
            self.performance_history[strategy_name].append(performance_record)
            
            # Keep only last 1000 records per strategy
            if len(self.performance_history[strategy_name]) > 1000:
                self.performance_history[strategy_name] = self.performance_history[strategy_name][-1000:]
                
        except Exception as e:
            self.logger.error(f"Failed to record performance for {strategy_name}: {str(e)}")
    
    def _generate_recommendation(self, consensus: SignalType, consensus_strength: float, 
                               best_strategy: tuple) -> str:
        """Generate trading recommendation based on analysis"""
        
        if consensus_strength > 0.7:
            return f"Strong consensus: {consensus.value} (agreement: {consensus_strength:.1%})"
        elif consensus_strength > 0.5:
            return f"Moderate consensus: {consensus.value} (agreement: {consensus_strength:.1%})"
        else:
            return f"No clear consensus. Best individual strategy ({best_strategy[0]}) suggests {best_strategy[1].signal.value} with {best_strategy[1].confidence:.1%} confidence"
    
    def get_performance_summary(self, strategy_name: str = None) -> Dict[str, Any]:
        """Get performance summary for a strategy or all strategies"""
        
        if strategy_name:
            if strategy_name not in self.performance_history:
                return {'error': f'No performance data for strategy: {strategy_name}'}
            
            history = self.performance_history[strategy_name]
            return self._calculate_strategy_performance(strategy_name, history)
        else:
            # Return summary for all strategies
            return {
                name: self._calculate_strategy_performance(name, history)
                for name, history in self.performance_history.items()
                if history  # Only include strategies with performance data
            }
    
    def _calculate_strategy_performance(self, name: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics for a strategy"""
        if not history:
            return {'total_signals': 0}
        
        signals = [record['signal'] for record in history]
        confidences = [record['confidence'] for record in history]
        
        return {
            'total_signals': len(history),
            'buy_signals': signals.count('BUY'),
            'sell_signals': signals.count('SELL'),
            'hold_signals': signals.count('HOLD'),
            'average_confidence': sum(confidences) / len(confidences),
            'max_confidence': max(confidences),
            'min_confidence': min(confidences),
            'last_signal': history[-1]['signal'],
            'last_confidence': history[-1]['confidence'],
            'last_timestamp': history[-1]['timestamp']
        }
    
    def export_strategies(self, filename: str = None) -> str:
        """Export strategy configurations to JSON"""
        try:
            export_data = {
                'strategies': {
                    name: {
                        'type': strategy.get_name(),
                        'description': strategy.get_description(),
                        'parameters': strategy.parameters
                    }
                    for name, strategy in self.strategies.items()
                },
                'export_timestamp': datetime.now().isoformat()
            }
            
            json_data = json.dumps(export_data, indent=2)
            
            if filename:
                with open(filename, 'w') as f:
                    f.write(json_data)
                self.logger.info(f"Strategies exported to {filename}")
            
            return json_data
            
        except Exception as e:
            self.logger.error(f"Failed to export strategies: {str(e)}")
            return ""
    
    def import_strategies(self, json_data: str = None, filename: str = None) -> bool:
        """Import strategy configurations from JSON"""
        try:
            if filename:
                with open(filename, 'r') as f:
                    json_data = f.read()
            
            if not json_data:
                raise ValueError("No JSON data provided")
            
            import_data = json.loads(json_data)
            strategies_data = import_data.get('strategies', {})
            
            imported_count = 0
            for name, strategy_config in strategies_data.items():
                strategy_type = strategy_config['type']
                parameters = strategy_config.get('parameters', {})
                
                if self.create_strategy(strategy_type, name, parameters):
                    imported_count += 1
            
            self.logger.info(f"Imported {imported_count} strategies")
            return imported_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to import strategies: {str(e)}")
            return False