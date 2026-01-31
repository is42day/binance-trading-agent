"""
Execute Trade Page - Enhanced with validation, preview, and safety features
"""

import traceback
from decimal import Decimal, ROUND_DOWN

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update

from binance_trade_agent.dashboard.utils.data_fetch import get_trading_components

# Default symbols for trading
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
ORDER_TYPES = ["LIMIT", "MARKET"]
SIDES = ["BUY", "SELL"]

# Symbol exchange info cache (would be populated from Binance)
SYMBOL_INFO_CACHE = {}


def get_symbol_info(symbol):
    """
    Get exchange info for symbol (mock for now, should fetch from Binance)
    Returns dict with constraints and a 'available' flag indicating if data is real
    """
    if symbol in SYMBOL_INFO_CACHE:
        return SYMBOL_INFO_CACHE[symbol]
    
    # Mock data - in production, fetch from Binance exchangeInfo endpoint
    # TODO: Implement dynamic fetching from Binance API with TTL cache (1h)
    known_symbols = {
        "BTCUSDT": {"tick_size": 0.01, "step_size": 0.00001, "min_notional": 10.0, "min_qty": 0.00001, "available": True},
        "ETHUSDT": {"tick_size": 0.01, "step_size": 0.0001, "min_notional": 10.0, "min_qty": 0.0001, "available": True},
        "BNBUSDT": {"tick_size": 0.01, "step_size": 0.001, "min_notional": 10.0, "min_qty": 0.001, "available": True},
        "SOLUSDT": {"tick_size": 0.01, "step_size": 0.01, "min_notional": 10.0, "min_qty": 0.01, "available": True},
        "ADAUSDT": {"tick_size": 0.0001, "step_size": 1.0, "min_notional": 10.0, "min_qty": 1.0, "available": True},
    }
    
    if symbol in known_symbols:
        SYMBOL_INFO_CACHE[symbol] = known_symbols[symbol]
    else:
        # Symbol not in our mock data - return conservative defaults with warning flag
        SYMBOL_INFO_CACHE[symbol] = {
            "tick_size": 0.01, 
            "step_size": 0.001, 
            "min_notional": 10.0, 
            "min_qty": 0.001,
            "available": False  # Flag: constraints are not verified
        }
    
    return SYMBOL_INFO_CACHE[symbol]


def format_quantity(qty, step_size):
    """
    Format quantity to match step size (rounds DOWN for safety)
    Returns: (formatted_qty, was_adjusted)
    """
    if not qty or not step_size:
        return qty, False
    
    original_qty = qty
    precision = len(str(step_size).split('.')[-1]) if '.' in str(step_size) else 0
    adjusted_qty = float(Decimal(str(qty)).quantize(Decimal(str(step_size)), rounding=ROUND_DOWN))
    
    was_adjusted = abs(original_qty - adjusted_qty) > 1e-10
    return adjusted_qty, was_adjusted


def format_price(price, tick_size):
    """
    Format price to match tick size (rounds DOWN for safety)
    Returns: (formatted_price, was_adjusted)
    """
    if not price or not tick_size:
        return price, False
    
    original_price = price
    precision = len(str(tick_size).split('.')[-1]) if '.' in str(tick_size) else 0
    adjusted_price = float(Decimal(str(price)).quantize(Decimal(str(tick_size)), rounding=ROUND_DOWN))
    
    was_adjusted = abs(original_price - adjusted_price) > 1e-10
    return adjusted_price, was_adjusted


layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "💼 Execute Trade",
                            style={"marginTop": "2rem", "marginBottom": "1rem"},
                        ),
                        dbc.Alert(
                            [
                                html.I(className="bi bi-shield-check me-2"),
                                "You're trading on ",
                                html.Strong("Binance Testnet"),
                                " - No real money at risk"
                            ],
                            color="info",
                            className="mb-3"
                        )
                    ]
                )
            ]
        ),
        # Order Form Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("📝 Trade Order Form", className="bg-dark"),
                                dbc.CardBody(
                                    [
                                        # Symbol and Side Selection
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Symbol",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="trade-symbol-selector",
                                                            options=[
                                                                {
                                                                    "label": sym,
                                                                    "value": sym,
                                                                }
                                                                for sym in DEFAULT_SYMBOLS
                                                            ],
                                                            value=DEFAULT_SYMBOLS[0],
                                                            className="form-control",
                                                            clearable=False,
                                                        ),
                                                        html.Small(
                                                            id="symbol-hint",
                                                            className="text-muted",
                                                            children="Select trading pair"
                                                        )
                                                    ],
                                                    md=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Side",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="trade-side-selector",
                                                            options=[
                                                                {
                                                                    "label": f"🟢 {side}" if side == "BUY" else f"🔴 {side}",
                                                                    "value": side,
                                                                }
                                                                for side in SIDES
                                                            ],
                                                            value="BUY",
                                                            className="form-control",
                                                            clearable=False,
                                                        ),
                                                        html.Small(
                                                            "Buy or sell position",
                                                            className="text-muted"
                                                        )
                                                    ],
                                                    md=6,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        # Order Type
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Order Type",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="trade-order-type",
                                                            options=[
                                                                {
                                                                    "label": ot,
                                                                    "value": ot,
                                                                }
                                                                for ot in ORDER_TYPES
                                                            ],
                                                            value="LIMIT",
                                                            className="form-control",
                                                            clearable=False,
                                                        ),
                                                        html.Small(
                                                            id="order-type-hint",
                                                            className="text-muted",
                                                            children="LIMIT: set price | MARKET: instant at best price"
                                                        )
                                                    ],
                                                    md=12,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        # Price Input (shown only for LIMIT orders)
                                        html.Div(
                                            id="price-input-container",
                                            children=[
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            [
                                                                html.Label(
                                                                    "Limit Price (USDT)",
                                                                    className="text-secondary font-weight-bold",
                                                                ),
                                                                dbc.Input(
                                                                    id="trade-price-input",
                                                                    type="number",
                                                                    placeholder="Enter limit price",
                                                                    className="form-control",
                                                                    step=0.01,
                                                                    min=0,
                                                                ),
                                                                html.Small(
                                                                    id="price-hint",
                                                                    className="text-muted",
                                                                    children="Must respect tick size; > 0"
                                                                )
                                                            ],
                                                            md=12,
                                                        ),
                                                    ],
                                                    className="mb-3",
                                                )
                                            ]
                                        ),
                                        # Market order note (shown only for MARKET orders)
                                        html.Div(
                                            id="market-note-container",
                                            style={"display": "none"},
                                            children=[
                                                dbc.Alert(
                                                    [
                                                        html.I(className="bi bi-info-circle me-2"),
                                                        html.Strong("Market Order: "),
                                                        "Will execute immediately at best available price"
                                                    ],
                                                    color="info",
                                                    className="mb-3"
                                                )
                                            ]
                                        ),
                                        # Quantity
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Quantity",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dbc.Input(
                                                            id="trade-quantity-input",
                                                            type="number",
                                                            placeholder="Enter quantity",
                                                            className="form-control",
                                                            step=0.001,
                                                            min=0,
                                                        ),
                                                        html.Small(
                                                            id="quantity-hint",
                                                            className="text-muted",
                                                            children="Must respect lot size / min notional"
                                                        )
                                                    ],
                                                    md=12,
                                                )
                                            ],
                                            className="mb-3",
                                        ),
                                        # Quick quantity buttons
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Small("Quick amounts:", className="text-muted me-2"),
                                                        dbc.ButtonGroup(
                                                            [
                                                                dbc.Button("25%", id="qty-25", size="sm", outline=True, color="secondary"),
                                                                dbc.Button("50%", id="qty-50", size="sm", outline=True, color="secondary"),
                                                                dbc.Button("75%", id="qty-75", size="sm", outline=True, color="secondary"),
                                                                dbc.Button("100%", id="qty-100", size="sm", outline=True, color="secondary"),
                                                            ],
                                                            size="sm"
                                                        )
                                                    ],
                                                    md=12,
                                                )
                                            ],
                                            className="mb-3",
                                        ),
                                        # Validation feedback
                                        html.Div(
                                            id="validation-feedback",
                                            className="mb-3"
                                        ),
                                        # Trade Preview Card
                                        html.Div(
                                            id="trade-preview",
                                            className="mb-3"
                                        ),
                                        # Buttons
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "🔍 Review Order",
                                                            id="trade-review-btn",
                                                            color="primary",
                                                            className="btn-primary",
                                                            style={
                                                                "width": "100%",
                                                                "minHeight": "44px",
                                                            },
                                                            disabled=True,
                                                        )
                                                    ],
                                                    md=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "🔄 Reset",
                                                            id="trade-reset-btn",
                                                            color="secondary",
                                                            style={
                                                                "width": "100%",
                                                                "minHeight": "44px",
                                                            },
                                                        )
                                                    ],
                                                    md=6,
                                                ),
                                            ]
                                        ),
                                    ]
                                ),
                            ],
                            className="mb-4",
                        )
                    ],
                    md=6,
                ),
                # Current Market Info
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("📊 Current Market Info", className="bg-dark"),
                                dbc.CardBody(
                                    [
                                        html.Div(
                                            id="trade-market-info",
                                            children=[
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            [
                                                                html.Div(
                                                                    [
                                                                        html.Div(
                                                                            "Current Price",
                                                                            className="metric-label",
                                                                        ),
                                                                        html.Div(
                                                                            "$0.00",
                                                                            className="metric-value",
                                                                        ),
                                                                    ],
                                                                    className="metric-card mb-3",
                                                                )
                                                            ],
                                                            width=12,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                html.Div(
                                                                    [
                                                                        html.Div(
                                                                            "24h Change",
                                                                            className="metric-label",
                                                                        ),
                                                                        html.Div(
                                                                            "0.00%",
                                                                            className="metric-value text-success",
                                                                        ),
                                                                    ],
                                                                    className="metric-card mb-3",
                                                                )
                                                            ],
                                                            width=12,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                html.Div(
                                                                    [
                                                                        html.Div(
                                                                            "24h Volume",
                                                                            className="metric-label",
                                                                        ),
                                                                        html.Div(
                                                                            "$0",
                                                                            className="metric-value",
                                                                        ),
                                                                    ],
                                                                    className="metric-card mb-3",
                                                                )
                                                            ],
                                                            width=12,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                html.Div(
                                                                    [
                                                                        html.Div(
                                                                            "Risk Status",
                                                                            className="metric-label",
                                                                        ),
                                                                        html.Div(
                                                                            "✓ Safe",
                                                                            className="metric-value text-success",
                                                                        ),
                                                                    ],
                                                                    className="metric-card",
                                                                )
                                                            ],
                                                            width=12,
                                                        ),
                                                    ]
                                                )
                                            ],
                                        )
                                    ]
                                ),
                            ],
                            className="mb-4",
                        )
                    ],
                    md=6,
                ),
            ],
            className="mb-4",
        ),
        # Recent Trades Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("📋 Recent Trades", className="bg-dark"),
                                dbc.CardBody([html.Div(id="recent-trades-table")]),
                            ],
                            className="mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # Confirmation Modal
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("🔍 Confirm Order")),
                dbc.ModalBody(
                    [
                        html.Div(id="modal-order-summary"),
                        html.Hr(),
                        html.Div(id="modal-risk-check"),
                        html.Div(id="modal-alert"),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Cancel", id="modal-cancel-btn", className="me-2", color="secondary"),
                        dbc.Button("Place Order", id="modal-confirm-btn", color="success"),
                    ]
                ),
            ],
            id="confirmation-modal",
            is_open=False,
            size="lg",
        ),
        # Auto-refresh interval
        dcc.Interval(id="trade-page-interval", interval=30000, n_intervals=0),  # 30 seconds
        # Store for current market price
        dcc.Store(id="current-market-price", data=0),
    ],
    fluid=True,
    className="p-4",
)


