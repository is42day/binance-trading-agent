"""Paper Trading Dashboard Page - Monitor paper trading performance"""

import logging
import os
from datetime import datetime

import dash_bootstrap_components as dbc
import requests
from dash import Input, Output, callback, dcc, html

logger = logging.getLogger(__name__)

# API base URL - use 'api' hostname in Docker, fallback to localhost for local dev
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")


def fetch_paper_status():
    """Fetch paper trading status from API"""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/paper-trading/status", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch paper status: {e}")
    return None


def fetch_paper_signals(limit=50):
    """Fetch paper trading signals from API"""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/paper-trading/signals?limit={limit}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch paper signals: {e}")
    return {"signals": [], "total": 0}


def fetch_paper_trades(limit=50):
    """Fetch paper trading trades from API"""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/paper-trading/trades?limit={limit}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch paper trades: {e}")
    return {"trades": [], "total": 0}


layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "Paper Trading",
                            style={"marginTop": "2rem", "color": "#f4f2ee"},
                        ),
                        html.P(
                            "Monitor simulated trading with real market data",
                            style={"color": "#b8b4b0"},
                        ),
                    ]
                )
            ],
            className="mb-4",
        ),
        # Auto-refresh
        dcc.Interval(id="paper-trading-timer", interval=5000, n_intervals=0),
        # Status Banner
        html.Div(id="paper-trading-status-banner", className="mb-4"),
        # Portfolio Summary Cards
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Balance", className="text-muted"),
                                    html.H3(
                                        id="paper-balance",
                                        children="$0.00",
                                        style={"color": "#17a2b8"},
                                    ),
                                ]
                            )
                        ],
                        className="bg-dark",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Total P&L", className="text-muted"),
                                    html.H3(
                                        id="paper-pnl",
                                        children="$0.00",
                                    ),
                                ]
                            )
                        ],
                        className="bg-dark",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Win Rate", className="text-muted"),
                                    html.H3(
                                        id="paper-winrate",
                                        children="0%",
                                        style={"color": "#f4f2ee"},
                                    ),
                                ]
                            )
                        ],
                        className="bg-dark",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Total Trades", className="text-muted"),
                                    html.H3(
                                        id="paper-trades",
                                        children="0",
                                        style={"color": "#f4f2ee"},
                                    ),
                                ]
                            )
                        ],
                        className="bg-dark",
                    ),
                    md=3,
                ),
            ],
            className="mb-4",
        ),
        # Second row of stats
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Max Drawdown", className="text-muted"),
                                    html.H3(
                                        id="paper-drawdown",
                                        children="$0.00",
                                        style={"color": "#e74c3c"},
                                    ),
                                ]
                            )
                        ],
                        className="bg-dark",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Open Positions", className="text-muted"),
                                    html.H3(
                                        id="paper-positions",
                                        children="0",
                                        style={"color": "#f4f2ee"},
                                    ),
                                ]
                            )
                        ],
                        className="bg-dark",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Profit Factor", className="text-muted"),
                                    html.H3(
                                        id="paper-profit-factor",
                                        children="0.00",
                                        style={"color": "#f4f2ee"},
                                    ),
                                ]
                            )
                        ],
                        className="bg-dark",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H6("Signals Generated", className="text-muted"),
                                    html.H3(
                                        id="paper-signals",
                                        children="0",
                                        style={"color": "#f4f2ee"},
                                    ),
                                ]
                            )
                        ],
                        className="bg-dark",
                    ),
                    md=3,
                ),
            ],
            className="mb-4",
        ),
        # Trade History and Signals
        dbc.Row(
            [
                # Trade History
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Trade History", className="bg-dark"),
                            dbc.CardBody(
                                html.Div(
                                    id="paper-trade-history",
                                    style={"maxHeight": "400px", "overflowY": "auto"},
                                )
                            ),
                        ],
                        className="bg-dark",
                    ),
                    md=6,
                ),
                # Recent Signals
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Recent Signals", className="bg-dark"),
                            dbc.CardBody(
                                html.Div(
                                    id="paper-signal-history",
                                    style={"maxHeight": "400px", "overflowY": "auto"},
                                )
                            ),
                        ],
                        className="bg-dark",
                    ),
                    md=6,
                ),
            ],
            className="mb-4",
        ),
        # Edge Strategy Details
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Latest Signal Details", className="bg-dark"),
                            dbc.CardBody(
                                html.Div(
                                    id="paper-signal-details",
                                    style={"maxHeight": "300px", "overflowY": "auto"},
                                )
                            ),
                        ],
                        className="bg-dark",
                    ),
                    md=12,
                ),
            ],
        ),
    ],
    fluid=True,
    style={"backgroundColor": "#0d1117", "minHeight": "100vh", "padding": "1rem"},
)


