# Binance Trading Agent - Comprehensive Guide

Complete documentation for the automated Binance trading system with agent-based architecture, portfolio management, and production deployment.

**Table of Contents:**
- [Quick Start (5 Minutes)](#quick-start-5-minutes)
- [Architecture Overview](#architecture-overview)
- [Installation & Setup](#installation--setup)
- [Usage Guides](#usage-guides)
- [Web UI Features](#web-ui-features)
- [Testing](#testing)
- [Deployment](#deployment)
- [Risk Management](#risk-management)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (5 Minutes)

### Prerequisites
- Docker & Docker Compose (recommended)
- Python 3.10+ (if running locally)
- Binance testnet API keys ([get them here](https://testnet.binance.vision))

### 1. Clone & Setup Environment
```bash
cd binance-trading-agent
cp .env.example .env
# Edit .env with your Binance testnet API keys:
# BINANCE_API_KEY=your_testnet_key
# BINANCE_API_SECRET=your_testnet_secret
# BINANCE_TESTNET=true (default, DO NOT REMOVE)
```

### 2. Start with Docker (Recommended)
```bash
./deploy.sh development
# Web UI: http://localhost:8501
# MCP Server: stdio protocol (internal)
# Wait 10-15 seconds for full startup
```

### 3. Access the System
- **Web UI:** http://localhost:8501 (Streamlit dashboard)
- **Portfolio Tab:** View positions, trades, P&L
- **Market Data Tab:** Real-time price data
- **Signals Tab:** Technical indicators & trading signals
- **System Health:** Emergency controls & status
- **Settings:** Configuration adjustments

### 4. Verify It's Working
```bash
# Check container status
docker-compose ps
# Should show: trading-agent (RUNNING), redis (RUNNING)

# Test portfolio loading
docker-compose exec trading-agent python -c "
from binance_trade_agent.portfolio_manager import PortfolioManager
pm = PortfolioManager('/app/data/web_portfolio.db')
print('Portfolio Stats:', pm.get_portfolio_stats())
"
```

---

## Architecture Overview

### Agent Orchestration Chain

The system follows a strict agent chaining pattern where each agent is independent and communicates via standardized interfaces:

```
MarketDataAgent → SignalAgent → RiskManagementAgent → TradeExecutionAgent → PortfolioManager
```

**Agent Responsibilities:**

1. **MarketDataAgent** (`market_data_agent.py`)
   - Fetches real-time market data from Binance
   - Calculates technical indicators (RSI, MACD, Bollinger Bands)
   - Maintains price history for analysis
   - Provides data to SignalAgent

2. **SignalAgent** (`signal_agent.py`)
   - Analyzes market data using strategy modules
   - Generates trading signals (BUY/SELL/HOLD)
   - Calculates confidence scores
   - Uses modular strategy system (RSI, MACD, etc.)

3. **RiskManagementAgent** (`risk_management_agent.py`)
   - Validates trades before execution
   - Enforces position size limits (5% max)
   - Manages stop-loss/take-profit levels
   - Controls emergency stop functionality
   - Tracks portfolio risk metrics

4. **TradeExecutionAgent** (`trade_execution_agent.py`)
   - Executes approved trades on Binance
   - Handles order placement & tracking
   - Manages order status updates
   - Records execution metrics

5. **PortfolioManager** (`portfolio_manager.py`)
   - SQLite-backed position tracking
   - Real-time P&L calculations
   - Trade history & audit trail
   - Position updates from market data

### Core Orchestration

**TradingOrchestrator** (`orchestrator.py`) coordinates the complete workflow:

```python
async def execute_workflow(symbol, quantity):
    # 1. Fetch market data
    data = await market_data_agent.fetch_data(symbol)
    
    # 2. Generate signal
    signal = signal_agent.analyze(data)
    
    # 3. Validate risk
    approved = risk_management_agent.validate_trade(
        symbol, signal['side'], quantity, data['price']
    )
    
    # 4. Execute if approved
    if approved:
        trade = trade_execution_agent.execute(...)
        portfolio_manager.record_trade(trade)
```

### MCP Server Integration

The **MCP Server** (`mcp_server.py`) exposes 15+ trading tools via Model Context Protocol:

- **Market Data Tools:** `get_price`, `get_indicators`, `fetch_ohlcv`
- **Trading Tools:** `place_order`, `cancel_order`, `get_open_orders`
- **Portfolio Tools:** `get_portfolio_stats`, `get_positions`, `get_trades`
- **Risk Tools:** `check_position_size`, `calculate_stop_loss`, `emergency_stop`
- **Strategy Tools:** `analyze_signal`, `backtest_strategy`, `optimize_parameters`

Tools follow standardized input/output schemas for AI agent integration.

---

## Installation & Setup

### Option 1: Docker (Recommended for Production)

**Advantages:**
- Consistent environment across machines
- Automatic service management
- Built-in health checks
- Pre-configured permissions

**Installation:**

```bash
# 1. Ensure Docker & Docker Compose are installed
docker --version  # Should be 20.10+
docker-compose --version  # Should be 1.29+

# 2. Setup environment file
cp .env.example .env
# Edit .env with your keys

# 3. Deploy
./deploy.sh development

# 4. Verify
docker-compose ps
```

**What Gets Deployed:**
- `trading-agent` container: Python application, MCP server, Streamlit UI
- `redis` container: Cache & session storage
- Supervisor daemon: Manages multiple processes
- SQLite database: `/app/data/web_portfolio.db`

### Option 2: Local Python Installation

**Prerequisites:**
- Python 3.10+
- Virtual environment: `python -m venv venv`

**Installation:**

```bash
# 1. Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your keys

# 4. Start components in separate terminals
# Terminal 1: MCP Server
python binance_trade_agent/mcp_server.py

# Terminal 2: Web UI
streamlit run binance_trade_agent/web_ui.py

# Terminal 3: CLI (optional)
python binance_trade_agent/cli.py
```

**Why Docker is Recommended:**
- Local installation requires manual service management
- Package installed in editable mode (`pip install -e .`) works better in Docker
- Virtual environment ownership and permissions handled automatically
- Connection pooling & async optimizations work reliably in containerized environment

### Configuration Files

**`.env` File** - Environment variables:
```bash
# Binance API (testnet by default)
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
BINANCE_TESTNET=true

# Trading settings
TRADING_ENABLED=true
DEMO_MODE=true
MAX_POSITION_SIZE=0.05  # 5% of portfolio

# Database
DATABASE_PATH=/app/data/web_portfolio.db

# Logging
LOG_LEVEL=INFO
```

**`config.toml`** - MCP tools & features configuration

**`supervisord.conf`** - Process management (Docker only):
- Manages MCP server startup
- Manages Streamlit UI startup
- Auto-restart on failure
- Logs to `/var/log/supervisor/`

---

## Usage Guides

### Web UI - Portfolio Tab

**Access:** http://localhost:8501 → Click "Portfolio" tab

**What You Can Do:**
1. **View Portfolio Summary**
   - Total portfolio value
   - Profit/Loss (absolute & percentage)
   - Number of open positions
   - Total completed trades

2. **View Open Positions**
   - Symbol (BTCUSDT, ETHUSDT, etc.)
   - Quantity held
   - Average entry price
   - Current price
   - Unrealized P&L

3. **View Trade History**
   - Trade ID and timestamp
   - Symbol, side (BUY/SELL), quantity, price
   - Fee charged
   - Complete audit trail

**Database Behind UI:**
- Stored in SQLite: `/app/data/web_portfolio.db`
- PortfolioManager ORM handles all queries
- Real-time updates from market data
- P&L recalculated on every refresh

### Web UI - Market Data Tab

**Data Available:**
- Current price for tracked symbols
- 24h high/low/change
- Volume traded
- Technical indicators (RSI, MACD, Bollinger Bands)

### Web UI - Signals & Risk Tab

**Trading Signals:**
- Strategy: RSI, MACD, Bollinger Bands, or combined
- Signal: BUY, SELL, or HOLD
- Confidence: 0.0 to 1.0
- Supporting indicators

**Risk Metrics:**
- Position size vs. limit
- Stop-loss level
- Take-profit level
- Portfolio heat (total risk)

### Web UI - System Health Tab

**Status Indicators:**
- Trading status (Active/Stopped)
- API connection status
- System health (CPU, memory)
- Portfolio health score
- Risk status (Safe/Warning/Critical)

**Emergency Controls:**
- Activate/deactivate emergency stop
- Check real-time status
- View risk configuration
- Switch between demo/live mode

### CLI - Interactive Trading

**Start CLI:**
```bash
python binance_trade_agent/cli.py
```

**Commands:**
- `status` - Show portfolio & market status
- `price <symbol>` - Get current price
- `buy <symbol> <quantity>` - Place buy order
- `sell <symbol> <quantity>` - Place sell order
- `positions` - List open positions
- `trades` - Show recent trades
- `cancel <order_id>` - Cancel an order
- `risk <symbol> <quantity>` - Check risk for proposed trade
- `quit` - Exit CLI

**Example Session:**
```
> price BTCUSDT
BTCUSDT: $43,200.00 (↑ 2.3%)

> positions
Open Positions: 2
- BTCUSDT: 0.001 @ $43,000 (Current: $43,200, P&L: +$0.20)
- ETHUSDT: 0.01 @ $2,500 (Current: $2,550, P&L: +$5.00)

> buy ETHUSDT 0.01
Risk check: ✅ Approved (Position: 1% of portfolio)
Executing order...
✅ Order placed: eth_1234
```

### Programmatic Access - Python Script

```python
from binance_trade_agent.portfolio_manager import PortfolioManager
from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.signal_agent import SignalAgent

# Initialize components
portfolio = PortfolioManager('/app/data/web_portfolio.db')
market_data = MarketDataAgent()
signals = SignalAgent(market_data)

# Get portfolio stats
stats = portfolio.get_portfolio_stats()
print(f"Portfolio Value: ${stats['total_value']:.2f}")
print(f"P&L: {stats['total_pnl']:.2f}")

# Get positions
positions = portfolio.get_all_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['quantity']} @ ${pos['current_price']}")

# Analyze a signal
data = market_data.fetch_data('BTCUSDT')
signal = signals.analyze(data, strategy='RSI')
print(f"Signal: {signal['signal']} (confidence: {signal['confidence']:.2f})")
```

---

## Web UI Features

### Horizontal Navigation Menu (7 Tabs)

**Layout:** Menu bar at top with 7 navigation items
- 📊 **Portfolio** - Positions, trades, P&L
- 💰 **Market Data** - Price data, indicators
- 🎯 **Signals & Risk** - Trading signals, risk metrics
- 💼 **Trading** - Place/manage orders
- 🏥 **System Health** - Status, emergency controls
- 📋 **Settings** - Configuration options
- ⚙️ **Advanced** - Debug mode, logs

**Features:**
- Orange highlight on selected tab
- Smooth transitions between tabs
- Responsive on desktop/tablet/mobile
- Icons for quick visual identification

### Styled Metric Cards

**Found On:** Portfolio, Market Data, System Health tabs

**Styling:**
- Orange left border (3px)
- Dark gray background (#2f3035)
- Rounded corners (12px)
- Subtle shadow on hover
- Clear typography with values and deltas

**Examples:**
```
┌─────────────────────────────────┐
│ │ Total Portfolio Value         │
│ │ $10,250.00                    │
│ │ ↑ +2.3% (↑ $230.50)          │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ │ Unrealized P&L                │
│ │ +$125.75 (+1.24%)            │
│ │ 4 positions | 8 trades       │
└─────────────────────────────────┘
```

### Emergency Control Groups

**Red Group - Emergency Controls:**
- Container: Red border (2px), red-tinted background
- Shows: Trading status indicator
- Buttons: Activate/Deactivate Emergency Stop, Check Status
- Purpose: High-visibility critical controls

**Blue Group - Trading Mode & Configuration:**
- Container: Blue border (2px), blue-tinted background
- Shows: Current mode (Demo/Live)
- Buttons: Switch mode, View risk config
- Purpose: Informational, less urgent

---

## Testing

### Running Tests

**All Tests:**
```bash
docker-compose exec trading-agent pytest binance_trade_agent/tests/ -v
```

**Specific Test File:**
```bash
docker-compose exec trading-agent pytest binance_trade_agent/tests/test_portfolio_manager.py -v
```

**Skip Integration Tests (Faster Local):**
```bash
docker-compose exec trading-agent pytest -m "not integration"
```

**With Coverage Report:**
```bash
docker-compose exec trading-agent pytest --cov=binance_trade_agent --cov-report=html
```

### Test Files

| File | Purpose | Type |
|------|---------|------|
| `test_market_data_agent.py` | Market data fetching, indicators | Unit |
| `test_signal_agent.py` | Signal generation, strategies | Unit |
| `test_portfolio_manager.py` | Position tracking, P&L | Unit |
| `test_agent_flow.py` | Complete workflow chain | Integration |
| `test_binance_connectivity.py` | Binance API testnet connection | Integration |
| `test_binance_order_flow.py` | Order placement & execution | Integration |
| `test_mcp_integration.py` | MCP server functionality | Integration |
| `test_web_ui.py` | Web UI components | Unit |

### Test Patterns

**Unit Test Example (Market Data):**
```python
def test_fetch_data_returns_ohlcv():
    agent = MarketDataAgent()
    data = agent.fetch_data('BTCUSDT')
    
    assert 'open' in data
    assert 'high' in data
    assert 'low' in data
    assert 'close' in data
    assert 'volume' in data
    assert data['symbol'] == 'BTCUSDT'
```

**Integration Test Example (Portfolio):**
```python
def test_portfolio_operations():
    pm = PortfolioManager(':memory:')  # In-memory for testing
    
    # Record a trade
    trade = {'symbol': 'BTCUSDT', 'side': 'BUY', 'quantity': 0.001, 
             'price': 43000, 'fee': 5}
    pm.record_trade(trade)
    
    # Verify position
    positions = pm.get_all_positions()
    assert len(positions) == 1
    assert positions[0]['symbol'] == 'BTCUSDT'
    assert positions[0]['quantity'] == 0.001
```

**Strategy Test Example:**
```python
def test_rsi_signal():
    prices = [100, 102, 101, 103, 102, 105, 104, 106]
    signal = analyze_rsi_strategy(prices)
    
    assert signal['signal'] in ['BUY', 'SELL', 'HOLD']
    assert 0.0 <= signal['confidence'] <= 1.0
    assert 'rsi_value' in signal
```

---

## Deployment

### Development Deployment

```bash
./deploy.sh development
```

**What It Does:**
- Builds Docker image with hot reload enabled
- Starts trading-agent + redis containers
- Enables debug logging
- Mounts local files for live editing
- Appropriate for local development & testing

### Production Deployment

```bash
./deploy.sh production
```

**Optimizations:**
- Optimized Docker build (no debug, smaller image)
- Health checks enabled
- Automatic restart on failure
- Production logging configuration
- Ready for cloud deployment

### Deployment with Monitoring

```bash
./deploy.sh monitoring
```

**Includes:**
- Prometheus metrics collection
- Grafana dashboard
- Health check endpoints
- Performance monitoring
- Alert triggers

### Docker Compose Files

**Main Services:**
```yaml
services:
  trading-agent:
    image: binance-trading-agent:latest
    container_name: trading-agent
    environment:
      - BINANCE_API_KEY=${BINANCE_API_KEY}
      - BINANCE_API_SECRET=${BINANCE_API_SECRET}
      - BINANCE_TESTNET=true
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    ports:
      - "8501:8501"  # Streamlit UI
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: redis
    volumes:
      - ./redis_data:/data
    restart: unless-stopped
```

### Deployment Checklist

**Before Going Live:**
- [ ] All tests passing: `pytest -v`
- [ ] Environment variables set correctly in `.env`
- [ ] API keys are testnet (BINANCE_TESTNET=true)
- [ ] Database path writable: `/app/data/`
- [ ] Container starts: `docker-compose up -d`
- [ ] Web UI accessible: http://localhost:8501
- [ ] Portfolio loads without errors
- [ ] Risk management active
- [ ] Monitoring enabled

**After Deployment:**
- [ ] Check container status: `docker-compose ps`
- [ ] Monitor logs: `docker-compose logs -f trading-agent`
- [ ] Test portfolio operations
- [ ] Verify risk controls active
- [ ] Set up alerts for failures

### Important Docker Notes

**Package Installation:**
- Package installed in editable mode: `pip install -e .`
- Requires Docker rebuild after code changes: `docker-compose build --no-cache`
- Always restart container: `docker-compose up -d --force-recreate`
- Without rebuild, code changes won't take effect

**Permissions:**
- Application runs as non-root user: `trading:trading`
- Virtual environment at `/opt/venv` owned by trading user
- SQLite databases in `/app/data/` must be writable
- Use `docker-compose exec -u 0 trading-agent` for root access if needed

---

## Risk Management

### Risk Control Architecture

The **RiskManagementAgent** enforces multi-layered controls:

```
Position Size Check
        ↓
Stop-Loss Validation
        ↓
Portfolio Heat Check
        ↓
Risk Score Calculation
        ↓
Emergency Stop Activation
```

### Risk Parameters (Configurable)

**Position Size Limits:**
- Maximum per position: 5% of portfolio
- Adjustable by symbol in risk config
- Conservative default for safety

**Stop-Loss Levels:**
- Default: 2% below entry
- Adjustable per strategy
- Enforced before trade execution

**Portfolio Heat:**
- Total risk across all positions
- Maximum: 10% portfolio loss capacity
- Triggers warnings or halt

**Emergency Stop:**
- Immediate halt to all trading
- Accessible from web UI
- Can be activated manually or automatically
- All orders get cancelled

### Risk Validation Flow

```python
risk_result = risk_agent.validate_trade(
    symbol='BTCUSDT',
    side='BUY',
    quantity=0.1,
    price=43000
)

# Returns:
# {
#     'approved': True,          # Overall approval
#     'reason': 'Within limits',  # Explanation
#     'recommended_quantity': 0.05  # Adjusted if needed
# }
```

### Risk Configuration (In `risk_management_agent.py`)

```python
DEFAULT_RISK_CONFIG = {
    'max_position_size': 0.05,      # 5% per position
    'stop_loss_percent': 0.02,      # 2% stop-loss
    'max_portfolio_heat': 0.10,     # 10% total risk
    'emergency_stop': False,
    'symbol_overrides': {
        'BTCUSDT': {'max_position_size': 0.1},   # Bitcoin: 10%
        'SHITCOIN': {'max_position_size': 0.01}  # Risky: 1%
    }
}
```

### Risk Dashboard (System Health Tab)

**Metrics Displayed:**
- Trading Status (Active/Stopped)
- Risk Score (0-100, Red/Yellow/Green)
- Portfolio Heat (% of max allowed)
- Emergency Stop Status
- Risk Warnings

**Manual Controls:**
- Activate Emergency Stop (Red button)
- Deactivate Emergency Stop
- Adjust Risk Configuration
- View Risk Rules

### Safety Best Practices

1. **Always Start in Demo Mode**
   - Test strategies without real funds
   - Verify risk controls working
   - Use testnet API keys

2. **Gradual Position Increase**
   - Start with 0.1% of portfolio
   - Monitor performance for 24+ hours
   - Increase to 1%, 5%, then 10% incrementally

3. **Risk Parameters Review**
   - Review position size limits regularly
   - Adjust stop-loss based on strategy
   - Monitor portfolio heat daily

4. **Emergency Stop Readiness**
   - Know how to trigger emergency stop
   - Test it regularly in demo mode
   - Keep personal override key nearby

5. **Correlation ID Tracking**
   - Every operation gets unique correlation ID
   - Helps trace issues in logs
   - Use for debugging & auditing

---

## Troubleshooting

### Portfolio Data Not Loading

**Symptom:** "Failed to load portfolio data" error in web UI

**Diagnosis Steps:**
1. Check container status: `docker-compose ps`
2. Check logs: `docker-compose logs trading-agent | tail -50`
3. Test database directly:
   ```bash
   docker-compose exec trading-agent python -c "
   from binance_trade_agent.portfolio_manager import PortfolioManager
   pm = PortfolioManager('/app/data/web_portfolio.db')
   print(pm.get_portfolio_stats())
   "
   ```

**Common Causes & Fixes:**

| Issue | Cause | Fix |
|-------|-------|-----|
| Database file not found | Path incorrect or permissions | Check `/app/data/` exists and is writable |
| AttributeError: 'dict' has no attribute 'symbol' | Data type mismatch in ORM | Rebuild container: `docker-compose build --no-cache` |
| Connection refused to SQLite | Database locked or corrupted | Stop containers, delete `.db`, restart |
| "ModuleNotFoundError" importing agents | Package not installed in editable mode | Rebuild container: `docker-compose build --no-cache` |
| Streamlit shows old data after code changes | Caching issue in editable install | Restart containers with `docker-compose up -d --force-recreate` |

**Recovery Steps:**

```bash
# 1. Rebuild container (clears caches, reinstalls packages)
docker-compose build --no-cache

# 2. Restart with force-recreate
docker-compose down
docker-compose up -d --force-recreate

# 3. Wait 15 seconds for startup
sleep 15

# 4. Test portfolio
docker-compose exec trading-agent python -c "
from binance_trade_agent.portfolio_manager import PortfolioManager
pm = PortfolioManager('/app/data/web_portfolio.db')
stats = pm.get_portfolio_stats()
print('✅ Portfolio loaded:', stats)
"

# 5. Access web UI
# http://localhost:8501
```

### Web UI Not Accessible

**Symptom:** http://localhost:8501 shows "Connection refused"

**Causes & Fixes:**

1. **Container not running:**
   ```bash
   docker-compose ps  # Check status
   docker-compose up -d  # Start if stopped
   ```

2. **Port 8501 already in use:**
   ```bash
   # Find what's using port 8501
   netstat -ano | findstr :8501  # Windows
   lsof -i :8501  # Mac/Linux
   
   # Stop the conflicting process or use different port
   docker-compose down
   # Edit docker-compose.yml: change "8501:8501" to "8502:8501"
   docker-compose up -d
   # Access at http://localhost:8502
   ```

3. **Streamlit failed to start:**
   ```bash
   docker-compose logs streamlit_ui | tail -20
   # Look for Python errors and fix them
   ```

### High Memory Usage

**Symptom:** Container consuming excessive memory after running

**Diagnosis:**
```bash
docker stats  # Monitor container resources

# Look for:
# - Python process consuming >500MB
# - Accumulated DataFrame objects
# - Unclosed database connections
```

**Solutions:**
1. **Increase container memory limit:**
   ```yaml
   services:
     trading-agent:
       mem_limit: 2g  # Increase from default
   ```

2. **Clear old logs:**
   ```bash
   docker-compose exec trading-agent rm -f /app/logs/*.log
   ```

3. **Restart container:**
   ```bash
   docker-compose restart trading-agent
   ```

### API Connection Errors

**Symptom:** "Failed to connect to Binance API"

**Checks:**
1. Verify testnet API keys are valid:
   ```bash
   docker-compose exec trading-agent python -c "
   from binance_trade_agent.binance_client import AsyncBinanceClient
   import asyncio
   async def test():
       async with AsyncBinanceClient() as client:
           balance = await client.get_account()
           print('✅ Connected to Binance')
   asyncio.run(test())
   "
   ```

2. Check `.env` file:
   ```bash
   cat .env | grep BINANCE
   # Verify keys are present and BINANCE_TESTNET=true
   ```

3. Verify network connectivity:
   ```bash
   docker-compose exec trading-agent ping testnet.binance.vision
   ```

### Test Failures

**Running Tests:**
```bash
# All tests
docker-compose exec trading-agent pytest -v

# Specific test
docker-compose exec trading-agent pytest binance_trade_agent/tests/test_portfolio_manager.py -v

# With detailed output
docker-compose exec trading-agent pytest -vv --tb=long test_file.py::test_name
```

**Common Test Issues:**

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportError: No module named 'binance_trade_agent'` | Package not installed | Rebuild: `docker-compose build --no-cache` |
| `FileNotFoundError: '/app/data/test.db'` | Permission denied | Run with `docker-compose exec` not `docker exec` |
| `AsyncIO errors` | Event loop not closed | Use `pytest-asyncio` properly configured |
| `Binance API rate limit` | Tests hitting real API too fast | Use mocks: `@mock.patch('binance_client')` |

### Performance Issues

**Slow Market Data Fetching:**
```python
# Use AsyncMarketDataAgent for concurrent requests
async with AsyncMarketDataAgent() as agent:
    prices = await agent.fetch_prices_batch([
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT'
    ])
    # Fetches 3 prices concurrently
```

**Slow Portfolio Calculations:**
- Check database indexes: `EXPLAIN QUERY PLAN ...`
- Use caching for frequently accessed data
- Batch updates instead of single updates

**Connection Pool Optimization:**
```python
# AsyncBinanceClient uses connection pooling
async with AsyncBinanceClient() as client:  # Reuses connection pool
    for symbol in symbols:
        await client.get_price(symbol)  # Concurrent requests
```

---

## Correlation ID Tracking

Every operation in the system includes a unique correlation ID for traceability:

```python
correlation_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
extra = {'correlation_id': correlation_id}

self.logger.info("Starting workflow", extra=extra)
# Logs: [CORR-ID: trade_20251109_120000_123456] Starting workflow

self.logger.error("Workflow failed", extra=extra)
# Logs: [CORR-ID: trade_20251109_120000_123456] Workflow failed

# Trace all operations with same correlation ID in logs
```

---

## Quick Command Reference

```bash
# Deployment
./deploy.sh development           # Start dev environment
./deploy.sh production            # Production deployment
docker-compose down               # Stop all services
docker-compose logs -f            # View live logs

# Testing
pytest binance_trade_agent/tests/ -v              # Run all tests
pytest -m "not integration"                       # Skip integration tests
docker-compose exec trading-agent pytest -v      # Tests in container

# Database
docker-compose exec trading-agent sqlite3 /app/data/web_portfolio.db
  > SELECT * FROM trades;        # Query trades

# Container Access
docker-compose exec trading-agent /bin/bash      # Shell access
docker-compose exec trading-agent python -c "..." # Run Python code

# Troubleshooting
docker-compose ps                                # Check status
docker-compose logs --tail=50 trading-agent      # Recent logs
docker stats                                     # Resource usage
docker-compose up -d --force-recreate            # Full restart
```

---

## Additional Resources

- **Binance API Documentation:** https://binance-docs.github.io/apidocs/
- **Binance Testnet:** https://testnet.binance.vision
- **Python AsyncIO:** https://docs.python.org/3/library/asyncio.html
- **SQLAlchemy ORM:** https://docs.sqlalchemy.org/
- **Streamlit Docs:** https://docs.streamlit.io/

---

**Last Updated:** November 9, 2025  
**Status:** Production-ready  
**Supported Python:** 3.10+  
**License:** MIT
