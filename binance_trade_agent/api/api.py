"""
FastAPI Data Service for Binance Trading Agent
Exposes portfolio, risk, and market data to the Dash UI
"""

import logging
import os
import traceback
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, inspect

from ..agents.market_data_agent import MarketDataAgent
from ..agents.risk_management_agent import EnhancedRiskManagementAgent
from ..clients.redis_cache import RedisCache
from ..common.config import config
from ..common.logging_config import setup_logging, get_logger, set_call_id, generate_call_id
from ..core.portfolio_manager import PortfolioManager
from ..core.performance_analytics import get_performance_analytics
from ..core import db

# Setup structured logging for this service
setup_logging(
    service_name="api",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    use_json=os.getenv("LOG_FORMAT", "plain").lower() == "json",
)

logger = get_logger(__name__)

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
db_path = os.getenv("DB_PATH", "/app/data/web_portfolio.db")
portfolio_manager = PortfolioManager(db_path=db_path)
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


@app.get("/health")
def health_check():
    """
    Health check endpoint for orchestration and monitoring.
    
    Checks:
    1. Database connectivity (can connect to DB)
    2. Schema presence (trades and positions tables exist)
    3. Basic system readiness
    
    Returns 200 if all checks pass, 503 if any check fails.
    """
    health_status = {
        "status": "unknown",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": "pending",
            "schema": "pending",
        },
    }
    
    try:
        # Check 1: Database connectivity
        try:
            session = db.get_session()
            # Simple connectivity test
            session.execute(text("SELECT 1"))
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["checks"]["database"] = f"unhealthy: {str(e)}"
            raise
        
        # Check 2: Schema presence (verify required tables exist)
        try:
            inspector = inspect(db.get_engine())
            tables = inspector.get_table_names()
            
            required_tables = {"trades", "positions"}
            missing_tables = required_tables - set(tables)
            
            if missing_tables:
                health_status["checks"]["schema"] = f"incomplete: missing tables {missing_tables}"
                raise Exception(f"Schema incomplete: missing tables {missing_tables}")
            
            health_status["checks"]["schema"] = "healthy"
        except Exception as e:
            health_status["checks"]["schema"] = f"unhealthy: {str(e)}"
            raise
        
        # All checks passed
        health_status["status"] = "healthy"
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status["status"] = "unhealthy"
        return health_status


@app.get("/ready")
def readiness_check():
    """
    Readiness probe for Kubernetes/orchestration.
    
    Different from /health - this checks if the service is ready to accept traffic:
    1. Database is connected and has schema
    2. Binance API is accessible (circuit breaker not open)
    3. Cache is available
    
    Returns 200 if ready, 503 if not ready.
    """
    from fastapi.responses import JSONResponse
    
    ready_status = {
        "ready": False,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": "pending",
            "binance_api": "pending",
            "cache": "pending",
        },
    }
    
    all_ready = True
    
    # Check 1: Database
    try:
        session = db.get_session()
        session.execute(text("SELECT 1"))
        ready_status["checks"]["database"] = "ready"
    except Exception as e:
        ready_status["checks"]["database"] = f"not ready: {str(e)}"
        all_ready = False
    
    # Check 2: Binance API circuit breaker status
    try:
        from ..clients.binance_client import BinanceAPIClient
        client = BinanceAPIClient()
        cb_status = client.get_circuit_breaker_status()
        if cb_status["state"] == "open":
            ready_status["checks"]["binance_api"] = "not ready: circuit breaker open"
            all_ready = False
        else:
            ready_status["checks"]["binance_api"] = f"ready ({cb_status['state']})"
    except Exception as e:
        ready_status["checks"]["binance_api"] = f"ready (demo mode)"
    
    # Check 3: Cache availability
    try:
        # Cache has already been connected during startup
        ready_status["checks"]["cache"] = "ready"
    except Exception as e:
        ready_status["checks"]["cache"] = f"not ready: {str(e)}"
        all_ready = False
    
    ready_status["ready"] = all_ready
    
    if all_ready:
        return ready_status
    else:
        return JSONResponse(status_code=503, content=ready_status)