@callback(
    [
        Output("paper-trading-status-banner", "children"),
        Output("paper-balance", "children"),
        Output("paper-pnl", "children"),
        Output("paper-pnl", "style"),
        Output("paper-winrate", "children"),
        Output("paper-trades", "children"),
        Output("paper-drawdown", "children"),
        Output("paper-positions", "children"),
        Output("paper-profit-factor", "children"),
        Output("paper-signals", "children"),
    ],
    Input("paper-trading-timer", "n_intervals"),
)
def update_portfolio_stats(n_intervals):
    """Update portfolio statistics"""
    status = fetch_paper_status()

    if status is None or not status.get("portfolio"):
        banner = dbc.Alert(
            [
                html.Strong("Paper trading not running. "),
                html.Span("Start with: python run_paper_trading.py --strategy combined_edge --balance 100"),
            ],
            color="warning",
        )
        return (
            banner,
            "$0.00",
            "$0.00",
            {"color": "#f4f2ee"},
            "0%",
            "0",
            "$0.00",
            "0",
            "0.00",
            "0",
        )

    portfolio = status.get("portfolio", {})
    active = status.get("active", False)
    last_update = status.get("last_update", "")
    age_seconds = status.get("age_seconds", 0)
    signals_count = status.get("signals_count", 0)

    # Determine status
    try:
        update_time = datetime.fromisoformat(last_update)
        if active:
            banner = dbc.Alert(
                f"Paper trading active - Last update: {update_time.strftime('%H:%M:%S')}",
                color="success",
            )
        else:
            banner = dbc.Alert(
                f"Paper trading idle - Last update: {update_time.strftime('%H:%M:%S')} ({age_seconds}s ago)",
                color="info",
            )
    except Exception:
        banner = dbc.Alert("Paper trading status unknown", color="secondary")

    # Extract stats - use total_value (cash + positions) instead of just cash balance
    balance = portfolio.get("total_value", portfolio.get("current_balance", 0))
    cash_balance = portfolio.get("current_balance", 0)
    positions_value = portfolio.get("positions_value", 0)

    # Use total P&L including unrealized
    pnl = portfolio.get("total_pnl_with_unrealized", portfolio.get("total_pnl", 0))
    unrealized_pnl = portfolio.get("unrealized_pnl", 0)
    initial_balance = portfolio.get("initial_balance", 100)
    pnl_pct = (pnl / initial_balance * 100) if initial_balance > 0 else 0

    win_rate = portfolio.get("win_rate", 0)
    total_trades = portfolio.get("total_trades", 0)
    drawdown = portfolio.get("max_drawdown", 0)
    open_positions = portfolio.get("open_positions", 0)
    profit_factor = portfolio.get("profit_factor", 0)

    # Style for P&L
    pnl_color = "#27ae60" if pnl >= 0 else "#e74c3c"
    pnl_style = {"color": pnl_color}

    return (
        banner,
        f"${balance:,.2f}",
        f"${pnl:+,.2f} ({pnl_pct:+.2f}%)",
        pnl_style,
        f"{win_rate:.1f}%",
        str(total_trades),
        f"${drawdown:,.2f}",
        str(open_positions),
        f"{profit_factor:.2f}",
        str(signals_count),
    )


