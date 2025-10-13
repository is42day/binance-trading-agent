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
from binance_trade_agent.config import config

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

# Smart-casual dark theme CSS and minor layout tweaks
# Note: primary theme colors are defined in .streamlit/config.toml; this CSS complements them.
st.markdown("""
<style>
    /* Page container spacing */
    div.block-container{padding-top:2rem; padding-left:1.6rem; padding-right:1.6rem;}

    /* Hide Streamlit chrome (menu/footer/header) for a cleaner app */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Body and text colors (reinforce theme) */
    .reportview-container, .main, body, .stApp {
        background-color: #23242a !important;
        color: #f4f2ee !important;
    }

    /* Metrics and cards — minimal, flat look */
    .metric-card {
        background-color: rgba(255,255,255,0.03);
        padding: 0.75rem;
        border-radius: 10px;
        margin: 0.4rem 0;
        box-shadow: none;
        border: 1px solid rgba(255,255,255,0.03);
    }

    /* Muted orange primary buttons */
    .stButton>button {
        background-color: #ff914d !important;
        color: #ffffff !important;
        font-weight: 600;
        border-radius: 8px !important;
        border: none !important;
        padding: 8px 12px !important;
        transition: background-color 0.15s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #ffb974 !important;
        color: #23242a !important;
    }

    /* Secondary small buttons (outline) */
    .stButton>button.secondary {
        background-color: transparent !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        color: #f4f2ee !important;
    }

    /* Headings - left aligned, understated */
    h1, h2, h3 {
        color: #f4f2ee !important;
        font-weight: 600;
        letter-spacing: 0.2px;
    }

    /* Reduce padding around Streamlit components for a tighter layout */
    .stMarkdown, .stText, .stMetric {
        color: #f4f2ee !important;
    }

    /* Tables: give a subtle muted accent on hover rows */
    .stDataFrame div[data-testid='stTable'] tr:hover td { background: rgba(255,145,77,0.03); }

    /* Make plot background transparent so Plotly uses theme */
    .stPlotlyChart > div { background: transparent !important; }

</style>
""", unsafe_allow_html=True)

# Small helper for using the muted orange as inline marker
def muted_orange_tag(text: str) -> str:
        return f"<span style=\"color:#ff914d;font-weight:600\">{text}</span>"

# Small helpers for consistent header styling across tabs
def styled_header(text: str):
    """Left-aligned, understated header with a small divider."""
    # Use markdown headers to keep typography consistent with theme
    st.markdown(f"## {text}", unsafe_allow_html=True)
    try:
        st.divider()
    except Exception:
        # Older Streamlit versions may not have st.divider
        st.markdown("---")


