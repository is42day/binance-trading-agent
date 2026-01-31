"""Performance Analytics Page - Trading performance metrics and history"""

import logging

import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

try:
    from binance_trade_agent.dashboard.components.navbar import create_metric_card
    from binance_trade_agent.dashboard.utils.data_fetch import get_performance_summary, get_trade_history
except Exception as e:
    print(f"Import error: {e}")
    get_performance_summary = None
    get_trade_history = None
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
                            "📊 Performance Analytics",
                            style={"marginTop": "2rem", "color": "#f4f2ee"},
                        ),
                        html.P(
                            "Track win rate, Sharpe ratio, drawdown, and trading history",
                            style={"color": "#b8b4b0"},
                        ),
                    ]
                )
            ],
            className="mb-4",
        ),
        # Key Metrics Row
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4(
                            "📈 Key Performance Metrics",
                            style={"color": "#ff914d", "marginTop": "1rem"},
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
                            id="performance-metrics",
                            children=[
                                dbc.Alert(
                                    "Loading performance metrics...",
                                    color="info",
                                    className="text-center",
                                )
                            ],
                        )
                    ],
                    width=12,
                )
            ],
            className="mb-4",
        ),
        # Risk Metrics Row
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
                            id="risk-metrics-detail",
                            children=[
                                dbc.Alert(
                                    "Loading risk metrics...",
                                    color="info",
                                    className="text-center",
                                )
                            ],
                        )
                    ],
                    width=12,
                )
            ],
            className="mb-4",
        ),
        # Trade Statistics
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4(
                            "🎯 Trade Statistics",
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
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.Div(id="trade-stats"),
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
                                            "Session Info",
                                            className="card-title",
                                            style={"color": "#f4f2ee"},
                                        ),
                                        html.Div(id="session-info"),
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
            ],
            className="mb-4",
        ),
        # Recent Trades
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4(
                            "📋 Recent Trades",
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
                            id="trade-history",
                            children=[
                                dbc.Alert(
                                    "No trades recorded yet",
                                    color="secondary",
                                    className="text-center",
                                )
                            ],
                        )
                    ],
                    width=12,
                )
            ],
            className="mb-4",
        ),
        # Auto-refresh interval
        dcc.Interval(id="performance-timer", interval=30000, n_intervals=0),
    ],
    fluid=True,
    style={"paddingBottom": "3rem"},
)


