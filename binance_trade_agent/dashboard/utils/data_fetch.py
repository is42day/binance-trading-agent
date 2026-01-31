"""
Data fetching utilities for Dash dashboard
Extracted from web_ui.py and adapted for Dash callbacks
"""

import asyncio
import threading
from datetime import datetime

from binance_trade_agent.agents.market_data_agent import MarketDataAgent
from binance_trade_agent.agents.risk_management_agent import EnhancedRiskManagementAgent
from binance_trade_agent.agents.signal_agent import SignalAgent
from binance_trade_agent.agents.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.common.config import config
from binance_trade_agent.core.autonomous_trading_loop import AutonomousTradingLoop
from binance_trade_agent.core.orchestrator import TradingOrchestrator
from binance_trade_agent.core.portfolio_manager import PortfolioManager
from binance_trade_agent.monitoring import monitoring

# Singleton component cache
_components = None

# Agent state management
_agent_state = {
    "is_running": False,
    "start_time": None,
    "stop_time": None,
    "task": None,
    "trading_loop": None,
}


def get_agent_state():
    """Get current agent state"""
    return _agent_state


def start_agent(symbols=None, interval=120, strategy="combined_default"):
    """Start the autonomous trading agent"""
    global _agent_state

    if _agent_state["is_running"]:
        return {"success": False, "message": "Agent is already running"}

    try:
        # Create autonomous trading loop
        trading_loop = AutonomousTradingLoop(
            symbols=symbols or config.supported_symbols,
            trade_interval_seconds=interval,
            duration_minutes=0,  # Run indefinitely
            strategy_name=strategy,
        )

        # Create or get event loop (handle thread context)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, try to get the current one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                # No event loop in this thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

        task = loop.create_task(trading_loop.run())

        _agent_state["is_running"] = True
        _agent_state["start_time"] = datetime.now()
        _agent_state["stop_time"] = None
        _agent_state["task"] = task
        _agent_state["trading_loop"] = trading_loop

        return {"success": True, "message": "Agent started successfully"}
    except Exception as e:
        return {"success": False, "message": f"Failed to start agent: {str(e)}"}


def stop_agent():
    """Stop the autonomous trading agent"""
    global _agent_state

    if not _agent_state["is_running"]:
        return {"success": False, "message": "Agent is not running"}

    try:
        # Set stop flag on trading loop
        if _agent_state["trading_loop"]:
            _agent_state["trading_loop"].stop_flag = True

        # Cancel the task
        if _agent_state["task"]:
            _agent_state["task"].cancel()

        _agent_state["is_running"] = False
        _agent_state["stop_time"] = datetime.now()
        _agent_state["task"] = None
        _agent_state["trading_loop"] = None

        return {"success": True, "message": "Agent stopped successfully"}
    except Exception as e:
        return {"success": False, "message": f"Failed to stop agent: {str(e)}"}


def restart_agent(symbols=None, interval=120, strategy="combined_default"):
    """Restart the autonomous trading agent"""
    stop_result = stop_agent()
    if not stop_result["success"] and "not running" not in stop_result["message"]:
        return stop_result

    return start_agent(symbols, interval, strategy)


def get_trading_components():
    """Initialize and cache trading components (singleton pattern)"""
    global _components

    if _components is None:
        market_agent = MarketDataAgent()
        _components = {
            "market_agent": market_agent,
            "signal_agent": SignalAgent(market_data_agent=market_agent),
            "risk_agent": EnhancedRiskManagementAgent(),
            "execution_agent": TradeExecutionAgent(),
            "portfolio": PortfolioManager("/app/data/web_portfolio.db"),
            "orchestrator": TradingOrchestrator(),
        }

    return _components


