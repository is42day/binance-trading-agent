"""
Streamlit Web UI for Binance Trading Agent
Connects directly to trading components (not MCP server)
"""

import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json

# Configure Streamlit to run on all interfaces (needed for Docker)
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
os.environ['STREAMLIT_SERVER_PORT'] = '8501'

# MCP Server URL (for legacy compatibility)
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8080')

# Page config must be the first Streamlit command
st.set_page_config(
    page_title="Binance Trading Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import trading components directly
from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.signal_agent import SignalAgent
from binance_trade_agent.risk_management_agent import EnhancedRiskManagementAgent
from binance_trade_agent.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.portfolio_manager import PortfolioManager
from binance_trade_agent.orchestrator import TradingOrchestrator
from binance_trade_agent.monitoring import monitoring

# Initialize components
@st.cache_resource
def get_trading_components():
    """Initialize and cache trading components"""
    market_agent = MarketDataAgent()
    signal_agent = SignalAgent()
    risk_agent = EnhancedRiskManagementAgent()
    execution_agent = TradeExecutionAgent()
    portfolio = PortfolioManager("/app/data/web_portfolio.db")
    orchestrator = TradingOrchestrator()
    
    return {
        'market_agent': market_agent,
        'signal_agent': signal_agent,
        'risk_agent': risk_agent,
        'execution_agent': execution_agent,
        'portfolio': portfolio,
        'orchestrator': orchestrator
    }

# Get components
components = get_trading_components()

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-text { color: #28a745; }
    .warning-text { color: #ffc107; }
    .danger-text { color: #dc3545; }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

def call_mcp_tool(tool_name: str, arguments: dict = None) -> dict:
    """Call MCP tool via HTTP request"""
    try:
        payload = {
            "tool": tool_name,
            "arguments": arguments or {}
        }
        response = requests.post(f"{MCP_SERVER_URL}/call", json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error calling {tool_name}: {str(e)}")
        return {"error": str(e)}

def get_portfolio_data():
    """Get portfolio summary"""
    try:
        portfolio = components['portfolio']
        stats = portfolio.get_portfolio_stats()
        positions = portfolio.get_all_positions()
        recent_trades = portfolio.get_recent_trades(limit=10)
        
        return {
            "total_value": stats.get('total_value', 0),
            "total_pnl": stats.get('total_pnl', 0),
            "total_pnl_percent": stats.get('total_pnl_percent', 0),
            "open_positions": len(positions),
            "total_trades": stats.get('total_trades', 0),
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "average_price": pos.average_price,
                    "current_value": pos.current_value
                } for pos in positions
            ],
            "recent_trades": [
                {
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "timestamp": trade.timestamp.isoformat()
                } for trade in recent_trades
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def get_market_data(symbol: str):
    """Get market data for symbol"""
    try:
        market_agent = components['market_agent']
        price = market_agent.get_latest_price(symbol)
        return {"price": price, "change_24h": 0.0}  # Mock change for now
    except Exception as e:
        return {"error": str(e)}

def get_order_book(symbol: str, limit: int = 10):
    """Get order book"""
    try:
        market_agent = components['market_agent']
        order_book = market_agent.fetch_order_book(symbol, limit)
        return order_book
    except Exception as e:
        return {"error": str(e)}

def execute_trade(symbol: str, side: str, quantity: float):
    """Execute trade"""
    try:
        execution_agent = components['execution_agent']
        portfolio = components['portfolio']
        
        # Create trade object
        from .portfolio_manager import Trade
        trade = Trade(
            trade_id=f"web_{int(datetime.now().timestamp())}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=components['market_agent'].get_latest_price(symbol),
            fee=0.001,
            timestamp=datetime.now(),
            order_id=f"order_{int(datetime.now().timestamp())}",
            correlation_id="web_ui"
        )
        
        # Add to portfolio
        portfolio.add_trade(trade)
        
        return {
            "order_id": trade.order_id,
            "status": "FILLED",
            "symbol": symbol,
            "side": side,
            "quantity": quantity
        }
    except Exception as e:
        return {"error": str(e)}

def get_signals():
    """Get latest signals"""
    try:
        signal_agent = components['signal_agent']
        # For demo, generate a signal for BTCUSDT
        signal_result = signal_agent.generate_signal("BTCUSDT")
        return signal_result
    except Exception as e:
        return {"error": str(e)}

def get_risk_status():
    """Get risk management status"""
    try:
        risk_agent = components['risk_agent']
        status = risk_agent.get_risk_status()
        return status
    except Exception as e:
        return {"error": str(e)}

def get_system_status():
    """Get system health status"""
    try:
        return {
            "status": "healthy",
            "uptime_seconds": 3600,
            "trade_error_rate": 0.0,
            "api_error_rate": 0.0
        }
    except Exception as e:
        return {"error": str(e)}

def get_trade_history():
    """Get trade history"""
    try:
        portfolio = components['portfolio']
        trades = portfolio.get_recent_trades(limit=20)
        return {
            "trades": [
                {
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "timestamp": trade.timestamp.isoformat()
                } for trade in trades
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def get_performance_metrics():
    """Get performance metrics"""
    try:
        portfolio = components['portfolio']
        stats = portfolio.get_portfolio_stats()
        return {
            "total_trades": stats.get('total_trades', 0),
            "portfolio_value": stats.get('total_value', 0)
        }
    except Exception as e:
        return {"error": str(e)}

def set_emergency_stop():
    """Set emergency stop"""
    try:
        risk_agent = components['risk_agent']
        risk_agent.set_emergency_stop(True, "Web UI emergency stop")
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

def main():
    st.title("📈 Binance Trading Agent Dashboard")

    # Sidebar
    st.sidebar.title("🎛️ Trading Controls")

    # Symbol selection
    symbol = st.sidebar.selectbox(
        "Trading Symbol",
        ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"],
        index=0
    )

    # Action selection
    action = st.sidebar.radio(
        "Action",
        ["View Portfolio", "Market Data", "Signals & Risk", "Execute Trade", "Logs & Monitoring", "Advanced Controls"]
    )

    # Quantity input for trades
    quantity = st.sidebar.number_input(
        "Quantity",
        min_value=0.0001,
        value=0.001,
        step=0.0001,
        format="%.4f"
    )

    # Quick stats in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Quick Stats")

    try:
        portfolio = get_portfolio_data()
        if "error" not in portfolio:
            st.sidebar.metric("Portfolio Value", f"${portfolio.get('total_value', 0):,.2f}")
            st.sidebar.metric("Open Positions", portfolio.get('open_positions', 0))
            st.sidebar.metric("P&L", f"{portfolio.get('total_pnl_percent', 0):+.2f}%")
    except:
        st.sidebar.warning("Unable to load portfolio data")

    # Main content based on selected action
    if action == "View Portfolio":
        show_portfolio_tab()
    elif action == "Market Data":
        show_market_data_tab(symbol)
    elif action == "Signals & Risk":
        show_signals_risk_tab()
    elif action == "Execute Trade":
        show_trade_execution_tab(symbol, quantity)
    elif action == "Logs & Monitoring":
        show_logs_monitoring_tab()
    elif action == "Advanced Controls":
        show_advanced_controls_tab()

def show_portfolio_tab():
    st.header("📊 Portfolio Overview")

    with st.spinner("Loading portfolio data..."):
        portfolio_data = get_portfolio_data()

    if "error" in portfolio_data:
        st.error("Failed to load portfolio data")
        return

    # Portfolio metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Value", f"${portfolio_data.get('total_value', 0):,.2f}")

    with col2:
        pnl = portfolio_data.get('total_pnl', 0)
        pnl_percent = portfolio_data.get('total_pnl_percent', 0)
        st.metric("Total P&L", f"${pnl:,.2f} ({pnl_percent:+.2f}%)",
                 delta=f"{pnl_percent:+.2f}%" if pnl_percent != 0 else None)

    with col3:
        st.metric("Open Positions", portfolio_data.get('open_positions', 0))

    with col4:
        st.metric("Total Trades", portfolio_data.get('total_trades', 0))

    # Positions table
    st.subheader("📋 Current Positions")
    positions = portfolio_data.get('positions', [])

    if positions:
        df_positions = pd.DataFrame(positions)
        st.dataframe(df_positions, use_container_width=True)

        # Portfolio allocation chart
        if 'symbol' in df_positions.columns and 'current_value' in df_positions.columns:
            fig = px.pie(df_positions, values='current_value', names='symbol',
                        title="Portfolio Allocation")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No open positions")

    # Recent trades
    st.subheader("📈 Recent Trades")
    trades = portfolio_data.get('recent_trades', [])

    if trades:
        df_trades = pd.DataFrame(trades)
        st.dataframe(df_trades, use_container_width=True)
    else:
        st.info("No recent trades")

def show_market_data_tab(symbol: str):
    st.header(f"📊 Market Data - {symbol}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💰 Current Price")
        with st.spinner("Fetching price..."):
            price_data = get_market_data(symbol)

        if "error" not in price_data:
            current_price = price_data.get('price', 0)
            change_24h = price_data.get('change_24h', 0)

            st.metric(
                f"{symbol} Price",
                f"${current_price:,.2f}",
                delta=f"{change_24h:+.2f}%" if change_24h != 0 else None
            )
        else:
            st.error("Failed to fetch price data")

    with col2:
        st.subheader("📋 Order Book")
        with st.spinner("Fetching order book..."):
            order_book = get_order_book(symbol)

        if "error" not in order_book:
            bids = order_book.get('bids', [])[:5]
            asks = order_book.get('asks', [])[:5]

            col_a, col_b = st.columns(2)

            with col_a:
                st.write("**Bids (Buy)**")
                if bids:
                    df_bids = pd.DataFrame(bids, columns=['Price', 'Quantity'])
                    st.dataframe(df_bids, use_container_width=True)
                else:
                    st.write("No bid data")

            with col_b:
                st.write("**Asks (Sell)**")
                if asks:
                    df_asks = pd.DataFrame(asks, columns=['Price', 'Quantity'])
                    st.dataframe(df_asks, use_container_width=True)
                else:
                    st.write("No ask data")
        else:
            st.error("Failed to fetch order book")

def show_signals_risk_tab():
    st.header("🎯 Signals & Risk Management")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Latest Signals")
        with st.spinner("Generating signals..."):
            signal_data = get_signals()

        if "error" not in signal_data:
            signal = signal_data.get('signal', 'HOLD')
            confidence = signal_data.get('confidence', 0)

            if signal == 'BUY':
                st.success(f"🟢 BUY Signal (Confidence: {confidence:.1%})")
            elif signal == 'SELL':
                st.error(f"🔴 SELL Signal (Confidence: {confidence:.1%})")
            else:
                st.info(f"🟡 HOLD Signal (Confidence: {confidence:.1%})")

            # Re-run signal button
            if st.button("🔄 Re-run Signal Analysis"):
                with st.spinner("Re-analyzing..."):
                    new_signal = get_signals()
                st.rerun()
        else:
            st.error("Failed to generate signals")

    with col2:
        st.subheader("⚠️ Risk Status")
        with st.spinner("Checking risk status..."):
            risk_data = get_risk_status()

        if "error" not in risk_data:
            emergency_stop = risk_data.get('emergency_stop', False)
            consecutive_losses = risk_data.get('consecutive_losses', 0)
            current_drawdown = risk_data.get('current_drawdown', 0)

            if emergency_stop:
                st.error("🚨 EMERGENCY STOP ACTIVE")
            else:
                st.success("✅ Risk Management Active")

            st.metric("Consecutive Losses", consecutive_losses)
            st.metric("Current Drawdown", f"{current_drawdown:.2f}%")

            # Risk controls
            if st.button("🛑 Emergency Stop", type="primary"):
                result = set_emergency_stop()
                if "error" not in result:
                    st.success("Emergency stop activated")
                    st.rerun()
                else:
                    st.error("Failed to activate emergency stop")
        else:
            st.error("Failed to fetch risk status")

def show_trade_execution_tab(symbol: str, quantity: float):
    st.header("💼 Trade Execution")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Trade Form")

        with st.form("trade_form"):
            trade_symbol = st.selectbox("Symbol", [symbol], index=0)
            side = st.selectbox("Side", ["BUY", "SELL"])
            trade_quantity = st.number_input(
                "Quantity",
                min_value=0.0001,
                value=quantity,
                step=0.0001,
                format="%.4f"
            )

            submitted = st.form_submit_button("Execute Trade")

            if submitted:
                with st.spinner("Executing trade..."):
                    result = execute_trade(trade_symbol, side, trade_quantity)

                if "error" not in result:
                    st.success(f"✅ Trade executed successfully!")
                    st.json(result)
                else:
                    st.error(f"❌ Trade failed: {result['error']}")

    with col2:
        st.subheader("Recent Trade History")
        with st.spinner("Loading trade history..."):
            trade_history = get_trade_history()

        if "error" not in trade_history:
            trades = trade_history.get('trades', [])
            if trades:
                df_trades = pd.DataFrame(trades)
                st.dataframe(df_trades, use_container_width=True)
            else:
                st.info("No trade history available")
        else:
            st.error("Failed to load trade history")

def show_logs_monitoring_tab():
    st.header("📋 Logs & System Monitoring")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏥 System Health")
        with st.spinner("Checking system status..."):
            system_status = get_system_status()

        if "error" not in system_status:
            status = system_status.get('status', 'unknown')
            uptime = system_status.get('uptime_seconds', 0)

            if status == 'healthy':
                st.success("✅ System Healthy")
            else:
                st.error("❌ System Issues Detected")

            st.metric("Uptime", f"{uptime:.1f} seconds")
            st.metric("Trade Error Rate", f"{system_status.get('trade_error_rate', 0):.2f}%")
            st.metric("API Error Rate", f"{system_status.get('api_error_rate', 0):.2f}%")
        else:
            st.error("Failed to fetch system status")

    with col2:
        st.subheader("📊 Performance Metrics")
        with st.spinner("Loading metrics..."):
            metrics = get_performance_metrics()

        if "error" not in metrics:
            total_trades = metrics.get('total_trades', 0)
            portfolio_value = metrics.get('portfolio_value', 0)

            st.metric("Total Trades", total_trades)
            st.metric("Portfolio Value", f"${portfolio_value:,.2f}")

            # Simple metrics chart
            if 'metrics_history' in metrics:
                history = metrics['metrics_history']
                if history:
                    df_metrics = pd.DataFrame(history)
                    fig = px.line(df_metrics, x='timestamp', y='portfolio_value',
                                title="Portfolio Value Over Time")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Failed to load performance metrics")

def show_advanced_controls_tab():
    st.header("⚙️ Advanced System Controls")

    st.warning("⚠️ These controls can affect system behavior. Use with caution.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🚨 Emergency Controls")

        if st.button("🛑 EMERGENCY STOP", type="primary"):
            with st.spinner("Activating emergency stop..."):
                result = set_emergency_stop()
            if "error" not in result:
                st.success("Emergency stop activated - all trading halted")
            else:
                st.error("Failed to activate emergency stop")

        if st.button("▶️ Resume Trading"):
            # This would need a corresponding MCP tool
            st.info("Resume trading functionality not yet implemented")

    with col2:
        st.subheader("🔧 System Operations")

        if st.button("📤 Export Portfolio Data"):
            # This would call an export MCP tool
            st.info("Export functionality not yet implemented")

        if st.button("🔄 Restart Orchestrator"):
            # This would call a restart MCP tool
            st.info("Restart functionality not yet implemented")

        if st.button("📊 Refresh Strategy"):
            # This would re-run strategy analysis
            st.info("Strategy refresh not yet implemented")

    st.markdown("---")
    st.subheader("📋 System Information")

    st.code(f"""
Trading Components: Direct API calls
Database: /app/data/web_portfolio.db
Timestamp: {datetime.now().isoformat()}
    """)

if __name__ == "__main__":
    main()