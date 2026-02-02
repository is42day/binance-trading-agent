"""Signals & Risk Page - Trading signals, risk metrics, emergency controls"""

import logging

import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

try:
    from binance_trade_agent.dashboard.components.navbar import create_metric_card
    from binance_trade_agent.dashboard.utils.data_fetch import (
        get_risk_status,
        get_signals,
        get_trailing_stops,
    )
except Exception as e:
    print(f"Import error: {e}")
    get_signals = None
    get_risk_status = None
    get_trailing_stops = None
    create_metric_card = None

logger = logging.getLogger(__name__)

layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "🎯 Signals & Risk",
                            style={"marginTop": "2rem", "color": "#f4f2ee"},
                        ),
                        html.P(
                            "Real-time trading signals and risk management metrics",
                            style={"color": "#b8b4b0"},
                        ),
                    ]
                )
            ],
            className="mb-4",
        ),
        # Signals Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4(
                            "📊 Trading Signals",
                            style={"color": "#ff914d", "marginTop": "2rem"},
                        ),
                    ]
                )
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            id="signals-content",
                            children=[
                                dbc.Alert(
                                    "Loading trading signals...",
                                    color="info",
                                    className="text-center",
                                )
                            ],
                            style={},
                        )
                    ],
                    width=12,
                )
            ],
            className="mb-4",
        ),
        # Risk Metrics Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4(
                            "⚠️ Risk Metrics",
                            style={"color": "#ff914d", "marginTop": "2rem"},
                        ),
                    ]
                )
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            id="risk-metrics",
                            children=[
                                dbc.Alert(
                                    "Loading risk metrics...",
                                    color="info",
                                    className="text-center",
                                )
                            ],
                            style={},
                        )
                    ],
                    width=12,
                )
            ],
            className="mb-4",
        ),
        # Risk Status Details
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Position Limits",
                                            className="card-title",
                                            style={"color": "#f4f2ee"},
                                        ),
                                        html.Div(
                                            id="position-limits",
                                            style={"minHeight": "200px"},
                                        ),
                                    ]
                                )
                            ],
                            style={
                                "backgroundColor": "#23242a",
                                "borderColor": "rgba(255, 145, 77, 0.2)",
                            },
                        )
                    ],
                    lg=6,
                    md=12,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Emergency Controls",
                                            className="card-title",
                                            style={"color": "#f4f2ee"},
                                        ),
                                        html.Div(
                                            id="emergency-controls",
                                            style={"minHeight": "200px"},
                                        ),
                                    ]
                                )
                            ],
                            style={
                                "backgroundColor": "#23242a",
                                "borderColor": "rgba(255, 145, 77, 0.2",
                            },
                        )
                    ],
                    lg=6,
                    md=12,
                ),
            ],
            className="mb-4",
        ),
        # Trailing Stops Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4(
                            "🎯 Active Trailing Stops",
                            style={"color": "#ff914d", "marginTop": "2rem"},
                        ),
                    ]
                )
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            id="trailing-stops-content",
                            children=[
                                dbc.Alert(
                                    "No active trailing stops",
                                    color="secondary",
                                    className="text-center",
                                )
                            ],
                            style={},
                        )
                    ],
                    width=12,
                )
            ],
            className="mb-4",
        ),
        # Auto-refresh interval
        dcc.Interval(id="signals-risk-timer", interval=30000, n_intervals=0),
    ],
    fluid=True,
    style={"paddingBottom": "3rem"},
)


