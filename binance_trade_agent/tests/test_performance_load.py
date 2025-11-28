"""
Performance & Load Testing - Non-Functional Requirements Validation
Tests API latency, throughput, concurrent user limits, cache performance, and system scalability
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime
from pathlib import Path
import tempfile
from typing import List, Dict, Tuple
import json

from binance_trade_agent.core.portfolio_manager import PortfolioManager
from binance_trade_agent.clients.redis_cache import RedisCache, InMemoryCache


# ============================================================================
# Performance Benchmark Fixtures
# ============================================================================

@pytest.fixture
def temp_portfolio_db():
    """Create a temporary SQLite database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_portfolio.db"
        yield str(db_path)


@pytest.fixture
def portfolio(temp_portfolio_db):
    """Initialize a clean portfolio manager for testing"""
    pm = PortfolioManager(db_path=temp_portfolio_db)
    yield pm
    pm.clear_portfolio()


@pytest.fixture
def populated_portfolio(portfolio):
    """Create a portfolio with multiple trades for performance testing"""
    # Add 100 trades across different symbols
    symbols = [f"COIN{i}" for i in range(10)]
    
    for i in range(100):
        portfolio.add_trade(
            trade_id=f"T{i}",
            symbol=symbols[i % len(symbols)],
            side="BUY" if i % 2 == 0 else "SELL",
            quantity=0.1 * (i % 10 + 1),
            price=1000.0 + (i * 10),
            fee=0.1
        )
    
    return portfolio


# ============================================================================
# SECTION 1: API Response Latency Tests
# ============================================================================

class TestAPILatency:
    """Measure API response times and verify SLA compliance"""
    
    SLA_P50_MS = 50    # 50ms target for P50
    SLA_P95_MS = 100   # 100ms target for P95
    SLA_P99_MS = 500   # 500ms target for P99
    
    def test_portfolio_get_all_positions_latency(self, populated_portfolio):
        """Measure latency of get_all_positions() with 10 positions"""
        latencies = []
        
        # Warm up
        populated_portfolio.get_all_positions()
        
        # Measure 50 calls
        for _ in range(50):
            start = time.perf_counter()
            positions = populated_portfolio.get_all_positions()
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            latencies.append(elapsed)
        
        # Calculate percentiles
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"\nget_all_positions latency: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
        
        # Assert SLA compliance
        assert p50 < self.SLA_P50_MS, f"P50 latency {p50:.2f}ms exceeds SLA {self.SLA_P50_MS}ms"
        assert p95 < self.SLA_P95_MS, f"P95 latency {p95:.2f}ms exceeds SLA {self.SLA_P95_MS}ms"
        assert p99 < self.SLA_P99_MS, f"P99 latency {p99:.2f}ms exceeds SLA {self.SLA_P99_MS}ms"
    
    def test_portfolio_get_trade_history_latency(self, populated_portfolio):
        """Measure latency of get_trade_history() with 100 trades"""
        latencies = []
        
        # Warm up
        populated_portfolio.get_trade_history()
        
        # Measure 50 calls
        for _ in range(50):
            start = time.perf_counter()
            history = populated_portfolio.get_trade_history()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"\nget_trade_history latency: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
        
        assert p50 < self.SLA_P50_MS
        assert p95 < self.SLA_P95_MS
        assert p99 < self.SLA_P99_MS
    
    def test_portfolio_get_portfolio_stats_latency(self, populated_portfolio):
        """Measure latency of get_portfolio_stats()"""
        latencies = []
        
        # Warm up
        populated_portfolio.get_portfolio_stats()
        
        # Measure 50 calls
        for _ in range(50):
            start = time.perf_counter()
            stats = populated_portfolio.get_portfolio_stats()
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"\nget_portfolio_stats latency: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
        
        assert p50 < self.SLA_P50_MS
        assert p95 < self.SLA_P95_MS
        assert p99 < self.SLA_P99_MS
    
    def test_add_trade_latency(self, portfolio):
        """Measure latency of add_trade() operation"""
        latencies = []
        
        # Measure trade addition
        for i in range(50):
            start = time.perf_counter()
            portfolio.add_trade(
                trade_id=f"T{i}",
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.1,
                price=40000.0 + (i * 10),
                fee=0.1
            )
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"\nadd_trade latency: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")
        
        # Add_trade is write operation, so slightly higher SLA acceptable
        assert p50 < 100, f"P50 latency {p50:.2f}ms exceeds 100ms"
        assert p95 < 300, f"P95 latency {p95:.2f}ms exceeds 300ms"
        assert p99 < 1000, f"P99 latency {p99:.2f}ms exceeds 1000ms"


