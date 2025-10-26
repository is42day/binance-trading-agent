"""
Test Strategy Manager Implementation
"""
import pytest
from binance_trade_agent.strategies.strategy_manager import StrategyManager
from binance_trade_agent.strategies.base_strategy import SignalType, StrategyResult
from binance_trade_agent.strategies.rsi_strategy import RSIStrategy
from binance_trade_agent.strategies.macd_strategy import MACDStrategy


class TestStrategyManager:
    """Test cases for Strategy Manager"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = StrategyManager()
        
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
    
    def test_initialization(self):
        """Test manager initialization"""
        # Should have default strategies registered
        strategies = self.manager.list_strategies()
        assert len(strategies) > 0
        
        # Check for expected default strategies
        strategy_names = list(strategies.keys())
        assert any('rsi' in name for name in strategy_names)
        assert any('macd' in name for name in strategy_names)
        assert any('combined' in name for name in strategy_names)
    
    def test_strategy_registration(self):
        """Test manual strategy registration"""
        custom_rsi = RSIStrategy({'period': 21})
        
        success = self.manager.register_strategy('custom_rsi', custom_rsi)
        assert success
        
        # Verify registration
        assert 'custom_rsi' in self.manager.list_strategies()
        retrieved = self.manager.get_strategy('custom_rsi')
        assert retrieved is not None
        assert retrieved.get_parameter('period') == 21
    
    def test_strategy_creation(self):
        """Test strategy creation via manager"""
        success = self.manager.create_strategy('rsi', 'test_rsi', {'period': 20})
        assert success
        
        # Verify creation
        strategy = self.manager.get_strategy('test_rsi')
        assert strategy is not None
        assert strategy.get_parameter('period') == 20
    
    def test_invalid_strategy_creation(self):
        """Test creation with invalid strategy type"""
        success = self.manager.create_strategy('invalid_type', 'test_invalid')
        assert not success
        
        # Should not be registered
        assert self.manager.get_strategy('test_invalid') is None
    
    def test_single_strategy_analysis(self):
        """Test analysis with single strategy"""
        result = self.manager.analyze_with_strategy('rsi_default', self.sample_data, 'BTCUSDT')
        
        assert result is not None
        assert isinstance(result, StrategyResult)
        assert result.signal in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 0 <= result.confidence <= 1
    
    def test_all_strategies_analysis(self):
        """Test analysis with all strategies"""
        results = self.manager.analyze_with_all_strategies(self.sample_data, 'BTCUSDT')
        
        assert len(results) > 0
        
        # All results should be valid
        for name, result in results.items():
            assert isinstance(result, StrategyResult)
            assert result.signal in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
            assert 0 <= result.confidence <= 1
    
    def test_strategy_comparison(self):
        """Test strategy comparison functionality"""
        comparison = self.manager.compare_strategies(self.sample_data, 'BTCUSDT')
        
        assert 'consensus' in comparison
        assert 'best_strategy' in comparison
        assert 'average_confidence' in comparison
        assert 'strategy_results' in comparison
        assert 'recommendation' in comparison
        
        # Consensus should have valid structure
        consensus = comparison['consensus']
        assert 'signal' in consensus
        assert 'strength' in consensus
        assert 'votes' in consensus
        
        # Votes should sum to total strategies
        votes = consensus['votes']
        total_votes = votes['buy'] + votes['sell'] + votes['hold']
        assert total_votes == len(comparison['strategy_results'])
    
    def test_best_strategy_selection(self):
        """Test best strategy selection"""
        best_strategy = self.manager.get_best_strategy(self.sample_data, 'BTCUSDT')
        
        assert best_strategy is not None
        assert best_strategy in self.manager.list_strategies()
    
    def test_performance_tracking(self):
        """Test performance tracking"""
        # Run analysis to generate performance data
        self.manager.analyze_with_strategy('rsi_default', self.sample_data, 'BTCUSDT')
        
        # Check performance summary
        performance = self.manager.get_performance_summary('rsi_default')
        
        assert 'total_signals' in performance
        assert performance['total_signals'] > 0
        assert 'last_signal' in performance
        assert 'average_confidence' in performance
    
    def test_all_strategies_performance(self):
        """Test performance summary for all strategies"""
        # Run analysis to generate performance data
        self.manager.analyze_with_all_strategies(self.sample_data, 'BTCUSDT')
        
        # Get all performance summaries
        all_performance = self.manager.get_performance_summary()
        
        assert isinstance(all_performance, dict)
        assert len(all_performance) > 0
        
        # Each strategy should have performance data
        for strategy_name, performance in all_performance.items():
            assert 'total_signals' in performance
            assert performance['total_signals'] > 0
    
    def test_strategy_export_import(self):
        """Test strategy export and import"""
        # Export current strategies
        export_data = self.manager.export_strategies()
        assert len(export_data) > 0
        
        # Create new manager and import
        new_manager = StrategyManager()
        
        # Clear default strategies to test import
        new_manager.strategies.clear()
        new_manager.performance_history.clear()
        
        success = new_manager.import_strategies(json_data=export_data)
        assert success
        
        # Should have imported strategies
        assert len(new_manager.list_strategies()) > 0
    
    def test_invalid_strategy_analysis(self):
        """Test analysis with invalid strategy name"""
        result = self.manager.analyze_with_strategy('nonexistent', self.sample_data)
        assert result is None
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient market data"""
        insufficient_data = self.sample_data[:5]  # Very little data
        
        results = self.manager.analyze_with_all_strategies(insufficient_data)
        
        # Some strategies might still work, others might return HOLD with low confidence
        for name, result in results.items():
            assert isinstance(result, StrategyResult)
            # Either valid signal or HOLD due to insufficient data
            assert result.signal in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
    
    def test_strategy_listing(self):
        """Test strategy listing functionality"""
        strategies = self.manager.list_strategies()
        
        # Should contain detailed information
        for name, info in strategies.items():
            assert 'type' in info
            assert 'description' in info
            assert 'parameters' in info
            assert 'min_data_required' in info
            assert 'performance_records' in info
    
    def test_custom_strategy_parameters(self):
        """Test creating strategies with custom parameters"""
        custom_params = {
            'period': 21,
            'overbought': 75,
            'oversold': 25
        }
        
        success = self.manager.create_strategy('rsi', 'custom_rsi_test', custom_params)
        assert success
        
        strategy = self.manager.get_strategy('custom_rsi_test')
        assert strategy.get_parameter('period') == 21
        assert strategy.get_parameter('overbought') == 75
        assert strategy.get_parameter('oversold') == 25
    
    def test_strategy_consensus_calculation(self):
        """Test consensus calculation with known strategy outputs"""
        # Create strategies with predictable outputs for testing
        # This would require creating mock strategies or using specific market data
        # that produces known signals
        
        comparison = self.manager.compare_strategies(self.sample_data)
        
        # Consensus should be calculated correctly
        assert comparison['consensus']['strength'] > 0
        assert 0 <= comparison['average_confidence'] <= 1
        
        # Recommendation should be a string
        assert isinstance(comparison['recommendation'], str)
        assert len(comparison['recommendation']) > 0