def styled_subheader(text: str):
    """Subtle subheader for sections."""
    st.markdown(f"### {text}", unsafe_allow_html=True)

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
        recent_trades = portfolio.get_trade_history(limit=10)
        
        return {
            "total_value": stats.get('total_value', 0),
            "total_pnl": stats.get('total_pnl', 0),
            "total_pnl_percent": (stats.get('total_pnl', 0) / max(stats.get('total_value', 0) - stats.get('total_pnl', 0), 1)) * 100,
            "open_positions": len(positions),
            "total_trades": stats.get('number_of_trades', 0),
            "positions": [
                {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "average_price": pos.average_price,
                    "current_value": pos.market_value,
                    "unrealized_pnl": pos.unrealized_pnl
                } for pos in positions.values()
            ],
            "recent_trades": [
                {
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "timestamp": trade.timestamp.isoformat(),
                    "pnl": trade.pnl or 0
                } for trade in recent_trades
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def get_market_data(symbol: str):
    """Get market data for symbol including 24h ticker"""
    try:
        market_agent = components['market_agent']
        price = market_agent.get_latest_price(symbol)
        
        # Get 24h ticker data
        ticker_data = market_agent.fetch_24h_ticker(symbol)
        
        # Calculate 24h change percentage
        price_change_percent = float(ticker_data.get('priceChangePercent', 0))
        
        return {
            "price": price,
            "change_24h": price_change_percent,
            "ticker": ticker_data
        }
    except Exception as e:
        return {"error": str(e)}

def get_ohlcv_data(symbol: str, interval: str = '1h', limit: int = 48):
    """Get OHLCV data for candlestick chart"""
    try:
        market_agent = components['market_agent']
        ohlcv_data = market_agent.fetch_ohlcv(symbol, interval, limit)
        return ohlcv_data
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
    """Get comprehensive risk management status"""
    try:
        risk_agent = components['risk_agent']
        from binance_trade_agent.config import config

        # Get basic risk status
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
    """Get comprehensive system health status"""
    try:
        from binance_trade_agent.config import config
        import time

        # Get basic health data from monitoring
        try:
            health_data = monitoring.get_health_status()
        except:
            # Fallback if monitoring not available
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
        ["View Portfolio", "Market Data", "Signals & Risk", "Execute Trade", "Health & Controls", "Logs & Monitoring", "Advanced Controls"]
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
    elif action == "Health & Controls":
        show_health_controls_tab()
    elif action == "Execute Trade":
        show_trade_execution_tab(symbol, quantity)
    elif action == "Health & Controls":
        show_health_controls_tab()
    elif action == "Logs & Monitoring":
        show_logs_monitoring_tab()
    elif action == "Advanced Controls":
        show_advanced_controls_tab()



def show_portfolio_tab():
    styled_header("📊 Portfolio Overview")

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
    styled_header(f"📊 Market Data - {symbol}")

    # Symbol selector for chart
    chart_symbol = st.selectbox(
        "Chart Symbol",
        ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"],
        index=["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"].index(symbol)
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💰 Current Price & 24h Stats")
        with st.spinner("Fetching price data..."):
            price_data = get_market_data(chart_symbol)

        if "error" not in price_data:
            current_price = price_data.get('price', 0)
            change_24h = price_data.get('change_24h', 0)
            ticker = price_data.get('ticker', {})

            # Main price metric
            st.metric(
                f"{chart_symbol} Price",
                f"${current_price:,.2f}",
                delta=f"{change_24h:+.2f}%" if change_24h != 0 else None,
                delta_color="normal"
            )

            # 24h Statistics
            st.markdown("### 📈 24h Statistics")
            stats_col1, stats_col2 = st.columns(2)

            with stats_col1:
                st.metric("24h High", f"${float(ticker.get('highPrice', 0)):,.2f}")
                st.metric("24h Volume", f"{float(ticker.get('volume', 0)):,.0f}")

            with stats_col2:
                st.metric("24h Low", f"${float(ticker.get('lowPrice', 0)):,.2f}")
                st.metric("24h Change", f"${float(ticker.get('priceChange', 0)):+,.2f}")
        else:
            st.error("Failed to fetch price data")

    with col2:
        st.subheader("📋 Order Book")
        with st.spinner("Fetching order book..."):
            order_book = get_order_book(chart_symbol)

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

    # Candlestick Chart Section
    st.markdown("---")
    st.subheader(f"📊 {chart_symbol} Candlestick Chart (48 Hours)")

    # Chart controls
    col_chart1, col_chart2 = st.columns([1, 1])
    with col_chart1:
        interval = st.selectbox("Timeframe", ["5m", "15m", "1h", "4h", "1d"], index=2)
    with col_chart2:
        chart_limit = st.slider("Hours to show", 24, 168, 48, 24)

    with st.spinner("Loading chart data..."):
        ohlcv_data = get_ohlcv_data(chart_symbol, interval, chart_limit)

    if "error" not in ohlcv_data and ohlcv_data:
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Create candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=chart_symbol
        )])

        # Update layout
        fig.update_layout(
            title=f"{chart_symbol} Price Chart ({interval} intervals)",
            xaxis_title="Time",
            yaxis_title="Price (USDT)",
            xaxis_rangeslider_visible=False,
            height=500
        )

        # Add volume bar chart
        fig2 = go.Figure(data=[go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name="Volume",
            marker_color='rgba(0, 100, 255, 0.5)'
        )])

        fig2.update_layout(
            title=f"{chart_symbol} Volume",
            xaxis_title="Time",
            yaxis_title="Volume",
            height=200
        )

        st.plotly_chart(fig, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.warning("Failed to load chart data. Using demo mode?")

    # Technical Indicators Section
    if "error" not in ohlcv_data and ohlcv_data:
        st.markdown("---")
        st.subheader("🎯 Technical Indicators")

        # Calculate simple indicators
        df = pd.DataFrame(ohlcv_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Simple moving averages
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()

        # RSI calculation (simplified)
        def calculate_rsi(prices, period=14):
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))

        df['RSI'] = calculate_rsi(df['close'])

        # Display indicators
        col_ind1, col_ind2, col_ind3 = st.columns(3)

        with col_ind1:
            latest_rsi = df['RSI'].iloc[-1] if not df['RSI'].empty else 50
            st.metric("RSI (14)", f"{latest_rsi:.1f}",
                     delta="Overbought" if latest_rsi > 70 else "Oversold" if latest_rsi < 30 else "Neutral")

        with col_ind2:
            latest_price = df['close'].iloc[-1]
            sma_20 = df['SMA_20'].iloc[-1] if not df['SMA_20'].isna().all() else latest_price
            st.metric("Price vs SMA(20)", f"{latest_price:.2f} vs {sma_20:.2f}",
                     delta="Above" if latest_price > sma_20 else "Below")

        with col_ind3:
            volume = df['volume'].iloc[-1] if not df['volume'].empty else 0
            avg_volume = df['volume'].tail(20).mean() if len(df) >= 20 else volume
            st.metric("Volume", f"{volume:,.0f}",
                     delta="High" if volume > avg_volume * 1.2 else "Normal")

