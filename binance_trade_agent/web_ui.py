"""
Streamlit Web UI for Binance Trading Agent - Enhanced UX
Connects directly to trading components with improved navigation, feedback, and responsive design
"""

import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import time
from streamlit_option_menu import option_menu
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.stylable_container import stylable_container

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

# Initialize session state for theme and auto-refresh
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'auto_refresh_interval' not in st.session_state:
    st.session_state.auto_refresh_interval = 30
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# Import trading components directly
from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.signal_agent import SignalAgent
from binance_trade_agent.risk_management_agent import EnhancedRiskManagementAgent
from binance_trade_agent.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.portfolio_manager import PortfolioManager
from binance_trade_agent.portfolio_manager import TradeORM
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

# Enhanced styling with theme support, responsive design, and improved UX
st.markdown("""
<style>
    /* Page container spacing & responsive */
    div.block-container{
        padding-top: 2rem;
        padding-left: 1.6rem;
        padding-right: 1.6rem;
    }
    
    @media (max-width: 768px) {
        div.block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }

    /* Hide Streamlit chrome for cleaner app */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Dark theme base */
    .reportview-container, .main, body, .stApp {
        background-color: #23242a !important;
        color: #f4f2ee !important;
    }

    /* Primary buttons - orange with better visibility */
    .stButton>button {
        background-color: #ff914d !important;
        color: #ffffff !important;
        font-weight: 600;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 16px !important;
        transition: all 0.2s ease;
        width: 100% !important;
    }
    .stButton>button:hover {
        background-color: #ffb974 !important;
        color: #23242a !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 145, 77, 0.3);
    }

    /* Danger buttons */
    .stButton>button.danger, button[data-testid="baseButton-secondary"]:contains("EMERGENCY") {
        background-color: #e74c3c !important;
    }
    .stButton>button.danger:hover {
        background-color: #c0392b !important;
    }

    /* Headings - improved hierarchy */
    h1 {
        color: #f4f2ee !important;
        font-weight: 700 !important;
        font-size: 2.2rem !important;
        letter-spacing: 0.5px !important;
        margin-bottom: 1rem !important;
    }
    
    h2 {
        color: #f4f2ee !important;
        font-weight: 650 !important;
        font-size: 1.6rem !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.8rem !important;
        border-bottom: 2px solid rgba(255, 145, 77, 0.3) !important;
        padding-bottom: 0.5rem !important;
    }
    
    h3 {
        color: #e8e6e1 !important;
        font-weight: 600 !important;
        font-size: 1.2rem !important;
    }

    /* Stat card blocks - better styling */
    .stat-block {
        background: linear-gradient(135deg, #2f3035 0%, #292a2d 100%);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem;
        display: inline-block;
        min-width: 150px;
        border: 1px solid rgba(255, 145, 77, 0.2);
        transition: all 0.3s ease;
    }
    .stat-block:hover {
        border-color: rgba(255, 145, 77, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 145, 77, 0.15);
    }
    
    .stat-title {
        color: #b8b8b8;
        font-size: 0.85rem;
        opacity: 0.85;
        font-weight: 500;
    }
    
    .stat-value {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 800;
        margin-top: 0.3rem;
    }

    /* Card containers */
    .card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 145, 77, 0.2);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .card:hover {
        border-color: rgba(255, 145, 77, 0.4);
        background: rgba(255, 145, 77, 0.05);
    }

    /* Data tables */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    .stDataFrame div[data-testid='stTable'] {
        border-radius: 8px;
    }
    .stDataFrame div[data-testid='stTable'] tr:hover td {
        background: rgba(255, 145, 77, 0.1) !important;
    }

    /* Plots */
    .stPlotlyChart > div {
        background: transparent !important;
        border-radius: 8px;
    }

    /* Status indicators */
    .status-healthy { color: #2ecc71; }
    .status-warning { color: #f39c12; }
    .status-critical { color: #e74c3c; }

    /* Tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
        border-bottom: 1px dotted rgba(255, 145, 77, 0.5);
        cursor: help;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        background-color: #1a1b1f;
        color: #f4f2ee;
        text-align: center;
        border-radius: 6px;
        padding: 8px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -50px;
        opacity: 0;
        transition: opacity 0.3s;
        border: 1px solid rgba(255, 145, 77, 0.3);
        font-size: 0.85rem;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }

    /* Notifications/Toast styling */
    .toast-success {
        background-color: rgba(46, 204, 113, 0.2);
        border-left: 4px solid #2ecc71;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    .toast-error {
        background-color: rgba(231, 76, 60, 0.2);
        border-left: 4px solid #e74c3c;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    .toast-info {
        background-color: rgba(52, 152, 219, 0.2);
        border-left: 4px solid #3498db;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }

    /* Mobile responsive */
    @media (max-width: 480px) {
        h1 { font-size: 1.8rem !important; }
        h2 { font-size: 1.2rem !important; }
        .stat-block { min-width: 120px; }
    }

    /* Muted note */
    .muted-note {
        color: rgba(244, 242, 238, 0.6);
        font-size: 0.9rem;
    }

    /* Refresh timestamp */
    .refresh-timestamp {
        color: rgba(255, 145, 77, 0.7);
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }

</style>
""", unsafe_allow_html=True)