# Callback for signals
@callback(
    Output("signals-content", "children"),
    Input("signals-risk-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_signals(n_intervals):
    """Update trading signals display"""
    try:
        if get_signals is None:
            return dbc.Alert("Signals unavailable", color="warning")

        signals = get_signals()

        if isinstance(signals, dict) and "error" in signals:
            return dbc.Alert(f"Error: {signals['error']}", color="danger")

        # Build signal cards - normalize signal to uppercase
        signal_type = signals.get("signal", "hold").upper()
        # Map "HOLD" to display text
        if signal_type == "HOLD":
            signal_type = "HOLD"
        confidence = signals.get("confidence", 0)
        indicators = signals.get("indicators", {})

        # Get MTF info from signal root
        mtf_trend = signals.get("mtf_trend", "N/A")
        mtf_confirmed = signals.get("mtf_confirmed", True)

        # Determine status color
        status_map = {"BUY": "success", "SELL": "danger", "HOLD": "warning", "NEUTRAL": "warning"}
        status = status_map.get(signal_type, "info")

        # MTF trend color
        mtf_color = "success" if mtf_trend == "BULLISH" else "danger" if mtf_trend == "BEARISH" else "warning"

        signal_card = dbc.Card(
            [
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.H4(
                                            signal_type,
                                            style={
                                                "color": "#f4f2ee",
                                                "marginBottom": "0",
                                            },
                                        ),
                                    ],
                                    width="auto",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Badge(
                                            f"Confidence: {confidence:.1%}",
                                            color=status,
                                            style={"fontSize": "0.875rem"},
                                        ),
                                        dbc.Badge(
                                            f"4h: {mtf_trend}",
                                            color=mtf_color,
                                            style={"fontSize": "0.75rem", "marginLeft": "0.5rem"},
                                        ),
                                    ],
                                    width="auto",
                                ),
                            ],
                            className="align-items-center",
                        ),
                        html.Hr(style={"borderColor": "rgba(255, 145, 77, 0.2)"}),
                        html.H6(
                            "Indicators:",
                            style={"color": "#f4f2ee", "marginTop": "1rem"},
                        ),
                        html.Div(
                            _format_indicators(indicators),
                            style={"marginBottom": "0"},
                        ),
                        # Show metadata if available
                        html.Hr(style={"borderColor": "rgba(255, 145, 77, 0.2)"}),
                        html.H6(
                            "Details:",
                            style={"color": "#f4f2ee", "marginTop": "0.5rem"},
                        ),
                        html.Ul(
                            _format_metadata(signals.get("metadata", {})),
                            style={"marginBottom": "0"},
                        ),
                    ]
                )
            ],
            style={
                "backgroundColor": "#23242a",
                "borderLeft": f"4px solid {'#27ae60' if signal_type == 'BUY' else '#e74c3c' if signal_type == 'SELL' else '#f39c12'}",
            },
        )

        return signal_card

    except Exception as e:
        logger.error(f"Signals error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


def _format_indicators(indicators: dict) -> list:
    """Format indicators for display, handling nested dicts"""
    items = []
    if not indicators:
        return [html.Li("No indicators available", style={"color": "#b8b4b0"})]

    for k, v in indicators.items():
        if isinstance(v, dict):
            # Nested dict (e.g., rsi, macd sub-indicators)
            if "value" in v:
                # Simple indicator with value
                val = v.get("value", "N/A")
                if isinstance(val, (int, float)):
                    val = f"{val:.2f}"
                items.append(
                    html.Li(
                        f"{k.upper()}: {val}",
                        style={"color": "#b8b4b0", "marginBottom": "0.25rem"},
                    )
                )
            else:
                # Complex nested dict - extract key values
                sub_items = []
                for sub_k, sub_v in list(v.items())[:3]:
                    if isinstance(sub_v, (int, float)):
                        sub_items.append(f"{sub_k}={sub_v:.2f}")
                    elif sub_v is not None:
                        sub_items.append(f"{sub_k}={sub_v}")
                if sub_items:
                    items.append(
                        html.Li(
                            f"{k.upper()}: {', '.join(sub_items)}",
                            style={"color": "#b8b4b0", "marginBottom": "0.25rem"},
                        )
                    )
        elif isinstance(v, (int, float)):
            items.append(
                html.Li(
                    f"{k.upper()}: {v:.4f}" if isinstance(v, float) else f"{k.upper()}: {v}",
                    style={"color": "#b8b4b0", "marginBottom": "0.25rem"},
                )
            )
        elif v is not None:
            items.append(
                html.Li(
                    f"{k.upper()}: {v}",
                    style={"color": "#b8b4b0", "marginBottom": "0.25rem"},
                )
            )

    return items[:8] if items else [html.Li("No indicators", style={"color": "#b8b4b0"})]


def _format_metadata(metadata: dict) -> list:
    """Format metadata for display"""
    if not metadata:
        return [html.Li("No metadata", style={"color": "#b8b4b0"})]

    # Key fields to display
    display_fields = [
        ("current_price", "Price"),
        ("rsi_signal", "RSI Signal"),
        ("macd_signal", "MACD Signal"),
        ("rsi_confidence", "RSI Conf"),
        ("macd_confidence", "MACD Conf"),
        ("volume_confirmed", "Vol Confirmed"),
        ("trend", "1h Trend"),
        ("trend_filtered", "Trend Filtered"),
    ]

    items = []
    for key, label in display_fields:
        if key in metadata:
            val = metadata[key]
            if isinstance(val, float):
                if "confidence" in key.lower():
                    val = f"{val:.1%}"
                elif "price" in key.lower():
                    val = f"${val:,.2f}"
                else:
                    val = f"{val:.2f}"
            elif isinstance(val, bool):
                val = "✓" if val else "✗"
            items.append(
                html.Li(
                    f"{label}: {val}",
                    style={"color": "#b8b4b0", "marginBottom": "0.25rem"},
                )
            )

    return items[:8] if items else [html.Li("No details", style={"color": "#b8b4b0"})]


# Callback for risk metrics
@callback(
    Output("risk-metrics", "children"),
    Input("signals-risk-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_risk_metrics(n_intervals):
    """Update risk metrics display"""
    try:
        if get_risk_status is None or create_metric_card is None:
            return dbc.Alert("Risk data unavailable", color="warning")

        risk_data = get_risk_status()

        if isinstance(risk_data, dict) and "error" in risk_data:
            return dbc.Alert(f"Error: {risk_data['error']}", color="danger")

        # Extract key metrics
        portfolio_value = risk_data.get("portfolio_value", 0)
        max_risk_per_trade = risk_data.get("max_risk_per_trade_percent", 2)
        current_drawdown = risk_data.get("current_drawdown_percent", 0)
        max_position = risk_data.get("max_position_percent", 5)

        metrics = dbc.Row(
            [
                dbc.Col(
                    [
                        create_metric_card(
                            label="Portfolio Value",
                            value=f"${portfolio_value:,.2f}",
                            icon="💰",
                            status="primary",
                        )
                    ],
                    lg=3,
                    md=6,
                    xs=12,
                    className="mb-3",
                ),
                dbc.Col(
                    [
                        create_metric_card(
                            label="Max Risk Per Trade",
                            value=f"{max_risk_per_trade:.1f}%",
                            icon="⚠️",
                            status="warning",
                        )
                    ],
                    lg=3,
                    md=6,
                    xs=12,
                    className="mb-3",
                ),
                dbc.Col(
                    [
                        create_metric_card(
                            label="Current Drawdown",
                            value=f"{current_drawdown:.2f}%",
                            delta=f"Max: {risk_data.get('max_drawdown_percent', 0):.2f}%",
                            icon="📉" if current_drawdown < 0 else "📈",
                            status=(
                                "danger"
                                if current_drawdown < -5
                                else "warning" if current_drawdown < 0 else "success"
                            ),
                        )
                    ],
                    lg=3,
                    md=6,
                    xs=12,
                    className="mb-3",
                ),
                dbc.Col(
                    [
                        create_metric_card(
                            label="Max Position",
                            value=f"{max_position:.1f}%",
                            icon="📊",
                            status="info",
                        )
                    ],
                    lg=3,
                    md=6,
                    xs=12,
                    className="mb-3",
                ),
            ]
        )

        return metrics

    except Exception as e:
        logger.error(f"Risk metrics error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for position limits
@callback(
    Output("position-limits", "children"),
    Input("signals-risk-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_position_limits(n_intervals):
    """Update position limits display"""
    try:
        if get_risk_status is None:
            return dbc.Alert("Position limits unavailable", color="warning")

        risk_data = get_risk_status()

        if isinstance(risk_data, dict) and "error" in risk_data:
            return dbc.Alert(f"Error: {risk_data['error']}", color="danger")

        config = risk_data.get("config", {})
        symbol_limits = risk_data.get("symbol_limits", {})

        # Build limits table
        rows = []
        rows.append(
            html.Tr(
                [
                    html.Th("Symbol", style={"color": "#f4f2ee", "textAlign": "left"}),
                    html.Th(
                        "Max Position %",
                        style={"color": "#f4f2ee", "textAlign": "right"},
                    ),
                    html.Th("Stop Loss %", style={"color": "#f4f2ee", "textAlign": "right"}),
                    html.Th("Status", style={"color": "#f4f2ee", "textAlign": "center"}),
                ]
            )
        )

        for symbol, limits in symbol_limits.items():
            status_badge = dbc.Badge("✓ Active", color="success", style={"fontSize": "0.75rem"})

            rows.append(
                html.Tr(
                    [
                        html.Td(symbol, style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                        html.Td(
                            f"{limits.get('max_position_percent', 5):.1f}%",
                            style={
                                "color": "#b8b4b0",
                                "fontSize": "0.875rem",
                                "textAlign": "right",
                            },
                        ),
                        html.Td(
                            f"{limits.get('stop_loss_percent', 2):.1f}%",
                            style={
                                "color": "#b8b4b0",
                                "fontSize": "0.875rem",
                                "textAlign": "right",
                            },
                        ),
                        html.Td(status_badge, style={"textAlign": "center"}),
                    ]
                )
            )

        return html.Table(
            rows,
            style={
                "width": "100%",
                "borderCollapse": "collapse",
                "fontSize": "0.875rem",
            },
        )

    except Exception as e:
        logger.error(f"Position limits error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for emergency controls
@callback(
    Output("emergency-controls", "children"),
    Input("signals-risk-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_emergency_controls(n_intervals):
    """Update emergency controls display"""
    try:
        if get_risk_status is None:
            return dbc.Alert("Controls unavailable", color="warning")

        risk_data = get_risk_status()

        if isinstance(risk_data, dict) and "error" in risk_data:
            return dbc.Alert(f"Error: {risk_data['error']}", color="danger")

        emergency_stop = risk_data.get("emergency_stop", False)

        # Display emergency stop status
        stop_status = dbc.Alert(
            [
                html.H6(
                    "🛑 Emergency Stop" if emergency_stop else "✓ Trading Active",
                    style={"marginBottom": "0"},
                ),
                html.P(
                    (
                        "System is in emergency mode. All trading halted."
                        if emergency_stop
                        else "System trading normally."
                    ),
                    style={"marginBottom": "0", "fontSize": "0.875rem"},
                ),
            ],
            color="danger" if emergency_stop else "success",
            style={"marginBottom": "1rem"},
        )

        # Display last update time
        last_updated = risk_data.get("last_updated", "N/A")

        return html.Div(
            [
                stop_status,
                html.Div(
                    [
                        html.Span(
                            "Last Updated: ",
                            style={"color": "#b8b4b0", "fontSize": "0.75rem"},
                        ),
                        html.Span(
                            last_updated[:19],
                            style={
                                "color": "#ff914d",
                                "fontSize": "0.75rem",
                                "fontWeight": "bold",
                            },
                        ),
                    ],
                    style={"textAlign": "center"},
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Emergency controls error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for trailing stops
@callback(
    Output("trailing-stops-content", "children"),
    Input("signals-risk-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_trailing_stops(n_intervals):
    """Update trailing stops display"""
    try:
        if get_trailing_stops is None:
            return dbc.Alert("Trailing stops unavailable", color="warning")

        trailing_data = get_trailing_stops()

        if isinstance(trailing_data, dict) and "error" in trailing_data:
            return dbc.Alert(f"Error: {trailing_data['error']}", color="danger")

        positions = trailing_data.get("positions", {})
        active_count = trailing_data.get("active_stops", 0)

        if not positions or active_count == 0:
            return dbc.Alert(
                [
                    html.Span("🎯 "),
                    html.Strong("No active trailing stops. "),
                    html.Span("Trailing stops are automatically registered when trades execute."),
                ],
                color="secondary",
                className="text-center",
            )

        # Build cards for each trailing stop
        cards = []
        for symbol, pos in positions.items():
            entry_price = pos.get("entry_price", 0)
            current_price = pos.get("current_price", 0)
            current_stop = pos.get("current_stop", 0)
            side = pos.get("side", "buy").upper()
            pnl_pct = pos.get("pnl_pct", 0)
            highest = pos.get("highest_price", 0)
            lowest = pos.get("lowest_price", 0)

            # Determine P&L color
            pnl_color = "success" if pnl_pct >= 0 else "danger"
            side_color = "#4CAF50" if side == "BUY" else "#f44336"

            card = dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.H5(
                                                symbol,
                                                style={
                                                    "color": "#f4f2ee",
                                                    "marginBottom": "0.5rem",
                                                    "display": "inline-block",
                                                },
                                            ),
                                            dbc.Badge(
                                                side,
                                                color="success" if side == "BUY" else "danger",
                                                className="ms-2",
                                            ),
                                        ]
                                    ),
                                    html.Hr(style={"borderColor": "rgba(255, 145, 77, 0.3)"}),
                                    # Price info
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Small("Entry", style={"color": "#b8b4b0"}),
                                                    html.Div(
                                                        f"${entry_price:,.2f}",
                                                        style={"color": "#f4f2ee", "fontWeight": "bold"},
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Small("Current", style={"color": "#b8b4b0"}),
                                                    html.Div(
                                                        f"${current_price:,.2f}" if current_price else "N/A",
                                                        style={"color": "#ff914d", "fontWeight": "bold"},
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    # Stop and P&L
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Small("Trail Stop", style={"color": "#b8b4b0"}),
                                                    html.Div(
                                                        f"${current_stop:,.2f}",
                                                        style={"color": "#FFC107", "fontWeight": "bold"},
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Small("P&L", style={"color": "#b8b4b0"}),
                                                    html.Div(
                                                        f"{pnl_pct:+.2f}%",
                                                        style={
                                                            "color": "#4CAF50" if pnl_pct >= 0 else "#f44336",
                                                            "fontWeight": "bold",
                                                        },
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    # High/Low
                                    html.Div(
                                        [
                                            html.Small(
                                                f"High: ${highest:,.2f} | Low: ${lowest:,.2f}",
                                                style={"color": "#888"},
                                            ),
                                        ],
                                        className="text-center",
                                    ),
                                ]
                            )
                        ],
                        style={
                            "backgroundColor": "#23242a",
                            "borderColor": "rgba(255, 145, 77, 0.3)",
                            "borderWidth": "1px",
                        },
                    )
                ],
                lg=4,
                md=6,
                xs=12,
                className="mb-3",
            )
            cards.append(card)

        return dbc.Row(cards)

    except Exception as e:
        logger.error(f"Trailing stops error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")
