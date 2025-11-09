# Binance Trading Agent

**Automated trading system for Binance with agent-based architecture, portfolio management, and risk controls.**

⏱️ **5-Minute Quickstart** | 📖 **[Full Documentation](COMPREHENSIVE_GUIDE.md)** | 👨‍💻 **[Development Guide](DEVELOPMENT_REFERENCE.md)**

## 🚀 Quick Start (5 Minutes)

### 1. Get Testnet API Keys
Create an account at [Binance Testnet](https://testnet.binance.vision) and generate API keys.

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your testnet API keys
# BINANCE_API_KEY=your_key
# BINANCE_API_SECRET=your_secret
# BINANCE_TESTNET=true (DO NOT REMOVE)
```

### 3. Start System (Docker Recommended)
```bash
./deploy.sh development
# Wait 10-15 seconds for startup
# Then visit: http://localhost:8501
```

### 4. Verify It Works
Click "Portfolio" tab → Should show portfolio stats and positions.

---

## ✨ Key Features

- **Agent Orchestration** - Market Data → Signal Analysis → Risk Management → Trade Execution
- **Portfolio Tracking** - Real-time P&L, position management, trade history
- **Risk Controls** - Emergency stop, position limits, stop-loss enforcement
- **Web UI** - Streamlit dashboard with real-time data visualization
- **MCP Integration** - 15+ tools for AI agent integration
- **Production Ready** - Docker deployment, health checks, monitoring

---

## 📚 Documentation

- **[COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md)** - Complete usage guide, architecture, testing, deployment, troubleshooting (START HERE for full docs)
- **[DEVELOPMENT_REFERENCE.md](DEVELOPMENT_REFERENCE.md)** - API reference, code patterns, optimization, extending system
- **[binance_trade_agent/README.md](binance_trade_agent/README.md)** - Package-level documentation

---

## 🔧 Available Commands

```bash
# Deployment
./deploy.sh development                    # Start dev environment
./deploy.sh production                     # Production build
docker-compose logs -f                     # View live logs
docker-compose down                        # Stop all services

# Testing
docker-compose exec trading-agent pytest -v    # Run all tests
docker-compose exec trading-agent pytest -m "not integration"  # Skip integration tests

# Web UI
http://localhost:8501                      # Access dashboard

# Interactive CLI
docker-compose exec trading-agent python binance_trade_agent/cli.py
```

---

## ⚠️ Important Notes

- **Testnet Only** - System uses Binance TESTNET by default with fake funds
- **Do NOT use production API keys** - Never replace `BINANCE_TESTNET=true` with real credentials
- **Docker Required** - Local Python setup not supported; always use Docker for deployment

---

## 🆘 Troubleshooting

**Portfolio not loading?**
```bash
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

**Container won't start?**
```bash
docker-compose logs -f trading-agent
```

**See [COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md#troubleshooting) for full troubleshooting guide.**

---

**Python 3.10+ | Production Ready | MIT License**