# Binance Trade Agent - LangChain, MCP, Binance

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