# Callback: Update market info and store current price
@callback(
    Output("trade-market-info", "children"),
    Output("current-market-price", "data"),
    Input("trade-symbol-selector", "value"),
    Input("trade-page-interval", "n_intervals"),
)
def update_market_info(symbol, n_intervals):
    """Update market information for selected symbol"""
    if not symbol:
        return html.Div("Select a symbol to view market data"), 0

    try:
        from binance_trade_agent.dashboard.utils.data_fetch import get_market_data

        market_data = get_market_data(symbol)

        if "error" in market_data:
            return dbc.Alert(f"Error: {market_data['error']}", color="danger"), 0

        price = market_data.get("price", 0)
        change_24h = market_data.get("change_24h", 0)
        ticker = market_data.get("ticker", {})
        volume_24h = ticker.get("quoteAssetVolume", 0)

        change_class = "text-success" if change_24h >= 0 else "text-danger"
        change_symbol = "▲" if change_24h >= 0 else "▼"

        market_info = dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div("Current Price", className="metric-label"),
                                html.Div(f"${price:.2f}", className="metric-value"),
                            ],
                            className="metric-card mb-3",
                        )
                    ],
                    width=12,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div("24h Change", className="metric-label"),
                                html.Div(
                                    f"{change_symbol} {change_24h:.2f}%",
                                    className=f"metric-value {change_class}",
                                ),
                            ],
                            className="metric-card mb-3",
                        )
                    ],
                    width=12,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div("24h Volume", className="metric-label"),
                                html.Div(f"${volume_24h:,.0f}", className="metric-value"),
                            ],
                            className="metric-card mb-3",
                        )
                    ],
                    width=12,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div("Risk Status", className="metric-label"),
                                html.Div("✓ Safe", className="metric-value text-success"),
                            ],
                            className="metric-card",
                        )
                    ],
                    width=12,
                ),
            ]
        )
        return market_info, price
    except Exception as e:
        return dbc.Alert(f"Error loading market data: {str(e)}", color="danger"), 0


