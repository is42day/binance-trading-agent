"""Market Data Page - Real-time price metrics, candlestick charts, technical indicators"""
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback, State
import plotly.graph_objs as go
import logging
import pandas as pd

try:
    from binance_trade_agent.dashboard.utils.data_fetch import (
        get_market_data, get_ohlcv_data, get_order_book
    )
    from binance_trade_agent.dashboard.components.navbar import create_metric_card
except Exception as e:
    print(f"Import error: {e}")
    get_market_data = None
    get_ohlcv_data = None
    get_order_book = None
    create_metric_card = None

logger = logging.getLogger(__name__)

# Default symbol
DEFAULT_SYMBOL = 'BTCUSDT'
AVAILABLE_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']

layout = dbc.Container([
    # Header
    dbc.Row([dbc.Col([
        html.H1("💰 Market Data", style={"marginTop": "2rem", "color": "#f4f2ee"}),
        html.P("Real-time price analysis and technical indicators", style={"color": "#b8b4b0"})
    ])], className="mb-4"),
    
    # Symbol Selector
    dbc.Row([dbc.Col([
        dbc.InputGroup([
            dbc.InputGroupText("Symbol", style={"minWidth": "80px"}),
            dcc.Dropdown(
                id="symbol-selector",
                options=[{"label": sym, "value": sym} for sym in AVAILABLE_SYMBOLS],
                value=DEFAULT_SYMBOL,
                style={"minWidth": "150px"}
            ),
        ], style={"maxWidth": "300px"})
    ], width=12)], className="mb-4"),
    
    # Price Metrics Cards
    dbc.Row([dbc.Col([
        html.Div(id="market-metrics", children=[
            dbc.Alert("Loading market data...", color="info", className="text-center")
        ])
    ], width=12)], className="mb-4"),
    
    # Charts Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Price Chart (1h)", className="card-title", style={"color": "#f4f2ee"}),
                    dcc.Graph(id="candlestick-chart", style={"minHeight": "400px"})
                ])
            ], style={"backgroundColor": "#23242a", "borderColor": "rgba(255, 145, 77, 0.2)"})
        ], lg=8, md=12),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Order Book", className="card-title", style={"color": "#f4f2ee"}),
                    html.Div(id="order-book-table", style={"maxHeight": "400px", "overflowY": "auto"})
                ])
            ], style={"backgroundColor": "#23242a", "borderColor": "rgba(255, 145, 77, 0.2"})
        ], lg=4, md=12)
    ], className="mb-4"),
    
    # Volume and Indicators Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Volume (24h)", className="card-title", style={"color": "#f4f2ee"}),
                    dcc.Graph(id="volume-chart", style={"minHeight": "300px"})
                ])
            ], style={"backgroundColor": "#23242a", "borderColor": "rgba(255, 145, 77, 0.2)"})
        ], lg=6, md=12),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("RSI (14)", className="card-title", style={"color": "#f4f2ee"}),
                    dcc.Graph(id="rsi-chart", style={"minHeight": "300px"})
                ])
            ], style={"backgroundColor": "#23242a", "borderColor": "rgba(255, 145, 77, 0.2)"})
        ], lg=6, md=12)
    ], className="mb-4"),
    
    # Auto-refresh interval
    dcc.Interval(id="market-timer", interval=60000, n_intervals=0)
], fluid=True, style={"paddingBottom": "3rem"})


