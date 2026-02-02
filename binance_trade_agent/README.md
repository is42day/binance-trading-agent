# Binance Trading Agent - Comprehensive Trading System

A production-ready automated trading system for Binance with advanced risk management, portfolio tracking, monitoring, and MCP integration.

## 🚀 Features

### Core Trading Components
- **Market Data Agent**: Real-time price feeds and order book data from Binance API
- **Signal Agent**: Technical analysis with RSI, MACD, and custom indicators
- **Risk Management Agent**: Advanced risk controls with position sizing, stop-loss, and drawdown protection
- **Trade Execution Agent**: Automated order placement with error handling
- **Orchestrator**: Complete workflow management from signal generation to execution

### Advanced Features
- **Portfolio Management**: SQLite-backed position tracking with P&L calculations
- **Enhanced Risk Controls**:
  - Stop-loss/take-profit automation
  - Position sizing limits
  - Maximum drawdown protection
  - Trading frequency controls
  - Symbol-specific rules
- **Structured Logging & Monitoring**:
  - Correlation ID tracking
  - Performance metrics collection
  - System health monitoring
  - Optional Prometheus integration
- **Command Line Interface**: Interactive CLI for testing and manual trading
- **MCP Integration**: Model Context Protocol server exposing all trading functionality
- **Web UI**: Streamlit-based dashboard for portfolio management, trading, and monitoring

## 📁 Project Structure

```
binance_trade_agent/
├── __init__.py                 # Package initialization
├── binance_client.py          # Binance API wrapper
├── market_data_agent.py       # Market data retrieval
├── signal_agent.py            # Technical analysis & signals
├── risk_management_agent.py   # Enhanced risk management
├── trade_execution_agent.py   # Order execution
├── orchestrator.py            # Workflow orchestration
├── portfolio_manager.py       # Portfolio tracking & P&L
├── monitoring.py              # Logging & metrics system
├── cli.py                     # Command line interface
├── mcp_server.py              # MCP server implementation
├── mcp_client.py              # MCP client for testing
├── web_ui.py                  # Streamlit web dashboard
├── demo.py                    # Quick demonstration
├── config.py                  # Configuration management
├── utils.py                   # Utility functions
└── tests/                     # Comprehensive test suite
    ├── test_agent_flow.py     # Integration tests
    ├── test_binance_client.py # API client tests
    ├── test_market_data_agent.py
    ├── test_signal_agent.py
    ├── test_mcp_integration.py
    └── ...
```

## 🛠️ Installation & Setup

### 1. Environment Setup
```bash
# Clone and navigate to project
cd binance-trading-agent

# Build and run Docker container
make run
make attach

# Or install dependencies locally
pip install -r requirements.txt
```

### 2. Configuration
Create `.env` file with your Binance testnet credentials:
```env
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_secret_key
BINANCE_TESTNET=true
```

### 3. Quick Start
```python
# In Docker container
python binance_trade_agent/demo.py

# Or run interactive CLI
python binance_trade_agent/cli.py
```

## 🎮 Usage Examples

### Command Line Interface
```bash
# Start interactive CLI
python binance_trade_agent/cli.py

# Available commands:
(trading) buy BTCUSDT 0.001      # Place buy order
(trading) sell BTCUSDT 0.001     # Place sell order
(trading) status                 # System status
(trading) portfolio              # Portfolio summary
(trading) positions              # Current positions
(trading) trades                 # Trade history
(trading) signals BTCUSDT        # Get trading signals
(trading) risk BTCUSDT buy 0.001 50000  # Test risk management
(trading) market BTCUSDT         # Market data
(trading) metrics                # Performance metrics
(trading) logs                   # Recent logs
(trading) emergency on           # Emergency stop
```

### Python API
```python
from binance_trade_agent.orchestrator import TradingOrchestrator
from binance_trade_agent.portfolio_manager import PortfolioManager

# Initialize components
orchestrator = TradingOrchestrator()
portfolio = PortfolioManager()

# Execute trading workflow
decision = await orchestrator.execute_trading_workflow("BTCUSDT", 0.001)

# Check portfolio
stats = portfolio.get_portfolio_stats()
positions = portfolio.get_all_positions()
```

### MCP Server Integration
```python
# Start MCP server
python binance_trade_agent/mcp_server.py

# Or use client
python binance_trade_agent/mcp_client.py
```

### Web UI Dashboard
```bash
# Option 1: Using Docker (recommended)
./deploy.sh development
# Web UI automatically available at http://localhost:8501

# Option 2: Manual installation
pip install streamlit
streamlit run binance_trade_agent/web_ui.py
# Access at http://localhost:8501
```