# Callback: Toggle price input and market note visibility
@callback(
    Output("price-input-container", "style"),
    Output("market-note-container", "style"),
    Output("order-type-hint", "children"),
    Input("trade-order-type", "value")
)
def toggle_price_visibility(order_type):
    """Show/hide price input based on order type"""
    if order_type == "MARKET":
        return {"display": "none"}, {"display": "block"}, "MARKET: instant execution at best price"
    else:
        return {"display": "block"}, {"display": "none"}, "LIMIT: set your desired price"


# Callback: Continuous validation and preview
@callback(
    Output("validation-feedback", "children"),
    Output("trade-preview", "children"),
    Output("trade-review-btn", "disabled"),
    Output("price-hint", "children"),
    Output("quantity-hint", "children"),
    Input("trade-symbol-selector", "value"),
    Input("trade-side-selector", "value"),
    Input("trade-order-type", "value"),
    Input("trade-quantity-input", "value"),
    Input("trade-price-input", "value"),
    State("current-market-price", "data"),
)
def validate_and_preview(symbol, side, order_type, quantity, price, market_price):
    """Continuously validate inputs and show trade preview"""
    errors = []
    warnings = []
    adjustments = []
    
    # Get symbol info for validation
    symbol_info = get_symbol_info(symbol)
    tick_size = symbol_info.get("tick_size", 0.01)
    step_size = symbol_info.get("step_size", 0.001)
    min_notional = symbol_info.get("min_notional", 10.0)
    min_qty = symbol_info.get("min_qty", 0.001)
    constraints_available = symbol_info.get("available", False)
    
    # WARNING: Exchange constraints not verified
    if not constraints_available:
        warnings.append(
            "⚠️ Exchange constraints not available for this symbol. "
            "Values will be validated at execution time by Binance."
        )
    
    # Update hints
    price_hint = f"Tick size: {tick_size} | Current: ${market_price:.2f}"
    qty_hint = f"Step size: {step_size} | Min qty: {min_qty} | Min notional: ${min_notional}"
    
    # Auto-adjust quantity for step size (round down for safety)
    adjusted_quantity = quantity
    qty_was_adjusted = False
    if quantity and step_size:
        adjusted_quantity, qty_was_adjusted = format_quantity(quantity, step_size)
        if qty_was_adjusted:
            adjustments.append(
                f"Quantity adjusted to {adjusted_quantity:.8f} (step size: {step_size}) - rounded down for safety"
            )
    
    # Auto-adjust price for tick size (round down for safety)
    adjusted_price = price
    price_was_adjusted = False
    if order_type == "LIMIT" and price and tick_size:
        adjusted_price, price_was_adjusted = format_price(price, tick_size)
        if price_was_adjusted:
            adjustments.append(
                f"Price adjusted to {adjusted_price:.8f} (tick size: {tick_size}) - rounded down for safety"
            )
    
    # Validate adjusted quantity
    if not adjusted_quantity or adjusted_quantity <= 0:
        errors.append("Quantity must be greater than 0")
    elif adjusted_quantity < min_qty:
        errors.append(f"Quantity must be at least {min_qty} (after adjustment)")
    
    # Validate adjusted price for LIMIT orders
    effective_price = adjusted_price if order_type == "LIMIT" else market_price
    if order_type == "LIMIT":
        if not adjusted_price or adjusted_price <= 0:
            errors.append("Price must be greater than 0 for LIMIT orders")
    
    # Validate min notional with adjusted values
    if adjusted_quantity and effective_price:
        notional = adjusted_quantity * effective_price
        if notional < min_notional:
            errors.append(f"Order value (${notional:.2f}) must be at least ${min_notional}")
    
    # Build validation feedback
    feedback_children = []
    if errors:
        feedback_children.append(
            dbc.Alert(
                [html.Div(f"❌ {error}") for error in errors],
                color="danger",
            )
        )
    if warnings:
        feedback_children.append(
            dbc.Alert(
                [html.Div(warning) for warning in warnings],
                color="warning",
            )
        )
    if adjustments:
        feedback_children.append(
            dbc.Alert(
                [
                    html.Div([html.Strong("🔧 Auto-adjustments applied:")]),
                    *[html.Div(adj, className="mt-1") for adj in adjustments]
                ],
                color="info",
            )
        )
    
    # Build trade preview using ADJUSTED values
    preview_children = []
    if adjusted_quantity and effective_price and not errors:
        notional = adjusted_quantity * effective_price
        estimated_fee = notional * 0.001  # 0.1% estimate
        
        side_color = "success" if side == "BUY" else "danger"
        side_icon = "🟢" if side == "BUY" else "🔴"
        
        preview_children = [
            dbc.Card(
                [
                    dbc.CardHeader([
                        html.I(className="bi bi-eye me-2"),
                        "Order Preview"
                    ], className="bg-secondary text-white"),
                    dbc.CardBody(
                        [
                            dbc.Row([
                                dbc.Col([
                                    html.Strong("Symbol:"),
                                    html.Div(symbol, className="text-primary fs-5")
                                ], width=3),
                                dbc.Col([
                                    html.Strong("Side:"),
                                    html.Div([side_icon, f" {side}"], className=f"text-{side_color} fs-5")
                                ], width=3),
                                dbc.Col([
                                    html.Strong("Type:"),
                                    html.Div(order_type, className="fs-5")
                                ], width=3),
                                dbc.Col([
                                    html.Strong("Quantity:"),
                                    html.Div(f"{adjusted_quantity:.8f}", className="fs-5"),
                                    html.Small("(adjusted)" if qty_was_adjusted else "", className="text-muted")
                                ], width=3),
                            ], className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.Strong("Price:"),
                                    html.Div(
                                        [
                                            f"${adjusted_price:.8f}" if order_type == "LIMIT" else f"~${market_price:.2f} (Market)",
                                            html.Br() if price_was_adjusted and order_type == "LIMIT" else "",
                                            html.Small("(adjusted)" if price_was_adjusted and order_type == "LIMIT" else "", className="text-muted")
                                        ],
                                        className="text-info fs-5"
                                    )
                                ], width=4),
                                dbc.Col([
                                    html.Strong("Est. Total:"),
                                    html.Div(f"${notional:.2f}", className="text-warning fs-5")
                                ], width=4),
                                dbc.Col([
                                    html.Strong("Est. Fee:"),
                                    html.Div([
                                        f"${estimated_fee:.4f}",
                                        html.Br(),
                                        html.Small("(assumes 0.1%)", className="text-muted")
                                    ], className="text-muted fs-6")
                                ], width=4),
                            ]),
                        ]
                    ),
                ],
                color="dark",
                outline=True,
            )
        ]
    
    # Enable/disable review button
    button_disabled = len(errors) > 0 or not adjusted_quantity or not symbol
    
    return feedback_children, preview_children, button_disabled, price_hint, qty_hint