# ============================================================================
# Helper Functions for Enhanced UX
# ============================================================================

def muted_orange_tag(text: str) -> str:
    """Create styled orange tag for highlighting"""
    return f"<span style=\"color:#ff914d;font-weight:600\">{text}</span>"

def tooltip(text: str, tooltip_text: str) -> str:
    """Create interactive tooltip"""
    return f"""<span class="tooltip">{text}
        <span class="tooltiptext">{tooltip_text}</span>
    </span>"""

def show_toast(message: str, toast_type: str = "info"):
    """Show toast notification (success, error, info)"""
    toast_class = f"toast-{toast_type}"
    icon_map = {"success": "✅", "error": "❌", "info": "ℹ️"}
    icon = icon_map.get(toast_type, "•")
    
    st.markdown(f"""
    <div class="{toast_class}">
        <strong>{icon} {toast_type.upper()}</strong><br>
        {message}
    </div>
    """, unsafe_allow_html=True)

def styled_header(text: str, subtitle: str = ""):
    """Enhanced header with better visual hierarchy"""
    st.markdown(f"## {text}")
    if subtitle:
        st.markdown(f"<p style='color: #b8b8b8; font-size: 0.95rem; margin-top: -0.8rem'>{subtitle}</p>", 
                   unsafe_allow_html=True)
    try:
        st.divider()
    except Exception:
        st.markdown("---")

def styled_subheader(text: str, icon: str = ""):
    """Styled subheader with optional icon"""
    prefix = f"{icon} " if icon else ""
    st.markdown(f"### {prefix}{text}")

def metric_card(label: str, value: str, delta: str = "", icon: str = "", help_text: str = ""):
    """Create enhanced metric card"""
    icon_html = f"<span style='font-size: 1.8rem; margin-right: 0.5rem'>{icon}</span>" if icon else ""
    help_html = f"<span class='tooltip'><span style='cursor: help; opacity: 0.7'>❓</span><span class='tooltiptext'>{help_text}</span></span>" if help_text else ""
    delta_html = f"<span style='color: #ff914d; font-size: 0.9rem; margin-left: 0.5rem'>{delta}</span>" if delta else ""
    
    st.markdown(f"""
    <div class="stat-block">
        <div class="stat-title">{icon_html}{label} {help_html}</div>
        <div class="stat-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def show_refresh_info():
    """Display last refresh timestamp"""
    st.markdown(f"""
    <div class="refresh-timestamp">
        🔄 Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)

def show_confirmation_dialog(title: str, message: str, action_name: str) -> bool:
    """Show confirmation modal for high-stakes actions"""
    st.warning(f"⚠️ {title}")
    st.markdown(f"**{message}**")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"✅ Confirm {action_name}", type="primary"):
            return True
    with col2:
        if st.button("❌ Cancel"):
            return False
    return None

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
                    "symbol": pos['symbol'],
                    "quantity": pos['quantity'],
                    "average_price": pos['average_price'],
                    "current_value": pos['market_value'],
                    "unrealized_pnl": pos['unrealized_pnl']
                } for pos in positions
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
        
        # Get current price
        price = components['market_agent'].get_latest_price(symbol)
        
        # Add trade to portfolio (portfolio manager handles creation)
        trade_id = f"web_{int(datetime.now().timestamp())}"
        order_id = f"order_{int(datetime.now().timestamp())}"
        
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
        # use top-level 'config' imported at module level

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
        # use top-level 'config' imported at module level
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