@callback(
    Output("paper-trade-history", "children"),
    Input("paper-trading-timer", "n_intervals"),
)
def update_trade_history(n_intervals):
    """Update trade history table"""
    data = fetch_paper_trades(limit=20)
    trades = data.get("trades", [])

    if not trades:
        return html.P("No trades yet", className="text-muted text-center")

    rows = []
    for trade in trades[:20]:  # Show last 20
        trade_data = trade.get("trade", {})
        event = trade.get("event", "")

        symbol = trade_data.get("symbol", "")
        side = trade_data.get("side", "")
        entry = trade_data.get("entry_price", 0)
        exit_price = trade_data.get("exit_price")
        pnl = trade_data.get("pnl")

        if event == "OPEN":
            row = html.Tr(
                [
                    html.Td(trade.get("timestamp", "")[:19], className="small"),
                    html.Td(symbol),
                    html.Td(
                        side,
                        style={"color": "#27ae60" if side == "BUY" else "#e74c3c"},
                    ),
                    html.Td(f"${entry:,.2f}"),
                    html.Td("-"),
                    html.Td("-"),
                ],
                style={"backgroundColor": "rgba(39, 174, 96, 0.1)"},
            )
        else:  # CLOSED
            pnl_color = "#27ae60" if pnl and pnl > 0 else "#e74c3c"
            row = html.Tr(
                [
                    html.Td(trade.get("timestamp", "")[:19], className="small"),
                    html.Td(symbol),
                    html.Td("CLOSE"),
                    html.Td(f"${entry:,.2f}"),
                    html.Td(f"${exit_price:,.2f}" if exit_price else "-"),
                    html.Td(
                        f"${pnl:+,.2f}" if pnl else "-",
                        style={"color": pnl_color, "fontWeight": "bold"},
                    ),
                ]
            )
        rows.append(row)

    table = html.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Time"),
                        html.Th("Symbol"),
                        html.Th("Side"),
                        html.Th("Entry"),
                        html.Th("Exit"),
                        html.Th("P&L"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        className="table table-sm table-dark",
    )

    return table


@callback(
    Output("paper-signal-history", "children"),
    Input("paper-trading-timer", "n_intervals"),
)
def update_signal_history(n_intervals):
    """Update signal history"""
    data = fetch_paper_signals(limit=30)
    signals = data.get("signals", [])

    if not signals:
        return html.P("No signals yet", className="text-muted text-center")

    rows = []
    for sig in signals:
        action = sig.get("action", "HOLD")
        confidence = sig.get("confidence", 0)
        executed = sig.get("executed", False)
        rejection = sig.get("rejection_reason")

        # Color based on action
        if action == "BUY":
            action_color = "#27ae60"
        elif action == "SELL":
            action_color = "#e74c3c"
        else:
            action_color = "#6c757d"

        # Execution status
        if executed:
            status = html.Span("EXEC", className="badge bg-success")
        elif rejection:
            status = html.Span("SKIP", className="badge bg-warning text-dark")
        else:
            status = html.Span("HOLD", className="badge bg-secondary")

        row = html.Tr(
            [
                html.Td(sig.get("timestamp", "")[:19], className="small"),
                html.Td(sig.get("symbol", "")),
                html.Td(action, style={"color": action_color, "fontWeight": "bold"}),
                html.Td(f"{confidence:.2f}"),
                html.Td(status),
            ]
        )
        rows.append(row)

    table = html.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Time"),
                        html.Th("Symbol"),
                        html.Th("Action"),
                        html.Th("Conf"),
                        html.Th("Status"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
        className="table table-sm table-dark",
    )

    return table


