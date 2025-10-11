# Binance Trading Agent

A comprehensive automated trading system for Binance with advanced risk management, portfolio tracking, and web UI.

## Quick Start

1. **Setup Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Binance testnet API keys
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the System:**
   ```bash
   # Start MCP server
   python binance_trade_agent/mcp_server.py

   # Launch web UI (in another terminal)
   streamlit run binance_trade_agent/web_ui.py

   # Or use CLI
   python binance_trade_agent/cli.py
   ```

## Features

- ✅ Complete agent chaining & orchestration
- ✅ Portfolio tracking with SQLite persistence
- ✅ Enhanced risk management with advanced controls
- ✅ Structured logging & monitoring system
- ✅ Full MCP integration with 15+ tools
- ✅ Interactive CLI for manual trading
- ✅ Streamlit web UI dashboard
- ✅ Production-ready deployment

## Documentation

See [binance_trade_agent/README.md](binance_trade_agent/README.md) for comprehensive documentation, API reference, and deployment guides.

## ⚠️ Important

This system is configured for **Binance TESTNET** by default. Do not use real API keys or funds without thorough testing.