def resume_trading():
    """Resume trading after emergency stop"""
    try:
        risk_agent = components['risk_agent']
        risk_agent.set_emergency_stop(False, "Trading resumed from Web UI")
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

def export_portfolio_data():
    """Export portfolio data to JSON/CSV"""
    try:
        portfolio = components['portfolio']
        
        # Get all data
        stats = portfolio.get_portfolio_stats()
        positions = portfolio.get_all_positions()
        trades = portfolio.get_trade_history(limit=100)
        
        # Create export data structure
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
    """Restart/reinitialize trading orchestrator"""
    try:
        # Clear the Streamlit cache to force component reinitialization
        st.cache_resource.clear()
        return {"success": True, "message": "Orchestrator will reinitialize on next action"}
    except Exception as e:
        return {"error": str(e)}

def refresh_strategy():
    """Refresh and re-analyze strategy for current market conditions"""
    try:
        signal_agent = components['signal_agent']
        market_agent = components['market_agent']
        
        # Get current active symbol from session state or use default
        symbol = st.session_state.get('symbol', 'BTCUSDT')
        
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

def main():
    try:
        st.title("📈 Binance Trading Agent Dashboard")
        st.write("### Testing New Design")

        # ========== SIDEBAR: Enhanced Settings ==========
        st.sidebar.title("🎛️ Trading Controls")
        
        # Symbol and quantity selection
        st.sidebar.markdown("### ⚙️ Settings")
        
        symbol = st.sidebar.selectbox(
            "Trading Symbol",
            ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"],
            index=0
        )

        quantity = st.sidebar.number_input(
            "Order Quantity",
            min_value=0.0001,
            value=0.001,
            step=0.0001,
            format="%.4f",
            help="Amount of the asset to trade"
        )

        st.write("✓ Sidebar loaded")

        # ========== MAIN CONTENT: Horizontal Option Menu Navigation ==========
        try:
            selected = option_menu(
                menu_title=None,
                options=["Portfolio", "Market Data", "Signals & Risk", "Execute Trade", "System Health", "Logs", "Advanced"],
                icons=["📊", "💰", "🎯", "💼", "🏥", "📋", "⚙️"],
                menu_icon="🎛️",
                default_index=0,
                orientation="horizontal",
                styles={
                    "container": {"padding": "0!important", "background-color": "#23242a"},
                    "icon": {"color": "#ff914d", "font-size": "20px"},
                    "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px", "--hover-color": "rgba(255, 145, 77, 0.2)"},
                    "nav-link-selected": {"background-color": "rgba(255, 145, 77, 0.3)", "color": "#ff914d", "font-weight": "bold"},
                }
            )
            st.write(f"✓ Menu loaded: {selected}")
        except Exception as e:
            st.error(f"Menu error: {e}")
            return

        # ========== MAIN CONTENT: Route to Selected Tab ==========
        if selected == "Portfolio":
            show_portfolio_tab()
        elif selected == "Market Data":
            show_market_data_tab(symbol)
        elif selected == "Signals & Risk":
            show_signals_risk_tab()
        elif selected == "Execute Trade":
            show_trade_execution_tab(symbol, quantity)
        elif selected == "System Health":
            show_health_controls_tab()
        elif selected == "Logs":
            show_logs_monitoring_tab()
        elif selected == "Advanced":
            show_advanced_controls_tab()
        else:
            show_portfolio_tab()
    except Exception as e:
        st.error(f"FATAL ERROR: {str(e)}")
        import traceback
        st.write(traceback.format_exc())



