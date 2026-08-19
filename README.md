# Binance Trading Agent

**Fully automated trading system for Binance with intelligent agent orchestration, real-time portfolio management, and comprehensive risk controls.**

🚀 **[Get Started Now](#quick-start)** | 📊 **[Live Dashboard](#dashboard)** | 📖 **[Full Docs](docs/README.md)**

## 🎯 Current Status

✅ **Production Ready** - Automated trading running on Binance Testnet  
✅ **Real-time Execution** - Trading every 60 seconds with live price capture  
✅ **Portfolio Tracking** - Trades persisting with correct prices and P&L calculation  
✅ **Web Dashboard** - Beautiful Dash UI showing portfolio, recent trades, and market data  
✅ **All Systems Operational** - API, Trading Agent, and Dashboard synchronized

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed
- Binance Testnet account ([Create here](https://testnet.binance.vision))

### 1. Clone & Setup (2 minutes)
```bash
git clone <repo>
cd binance-trading-agent
cp .env.example .env
```

### 2. Add Testnet Credentials to .env
```bash
# Edit .env with your Binance Testnet API credentials
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
BINANCE_TESTNET=true  # CRITICAL: Never remove this line
```

### 3. Start the System (1 command)
```bash
make start
```

**Or manually (without Makefile)**:
```bash
docker build -t binance-trading-agent:latest . -q
docker rm api dashboard trading-agent -f 2>/dev/null
docker run -d -p 8000:8000 --env-file .env -v "$(pwd)/data:/app/data" --name api binance-trading-agent:latest python -m binance_trade_agent.api.api
docker run -d -p 8050:8050 --env-file .env --name dashboard binance-trading-agent:latest python binance_trade_agent/dashboard/run.py
docker run -d --env-file .env -v "$(pwd)/logs:/app/logs" -v "$(pwd)/data:/app/data" --name trading-agent binance-trading-agent:latest python start_auto_trading.py --strategy combined --symbols BTCUSDT --interval 60
```

### 4. Access the System
- **React Dashboard**: http://localhost:8080 (Modern React + TypeScript UI - **recommended**)
- **API**: http://localhost:8000/docs (REST API + OpenAPI docs)
- **Legacy Dash Dashboard**: http://localhost:8050 (Python Dash UI - still available)
- **Trading Agent Logs**: `docker logs trading-agent -f`

---

## 📊 Dashboard Features

### React + TypeScript Frontend (Port 8080) — **Recommended**
A modern, professional trading dashboard built with React 19, TypeScript, TailwindCSS, and Recharts:

- **Dashboard** — Portfolio value, P&L, open positions, recent trades table
- **Market Data** — Symbol selector, live price, 24h change, live price trend chart
- **Paper Trading** — Paper trading status, portfolio stats, signals & trades log
- **Signals & Risk** — Emergency stop status, drawdown, trailing stops table, risk config
- **Performance** — Win rate, Sharpe ratio, profit factor, performance by symbol
- **System Health** — Health/readiness checks, API status, configuration display

> Auto-refreshes every 30 seconds; shows graceful "API Offline" state when backend is unavailable.

### Legacy Dash Dashboard (Port 8050)
Python Dash-based UI — still available but deprecated in favor of the React frontend.

---

## ✨ Key Features

### 🤖 Intelligent Agent Orchestration
Four specialized agents working in sequence:
1. **Market Data Agent** - Fetches real-time price data from Binance
2. **Signal Agent** - Generates trading signals (RSI, MACD, or Combined strategy)
3. **Risk Management Agent** - Validates trades against portfolio limits
4. **Trade Execution Agent** - Places orders and persists to database

### 💼 Portfolio Management
- Real-time position tracking across multiple symbols
- Trade history with execution prices and fees
- P&L calculation (both realized and unrealized)
- Multi-symbol support (default: BTCUSDT)

### 🛡️ Risk Controls
- Position size limits per symbol
- Daily and hourly trade frequency limits
- Minimum time between trades
- Emergency stop capability
- Drawdown monitoring with trailing stops

### 📈 Trading Strategies
- **RSI Strategy** - Relative Strength Index based signals
- **MACD Strategy** - Moving Average Convergence Divergence
- **Combined Strategy** - Hybrid approach (current default)
- **Edge / Smart Entry strategies** - Advanced signal generation

### 🔌 Rest API
All data accessible via FastAPI endpoints (docs at http://localhost:8000/docs):
```bash
GET  /api/v1/portfolio/summary          # Portfolio metrics
GET  /api/v1/portfolio/trade-history    # Recent trades
GET  /api/v1/portfolio/positions        # Current positions
GET  /api/v1/market/price/<symbol>      # Current price
GET  /api/v1/risk/status                # Risk assessment
GET  /api/v1/performance/summary        # Performance analytics
GET  /api/v1/paper-trading/status       # Paper trading state
GET  /health                            # Health check
GET  /ready                             # Readiness probe
```

---

## 🗄️ Database: SQLite → PostgreSQL Migration

### Production-Grade Database Support

The system now supports **PostgreSQL** for multi-writer safety and production reliability, while maintaining backward compatibility with SQLite for local development.

### Database Configuration

**Option 1: PostgreSQL (Recommended for Production)**
```bash
# Set in .env or environment
DATABASE_URL=postgresql+psycopg2://trading_user:password@postgres:5432/binance_trading
```

**Option 2: SQLite (Local Development)**
```bash
# Set in .env or environment
DB_PATH=/app/data/portfolio.db
```

### Quick Start with PostgreSQL

1. **Start PostgreSQL**
```bash
make db-up
# Or: docker-compose up -d postgres
```

2. **Run Migrations**
```bash
make migrate
# Or: alembic upgrade head
```

3. **Migrate Existing SQLite Data (Optional)**
```bash
make migrate-sqlite
# Or: python -m binance_trade_agent.scripts.migrate_sqlite_to_postgres
```

4. **Start Trading System**
```bash
docker-compose up -d
```

For a single-VPS deployment that runs the complete stack on its own, use the
[VPS deployment runbook](docs/VPS_DEPLOYMENT.md). It covers required secrets,
preflight checks, safe port bindings, health checks, backups, and live-trading
opt-in.

### Migration Features

- **Idempotent**: Can run multiple times safely
- **Validation**: Compares row counts before/after
- **Safety**: Confirmation prompts, preserves existing data
- **Batch Processing**: Handles large datasets efficiently

### PostgreSQL Benefits

✅ **Multi-writer safety** - No more "database is locked" errors  
✅ **ACID transactions** - Consistent concurrent writes  
✅ **Schema migrations** - Alembic for version control  
✅ **Production-grade** - Connection pooling, health checks  
✅ **Better performance** - Optimized indexes for trading queries

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Trading System Architecture                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐              │
│  │React Frontend  │   │    FastAPI     │   │  Trading Agent │              │
│  │  (Port 8080)   │◄─►│   (Port 8000)  │   │  (Background)  │              │
│  │React+TypeScript│   │   REST API     │   │  Autonomous    │              │
│  └───────┬────────┘   └───────┬────────┘   └───────┬────────┘              │
│          │                    │                    │                        │
│          ▼                    ▼                    ▼                        │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                    Shared Components                         │           │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │           │
│  │  │MarketData   │ │ SignalAgent │ │   RiskManagement      │ │           │
│  │  │Agent (REST) │►│ (Strategies)│►│   Agent (887 lines)   │ │           │
│  │  └──────┬──────┘ └──────┬──────┘ └───────────┬────────────┘ │           │
│  │         │               │                    │               │           │
│  │         ▼               ▼                    ▼               │           │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │           │
│  │  │Binance      │ │ Strategies  │ │   TradeExecution      │ │           │
│  │  │Client       │ │ RSI/MACD/BB │ │   Agent               │ │           │
│  │  │(REST ONLY!) │ │ Combined    │ │   (Portfolio Manager) │ │           │
│  │  └─────────────┘ └─────────────┘ └───────────┬────────────┘ │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                 │                           │
│  ┌─────────────────────────────────────────────┼───────────────┐           │
│  │                    Data Layer               │                │           │
│  │  ┌─────────────┐ ┌────────────┐ ┌──────────▼─────────────┐  │           │
│  │  │ RedisCache  │ │ PostgreSQL │ │ SQLite                  │  │           │
│  │  │ (fallback   │ │ (prod)     │ │ (local testing)        │  │           │
│  │  │ InMemory)   │ │ Alembic    │ │ web_portfolio.db       │  │           │
│  │  └─────────────┘ └────────────┘ └─────────────────────────┘  │           │
│  └─────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Technology Stack

- **Framework**: Python 3.10+
- **Trading**: Binance API (python-binance)
- **Frontend**: React 19 + TypeScript + Vite + TailwindCSS + Recharts *(new)*
- **Legacy UI**: Dash (Plotly) *(deprecated)*
- **API**: FastAPI
- **Database**: SQLAlchemy ORM + PostgreSQL (production) / SQLite (dev)
- **Migrations**: Alembic
- **Deployment**: Docker + Docker Compose
- **Monitoring**: Custom logging system with correlation tracking
- **Testing**: Pytest + pytest-asyncio

---

## 🔧 Available Commands

### Docker Management
```bash
# View logs
docker logs trading-agent -f      # Trading agent logs
docker logs api -f                # API logs
docker logs dashboard -f          # Dashboard logs

# Stop system
docker rm api dashboard trading-agent -f

# Rebuild image
docker build -t binance-trading-agent:latest . -q
```

### Testing
```bash
# Run all tests
docker run --rm -v "$(pwd):/app" -w /app binance-trading-agent:latest pytest -v

# Run specific test
docker run --rm -v "$(pwd):/app" -w /app binance-trading-agent:latest pytest tests/test_api_endpoints.py -v

# Run with coverage
docker run --rm -v "$(pwd):/app" -w /app binance-trading-agent:latest pytest --cov=binance_trade_agent tests/
```

### Interactive CLI
```bash
# Launch command-line interface
docker run -it --env-file .env binance-trading-agent:latest python -m binance_trade_agent.scripts.cli

# Available commands: buy, sell, portfolio, positions, trades, signals, market, risk, status, metrics, etc.
```

---

## ⚙️ Configuration

### Risk Management (in `binance_trade_agent/agents/risk_management_agent.py`)
```python
'max_trades_per_hour': 100           # Max trades per hour
'max_trades_per_day': 500            # Max trades per day
'min_time_between_trades': 5         # Seconds between trades
'max_position_per_symbol': 0.10      # 10% of portfolio per symbol
'max_single_trade_size': 0.05        # 5% of portfolio per trade
'default_stop_loss_pct': 0.02        # 2% stop loss
'default_take_profit_pct': 0.05      # 5% take profit
```

### Trading Loop (in `start_auto_trading.py`)
```python
--strategy combined     # Strategy name (default: combined)
--symbols BTCUSDT      # Trading symbols (comma-separated)
--interval 60          # Trading loop interval in seconds
```
Trade quantity per symbol is configured via env vars (e.g. `TRADING_DEFAULT_QUANTITY_BTC`), not a CLI flag — see `.env.example`.

### Database
- Location: `data/web_portfolio.db` (SQLite)
- Auto-created on first run
- Contains: Trades, Positions, Order history
- Shared between Trading Agent, API, and Dashboard

---

## 📈 Performance Metrics

Recent trading session (Testnet):
- **Trading Frequency**: 1 trade per ~60 seconds
- **Strategy**: Combined (RSI + MACD)
- **Symbol**: BTCUSDT
- **Trade Size**: 0.001 BTC per trade
- **Risk Level**: Low (all trades approved)
- **Price Capture**: Accurate (prices from Binance API)

---

## 🐛 Troubleshooting

### Trades not appearing in dashboard?
```bash
# 1. Check if database is accessible
ls -la data/web_portfolio.db

# 2. Check API logs
docker logs api -f

# 3. Refresh dashboard (F5 in browser)

# 4. Verify API endpoint
curl http://localhost:8000/api/v1/portfolio/trade-history
```

### Trading agent not executing trades?
```bash
# Check logs
docker logs trading-agent -f

# Verify risk management is approving trades
# Look for: "Risk assessment: low - Approved: True"

# Check Binance connectivity
docker logs trading-agent -f | grep -i "market data"
```

### API not connecting?
```bash
# Rebuild with fresh data volume
docker rm api -f
docker run -d -p 8000:8000 --env-file .env -v "$(pwd)/data:/app/data" --name api binance-trading-agent:latest python -m binance_trade_agent.api.api

# Check logs
docker logs api -f
```

### Dashboard won't load?
```bash
# Check dashboard logs
docker logs dashboard -f

# Rebuild dashboard
docker rm dashboard -f
docker run -d -p 8050:8050 --env-file .env --name dashboard binance-trading-agent:latest python binance_trade_agent/dashboard/run.py
```

---

## 📚 Documentation

Complete documentation available in `docs/`:
- **[COMPREHENSIVE_GUIDE.md](docs/COMPREHENSIVE_GUIDE.md)** - Full system guide
- **[DEVELOPMENT_REFERENCE.md](docs/DEVELOPMENT_REFERENCE.md)** - API and code patterns
- **[QUICK_START_AUTONOMOUS_TRADING.md](docs/QUICK_START_AUTONOMOUS_TRADING.md)** - Autonomous trading setup
- **[binance_trade_agent/README.md](binance_trade_agent/README.md)** - Package documentation

---

## ⚠️ Critical Notes

### 🔴 Testnet Only
- System is configured for **Binance TESTNET** with fake funds
- Do NOT add production API keys
- `BINANCE_TESTNET=true` must remain in .env
- No real money is at risk

### 🐳 Docker Required
- Python virtual environment setup is not supported
- All deployment must use Docker
- Ensure Docker Desktop is running

### 📊 Data Persistence
- All trades stored in `data/web_portfolio.db`
- Database is NOT committed to git (.gitignore)
- Each run creates new database
- Backup important data before restarting

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test: `docker run --rm -v "$(pwd):/app" -w /app binance-trading-agent:latest pytest`
3. Commit: `git commit -am "feat: description"`
4. Push: `git push origin feature/my-feature`
5. Submit PR with test results

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙋 Support

**Issues?** Check the [Troubleshooting](#troubleshooting) section above or see full docs in `docs/`

**Questions?** Review the architecture section or read COMPREHENSIVE_GUIDE.md

---

**Last Updated**: November 28, 2025  
**Status**: ✅ Production Ready  
**Test Network**: Binance Testnet  
**Python Version**: 3.10+
