"""
Trading Agent Orchestrator - Coordinates the full trading workflow
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import json

from .market_data_agent import MarketDataAgent
from .signal_agent import SignalAgent
from .risk_management_agent import RiskManagementAgent
from .trade_execution_agent import TradeExecutionAgent
from .config import config


@dataclass
class TradeDecision:
    """Trade decision data structure"""
    symbol: str
    signal_type: str
    confidence: float
    price: float
    quantity: float
    timestamp: datetime
    correlation_id: str
    risk_approved: bool
    executed: bool = False
    order_id: Optional[str] = None
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None


class TradingOrchestrator:
    """Orchestrates the complete trading workflow"""
    
    def __init__(self, strategy_name: str = None, strategy_parameters: Dict[str, Any] = None):
        """
        Initialize TradingOrchestrator with optional strategy configuration
        
        Args:
            strategy_name: Name of strategy to use (optional)
            strategy_parameters: Custom strategy parameters (optional)
        """
        self.market_agent = MarketDataAgent()
        self.signal_agent = SignalAgent(
            market_data_agent=self.market_agent,
            strategy_name=strategy_name,
            strategy_parameters=strategy_parameters
        )
        self.risk_agent = RiskManagementAgent()
        self.execution_agent = TradeExecutionAgent()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Trade history
        self.trade_decisions: List[TradeDecision] = []
    
    async def execute_trading_workflow(
        self, 
        symbol: str, 
        quantity: float,
        correlation_id: Optional[str] = None,
        strategy_name: Optional[str] = None
    ) -> TradeDecision:
        """
        Execute the complete trading workflow:
        MarketDataAgent → SignalAgent → RiskManagementAgent → TradeExecutionAgent
        
        Args:
            symbol: Trading symbol
            quantity: Trading quantity
            correlation_id: Optional correlation ID for tracking
            strategy_name: Optional strategy override
        """
        if not correlation_id:
            correlation_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Add correlation ID to logger context
        extra = {'correlation_id': correlation_id}
        
        self.logger.info(f"Starting trading workflow for {symbol}", extra=extra)
        if strategy_name:
            self.logger.info(f"Using strategy override: {strategy_name}", extra=extra)
        
        try:
            # Step 1: Get market data
            self.logger.info("Step 1: Fetching market data", extra=extra)
            price = await self._get_market_data(symbol, correlation_id)
            
            # Step 2: Generate trading signal (with optional strategy override)
            self.logger.info("Step 2: Generating trading signal", extra=extra)
            signal_result = await self._generate_signal(symbol, correlation_id, strategy_name)
            
            # Step 3: Risk management validation
            self.logger.info("Step 3: Risk management validation", extra=extra)
            risk_approved = await self._validate_risk(
                symbol, signal_result['signal'], quantity, price, correlation_id
            )
            
            # Create trade decision
            trade_decision = TradeDecision(
                symbol=symbol,
                signal_type=signal_result['signal'],
                confidence=signal_result['confidence'],
                price=price,
                quantity=quantity,
                timestamp=datetime.now(),
                correlation_id=correlation_id,
                risk_approved=risk_approved
            )
            
            # Step 4: Execute trade if approved
            if risk_approved:
                self.logger.info("Step 4: Executing trade", extra=extra)
                execution_result = await self._execute_trade(trade_decision, correlation_id)
                
                if execution_result:
                    trade_decision.executed = True
                    trade_decision.order_id = execution_result.get('order_id')
                    trade_decision.execution_price = execution_result.get('price')
                    trade_decision.execution_time = datetime.now()
            else:
                self.logger.info(
                    f"Trade not executed - Risk approved: {risk_approved}, "
                    f"Signal: {signal_result['signal']}", 
                    extra=extra
                )
            
            # Store decision
            self.trade_decisions.append(trade_decision)
            
            self.logger.info(
                f"Trading workflow completed - Executed: {trade_decision.executed}",
                extra=extra
            )
            
            return trade_decision
            
        except Exception as e:
            self.logger.error(f"Trading workflow failed: {str(e)}", extra=extra)
            raise
    
    async def _get_market_data(self, symbol: str, correlation_id: str) -> float:
        """Get latest market price"""
        try:
            price = self.market_agent.get_latest_price(symbol)
            self.logger.info(
                f"Market data retrieved - {symbol}: ${price:,.2f}",
                extra={'correlation_id': correlation_id}
            )
            return price
        except Exception as e:
            self.logger.error(
                f"Market data retrieval failed: {str(e)}",
                extra={'correlation_id': correlation_id}
            )
            raise
    
    async def _generate_signal(self, symbol: str, correlation_id: str, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate trading signal with optional strategy override"""
        try:
            signal_result = self.signal_agent.generate_signal(symbol, strategy_name)
            self.logger.info(
                f"Signal generated - {signal_result['signal'].upper()} "
                f"(confidence: {signal_result['confidence']:.1%})",
                extra={'correlation_id': correlation_id}
            )
            return signal_result
        except Exception as e:
            self.logger.error(
                f"Signal generation failed: {str(e)}",
                extra={'correlation_id': correlation_id}
            )
            raise
    
    async def _validate_risk(
        self, 
        symbol: str, 
        signal: str, 
        quantity: float, 
        price: float,
        correlation_id: str
    ) -> bool:
        """Validate trade against risk management rules"""
        try:
            risk_result = self.risk_agent.validate_trade(
                symbol=symbol,
                side=signal.lower(),
                quantity=quantity,
                price=price
            )
            
            approved = risk_result.get('approved', False)
            reason = risk_result.get('reason', 'No reason provided')
            
            self.logger.info(
                f"Risk validation - Approved: {approved}, Reason: {reason}",
                extra={'correlation_id': correlation_id}
            )
            
            return approved
        except Exception as e:
            self.logger.error(
                f"Risk validation failed: {str(e)}",
                extra={'correlation_id': correlation_id}
            )
            return False
    
    async def _execute_trade(
        self, 
        trade_decision: TradeDecision, 
        correlation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Execute the trade"""
        try:
            # Normalize signal type to uppercase
            signal_upper = trade_decision.signal_type.upper()
            
            if signal_upper == 'BUY':
                result = self.execution_agent.place_buy_order(
                    symbol=trade_decision.symbol,
                    quantity=trade_decision.quantity
                )
            elif signal_upper == 'SELL':
                result = self.execution_agent.place_sell_order(
                    symbol=trade_decision.symbol,
                    quantity=trade_decision.quantity
                )
            else:
                self.logger.warning(
                    f"Invalid signal type for execution: {trade_decision.signal_type}",
                    extra={'correlation_id': correlation_id}
                )
                return None
            
            self.logger.info(
                f"Trade executed - Order ID: {result.get('order_id')}",
                extra={'correlation_id': correlation_id}
            )
            
            return result
        except Exception as e:
            self.logger.error(
                f"Trade execution failed: {str(e)}",
                extra={'correlation_id': correlation_id}
            )
            return None
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Get trade decision history"""
        return [asdict(decision) for decision in self.trade_decisions]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        total_decisions = len(self.trade_decisions)
        executed_trades = sum(1 for d in self.trade_decisions if d.executed)
        approved_trades = sum(1 for d in self.trade_decisions if d.risk_approved)
        
        return {
            'total_decisions': total_decisions,
            'approved_trades': approved_trades,
            'executed_trades': executed_trades,
            'execution_rate': executed_trades / total_decisions if total_decisions > 0 else 0,
            'approval_rate': approved_trades / total_decisions if total_decisions > 0 else 0
        }
    
    async def run_continuous_trading(
        self, 
        symbols: List[str], 
        quantities: Dict[str, float],
        interval_seconds: int = 300
    ):
        """Run continuous trading loop"""
        self.logger.info(f"Starting continuous trading for {symbols}")
        
        while True:
            for symbol in symbols:
                try:
                    quantity = quantities.get(symbol, 0.01)
                    await self.execute_trading_workflow(symbol, quantity)
                except Exception as e:
                    self.logger.error(f"Error in continuous trading for {symbol}: {str(e)}")
            
            self.logger.info(f"Sleeping for {interval_seconds} seconds")
            await asyncio.sleep(interval_seconds)
    
    def set_strategy(self, strategy_name: str) -> bool:
        """
        Change the trading strategy for all future operations
        
        Args:
            strategy_name: Name of strategy to use
            
        Returns:
            True if strategy was set successfully
        """
        return self.signal_agent.set_strategy(strategy_name)
    
    def get_available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available trading strategies"""
        return self.signal_agent.get_available_strategies()
    
    def compare_strategies_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Compare all available strategies for a specific symbol
        
        Args:
            symbol: Trading symbol to analyze
            
        Returns:
            Strategy comparison results
        """
        return self.signal_agent.compare_strategies(symbol)
    
    def create_custom_strategy(self, name: str, strategy_type: str, parameters: Dict[str, Any]) -> bool:
        """
        Create a custom trading strategy
        
        Args:
            name: Unique name for the strategy
            strategy_type: Type of strategy ('rsi', 'macd', 'combined')
            parameters: Strategy parameters
            
        Returns:
            True if strategy was created successfully
        """
        return self.signal_agent.create_custom_strategy(name, strategy_type, parameters)
    
    async def analyze_market_with_all_strategies(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze a symbol with all available strategies without executing trades
        
        Args:
            symbol: Trading symbol to analyze
            
        Returns:
            Comprehensive analysis from all strategies
        """
        correlation_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        extra = {'correlation_id': correlation_id}
        
        try:
            # Get market data
            price = await self._get_market_data(symbol, correlation_id)
            
            # Get strategy comparison
            strategy_comparison = self.signal_agent.compare_strategies(symbol)
            
            # Get current strategy info
            current_strategy_info = self.signal_agent.get_current_strategy_info()
            
            return {
                'symbol': symbol,
                'current_price': price,
                'timestamp': datetime.now().isoformat(),
                'current_strategy': self.signal_agent.current_strategy_name,
                'current_strategy_info': current_strategy_info,
                'strategy_comparison': strategy_comparison,
                'correlation_id': correlation_id
            }
            
        except Exception as e:
            self.logger.error(f"Market analysis failed for {symbol}: {str(e)}", extra=extra)
            return {
                'symbol': symbol,
                'error': str(e),
                'correlation_id': correlation_id
            }
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all strategies"""
        return self.signal_agent.get_strategy_performance()
    
    async def backtest_strategy(self, strategy_name: str, symbol: str, 
                              historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Backtest a strategy against historical data
        
        Args:
            strategy_name: Name of strategy to test
            symbol: Trading symbol
            historical_data: Historical OHLCV data
            
        Returns:
            Backtest results
        """
        # This is a simplified backtest - in production you'd want more sophisticated backtesting
        results = []
        strategy = self.signal_agent.strategy_manager.get_strategy(strategy_name)
        
        if not strategy:
            return {'error': f'Strategy {strategy_name} not found'}
        
        try:
            # Analyze each data point
            for i in range(strategy.requires_minimum_data(), len(historical_data)):
                data_slice = historical_data[:i+1]
                result = strategy.analyze(data_slice, symbol)
                
                results.append({
                    'timestamp': i,
                    'price': float(historical_data[i]['close']),
                    'signal': result.signal.value,
                    'confidence': result.confidence,
                    'indicators': result.indicators
                })
            
            # Calculate basic statistics
            signals = [r['signal'] for r in results]
            buy_signals = signals.count('BUY')
            sell_signals = signals.count('SELL')
            hold_signals = signals.count('HOLD')
            
            avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0
            
            return {
                'strategy_name': strategy_name,
                'symbol': symbol,
                'total_signals': len(results),
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'hold_signals': hold_signals,
                'average_confidence': avg_confidence,
                'results': results[-10:] if len(results) > 10 else results  # Last 10 for brevity
            }
            
        except Exception as e:
            return {'error': f'Backtest failed: {str(e)}'}


# Enhanced demo function showcasing strategy capabilities
async def demo_orchestration():
    """Enhanced demo showcasing the trading orchestration workflow with modular strategies"""
    print("=== Enhanced Trading Orchestration Demo ===")
    
    orchestrator = TradingOrchestrator()
    
    print(f"\n1. Current Configuration:")
    print(f"   Default Strategy: {orchestrator.signal_agent.current_strategy_name}")
    
    available_strategies = orchestrator.get_available_strategies()
    print(f"   Available Strategies: {len(available_strategies)}")
    for name, info in list(available_strategies.items())[:3]:  # Show first 3
        print(f"     - {name}: {info['description']}")
    
    print(f"\n2. Market Analysis with All Strategies:")
    try:
        analysis = await orchestrator.analyze_market_with_all_strategies("BTCUSDT")
        if 'error' not in analysis:
            print(f"   Symbol: {analysis['symbol']}")
            print(f"   Current Price: ${analysis['current_price']:,.2f}")
            
            if 'strategy_comparison' in analysis:
                comparison = analysis['strategy_comparison']
                if 'consensus' in comparison:
                    consensus = comparison['consensus']
                    print(f"   Strategy Consensus: {consensus['signal']} (strength: {consensus['strength']:.1%})")
                    print(f"   Best Strategy: {comparison['best_strategy']['name']}")
        else:
            print(f"   Analysis Error: {analysis['error']}")
    except Exception as e:
        print(f"   Analysis failed: {str(e)}")
    
    print(f"\n3. Creating Custom Strategy:")
    custom_params = {
        'rsi_period': 21,
        'rsi_overbought': 75,
        'rsi_oversold': 25,
        'macd_fast_period': 10,
        'macd_slow_period': 22
    }
    
    success = orchestrator.create_custom_strategy('demo_custom', 'combined', custom_params)
    if success:
        print(f"   ✓ Custom strategy 'demo_custom' created successfully")
        
        # Switch to custom strategy
        if orchestrator.set_strategy('demo_custom'):
            print(f"   ✓ Switched to custom strategy")
        else:
            print(f"   ✗ Failed to switch to custom strategy")
    else:
        print(f"   ✗ Failed to create custom strategy")
    
    print(f"\n4. Execute Trading Workflow:")
    # Execute with default strategy
    try:
        decision = await orchestrator.execute_trading_workflow(
            symbol="BTCUSDT",
            quantity=config.get_default_quantity("BTCUSDT")
        )
        
        print(f"   Symbol: {decision.symbol}")
        print(f"   Signal: {decision.signal_type}")
        print(f"   Confidence: {decision.confidence:.1%}")
        print(f"   Price: ${decision.price:,.2f}")
        print(f"   Risk Approved: {decision.risk_approved}")
        print(f"   Executed: {decision.executed}")
        
        if decision.executed:
            print(f"   Order ID: {decision.order_id}")
            print(f"   Execution Price: ${decision.execution_price:,.2f}")
    except Exception as e:
        print(f"   Workflow Error: {str(e)}")
    
    print(f"\n5. Strategy Comparison:")
    try:
        comparison = orchestrator.compare_strategies_for_symbol("BTCUSDT")
        if 'error' not in comparison:
            print(f"   Consensus: {comparison['consensus']['signal']} "
                  f"(strength: {comparison['consensus']['strength']:.1%})")
            print(f"   Recommendation: {comparison['recommendation']}")
            
            # Show individual strategy results
            strategy_results = comparison.get('strategy_results', {})
            print(f"   Individual Results:")
            for strategy_name, result in list(strategy_results.items())[:3]:  # Show first 3
                print(f"     {strategy_name}: {result['signal']} (confidence: {result['confidence']:.1%})")
        else:
            print(f"   Comparison Error: {comparison['error']}")
    except Exception as e:
        print(f"   Comparison failed: {str(e)}")
    
    print(f"\n6. Strategy Performance:")
    try:
        performance = orchestrator.get_strategy_performance_summary()
        if performance and not isinstance(performance, dict) or 'error' not in performance:
            print(f"   Tracked strategies: {len(performance) if isinstance(performance, dict) else 'N/A'}")
            if isinstance(performance, dict):
                for strategy_name, perf in list(performance.items())[:2]:  # Show first 2
                    total = perf.get('total_signals', 0)
                    avg_conf = perf.get('average_confidence', 0)
                    print(f"     {strategy_name}: {total} signals, avg confidence: {avg_conf:.1%}")
        else:
            print(f"   No performance data available yet")
    except Exception as e:
        print(f"   Performance tracking error: {str(e)}")
    
    # Show stats
    stats = orchestrator.get_execution_stats()
    print(f"\n7. Execution Stats:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.1%}")
        else:
            print(f"   {key}: {value}")
    
    print(f"\n=== Enhanced Demo Complete ===")
    print(f"New Strategy Features:")
    print(f"- ✓ Multiple modular strategies (RSI, MACD, Combined)")
    print(f"- ✓ Easy strategy switching and comparison")
    print(f"- ✓ Custom strategy creation with parameters")
    print(f"- ✓ Strategy performance tracking")
    print(f"- ✓ Market analysis with consensus building")
    print(f"- ✓ Full backward compatibility maintained")


if __name__ == "__main__":
    asyncio.run(demo_orchestration())