@app.get("/api/v1/system/circuit-breaker")
async def get_circuit_breaker_status():
    """Get circuit breaker status for Binance API calls."""
    try:
        from ..clients.binance_client import BinanceAPIClient
        client = BinanceAPIClient()
        return {
            "binance_api": client.get_circuit_breaker_status(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
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


@app.get("/api/v1/risk/trailing-stops")
async def get_trailing_stops():
    """Get all active trailing stops."""
    try:
        return risk_agent.get_trailing_stop_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/risk/trailing-stops/{symbol}")
async def get_trailing_stop_for_symbol(symbol: str):
    """Get trailing stop info for a specific symbol."""
    try:
        result = risk_agent.get_trailing_stop_info(symbol.upper())
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
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
            "supported_symbols": config.supported_symbols,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/performance/summary")
async def get_performance_summary():
    """Get comprehensive performance analytics summary."""
    try:
        analytics = get_performance_analytics(config.portfolio_initial_value)
        return analytics.get_performance_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/performance/trades")
async def get_trade_history(limit: int = 50):
    """Get recent trade history."""
    try:
        analytics = get_performance_analytics(config.portfolio_initial_value)
        return {
            "trades": analytics.get_trade_history(limit),
            "total_trades": len(analytics.trades),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/performance/by-symbol")
async def get_performance_by_symbol():
    """Get performance breakdown by trading symbol."""
    try:
        analytics = get_performance_analytics(config.portfolio_initial_value)
        return analytics.get_symbol_performance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- Paper Trading Endpoints ---

@app.get("/api/v1/paper-trading/status")
async def get_paper_trading_status():
    """Get paper trading portfolio state and statistics."""
    import json
    from pathlib import Path
    
    paper_dir = Path("data/paper_trading")
    state_file = paper_dir / "portfolio_state.json"
    signal_file = paper_dir / "signal_log.jsonl"
    
    # Count signals first
    signal_count = 0
    last_signal_time = None
    if signal_file.exists():
        try:
            with open(signal_file) as f:
                lines = f.readlines()
                signal_count = len(lines)
                if lines:
                    # Get timestamp from last signal
                    last_signal = json.loads(lines[-1])
                    last_signal_time = last_signal.get("timestamp")
        except:
            pass
    
    # Check portfolio state file
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
            
            saved_at = state.get("saved_at", "")
            try:
                last_update = datetime.fromisoformat(saved_at)
                age_seconds = (datetime.now() - last_update).total_seconds()
                active = age_seconds < 120
            except:
                active = False
                age_seconds = 0
            
            return {
                "active": active,
                "last_update": saved_at,
                "age_seconds": int(age_seconds),
                "portfolio": state.get("portfolio", {}),
                "signals_count": signal_count,
            }
        except Exception as e:
            pass
    
    # No portfolio state, but check if we have recent signals
    if signal_count > 0 and last_signal_time:
        try:
            last_update = datetime.fromisoformat(last_signal_time)
            age_seconds = (datetime.now() - last_update).total_seconds()
            active = age_seconds < 120
            
            return {
                "active": active,
                "last_update": last_signal_time,
                "age_seconds": int(age_seconds),
                "portfolio": {
                    "current_balance": 100.0,
                    "total_pnl": 0.0,
                    "total_pnl_percent": 0.0,
                    "win_rate": 0.0,
                    "total_trades": 0,
                    "max_drawdown": 0.0,
                    "open_positions": 0,
                    "profit_factor": 0.0,
                },
                "signals_count": signal_count,
            }
        except:
            pass
    
    return {
        "active": False,
        "message": "Paper trading not running",
        "portfolio": None,
        "signals_count": signal_count,
    }


@app.get("/api/v1/paper-trading/signals")
async def get_paper_trading_signals(limit: int = 50):
    """Get recent paper trading signals."""
    import json
    from pathlib import Path
    
    signal_file = Path("data/paper_trading/signal_log.jsonl")
    
    if not signal_file.exists():
        return {"signals": [], "total": 0}
    
    try:
        signals = []
        with open(signal_file) as f:
            for line in f:
                if line.strip():
                    signals.append(json.loads(line))
        
        # Return most recent
        return {
            "signals": signals[-limit:][::-1],  # Reverse for newest first
            "total": len(signals),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/paper-trading/trades")
async def get_paper_trading_trades(limit: int = 50):
    """Get paper trading trade history."""
    import json
    from pathlib import Path
    
    trade_file = Path("data/paper_trading/trade_log.jsonl")
    
    if not trade_file.exists():
        return {"trades": [], "total": 0}
    
    try:
        trades = []
        with open(trade_file) as f:
            for line in f:
                if line.strip():
                    trades.append(json.loads(line))
        
        # Return most recent
        return {
            "trades": trades[-limit:][::-1],  # Reverse for newest first
            "total": len(trades),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