# Callback for performance metrics
@callback(
    Output("performance-metrics", "children"),
    Input("performance-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_performance_metrics(n_intervals):
    """Update key performance metrics"""
    try:
        if get_performance_summary is None or create_metric_card is None:
            return dbc.Alert("Performance data unavailable", color="warning")

        data = get_performance_summary()

        if isinstance(data, dict) and "error" in data:
            return dbc.Alert(f"Error: {data['error']}", color="danger")

        # Extract metrics
        win_rate = data.get("win_rate", 0)
        profit_factor = data.get("profit_factor", 0)
        total_return = data.get("total_return_pct", 0)
        sharpe = data.get("sharpe_ratio", 0)

        # Determine colors based on values
        win_rate_status = "success" if win_rate >= 50 else "warning" if win_rate >= 40 else "danger"
        pf_status = "success" if profit_factor >= 1.5 else "warning" if profit_factor >= 1 else "danger"
        return_status = "success" if total_return >= 0 else "danger"
        sharpe_status = "success" if sharpe >= 1 else "warning" if sharpe >= 0 else "danger"

        return dbc.Row(
            [
                dbc.Col(
                    [
                        create_metric_card(
                            label="Win Rate",
                            value=f"{win_rate:.1f}%",
                            icon="🎯",
                            status=win_rate_status,
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
                            label="Profit Factor",
                            value=f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞",
                            icon="📊",
                            status=pf_status,
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
                            label="Total Return",
                            value=f"{total_return:+.2f}%",
                            icon="💰",
                            status=return_status,
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
                            label="Sharpe Ratio",
                            value=f"{sharpe:.2f}",
                            icon="📈",
                            status=sharpe_status,
                        )
                    ],
                    lg=3,
                    md=6,
                    xs=12,
                    className="mb-3",
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Performance metrics error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for risk metrics
@callback(
    Output("risk-metrics-detail", "children"),
    Input("performance-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_risk_metrics_detail(n_intervals):
    """Update risk metrics"""
    try:
        if get_performance_summary is None or create_metric_card is None:
            return dbc.Alert("Risk data unavailable", color="warning")

        data = get_performance_summary()

        if isinstance(data, dict) and "error" in data:
            return dbc.Alert(f"Error: {data['error']}", color="danger")

        max_dd = data.get("max_drawdown_pct", 0)
        current_dd = data.get("current_drawdown_pct", 0)
        sortino = data.get("sortino_ratio", 0)
        rr_ratio = data.get("risk_reward_ratio", 0)

        dd_status = "success" if max_dd < 5 else "warning" if max_dd < 10 else "danger"
        current_dd_status = "success" if current_dd < 3 else "warning" if current_dd < 5 else "danger"

        return dbc.Row(
            [
                dbc.Col(
                    [
                        create_metric_card(
                            label="Max Drawdown",
                            value=f"{max_dd:.2f}%",
                            icon="📉",
                            status=dd_status,
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
                            value=f"{current_dd:.2f}%",
                            icon="📊",
                            status=current_dd_status,
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
                            label="Sortino Ratio",
                            value=f"{sortino:.2f}",
                            icon="🛡️",
                            status="success" if sortino >= 1 else "warning",
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
                            label="Risk/Reward",
                            value=f"{rr_ratio:.2f}" if rr_ratio != float('inf') else "∞",
                            icon="⚖️",
                            status="success" if rr_ratio >= 1.5 else "warning",
                        )
                    ],
                    lg=3,
                    md=6,
                    xs=12,
                    className="mb-3",
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Risk metrics error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for trade stats
@callback(
    Output("trade-stats", "children"),
    Input("performance-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_trade_stats(n_intervals):
    """Update trade statistics"""
    try:
        if get_performance_summary is None:
            return html.Div("Trade stats unavailable")

        data = get_performance_summary()

        if isinstance(data, dict) and "error" in data:
            return html.Div(f"Error: {data['error']}")

        total = data.get("total_trades", 0)
        closed = data.get("closed_trades", 0)
        open_pos = data.get("open_positions", 0)
        winning = data.get("winning_trades", 0)
        losing = data.get("losing_trades", 0)
        avg_win = data.get("average_win", 0)
        avg_loss = data.get("average_loss", 0)

        return html.Div(
            [
                html.H5("Trade Counts", style={"color": "#f4f2ee", "marginBottom": "1rem"}),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Total Trades", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"{total}", style={"color": "#f4f2ee", "fontSize": "1.5rem", "fontWeight": "bold"}),
                            ],
                            width=4,
                        ),
                        dbc.Col(
                            [
                                html.Div("Closed", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"{closed}", style={"color": "#f4f2ee", "fontSize": "1.5rem", "fontWeight": "bold"}),
                            ],
                            width=4,
                        ),
                        dbc.Col(
                            [
                                html.Div("Open", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"{open_pos}", style={"color": "#ff914d", "fontSize": "1.5rem", "fontWeight": "bold"}),
                            ],
                            width=4,
                        ),
                    ],
                    className="mb-4",
                ),
                html.Hr(style={"borderColor": "rgba(255, 145, 77, 0.3)"}),
                html.H5("Win/Loss Breakdown", style={"color": "#f4f2ee", "marginBottom": "1rem"}),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Winning", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"{winning}", style={"color": "#4CAF50", "fontSize": "1.5rem", "fontWeight": "bold"}),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                html.Div("Losing", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"{losing}", style={"color": "#f44336", "fontSize": "1.5rem", "fontWeight": "bold"}),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Avg Win", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"${avg_win:,.2f}", style={"color": "#4CAF50", "fontSize": "1.25rem", "fontWeight": "bold"}),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                html.Div("Avg Loss", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"${avg_loss:,.2f}", style={"color": "#f44336", "fontSize": "1.25rem", "fontWeight": "bold"}),
                            ],
                            width=6,
                        ),
                    ],
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Trade stats error: {str(e)}")
        return html.Div(f"Error: {str(e)}")


# Callback for session info
@callback(
    Output("session-info", "children"),
    Input("performance-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_session_info(n_intervals):
    """Update session information"""
    try:
        if get_performance_summary is None:
            return html.Div("Session info unavailable")

        data = get_performance_summary()

        if isinstance(data, dict) and "error" in data:
            return html.Div(f"Error: {data['error']}")

        session_start = data.get("session_start", "N/A")
        session_duration = data.get("session_duration", "N/A")
        initial_capital = data.get("initial_capital", 0)
        current_capital = data.get("current_capital", 0)
        total_pnl = data.get("total_pnl", 0)

        pnl_color = "#4CAF50" if total_pnl >= 0 else "#f44336"

        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Session Start", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(session_start[:19] if len(session_start) > 19 else session_start, 
                                         style={"color": "#f4f2ee", "fontSize": "1rem"}),
                            ],
                            width=12,
                            className="mb-3",
                        ),
                    ],
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Duration", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(session_duration, style={"color": "#ff914d", "fontSize": "1rem"}),
                            ],
                            width=12,
                            className="mb-3",
                        ),
                    ],
                ),
                html.Hr(style={"borderColor": "rgba(255, 145, 77, 0.3)"}),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Initial Capital", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"${initial_capital:,.2f}", style={"color": "#f4f2ee", "fontSize": "1.25rem", "fontWeight": "bold"}),
                            ],
                            width=12,
                            className="mb-3",
                        ),
                    ],
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Current Capital", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"${current_capital:,.2f}", style={"color": "#f4f2ee", "fontSize": "1.25rem", "fontWeight": "bold"}),
                            ],
                            width=12,
                            className="mb-3",
                        ),
                    ],
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Total P&L", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                                html.Div(f"${total_pnl:+,.2f}", style={"color": pnl_color, "fontSize": "1.5rem", "fontWeight": "bold"}),
                            ],
                            width=12,
                        ),
                    ],
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Session info error: {str(e)}")
        return html.Div(f"Error: {str(e)}")


