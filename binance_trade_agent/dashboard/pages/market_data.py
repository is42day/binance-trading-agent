"""Market Data Page - Real-time price metrics, candlestick charts, technical indicators"""

import logging

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
from dash import Input, Output, callback, dcc, html

try:
    from binance_trade_agent.dashboard.components.navbar import create_metric_card
    from binance_trade_agent.dashboard.utils.data_fetch import (
        get_market_data,
        get_ohlcv_data,
        get_order_book,
    )
except Exception as e:
    print(f"Import error: {e}")
    get_market_data = None
    get_ohlcv_data = None
    get_order_book = None
    create_metric_card = None

logger = logging.getLogger(__name__)

# Default symbol
DEFAULT_SYMBOL = "BTCUSDT"
AVAILABLE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
AVAILABLE_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
DEFAULT_TIMEFRAME = "1h"

layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "💰 Market Data",
                            style={"marginTop": "2rem", "color": "#f4f2ee"},
                        ),
                        html.P(
                            "Real-time price analysis and technical indicators",
                            style={"color": "#b8b4b0"},
                        ),
                    ]
                )
            ],
            className="mb-4",
        ),
        # Controls Row (Symbol + Timeframe)
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Symbol", style={"minWidth": "80px"}),
                                dcc.Dropdown(
                                    id="symbol-selector",
                                    options=[
                                        {"label": sym, "value": sym} for sym in AVAILABLE_SYMBOLS
                                    ],
                                    value=DEFAULT_SYMBOL,
                                    style={"minWidth": "120px"},
                                ),
                            ],
                            className="me-3",
                        )
                    ],
                    width="auto",
                ),
                dbc.Col(
                    [
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Timeframe", style={"minWidth": "100px"}),
                                dcc.Dropdown(
                                    id="timeframe-selector",
                                    options=[
                                        {"label": tf, "value": tf} for tf in AVAILABLE_TIMEFRAMES
                                    ],
                                    value=DEFAULT_TIMEFRAME,
                                    style={"minWidth": "100px"},
                                ),
                            ],
                        )
                    ],
                    width="auto",
                ),
            ],
            className="mb-4",
        ),
        # Price Metrics Cards
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            id="market-metrics",
                            children=[
                                dbc.Alert(
                                    "Loading market data...",
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
        # Main Chart and Market Sentiment
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Price Trend",
                                            className="card-title",
                                            style={"color": "#f4f2ee"},
                                        ),
                                        dcc.Graph(
                                            id="main-chart",
                                            style={"minHeight": "450px"},
                                            config={"displayModeBar": False},
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
                    lg=8,
                    md=12,
                    className="mb-4",
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Market Sentiment",
                                            className="card-title",
                                            style={"color": "#f4f2ee"},
                                        ),
                                        html.Div(id="market-sentiment-content"),
                                    ]
                                )
                            ],
                            style={
                                "backgroundColor": "#23242a",
                                "borderColor": "rgba(255, 145, 77, 0.2)",
                                "height": "100%",
                            },
                        )
                    ],
                    lg=4,
                    md=12,
                    className="mb-4",
                ),
            ],
        ),
        # Technical Summary Row
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Technical Summary",
                                            className="card-title",
                                            style={"color": "#f4f2ee"},
                                        ),
                                        html.Div(id="technical-summary-content"),
                                    ]
                                )
                            ],
                            style={
                                "backgroundColor": "#23242a",
                                "borderColor": "rgba(255, 145, 77, 0.2)",
                            },
                        )
                    ],
                    width=12,
                ),
            ],
            className="mb-4",
        ),
        # Auto-refresh interval (10s)
        dcc.Interval(id="market-timer", interval=10000, n_intervals=0),
    ],
    fluid=True,
    style={"paddingBottom": "3rem"},
)