# Callback for market metrics
@callback(
    Output("market-metrics", "children"),
    Input("symbol-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False
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
        metrics = dbc.Row([
            dbc.Col([
                create_metric_card(
                    label="Current Price",
                    value=f"${data.get('current_price', 0):,.2f}",
                    icon="💵",
                    status="primary"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="24h Change",
                    value=f"{data.get('price_change_percent', 0):+.2f}%",
                    delta=f"${data.get('price_change', 0):+,.2f}",
                    icon="📈" if data.get('price_change_percent', 0) >= 0 else "📉",
                    status="success" if data.get("price_change_percent", 0) >= 0 else "danger"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="24h Volume",
                    value=f"${data.get('volume_24h', 0):,.0f}",
                    icon="💹",
                    status="info"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="High/Low",
                    value=f"${data.get('high_24h', 0):,.2f}",
                    delta=f"L: ${data.get('low_24h', 0):,.2f}",
                    icon="📊",
                    status="warning"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
        ])
        
        return metrics
        
    except Exception as e:
        logger.error(f"Market metrics error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for candlestick chart
@callback(
    Output("candlestick-chart", "figure"),
    Input("symbol-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_candlestick(symbol, n_intervals):
    """Update candlestick chart"""
    try:
        if get_ohlcv_data is None:
            return go.Figure().add_annotation(text="Data unavailable")
        
        data = get_ohlcv_data(symbol, interval='1h', limit=48)
        
        if isinstance(data, dict) and "error" in data:
            return go.Figure().add_annotation(text=f"Error: {data['error']}")
        
        if not data or len(data) == 0:
            return go.Figure().add_annotation(text="No data available")
        
        df = pd.DataFrame(data)
        
        # Create candlestick chart with SMA
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC',
            hovertemplate='<b>%{x}</b><br>O: $%{open:.2f}<br>H: $%{high:.2f}<br>L: $%{low:.2f}<br>C: $%{close:.2f}',
            increasing_line_color='#27ae60',
            decreasing_line_color='#e74c3c'
        ))
        
        # Add SMA20 and SMA50
        if len(df) >= 20:
            sma20 = df['close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=sma20,
                name='SMA20',
                line=dict(color='#3498db', width=2),
                hovertemplate='SMA20: $%{y:.2f}'
            ))
        
        if len(df) >= 50:
            sma50 = df['close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=sma50,
                name='SMA50',
                line=dict(color='#e67e22', width=2),
                hovertemplate='SMA50: $%{y:.2f}'
            ))
        
        fig.update_layout(
            title=f"{symbol} Price Chart (1h) - Last 48 Hours",
            yaxis_title="Price (USDT)",
            xaxis_title="Time",
            template="plotly_dark",
            hovermode="x unified",
            paper_bgcolor='#1a1d23',
            plot_bgcolor='#23242a',
            font=dict(color='#f4f2ee'),
            xaxis=dict(gridcolor='rgba(255, 145, 77, 0.1)'),
            yaxis=dict(gridcolor='rgba(255, 145, 77, 0.1)'),
            height=400
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Candlestick error: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}")


# Callback for order book
@callback(
    Output("order-book-table", "children"),
    Input("symbol-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_order_book(symbol, n_intervals):
    """Update order book table"""
    try:
        if get_order_book is None:
            return dbc.Alert("Order book unavailable", color="warning")
        
        data = get_order_book(symbol, limit=10)
        
        if isinstance(data, dict) and "error" in data:
            return dbc.Alert(f"Error: {data['error']}", color="danger")
        
        if not data:
            return dbc.Alert("No order book data", color="info")
        
        # Separate bids and asks
        bids = data.get('bids', [])
        asks = data.get('asks', [])
        
        # Build table
        table_rows = []
        
        # Add header
        table_rows.append(
            html.Tr([
                html.Th("Bid Price", style={"color": "#27ae60", "textAlign": "right"}),
                html.Th("Bid Qty", style={"color": "#27ae60", "textAlign": "right"}),
                html.Th(" ", style={"textAlign": "center"}),
                html.Th("Ask Price", style={"color": "#e74c3c", "textAlign": "right"}),
                html.Th("Ask Qty", style={"color": "#e74c3c", "textAlign": "right"}),
            ])
        )
        
        # Add bids and asks
        max_rows = max(len(bids), len(asks))
        for i in range(max_rows):
            bid_price = f"${bids[i][0]:,.2f}" if i < len(bids) else ""
            bid_qty = f"{bids[i][1]:.4f}" if i < len(bids) else ""
            ask_price = f"${asks[i][0]:,.2f}" if i < len(asks) else ""
            ask_qty = f"{asks[i][1]:.4f}" if i < len(asks) else ""
            
            table_rows.append(
                html.Tr([
                    html.Td(bid_price, style={"color": "#27ae60", "textAlign": "right", "fontSize": "0.875rem"}),
                    html.Td(bid_qty, style={"color": "#27ae60", "textAlign": "right", "fontSize": "0.875rem"}),
                    html.Td("", style={"textAlign": "center"}),
                    html.Td(ask_price, style={"color": "#e74c3c", "textAlign": "right", "fontSize": "0.875rem"}),
                    html.Td(ask_qty, style={"color": "#e74c3c", "textAlign": "right", "fontSize": "0.875rem"}),
                ])
            )
        
        return html.Table(
            table_rows,
            style={
                "width": "100%",
                "borderCollapse": "collapse",
                "fontSize": "0.875rem"
            }
        )
        
    except Exception as e:
        logger.error(f"Order book error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


# Callback for volume chart
@callback(
    Output("volume-chart", "figure"),
    Input("symbol-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_volume_chart(symbol, n_intervals):
    """Update volume chart"""
    try:
        if get_ohlcv_data is None:
            return go.Figure().add_annotation(text="Data unavailable")
        
        data = get_ohlcv_data(symbol, interval='1h', limit=48)
        
        if isinstance(data, dict) and "error" in data:
            return go.Figure().add_annotation(text=f"Error: {data['error']}")
        
        if not data:
            return go.Figure().add_annotation(text="No data available")
        
        df = pd.DataFrame(data)
        
        fig = go.Figure()
        
        # Color bars based on price movement
        colors = ['#27ae60' if (df['close'].iloc[i] >= df['open'].iloc[i]) else '#e74c3c' 
                  for i in range(len(df))]
        
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volume',
            marker=dict(color=colors),
            hovertemplate='<b>%{x}</b><br>Volume: %{y:.0f}'
        ))
        
        fig.update_layout(
            title="Trading Volume (24h)",
            yaxis_title="Volume",
            xaxis_title="Time",
            template="plotly_dark",
            hovermode="x",
            paper_bgcolor='#1a1d23',
            plot_bgcolor='#23242a',
            font=dict(color='#f4f2ee'),
            xaxis=dict(gridcolor='rgba(255, 145, 77, 0.1)'),
            yaxis=dict(gridcolor='rgba(255, 145, 77, 0.1)'),
            height=300,
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Volume chart error: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}")


# Callback for RSI chart
@callback(
    Output("rsi-chart", "figure"),
    Input("symbol-selector", "value"),
    Input("market-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_rsi_chart(symbol, n_intervals):
    """Update RSI chart"""
    try:
        if get_ohlcv_data is None:
            return go.Figure().add_annotation(text="Data unavailable")
        
        data = get_ohlcv_data(symbol, interval='1h', limit=48)
        
        if isinstance(data, dict) and "error" in data:
            return go.Figure().add_annotation(text=f"Error: {data['error']}")
        
        if not data:
            return go.Figure().add_annotation(text="No data available")
        
        df = pd.DataFrame(data)
        
        # Calculate RSI (14 period)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=rsi,
            name='RSI(14)',
            line=dict(color='#3498db', width=2),
            fill='tozeroy',
            fillcolor='rgba(52, 152, 219, 0.2)',
            hovertemplate='<b>%{x}</b><br>RSI: %{y:.2f}'
        ))
        
        # Add overbought/oversold levels
        fig.add_hline(y=70, line_dash="dash", line_color="#e74c3c", 
                     annotation_text="Overbought (70)", annotation_position="right")
        fig.add_hline(y=30, line_dash="dash", line_color="#27ae60",
                     annotation_text="Oversold (30)", annotation_position="right")
        
        fig.update_layout(
            title="Relative Strength Index (14)",
            yaxis_title="RSI",
            xaxis_title="Time",
            yaxis=dict(range=[0, 100], gridcolor='rgba(255, 145, 77, 0.1)'),
            template="plotly_dark",
            hovermode="x",
            paper_bgcolor='#1a1d23',
            plot_bgcolor='#23242a',
            font=dict(color='#f4f2ee'),
            xaxis=dict(gridcolor='rgba(255, 145, 77, 0.1)'),
            height=300,
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"RSI chart error: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}")
