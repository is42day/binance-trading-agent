"""
API Client for the Dash Dashboard
Centralizes all HTTP requests to the FastAPI data service
"""

import os
import time
from typing import Any, Dict, List

import requests

# Get API URL from environment
# Priority order:
# 1. API_BASE_URL (full URL override)
# 2. API_HOST + API_PORT (Docker services: api:8000, Local: localhost:8000)
# 3. Default: localhost:8000

if os.getenv("API_BASE_URL"):
    API_BASE_URL = os.getenv("API_BASE_URL")
else:
    API_HOST = os.getenv("API_HOST", "localhost")
    API_PORT = os.getenv("API_PORT", "8000")
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}/api/v1"

# Connection settings
REQUEST_TIMEOUT = 5  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

print(f"[API Client] Connecting to: {API_BASE_URL}")


def _make_request_with_retry(url: str, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
    """
    Make HTTP request with retry logic for transient failures.
    
    Args:
        url: Full URL to request
        max_retries: Maximum number of retry attempts
        
    Returns:
        JSON response as dict, or dict with 'error' key on failure
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection failed to {API_BASE_URL} - is API service running?"
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                continue
        except requests.exceptions.Timeout as e:
            last_error = f"Request timeout after {REQUEST_TIMEOUT}s"
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
    
    print(f"API Error after {max_retries} retries: {last_error}")
    return {"error": last_error}


def get_portfolio_summary() -> Dict[str, Any]:
    """Fetch portfolio summary stats."""
    return _make_request_with_retry(f"{API_BASE_URL}/portfolio/summary")


def get_all_positions() -> List[Dict[str, Any]]:
    """Fetch all open positions."""
    result = _make_request_with_retry(f"{API_BASE_URL}/portfolio/positions")
    if "error" in result:
        return []
    return result.get("positions", [])


def get_trade_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent trade history."""
    result = _make_request_with_retry(f"{API_BASE_URL}/portfolio/trade-history?limit={limit}")
    if "error" in result:
        return []
    return result.get("trades", [])


def get_risk_status() -> Dict[str, Any]:
    """Fetch risk management agent status."""
    return _make_request_with_retry(f"{API_BASE_URL}/risk/status")


def get_market_price(symbol: str) -> Dict[str, Any]:
    """Fetch the latest price for a symbol."""
    result = _make_request_with_retry(f"{API_BASE_URL}/market/price/{symbol}")
    if "error" in result and "price" not in result:
        result["price"] = 0  # Add default price for error case
    return result


def get_system_config() -> Dict[str, Any]:
    """Fetch system configuration details."""
    return _make_request_with_retry(f"{API_BASE_URL}/system/config")
