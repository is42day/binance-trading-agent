"""System Health Page - System status, health metrics, API connectivity"""
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback
import logging

try:
    from binance_trade_agent.dashboard.utils.data_fetch import get_system_status
    from binance_trade_agent.dashboard.components.navbar import create_metric_card
except Exception as e:
    print(f"Import error: {e}")
    get_system_status = None
    create_metric_card = None

logger = logging.getLogger(__name__)

layout = dbc.Container([
    # Header
    dbc.Row([dbc.Col([
        html.H1("🏥 System Health", style={"marginTop": "2rem", "color": "#f4f2ee"}),
        html.P("Real-time system status and performance metrics", style={"color": "#b8b4b0"})
    ])], className="mb-4"),
    
    # Health Metrics
    dbc.Row([dbc.Col([
        html.Div(id="health-metrics", children=[
            dbc.Alert("Loading system health...", color="info", className="text-center")
        ], style={})
    ], width=12)], className="mb-4"),
    
    # System Status Details
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("System Status", className="card-title", style={"color": "#f4f2ee"}),
                    html.Div(id="system-status", style={"minHeight": "250px"})
                ])
            ], style={"backgroundColor": "#23242a", "borderColor": "rgba(255, 145, 77, 0.2)"})
        ], lg=6, md=12),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("API Connectivity", className="card-title", style={"color": "#f4f2ee"}),
                    html.Div(id="api-status", style={"minHeight": "250px"})
                ])
            ], style={"backgroundColor": "#23242a", "borderColor": "rgba(255, 145, 77, 0.2"})
        ], lg=6, md=12)
    ], className="mb-4"),
    
    # Auto-refresh interval
    dcc.Interval(id="health-timer", interval=30000, n_intervals=0)
], fluid=True, style={"paddingBottom": "3rem"})


@callback(
    Output("health-metrics", "children"),
    Input("health-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_health_metrics(n_intervals):
    """Update system health metrics"""
    try:
        if get_system_status is None or create_metric_card is None:
            return dbc.Alert("System health unavailable", color="warning")
        
        health = get_system_status()
        
        if isinstance(health, dict) and "error" in health:
            return dbc.Alert(f"Error: {health['error']}", color="danger")
        
        # Calculate uptime display
        uptime_seconds = health.get("uptime_seconds", 0)
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        # Get status
        status = health.get("status", "unknown")
        status_color = "success" if status == "healthy" else "warning" if status == "degraded" else "danger"
        
        metrics = dbc.Row([
            dbc.Col([
                create_metric_card(
                    label="Uptime",
                    value=uptime_str,
                    icon="⏱️",
                    status="success"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="Trade Error Rate",
                    value=f"{health.get('trade_error_rate', 0):.2f}%",
                    icon="📊",
                    status="success" if health.get("trade_error_rate", 0) < 5 else "warning"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="API Error Rate",
                    value=f"{health.get('api_error_rate', 0):.2f}%",
                    icon="🔌",
                    status="success" if health.get("api_error_rate", 0) < 5 else "warning"
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
            
            dbc.Col([
                create_metric_card(
                    label="Status",
                    value=status.upper(),
                    icon="✓" if status == "healthy" else "⚠️",
                    status=status_color
                )
            ], lg=3, md=6, xs=12, className="mb-3"),
        ])
        
        return metrics
        
    except Exception as e:
        logger.error(f"Health metrics error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


@callback(
    Output("system-status", "children"),
    Input("health-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_system_status(n_intervals):
    """Update system status details"""
    try:
        if get_system_status is None:
            return dbc.Alert("Status unavailable", color="warning")
        
        health = get_system_status()
        
        if isinstance(health, dict) and "error" in health:
            return dbc.Alert(f"Error: {health['error']}", color="danger")
        
        trading_mode = health.get("trading_mode", "demo")
        demo_mode = health.get("demo_mode", True)
        binance_testnet = health.get("binance_testnet", True)
        production_ready = health.get("production_ready", False)
        
        status_items = [
            ("Trading Mode", trading_mode.upper(), "#ff914d"),
            ("Demo Mode", "ON" if demo_mode else "OFF", "#27ae60" if demo_mode else "#e74c3c"),
            ("Binance Testnet", "ON" if binance_testnet else "OFF", "#27ae60" if binance_testnet else "#e74c3c"),
            ("Production Ready", "YES" if production_ready else "NO", "#27ae60" if production_ready else "#e74c3c"),
        ]
        
        status_display = []
        for label, value, color in status_items:
            status_display.append(
                html.Div([
                    html.Span(f"{label}: ", style={"color": "#b8b4b0", "fontSize": "0.875rem"}),
                    html.Span(value, style={"color": color, "fontWeight": "bold", "fontSize": "0.875rem"})
                ], style={"marginBottom": "1rem"})
            )
        
        last_updated = health.get("last_updated", "N/A")
        status_display.append(
            html.Div([
                html.Span("Last Updated: ", style={"color": "#b8b4b0", "fontSize": "0.75rem"}),
                html.Span(last_updated[:19] if last_updated else "N/A", style={"color": "#ff914d", "fontSize": "0.75rem"})
            ], style={"marginTop": "1rem", "paddingTop": "1rem", "borderTop": "1px solid rgba(255, 145, 77, 0.2)"})
        )
        
        return html.Div(status_display)
        
    except Exception as e:
        logger.error(f"System status error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")


@callback(
    Output("api-status", "children"),
    Input("health-timer", "n_intervals"),
    prevent_initial_call=False
)
def update_api_status(n_intervals):
    """Update API connectivity status"""
    try:
        if get_system_status is None:
            return dbc.Alert("API status unavailable", color="warning")
        
        health = get_system_status()
        
        if isinstance(health, dict) and "error" in health:
            return dbc.Alert(f"Error: {health['error']}", color="danger")
        
        # Determine API status based on error rate
        api_error_rate = health.get("api_error_rate", 0)
        trade_error_rate = health.get("trade_error_rate", 0)
        
        api_status = "Connected" if api_error_rate < 10 else "Degraded" if api_error_rate < 50 else "Disconnected"
        trade_status = "OK" if trade_error_rate < 5 else "Issues"
        
        status_color = "#27ae60" if api_status == "Connected" else "#f39c12" if api_status == "Degraded" else "#e74c3c"
        trade_color = "#27ae60" if trade_status == "OK" else "#e74c3c"
        
        status_display = [
            dbc.Alert([
                html.H6("📡 Binance API", style={"marginBottom": "0.5rem"}),
                html.P(f"Status: {api_status}", style={"marginBottom": "0", "fontSize": "0.875rem"}),
                html.P(f"Error Rate: {api_error_rate:.2f}%", style={"marginBottom": "0", "fontSize": "0.875rem", "color": status_color})
            ], color="success" if api_status == "Connected" else "warning" if api_status == "Degraded" else "danger", style={"marginBottom": "1rem"}),
            
            dbc.Alert([
                html.H6("🔄 Trading Engine", style={"marginBottom": "0.5rem"}),
                html.P(f"Status: {trade_status}", style={"marginBottom": "0", "fontSize": "0.875rem"}),
                html.P(f"Error Rate: {trade_error_rate:.2f}%", style={"marginBottom": "0", "fontSize": "0.875rem", "color": trade_color})
            ], color="success" if trade_status == "OK" else "danger")
        ]
        
        return html.Div(status_display)
        
    except Exception as e:
        logger.error(f"API status error: {str(e)}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")
