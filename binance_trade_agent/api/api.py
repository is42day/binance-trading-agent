"""
FastAPI Data Service for Binance Trading Agent
Exposes portfolio, risk, and market data to the Dash UI
"""

import logging
import traceback
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..agents.market_data_agent import MarketDataAgent
from ..agents.risk_management_agent import EnhancedRiskManagementAgent
from ..clients.redis_cache import RedisCache
from ..common.config import config
from ..core.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Binance Trading Agent API",
    description="API for real-time trading data and system monitoring.",
    version="1.0.0",
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
# Use web_portfolio.db which is shared with the dashboard and trading agent
portfolio_manager = PortfolioManager(db_path="/app/data/web_portfolio.db")
risk_agent = EnhancedRiskManagementAgent()
market_agent = MarketDataAgent()
cache = RedisCache(host="redis")  # Use the service name from docker-compose

# --- Lifecycle Events ---


@app.on_event("startup")
async def startup_event():
    """Connect to Redis on startup."""
    logger.info("=== STARTUP EVENT TRIGGERED ===")
    try:
        logger.info("Calling cache.connect()...")
        await cache.connect()
        logger.info("✅ Cache connected successfully")
    except Exception as e:
        logger.error(f"❌ Error in startup event: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Disconnect from Redis on shutdown."""
    logger.info("=== SHUTDOWN EVENT TRIGGERED ===")
    try:
        await cache.close()
        logger.info("✅ Cache closed successfully")
    except Exception as e:
        logger.error(f"❌ Error in shutdown event: {e}", exc_info=True)


# --- API Endpoints ---


@app.get("/")
def read_root():
    """Root endpoint for API health check."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "message": "Binance Trading Agent API is running.",
    }


@app.get("/api/v1/portfolio/summary")
async def get_portfolio_summary():
    """Get a summary of the portfolio including P&L and value."""
    cache_key = "portfolio:summary"
    logger.info("=== GET /api/v1/portfolio/summary ===")
    try:
        logger.info(f"Attempting to get cached value for key '{cache_key}'...")
        # 1. Check cache first
        cached_stats = await cache.get(cache_key)
        if cached_stats:
            logger.info(f"✅ Cache hit for {cache_key}")
            return {**cached_stats, "source": "cache"}

        logger.info(f"Cache miss for {cache_key}. Fetching from portfolio manager...")
        # 2. If cache miss, fetch from portfolio manager
        stats = portfolio_manager.get_portfolio_stats()
        logger.info(f"Got stats from portfolio manager: {stats}")

        # 3. Store in cache (TTL is 2s by default)
        await cache.set(cache_key, stats)
        logger.info(f"✅ Stored {cache_key} in cache")

        return {**stats, "source": "live"}
    except Exception as e:
        logger.error(f"Error in get_portfolio_summary: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/portfolio/positions")
async def get_all_positions():
    """Get all open positions."""
    try:
        positions = portfolio_manager.get_all_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/portfolio/trade-history")
async def get_trade_history(limit: int = 50):
    """Get recent trade history."""
    try:
        trades = portfolio_manager.get_trade_history(limit=limit)
        return {"trades": trades}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/risk/status")
async def get_risk_status():
    """Get the current status of the risk management agent."""
    cache_key = "risk:status"
    try:
        # 1. Check cache first
        cached_status = await cache.get(cache_key)
        if cached_status:
            return {**cached_status, "source": "cache"}

        # 2. If cache miss, fetch from agent
        status = risk_agent.get_risk_status()

        # 3. Store in cache
        await cache.set(cache_key, status)

        return {**status, "source": "live"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/market/price/{symbol}")
async def get_market_price(symbol: str):
    """Get the latest market price for a given symbol, with caching."""
    symbol_upper = symbol.upper()
    cache_key = f"price:{symbol_upper}"

    try:
        # 1. Check cache first
        cached_price = await cache.get(cache_key)
        if cached_price is not None:
            return {"symbol": symbol_upper, "price": cached_price, "source": "cache"}

        # 2. If cache miss, fetch from market agent
        price = market_agent.get_latest_price(symbol_upper)
        if price is None:
            raise HTTPException(status_code=404, detail="Symbol not found")

        # 3. Store in cache for future requests (TTL is 2s by default)
        await cache.set(cache_key, price)

        return {"symbol": symbol_upper, "price": price, "source": "live"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {e}") from e


@app.get("/api/v1/system/config")
async def get_system_config():
    """Get key configuration parameters."""
    try:
        return {
            "demo_mode": config.demo_mode,
            "binance_testnet": config.binance_testnet,
            "risk_config": config.get_risk_config(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