@callback(
    Output("paper-signal-details", "children"),
    Input("paper-trading-timer", "n_intervals"),
)
def update_signal_details(n_intervals):
    """Show details of the latest signal"""
    data = fetch_paper_signals(limit=1)
    signals = data.get("signals", [])

    if not signals:
        return html.P("No signals yet", className="text-muted text-center")

    sig = signals[0]  # Already newest first from API
    metadata = sig.get("metadata", {})

    details = []

    # Basic info
    details.append(
        dbc.Row(
            [
                dbc.Col(html.Strong("Symbol:"), width=2),
                dbc.Col(sig.get("symbol", ""), width=2),
                dbc.Col(html.Strong("Action:"), width=2),
                dbc.Col(
                    sig.get("action", ""),
                    style={
                        "color": "#27ae60" if sig.get("action") == "BUY" else "#e74c3c"
                    }
                    if sig.get("action") != "HOLD"
                    else {},
                    width=2,
                ),
                dbc.Col(html.Strong("Confidence:"), width=2),
                dbc.Col(f"{sig.get('confidence', 0):.2f}", width=2),
            ],
            className="mb-2",
        )
    )

    # Rejection reason
    if sig.get("rejection_reason"):
        details.append(
            dbc.Alert(
                f"Not executed: {sig.get('rejection_reason')}",
                color="warning",
                className="py-1 px-2 mb-2",
            )
        )

    # Edge factors
    edge_data = metadata.get("edge", {})
    if edge_data:
        factors = edge_data.get("factors", {})

        factor_items = []
        for factor_name, factor_data in factors.items():
            if isinstance(factor_data, dict):
                signal = factor_data.get("signal", "neutral")
                strength = factor_data.get("strength", 0)
                interp = factor_data.get("interpretation", "")
                value = factor_data.get("value", "")

                color = "#27ae60" if signal == "bullish" else "#e74c3c" if signal == "bearish" else "#6c757d"

                factor_items.append(
                    html.Div(
                        [
                            html.Strong(f"{factor_name.replace('_', ' ').title()}: "),
                            html.Span(
                                f"{signal.upper()} ",
                                style={"color": color},
                            ),
                            html.Span(
                                f"(strength: {strength:.2f})" if strength else "",
                                className="text-muted small",
                            ),
                            html.Br(),
                            html.Small(interp or f"Value: {value}", className="text-muted"),
                        ],
                        className="mb-2",
                    )
                )

        if factor_items:
            details.append(
                html.Div(
                    [
                        html.H6("Edge Factors:", className="text-info mt-2"),
                        html.Div(factor_items),
                    ]
                )
            )

    # Entry data
    entry_data = metadata.get("entry", {})
    if entry_data:
        details.append(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Strong("Entry Score: "),
                            html.Span(f"{entry_data.get('score', 0):.2f}"),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Strong("Zone: "),
                            html.Span(entry_data.get("zone", "unknown")),
                        ],
                        width=4,
                    ),
                    dbc.Col(
                        [
                            html.Strong("Volatility Compressed: "),
                            html.Span(
                                "Yes" if entry_data.get("volatility_compressed") else "No"
                            ),
                        ],
                        width=4,
                    ),
                ],
                className="mt-2",
            )
        )

    # TA Confirmations
    ta_data = metadata.get("ta_confirmations", {})
    if ta_data:
        ta_details = ta_data.get("details", {})
        details.append(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Strong("TA Confirmations: "),
                            html.Span(
                                f"Bullish: {ta_data.get('bullish', 0)}, Bearish: {ta_data.get('bearish', 0)}"
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.Small(
                                f"RSI: {ta_details.get('rsi', '-')}, "
                                f"MACD: {ta_details.get('macd', '-')}, "
                                f"BB: {ta_details.get('bollinger', '-')}",
                                className="text-muted",
                            ),
                        ],
                        width=6,
                    ),
                ],
                className="mt-2",
            )
        )

    return html.Div(details)