# Callback for market metrics
@callback(
    Output("market-metrics", "children"),
    Input("symbol-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_market_metrics(symbol, n_intervals):
    """Update market price metrics"""
    try:
        if get_market_data is None or create_metric_card is None:
            return dbc.Alert("Data loading unavailable", color="warning")

        data = get_market_data(symbol)

        if isinstance(data, dict) and "error" in data:
            return dbc.Alert(f"Error: {data['error']}", color="danger")

        # Build metric cards
        metrics = dbc.Row(
            [
                dbc.Col(
                    [
                        create_metric_card(
                            label="Current Price",
                            value=f"${data.get('current_price', 0):,.2f}",
                            icon="💵",
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
                            label="24h Change",
                            value=f"{data.get('price_change_percent', 0):+.2f}%",
                            delta=f"${data.get('price_change', 0):+,.2f}",
                            icon=("📈" if data.get("price_change_percent", 0) >= 0 else "📉"),
                            status=(
                                "success" if data.get("price_change_percent", 0) >= 0 else "danger"
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
                            label="24h Volume",
                            value=f"${data.get('volume_24h', 0):,.0f}",
                            icon="💹",
                            status="info",
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
                            label="High/Low",
                            value=f"${data.get('high_24h', 0):,.2f}",
                            delta=f"L: ${data.get('low_24h', 0):,.2f}",
                            icon="📊",
                            status="warning",
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
        logger.error(f"Market metrics error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for main chart (Price only, simplified)
@callback(
    Output("main-chart", "figure"),
    Input("symbol-selector", "value"),
    Input("timeframe-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_main_chart(symbol, timeframe, n_intervals):
    """Update main chart with Price and SMAs"""
    try:
        if get_ohlcv_data is None:
            return go.Figure().add_annotation(text="Data unavailable")

        # Fetch data
        data = get_ohlcv_data(symbol, interval=timeframe, limit=100)

        if isinstance(data, dict) and "error" in data:
            return go.Figure().add_annotation(text=f"Error: {data['error']}")

        if not data or len(data) == 0:
            return go.Figure().add_annotation(text="No data available")

        df = pd.DataFrame(data)

        # Create simple chart
        fig = go.Figure()

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df["timestamp"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="Price",
                increasing_line_color="#27ae60",
                decreasing_line_color="#e74c3c",
            )
        )

        # SMAs
        if len(df) >= 20:
            sma20 = df["close"].rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=sma20,
                    name="SMA 20",
                    line=dict(color="#3498db", width=1.5),
                )
            )

        if len(df) >= 50:
            sma50 = df["close"].rolling(window=50).mean()
            fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=sma50,
                    name="SMA 50",
                    line=dict(color="#e67e22", width=1.5),
                )
            )

        fig.update_layout(
            template="plotly_dark",
            hovermode="x unified",
            paper_bgcolor="#23242a",
            plot_bgcolor="#23242a",
            font=dict(color="#f4f2ee"),
            margin=dict(l=40, r=40, t=20, b=40),
            height=450,
            xaxis_rangeslider_visible=False,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.05)",
                showgrid=True,
            ),
            yaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.05)",
                showgrid=True,
            ),
        )

        return fig

    except Exception as e:
        logger.error(f"Main chart error: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}")


# Callback for market sentiment (Order Book + Ratio)
@callback(
    Output("market-sentiment-content", "children"),
    Input("symbol-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_market_sentiment(symbol, n_intervals):
    """Update market sentiment display"""
    try:
        if get_order_book is None:
            return dbc.Alert("Data unavailable", color="warning")

        data = get_order_book(symbol, limit=10)

        if isinstance(data, dict) and "error" in data:
            return dbc.Alert(f"Error: {data['error']}", color="danger")

        if not data:
            return dbc.Alert("No data available", color="info")

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        # Calculate pressure
        total_bid_qty = sum([float(x[1]) for x in bids])
        total_ask_qty = sum([float(x[1]) for x in asks])
        total_qty = total_bid_qty + total_ask_qty

        bid_percent = (total_bid_qty / total_qty * 100) if total_qty > 0 else 50
        ask_percent = 100 - bid_percent

        # Sentiment Bar
        sentiment_bar = html.Div(
            [
                html.Div(
                    [
                        html.Span("Buying Pressure", className="float-start text-success small"),
                        html.Span("Selling Pressure", className="float-end text-danger small"),
                    ],
                    className="clearfix mb-1",
                ),
                dbc.Progress(
                    [
                        dbc.Progress(value=bid_percent, color="success", bar=True),
                        dbc.Progress(value=ask_percent, color="danger", bar=True),
                    ],
                    style={"height": "10px", "backgroundColor": "#1a1d23"},
                ),
                html.Div(
                    [
                        html.Span(
                            f"{bid_percent:.1f}%",
                            className="float-start text-success small fw-bold",
                        ),
                        html.Span(
                            f"{ask_percent:.1f}%", className="float-end text-danger small fw-bold"
                        ),
                    ],
                    className="clearfix mt-1 mb-4",
                ),
            ]
        )

        # Top Orders Table
        table_rows = []
        for i in range(min(5, len(bids), len(asks))):
            bid_price = float(bids[i][0])
            bid_qty = float(bids[i][1])
            ask_price = float(asks[i][0])
            ask_qty = float(asks[i][1])

            table_rows.append(
                html.Tr(
                    [
                        html.Td(f"{bid_qty:.4f}", className="text-end text-muted small"),
                        html.Td(
                            f"${bid_price:,.2f}", className="text-end text-success small fw-bold"
                        ),
                        html.Td(
                            f"${ask_price:,.2f}", className="text-end text-danger small fw-bold"
                        ),
                        html.Td(f"{ask_qty:.4f}", className="text-end text-muted small"),
                    ]
                )
            )

        order_table = html.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Qty", className="text-end text-secondary small"),
                            html.Th("Bid", className="text-end text-success small"),
                            html.Th("Ask", className="text-end text-danger small"),
                            html.Th("Qty", className="text-end text-secondary small"),
                        ]
                    )
                ),
                html.Tbody(table_rows),
            ],
            className="table table-sm table-borderless mb-0",
            style={"color": "#b8b4b0"},
        )

        return html.Div([sentiment_bar, order_table])

    except Exception as e:
        logger.error(f"Sentiment error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for Technical Summary
@callback(
    Output("technical-summary-content", "children"),
    Input("symbol-selector", "value"),
    Input("timeframe-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False,
)
def update_technical_summary(symbol, timeframe, n_intervals):
    """Update technical summary"""
    try:
        if get_ohlcv_data is None:
            return dbc.Alert("Data unavailable", color="warning")

        data = get_ohlcv_data(symbol, interval=timeframe, limit=100)

        if isinstance(data, dict) and "error" in data:
            return dbc.Alert(f"Error: {data['error']}", color="danger")

        if not data:
            return dbc.Alert("No data available", color="info")

        df = pd.DataFrame(data)

        # Calculate Indicators
        current_price = df["close"].iloc[-1]

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # SMAs
        sma20 = df["close"].rolling(window=20).mean().iloc[-1]
        sma50 = df["close"].rolling(window=50).mean().iloc[-1]

        # Determine Trend
        trend = "NEUTRAL"
        trend_color = "warning"
        if current_price > sma20 > sma50:
            trend = "BULLISH"
            trend_color = "success"
        elif current_price < sma20 < sma50:
            trend = "BEARISH"
            trend_color = "danger"

        # RSI Status
        rsi_status = "NEUTRAL"
        rsi_color = "info"
        if current_rsi > 70:
            rsi_status = "OVERBOUGHT"
            rsi_color = "danger"
        elif current_rsi < 30:
            rsi_status = "OVERSOLD"
            rsi_color = "success"

        # Build Cards
        return dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H6("Market Trend", className="text-muted mb-2"),
                                html.H3(trend, className=f"text-{trend_color} mb-0"),
                                html.Small("Price vs SMA20/50", className="text-muted"),
                            ],
                            className="text-center p-3 border rounded border-secondary bg-dark",
                        )
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H6("RSI (14)", className="text-muted mb-2"),
                                html.H3(f"{current_rsi:.1f}", className=f"text-{rsi_color} mb-0"),
                                html.Small(rsi_status, className=f"text-{rsi_color}"),
                            ],
                            className="text-center p-3 border rounded border-secondary bg-dark",
                        )
                    ],
                    width=4,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H6("Volatility (24h)", className="text-muted mb-2"),
                                html.H3(
                                    f"{(df['high'].max() - df['low'].min()) / df['low'].min() * 100:.1f}%",
                                    className="text-info mb-0",
                                ),
                                html.Small("High/Low Range", className="text-muted"),
                            ],
                            className="text-center p-3 border rounded border-secondary bg-dark",
                        )
                    ],
                    width=4,
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Technical summary error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")
