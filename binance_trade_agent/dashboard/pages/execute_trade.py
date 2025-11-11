"""
Execute Trade Page - Trade form, recent trades, order execution
"""

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL
import traceback
from binance_trade_agent.dashboard.utils.data_fetch import get_trading_components

# Default symbols for trading
DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
ORDER_TYPES = ['LIMIT', 'MARKET']
SIDES = ['BUY', 'SELL']

layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("💼 Execute Trade", style={'marginTop': '2rem', 'marginBottom': '1rem'})
        ])
    ]),
    
    # Order Form Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📝 Trade Order Form", className="bg-dark"),
                dbc.CardBody([
                    # Symbol and Side Selection
                    dbc.Row([
                        dbc.Col([
                            html.Label("Symbol", className="text-secondary font-weight-bold"),
                            dcc.Dropdown(
                                id="trade-symbol-selector",
                                options=[{"label": sym, "value": sym} for sym in DEFAULT_SYMBOLS],
                                value=DEFAULT_SYMBOLS[0],
                                className="form-control",
                                clearable=False
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Side", className="text-secondary font-weight-bold"),
                            dcc.Dropdown(
                                id="trade-side-selector",
                                options=[{"label": side, "value": side} for side in SIDES],
                                value="BUY",
                                className="form-control",
                                clearable=False
                            )
                        ], md=6)
                    ], className="mb-3"),
                    
                    # Order Type and Price
                    dbc.Row([
                        dbc.Col([
                            html.Label("Order Type", className="text-secondary font-weight-bold"),
                            dcc.Dropdown(
                                id="trade-order-type",
                                options=[{"label": ot, "value": ot} for ot in ORDER_TYPES],
                                value="LIMIT",
                                className="form-control",
                                clearable=False
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Price (USDT)", className="text-secondary font-weight-bold"),
                            dbc.Input(
                                id="trade-price-input",
                                type="number",
                                placeholder="Enter price",
                                className="form-control",
                                step=0.01,
                                min=0
                            )
                        ], md=6)
                    ], className="mb-3"),
                    
                    # Quantity
                    dbc.Row([
                        dbc.Col([
                            html.Label("Quantity", className="text-secondary font-weight-bold"),
                            dbc.Input(
                                id="trade-quantity-input",
                                type="number",
                                placeholder="Enter quantity",
                                className="form-control",
                                step=0.001,
                                min=0
                            )
                        ], md=12)
                    ], className="mb-3"),
                    
                    # Alerts
                    html.Div(id="trade-alert", style={"marginBottom": "1rem"}),
                    
                    # Buttons
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "🚀 Place Order",
                                id="trade-submit-btn",
                                color="primary",
                                className="btn-primary",
                                style={"width": "100%", "minHeight": "44px"}
                            )
                        ], md=6),
                        dbc.Col([
                            dbc.Button(
                                "🔄 Reset",
                                id="trade-reset-btn",
                                color="secondary",
                                style={"width": "100%", "minHeight": "44px"}
                            )
                        ], md=6)
                    ])
                ])
            ], className="mb-4")
        ], md=6),
        
        # Current Market Info
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 Current Market Info", className="bg-dark"),
                dbc.CardBody([
                    html.Div(id="trade-market-info", children=[
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.Div("Current Price", className="metric-label"),
                                    html.Div("$0.00", className="metric-value"),
                                ], className="metric-card mb-3")
                            ], width=12),
                            dbc.Col([
                                html.Div([
                                    html.Div("24h Change", className="metric-label"),
                                    html.Div("0.00%", className="metric-value text-success"),
                                ], className="metric-card mb-3")
                            ], width=12),
                            dbc.Col([
                                html.Div([
                                    html.Div("24h Volume", className="metric-label"),
                                    html.Div("$0", className="metric-value"),
                                ], className="metric-card mb-3")
                            ], width=12),
                            dbc.Col([
                                html.Div([
                                    html.Div("Risk Status", className="metric-label"),
                                    html.Div("✓ Safe", className="metric-value text-success"),
                                ], className="metric-card")
                            ], width=12)
                        ])
                    ])
                ])
            ], className="mb-4")
        ], md=6)
    ], className="mb-4"),
    
    # Recent Trades Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📋 Recent Trades", className="bg-dark"),
                dbc.CardBody([
                    html.Div(id="recent-trades-table")
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Auto-refresh interval
    dcc.Interval(
        id="trade-page-interval",
        interval=30000,  # 30 seconds
        n_intervals=0
    )
], fluid=True, className="p-4")


