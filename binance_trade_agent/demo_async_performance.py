"""
Performance comparison demo: Sync vs Async trading operations
Demonstrates the performance benefits of async operations with concurrent execution
"""
import asyncio
import time
from typing import List
from binance_trade_agent.orchestrator import TradingOrchestrator
from binance_trade_agent.async_orchestrator import AsyncTradingOrchestrator


async def run_async_multi_symbol_test(symbols: List[str]):
    """Run async workflow for multiple symbols concurrently"""
    print("\n" + "="*80)
    print("ASYNC WORKFLOW - Multiple Symbols Concurrently")
    print("="*80)
    
    start_time = time.time()
    
    async with AsyncTradingOrchestrator() as async_orchestrator:
        # Prepare symbol/quantity pairs
        symbols_quantities = [
            {'symbol': symbol, 'quantity': 0.001}
            for symbol in symbols
        ]
        
        # Execute all workflows concurrently
        decisions = await async_orchestrator.execute_multi_symbol_workflow(
            symbols_quantities,
            strategy_name='rsi_default'
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ Processed {len(decisions)} symbols in {duration:.3f} seconds")
        print(f"📊 Average per symbol: {duration/len(symbols):.3f} seconds")
        
        for decision in decisions:
            print(f"\n{decision.symbol}:")
            print(f"  Signal: {decision.signal_type} (confidence: {decision.confidence:.1%})")
            print(f"  Price: ${decision.price:,.2f}")
            print(f"  Execution time: {decision.execution_duration_ms:.2f}ms")
            print(f"  Risk approved: {decision.risk_approved}")
            print(f"  Executed: {decision.executed}")
    
    return duration


def run_sync_multi_symbol_test(symbols: List[str]):
    """Run sync workflow for multiple symbols sequentially"""
    print("\n" + "="*80)
    print("SYNC WORKFLOW - Multiple Symbols Sequentially")
    print("="*80)
    
    start_time = time.time()
    
    orchestrator = TradingOrchestrator(strategy_name='rsi_default')
    decisions = []
    
    # Execute workflows sequentially
    for symbol in symbols:
        try:
            decision = asyncio.run(
                orchestrator.execute_trading_workflow(
                    symbol=symbol,
                    quantity=0.001
                )
            )
            decisions.append(decision)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n✅ Processed {len(decisions)} symbols in {duration:.3f} seconds")
    print(f"📊 Average per symbol: {duration/len(symbols):.3f} seconds")
    
    for decision in decisions:
        print(f"\n{decision.symbol}:")
        print(f"  Signal: {decision.signal_type} (confidence: {decision.confidence:.1%})")
        print(f"  Price: ${decision.price:,.2f}")
        print(f"  Risk approved: {decision.risk_approved}")
        print(f"  Executed: {decision.executed}")
    
    return duration


async def run_async_portfolio_snapshot_test(symbols: List[str]):
    """Test concurrent portfolio snapshot fetching"""
    print("\n" + "="*80)
    print("ASYNC PORTFOLIO SNAPSHOT - Concurrent Price Fetching")
    print("="*80)
    
    start_time = time.time()
    
    async with AsyncTradingOrchestrator() as async_orchestrator:
        snapshot = await async_orchestrator.get_portfolio_snapshot(symbols)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ Fetched prices for {len(symbols)} symbols in {duration:.3f} seconds")
        print(f"📊 Average per symbol: {duration/len(symbols):.3f} seconds")
        
        print("\nPrices:")
        for symbol, price in snapshot['prices'].items():
            if price is not None:
                print(f"  {symbol}: ${price:,.2f}")
            else:
                print(f"  {symbol}: Failed to fetch")
    
    return duration


async def main():
    """Run performance comparison tests"""
    print("\n" + "="*80)
    print("ASYNC OPTIMIZATION PERFORMANCE COMPARISON")
    print("="*80)
    print("\nComparing sync vs async performance for trading operations")
    print("Using demo mode for safe testing\n")
    
    # Test symbols
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
    
    # Test 1: Sync multi-symbol workflow
    print("\n" + "-"*80)
    print("TEST 1: Sequential (Sync) Multi-Symbol Workflow")
    print("-"*80)
    sync_duration = run_sync_multi_symbol_test(symbols)
    
    # Test 2: Async multi-symbol workflow
    print("\n" + "-"*80)
    print("TEST 2: Concurrent (Async) Multi-Symbol Workflow")
    print("-"*80)
    async_duration = await run_async_multi_symbol_test(symbols)
    
    # Test 3: Async portfolio snapshot
    print("\n" + "-"*80)
    print("TEST 3: Concurrent Portfolio Snapshot")
    print("-"*80)
    snapshot_duration = await run_async_portfolio_snapshot_test(symbols)
    
    # Performance summary
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    print(f"\nSync workflow total time:     {sync_duration:.3f} seconds")
    print(f"Async workflow total time:    {async_duration:.3f} seconds")
    print(f"Portfolio snapshot time:      {snapshot_duration:.3f} seconds")
    print(f"\n🚀 Performance improvement:   {(sync_duration/async_duration):.2f}x faster")
    print(f"⚡ Time saved:                {sync_duration - async_duration:.3f} seconds ({((sync_duration - async_duration)/sync_duration*100):.1f}%)")
    
    print("\n" + "="*80)
    print("KEY BENEFITS OF ASYNC OPTIMIZATION")
    print("="*80)
    print("""
1. ⚡ Concurrent Execution: Multiple API calls execute simultaneously
2. 🔄 Non-blocking I/O: System doesn't wait idle during network requests
3. 📈 Better Resource Utilization: CPU and network bandwidth used efficiently
4. 🎯 Lower Latency: Faster response times for trading decisions
5. 📊 Scalability: Can handle more symbols without linear time increase
    """)


if __name__ == "__main__":
    asyncio.run(main())
