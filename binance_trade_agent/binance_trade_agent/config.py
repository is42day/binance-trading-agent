# binance_trade_agent/config.py
import os

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
MCP_SERVER_PORT = os.getenv('MCP_SERVER_PORT', '8080')