# Callback for trade history
@callback(
    Output("trade-history", "children"),
    Input("performance-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_trade_history(n_intervals):
    """Update trade history table"""
    try:
        if get_trade_history is None:
            return dbc.Alert("Trade history unavailable", color="warning")

        trades = get_trade_history(20)  # Last 20 trades

        if not trades:
            return dbc.Alert(
                [
                    html.Span("📋 "),
                    html.Strong("No trades recorded yet. "),
                    html.Span("Trades will appear here as they are executed."),
                ],
                color="secondary",
                className="text-center",
            )

        # Build table rows
        rows = []
        for trade in trades:
            pnl = trade.get("pnl")
            pnl_pct = trade.get("pnl_pct")
            is_closed = trade.get("is_closed", False)

            pnl_display = f"${pnl:+,.2f}" if pnl else "-"
            pnl_pct_display = f"{pnl_pct:+.2f}%" if pnl_pct else "-"
            pnl_color = "#4CAF50" if (pnl and pnl >= 0) else "#f44336" if pnl else "#888"

            side = trade.get("side", "").upper()
            side_color = "success" if side == "BUY" else "danger"

            rows.append(
                html.Tr(
                    [
                        html.Td(trade.get("symbol", ""), style={"color": "#f4f2ee", "fontWeight": "bold"}),
                        html.Td(
                            dbc.Badge(side, color=side_color),
                        ),
                        html.Td(f"${trade.get('entry_price', 0):,.2f}", style={"color": "#f4f2ee"}),
                        html.Td(
                            f"${trade.get('exit_price', 0):,.2f}" if trade.get("exit_price") else "-",
                            style={"color": "#f4f2ee"},
                        ),
                        html.Td(pnl_display, style={"color": pnl_color, "fontWeight": "bold"}),
                        html.Td(pnl_pct_display, style={"color": pnl_color}),
                        html.Td(
                            dbc.Badge("Closed", color="secondary") if is_closed else dbc.Badge("Open", color="warning"),
                        ),
                        html.Td(
                            trade.get("entry_time", "")[:19] if trade.get("entry_time") else "-",
                            style={"color": "#888", "fontSize": "0.85rem"},
                        ),
                    ],
                    style={"borderBottom": "1px solid rgba(255, 145, 77, 0.1)"},
                )
            )

        table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Symbol", style={"color": "#ff914d"}),
                            html.Th("Side", style={"color": "#ff914d"}),
                            html.Th("Entry", style={"color": "#ff914d"}),
                            html.Th("Exit", style={"color": "#ff914d"}),
                            html.Th("P&L", style={"color": "#ff914d"}),
                            html.Th("P&L %", style={"color": "#ff914d"}),
                            html.Th("Status", style={"color": "#ff914d"}),
                            html.Th("Time", style={"color": "#ff914d"}),
                        ]
                    )
                ),
                html.Tbody(rows),
            ],
            bordered=False,
            hover=True,
            responsive=True,
            striped=False,
            style={"backgroundColor": "#23242a"},
        )

        return dbc.Card(
            dbc.CardBody([table]),
            style={
                "backgroundColor": "#23242a",
                "borderColor": "rgba(255, 145, 77, 0.2)",
            },
        )

    except Exception as e:
        logger.error(f"Trade history error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")
