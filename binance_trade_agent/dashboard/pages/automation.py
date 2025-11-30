"""
Automation Control Page - Manage automated trading agent
Control strategy parameters, trading frequency, and risk settings
"""

from datetime import datetime

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "🤖 Automation Control",
                            style={"marginTop": "2rem", "marginBottom": "1rem"},
                        )
                    ]
                )
            ]
        ),
        # Agent Status and Control
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    "Agent Status & Control",
                                    className="bg-dark d-flex justify-content-between align-items-center",
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Div(
                                                            [
                                                                html.P(
                                                                    "Agent Status:",
                                                                    className="text-secondary font-weight-bold",
                                                                ),
                                                                html.Div(
                                                                    id="agent-status-display",
                                                                    children=html.Span(
                                                                        "🟡 Unknown",
                                                                        className="text-warning",
                                                                    ),
                                                                    style={
                                                                        "fontSize": "1.5rem",
                                                                        "fontWeight": "bold",
                                                                    },
                                                                ),
                                                            ]
                                                        )
                                                    ],
                                                    md=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.P(
                                                            "Last Update:",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        html.Div(
                                                            id="last-update-time",
                                                            children="--:--:--",
                                                            style={
                                                                "fontSize": "1.2rem",
                                                                "color": "#17a2b8",
                                                            },
                                                        ),
                                                    ],
                                                    md=6,
                                                ),
                                            ]
                                        ),
                                        html.Hr(),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "▶️  Start Agent",
                                                            id="start-agent-btn",
                                                            color="success",
                                                            className="me-2",
                                                            style={"width": "100%"},
                                                        ),
                                                    ],
                                                    md=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "⏸️  Stop Agent",
                                                            id="stop-agent-btn",
                                                            color="danger",
                                                            style={"width": "100%"},
                                                        ),
                                                    ],
                                                    md=6,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "🔄 Restart Agent",
                                                            id="restart-agent-btn",
                                                            color="warning",
                                                            style={"width": "100%"},
                                                        ),
                                                    ],
                                                    md=12,
                                                ),
                                            ],
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    "Trading Settings",
                                    className="bg-dark",
                                ),
                                dbc.CardBody(
                                    [
                                        html.Div(
                                            [
                                                html.P(
                                                    "Strategy:",
                                                    className="text-secondary font-weight-bold",
                                                ),
                                                dcc.Dropdown(
                                                    id="strategy-selector",
                                                    options=[
                                                        {"label": "RSI", "value": "rsi"},
                                                        {
                                                            "label": "MACD",
                                                            "value": "macd",
                                                        },
                                                        {
                                                            "label": "Combined",
                                                            "value": "combined",
                                                        },
                                                    ],
                                                    value="combined",
                                                    clearable=False,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        html.Div(
                                            [
                                                html.P(
                                                    "Trading Symbols:",
                                                    className="text-secondary font-weight-bold",
                                                ),
                                                dcc.Input(
                                                    id="symbols-input",
                                                    type="text",
                                                    placeholder="BTCUSDT,ETHUSDT",
                                                    value="BTCUSDT",
                                                    className="form-control",
                                                    style={"marginBottom": "0.5rem"},
                                                ),
                                                html.Small(
                                                    "Comma-separated list",
                                                    className="text-muted",
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        html.Div(
                                            [
                                                html.P(
                                                    "Trading Interval (seconds):",
                                                    className="text-secondary font-weight-bold",
                                                ),
                                                dcc.Slider(
                                                    id="interval-slider",
                                                    min=30,
                                                    max=300,
                                                    step=10,
                                                    value=60,
                                                    marks={
                                                        30: "30s",
                                                        60: "60s",
                                                        120: "2m",
                                                        180: "3m",
                                                        300: "5m",
                                                    },
                                                    tooltip={
                                                        "placement": "bottom",
                                                        "always_visible": True,
                                                    },
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        html.Div(
                                            [
                                                html.P(
                                                    "Trade Quantity (BTC):",
                                                    className="text-secondary font-weight-bold",
                                                ),
                                                dcc.Input(
                                                    id="quantity-input",
                                                    type="number",
                                                    placeholder="0.001",
                                                    value=0.001,
                                                    step=0.0001,
                                                    min=0.0001,
                                                    className="form-control",
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Button(
                                            "💾 Apply Settings",
                                            id="apply-settings-btn",
                                            color="info",
                                            style={"width": "100%"},
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ],
                    md=6,
                ),
            ],
            className="mb-4",
        ),
        # Risk Management Settings
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    "Risk Management",
                                    className="bg-dark",
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.P(
                                                            "Max Trades/Hour:",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Input(
                                                            id="max-trades-hour",
                                                            type="number",
                                                            value=100,
                                                            min=1,
                                                            className="form-control",
                                                        ),
                                                    ],
                                                    md=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.P(
                                                            "Max Trades/Day:",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Input(
                                                            id="max-trades-day",
                                                            type="number",
                                                            value=500,
                                                            min=1,
                                                            className="form-control",
                                                        ),
                                                    ],
                                                    md=6,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.P(
                                                            "Max Position Per Symbol (%):",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Slider(
                                                            id="max-position-slider",
                                                            min=1,
                                                            max=50,
                                                            step=1,
                                                            value=10,
                                                            marks={
                                                                1: "1%",
                                                                10: "10%",
                                                                25: "25%",
                                                                50: "50%",
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
                                                    ],
                                                    md=6,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.P(
                                                            "Stop Loss (%):",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Slider(
                                                            id="stop-loss-slider",
                                                            min=0.5,
                                                            max=5,
                                                            step=0.5,
                                                            value=2,
                                                            marks={
                                                                0.5: "0.5%",
                                                                1: "1%",
                                                                2: "2%",
                                                                5: "5%",
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
                                                    ],
                                                    md=6,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.P(
                                                            "Take Profit (%):",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Slider(
                                                            id="take-profit-slider",
                                                            min=1,
                                                            max=20,
                                                            step=1,
                                                            value=5,
                                                            marks={
                                                                1: "1%",
                                                                5: "5%",
                                                                10: "10%",
                                                                20: "20%",
                                                            },
                                                            tooltip={
                                                                "placement": "bottom",
                                                                "always_visible": True,
                                                            },
                                                        ),
                                                    ],
                                                    md=12,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Button(
                                            "🛡️  Save Risk Settings",
                                            id="save-risk-btn",
                                            color="warning",
                                            style={"width": "100%"},
                                        ),
                                    ]
                                ),
                            ]
                        )
                    ],
                    md=12,
                ),
            ],
            className="mb-4",
        ),
        # Agent Activity Log
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    "Recent Activity",
                                    className="bg-dark",
                                ),
                                dbc.CardBody(
                                    [
                                        html.Div(
                                            id="activity-log",
                                            style={
                                                "maxHeight": "300px",
                                                "overflowY": "auto",
                                                "backgroundColor": "#1a1a1a",
                                                "padding": "10px",
                                                "borderRadius": "5px",
                                                "fontFamily": "monospace",
                                                "fontSize": "0.85rem",
                                            },
                                            children=html.Span(
                                                "No activity yet...",
                                                className="text-muted",
                                            ),
                                        )
                                    ]
                                ),
                            ]
                        )
                    ],
                    md=12,
                ),
            ],
        ),
        # Hidden div for storing notification
        dbc.Toast(
            id="automation-toast",
            header="Notification",
            is_open=False,
            dismissable=True,
            icon="info",
            style={"position": "fixed", "top": 20, "right": 20, "width": 350},
        ),
        # Interval for auto-refresh
        dcc.Interval(
            id="automation-interval",
            interval=5000,  # 5 seconds
            n_intervals=0,
        ),
    ],
    fluid=True,
)


