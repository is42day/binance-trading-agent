"""
Test RSI Strategy Implementation
"""
import pytest
from binance_trade_agent.strategies.rsi_strategy import RSIStrategy
from binance_trade_agent.strategies.base_strategy import SignalType, StrategyResult


class TestRSIStrategy:
    """Test cases for RSI Strategy"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.strategy = RSIStrategy()
        
        # Sample market data for testing
        self.sample_data = [
            {'close': 100}, {'close': 102}, {'close': 101}, {'close': 103}, {'close': 105},
            {'close': 104}, {'close': 106}, {'close': 108}, {'close': 107}, {'close': 109},
            {'close': 110}, {'close': 111}, {'close': 112}, {'close': 113}, {'close': 114},
            {'close': 115}, {'close': 116}, {'close': 117}, {'close': 118}, {'close': 119},
            {'close': 120}, {'close': 121}, {'close': 122}, {'close': 123}, {'close': 124},
            {'close': 125}, {'close': 126}, {'close': 127}, {'close': 128}, {'close': 129},
            {'close': 130}
        ]
        
        # Oversold scenario (declining prices)
        self.oversold_data = [
            {'close': 130}, {'close': 128}, {'close': 126}, {'close': 124}, {'close': 122},
            {'close': 120}, {'close': 118}, {'close': 116}, {'close': 114}, {'close': 112},
            {'close': 110}, {'close': 108}, {'close': 106}, {'close': 104}, {'close': 102},
            {'close': 100}, {'close': 98}, {'close': 96}, {'close': 94}, {'close': 92},
            {'close': 90}, {'close': 88}, {'close': 86}, {'close': 84}, {'close': 82},
            {'close': 80}, {'close': 78}, {'close': 76}, {'close': 74}, {'close': 72},
            {'close': 70}
        ]
    
    def test_strategy_initialization(self):
        """Test strategy initialization"""
        assert self.strategy.get_name() == "rsi"
        assert "RSI" in self.strategy.get_description()
        assert self.strategy.requires_minimum_data() == 15  # default period + 1
    
    def test_parameters(self):
        """Test parameter handling"""
        params = self.strategy.get_parameters()
        
        # Check required parameters exist
        assert 'period' in params
        assert 'overbought' in params
        assert 'oversold' in params
        
        # Test parameter retrieval
        assert self.strategy.get_parameter('period') == 14
        assert self.strategy.get_parameter('overbought') == 70
        assert self.strategy.get_parameter('oversold') == 30
    
    def test_parameter_validation(self):
        """Test parameter validation"""
        # Valid parameters
        strategy = RSIStrategy({'period': 20, 'overbought': 75})
        assert strategy.get_parameter('period') == 20
        assert strategy.get_parameter('overbought') == 75
        
        # Invalid parameters should raise errors
        with pytest.raises(ValueError):
            RSIStrategy({'period': 1})  # Below minimum
        
        with pytest.raises(ValueError):
            RSIStrategy({'overbought': 100})  # Above maximum
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        closes = [float(candle['close']) for candle in self.sample_data]
        rsi = self.strategy._calculate_rsi(closes)
        
        # RSI should be between 0 and 100
        assert 0 <= rsi <= 100
        
        # For rising prices, RSI should be high
        assert rsi > 50  # Since prices are generally rising
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data"""
        insufficient_data = self.sample_data[:10]  # Less than required
        
        result = self.strategy.analyze(insufficient_data)
        
        assert result.signal == SignalType.HOLD
        assert result.confidence == 0.0
        assert 'error' in result.metadata
    
    def test_buy_signal_generation(self):
        """Test BUY signal generation for oversold conditions"""
        result = self.strategy.analyze(self.oversold_data)
        
        # Should generate BUY signal for oversold conditions
        assert result.signal == SignalType.BUY
        assert result.confidence > 0.0
        assert 'rsi' in result.indicators
        assert result.indicators['rsi'] < 30  # Should be oversold
    
    def test_sell_signal_generation(self):
        """Test SELL signal generation for overbought conditions"""
        # Create overbought scenario
        overbought_strategy = RSIStrategy({'overbought': 60})  # Lower threshold for testing
        
        result = overbought_strategy.analyze(self.sample_data)
        
        # Should generate SELL signal for overbought conditions
        assert result.signal == SignalType.SELL
        assert result.confidence > 0.0
        assert 'rsi' in result.indicators
    
    def test_hold_signal_generation(self):
        """Test HOLD signal generation for neutral conditions"""
        # Use moderate thresholds to ensure neutral zone
        neutral_strategy = RSIStrategy({'overbought': 90, 'oversold': 10})

        # Create neutral data: prices oscillate around a mean
        neutral_data = []
        price = 100
        for i in range(31):
            price += 1 if i % 2 == 0 else -1
            neutral_data.append({'close': price})

        result = neutral_strategy.analyze(neutral_data)

        # Should generate HOLD signal for neutral conditions
        assert result.signal == SignalType.HOLD
        assert result.confidence > 0.0
    
    def test_price_levels_calculation(self):
        """Test price target and stop loss calculation"""
        result = self.strategy.analyze(self.oversold_data)
        
        if result.signal != SignalType.HOLD:
            assert result.price_target is not None
            assert result.stop_loss is not None
            assert result.take_profit is not None
            
            current_price = float(self.oversold_data[-1]['close'])
            
            if result.signal == SignalType.BUY:
                assert result.price_target > current_price
                assert result.stop_loss < current_price
                assert result.take_profit > current_price
    
    def test_risk_metrics(self):
        """Test risk metrics calculation"""
        risk_metrics = self.strategy.get_risk_metrics(self.sample_data)
        
        assert 'volatility' in risk_metrics
        assert 'risk_level' in risk_metrics
        assert 'rsi_risk' in risk_metrics
        assert 'rsi_value' in risk_metrics
        
        # Risk metrics should be reasonable
        assert 0 <= risk_metrics['volatility'] <= 1
        assert 0 <= risk_metrics['risk_level'] <= 1
        assert 0 <= risk_metrics['rsi_risk'] <= 1
        assert 0 <= risk_metrics['rsi_value'] <= 100
    
    def test_custom_parameters(self):
        """Test strategy with custom parameters"""
        custom_strategy = RSIStrategy({
            'period': 21,
            'overbought': 75,
            'oversold': 25,
            'extreme_overbought': 85,
            'extreme_oversold': 15
        })
        
        assert custom_strategy.get_parameter('period') == 21
        assert custom_strategy.get_parameter('overbought') == 75
        assert custom_strategy.requires_minimum_data() == 22
        
        result = custom_strategy.analyze(self.sample_data)
        assert isinstance(result, StrategyResult)
    
    def test_symbol_support(self):
        """Test symbol support"""
        assert self.strategy.supports_symbol('BTCUSDT')
        assert self.strategy.supports_symbol('ETHUSDT')
        assert self.strategy.supports_symbol('ANY_SYMBOL')
    
    def test_strategy_result_serialization(self):
        """Test strategy result can be serialized"""
        result = self.strategy.analyze(self.sample_data)
        
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert 'signal' in result_dict
        assert 'confidence' in result_dict
        assert 'indicators' in result_dict
        assert 'metadata' in result_dict
    
    def test_extreme_conditions(self):
        """Test strategy behavior under extreme market conditions"""
        # Test with extreme overbought strategy
        extreme_strategy = RSIStrategy({
            'extreme_oversold': 5,
            'extreme_overbought': 95
        })
        
        result = extreme_strategy.analyze(self.oversold_data)
        
        # Should still produce valid result
        assert isinstance(result, StrategyResult)
        assert result.signal in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 0 <= result.confidence <= 1
    
    def test_error_handling(self):
        """Test error handling with malformed data"""
        # Test with empty data
        result = self.strategy.analyze([])
        assert result.signal == SignalType.HOLD
        assert result.confidence == 0.0
        
        # Test with malformed data
        malformed_data = [{'price': 100}]  # Missing 'close' key
        result = self.strategy.analyze(malformed_data)
        assert result.signal == SignalType.HOLD
        assert result.confidence == 0.0
        assert 'error' in result.metadata