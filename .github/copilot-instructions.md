# Binance Trading Agent - AI Assistant Instructions

This is a production-ready automated trading system for Binance with comprehensive agent-based architecture, Model Context Protocol (MCP) integration, and advanced risk management.

## Architecture Overview

### Core Agent Workflow Chain
The system follows a strict agent orchestration pattern: `MarketDataAgent → SignalAgent → RiskManagementAgent → TradeExecutionAgent`

- **TradingOrchestrator** (`orchestrator.py`) coordinates the complete workflow with correlation ID tracking
- Each agent is independent and communicates via standardized interfaces
- All operations use async/await patterns with proper error handling and logging

### Key Components
- **MCP Server** (`mcp_server.py`): Exposes 15+ trading tools via Model Context Protocol
- **Portfolio Manager** (`portfolio_manager.py`): SQLite-backed position tracking with real-time P&L
- **Risk Management** (`risk_management_agent.py`): Multi-layered risk controls with emergency stop capability
- **Monitoring System** (`monitoring.py`): Structured logging with correlation ID tracking and metrics collection
- **Async Optimization** (`async_orchestrator.py`, `async_binance_client.py`): High-performance async operations with connection pooling and concurrent execution

## Development Patterns

### Async Optimization Patterns
For high-performance operations, use async components:
```python
# Use AsyncTradingOrchestrator for concurrent multi-symbol processing
async with AsyncTradingOrchestrator() as orchestrator:
    decisions = await orchestrator.execute_multi_symbol_workflow([
        {'symbol': 'BTCUSDT', 'quantity': 0.001},
        {'symbol': 'ETHUSDT', 'quantity': 0.01}
    ])

# Use AsyncMarketDataAgent for concurrent data fetching
async with AsyncMarketDataAgent() as agent:
    prices = await agent.fetch_prices_batch(['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])
```

### Correlation ID Pattern
All operations must include correlation IDs for traceability:
```python
correlation_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
extra = {'correlation_id': correlation_id}
self.logger.info("Starting operation", extra=extra)
```

### Agent Communication
Agents communicate via structured dictionaries, not direct method calls:
```python
# Signal Agent output
signal_result = {'signal': 'BUY', 'confidence': 0.85, 'indicators': {...}}

# Risk Agent input/output  
risk_result = risk_agent.validate_trade(symbol, side, quantity, price)
# Returns: {'approved': bool, 'reason': str, 'recommended_quantity': float}
```

### Error Handling Pattern
Always wrap agent operations in try/catch with correlation logging:
```python
try:
    result = await agent.operation(params)
    self.logger.info("Operation succeeded", extra={'correlation_id': corr_id})
except Exception as e:
    self.logger.error(f"Operation failed: {str(e)}", extra={'correlation_id': corr_id})
    raise
```

## Development Workflows

### Testing Strategy
- **Integration Tests**: `test_agent_flow.py` tests complete workflows end-to-end
- **Unit Tests**: Individual agent tests with mocked dependencies
- **Strategy Tests**: `test_rsi_strategy.py` and `test_strategy_manager.py` validate modular trading strategies
- **Live API Tests**: `test_binance_connectivity.py` validates actual Binance testnet integration
- Run tests: `docker-compose exec trading-agent pytest binance_trade_agent/tests/ -v` inside Docker container
- Skip integration tests: `pytest -m "not integration"` for faster local runs

### Deployment Pipeline
Use `./deploy.sh` with these modes:
- `development`: Single container with hot reload
- `production`: Optimized build with health checks
- `monitoring`: Includes Prometheus + Grafana stack
- Always deploy via Docker - local Python installation not supported

### Configuration Management
- Environment variables loaded via `config.py` from `.env` file
- Risk parameters in `risk_management_agent.py` with symbol-specific overrides
- MCP tools configured in `config.toml`
- Binance testnet is default - never use production keys without explicit confirmation
- Package configuration in `setup.py` and `pyproject.toml` (Python 3.10 target)

## Critical Implementation Rules

### Import Patterns
- **Always use absolute imports** from `binance_trade_agent.*` in all modules
- `SignalType` and other strategy enums are exported from `binance_trade_agent.strategies`
- Never use relative imports (e.g., `from .module import X`) in standalone scripts or when running via pytest
- Package is installed in editable mode (`pip install -e .`) in the Docker container for proper imports

### Risk Management
- **Never bypass risk validation** - all trades must pass through `RiskManagementAgent.validate_trade()`
- Risk rules are configurable but default to conservative limits (5% max position, 2% stop-loss)
- Emergency stop functionality must be accessible from all trading interfaces

### Data Persistence
- Portfolio data stored in SQLite (`/app/data/portfolio.db`)
- Positions updated in real-time with market price changes
- Trade history maintained with complete audit trail including correlation IDs

### MCP Integration
- All trading functionality exposed as MCP tools for AI agent integration
- Tools follow standardized input/output schemas
- Server runs on stdio protocol, not HTTP (important for container deployment)

### Logging Standards
- Use structured logging with correlation IDs for all operations
- Log levels: DEBUG for detailed flow, INFO for major events, ERROR for failures
- Performance metrics tracked automatically via `@monitoring.time_function` decorator

## Common Gotchas

### Agent Dependencies
- `SignalAgent` requires `MarketDataAgent` instance in constructor
- `TradingOrchestrator` initializes all agents - don't create separate instances
- Portfolio manager needs database path - defaults to `/app/data/`

### Docker Considerations
- Application runs as non-root user `trading:trading`
- SQLite databases must be in `/app/data/` with proper permissions
- Supervisor manages multiple processes (MCP server + web UI)
- Environment variables passed via `.env` file, not Docker ENV
- Package installed in editable mode during build with `pip install -e .`
- Virtual environment at `/opt/venv` is owned by `trading` user for package installs
- `.dockerignore` excludes `.git/`, `__pycache__/`, `*.db`, `logs/`, and `data/` from builds

### Testing in Development
- Always use Binance testnet (`BINANCE_TESTNET=true`)
- Test data stored in separate SQLite databases per test
- Integration tests require valid testnet API keys
- Use `pytest -v` for detailed test output with correlation tracking
- Tests marked with `@pytest.mark.integration` can be skipped with `-m "not integration"`
- All import errors resolved with absolute imports and proper package installation

## Quick Commands

```bash
# Deploy development environment
./deploy.sh development

# Run tests
docker-compose exec trading-agent pytest binance_trade_agent/tests/ -v

# Run tests excluding integration tests
docker-compose exec trading-agent pytest binance_trade_agent/tests/ -m "not integration"

# Check logs
docker-compose logs -f trading-agent

# Access container shell
docker-compose exec trading-agent /bin/bash

# Rebuild container after code changes
docker-compose build && docker-compose up -d --force-recreate

# Start interactive CLI
python binance_trade_agent/cli.py
```

This system prioritizes safety, traceability, and modular design. When extending functionality, maintain the agent chain pattern and ensure all operations are properly logged with correlation IDs.