The web UI provides:
- **Portfolio Overview**: Live positions, P&L, and allocation charts
- **Market Data**: Real-time prices, order book, and trading pairs
- **Trade Execution**: Buy/sell forms with risk validation
- **Signals & Risk**: Latest signals and risk management status
- **Logs & Monitoring**: System health and performance metrics
- **Advanced Controls**: Emergency stop and system management

## 🔒 Risk Management Features

### Position Sizing
- Maximum position per symbol (default: 5% of portfolio)
- Maximum single trade size (default: 2% of portfolio)
- Total portfolio exposure limits (default: 80%)

### Stop-Loss & Take-Profit
- Automatic stop-loss calculation (default: 2%)
- Take-profit targets (default: 6% for 3:1 ratio)
- Trailing stop support

### Drawdown Protection
- Maximum daily drawdown limits (default: 5%)
- Maximum total drawdown limits (default: 15%)
- Automatic trading pause after drawdown breaches

### Frequency Controls
- Maximum trades per hour/day
- Minimum time between trades
- Consecutive loss protection

### Emergency Controls
- Emergency stop functionality
- Manual override capabilities
- Risk rule configuration

## 📊 Monitoring & Metrics

### Structured Logging
- Correlation ID tracking across components
- Event-based logging with context
- Configurable log levels and formats

### Performance Metrics
- Trade execution timing
- Signal generation performance
- Risk assessment duration
- API call latency
- Success/failure rates

### Health Monitoring
- System uptime tracking
- Error rate monitoring
- Portfolio value tracking
- Position count monitoring

## 🧪 Testing

### Run Test Suite
```bash
# All tests
pytest binance_trade_agent/tests/

# Specific test categories
pytest binance_trade_agent/tests/test_agent_flow.py      # Integration tests
pytest binance_trade_agent/tests/test_binance_client.py  # API tests
pytest binance_trade_agent/tests/test_mcp_integration.py # MCP tests
```

### Integration Testing
The test suite includes comprehensive integration tests that validate:
- End-to-end trading workflows
- Live Binance testnet connectivity
- Risk management validation
- Portfolio tracking accuracy
- MCP tool functionality

## 🚀 Deployment

### Docker Deployment
```bash
# Build production image
docker build -t binance-trading-agent .

# Run with environment variables
docker run -d \
  -e BINANCE_API_KEY=your_key \
  -e BINANCE_API_SECRET=your_secret \
  -e BINANCE_TESTNET=true \
  binance-trading-agent
```

### Production Considerations
- Use proper secret management for API keys
- Configure appropriate risk limits
- Set up monitoring and alerting
- Implement backup strategies for portfolio data
- Consider rate limiting and API quotas

## 📝 Configuration

### Risk Management Config
```python
# Default configuration in risk_management_agent.py
config = {
    'max_position_per_symbol': 0.05,    # 5% per symbol
    'max_total_exposure': 0.8,          # 80% total exposure
    'max_single_trade_size': 0.02,      # 2% per trade
    'default_stop_loss_pct': 0.02,      # 2% stop-loss
    'default_take_profit_pct': 0.06,    # 6% take-profit
    'max_daily_drawdown': 0.05,         # 5% daily drawdown
    'max_total_drawdown': 0.15,         # 15% total drawdown
    'max_trades_per_day': 50,           # Daily trade limit
    'emergency_stop': False             # Emergency stop state
}
```

### Symbol-Specific Rules
```python
'symbol_rules': {
    'BTCUSDT': {
        'max_position': 0.1,            # 10% max position
        'volatility_multiplier': 1.0    # Standard volatility handling
    },
    'ETHUSDT': {
        'max_position': 0.08,           # 8% max position
        'volatility_multiplier': 1.2    # Higher volatility adjustment
    }
}
```

## 🔍 Troubleshooting

### Common Issues
1. **API Connection Errors**: Check API keys and testnet settings
2. **Risk Rejections**: Review position sizing and risk limits
3. **Portfolio Sync Issues**: Update market prices regularly
4. **Memory Issues**: Monitor log retention and metric storage

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python binance_trade_agent/cli.py
```

### Health Checks
```python
# Check system health
from binance_trade_agent.monitoring import monitoring
health = monitoring.get_health_status()
print(health)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

## ⚠️ Disclaimer

This software is for educational and testing purposes only. Use at your own risk. Always test thoroughly on Binance testnet before considering any live trading. The authors are not responsible for any financial losses.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Resources

- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Technical Analysis Library](https://technical-analysis-library-in-python.readthedocs.io/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Docker Documentation](https://docs.docker.com/)

---

**Happy Trading! 📈**

## Repository State (as of October 10, 2025)


This project is a modular Python trading agent for Binance, designed for AI integration and orchestration using LangChain and the Model Context Protocol (MCP). The repo is fully containerized for development and deployment using Docker and VS Code DevContainers.

**Recent Updates:**
- `MarketDataAgent` implemented for structured price, order book, and balance retrieval via Binance.
- Matching tests for `MarketDataAgent` in `tests/test_market_data_agent.py`.
- MCP server integration instructions and config examples included.
- `requirements.txt` updated for all dependencies.

**Current State (as of October 10, 2025):**
- All core files (`Dockerfile`, `requirements.txt`, `supervisord.conf`) are now located in the workspace root for correct Docker builds.
- The container builds and runs successfully using:
	- `docker build -t binance-agent -f Dockerfile .`
	- `docker run -d --env-file binance_trade_agent/.env.example -p 8080:8080 binance-agent`
- You can attach to the running container for development/debugging:
	- `docker exec -it <container_id> /bin/bash`
- Both MCP server and agent processes are managed by Supervisor and stay running until the container is stopped.
- VS Code DevContainer workflow is supported; you can use "Reopen in Container" for integrated development.

### Structure

binance_trade_agent/
│
```
binance-trading-agent/
│
├── Dockerfile                   # Container build instructions (now in workspace root)
├── requirements.txt             # Python dependencies (langchain, python-binance, supervisor, mcp-server-git)
├── supervisord.conf             # Supervisor config (workspace root)
├── .env.example                 # Environment variable template
├── README.md                    # Project documentation
│
├── .devcontainer/
│   └── devcontainer.json        # VS Code DevContainer config
│
├── binance_trade_agent/
│   ├── __init__.py
│   ├── binance_client.py        # Binance API wrapper (sync, price/order/balance/trade)
│   ├── config.py                # Loads environment variables
│   ├── main.py                  # Main entry point
│   ├── market_data_agent.py     # LangChain agent for market data (MCP tool)
│   └── utils.py                 # Utility functions
│
├── tests/
│   ├── __init__.py
│   ├── test_binance_client.py   # Pytest for Binance client
│   └── test_market_data_agent.py # Pytest for MarketDataAgent
```

### Key Features
- **Docker/DevContainer:** All dependencies and environment setup are handled in the container. No host Python setup required.
- **MCP Server:** Uses the official Python MCP server (`mcp-server-git`) installed via pip. Git is installed in the container for MCP server functionality.
- **Binance API:** Synchronous wrapper for price, order book, balance, and order management.
- **Testing:** Pytest supported out of the box, with coverage for Binance client and MarketDataAgent.
- **Supervisor:** Manages both MCP server and agent process in the container. MCP server is launched via supervisord and configured via `/opt/mcpserver/config.toml`.
- **VS Code Integration:** Includes `.devcontainer` and `.vscode/mcp.json` for MCP debugging and development.

### Current Status



- Container builds and runs successfully with all dependencies in the workspace root.
- MCP server and agent both launch and stay running via Supervisor.
- MarketDataAgent is registered as a tool in MCP server and accessible via API endpoints.
- You can run the container in detached mode and attach a shell for debugging/development.
- `main.py` supports a long-running agent loop, compatible with Docker and Supervisor.
- Python codebase is scaffolded for modular development and testing.
- Ready for further extension (tools, orchestration, cloud integration).

---

## Getting Started (with Docker & DevContainer)

### Prerequisites

- Docker Desktop (https://www.docker.com/products/docker-desktop)
- Visual Studio Code + DevContainers Extension (https://code.visualstudio.com)

### Steps


1. Clone this repo.
2. Copy or rename `.env.example` to `.env` and fill in your API keys.
3. Build the Docker image:
	```powershell
	docker build -t binance-agent -f Dockerfile .
	```
4. Run the container in detached mode:
	```powershell
	docker run -d --env-file binance_trade_agent/.env.example -p 8080:8080 binance-agent
	```
5. Attach to the running container for development/debugging:
	```powershell
	docker exec -it <container_id> /bin/bash
	```
6. Use `docker logs <container_id>` to verify both MCP server and your agent are running.
7. Access MCP server on `localhost:8080` (use correct port if changed).
8. For VS Code DevContainer workflow, use "Reopen in Container" for integrated development.
9. Begin developing modules and run tests inside the container.

**Testing:**


**Testing:**
- Use `pytest binance_trade_agent/tests/test_binance_client.py` and `pytest binance_trade_agent/tests/test_market_data_agent.py` in `/app` to run tests inside the container shell.

**MCP Integration:**

**MCP Integration:**

**MCP Integration:**
- Adjust `/app/mcpserver_setup.sh` and `/opt/mcpserver/config.toml` as needed for your cloud, access, and orchestration goals.
- Register tools (agents) in MCP config and test endpoints with curl as described above.