# Callback: Update market info when symbol changes
@callback(
    Output("trade-market-info", "children"),
    Input("trade-symbol-selector", "value"),
    Input("trade-page-interval", "n_intervals")
)
def update_market_info(symbol, n_intervals):
    """Update market information for selected symbol"""
    if not symbol:
        return html.Div("Select a symbol to view market data")
    
    try:
        from binance_trade_agent.dashboard.utils.data_fetch import get_market_data
        market_data = get_market_data(symbol)
        
        if "error" in market_data:
            return dbc.Alert(f"Error: {market_data['error']}", color="danger")
        
        price = market_data.get('price', 0)
        change_24h = market_data.get('change_24h', 0)
        ticker = market_data.get('ticker', {})
        volume_24h = ticker.get('quoteAssetVolume', 0)
        
        change_class = "text-success" if change_24h >= 0 else "text-danger"
        change_symbol = "▲" if change_24h >= 0 else "▼"
        
        return dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div("Current Price", className="metric-label"),
                    html.Div(f"${price:.2f}", className="metric-value"),
                ], className="metric-card mb-3")
            ], width=12),
            dbc.Col([
                html.Div([
                    html.Div("24h Change", className="metric-label"),
                    html.Div(f"{change_symbol} {change_24h:.2f}%", className=f"metric-value {change_class}"),
                ], className="metric-card mb-3")
            ], width=12),
            dbc.Col([
                html.Div([
                    html.Div("24h Volume", className="metric-label"),
                    html.Div(f"${volume_24h:,.0f}", className="metric-value"),
                ], className="metric-card mb-3")
            ], width=12),
            dbc.Col([
                html.Div([
                    html.Div("Risk Status", className="metric-label"),
                    html.Div("✓ Safe", className="metric-value text-success"),
                ], className="metric-card")
            ], width=12)
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading market data: {str(e)}", color="danger")


# Callback: Update price when LIMIT order type is selected
@callback(
    Output("trade-price-input", "disabled"),
    Input("trade-order-type", "value")
)
def toggle_price_input(order_type):
    """Enable/disable price input based on order type"""
    return order_type == "MARKET"


# Callback: Place order
@callback(
    Output("trade-alert", "children"),
    Output("trade-quantity-input", "value"),
    Output("trade-price-input", "value"),
    Input("trade-submit-btn", "n_clicks"),
    State("trade-symbol-selector", "value"),
    State("trade-side-selector", "value"),
    State("trade-order-type", "value"),
    State("trade-quantity-input", "value"),
    State("trade-price-input", "value"),
    prevent_initial_call=True
)
def place_trade_order(n_clicks, symbol, side, order_type, quantity, price):
    """Place a trade order"""
    if not n_clicks:
        return html.Div(), None, None
    
    # Validation
    errors = []
    if not symbol:
        errors.append("Symbol is required")
    if not side:
        errors.append("Side (BUY/SELL) is required")
    if not quantity or quantity <= 0:
        errors.append("Quantity must be greater than 0")
    if order_type == "LIMIT" and (not price or price <= 0):
        errors.append("Price must be greater than 0 for LIMIT orders")
    
    if errors:
        alert = dbc.Alert([
            html.Div(f"❌ {error}", className="mb-2") for error in errors
        ], color="danger")
        return alert, None, None
    
    try:
        components = get_trading_components()
        execution_agent = components['execution_agent']
        risk_agent = components['risk_agent']
        
        # Check risk limits
        risk_check = risk_agent.validate_trade(symbol, side, quantity, price or 0)
        if not risk_check.get('approved', False):
            reason = risk_check.get('reason', 'Trade rejected by risk management')
            return dbc.Alert(f"⚠️ Risk Check Failed: {reason}", color="warning"), None, None
        
        # Place the order
        order_result = execution_agent.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price
        )
        
        if order_result.get('success'):
            alert = dbc.Alert([
                html.H5("✅ Order Placed Successfully!"),
                html.Div(f"Order ID: {order_result.get('order_id', 'N/A')}"),
                html.Div(f"Symbol: {symbol} | Side: {side} | Qty: {quantity}"),
                html.Div(f"Price: ${price or 'Market'}")
            ], color="success")
            return alert, None, None
        else:
            error_msg = order_result.get('message', 'Unknown error')
            return dbc.Alert(f"❌ Order Failed: {error_msg}", color="danger"), None, None
            
    except Exception as e:
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        return dbc.Alert(f"❌ Error: {str(e)}", color="danger"), None, None


# Callback: Update recent trades table
@callback(
    Output("recent-trades-table", "children"),
    Input("trade-page-interval", "n_intervals")
)
def update_recent_trades(n_intervals):
    """Update recent trades table"""
    try:
        from binance_trade_agent.dashboard.utils.data_fetch import get_portfolio_data
        portfolio_data = get_portfolio_data()
        
        if "error" in portfolio_data:
            return dbc.Alert(f"Error: {portfolio_data['error']}", color="danger")
        
        recent_trades = portfolio_data.get('recent_trades', [])
        
        if not recent_trades:
            return dbc.Alert("No recent trades", color="info")
        
        rows = []
        for trade in recent_trades[:10]:  # Show last 10 trades
            pnl = float(trade.get('pnl', 0))
            pnl_class = "text-success" if pnl >= 0 else "text-danger"
            pnl_symbol = "+" if pnl >= 0 else ""
            
            rows.append(
                html.Tr([
                    html.Td(trade.get('symbol', 'N/A'), className="text-primary font-weight-bold"),
                    html.Td(trade.get('side', 'N/A')),
                    html.Td(f"{trade.get('quantity', 0):.4f}"),
                    html.Td(f"${trade.get('price', 0):.2f}"),
                    html.Td(pnl_symbol + f"${pnl:.2f}", className=pnl_class),
                    html.Td(trade.get('timestamp', 'N/A'), style={"fontSize": "0.85rem"})
                ])
            )
        
        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("Symbol"),
                html.Th("Side"),
                html.Th("Qty"),
                html.Th("Price"),
                html.Th("P&L"),
                html.Th("Time")
            ])),
            html.Tbody(rows)
        ], dark=True, hover=True, responsive=True, className="mb-0")
        
    except Exception as e:
        return dbc.Alert(f"Error loading trades: {str(e)}", color="danger")
