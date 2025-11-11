#!/usr/bin/env python3
"""
Autonomous Trading Loop - Continuous trading with configurable intervals
Executes trading workflow repeatedly until time limit or manual stop
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# Add the parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance_trade_agent.orchestrator import TradingOrchestrator
from binance_trade_agent.config import config
from binance_trade_agent.monitoring import monitoring


class AutonomousTradingLoop:
    """
    Continuous autonomous trading loop
    """
    
    def __init__(
        self,
        symbols: list = None,
        trade_interval_seconds: int = 120,
        duration_minutes: int = 60,
        strategy_name: str = None,
        strategy_parameters: dict = None
    ):
        """
        Initialize the autonomous trading loop
        
        Args:
            symbols: List of symbols to trade (default: [BTCUSDT, ETHUSDT])
            trade_interval_seconds: Seconds between trades (minimum 60 for testnet)
            duration_minutes: Total duration to run (0 = infinite)
            strategy_name: Trading strategy to use
            strategy_parameters: Custom strategy parameters
        """
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        self.trade_interval = max(trade_interval_seconds, 60)  # Min 60 seconds for testnet
        self.duration_minutes = duration_minutes
        self.strategy_name = strategy_name or 'combined_default'
        self.strategy_parameters = strategy_parameters
        
        # Initialize orchestrator
        self.orchestrator = TradingOrchestrator(
            strategy_name=self.strategy_name,
            strategy_parameters=self.strategy_parameters
        )
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.info(
            f"AutonomousTradingLoop initialized:\n"
            f"  Symbols: {self.symbols}\n"
            f"  Interval: {self.trade_interval}s\n"
            f"  Duration: {self.duration_minutes} min\n"
            f"  Strategy: {self.strategy_name}"
        )
        
        # Tracking
        self.trades_executed = 0
        self.start_time = None
        self.stop_flag = False
        
    async def run(self):
        """
        Run the autonomous trading loop
        """
        self.start_time = datetime.now()
        end_time = self.start_time + timedelta(minutes=self.duration_minutes) if self.duration_minutes > 0 else None
        
        self.logger.info(f"🚀 Starting autonomous trading loop...")
        if end_time:
            self.logger.info(f"   Will run until: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.logger.info(f"   Running indefinitely (press Ctrl+C to stop)")
        
        cycle = 0
        while not self.stop_flag:
            # Check if time limit reached
            if end_time and datetime.now() >= end_time:
                self.logger.info(f"⏰ Time limit reached. Stopping autonomous trading.")
                break
            
            cycle += 1
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"Trading Cycle #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
            self.logger.info(f"{'='*70}")
            
            # Execute trades for each symbol
            for symbol in self.symbols:
                if self.stop_flag:
                    break
                    
                try:
                    self.logger.info(f"\n📊 Processing {symbol}...")
                    
                    # Get default quantity
                    quantity = config.get_default_quantity(symbol)
                    
                    # Execute trading workflow
                    decision = await self.orchestrator.execute_trading_workflow(
                        symbol=symbol,
                        quantity=quantity
                    )
                    
                    # Log decision
                    self.logger.info(
                        f"  Signal: {decision.signal_type.upper()}\n"
                        f"  Confidence: {decision.confidence:.1%}\n"
                        f"  Price: ${decision.price:,.2f}\n"
                        f"  Risk Approved: {decision.risk_approved}"
                    )
                    
                    if decision.executed:
                        self.trades_executed += 1
                        exec_price = f"${decision.execution_price:,.2f}" if decision.execution_price else "N/A"
                        exec_time = decision.execution_time.strftime('%H:%M:%S') if decision.execution_time else 'N/A'
                        self.logger.info(
                            f"  ✅ TRADE EXECUTED!\n"
                            f"     Order ID: {decision.order_id}\n"
                            f"     Fill Price: {exec_price}\n"
                            f"     Time: {exec_time}"
                        )
                    else:
                        self.logger.info(f"  ⏸️ Trade not executed (risk check failed)")
                    
                except Exception as e:
                    self.logger.error(f"  ❌ Error processing {symbol}: {str(e)}", exc_info=True)
            
            # Log cycle summary
            elapsed = datetime.now() - self.start_time
            self.logger.info(f"\n📈 Cycle Summary:")
            self.logger.info(f"   Cycles completed: {cycle}")
            self.logger.info(f"   Trades executed: {self.trades_executed}")
            self.logger.info(f"   Time elapsed: {elapsed}")
            
            # Wait before next cycle (unless it's the last iteration)
            if not self.stop_flag:
                if end_time and datetime.now() >= end_time:
                    break
                    
                self.logger.info(f"\n⏳ Waiting {self.trade_interval} seconds before next cycle...")
                try:
                    await asyncio.sleep(self.trade_interval)
                except asyncio.CancelledError:
                    self.logger.info("Interrupted by user during sleep")
                    self.stop_flag = True
        
        # Final summary
        elapsed = datetime.now() - self.start_time
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"🏁 TRADING SESSION COMPLETE")
        self.logger.info(f"{'='*70}")
        self.logger.info(f"Total cycles: {cycle}")
        self.logger.info(f"Total trades executed: {self.trades_executed}")
        self.logger.info(f"Total time: {elapsed}")
        self.logger.info(f"Average trades per minute: {(self.trades_executed / elapsed.total_seconds() * 60):.2f}")


async def main():
    """
    Main entry point
    """
    # Get configuration from environment
    symbols = os.getenv('TRADING_SYMBOLS', 'BTCUSDT,ETHUSDT').split(',')
    interval = int(os.getenv('TRADING_INTERVAL_SECONDS', '120'))
    duration = int(os.getenv('TRADING_DURATION_MINUTES', '60'))
    strategy = os.getenv('STRATEGY_NAME', 'combined_default')
    
    # Create and run loop
    loop = AutonomousTradingLoop(
        symbols=symbols,
        trade_interval_seconds=interval,
        duration_minutes=duration,
        strategy_name=strategy
    )
    
    try:
        await loop.run()
    except KeyboardInterrupt:
        print("\n\n⛔ Interrupted by user. Shutting down gracefully...")
        loop.stop_flag = True


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run
    asyncio.run(main())