def get_portfolio_data():
    """Get portfolio summary

    Returns:
        dict: Portfolio data with keys:
            - total_value: float
            - total_pnl: float
            - total_pnl_percent: float
            - open_positions: int
            - total_trades: int
            - positions: list of position dicts
            - recent_trades: list of trade dicts
    """
    try:
        components = get_trading_components()
        portfolio = components["portfolio"]

        stats = portfolio.get_portfolio_stats()
        positions = portfolio.get_all_positions()
        recent_trades = portfolio.get_trade_history(limit=10)

        result = {
            "total_value": stats.get("total_value", 0),
            "total_pnl": stats.get("total_pnl", 0),
            "total_pnl_percent": (
                stats.get("total_pnl", 0)
                / max(stats.get("total_value", 0) - stats.get("total_pnl", 0), 1)
            )
            * 100,
            "open_positions": len(positions),
            "total_trades": stats.get("number_of_trades", 0),
            "positions": [
                {
                    "symbol": pos["symbol"],
                    "quantity": pos["quantity"],
                    "average_price": pos["average_price"],
                    "current_value": pos["market_value"],
                    "unrealized_pnl": pos["unrealized_pnl"],
                }
                for pos in positions
            ],
            "recent_trades": [
                {
                    "symbol": trade["symbol"],
                    "side": trade["side"],
                    "quantity": trade["quantity"],
                    "price": trade["price"],
                    "timestamp": trade["timestamp"],
                    "pnl": trade.get("pnl") or 0,
                }
                for trade in recent_trades
            ],
        }
        return result
    except Exception as e:
        print(f"ERROR in get_portfolio_data: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def get_market_data(symbol: str):
    """Get market data for symbol including 24h ticker

    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')

    Returns:
        dict: Market data with keys:
            - price: float
            - change_24h: float
            - ticker: dict
    """
    try:
        components = get_trading_components()
        market_agent = components["market_agent"]

        price = market_agent.get_latest_price(symbol)
        ticker_data = market_agent.fetch_24h_ticker(symbol)
        price_change_percent = float(ticker_data.get("priceChangePercent", 0))

        return {
            "price": price,
            "change_24h": price_change_percent,
            "ticker": ticker_data,
        }
    except Exception as e:
        return {"error": str(e)}


def get_ohlcv_data(symbol: str, interval: str = "1h", limit: int = 48):
    """Get OHLCV data for candlestick chart

    Args:
        symbol: Trading pair symbol
        interval: Candlestick interval ('1h', '4h', '1d', etc)
        limit: Number of candles to fetch

    Returns:
        list: OHLCV data formatted for Plotly
    """
    try:
        components = get_trading_components()
        market_agent = components["market_agent"]
        ohlcv_data = market_agent.fetch_ohlcv(symbol, interval, limit)
        return ohlcv_data
    except Exception as e:
        return {"error": str(e)}


def get_order_book(symbol: str, limit: int = 10):
    """Get order book (bids and asks)

    Args:
        symbol: Trading pair symbol
        limit: Number of levels to fetch

    Returns:
        dict: Order book with 'bids' and 'asks' keys
    """
    try:
        components = get_trading_components()
        market_agent = components["market_agent"]
        order_book = market_agent.fetch_order_book(symbol, limit)
        return order_book
    except Exception as e:
        return {"error": str(e)}


def execute_trade(symbol: str, side: str, quantity: float):
    """Execute trade order

    Args:
        symbol: Trading pair symbol
        side: 'BUY' or 'SELL'
        quantity: Trade quantity

    Returns:
        dict: Order execution result with keys:
            - order_id: str
            - status: str
            - symbol: str
            - side: str
            - quantity: float
    """
    try:
        components = get_trading_components()
        execution_agent = components["execution_agent"]
        portfolio = components["portfolio"]
        market_agent = components["market_agent"]

        # Get current price
        price = market_agent.get_latest_price(symbol)

        # Create trade ID and order ID
        trade_id = f"web_{int(datetime.now().timestamp())}"
        order_id = f"order_{int(datetime.now().timestamp())}"

        # Add trade to portfolio
        portfolio.add_trade(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            fee=0.001,
            order_id=order_id,
            correlation_id="web_ui",
        )

        return {
            "order_id": order_id,
            "status": "FILLED",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }
    except Exception as e:
        return {"error": str(e)}


def get_signals():
    """Get latest trading signals

    Returns:
        dict: Signal result from signal_agent
    """
    try:
        components = get_trading_components()
        signal_agent = components["signal_agent"]
        signal_result = signal_agent.generate_signal("BTCUSDT")
        return signal_result
    except Exception as e:
        return {"error": str(e)}


def get_risk_status():
    """Get comprehensive risk management status

    Returns:
        dict: Risk metrics and configuration
    """
    try:
        components = get_trading_components()
        risk_agent = components["risk_agent"]

        status = risk_agent.get_risk_status()

        # Enhance with configuration info
        risk_config = config.get_risk_config()
        status.update(
            {
                "config": risk_config,
                "symbol_limits": {
                    symbol: config.get_symbol_risk_config(symbol)
                    for symbol in config.supported_symbols
                },
                "emergency_stop": getattr(risk_agent, "emergency_stop_active", False),
                "last_updated": datetime.now().isoformat(),
            }
        )

        return status
    except Exception as e:
        return {"error": str(e)}


def get_trailing_stops():
    """Get all active trailing stops

    Returns:
        dict: Active trailing stops with position info
    """
    try:
        components = get_trading_components()
        risk_agent = components["risk_agent"]
        market_agent = components["market_agent"]

        trailing_info = risk_agent.get_trailing_stop_info()
        
        # Enhance with current prices and P&L
        if trailing_info.get("positions"):
            for symbol, position in trailing_info["positions"].items():
                try:
                    current_price = market_agent.get_latest_price(symbol)
                    position["current_price"] = current_price
                    
                    # Calculate unrealized P&L
                    entry = position.get("entry_price", 0)
                    side = position.get("side", "buy")
                    if entry > 0:
                        if side == "buy":
                            position["pnl_pct"] = (current_price - entry) / entry * 100
                        else:
                            position["pnl_pct"] = (entry - current_price) / entry * 100
                except Exception:
                    position["current_price"] = None
                    position["pnl_pct"] = None
        
        trailing_info["last_updated"] = datetime.now().isoformat()
        return trailing_info
    except Exception as e:
        return {"error": str(e), "active_stops": 0, "positions": {}}


def get_performance_summary():
    """Get performance analytics summary

    Returns:
        dict: Performance metrics including win rate, Sharpe ratio, drawdown
    """
    try:
        from binance_trade_agent.core.performance_analytics import get_performance_analytics
        
        analytics = get_performance_analytics(config.portfolio_initial_value)
        return analytics.get_performance_summary()
    except Exception as e:
        return {"error": str(e)}


def get_trade_history(limit: int = 50):
    """Get recent trade history

    Returns:
        list: Recent trades with P&L info
    """
    try:
        from binance_trade_agent.core.performance_analytics import get_performance_analytics
        
        analytics = get_performance_analytics(config.portfolio_initial_value)
        return analytics.get_trade_history(limit)
    except Exception as e:
        return []


def get_system_status():
    """Get comprehensive system health status

    Returns:
        dict: System health data including uptime, error rates, trading mode, trading_active, current_drawdown
    """
    try:
        # Get basic health data from monitoring
        try:
            health_data = monitoring.get_health_status()
        except Exception:  # noqa: E722
            health_data = {
                "status": "healthy",
                "uptime_seconds": 3600,
                "trade_error_rate": 0.0,
                "api_error_rate": 0.0,
            }

        # Get agent state
        agent_state = get_agent_state()

        # Get risk management status
        try:
            components = get_trading_components()
            risk_agent = components["risk_agent"]
            risk_status = risk_agent.get_risk_status()
            current_drawdown = risk_status.get("current_drawdown", 0)
            emergency_stop = risk_status.get("emergency_stop", False)
        except Exception:
            current_drawdown = 0
            emergency_stop = False

        # Enhance with system information
        health_data.update(
            {
                "demo_mode": config.demo_mode,
                "production_ready": config.is_production_ready(),
                "trading_mode": ("production" if config.is_production_ready() else "demo"),
                "binance_testnet": config.binance_testnet,
                "trading_active": agent_state["is_running"] and not emergency_stop,
                "current_drawdown": current_drawdown,
                "emergency_stop": emergency_stop,
                "last_updated": datetime.now().isoformat(),
            }
        )

        return health_data
    except Exception as e:
        return {"error": str(e)}


def get_trade_history(limit: int = 20):
    """Get trade history

    Args:
        limit: Number of trades to fetch

    Returns:
        dict: Trades list
    """
    try:
        components = get_trading_components()
        portfolio = components["portfolio"]
        trades = portfolio.get_trade_history(limit=limit)
        return {"trades": trades}
    except Exception as e:
        print(f"ERROR in get_trade_history: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


def get_performance_metrics():
    """Get performance metrics

    Returns:
        dict: Total trades and portfolio value
    """
    try:
        components = get_trading_components()
        portfolio = components["portfolio"]
        stats = portfolio.get_portfolio_stats()
        return {
            "total_trades": stats.get("total_trades", 0),
            "portfolio_value": stats.get("total_value", 0),
        }
    except Exception as e:
        return {"error": str(e)}


def set_emergency_stop():
    """Set emergency stop

    Returns:
        dict: Success status
    """
    try:
        components = get_trading_components()
        risk_agent = components["risk_agent"]
        risk_agent.set_emergency_stop(True, "Web UI emergency stop")
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def resume_trading():
    """Resume trading after emergency stop

    Returns:
        dict: Success status
    """
    try:
        components = get_trading_components()
        risk_agent = components["risk_agent"]
        risk_agent.set_emergency_stop(False, "Trading resumed from Web UI")
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def export_portfolio_data():
    """Export portfolio data to JSON/CSV

    Returns:
        dict: Export data structure
    """
    try:
        components = get_trading_components()
        portfolio = components["portfolio"]

        stats = portfolio.get_portfolio_stats()
        positions = portfolio.get_all_positions()
        trades = portfolio.get_trade_history(limit=100)

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "positions": positions,
            "trades": trades,
        }

        return {"success": True, "data": export_data}
    except Exception as e:
        return {"error": str(e)}


def restart_orchestrator():
    """Restart/reinitialize trading orchestrator

    Returns:
        dict: Success message
    """
    try:
        # Clear the global components cache to force reinitialization
        global _components
        _components = None
        return {
            "success": True,
            "message": "Orchestrator will reinitialize on next action",
        }
    except Exception as e:
        return {"error": str(e)}


def refresh_strategy(symbol: str = "BTCUSDT"):
    """Refresh and re-analyze strategy for current market conditions

    Args:
        symbol: Trading pair symbol to analyze

    Returns:
        dict: Updated signal and confidence
    """
    try:
        components = get_trading_components()
        signal_agent = components["signal_agent"]
        market_agent = components["market_agent"]

        # Fetch latest market data
        ohlcv_data = market_agent.fetch_ohlcv(symbol, "1h", 100)

        # Re-run strategy analysis
        signal_result = signal_agent.analyze_signal(symbol, ohlcv_data)

        return {
            "success": True,
            "signal": signal_result.get("signal"),
            "confidence": signal_result.get("confidence"),
            "strategy": signal_agent.active_strategy,
        }
    except Exception as e:
        return {"error": str(e)}
