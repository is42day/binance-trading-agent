"""
API Client for the Dash Dashboard
Centralizes all HTTP requests to the FastAPI data service
"""

import requests
import pandas as pd
import os
from typing import Dict, List, Optional, Any

# Get API URL from environment or use host.docker.internal for Docker Desktop
# When running locally: http://localhost:8000
# When running in Docker: http://host.docker.internal:8000 (Docker Desktop)
API_HOST = os.getenv("API_HOST", "host.docker.internal")
API_PORT = os.getenv("API_PORT", "8000")
API_BASE_URL = f"http://{API_HOST}:{API_PORT}/api/v1"

def get_portfolio_summary() -> Dict[str, Any]:
    """Fetch portfolio summary stats."""
    try:
        response = requests.get(f"{API_BASE_URL}/portfolio/summary")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_portfolio_summary): {e}")
        return {"error": str(e)}

def get_all_positions() -> List[Dict[str, Any]]:
    """Fetch all open positions."""
    try:
        response = requests.get(f"{API_BASE_URL}/portfolio/positions")
        response.raise_for_status()
        return response.json().get("positions", [])
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_all_positions): {e}")
        return []

def get_trade_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent trade history."""
    try:
        response = requests.get(f"{API_BASE_URL}/portfolio/trade-history?limit={limit}")
        response.raise_for_status()
        return response.json().get("trades", [])
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_trade_history): {e}")
        return []

def get_risk_status() -> Dict[str, Any]:
    """Fetch risk management agent status."""
    try:
        response = requests.get(f"{API_BASE_URL}/risk/status")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_risk_status): {e}")
        return {"error": str(e)}

def get_market_price(symbol: str) -> Dict[str, Any]:
    """Fetch the latest price for a symbol."""
    try:
        response = requests.get(f"{API_BASE_URL}/market/price/{symbol}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_market_price): {e}")
        return {"error": str(e), "price": 0}

def get_system_config() -> Dict[str, Any]:
    """Fetch system configuration details."""
    try:
        response = requests.get(f"{API_BASE_URL}/system/config")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_system_config): {e}")
        return {"error": str(e)}
