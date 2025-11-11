"""Portfolio Page - Real-time portfolio overview"""
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback
import logging

try:
    from binance_trade_agent.dashboard.utils.data_fetch import get_portfolio_data
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
        if get_portfolio_data is None or create_metric_card is None:
            logger.warning("Data fetch functions not available")
            return dbc.Alert("Data loading unavailable", color="warning")
        
        try:
            data = get_portfolio_data()
        except Exception as fetch_err:
            logger.error(f"Failed to fetch portfolio data: {fetch_err}")
            return dbc.Alert(f"Failed to fetch data: {str(fetch_err)[:100]}", color="danger")
        
        if isinstance(data, dict) and "error" in data:
            logger.error(f"Data error: {data['error']}")
            return dbc.Alert(f"Error: {data['error']}", color="danger")
        
        # Build metric cards
        cards = dbc.Row([
            dbc.Col([
                create_metric_card(
                    label="Total Value",
                    value=f"${data.get('total_value', 0):,.2f}",
                    icon="💰",
                    status="primary"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="Total P&L",
                    value=f"${data.get('total_pnl', 0):,.2f}",
                    delta=f"{data.get('total_pnl_percent', 0):+.2f}%",
                    icon="📊",
                    status="success" if data.get("total_pnl", 0) >= 0 else "danger"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="Open Positions",
                    value=str(data.get("open_positions", 0)),
                    icon="📍",
                    status="info"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="Total Trades",
                    value=str(data.get("total_trades", 0)),
                    icon="📈",
                    status="warning"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
        ])
        
        return cards
        
    except Exception as e:
        logger.error(f"Portfolio update error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")
