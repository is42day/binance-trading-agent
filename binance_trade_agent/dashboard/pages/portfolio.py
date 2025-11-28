"""Portfolio Page - Real-time portfolio overview"""
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback
import logging

try:
    from binance_trade_agent.dashboard import api_client
    from binance_trade_agent.dashboard.components.navbar import create_metric_card
except Exception as e:
    print(f"Import error: {e}")
    get_portfolio_data = None
    create_metric_card = None

logger = logging.getLogger(__name__)

layout = dbc.Container([
    dbc.Row([dbc.Col([
        html.H1("📊 Portfolio Overview", style={"marginTop": "2rem", "color": "#f4f2ee"}),
        html.P("Real-time position tracking and P&L analysis", style={"color": "#b8b4b0"})
    ])], className="mb-4"),
    
    dbc.Row([dbc.Col([
        html.Div(id="portfolio-metrics", children=[
            dbc.Alert("Loading portfolio data...", color="info", className="text-center")
        ], style={})
    ], width=12)]),
    
    dbc.Row([dbc.Col([
        html.Div(id="portfolio-trades", children=[
            dbc.Alert("Loading recent trades...", color="info", className="text-center")
        ], style={})
    ], width=12, className="mt-5")]),
    
    dcc.Interval(id="portfolio-timer", interval=30000, n_intervals=0)
], fluid=True, style={"paddingBottom": "3rem"})


@callback(
    Output("portfolio-metrics", "children"),
    Input("portfolio-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_metrics(n_intervals):
    """Update portfolio metrics display"""
    try:
        data = api_client.get_portfolio_summary()
        
        if "error" in data:
            logger.error(f"API Error: {data['error']}")
            return dbc.Alert(f"API Error: {data['error']}", color="danger")

        # Calculate P&L percentage
        total_value = data.get('total_value', 0)
        total_pnl = data.get('total_pnl', 0)
        initial_capital = total_value - total_pnl
        pnl_percent = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0

        # Build metric cards
        cards = dbc.Row([
            dbc.Col([
                create_metric_card(
                    label="Total Value",
                    value=f"${total_value:,.2f}",
                    icon="💰",
                    status="primary"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="Total P&L",
                    value=f"${total_pnl:,.2f}",
                    delta=f"{pnl_percent:+.2f}%",
                    icon="📊",
                    status="success" if total_pnl >= 0 else "danger"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="Open Positions",
                    value=str(data.get("positions_count", 0)),
                    icon="📍",
                    status="info"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="Total Trades",
                    value=str(data.get("number_of_trades", 0)),
                    icon="📈",
                    status="warning"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
        ])
        
        return cards
        
    except Exception as e:
        logger.error(f"Portfolio update error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


@callback(
    Output("portfolio-trades", "children"),
    Input("portfolio-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_trades(n_intervals):
    """Update recent trades display"""
    try:
        trades = api_client.get_trade_history(limit=20)
        
        if not trades:
            return dbc.Alert("No trades yet", color="info", className="text-center")
        
        # Build trades table
        rows = []
        for trade in trades:
            action = trade.get('action', 'N/A').upper()
            action_color = "success" if action == "BUY" else "danger" if action == "SELL" else "secondary"
            action_icon = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⚪"
            
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            total = quantity * price
            
            rows.append(html.Tr([
                html.Td(trade.get('timestamp', 'N/A'), className="text-secondary", style={"fontSize": "0.85rem"}),
                html.Td(trade.get('symbol', 'N/A'), className="text-primary font-weight-bold"),
                html.Td(f"{action_icon} {action}", className=f"text-{action_color} font-weight-bold"),
                html.Td(f"{quantity:.6f}", className="text-muted", style={"textAlign": "right"}),
                html.Td(f"${price:,.2f}", className="text-muted", style={"textAlign": "right"}),
                html.Td(f"${total:,.2f}", className="text-success font-weight-bold", style={"textAlign": "right"}),
            ]))
        
        table = dbc.Card([
            dbc.CardHeader(
                html.H5("📜 Recent Trades (Last 20)", className="mb-0"),
                className="bg-dark"
            ),
            dbc.CardBody([
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("Timestamp", style={"width": "20%"}),
                        html.Th("Symbol", style={"width": "15%"}),
                        html.Th("Action", style={"width": "15%"}),
                        html.Th("Quantity", style={"width": "15%", "textAlign": "right"}),
                        html.Th("Price", style={"width": "15%", "textAlign": "right"}),
                        html.Th("Total", style={"width": "20%", "textAlign": "right"}),
                    ])),
                    html.Tbody(rows)
                ], dark=True, hover=True, responsive=True, className="mb-0")
            ])
        ])
        
        return table
        
    except Exception as e:
        logger.error(f"Trades update error: {str(e)}")
        return dbc.Alert(f"Error loading trades: {str(e)}", color="danger")
