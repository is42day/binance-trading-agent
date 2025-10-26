"""
Async Trading Orchestrator - High-performance orchestration with concurrent operations
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from .async_market_data_agent import AsyncMarketDataAgent
from .async_binance_client import AsyncBinanceClient
from .signal_agent import SignalAgent
from .risk_management_agent import RiskManagementAgent
from .trade_execution_agent import TradeExecutionAgent
from .config import config


@dataclass
class AsyncTradeDecision:
    """Trade decision data structure for async operations"""
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
    execution_duration_ms: Optional[float] = None


class AsyncTradingOrchestrator:
    """
    High-performance async trading orchestrator
    Uses asyncio.gather() for concurrent operations where possible
    """
    
    def __init__(
        self,
        strategy_name: str = None,
        strategy_parameters: Dict[str, Any] = None
    ):
        """
        Initialize AsyncTradingOrchestrator
        
        Args:
            strategy_name: Name of strategy to use (optional)
            strategy_parameters: Custom strategy parameters (optional)
        """
        # Shared async client with connection pooling
        self.binance_client = AsyncBinanceClient()
        
        # Async market data agent with shared client
        self.async_market_agent = AsyncMarketDataAgent(self.binance_client)
        
        # Signal agent (can use async market agent internally)
        self.signal_agent = SignalAgent(
            market_data_agent=None,  # Will use async calls directly
            strategy_name=strategy_name,
            strategy_parameters=strategy_parameters
        )
        
        # Risk and execution agents (to be converted to async)
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
        self.trade_decisions: List[AsyncTradeDecision] = []
    
    async def execute_trading_workflow(
        self,
        symbol: str,
        quantity: float,
        correlation_id: Optional[str] = None,
        strategy_name: Optional[str] = None
    ) -> AsyncTradeDecision:
        """
        Execute complete async trading workflow with concurrent operations where possible
        
        Args:
            symbol: Trading symbol
            quantity: Trading quantity
            correlation_id: Optional correlation ID for tracking
            strategy_name: Optional strategy override
            
        Returns:
            AsyncTradeDecision with execution details
        """
        start_time = datetime.now()
        
        if not correlation_id:
            correlation_id = f"async_trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        extra = {'correlation_id': correlation_id}
        self.logger.info(f"Starting ASYNC trading workflow for {symbol}", extra=extra)
        
        try:
            # Step 1: Fetch market data AND klines concurrently
            self.logger.info("Step 1: Fetching market data (concurrent)", extra=extra)
            price, klines = await asyncio.gather(
                self.async_market_agent.fetch_price(symbol),
                self.async_market_agent.fetch_klines(symbol, interval='1h', limit=100),
                return_exceptions=False
            )
            
            self.logger.info(
                f"Market data retrieved - {symbol}: ${price:,.2f} "
                f"with {len(klines)} klines",
                extra=extra
            )
            
            # Step 2: Generate trading signal (uses klines data)
            self.logger.info("Step 2: Generating trading signal", extra=extra)
            signal_result = await self._generate_signal_async(
                symbol, klines, correlation_id, strategy_name
            )
            
            # Step 3: Risk management validation
            self.logger.info("Step 3: Risk management validation", extra=extra)
            risk_approved = await self._validate_risk_async(
                symbol, signal_result['signal'], quantity, price, correlation_id
            )
            
            # Create trade decision
            trade_decision = AsyncTradeDecision(
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
            if risk_approved and signal_result['signal'] in ['BUY', 'SELL', 'buy', 'sell']:
                self.logger.info("Step 4: Executing trade", extra=extra)
                execution_result = await self._execute_trade_async(
                    trade_decision, correlation_id
                )
                
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
            
            # Calculate execution duration
            end_time = datetime.now()
            trade_decision.execution_duration_ms = (
                (end_time - start_time).total_seconds() * 1000
            )
            
            # Store decision
            self.trade_decisions.append(trade_decision)
            
            self.logger.info(
                f"ASYNC trading workflow completed in {trade_decision.execution_duration_ms:.2f}ms - "
                f"Executed: {trade_decision.executed}",
                extra=extra
            )
            
            return trade_decision
            
        except Exception as e:
            self.logger.error(f"ASYNC trading workflow failed: {str(e)}", extra=extra)
            raise
    
    async def execute_multi_symbol_workflow(
        self,
        symbols_quantities: List[Dict[str, Any]],
        strategy_name: Optional[str] = None
    ) -> List[AsyncTradeDecision]:
        """
        Execute trading workflow for multiple symbols concurrently
        
        Args:
            symbols_quantities: List of dicts with 'symbol' and 'quantity' keys
            strategy_name: Optional strategy override
            
        Returns:
            List of AsyncTradeDecisions
        """
        tasks = [
            self.execute_trading_workflow(
                symbol=item['symbol'],
                quantity=item['quantity'],
                strategy_name=strategy_name
            )
            for item in symbols_quantities
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log them
        decisions = []
        for symbol_qty, result in zip(symbols_quantities, results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Failed to execute workflow for {symbol_qty['symbol']}: {result}"
                )
            else:
                decisions.append(result)
        
        return decisions
    
    async def _generate_signal_async(
        self,
        symbol: str,
        klines: List[Dict[str, Any]],
        correlation_id: str,
        strategy_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate trading signal using klines data (async wrapper)"""
        try:
            # Note: signal_agent.generate_signal is sync, but we can wrap it
            # In a future optimization, we'd make strategy analysis async too
            loop = asyncio.get_event_loop()
            signal_result = await loop.run_in_executor(
                None,
                lambda: self.signal_agent.generate_signal(symbol, strategy_name)
            )
            
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
    
    async def _validate_risk_async(
        self,
        symbol: str,
        signal: str,
        quantity: float,
        price: float,
        correlation_id: str
    ) -> bool:
        """Validate trade against risk management rules (async wrapper)"""
        try:
            # Wrap sync risk validation in executor
            loop = asyncio.get_event_loop()
            risk_result = await loop.run_in_executor(
                None,
                lambda: self.risk_agent.validate_trade(
                    symbol=symbol,
                    side=signal.lower(),
                    quantity=quantity,
                    price=price
                )
            )
            
            approved = risk_result.get('approved', False)
            self.logger.info(
                f"Risk validation - {'APPROVED' if approved else 'REJECTED'}: "
                f"{risk_result.get('reason', 'No reason provided')}",
                extra={'correlation_id': correlation_id}
            )
            return approved
        except Exception as e:
            self.logger.error(
                f"Risk validation failed: {str(e)}",
                extra={'correlation_id': correlation_id}
            )
            return False
    
    async def _execute_trade_async(
        self,
        trade_decision: AsyncTradeDecision,
        correlation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Execute trade (async)"""
        try:
            # Use async Binance client for order placement
            order_result = await self.binance_client.create_order(
                symbol=trade_decision.symbol,
                side=trade_decision.signal_type.upper(),
                order_type='MARKET',
                quantity=trade_decision.quantity
            )
            
            self.logger.info(
                f"Order executed - ID: {order_result.get('orderId')}, "
                f"Status: {order_result.get('status')}",
                extra={'correlation_id': correlation_id}
            )
            
            return {
                'order_id': str(order_result.get('orderId')),
                'price': float(order_result.get('price', trade_decision.price)),
                'status': order_result.get('status')
            }
        except Exception as e:
            self.logger.error(
                f"Trade execution failed: {str(e)}",
                extra={'correlation_id': correlation_id}
            )
            return None
    
    async def get_portfolio_snapshot(
        self,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Get complete portfolio snapshot with concurrent price fetching
        
        Args:
            symbols: List of symbols to include in snapshot
            
        Returns:
            Portfolio snapshot with prices and metrics
        """
        try:
            # Fetch all prices concurrently
            prices = await self.async_market_agent.fetch_prices_batch(symbols)
            
            # Get balances concurrently (if needed)
            # balance_tasks = [self.binance_client.get_balance(asset) for asset in assets]
            # balances = await asyncio.gather(*balance_tasks)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'prices': prices,
                'symbols': symbols
            }
        except Exception as e:
            self.logger.error(f"Failed to get portfolio snapshot: {str(e)}")
            raise
    
    async def close(self):
        """Cleanup resources"""
        await self.async_market_agent.close()
        await self.binance_client.close()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
