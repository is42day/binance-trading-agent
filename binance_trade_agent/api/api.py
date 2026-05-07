"""
FastAPI Data Service for Binance Trading Agent
Exposes portfolio, risk, and market data to the Dash UI
"""

import os
import traceback
from datetime import datetime

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from ..agents.market_data_agent import MarketDataAgent
from ..agents.risk_management_agent import EnhancedRiskManagementAgent
from ..clients.redis_cache import RedisCache
from ..common.config import config
from ..common.logging_config import get_logger, setup_logging
from ..core import db
from ..core.exchange_reconciliation import ExchangeReconciliationService
from ..core.performance_analytics import get_performance_analytics
from ..core.portfolio_manager import PortfolioManager

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


def _configured_cors_origins():
    origins = os.getenv(
        "API_CORS_ORIGINS",
        "http://localhost:8050,http://127.0.0.1:8050",
    )
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


def require_api_token(authorization: str | None = Header(default=None)):
    """
    Optional bearer-token guard.

    Set API_AUTH_TOKEN in production to require Authorization: Bearer <token>.
    Leaving it unset keeps local/test workflows compatible.
    """
    auth_required = os.getenv("API_AUTH_REQUIRED", "false").lower() in {
        "true",
        "1",
        "yes",
        "on",
    }
    expected = os.getenv("API_AUTH_TOKEN")
    if auth_required and not expected:
        logger.error("API_AUTH_REQUIRED is true but API_AUTH_TOKEN is not configured")
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    if not expected:
        return

    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_cors_origins(),
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
        return JSONResponse(status_code=503, content=health_status)


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
        ready_status["checks"]["binance_api"] = "ready (demo mode)"

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


@app.get("/api/v1/system/circuit-breaker", dependencies=[Depends(require_api_token)])
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


@app.get("/api/v1/system/exchange-orders/open", dependencies=[Depends(require_api_token)])
async def get_open_exchange_orders(symbol: str | None = None):
    """Get locally tracked exchange orders that still need reconciliation."""
    try:
        return {"orders": portfolio_manager.get_open_exchange_orders(symbol=symbol)}
    except Exception as e:
        logger.error(f"Error fetching open exchange orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/system/reconcile", dependencies=[Depends(require_api_token)])
async def reconcile_exchange_orders(symbol: str | None = None):
    """Reconcile locally tracked open exchange orders with Binance."""
    try:
        service = ExchangeReconciliationService(
            client=market_agent.client,
            portfolio=portfolio_manager,
        )
        return service.reconcile_open_orders(symbol=symbol)
    except Exception as e:
        logger.error(f"Error reconciling exchange orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/portfolio/summary", dependencies=[Depends(require_api_token)])
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


@app.get("/api/v1/portfolio/positions", dependencies=[Depends(require_api_token)])
async def get_all_positions():
    """Get all open positions."""
    try:
        positions = portfolio_manager.get_all_positions()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/portfolio/trade-history", dependencies=[Depends(require_api_token)])
async def get_trade_history(limit: int = 50):
    """Get recent trade history."""
    try:
        trades = portfolio_manager.get_trade_history(limit=limit)
        return {"trades": trades}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/risk/status", dependencies=[Depends(require_api_token)])
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


@app.get("/api/v1/risk/trailing-stops", dependencies=[Depends(require_api_token)])
async def get_trailing_stops():
    """Get all active trailing stops."""
    try:
        return risk_agent.get_trailing_stop_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/risk/trailing-stops/{symbol}", dependencies=[Depends(require_api_token)])
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


@app.get("/api/v1/market/price/{symbol}", dependencies=[Depends(require_api_token)])
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


@app.get("/api/v1/market/symbol-rules/{symbol}", dependencies=[Depends(require_api_token)])
async def get_market_symbol_rules(symbol: str):
    """Get Binance exchange filters used for order validation."""
    try:
        return market_agent.client.get_symbol_rules(symbol.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {e}") from e


@app.get("/api/v1/market/order-validation", dependencies=[Depends(require_api_token)])
async def validate_market_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
):
    """Validate order parameters against Binance symbol filters before placement."""
    try:
        return market_agent.client.validate_order_params(
            symbol=symbol.upper(),
            side=side.upper(),
            order_type=order_type.upper(),
            quantity=quantity,
            price=price,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {e}") from e


@app.get("/api/v1/market/slippage", dependencies=[Depends(require_api_token)])
async def estimate_market_slippage(
    symbol: str,
    side: str,
    quantity: float,
    limit: int = 50,
):
    """Estimate market-order effective price and slippage from current order book depth."""
    try:
        return market_agent.client.estimate_market_order_slippage(
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=quantity,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API error: {e}") from e


@app.get("/api/v1/system/config", dependencies=[Depends(require_api_token)])
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


@app.get("/api/v1/performance/summary", dependencies=[Depends(require_api_token)])
async def get_performance_summary():
    """Get comprehensive performance analytics summary."""
    try:
        analytics = get_performance_analytics(config.portfolio_initial_value)
        return analytics.get_performance_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/performance/trades", dependencies=[Depends(require_api_token)])
async def get_performance_trade_history(limit: int = 50):
    """Get recent trade history."""
    try:
        analytics = get_performance_analytics(config.portfolio_initial_value)
        return {
            "trades": analytics.get_trade_history(limit),
            "total_trades": len(analytics.trades),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/performance/by-symbol", dependencies=[Depends(require_api_token)])
async def get_performance_by_symbol():
    """Get performance breakdown by trading symbol."""
    try:
        analytics = get_performance_analytics(config.portfolio_initial_value)
        return analytics.get_symbol_performance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- Paper Trading Endpoints ---


@app.get("/api/v1/paper-trading/status", dependencies=[Depends(require_api_token)])
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
        except Exception:
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
            except Exception:
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
        except Exception:
            pass

    return {
        "active": False,
        "message": "Paper trading not running",
        "portfolio": None,
        "signals_count": signal_count,
    }


@app.get("/api/v1/paper-trading/signals", dependencies=[Depends(require_api_token)])
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


@app.get("/api/v1/paper-trading/trades", dependencies=[Depends(require_api_token)])
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