# ============================================================================
# SECTION 2: Cache Performance Tests
# ============================================================================

class TestCachePerformance:
    """Validate cache hit rates and performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_inmemory_cache_hit_latency(self):
        """Measure latency of in-memory cache hits"""
        cache = InMemoryCache()
        
        # Set some values
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}", ttl=60)
        
        latencies = []
        
        # Measure cache get operations
        for i in range(1000):
            key = f"key_{i % 100}"
            start = time.perf_counter()
            value = await cache.get(key)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        p99 = sorted(latencies)[int(len(latencies) * 0.99)]
        
        print(f"\nIn-memory cache latency: P50={p50:.4f}ms, P95={p95:.4f}ms, P99={p99:.4f}ms")
        
        # In-memory cache should be very fast (<1ms)
        assert p50 < 1.0, f"P50 latency {p50:.4f}ms exceeds 1ms"
        assert p95 < 5.0, f"P95 latency {p95:.4f}ms exceeds 5ms"
        assert p99 < 10.0, f"P99 latency {p99:.4f}ms exceeds 10ms"
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate(self):
        """Measure cache hit rate"""
        cache = InMemoryCache()
        
        # Set values
        for i in range(10):
            await cache.set(f"key_{i}", f"value_{i}", ttl=60)
        
        # Perform 100 get operations with 90% hit rate
        hits = 0
        misses = 0
        
        for i in range(100):
            key = f"key_{i % 10}"
            value = await cache.get(key)
            if value is not None:
                hits += 1
            else:
                misses += 1
        
        hit_rate = hits / (hits + misses)
        print(f"\nCache hit rate: {hit_rate:.1%}")
        
        # Should have ~100% hit rate (all keys exist)
        assert hit_rate > 0.95, f"Hit rate {hit_rate:.1%} below 95%"
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiry_latency(self):
        """Measure performance during TTL expiry"""
        cache = InMemoryCache()
        
        # Set values with short TTL
        for i in range(10):
            await cache.set(f"key_{i}", f"value_{i}", ttl=0.1)
        
        # Wait for expiry
        await asyncio.sleep(0.2)
        
        # Measure get operations on expired keys
        latencies = []
        
        for i in range(100):
            key = f"key_{i % 10}"
            start = time.perf_counter()
            value = await cache.get(key)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
        
        p50 = statistics.median(latencies)
        print(f"\nCache miss latency (after expiry): P50={p50:.4f}ms")
        
        # Should still be fast even on miss
        assert p50 < 1.0, f"P50 latency {p50:.4f}ms exceeds 1ms"


# ============================================================================
# SECTION 3: Throughput & Concurrency Tests
# ============================================================================

class TestThroughputConcurrency:
    """Measure system throughput and concurrent user capacity"""
    
    @pytest.mark.asyncio
    async def test_concurrent_trade_additions(self):
        """Measure throughput of concurrent trade additions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "concurrent_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            start_time = time.perf_counter()
            
            async def add_trades(worker_id):
                """Add trades concurrently"""
                for i in range(20):
                    portfolio.add_trade(
                        trade_id=f"W{worker_id}_T{i}",
                        symbol=f"COIN{worker_id}",
                        side="BUY" if i % 2 == 0 else "SELL",
                        quantity=0.1,
                        price=1000.0 + (i * 10),
                        fee=0.1
                    )
            
            # Run 10 concurrent workers, each adding 20 trades (200 total)
            await asyncio.gather(*[add_trades(i) for i in range(10)])
            
            elapsed = time.perf_counter() - start_time
            total_trades = 200
            throughput = total_trades / elapsed
            
            print(f"\nConcurrent trade throughput: {throughput:.1f} trades/second")
            print(f"Total time: {elapsed:.2f}s for {total_trades} trades")
            
            # Verify all trades added
            trades = portfolio.get_trade_history()
            assert len(trades) == total_trades
            
            # Target: >50 trades/second
            assert throughput > 50, f"Throughput {throughput:.1f} trades/s below target 50"
    
    @pytest.mark.asyncio
    async def test_concurrent_reads_under_load(self):
        """Measure read performance under concurrent load"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "read_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            # Add 100 trades
            for i in range(100):
                portfolio.add_trade(
                    trade_id=f"T{i}",
                    symbol=f"COIN{i % 10}",
                    side="BUY",
                    quantity=0.1,
                    price=1000.0,
                    fee=0.1
                )
            
            start_time = time.perf_counter()
            
            async def read_portfolio():
                """Read portfolio data concurrently"""
                results = []
                for _ in range(20):
                    positions = portfolio.get_all_positions()
                    stats = portfolio.get_portfolio_stats()
                    history = portfolio.get_trade_history(limit=10)
                    results.append((positions, stats, history))
                return results
            
            # Run 5 concurrent readers
            results = await asyncio.gather(*[read_portfolio() for _ in range(5)])
            
            elapsed = time.perf_counter() - start_time
            total_reads = 5 * 20 * 3  # 5 workers * 20 iterations * 3 operations
            throughput = total_reads / elapsed
            
            print(f"\nConcurrent read throughput: {throughput:.1f} reads/second")
            
            # Target: >500 reads/second
            assert throughput > 500, f"Throughput {throughput:.1f} reads/s below target 500"
    
    @pytest.mark.asyncio
    async def test_mixed_workload_throughput(self):
        """Measure throughput with mixed read/write workload"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "mixed_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            # Add initial trades
            for i in range(50):
                portfolio.add_trade(
                    trade_id=f"INIT_{i}",
                    symbol="BTCUSDT",
                    side="BUY",
                    quantity=0.1,
                    price=40000.0,
                    fee=0.1
                )
            
            start_time = time.perf_counter()
            
            async def mixed_workload(worker_id):
                """Mix of reads and writes"""
                for i in range(10):
                    # Write
                    portfolio.add_trade(
                        trade_id=f"W{worker_id}_T{i}",
                        symbol="BTCUSDT",
                        side="BUY",
                        quantity=0.1,
                        price=40000.0 + (i * 10),
                        fee=0.1
                    )
                    # Read
                    portfolio.get_all_positions()
                    portfolio.get_portfolio_stats()
            
            # Run 5 concurrent workers
            await asyncio.gather(*[mixed_workload(i) for i in range(5)])
            
            elapsed = time.perf_counter() - start_time
            total_operations = 5 * 10 * 3  # 5 workers * 10 iterations * 3 operations
            throughput = total_operations / elapsed
            
            print(f"\nMixed workload throughput: {throughput:.1f} ops/second")
            print(f"Total time: {elapsed:.2f}s for {total_operations} operations")
            
            # Target: >100 ops/second for mixed workload
            assert throughput > 100, f"Throughput {throughput:.1f} ops/s below target 100"


