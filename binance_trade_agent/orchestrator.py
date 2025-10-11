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
    
    def __init__(self):
        self.market_agent = MarketDataAgent()
        self.signal_agent = SignalAgent()
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
        correlation_id: Optional[str] = None
    ) -> TradeDecision:
        """
        Execute the complete trading workflow:
        MarketDataAgent → SignalAgent → RiskManagementAgent → TradeExecutionAgent
        """
        if not correlation_id:
            correlation_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Add correlation ID to logger context
        extra = {'correlation_id': correlation_id}
        
        self.logger.info(f"Starting trading workflow for {symbol}", extra=extra)
        
        try:
            # Step 1: Get market data
            self.logger.info("Step 1: Fetching market data", extra=extra)
            price = await self._get_market_data(symbol, correlation_id)
            
            # Step 2: Generate trading signal
            self.logger.info("Step 2: Generating trading signal", extra=extra)
            signal_result = await self._generate_signal(symbol, correlation_id)
            
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
            if risk_approved and signal_result['signal'] in ['BUY', 'SELL']:
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
    
    async def _generate_signal(self, symbol: str, correlation_id: str) -> Dict[str, Any]:
        """Generate trading signal"""
        try:
            signal_result = self.signal_agent.generate_signal(symbol)
            self.logger.info(
                f"Signal generated - {signal_result['signal']} "
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
            if trade_decision.signal_type == 'BUY':
                result = self.execution_agent.place_buy_order(
                    symbol=trade_decision.symbol,
                    quantity=trade_decision.quantity
                )
            elif trade_decision.signal_type == 'SELL':
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


# Demo function for testing
async def demo_orchestration():
    """Demo the trading orchestration workflow"""
    orchestrator = TradingOrchestrator()
    
    print("=== Trading Orchestration Demo ===")
    
    # Execute single workflow
    decision = await orchestrator.execute_trading_workflow(
        symbol="BTCUSDT",
        quantity=0.001
    )
    
    print(f"\nTrade Decision:")
    print(f"Symbol: {decision.symbol}")
    print(f"Signal: {decision.signal_type}")
    print(f"Confidence: {decision.confidence:.1%}")
    print(f"Price: ${decision.price:,.2f}")
    print(f"Risk Approved: {decision.risk_approved}")
    print(f"Executed: {decision.executed}")
    
    if decision.executed:
        print(f"Order ID: {decision.order_id}")
        print(f"Execution Price: ${decision.execution_price:,.2f}")
    
    # Show stats
    stats = orchestrator.get_execution_stats()
    print(f"\nExecution Stats:")
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo_orchestration())