# Callback: Open confirmation modal
@callback(
    Output("confirmation-modal", "is_open"),
    Output("modal-order-summary", "children"),
    Output("modal-risk-check", "children"),
    Input("trade-review-btn", "n_clicks"),
    Input("modal-cancel-btn", "n_clicks"),
    Input("modal-confirm-btn", "n_clicks"),
    State("trade-symbol-selector", "value"),
    State("trade-side-selector", "value"),
    State("trade-order-type", "value"),
    State("trade-quantity-input", "value"),
    State("trade-price-input", "value"),
    State("current-market-price", "data"),
    State("confirmation-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_confirmation_modal(review_clicks, cancel_clicks, confirm_clicks, 
                               symbol, side, order_type, quantity, price, market_price, is_open):
    """Toggle confirmation modal and show order summary with ADJUSTED values"""
    from dash import ctx
    
    if not ctx.triggered_id:
        return no_update, no_update, no_update
    
    # Close modal on cancel or confirm
    if ctx.triggered_id in ["modal-cancel-btn", "modal-confirm-btn"]:
        return False, no_update, no_update
    
    # Open modal on review
    if ctx.triggered_id == "trade-review-btn":
        # Get symbol info and apply adjustments (same logic as preview)
        symbol_info = get_symbol_info(symbol)
        step_size = symbol_info.get("step_size", 0.001)
        tick_size = symbol_info.get("tick_size", 0.01)
        
        # Adjust values for execution
        adjusted_quantity, qty_adjusted = format_quantity(quantity, step_size)
        adjusted_price = price
        price_adjusted = False
        
        if order_type == "LIMIT" and price:
            adjusted_price, price_adjusted = format_price(price, tick_size)
        
        effective_price = adjusted_price if order_type == "LIMIT" else market_price
        notional = adjusted_quantity * effective_price if adjusted_quantity and effective_price else 0
        estimated_fee = notional * 0.001
        
        side_color = "success" if side == "BUY" else "danger"
        side_icon = "🟢" if side == "BUY" else "🔴"
        action_verb = "BUY" if side == "BUY" else "SELL"
        
        # SAFETY BANNER - Big, bold warning
        safety_banner = dbc.Alert([
            html.H4([
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                "CONFIRM ACTION"
            ], className="mb-3"),
            html.Div([
                "You are about to ",
                html.Strong(f"{action_verb} {adjusted_quantity:.8f} {symbol}", className=f"text-{side_color}"),
                " for approximately ",
                html.Strong(f"${notional:.2f}", className="text-warning"),
            ], className="fs-5 mb-2"),
            html.Hr(),
            html.Div([
                html.I(className="bi bi-shield-check me-2"),
                "This will place a ",
                html.Strong("real order on Binance TESTNET"),
                " (no real money at risk)"
            ], className="text-muted")
        ], color="warning", className="mb-3")
        
        # Order summary table
        summary_rows = [
            html.Tr([html.Td(html.Strong("Symbol")), html.Td(symbol, className="text-primary")]),
            html.Tr([html.Td(html.Strong("Side")), html.Td([side_icon, f" {side}"], className=f"text-{side_color}")]),
            html.Tr([html.Td(html.Strong("Order Type")), html.Td(order_type)]),
            html.Tr([
                html.Td(html.Strong("Quantity")), 
                html.Td([
                    f"{adjusted_quantity:.8f}",
                    html.Br() if qty_adjusted else "",
                    html.Small(f" (adjusted from {quantity:.8f})", className="text-info") if qty_adjusted else ""
                ])
            ]),
        ]
        
        if order_type == "LIMIT":
            summary_rows.append(
                html.Tr([
                    html.Td(html.Strong("Price")), 
                    html.Td([
                        f"${adjusted_price:.8f}",
                        html.Br() if price_adjusted else "",
                        html.Small(f" (adjusted from ${price:.8f})", className="text-info") if price_adjusted else ""
                    ], className="text-info")
                ])
            )
        else:
            summary_rows.append(
                html.Tr([
                    html.Td(html.Strong("Price")), 
                    html.Td(f"~${market_price:.2f} (Market - best available)", className="text-info")
                ])
            )
        
        summary_rows.extend([
            html.Tr([html.Td(html.Strong("Estimated Total")), html.Td(f"${notional:.2f}", className="text-warning")]),
            html.Tr([
                html.Td(html.Strong("Estimated Fee")), 
                html.Td([f"${estimated_fee:.4f} ", html.Small("(assumes 0.1%)", className="text-muted")])
            ]),
        ])
        
        summary = html.Div([
            safety_banner,
            dbc.Table(summary_rows, bordered=True, hover=True, dark=True)
        ])
        
        # Perform risk check with ADJUSTED values
        try:
            components = get_trading_components()
            risk_agent = components["risk_agent"]
            risk_check = risk_agent.validate_trade(symbol, side, adjusted_quantity, effective_price or 0)
            
            if risk_check.get("approved", False):
                risk_status = dbc.Alert([
                    html.I(className="bi bi-shield-check me-2"),
                    html.Strong("✅ Risk Check: PASSED"),
                    html.Div("Order meets all risk management criteria", className="mt-2 text-muted")
                ], color="success")
            else:
                reason = risk_check.get("reason", "Unknown reason")
                risk_status = dbc.Alert([
                    html.I(className="bi bi-exclamation-triangle me-2"),
                    html.Strong("⚠️ Risk Check: BLOCKED"),
                    html.Br(),
                    html.Div(f"Reason: {reason}", className="mt-2")
                ], color="danger")
        except Exception as e:
            risk_status = dbc.Alert(f"Error checking risk: {str(e)}", color="warning")
        
        return True, summary, risk_status
    
    return no_update, no_update, no_update


# Callback: Place order after confirmation
@callback(
    Output("modal-alert", "children"),
    Output("trade-quantity-input", "value"),
    Output("trade-price-input", "value"),
    Input("modal-confirm-btn", "n_clicks"),
    State("trade-symbol-selector", "value"),
    State("trade-side-selector", "value"),
    State("trade-order-type", "value"),
    State("trade-quantity-input", "value"),
    State("trade-price-input", "value"),
    prevent_initial_call=True,
)
def place_order_confirmed(n_clicks, symbol, side, order_type, quantity, price):
    """Place order after confirmation - uses ADJUSTED values for execution"""
    if not n_clicks:
        return no_update, no_update, no_update

    try:
        components = get_trading_components()
        execution_agent = components["execution_agent"]
        risk_agent = components["risk_agent"]
        
        # Apply same adjustments as validation and modal
        symbol_info = get_symbol_info(symbol)
        step_size = symbol_info.get("step_size", 0.001)
        tick_size = symbol_info.get("tick_size", 0.01)
        
        # Adjust values for execution
        adjusted_quantity, _ = format_quantity(quantity, step_size)
        adjusted_price = price
        
        if order_type == "LIMIT" and price:
            adjusted_price, _ = format_price(price, tick_size)

        # Final risk check with ADJUSTED values
        risk_check = risk_agent.validate_trade(symbol, side, adjusted_quantity, adjusted_price or 0)
        if not risk_check.get("approved", False):
            reason = risk_check.get("reason", "Trade rejected by risk management")
            return dbc.Alert(f"⚠️ Risk Check Failed: {reason}", color="danger"), no_update, no_update

        # Place the order with ADJUSTED values
        order_result = execution_agent.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=adjusted_quantity,  # Use adjusted
            price=adjusted_price,         # Use adjusted
        )

        if order_result.get("success"):
            alert = dbc.Alert(
                [
                    html.H5([html.I(className="bi bi-check-circle me-2"), "Order Placed Successfully!"]),
                    html.Div(f"Order ID: {order_result.get('order_id', 'N/A')}"),
                    html.Div(f"Symbol: {symbol} | Side: {side} | Qty: {adjusted_quantity:.8f}"),
                    html.Div(f"Price: ${adjusted_price or 'Market'}"),
                ],
                color="success",
            )
            return alert, None, None
        else:
            error_msg = order_result.get("message", "Unknown error")
            return dbc.Alert(f"❌ Order Failed: {error_msg}", color="danger"), no_update, no_update

    except Exception as e:
        return dbc.Alert(f"❌ Error: {str(e)}", color="danger"), no_update, no_update