# Callbacks for agent control
@callback(
    [
        Output("agent-status-display", "children"),
        Output("last-update-time", "children"),
    ],
    Input("automation-interval", "n_intervals"),
)
def update_agent_status(n):
    """Update agent status display."""
    try:
        from binance_trade_agent.dashboard.utils.data_fetch import get_agent_state

        agent_state = get_agent_state()

        if agent_state["is_running"]:
            status_display = html.Span("🟢 Running", className="text-success")
        else:
            status_display = html.Span("🔴 Stopped", className="text-danger")

        current_time = datetime.now().strftime("%H:%M:%S")
        return status_display, current_time

    except Exception as e:
        return html.Span("⚠️  Error checking status", className="text-warning"), "--:--:--"


@callback(
    [Output("automation-toast", "is_open"), Output("automation-toast", "children")],
    Input("start-agent-btn", "n_clicks"),
    Input("stop-agent-btn", "n_clicks"),
    Input("restart-agent-btn", "n_clicks"),
    Input("apply-settings-btn", "n_clicks"),
    Input("save-risk-btn", "n_clicks"),
    State("strategy-selector", "value"),
    State("symbols-input", "value"),
    State("interval-slider", "value"),
    prevent_initial_call=True,
)
def handle_agent_control(
    start_clicks,
    stop_clicks,
    restart_clicks,
    apply_clicks,
    risk_clicks,
    strategy,
    symbols_str,
    interval,
):
    """Handle agent control button clicks."""
    from dash import callback_context
    from binance_trade_agent.dashboard.utils.data_fetch import (
        start_agent,
        stop_agent,
        restart_agent,
    )

    if not callback_context.triggered:
        raise PreventUpdate

    button_id = callback_context.triggered[0]["prop_id"].split(".")[0]

    try:
        message = ""
        color = "info"
        result = None

        # Parse symbols from comma-separated string
        symbols = [s.strip().upper() for s in (symbols_str or "BTCUSDT").split(",") if s.strip()]

        if button_id == "start-agent-btn":
            result = start_agent(symbols=symbols, interval=interval, strategy=strategy)
            if result["success"]:
                message = f"✅ Agent started successfully with {len(symbols)} symbol(s)"
                color = "success"
            else:
                message = f"❌ Failed to start agent: {result['message']}"
                color = "danger"

        elif button_id == "stop-agent-btn":
            result = stop_agent()
            if result["success"]:
                message = "⏸️  Agent stopped successfully"
                color = "warning"
            else:
                message = f"❌ Failed to stop agent: {result['message']}"
                color = "danger"

        elif button_id == "restart-agent-btn":
            result = restart_agent(symbols=symbols, interval=interval, strategy=strategy)
            if result["success"]:
                message = f"🔄 Agent restarted successfully with {len(symbols)} symbol(s)"
                color = "info"
            else:
                message = f"❌ Failed to restart agent: {result['message']}"
                color = "danger"

        elif button_id == "apply-settings-btn":
            message = "💾 Settings applied (restart agent for changes to take effect)"
            color = "info"

        elif button_id == "save-risk-btn":
            message = "🛡️  Risk settings saved"
            color = "warning"

        else:
            raise PreventUpdate

        return (
            True,
            html.Div(
                [
                    html.H5("✓ Success" if "success" in color else "⚠️ Notice", className="mb-2"),
                    html.P(message, className="mb-0"),
                ],
                style={"color": "white"},
            ),
        )

    except Exception as e:
        return (
            True,
            html.Div(
                [
                    html.H5("❌ Error", className="mb-2"),
                    html.P(f"Error: {str(e)}", className="mb-0"),
                ],
                style={"color": "white"},
            ),
        )