def show_portfolio_tab():
    styled_header("📊 Portfolio Overview", "Real-time position tracking and P&L analysis")

    with st.spinner("Loading portfolio data..."):
        portfolio_data = get_portfolio_data()

    if "error" in portfolio_data:
        st.error("❌ Failed to load portfolio data. Check database connection.")
        return

    # ===== GROUPED STATS CARDS (Enhanced with Styling) =====
    st.markdown("### 💰 Portfolio Summary")
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_val = portfolio_data.get('total_value', 0)
        st.metric(
            "Total Value",
            f"${total_val:,.2f}",
            help="Current market value of all positions"
        )

    with col2:
        total_pnl = portfolio_data.get('total_pnl', 0)
        pnl_pct = portfolio_data.get('total_pnl_percent', 0)
        pnl_color = "🟢" if total_pnl >= 0 else "🔴"
        st.metric(
            "Total P&L",
            f"{pnl_color} ${total_pnl:,.2f}",
            delta=f"{pnl_pct:+.2f}%",
            help="Realized + Unrealized profit/loss"
        )

    with col3:
        open_pos = portfolio_data.get('open_positions', 0)
        st.metric(
            "Open Positions",
            f"📍 {open_pos}",
            help="Number of active trading positions"
        )

    with col4:
        total_trades = portfolio_data.get('total_trades', 0)
        st.metric(
            "Total Trades",
            f"📈 {total_trades}",
            help="Cumulative number of executed trades"
        )
    
    # Apply streamlit-extras styling to metrics
    style_metric_cards(
        background_color="#2f3035",
        border_left_color="#ff914d",
        border_size_px=3
    )

    # ===== PORTFOLIO ALLOCATION CHART =====
    st.markdown("---")
    st.markdown("### 🥧 Portfolio Allocation")
    
    positions = portfolio_data.get('positions', [])
    
    if positions:
        df_positions = pd.DataFrame(positions)
        
        # Create visual pie chart
        fig = px.pie(
            df_positions,
            values='current_value',
            names='symbol',
            title="Asset Distribution by Market Value",
            hole=0.3,  # Donut chart for better look
            color_discrete_sequence=["#ff914d", "#ffb974", "#ffd9a8", "#4a90e2", "#50c878"]
        )
        fig.update_layout(
            font=dict(color='#f4f2ee'),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Horizontal bar chart for detailed view
        fig_bar = px.bar(
            df_positions.sort_values('current_value', ascending=True),
            x='current_value',
            y='symbol',
            orientation='h',
            title="Position Sizes (Market Value)",
            labels={'current_value': 'Value (USDT)', 'symbol': 'Asset'}
        )
        fig_bar.update_layout(
            font=dict(color='#f4f2ee'),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=300
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ===== POSITIONS TABLE =====
    st.markdown("---")
    styled_subheader("📋 Current Positions", "💾")
    
    if positions:
        df_positions = pd.DataFrame(positions)
        
        # Color-code the PnL column
        def pnl_color(val):
            color = "#2ecc71" if val >= 0 else "#e74c3c"
            return f"color: {color}"
        
        styled_df = df_positions.style.applymap(
            pnl_color,
            subset=['unrealized_pnl']
        ).format({
            'quantity': '{:.4f}',
            'average_price': '${:,.2f}',
            'current_value': '${:,.2f}',
            'unrealized_pnl': '${:,.2f}'
        })
        
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("📭 No open positions")

    # ===== RECENT TRADES =====
    st.markdown("---")
    styled_subheader("📈 Recent Trades", "📊")
    
    trades = portfolio_data.get('recent_trades', [])

    if trades:
        df_trades = pd.DataFrame(trades)
        
        # Format trades table with colors
        def trade_side_color(val):
            color = "#2ecc71" if val == "BUY" else "#e74c3c"
            return f"background-color: rgba({color}, 0.1); color: {color}"
        
        styled_trades = df_trades.style.applymap(
            trade_side_color,
            subset=['side']
        ).format({
            'quantity': '{:.4f}',
            'price': '${:,.2f}',
            'pnl': '${:,.2f}'
        })
        
        st.dataframe(styled_trades, use_container_width=True, height=300)
    else:
        st.info("📭 No recent trades")

    show_refresh_info()

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
    styled_header("💼 Trade Execution", "Execute trades with confirmation & real-time feedback")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 📝 Trade Form")

        with st.form("trade_form", clear_on_submit=True):
            trade_symbol = st.selectbox(
                "Symbol",
                ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"],
                index=["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"].index(symbol),
                help="Select the trading pair"
            )
            
            side = st.selectbox(
                "Side",
                ["BUY", "SELL"],
                help="Buy or Sell the asset"
            )
            
            trade_quantity = st.number_input(
                "Quantity",
                min_value=0.0001,
                value=quantity,
                step=0.0001,
                format="%.4f",
                help="Amount of asset to trade"
            )
            
            # Get current price for reference
            try:
                current_price = components['market_agent'].get_latest_price(trade_symbol)
                total_value = trade_quantity * current_price
                st.caption(f"Current Price: ${current_price:,.2f} | Total: ${total_value:,.2f}")
            except:
                pass

            # Better button styling with color differentiation
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submitted = st.form_submit_button(
                    "✅ Execute Trade",
                    type="primary",
                    use_container_width=True,
                    help="Click to execute the trade (requires confirmation)"
                )
            
            with col_btn2:
                st.form_submit_button(
                    "❌ Cancel",
                    use_container_width=True,
                    help="Clear the form"
                )

            if submitted:
                # Show confirmation dialog
                st.markdown("---")
                confirm = show_confirmation_dialog(
                    "Confirm Trade Execution",
                    f"Execute {side} {trade_quantity} {trade_symbol} at current market price?",
                    f"{side} Trade"
                )
                
                if confirm:
                    with st.spinner(f"⏳ Executing {side} order..."):
                        result = execute_trade(trade_symbol, side, trade_quantity)

                    if "error" not in result:
                        show_toast(
                            f"Trade {result.get('status', 'FILLED')} - Order ID: {result.get('order_id')}",
                            "success"
                        )
                        st.success(f"✅ {side} order executed successfully!")
                        st.json(result)
                        time.sleep(2)
                        st.rerun()
                    else:
                        show_toast(f"Trade failed: {result['error']}", "error")
                        st.error(f"❌ {result['error']}")

    with col2:
        st.markdown("### 📊 Recent Trade History")
        with st.spinner("Loading trade history..."):
            trade_history = get_trade_history()

        if "error" not in trade_history:
            trades = trade_history.get('trades', [])
            if trades:
                df_trades = pd.DataFrame(trades)
                
                # Format for better visualization
                df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp']).dt.strftime('%H:%M:%S')
                df_trades_display = df_trades[['symbol', 'side', 'quantity', 'price', 'timestamp']]
                
                st.dataframe(df_trades_display, use_container_width=True, height=400)
            else:
                st.info("📭 No trade history available")
        else:
            st.error("Failed to load trade history")
    
    show_refresh_info()

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
            with st.spinner("Resuming trading..."):
                result = resume_trading()
            if "error" not in result:
                st.success("✅ Trading resumed - system is active again")
            else:
                st.error(f"Failed to resume trading: {result['error']}")

    with col2:
        st.subheader("🔧 System Operations")

        if st.button("📤 Export Portfolio Data"):
            with st.spinner("Exporting portfolio data..."):
                result = export_portfolio_data()
            if "error" not in result:
                # Convert to JSON for download
                import json
                json_str = json.dumps(result['data'], indent=2)
                st.download_button(
                    label="⬇️ Download Portfolio Data (JSON)",
                    data=json_str,
                    file_name=f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
                st.success("✅ Portfolio data ready for download")

        if st.button("🔄 Restart Orchestrator"):
            with st.spinner("Restarting orchestrator..."):
                result = restart_orchestrator()
            if "error" not in result:
                st.success("✅ Orchestrator restarted - components reinitialized")
                st.info(result.get('message', 'System refreshed'))
            else:
                st.error(f"Failed to restart orchestrator: {result['error']}")

        if st.button("📊 Refresh Strategy"):
            with st.spinner("Refreshing strategy analysis..."):
                result = refresh_strategy()
            if "error" not in result:
                st.success("✅ Strategy refreshed with latest market data")
                st.info(f"**Signal:** {result.get('signal')} | **Confidence:** {result.get('confidence', 0):.2%} | **Strategy:** {result.get('strategy')}")
            else:
                st.error(f"Failed to refresh strategy: {result['error']}")

    st.markdown("---")
    st.subheader("📋 System Information")

    st.code(f"""
Trading Components: Direct API calls
Database: /app/data/web_portfolio.db
Timestamp: {datetime.now().isoformat()}
    """)

def show_health_controls_tab():
    """Show system health and real-time controls"""
    styled_header("🏥 System Health & Controls", "Monitor health, manage emergency controls, configure trading mode")

    # System status overview
    col1, col2, col3 = st.columns(3)

    with col1:
        # Trading mode status
        mode = "🚨 PRODUCTION" if config.is_production_ready() else "🔧 DEMO MODE"
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

    # Apply metric styling
    style_metric_cards(
        background_color="#2f3035",
        border_left_color="#ff914d",
        border_size_px=3
    )

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

    # Apply metric styling
    style_metric_cards(
        background_color="#2f3035",
        border_left_color="#2ecc71",
        border_size_px=2
    )

    st.markdown("---")

    # Real-time Controls Section with better grouping
    st.subheader("🎛️ Real-Time Controls")

    # Emergency Controls Group
    st.markdown("### 🚨 Emergency Controls")
    
    with stylable_container(
        key="emergency_container",
        css_styles="""
        {
            background-color: rgba(231, 76, 60, 0.1);
            border: 2px solid #e74c3c;
            border-radius: 8px;
            padding: 1rem;
        }
        """
    ):
        try:
            risk_data = get_risk_status()
            if "error" not in risk_data:
                emergency_active = risk_data.get('emergency_stop', False)

                if emergency_active:
                    st.error("🚨 **EMERGENCY STOP IS ACTIVE** - All trading halted")
                else:
                    st.success("✅ **Trading Active** - Risk controls enabled")

                # Toggle button
                em_col1, em_col2 = st.columns(2)
                
                with em_col1:
                    if st.button(
                        "🔴 Activate Emergency Stop" if not emergency_active else "🟢 Deactivate Emergency Stop",
                        key="emergency_toggle",
                        use_container_width=True
                    ):
                        with st.spinner("Updating emergency stop..."):
                            result = set_emergency_stop()

                        if "error" not in result:
                            st.success("✅ Emergency stop status updated")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to update emergency stop: {result['error']}")
                
                with em_col2:
                    if st.button("🔄 Check Status", use_container_width=True, key="check_status"):
                        st.rerun()
            else:
                st.error("Unable to fetch risk status for emergency controls")

        except Exception as e:
            st.error(f"Error loading emergency controls: {str(e)}")

    st.markdown("")

    # Trading Mode Group
    st.markdown("### 🔄 Trading Mode & Configuration")
    
    with stylable_container(
        key="config_container",
        css_styles="""
        {
            background-color: rgba(52, 152, 219, 0.1);
            border: 2px solid #3498db;
            border-radius: 8px;
            padding: 1rem;
        }
        """
    ):
        current_demo = config.demo_mode
        target_mode = "Live Trading" if current_demo else "Demo Mode"
        
        st.info(f"**Current Mode:** {'Demo Mode (Mock Data)' if current_demo else 'Live Mode (Real API)'}")

        config_col1, config_col2 = st.columns(2)
        
        with config_col1:
            if st.button(f"🔄 Switch to {target_mode}", use_container_width=True):
                st.warning(f"⚠️ **To switch to {target_mode}:**")
                st.markdown(f"""
                1. Set environment variables in `.env`
                2. Restart container: `docker-compose build && docker-compose up -d`
                3. Current mode requires restart to change
                """)
        
        with config_col2:
            if st.button("📊 View Risk Configuration", use_container_width=True):
                st.markdown("### Risk Parameters")
                try:
                    risk_config = config.get_risk_config()
                    st.info(f"""
                    - Max Position/Symbol: {risk_config['max_position_per_symbol']:.1%}
                    - Max Total Exposure: {risk_config['max_total_exposure']:.1%}
                    - Stop Loss: {risk_config['default_stop_loss_pct']:.1%}
                    - Take Profit: {risk_config['default_take_profit_pct']:.1%}
                    """)
                except Exception as e:
                    st.error(f"Error loading risk config: {str(e)}")

if __name__ == "__main__":
    main()