# Callback: Update recent trades table
@callback(
    Output("recent-trades-table", "children"),
    Input("trade-page-interval", "n_intervals"),
)
def update_recent_trades(n_intervals):
    """Update recent trades table"""
    try:
        from binance_trade_agent.dashboard.utils.data_fetch import get_portfolio_data

        portfolio_data = get_portfolio_data()

        if "error" in portfolio_data:
            return dbc.Alert(f"Error: {portfolio_data['error']}", color="danger")

        recent_trades = portfolio_data.get("recent_trades", [])

        if not recent_trades:
            return dbc.Alert("No recent trades", color="info")

        rows = []
        for trade in recent_trades[:10]:  # Show last 10 trades
            pnl = float(trade.get("pnl", 0))
            pnl_class = "text-success" if pnl >= 0 else "text-danger"
            pnl_symbol = "+" if pnl >= 0 else ""

            rows.append(
                html.Tr(
                    [
                        html.Td(
                            trade.get("symbol", "N/A"),
                            className="text-primary font-weight-bold",
                        ),
                        html.Td(trade.get("side", "N/A")),
                        html.Td(f"{trade.get('quantity', 0):.4f}"),
                        html.Td(f"${trade.get('price', 0):.2f}"),
                        html.Td(pnl_symbol + f"${pnl:.2f}", className=pnl_class),
                        html.Td(trade.get("timestamp", "N/A"), style={"fontSize": "0.85rem"}),
                    ]
                )
            )

        return dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Symbol"),
                            html.Th("Side"),
                            html.Th("Qty"),
                            html.Th("Price"),
                            html.Th("P&L"),
                            html.Th("Time"),
                        ]
                    )
                ),
                html.Tbody(rows),
            ],
            dark=True,
            hover=True,
            responsive=True,
            className="mb-0",
        )

    except Exception as e:
        return dbc.Alert(f"Error loading trades: {str(e)}", color="danger")