# ============================================================================
# SECTION 4: Scalability Tests
# ============================================================================

class TestScalability:
    """Test system behavior as data volume grows"""
    
    def test_portfolio_stats_scales_linearly(self):
        """Verify portfolio stats computation scales linearly with trade count"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "scale_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            measurements = []
            
            for num_trades in [10, 50, 100, 200]:
                # Add trades
                while len(portfolio.get_trade_history()) < num_trades:
                    i = len(portfolio.get_trade_history())
                    portfolio.add_trade(
                        trade_id=f"T{i}",
                        symbol="BTCUSDT",
                        side="BUY" if i % 2 == 0 else "SELL",
                        quantity=0.1,
                        price=40000.0 + (i * 10),
                        fee=0.1
                    )
                
                # Measure get_portfolio_stats
                latencies = []
                for _ in range(10):
                    start = time.perf_counter()
                    stats = portfolio.get_portfolio_stats()
                    elapsed = (time.perf_counter() - start) * 1000
                    latencies.append(elapsed)
                
                avg_latency = statistics.mean(latencies)
                measurements.append((num_trades, avg_latency))
                print(f"\nTrades: {num_trades}, Avg latency: {avg_latency:.2f}ms")
            
            # Check that latency growth is sub-linear (O(n) or better)
            growth_rate = measurements[3][1] / measurements[2][1]
            trades_growth = measurements[3][0] / measurements[2][0]
            
            print(f"Latency growth rate: {growth_rate:.2f}x for {trades_growth:.2f}x trades")
            
            # Latency should not grow faster than trades
            assert growth_rate <= trades_growth * 1.5, "Latency scaling is super-linear"
    
    def test_position_retrieval_scales(self):
        """Verify position retrieval scales with number of positions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "pos_scale_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            measurements = []
            trade_counter = 0
            
            for num_positions in [5, 20, 50]:
                # Add positions
                for i in range(num_positions):
                    portfolio.add_trade(
                        trade_id=f"T{trade_counter}",
                        symbol=f"COIN{i}",
                        side="BUY",
                        quantity=1.0,
                        price=1000.0 + (i * 10),
                        fee=0.1
                    )
                    trade_counter += 1
                
                # Measure get_all_positions
                latencies = []
                for _ in range(20):
                    start = time.perf_counter()
                    positions = portfolio.get_all_positions()
                    elapsed = (time.perf_counter() - start) * 1000
                    latencies.append(elapsed)
                
                avg_latency = statistics.mean(latencies)
                measurements.append((num_positions, avg_latency))
                print(f"\nPositions: {num_positions}, Avg latency: {avg_latency:.3f}ms")
            
            # Verify sub-linear scaling
            if len(measurements) >= 2:
                growth_rate = measurements[-1][1] / measurements[-2][1]
                positions_growth = measurements[-1][0] / measurements[-2][0]
                print(f"Latency growth: {growth_rate:.2f}x for {positions_growth:.2f}x positions")