def show_signals_risk_tab():
    styled_header("🎯 Signals & Risk Management")

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
    styled_header("💼 Trade Execution")

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

def show_health_controls_tab():
    styled_header("🏥 System Health & Real-time Controls")

    # System status banner
    from binance_trade_agent.config import config
    if config.demo_mode:
        st.warning("⚠️ **DEMO MODE ACTIVE** - Using mock data. Set BINANCE_API_KEY and BINANCE_API_SECRET for live trading.")
    else:
        st.success("🚀 **LIVE MODE ACTIVE** - Connected to Binance API")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏥 System Health Status")

        # Get comprehensive health data
        with st.spinner("Checking system health..."):
            try:
                # Get portfolio health
                portfolio_data = get_portfolio_data()
                portfolio_healthy = "error" not in portfolio_data

                # Get risk status
                risk_data = get_risk_status()
                risk_healthy = "error" not in risk_data

                # Get system status
                system_status = get_system_status()
                system_healthy = "error" not in system_status

                # Overall health
                overall_healthy = portfolio_healthy and risk_healthy and system_healthy

                if overall_healthy:
                    st.success("✅ **System Status: HEALTHY**")
                else:
                    st.error("❌ **System Status: ISSUES DETECTED**")

                # Detailed metrics
                st.markdown("### 📊 Health Metrics")

                health_col1, health_col2 = st.columns(2)

                with health_col1:
                    if portfolio_healthy:
                        st.metric("Portfolio", "Healthy", "✅")
                    else:
                        st.metric("Portfolio", "Error", "❌")

                    if system_healthy:
                        uptime = system_status.get('uptime_seconds', 0)
                        st.metric("Uptime", f"{uptime:.0f}s", "✅")
                    else:
                        st.metric("Uptime", "Unknown", "❌")

                with health_col2:
                    if risk_healthy:
                        emergency_stop = risk_data.get('emergency_stop', False)
                        st.metric("Risk Engine", "Active" if not emergency_stop else "EMERGENCY", "⚠️" if emergency_stop else "✅")
                    else:
                        st.metric("Risk Engine", "Error", "❌")

                    if system_healthy:
                        api_error_rate = system_status.get('api_error_rate', 0)
                        st.metric("API Errors", f"{api_error_rate:.1f}%", "✅" if api_error_rate < 5 else "⚠️")
                    else:
                        st.metric("API Errors", "Unknown", "❌")

            except Exception as e:
                st.error(f"Failed to load health data: {str(e)}")

    with col2:
        st.subheader("🎛️ Real-time Controls")

        # Emergency Stop Toggle
        st.markdown("### 🚨 Emergency Controls")

        try:
            risk_data = get_risk_status()
            if "error" not in risk_data:
                emergency_active = risk_data.get('emergency_stop', False)

                if emergency_active:
                    st.error("🚨 **EMERGENCY STOP IS ACTIVE** - All trading halted")
                else:
                    st.success("✅ **Trading Active** - Risk controls enabled")

                # Toggle button
                button_text = "🔴 Deactivate Emergency Stop" if emergency_active else "🟡 Activate Emergency Stop"
                button_help = "Immediately halt all trading activity" if not emergency_active else "Resume normal trading operations"

                if st.button(button_text, help=button_help):
                    with st.spinner("Updating emergency stop..."):
                        result = set_emergency_stop()

                    if "error" not in result:
                        st.success("✅ Emergency stop status updated")
                        st.rerun()  # Refresh the page
                    else:
                        st.error(f"❌ Failed to update emergency stop: {result['error']}")
            else:
                st.error("Unable to fetch risk status for emergency controls")

        except Exception as e:
            st.error(f"Error loading emergency controls: {str(e)}")

        st.markdown("---")

        # Trading Mode Toggle
        st.markdown("### 🔄 Trading Mode")

        current_demo = config.demo_mode
        target_mode = "Live Trading" if current_demo else "Demo Mode"
        target_desc = "Connect to real Binance API" if current_demo else "Switch to mock data mode"

        st.info(f"**Current Mode:** {'Demo Mode (Mock Data)' if current_demo else 'Live Mode (Real API)'}")

        if st.button(f"🔄 Switch to {target_mode}", help=target_desc):
            st.warning("⚠️ **Mode switching requires environment variable changes and container restart.**")
            st.markdown(f"""
            **To switch to {target_mode}:**
            1. Set environment variables:
               - `DEMO_MODE={'false' if current_demo else 'true'}`
               {'- `BINANCE_API_KEY=your_key`' if current_demo else ''}
               {'- `BINANCE_API_SECRET=your_secret`' if current_demo else ''}
            2. Restart the container: `make build && make run`
            """)

        # Risk Level Indicator
        st.markdown("---")
        st.markdown("### 📊 Risk Configuration")

        try:
            risk_config = config.get_risk_config()
            st.metric("Max Position/Symbol", f"{risk_config['max_position_per_symbol']:.1%}")
            st.metric("Max Total Exposure", f"{risk_config['max_total_exposure']:.1%}")
            st.metric("Stop Loss Default", f"{risk_config['default_stop_loss_pct']:.1%}")
            st.metric("Take Profit Default", f"{risk_config['default_take_profit_pct']:.1%}")

            if st.button("🔧 Edit Risk Settings", help="Modify risk parameters (requires config change)"):
                st.info("Risk settings are configured via environment variables. Edit your .env file and restart the container.")

        except Exception as e:
            st.error(f"Error loading risk configuration: {str(e)}")

