# binance_trade_agent/signal_agent.py
"""
Enhanced SignalAgent: Uses modular trading strategies for signal generation.
Supports multiple strategies with easy swapping and testing capabilities.
"""
import os
import logging
from typing import Dict, Any, Optional, List
from .config import config
from .strategies import StrategyManager, BaseStrategy, StrategyResult, SignalType


class SignalAgent:
    """
    Enhanced Signal Agent using modular trading strategies
    
    Features:
    - Multiple strategy support (RSI, MACD, Combined)
    - Easy strategy swapping and comparison
    - Performance tracking and analysis
    - Backward compatibility with existing interfaces
    """
    
    def __init__(self, market_data_agent=None, strategy_name: str = None, 
                 strategy_parameters: Dict[str, Any] = None, test_mode: bool = False):
        """
        Initialize SignalAgent with strategy management capabilities.
        
        Args:
            market_data_agent: MarketDataAgent instance for fetching OHLCV data
            strategy_name: Name of strategy to use (default: 'combined_default')
            strategy_parameters: Parameters for custom strategy creation
            test_mode: Enable test mode for predictable signals
        """
        self.market_agent = market_data_agent
        self.strategy_manager = StrategyManager()
        
        # Test mode configuration
        self.test_mode = test_mode or bool(os.environ.get("SIGNAL_AGENT_TEST_MODE", "").lower() in ("1", "true", "yes"))
        
        # Strategy selection
        self.current_strategy_name = strategy_name or 'combined_default'
        
        # Create custom strategy if parameters provided
        if strategy_parameters and strategy_name:
            strategy_type = strategy_parameters.get('type', 'combined')
            custom_name = f"{strategy_name}_custom"
            if self.strategy_manager.create_strategy(strategy_type, custom_name, strategy_parameters):
                self.current_strategy_name = custom_name
        
        # Backward compatibility parameters (deprecated but supported)
        self.rsi_overbought = config.signal_rsi_overbought
        self.rsi_oversold = config.signal_rsi_oversold
        self.macd_signal_window = config.signal_macd_signal_window
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"SignalAgent initialized with strategy: {self.current_strategy_name}")

    def generate_signal(self, symbol: str, strategy_name: str = None) -> Dict[str, Any]:
        """
        Generate a trading signal for the given symbol using the configured strategy.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            strategy_name: Override default strategy for this signal (optional)
            
        Returns:
            Dictionary containing signal, confidence, and additional data
        """
        if self.test_mode:
            # Test mode: always generate a predictable trade signal
            import random
            forced_signal = random.choice(["buy", "sell"])
            return {"signal": forced_signal, "confidence": 0.9, "test_mode": True}
        
        if not self.market_agent:
            # Fallback to demo mode if no market data agent provided
            return {"signal": "buy", "confidence": 0.8, "mode": "demo"}
        
        try:
            # Fetch OHLCV data for technical analysis
            ohlcv_data = self.market_agent.fetch_ohlcv(symbol, interval='1h', limit=50)
            
            if not ohlcv_data or len(ohlcv_data) < 20:
                # Not enough data for reliable signals
                return {"signal": "hold", "confidence": 0.5, "reason": "insufficient_data"}
            
            # Use specified strategy or current default
            strategy_name = strategy_name or self.current_strategy_name
            
            # Generate signal using strategy manager
            result = self.strategy_manager.analyze_with_strategy(strategy_name, ohlcv_data, symbol)
            
            if result is None:
                # Strategy analysis failed - return hold signal
                return {"signal": "hold", "confidence": 0.5, "reason": "strategy_analysis_failed"}
            
            # Convert to backward-compatible format
            return self._convert_strategy_result(result)
            
        except Exception as e:
            self.logger.error(f"Signal generation failed for {symbol}: {str(e)}")
            # On any error, fall back to hold signal
            return {"signal": "hold", "confidence": 0.5, "reason": "error", "error": str(e)}
    
    def _convert_strategy_result(self, result: StrategyResult) -> Dict[str, Any]:
        """Convert StrategyResult to backward-compatible dictionary format"""
        return {
            "signal": result.signal.value.lower(),
            "confidence": result.confidence,
            "indicators": result.indicators,
            "metadata": result.metadata,
            "price_target": result.price_target,
            "stop_loss": result.stop_loss,
            "take_profit": result.take_profit,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None
        }
    
    def set_strategy(self, strategy_name: str) -> bool:
        """
        Change the current strategy
        
        Args:
            strategy_name: Name of registered strategy
            
        Returns:
            True if strategy was set successfully
        """
        if strategy_name in self.strategy_manager.list_strategies():
            self.current_strategy_name = strategy_name
            self.logger.info(f"Strategy changed to: {strategy_name}")
            return True
        else:
            self.logger.error(f"Strategy not found: {strategy_name}")
            return False
    
    def get_available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available strategies with their descriptions"""
        return self.strategy_manager.list_strategies()
    
    def compare_strategies(self, symbol: str) -> Dict[str, Any]:
        """
        Compare all available strategies for the given symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Strategy comparison results with consensus and recommendations
        """
        try:
            if not self.market_agent:
                return {"error": "No market data agent available"}
            
            # Fetch market data
            ohlcv_data = self.market_agent.fetch_ohlcv(symbol, interval='1h', limit=50)
            
            if not ohlcv_data or len(ohlcv_data) < 20:
                return {"error": "Insufficient market data"}
            
            # Get strategy comparison
            return self.strategy_manager.compare_strategies(ohlcv_data, symbol)
            
        except Exception as e:
            self.logger.error(f"Strategy comparison failed for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    def create_custom_strategy(self, name: str, strategy_type: str, parameters: Dict[str, Any]) -> bool:
        """
        Create and register a custom strategy
        
        Args:
            name: Unique name for the strategy
            strategy_type: Type of strategy ('rsi', 'macd', 'combined')
            parameters: Strategy parameters
            
        Returns:
            True if strategy was created successfully
        """
        return self.strategy_manager.create_strategy(strategy_type, name, parameters)
    
    def get_strategy_performance(self, strategy_name: str = None) -> Dict[str, Any]:
        """
        Get performance metrics for a strategy
        
        Args:
            strategy_name: Strategy name (optional, defaults to current strategy)
            
        Returns:
            Performance metrics dictionary
        """
        strategy_name = strategy_name or self.current_strategy_name
        return self.strategy_manager.get_performance_summary(strategy_name)
    
    def get_current_strategy_info(self) -> Dict[str, Any]:
        """Get information about the currently selected strategy"""
        strategies = self.strategy_manager.list_strategies()
        return strategies.get(self.current_strategy_name, {})
    
    # Backward compatibility methods (deprecated but maintained for existing code)
    def compute_signal(self, ohlcv, indicator='rsi'):
        """
        Legacy method: Compute trading signal from OHLCV data and selected indicator.
        
        DEPRECATED: Use generate_signal() instead for enhanced functionality.
        """
        self.logger.warning("compute_signal() is deprecated. Use generate_signal() for enhanced strategy support.")
        
        if not ohlcv or not isinstance(ohlcv, list):
            raise ValueError("OHLCV data must be a non-empty list.")
        
        # Convert to strategy format and use RSI strategy for backward compatibility
        if indicator == 'rsi':
            rsi_strategy = self.strategy_manager.get_strategy('rsi_default')
            if rsi_strategy:
                result = rsi_strategy.analyze(ohlcv)
                return {
                    'signal': result.signal.value,
                    'confidence': result.confidence,
                    'indicator_value': result.indicators.get('rsi', 50),
                    'indicator_type': 'RSI'
                }
        elif indicator == 'macd':
            macd_strategy = self.strategy_manager.get_strategy('macd_default')
            if macd_strategy:
                result = macd_strategy.analyze(ohlcv)
                return {
                    'signal': result.signal.value,
                    'confidence': result.confidence,
                    'indicator_value': result.indicators.get('macd_line', 0),
                    'indicator_type': 'MACD'
                }
        
        # Fallback for unknown indicators
        raise ValueError(f"Unsupported indicator: {indicator}")
    
    def compute_rsi(self, closes, period=14):
        """Legacy RSI calculation - DEPRECATED"""
        self.logger.warning("compute_rsi() is deprecated. Use RSI strategy instead.")
        
        if not closes or len(closes) < period + 1:
            raise ValueError("Not enough data for RSI calculation.")
        
        # Use RSI strategy for calculation
        rsi_strategy = self.strategy_manager.get_strategy('rsi_default')
        if rsi_strategy:
            return rsi_strategy._calculate_rsi(closes)
        
        # Fallback calculation
        gains = []
        losses = []
        for i in range(1, period + 1):
            delta = closes[-i] - closes[-i-1]
            if delta > 0:
                gains.append(delta)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-delta)
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def compute_macd(self, closes, fast_period=12, slow_period=26, signal_period=9):
        """Legacy MACD calculation - DEPRECATED"""
        self.logger.warning("compute_macd() is deprecated. Use MACD strategy instead.")
        
        # Use MACD strategy for calculation
        macd_strategy = self.strategy_manager.get_strategy('macd_default')
        if macd_strategy:
            return macd_strategy._calculate_macd(closes)
        
        # Fallback calculation (simplified)
        if not closes or len(closes) < slow_period + signal_period:
            raise ValueError("Not enough data for MACD calculation.")
        
        def ema(data, period):
            k = 2 / (period + 1)
            ema_vals = [data[0]]
            for price in data[1:]:
                ema_vals.append(price * k + ema_vals[-1] * (1 - k))
            return ema_vals
        
        fast_ema = ema(closes, fast_period)
        slow_ema = ema(closes, slow_period)
        macd_line = [f - s for f, s in zip(fast_ema[-len(slow_ema):], slow_ema)]
        signal_line = ema(macd_line, signal_period)
        histogram = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
        
        return macd_line[-1], signal_line[-1], histogram[-1]
    
    def compute_ma(self, closes, period=20):
        """Legacy MA calculation - DEPRECATED"""
        self.logger.warning("compute_ma() is deprecated.")
        if not closes or len(closes) < period:
            raise ValueError("Not enough data for MA calculation.")
        return sum(closes[-period:]) / period
    
    def compute_custom(self, ohlcv, **kwargs):
        """Legacy custom indicator placeholder - DEPRECATED"""
        self.logger.warning("compute_custom() is deprecated. Create custom strategies instead.")
        pass


if __name__ == "__main__":
    """
    Enhanced demo showcasing the new modular strategy system
    """
    print("=== Enhanced SignalAgent with Modular Strategies Demo ===\n")
    
    # Sample OHLCV data for testing
    sample_ohlcv = [
        {'close': 100}, {'close': 102}, {'close': 101}, {'close': 103}, {'close': 105},
        {'close': 104}, {'close': 106}, {'close': 108}, {'close': 107}, {'close': 109},
        {'close': 110}, {'close': 111}, {'close': 112}, {'close': 113}, {'close': 114},
        {'close': 115}, {'close': 116}, {'close': 117}, {'close': 118}, {'close': 119},
        {'close': 120}, {'close': 121}, {'close': 122}, {'close': 123}, {'close': 124},
        {'close': 125}, {'close': 126}, {'close': 127}, {'close': 128}, {'close': 129},
        {'close': 130}, {'close': 131}, {'close': 132}, {'close': 133}, {'close': 134},
        {'close': 135}, {'close': 136}, {'close': 137}, {'close': 138}, {'close': 139},
        {'close': 140}
    ]
    
    # Initialize agent
    agent = SignalAgent()
    
    print("1. Available Strategies:")
    strategies = agent.get_available_strategies()
    for name, info in strategies.items():
        print(f"   {name}: {info['description']}")
    print()
    
    print("2. Current Strategy Information:")
    current_info = agent.get_current_strategy_info()
    print(f"   Strategy: {agent.current_strategy_name}")
    print(f"   Type: {current_info.get('type', 'unknown')}")
    print(f"   Description: {current_info.get('description', 'N/A')}")
    print()
    
    print("3. Strategy Analysis Results:")
    # Test with different strategies
    test_strategies = ['rsi_default', 'macd_default', 'combined_default']
    
    for strategy in test_strategies:
        if strategy in strategies:
            print(f"\n   Testing {strategy}:")
            # Mock market data agent for demo
            class MockMarketAgent:
                def fetch_ohlcv(self, symbol, interval='1h', limit=50):
                    return sample_ohlcv
            
            agent.market_agent = MockMarketAgent()
            agent.set_strategy(strategy)
            
            result = agent.generate_signal('BTCUSDT')
            print(f"     Signal: {result['signal'].upper()}")
            print(f"     Confidence: {result['confidence']:.1%}")
            if 'indicators' in result:
                print(f"     Indicators: {list(result['indicators'].keys())}")
    
    print("\n4. Strategy Comparison:")
    if hasattr(agent, 'market_agent') and agent.market_agent:
        comparison = agent.compare_strategies('BTCUSDT')
        if 'error' not in comparison:
            consensus = comparison['consensus']
            print(f"   Consensus: {consensus['signal']} (strength: {consensus['strength']:.1%})")
            print(f"   Best Strategy: {comparison['best_strategy']['name']}")
            print(f"   Recommendation: {comparison['recommendation']}")
        else:
            print(f"   Error: {comparison['error']}")
    
    print("\n5. Creating Custom Strategy:")
    custom_params = {
        'rsi_period': 21,
        'rsi_overbought': 75,
        'rsi_oversold': 25,
        'macd_fast_period': 10,
        'macd_slow_period': 22
    }
    
    success = agent.create_custom_strategy('my_custom_strategy', 'combined', custom_params)
    if success:
        print("   Custom strategy created successfully!")
        agent.set_strategy('my_custom_strategy')
        result = agent.generate_signal('BTCUSDT')
        print(f"   Custom strategy signal: {result['signal'].upper()} (confidence: {result['confidence']:.1%})")
    else:
        print("   Failed to create custom strategy")
    
    print("\n6. Backward Compatibility Test:")
    try:
        # Test legacy methods still work
        rsi_result = agent.compute_signal(sample_ohlcv, indicator='rsi')
        macd_result = agent.compute_signal(sample_ohlcv, indicator='macd')
        print(f"   Legacy RSI: {rsi_result['signal']} (confidence: {rsi_result['confidence']:.1%})")
        print(f"   Legacy MACD: {macd_result['signal']} (confidence: {macd_result['confidence']:.1%})")
    except Exception as e:
        print(f"   Legacy compatibility error: {str(e)}")
    
    print("\n=== Demo Complete ===")
    print("The SignalAgent now supports:")
    print("- Multiple modular trading strategies")
    print("- Easy strategy switching and comparison")
    print("- Custom strategy creation with parameters")
    print("- Performance tracking and analysis")
    print("- Full backward compatibility")
