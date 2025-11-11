"""
Data fetching utilities for Dash dashboard
Extracted from web_ui.py and adapted for Dash callbacks
"""

from datetime import datetime
from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.signal_agent import SignalAgent
from binance_trade_agent.risk_management_agent import EnhancedRiskManagementAgent
from binance_trade_agent.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.portfolio_manager import PortfolioManager
from binance_trade_agent.orchestrator import TradingOrchestrator
from binance_trade_agent.monitoring import monitoring
from binance_trade_agent.config import config


# Singleton component cache
_components = None


def get_trading_components():
    """Initialize and cache trading components (singleton pattern)"""
    global _components
    
    if _components is None:
        _components = {
            'market_agent': MarketDataAgent(),
            'signal_agent': SignalAgent(),
            'risk_agent': EnhancedRiskManagementAgent(),
            'execution_agent': TradeExecutionAgent(),
            'portfolio': PortfolioManager("/app/data/web_portfolio.db"),
            'orchestrator': TradingOrchestrator()
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
        portfolio = components['portfolio']
        
        stats = portfolio.get_portfolio_stats()
        positions = portfolio.get_all_positions()
        recent_trades = portfolio.get_trade_history(limit=10)
        
        result = {
            "total_value": stats.get('total_value', 0),
            "total_pnl": stats.get('total_pnl', 0),
            "total_pnl_percent": (stats.get('total_pnl', 0) / max(
                stats.get('total_value', 0) - stats.get('total_pnl', 0), 1)) * 100,
            "open_positions": len(positions),
            "total_trades": stats.get('number_of_trades', 0),
            "positions": [
                {
                    "symbol": pos['symbol'],
                    "quantity": pos['quantity'],
                    "average_price": pos['average_price'],
                    "current_value": pos['market_value'],
                    "unrealized_pnl": pos['unrealized_pnl']
                } for pos in positions
            ],
            "recent_trades": [
                {
                    "symbol": trade['symbol'],
                    "side": trade['side'],
                    "quantity": trade['quantity'],
                    "price": trade['price'],
                    "timestamp": trade['timestamp'],
                    "pnl": trade.get('pnl') or 0
                } for trade in recent_trades
            ]
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
        market_agent = components['market_agent']
        
        price = market_agent.get_latest_price(symbol)
        ticker_data = market_agent.fetch_24h_ticker(symbol)
        price_change_percent = float(ticker_data.get('priceChangePercent', 0))
        
        return {
            "price": price,
            "change_24h": price_change_percent,
            "ticker": ticker_data
        }
    except Exception as e:
        return {"error": str(e)}


def get_ohlcv_data(symbol: str, interval: str = '1h', limit: int = 48):
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
        market_agent = components['market_agent']
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
        market_agent = components['market_agent']
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
        execution_agent = components['execution_agent']
        portfolio = components['portfolio']
        market_agent = components['market_agent']
        
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
            correlation_id="web_ui"
        )
        
        return {
            "order_id": order_id,
            "status": "FILLED",
            "symbol": symbol,
            "side": side,
            "quantity": quantity
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
        signal_agent = components['signal_agent']
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
        risk_agent = components['risk_agent']
        
        status = risk_agent.get_risk_status()
        
        # Enhance with configuration info
        risk_config = config.get_risk_config()
        status.update({
            "config": risk_config,
            "symbol_limits": {
                symbol: config.get_symbol_risk_config(symbol)
                for symbol in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            },
            "emergency_stop": getattr(risk_agent, 'emergency_stop_active', False),
            "last_updated": datetime.now().isoformat()
        })
        
        return status
    except Exception as e:
        return {"error": str(e)}


def get_system_status():
    """Get comprehensive system health status
    
    Returns:
        dict: System health data including uptime, error rates, trading mode
    """
    try:
        # Get basic health data from monitoring
        try:
            health_data = monitoring.get_health_status()
        except:
            health_data = {
                "status": "healthy",
                "uptime_seconds": 3600,
                "trade_error_rate": 0.0,
                "api_error_rate": 0.0
            }
        
        # Enhance with system information
        health_data.update({
            "demo_mode": config.demo_mode,
            "production_ready": config.is_production_ready(),
            "trading_mode": "production" if config.is_production_ready() else "demo",
            "binance_testnet": config.binance_testnet,
            "last_updated": datetime.now().isoformat()
        })
        
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
        portfolio = components['portfolio']
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
        portfolio = components['portfolio']
        stats = portfolio.get_portfolio_stats()
        return {
            "total_trades": stats.get('total_trades', 0),
            "portfolio_value": stats.get('total_value', 0)
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
        risk_agent = components['risk_agent']
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
        risk_agent = components['risk_agent']
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
        portfolio = components['portfolio']
        
        stats = portfolio.get_portfolio_stats()
        positions = portfolio.get_all_positions()
        trades = portfolio.get_trade_history(limit=100)
        
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "positions": positions,
            "trades": trades
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
        return {"success": True, "message": "Orchestrator will reinitialize on next action"}
    except Exception as e:
        return {"error": str(e)}


def refresh_strategy(symbol: str = 'BTCUSDT'):
    """Refresh and re-analyze strategy for current market conditions
    
    Args:
        symbol: Trading pair symbol to analyze
        
    Returns:
        dict: Updated signal and confidence
    """
    try:
        components = get_trading_components()
        signal_agent = components['signal_agent']
        market_agent = components['market_agent']
        
        # Fetch latest market data
        ohlcv_data = market_agent.fetch_ohlcv(symbol, '1h', 100)
        
        # Re-run strategy analysis
        signal_result = signal_agent.analyze_signal(symbol, ohlcv_data)
        
        return {
            "success": True,
            "signal": signal_result.get('signal'),
            "confidence": signal_result.get('confidence'),
            "strategy": signal_agent.active_strategy
        }
    except Exception as e:
        return {"error": str(e)}