def show_logs_monitoring_tab():
    styled_header("📋 Logs & System Monitoring")

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
    styled_header("⚙️ Advanced System Controls")

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

def show_health_controls_tab():
    """Show system health and real-time controls"""
    styled_header("🏥 System Health & Controls")

    # System status overview
    col1, col2, col3 = st.columns(3)

    with col1:
        # Trading mode status
        from .config import config
        mode = "🚨 PRODUCTION" if config.is_production_ready() else "🔧 DEMO MODE"
        mode_color = "danger" if config.is_production_ready() else "warning"
        st.metric("Trading Mode", mode)

    with col2:
        # API connectivity
        try:
            test_price = components['market_agent'].get_latest_price('BTCUSDT')
            st.metric("API Status", "🟢 Connected", delta="OK")
        except:
            st.metric("API Status", "🔴 Disconnected", delta="ERROR")

    with col3:
        # System uptime (simplified)
        st.metric("System Status", "🟢 Healthy")

    st.markdown("---")

    # Health Metrics Section
    st.subheader("📊 Health Metrics")

    health_col1, health_col2, health_col3, health_col4 = st.columns(4)

    with health_col1:
        # Portfolio health
        try:
            portfolio = get_portfolio_data()
            pnl_pct = portfolio.get('total_pnl_percent', 0)
            st.metric("Portfolio Health",
                     "🟢 Good" if pnl_pct >= -5 else "🟡 Warning" if pnl_pct >= -15 else "🔴 Critical",
                     delta=f"{pnl_pct:+.1f}%")
        except:
            st.metric("Portfolio Health", "🔴 Error")

    with health_col2:
        # Risk status
        try:
            risk_data = get_risk_status()
            emergency = risk_data.get('emergency_stop', False)
            st.metric("Risk Status", "🚨 EMERGENCY STOP" if emergency else "🟢 Normal")
        except:
            st.metric("Risk Status", "🔴 Unknown")

    with health_col3:
        # Signal generation
        try:
            signal = get_signals()
            confidence = signal.get('confidence', 0)
            st.metric("Signal Confidence", f"{confidence:.1%}",
                     delta="High" if confidence > 0.7 else "Medium" if confidence > 0.5 else "Low")
        except:
            st.metric("Signal Confidence", "🔴 Error")

    with health_col4:
        # Active positions
        try:
            portfolio = get_portfolio_data()
            positions = portfolio.get('open_positions', 0)
            st.metric("Active Positions", positions)
        except:
            st.metric("Active Positions", "🔴 Error")

    st.markdown("---")

    # Real-time Controls Section
    st.subheader("🎛️ Real-Time Controls")

    control_col1, control_col2 = st.columns(2)

    with control_col1:
        st.write("**Emergency Controls**")

        # Emergency stop toggle
        emergency_stop = st.checkbox("🚨 Emergency Stop All Trading",
                                   help="Immediately stop all automated trading")

        if emergency_stop:
            if st.button("CONFIRM EMERGENCY STOP", type="primary"):
                try:
                    result = set_emergency_stop()
                    if "error" not in result:
                        st.success("🚨 Emergency stop activated!")
                        st.rerun()
                    else:
                        st.error(f"Failed to activate emergency stop: {result['error']}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

        # Reset emergency stop
        if st.button("🔄 Reset Emergency Stop"):
            try:
                # This would need a reset function in the risk agent
                st.info("Emergency stop reset functionality needs to be implemented")
            except Exception as e:
                st.error(f"Error: {str(e)}")

    with control_col2:
        st.write("**Trading Mode Controls**")

        # Demo mode toggle
        current_demo = config.demo_mode
        demo_mode = st.checkbox("🔧 Enable Demo Mode",
                              value=current_demo,
                              help="Use mock data instead of live trading")

        if demo_mode != current_demo:
            st.warning("⚠️ Mode change requires application restart")
            if st.button("🔄 Restart Application"):
                st.info("Application restart functionality needs to be implemented")

        # Risk level selector
        risk_level = st.selectbox("Risk Level",
                                ["Conservative", "Moderate", "Aggressive"],
                                index=1,
                                help="Adjust risk parameters")

        if risk_level != "Moderate":
            st.info(f"⚠️ {risk_level} risk settings need to be implemented")

    st.markdown("---")

    # System Configuration Display
    st.subheader("⚙️ Current Configuration")

    config_col1, config_col2 = st.columns(2)

    with config_col1:
        st.write("**Risk Parameters**")
        st.code(f"""
Max Position/Symbol: {config.risk_max_position_per_symbol * 100:.0f}%
Max Total Exposure: {config.risk_max_total_exposure * 100:.0f}%
Stop Loss: {config.risk_default_stop_loss_pct * 100:.1f}%
Take Profit: {config.risk_default_take_profit_pct * 100:.1f}%
        """)

    with config_col2:
        st.write("**Signal Parameters**")
        st.code(f"""
RSI Overbought: {config.signal_rsi_overbought}
RSI Oversold: {config.signal_rsi_oversold}
MACD Window: {config.signal_macd_signal_window}
        """)

    # Quick Actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if st.button("🔄 Refresh All Data"):
            st.rerun()

    with action_col2:
        if st.button("📊 Generate New Signals"):
            with st.spinner("Generating signals..."):
                signal = get_signals()
            if "error" not in signal:
                st.success(f"New signal: {signal.get('signal', 'UNKNOWN')} ({signal.get('confidence', 0):.1%})")
            else:
                st.error("Failed to generate signals")

    with action_col3:
        if st.button("📈 Update Portfolio"):
            with st.spinner("Updating portfolio..."):
                portfolio = get_portfolio_data()
            if "error" not in portfolio:
                st.success(f"Portfolio updated: ${portfolio.get('total_value', 0):,.2f}")
            else:
                st.error("Failed to update portfolio")

if __name__ == "__main__":
    main()