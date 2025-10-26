"""
Strategy Testing CLI

A command-line interface for testing and comparing the modular trading strategies
"""
import asyncio
import argparse
import json
from datetime import datetime
from typing import Dict, Any

from .signal_agent import SignalAgent
from .strategies import StrategyManager
from .market_data_agent import MarketDataAgent
from .orchestrator import TradingOrchestrator


class StrategyTestCLI:
    """Command-line interface for strategy testing"""
    
    def __init__(self):
        self.signal_agent = SignalAgent()
        self.strategy_manager = StrategyManager()
        self.market_agent = MarketDataAgent()
        self.orchestrator = TradingOrchestrator()
        
        # Mock market data for testing
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
    
    def list_strategies(self):
        """List all available strategies"""
        print("=== Available Trading Strategies ===")
        strategies = self.strategy_manager.list_strategies()
        
        for name, info in strategies.items():
            print(f"\n{name}:")
            print(f"  Type: {info['type']}")
            print(f"  Description: {info['description']}")
            print(f"  Min Data Required: {info['min_data_required']}")
            print(f"  Parameters: {len(info['parameters'])}")
            if info['performance_records'] > 0:
                print(f"  Performance Records: {info['performance_records']}")
    
    def test_strategy(self, strategy_name: str, symbol: str = "BTCUSDT"):
        """Test a specific strategy"""
        print(f"=== Testing Strategy: {strategy_name} ===")
        
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if not strategy:
            print(f"Error: Strategy '{strategy_name}' not found")
            return
        
        # Test with sample data
        try:
            result = strategy.analyze(self.sample_data, symbol)
            
            print(f"Symbol: {symbol}")
            print(f"Signal: {result.signal.value}")
            print(f"Confidence: {result.confidence:.1%}")
            
            if result.price_target:
                print(f"Price Target: ${result.price_target:.2f}")
            if result.stop_loss:
                print(f"Stop Loss: ${result.stop_loss:.2f}")
            if result.take_profit:
                print(f"Take Profit: ${result.take_profit:.2f}")
            
            print(f"Indicators: {list(result.indicators.keys())}")
            
            # Show risk metrics
            risk_metrics = strategy.get_risk_metrics(self.sample_data)
            print(f"Risk Level: {risk_metrics.get('risk_level', 0):.1%}")
            print(f"Volatility: {risk_metrics.get('volatility', 0):.3f}")
            
        except Exception as e:
            print(f"Error testing strategy: {str(e)}")
    
    def compare_strategies(self, symbol: str = "BTCUSDT"):
        """Compare all strategies"""
        print(f"=== Strategy Comparison for {symbol} ===")
        
        try:
            comparison = self.strategy_manager.compare_strategies(self.sample_data, symbol)
            
            if 'error' in comparison:
                print(f"Error: {comparison['error']}")
                return
            
            # Show consensus
            consensus = comparison['consensus']
            print(f"\nConsensus: {consensus['signal']} (strength: {consensus['strength']:.1%})")
            print(f"Votes - Buy: {consensus['votes']['buy']}, "
                  f"Sell: {consensus['votes']['sell']}, "
                  f"Hold: {consensus['votes']['hold']}")
            
            # Show best strategy
            best = comparison['best_strategy']
            print(f"\nBest Strategy: {best['name']}")
            print(f"Signal: {best['signal']} (confidence: {best['confidence']:.1%})")
            
            print(f"\nAverage Confidence: {comparison['average_confidence']:.1%}")
            print(f"Recommendation: {comparison['recommendation']}")
            
            # Show individual results
            print(f"\nIndividual Strategy Results:")
            for name, result in comparison['strategy_results'].items():
                print(f"  {name}: {result['signal']} (confidence: {result['confidence']:.1%})")
                
        except Exception as e:
            print(f"Error comparing strategies: {str(e)}")
    
    def create_strategy(self, name: str, strategy_type: str, parameters: Dict[str, Any]):
        """Create a custom strategy"""
        print(f"=== Creating Custom Strategy: {name} ===")
        
        try:
            success = self.strategy_manager.create_strategy(strategy_type, name, parameters)
            
            if success:
                print(f"✓ Strategy '{name}' created successfully")
                
                # Test the new strategy
                self.test_strategy(name)
            else:
                print(f"✗ Failed to create strategy '{name}'")
                
        except Exception as e:
            print(f"Error creating strategy: {str(e)}")
    
    def benchmark_strategies(self, iterations: int = 10):
        """Benchmark strategy performance"""
        print(f"=== Strategy Performance Benchmark ({iterations} iterations) ===")
        
        strategies = list(self.strategy_manager.list_strategies().keys())[:5]  # Test first 5
        results = {}
        
        for strategy_name in strategies:
            strategy = self.strategy_manager.get_strategy(strategy_name)
            if not strategy:
                continue
            
            print(f"\nBenchmarking {strategy_name}...")
            
            times = []
            signals = []
            confidences = []
            
            for i in range(iterations):
                start_time = datetime.now()
                try:
                    result = strategy.analyze(self.sample_data, "BTCUSDT")
                    end_time = datetime.now()
                    
                    times.append((end_time - start_time).total_seconds() * 1000)  # ms
                    signals.append(result.signal.value)
                    confidences.append(result.confidence)
                    
                except Exception as e:
                    print(f"  Error in iteration {i+1}: {str(e)}")
            
            if times:
                avg_time = sum(times) / len(times)
                avg_confidence = sum(confidences) / len(confidences)
                
                results[strategy_name] = {
                    'avg_time_ms': avg_time,
                    'avg_confidence': avg_confidence,
                    'signals': signals,
                    'success_rate': len(times) / iterations
                }
                
                print(f"  Average Time: {avg_time:.2f}ms")
                print(f"  Average Confidence: {avg_confidence:.1%}")
                print(f"  Success Rate: {len(times)}/{iterations}")
        
        # Show summary
        print(f"\n=== Benchmark Summary ===")
        for name, result in results.items():
            print(f"{name}: {result['avg_time_ms']:.2f}ms, "
                  f"{result['avg_confidence']:.1%} confidence")
    
    async def test_orchestrator_integration(self, symbol: str = "BTCUSDT"):
        """Test orchestrator integration with strategies"""
        print(f"=== Testing Orchestrator Integration ===")
        
        try:
            # Test market analysis with all strategies
            analysis = await self.orchestrator.analyze_market_with_all_strategies(symbol)
            
            if 'error' not in analysis:
                print(f"Symbol: {analysis['symbol']}")
                print(f"Current Strategy: {analysis['current_strategy']}")
                
                if 'strategy_comparison' in analysis:
                    comparison = analysis['strategy_comparison']
                    if 'consensus' in comparison:
                        consensus = comparison['consensus']
                        print(f"Consensus: {consensus['signal']} (strength: {consensus['strength']:.1%})")
            else:
                print(f"Error: {analysis['error']}")
            
            # Test custom strategy creation through orchestrator
            custom_params = {'rsi_period': 21, 'rsi_overbought': 75}
            success = self.orchestrator.create_custom_strategy('test_orch', 'rsi', custom_params)
            
            if success:
                print(f"✓ Custom strategy created via orchestrator")
                
                # Test switching strategy
                if self.orchestrator.set_strategy('test_orch'):
                    print(f"✓ Strategy switched successfully")
                else:
                    print(f"✗ Failed to switch strategy")
            
        except Exception as e:
            print(f"Error testing orchestrator: {str(e)}")
    
    def export_import_test(self):
        """Test strategy export/import functionality"""
        print(f"=== Testing Strategy Export/Import ===")
        
        try:
            # Export strategies
            export_data = self.strategy_manager.export_strategies()
            print(f"✓ Exported {len(export_data)} characters of strategy data")
            
            # Create new manager for import test
            new_manager = StrategyManager()
            original_count = len(new_manager.list_strategies())
            
            # Clear and import
            new_manager.strategies.clear()
            new_manager.performance_history.clear()
            
            success = new_manager.import_strategies(json_data=export_data)
            imported_count = len(new_manager.list_strategies())
            
            if success:
                print(f"✓ Import successful: {imported_count} strategies imported")
            else:
                print(f"✗ Import failed")
                
        except Exception as e:
            print(f"Error testing export/import: {str(e)}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Trading Strategy Testing CLI")
    parser.add_argument('command', choices=[
        'list', 'test', 'compare', 'create', 'benchmark', 'integration', 'export-import'
    ], help='Command to execute')
    
    parser.add_argument('--strategy', help='Strategy name for test command')
    parser.add_argument('--symbol', default='BTCUSDT', help='Trading symbol')
    parser.add_argument('--type', help='Strategy type for create command')
    parser.add_argument('--name', help='Strategy name for create command')
    parser.add_argument('--params', help='JSON parameters for create command')
    parser.add_argument('--iterations', type=int, default=10, help='Iterations for benchmark')
    
    args = parser.parse_args()
    cli = StrategyTestCLI()
    
    if args.command == 'list':
        cli.list_strategies()
    
    elif args.command == 'test':
        if not args.strategy:
            print("Error: --strategy required for test command")
            return
        cli.test_strategy(args.strategy, args.symbol)
    
    elif args.command == 'compare':
        cli.compare_strategies(args.symbol)
    
    elif args.command == 'create':
        if not all([args.name, args.type]):
            print("Error: --name and --type required for create command")
            return
        
        params = {}
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError:
                print("Error: Invalid JSON in --params")
                return
        
        cli.create_strategy(args.name, args.type, params)
    
    elif args.command == 'benchmark':
        cli.benchmark_strategies(args.iterations)
    
    elif args.command == 'integration':
        asyncio.run(cli.test_orchestrator_integration(args.symbol))
    
    elif args.command == 'export-import':
        cli.export_import_test()


if __name__ == "__main__":
    main()