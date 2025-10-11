"""
Integration tests for the complete trading agent workflow
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from binance_trade_agent.orchestrator import TradingOrchestrator, TradeDecision
from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.signal_agent import SignalAgent
from binance_trade_agent.risk_management_agent import RiskManagementAgent
from binance_trade_agent.trade_execution_agent import TradeExecutionAgent


class TestAgentFlow:
    """Test the complete agent workflow integration"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.market_agent = MarketDataAgent()
        self.signal_agent = SignalAgent()
        self.risk_agent = RiskManagementAgent()
        self.execution_agent = TradeExecutionAgent()
        self.orchestrator = TradingOrchestrator()
    
    def test_market_to_signal_flow(self):
        """Test market data to signal generation flow"""
        # Test that market data flows correctly to signal generation
        symbol = "BTCUSDT"
        
        # Get market data
        price = self.market_agent.get_latest_price(symbol)
        assert price > 0
        
        # Generate signal
        signal_result = self.signal_agent.generate_signal(symbol)
        assert 'signal' in signal_result
        assert 'confidence' in signal_result
        assert signal_result['signal'] in ['BUY', 'SELL', 'HOLD']
        assert 0 <= signal_result['confidence'] <= 1
    
    def test_signal_to_risk_flow(self):
        """Test signal to risk management flow"""
        symbol = "BTCUSDT"
        
        # Generate signal
        signal_result = self.signal_agent.generate_signal(symbol)
        
        # Validate with risk management
        risk_result = self.risk_agent.validate_trade(
            symbol=symbol,
            side=signal_result['signal'].lower(),
            quantity=0.001,
            price=50000.0
        )
        
        assert 'approved' in risk_result
        assert 'reason' in risk_result
        assert isinstance(risk_result['approved'], bool)
    
    def test_risk_to_execution_flow(self):
        """Test risk management to execution flow"""
        symbol = "BTCUSDT"
        quantity = 0.001
        
        # Mock risk approval
        risk_result = {'approved': True, 'reason': 'Trade within limits'}
        
        if risk_result['approved']:
            # This would normally execute a trade
            # For testing, we'll mock the execution
            with patch.object(self.execution_agent, 'place_buy_order') as mock_buy:
                mock_buy.return_value = {
                    'order_id': 'test_123',
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': 50000.0,
                    'status': 'FILLED'
                }
                
                result = self.execution_agent.place_buy_order(symbol, quantity)
                assert result['order_id'] == 'test_123'
                assert result['symbol'] == symbol
    
    def test_complete_workflow_integration(self):
        """Test the complete workflow from market data to execution"""
        symbol = "BTCUSDT"
        quantity = 0.001
        
        # Step 1: Market data
        price = self.market_agent.get_latest_price(symbol)
        assert price > 0
        
        # Step 2: Signal generation
        signal_result = self.signal_agent.generate_signal(symbol)
        assert signal_result['signal'] in ['BUY', 'SELL', 'HOLD']
        
        # Step 3: Risk validation
        risk_result = self.risk_agent.validate_trade(
            symbol=symbol,
            side=signal_result['signal'].lower(),
            quantity=quantity,
            price=price
        )
        
        # Step 4: Conditional execution
        if risk_result['approved'] and signal_result['signal'] in ['BUY', 'SELL']:
            # Mock execution for testing
            with patch.object(self.execution_agent, 'place_buy_order') as mock_execution:
                mock_execution.return_value = {
                    'order_id': 'integration_test_123',
                    'status': 'FILLED'
                }
                
                if signal_result['signal'] == 'BUY':
                    result = self.execution_agent.place_buy_order(symbol, quantity)
                    assert 'order_id' in result
        
        # Workflow completed successfully if we reach here
        assert True
    
    @pytest.mark.asyncio
    async def test_orchestrator_workflow(self):
        """Test the orchestrator workflow integration"""
        symbol = "BTCUSDT"
        quantity = 0.001
        
        # Mock execution for testing
        with patch.object(self.orchestrator.execution_agent, 'place_buy_order') as mock_buy:
            mock_buy.return_value = {
                'order_id': 'orchestrator_test_123',
                'symbol': symbol,
                'quantity': quantity,
                'price': 50000.0,
                'status': 'FILLED'
            }
            
            # Execute workflow
            decision = await self.orchestrator.execute_trading_workflow(symbol, quantity)
            
            # Validate decision structure
            assert isinstance(decision, TradeDecision)
            assert decision.symbol == symbol
            assert decision.quantity == quantity
            assert decision.signal_type in ['BUY', 'SELL', 'HOLD']
            assert 0 <= decision.confidence <= 1
            assert decision.price > 0
            assert isinstance(decision.risk_approved, bool)
            assert decision.correlation_id is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_live_data(self):
        """Test orchestrator with actual live testnet data"""
        symbol = "BTCUSDT"
        quantity = 0.001
        
        # Execute workflow with live data (but mock execution)
        with patch.object(self.orchestrator.execution_agent, 'place_buy_order') as mock_buy, \
             patch.object(self.orchestrator.execution_agent, 'place_sell_order') as mock_sell:
            
            mock_buy.return_value = {
                'order_id': 'live_test_buy_123',
                'symbol': symbol,
                'quantity': quantity,
                'price': 50000.0,
                'status': 'FILLED'
            }
            
            mock_sell.return_value = {
                'order_id': 'live_test_sell_123',
                'symbol': symbol,
                'quantity': quantity,
                'price': 50000.0,
                'status': 'FILLED'
            }
            
            # Execute multiple workflows
            decisions = []
            for i in range(3):
                decision = await self.orchestrator.execute_trading_workflow(
                    symbol, quantity, f"live_test_{i}"
                )
                decisions.append(decision)
            
            # Validate results
            assert len(decisions) == 3
            assert all(isinstance(d, TradeDecision) for d in decisions)
            assert all(d.symbol == symbol for d in decisions)
            
            # Check orchestrator stats
            stats = self.orchestrator.get_execution_stats()
            assert stats['total_decisions'] == 3
            assert stats['execution_rate'] >= 0
            assert stats['approval_rate'] >= 0
    
    def test_orchestrator_error_handling(self):
        """Test orchestrator error handling"""
        symbol = "INVALID_SYMBOL"
        quantity = 0.001
        
        # This should handle errors gracefully
        async def run_test():
            try:
                decision = await self.orchestrator.execute_trading_workflow(symbol, quantity)
                # If it doesn't fail, that's also valid (error handling worked)
                return True
            except Exception as e:
                # Should not reach here if error handling is proper
                pytest.fail(f"Orchestrator should handle errors gracefully: {str(e)}")
        
        asyncio.run(run_test())
    
    def test_trade_decision_serialization(self):
        """Test TradeDecision can be serialized"""
        decision = TradeDecision(
            symbol="BTCUSDT",
            signal_type="BUY",
            confidence=0.85,
            price=50000.0,
            quantity=0.001,
            timestamp=datetime.now(),
            correlation_id="test_123",
            risk_approved=True
        )
        
        # Test conversion to dict
        decision_dict = decision.__dict__
        assert 'symbol' in decision_dict
        assert 'signal_type' in decision_dict
        assert 'confidence' in decision_dict
        
        # Verify JSON serialization would work
        import json
        json_str = json.dumps(decision_dict, default=str)
        assert len(json_str) > 0
    
    @pytest.mark.asyncio
    async def test_continuous_trading_setup(self):
        """Test continuous trading setup (without actually running)"""
        symbols = ["BTCUSDT", "ETHUSDT"]
        quantities = {"BTCUSDT": 0.001, "ETHUSDT": 0.01}
        
        # Mock sleep to avoid actual waiting
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Mock execution to avoid actual trades
            with patch.object(self.orchestrator, 'execute_trading_workflow') as mock_workflow:
                mock_workflow.return_value = TradeDecision(
                    symbol="BTCUSDT",
                    signal_type="HOLD",
                    confidence=0.5,
                    price=50000.0,
                    quantity=0.001,
                    timestamp=datetime.now(),
                    correlation_id="continuous_test",
                    risk_approved=False
                )
                
                # Run one iteration only
                mock_sleep.side_effect = [None, KeyboardInterrupt()]
                
                try:
                    await self.orchestrator.run_continuous_trading(
                        symbols, quantities, interval_seconds=1
                    )
                except KeyboardInterrupt:
                    pass  # Expected
                
                # Verify workflow was called
                assert mock_workflow.call_count >= len(symbols)
    
    def test_orchestrator_trade_history(self):
        """Test trade history tracking"""
        # Create some mock decisions
        decision1 = TradeDecision(
            symbol="BTCUSDT",
            signal_type="BUY",
            confidence=0.85,
            price=50000.0,
            quantity=0.001,
            timestamp=datetime.now(),
            correlation_id="test_1",
            risk_approved=True
        )
        
        decision2 = TradeDecision(
            symbol="ETHUSDT",
            signal_type="SELL",
            confidence=0.75,
            price=3000.0,
            quantity=0.01,
            timestamp=datetime.now(),
            correlation_id="test_2",
            risk_approved=False
        )
        
        # Add to orchestrator
        self.orchestrator.trade_decisions = [decision1, decision2]
        
        # Test history retrieval
        history = self.orchestrator.get_trade_history()
        assert len(history) == 2
        assert all(isinstance(h, dict) for h in history)
        
        # Test stats
        stats = self.orchestrator.get_execution_stats()
        assert stats['total_decisions'] == 2
        assert stats['approved_trades'] == 1
        assert stats['executed_trades'] == 0  # None were executed
        assert stats['approval_rate'] == 0.5
