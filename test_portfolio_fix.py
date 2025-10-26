import sys
sys.path.insert(0, '/app')

print("\n" + "="*60)
print("PORTFOLIO OVERVIEW DEBUG - FINAL VERIFICATION")
print("="*60 + "\n")

# Test 1: Config Validation
print("✓ Test 1: Configuration Validation")
try:
    from binance_trade_agent.config import config
    config.validate()
    print(f"  - API Keys: Set ✓")
    print(f"  - Testnet Mode: {config.binance_testnet} ✓")
    print(f"  - Demo Mode: {config.demo_mode} ✓")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

print("\n✓ Test 2: Database Connection")
try:
    from binance_trade_agent.portfolio_manager import PortfolioManager
    pm = PortfolioManager('/app/data/web_portfolio.db')
    stats = pm.get_portfolio_stats()
    print(f"  - Database Connected ✓")
    print(f"  - Total Portfolio Value: ${stats.get('total_value'):.2f}")
    print(f"  - Total Positions: {stats.get('positions_count')}")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

print("\n✓ Test 3: Component Initialization")
try:
    from binance_trade_agent.web_ui import components
    required = ['market_agent', 'signal_agent', 'risk_agent', 'execution_agent', 'portfolio', 'orchestrator']
    initialized = list(components.keys())
    if all(r in initialized for r in required):
        print(f"  - All {len(initialized)} components initialized ✓")
    else:
        missing = set(required) - set(initialized)
        print(f"  ✗ Missing components: {missing}")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    sys.exit(1)

print("\n✓ Test 4: Portfolio Data Loading")
try:
    from binance_trade_agent.web_ui import get_portfolio_data
    data = get_portfolio_data()
    if 'error' in data:
        print(f"  ✗ FAILED: {data['error']}")
        sys.exit(1)
    else:
        print(f"  - Portfolio data loaded ✓")
        print(f"  - Total Value: ${data.get('total_value'):.2f}")
        print(f"  - Total P&L: ${data.get('total_pnl'):.2f} ({data.get('total_pnl_percent'):+.2f}%)")
        print(f"  - Open Positions: {data.get('open_positions')}")
        print(f"  - Position Details:")
        for pos in data.get('positions', []):
            print(f"    * {pos['symbol']}: {pos['quantity']:.4f} @ ${pos['average_price']:.2f}")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("ALL TESTS PASSED ✓")
print("Portfolio Overview is now fully functional!")
print("="*60 + "\n")
