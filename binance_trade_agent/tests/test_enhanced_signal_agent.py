"""
Test Enhanced Signal Agent with Modular Strategies
"""
import pytest
from unittest.mock import Mock, patch
from binance_trade_agent.signal_agent import SignalAgent
from binance_trade_agent.strategies.base_strategy import SignalType


class TestEnhancedSignalAgent:
    """Test cases for enhanced SignalAgent with modular strategies"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.agent = SignalAgent()
        
        # Sample market data
        self.sample_data = [
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
        
        # Mock market data agent
        self.mock_market_agent = Mock()
        self.mock_market_agent.fetch_ohlcv.return_value = self.sample_data
        self.agent.market_agent = self.mock_market_agent
    
    def test_initialization(self):
        """Test agent initialization with strategy manager"""
        assert hasattr(self.agent, 'strategy_manager')
        assert hasattr(self.agent, 'current_strategy_name')
        assert self.agent.current_strategy_name == 'combined_default'
        
        # Should have available strategies
        strategies = self.agent.get_available_strategies()
        assert len(strategies) > 0
    
    def test_custom_strategy_initialization(self):
        """Test initialization with custom strategy parameters"""
        custom_params = {
            'type': 'rsi',
            'period': 21,
            'overbought': 75
        }
        
        agent = SignalAgent(strategy_name='test_strategy', strategy_parameters=custom_params)
        assert 'test_strategy_custom' in agent.get_available_strategies()
    
    def test_signal_generation(self):
        """Test signal generation with current strategy"""
        result = self.agent.generate_signal('BTCUSDT')
        
        assert 'signal' in result
        assert 'confidence' in result
        assert result['signal'] in ['buy', 'sell', 'hold']
        assert 0 <= result['confidence'] <= 1
        
        # Should have called market agent
        self.mock_market_agent.fetch_ohlcv.assert_called_once()
    
    def test_strategy_switching(self):
        """Test switching between different strategies"""
        original_strategy = self.agent.current_strategy_name
        
        # Switch to RSI strategy
        success = self.agent.set_strategy('rsi_default')
        assert success
        assert self.agent.current_strategy_name == 'rsi_default'
        
        # Generate signal with new strategy
        result = self.agent.generate_signal('BTCUSDT')
        assert 'signal' in result
        
        # Switch back
        self.agent.set_strategy(original_strategy)
        assert self.agent.current_strategy_name == original_strategy
    
    def test_invalid_strategy_switching(self):
        """Test switching to invalid strategy"""
        original_strategy = self.agent.current_strategy_name
        
        success = self.agent.set_strategy('nonexistent_strategy')
        assert not success
        assert self.agent.current_strategy_name == original_strategy
    
    def test_strategy_comparison(self):
        """Test strategy comparison functionality"""
        comparison = self.agent.compare_strategies('BTCUSDT')
        
        assert 'consensus' in comparison
        assert 'best_strategy' in comparison
        assert 'strategy_results' in comparison
        
        # Consensus should have required fields
        consensus = comparison['consensus']
        assert 'signal' in consensus
        assert 'strength' in consensus
        assert 'votes' in consensus
    
    def test_custom_strategy_creation(self):
        """Test creating custom strategies"""
        custom_params = {
            'period': 21,
            'overbought': 75,
            'oversold': 25
        }
        
        success = self.agent.create_custom_strategy('test_rsi', 'rsi', custom_params)
        assert success
        
        # Strategy should be available
        strategies = self.agent.get_available_strategies()
        assert 'test_rsi' in strategies
        
        # Should be able to use the new strategy
        success = self.agent.set_strategy('test_rsi')
        assert success
        
        result = self.agent.generate_signal('BTCUSDT')
        assert 'signal' in result
    
    def test_strategy_performance_tracking(self):
        """Test strategy performance tracking"""
        # Generate some signals to create performance data
        self.agent.generate_signal('BTCUSDT')
        self.agent.generate_signal('ETHUSDT')
        
        # Get performance summary
        performance = self.agent.get_strategy_performance()
        
        assert 'total_signals' in performance
        assert performance['total_signals'] > 0
    
    def test_test_mode(self):
        """Test test mode functionality"""
        test_agent = SignalAgent(test_mode=True)
        
        result = test_agent.generate_signal('BTCUSDT')
        
        assert 'test_mode' in result
        assert result['test_mode'] is True
        assert result['signal'] in ['buy', 'sell']
        assert result['confidence'] == 0.9
    
    def test_no_market_agent_fallback(self):
        """Test fallback behavior when no market agent is provided"""
        agent = SignalAgent()  # No market agent
        
        result = agent.generate_signal('BTCUSDT')
        
        assert result['signal'] == 'buy'
        assert result['confidence'] == 0.8
        assert 'mode' in result
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient market data"""
        # Mock insufficient data
        self.mock_market_agent.fetch_ohlcv.return_value = [{'close': 100}]
        
        result = self.agent.generate_signal('BTCUSDT')
        
        assert result['signal'] == 'hold'
        assert result['confidence'] == 0.5
        assert 'reason' in result
    
    def test_market_data_fetch_error(self):
        """Test handling of market data fetch errors"""
        # Mock market agent to raise exception
        self.mock_market_agent.fetch_ohlcv.side_effect = Exception("API Error")
        
        result = self.agent.generate_signal('BTCUSDT')
        
        assert result['signal'] == 'hold'
        assert result['confidence'] == 0.5
        assert 'error' in result
    
    def test_backward_compatibility(self):
        """Test backward compatibility with legacy methods"""
        # Test legacy compute_signal method
        result = self.agent.compute_signal(self.sample_data, indicator='rsi')
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'indicator_value' in result
        assert 'indicator_type' in result
        
        # Test MACD
        result = self.agent.compute_signal(self.sample_data, indicator='macd')
        assert result['indicator_type'] == 'MACD'
    
    def test_legacy_rsi_calculation(self):
        """Test legacy RSI calculation method"""
        closes = [float(candle['close']) for candle in self.sample_data]
        
        rsi = self.agent.compute_rsi(closes)
        assert 0 <= rsi <= 100
    
    def test_legacy_macd_calculation(self):
        """Test legacy MACD calculation method"""
        closes = [float(candle['close']) for candle in self.sample_data]
        
        macd, signal, histogram = self.agent.compute_macd(closes)
        assert isinstance(macd, float)
        assert isinstance(signal, float)
        assert isinstance(histogram, float)
    
    def test_strategy_override_in_signal_generation(self):
        """Test strategy override in generate_signal method"""
        # Generate signal with default strategy
        result1 = self.agent.generate_signal('BTCUSDT')
        
        # Generate signal with specific strategy override
        result2 = self.agent.generate_signal('BTCUSDT', strategy_name='rsi_default')
        
        # Both should be valid but might be different
        assert 'signal' in result1
        assert 'signal' in result2
        assert result1['signal'] in ['buy', 'sell', 'hold']
        assert result2['signal'] in ['buy', 'sell', 'hold']
    
    def test_current_strategy_info(self):
        """Test getting current strategy information"""
        info = self.agent.get_current_strategy_info()
        
        assert 'type' in info
        assert 'description' in info
        assert 'parameters' in info
    
    def test_available_strategies_listing(self):
        """Test listing available strategies"""
        strategies = self.agent.get_available_strategies()
        
        assert isinstance(strategies, dict)
        assert len(strategies) > 0
        
        # Check structure of strategy info
        for name, info in strategies.items():
            assert 'type' in info
            assert 'description' in info
            assert 'parameters' in info
            assert 'min_data_required' in info
    
    def test_strategy_result_conversion(self):
        """Test conversion of StrategyResult to dictionary format"""
        from binance_trade_agent.strategies.base_strategy import StrategyResult, SignalType
        from datetime import datetime
        
        # Create a test StrategyResult
        result = StrategyResult(
            signal=SignalType.BUY,
            confidence=0.8,
            price_target=100.0,
            stop_loss=95.0,
            take_profit=105.0,
            indicators={'rsi': 25},
            metadata={'test': True},
            timestamp=datetime.now()
        )
        
        # Convert using agent's method
        converted = self.agent._convert_strategy_result(result)
        
        assert converted['signal'] == 'buy'
        assert converted['confidence'] == 0.8
        assert converted['price_target'] == 100.0
        assert converted['stop_loss'] == 95.0
        assert converted['take_profit'] == 105.0
        assert 'indicators' in converted
        assert 'metadata' in converted
        assert 'timestamp' in converted