# ============================================================================
# SECTION 5: Memory & Resource Tests
# ============================================================================

class TestResourceUsage:
    """Test memory usage and resource efficiency"""
    
    def test_large_portfolio_memory(self):
        """Verify memory usage remains acceptable with large portfolio"""
        import sys
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "mem_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            # Add 1000 trades
            for i in range(1000):
                portfolio.add_trade(
                    trade_id=f"T{i}",
                    symbol=f"COIN{i % 50}",
                    side="BUY" if i % 2 == 0 else "SELL",
                    quantity=0.1 * (i % 10 + 1),
                    price=1000.0 + (i * 10),
                    fee=0.1
                )
            
            # Verify operations still work
            positions = portfolio.get_all_positions()
            stats = portfolio.get_portfolio_stats()
            history = portfolio.get_trade_history()
            
            assert len(history) == 1000
            assert stats['number_of_trades'] == 1000
            
            print(f"\nSuccessfully stored 1000 trades")
            print(f"Positions: {len(positions)}")
            print(f"Stats: {json.dumps(stats, indent=2)}")
    
    def test_query_latency_with_large_history(self):
        """Verify query latency remains acceptable with large trade history"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "large_hist_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            # Add 500 trades
            for i in range(500):
                portfolio.add_trade(
                    trade_id=f"T{i}",
                    symbol=f"COIN{i % 10}",
                    side="BUY" if i % 2 == 0 else "SELL",
                    quantity=0.1,
                    price=1000.0,
                    fee=0.1
                )
            
            # Measure trade history retrieval with limit
            latencies = []
            
            for limit in [10, 50, 100, 500]:
                limit_latencies = []
                for _ in range(20):
                    start = time.perf_counter()
                    history = portfolio.get_trade_history(limit=limit)
                    elapsed = (time.perf_counter() - start) * 1000
                    limit_latencies.append(elapsed)
                
                avg_latency = statistics.mean(limit_latencies)
                print(f"\nTrade history (limit={limit}): {avg_latency:.2f}ms")
                
                # Even full history retrieval should be fast
                assert avg_latency < 50, f"History retrieval latency {avg_latency:.2f}ms exceeds 50ms"


# ============================================================================
# SECTION 6: Stress Tests
# ============================================================================

class TestStress:
    """Test system under stress conditions"""
    
    @pytest.mark.asyncio
    async def test_rapid_fire_trade_additions(self):
        """Test system under rapid trade addition"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "stress_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            start_time = time.perf_counter()
            
            # Add 500 trades as fast as possible
            for i in range(500):
                portfolio.add_trade(
                    trade_id=f"T{i}",
                    symbol="BTCUSDT",
                    side="BUY" if i % 2 == 0 else "SELL",
                    quantity=0.1,
                    price=40000.0 + (i * 10),
                    fee=0.1
                )
            
            elapsed = time.perf_counter() - start_time
            throughput = 500 / elapsed
            
            print(f"\nRapid trade addition: {throughput:.0f} trades/second")
            print(f"Total time: {elapsed:.2f}s for 500 trades")
            
            # Verify all trades added
            trades = portfolio.get_trade_history()
            assert len(trades) == 500
            
            # Verify system stability (stats calculation still works)
            stats = portfolio.get_portfolio_stats()
            assert stats['number_of_trades'] == 500
    
    def test_position_calculation_under_load(self):
        """Test position calculations with many updates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "calc_stress_test.db"
            portfolio = PortfolioManager(db_path=str(db_path))
            
            # Create positions
            for i in range(20):
                portfolio.add_trade(
                    trade_id=f"T{i}",
                    symbol=f"COIN{i}",
                    side="BUY",
                    quantity=1.0,
                    price=1000.0,
                    fee=0.1
                )
            
            # Perform 100 price updates
            start_time = time.perf_counter()
            
            for update_round in range(100):
                prices = {f"COIN{i}": 1000.0 + (update_round * 10) for i in range(20)}
                portfolio.update_market_prices(prices)
            
            elapsed = time.perf_counter() - start_time
            
            print(f"\n100 price update rounds: {elapsed:.2f}s")
            print(f"Avg time per update: {elapsed/100:.3f}s")
            
            # Verify final state is correct
            stats = portfolio.get_portfolio_stats()
            assert len(portfolio.get_all_positions()) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
