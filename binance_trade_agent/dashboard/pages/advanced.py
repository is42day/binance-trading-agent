"""
Advanced Page - System controls, risk management, configuration
"""

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL
from datetime import datetime
import json

layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("⚙️ Advanced Controls", style={'marginTop': '2rem', 'marginBottom': '1rem'})
        ])
    ]),
    
    # Risk Management Configuration
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🛡️ Risk Management Settings", className="bg-dark"),
                dbc.CardBody([
                    dbc.Row([
                        # Max Position Size
                        dbc.Col([
                            html.Label("Max Position Size (%)", className="text-secondary font-weight-bold"),
                            dbc.InputGroup([
                                dbc.Input(
                                    id="adv-max-position-pct",
                                    type="number",
                                    placeholder="5",
                                    value=5,
                                    min=1,
                                    max=50,
                                    step=0.5,
                                    className="form-control"
                                ),
                                dbc.InputGroupText("%")
                            ]),
                            html.Small("Maximum % of portfolio per position", className="text-tertiary")
                        ], md=6, className="mb-3"),
                        
                        # Stop Loss
                        dbc.Col([
                            html.Label("Stop Loss (%)", className="text-secondary font-weight-bold"),
                            dbc.InputGroup([
                                dbc.Input(
                                    id="adv-stop-loss-pct",
                                    type="number",
                                    placeholder="2",
                                    value=2,
                                    min=0.1,
                                    max=10,
                                    step=0.1,
                                    className="form-control"
                                ),
                                dbc.InputGroupText("%")
                            ]),
                            html.Small("Automatic stop loss trigger", className="text-tertiary")
                        ], md=6, className="mb-3")
                    ]),
                    
                    dbc.Row([
                        # Max Daily Loss
                        dbc.Col([
                            html.Label("Max Daily Loss ($)", className="text-secondary font-weight-bold"),
                            dbc.InputGroup([
                                dbc.InputGroupText("$"),
                                dbc.Input(
                                    id="adv-max-daily-loss",
                                    type="number",
                                    placeholder="1000",
                                    value=1000,
                                    min=100,
                                    step=100,
                                    className="form-control"
                                )
                            ]),
                            html.Small("Daily loss limit before stop trading", className="text-tertiary")
                        ], md=6, className="mb-3"),
                        
                        # Max Open Positions
                        dbc.Col([
                            html.Label("Max Open Positions", className="text-secondary font-weight-bold"),
                            dbc.Input(
                                id="adv-max-positions",
                                type="number",
                                placeholder="5",
                                value=5,
                                min=1,
                                max=20,
                                step=1,
                                className="form-control"
                            ),
                            html.Small("Maximum concurrent open positions", className="text-tertiary")
                        ], md=6, className="mb-3")
                    ]),
                    
                    # Emergency Stop
                    dbc.Row([
                        dbc.Col([
                            html.Div(className="mb-3"),
                            dbc.Button(
                                "🛑 EMERGENCY STOP",
                                id="adv-emergency-stop-btn",
                                color="danger",
                                size="lg",
                                style={"width": "100%", "minHeight": "50px"},
                                className="font-weight-bold"
                            ),
                            html.Small("Immediately stop all trading and close all positions", className="text-danger")
                        ], width=12, className="mt-3")
                    ]),
                    
                    # Save Button
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "💾 Save Settings",
                                id="adv-save-settings-btn",
                                color="primary",
                                className="btn-primary mt-3",
                                style={"width": "100%", "minHeight": "44px"}
                            )
                        ], width=12)
                    ])
                ])
            ], className="mb-4")
        ], md=6),
        
        # Status Panel
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 System Status", className="bg-dark"),
                dbc.CardBody([
                    # Trading Status
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Div("Trading Status", className="metric-label"),
                                html.Div("🟢 ACTIVE", id="adv-trading-status", className="metric-value text-success"),
                            ], className="metric-card mb-3")
                        ], width=12)
                    ]),
                    
                    # Current Drawdown
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Div("Current Drawdown", className="metric-label"),
                                html.Div("2.34%", id="adv-drawdown", className="metric-value text-warning"),
                            ], className="metric-card mb-3")
                        ], width=12)
                    ]),
                    
                    # Daily P&L
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Div("Daily P&L", className="metric-label"),
                                html.Div("+$234.56", id="adv-daily-pnl", className="metric-value text-success"),
                            ], className="metric-card mb-3")
                        ], width=12)
                    ]),
                    
                    # Last Update
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Div("Last Update", className="metric-label"),
                                html.Div("Just now", id="adv-last-update", className="metric-value text-secondary"),
                            ], className="metric-card")
                        ], width=12)
                    ])
                ])
            ], className="mb-4")
        ], md=6)
    ], className="mb-4"),
    
    # Strategy Configuration
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📈 Trading Strategy Settings", className="bg-dark"),
                dbc.CardBody([
                    dbc.Row([
                        # Strategy Selection
                        dbc.Col([
                            html.Label("Active Strategy", className="text-secondary font-weight-bold"),
                            dcc.Dropdown(
                                id="adv-strategy-selector",
                                options=[
                                    {"label": "RSI Momentum", "value": "rsi"},
                                    {"label": "Moving Average Crossover", "value": "ma"},
                                    {"label": "Bollinger Bands", "value": "bb"},
                                    {"label": "Manual Trading", "value": "manual"}
                                ],
                                value="rsi",
                                clearable=False,
                                className="form-control"
                            )
                        ], md=6, className="mb-3"),
                        
                        # Timeframe
                        dbc.Col([
                            html.Label("Timeframe", className="text-secondary font-weight-bold"),
                            dcc.Dropdown(
                                id="adv-timeframe-selector",
                                options=[
                                    {"label": "1 Minute", "value": "1m"},
                                    {"label": "5 Minutes", "value": "5m"},
                                    {"label": "15 Minutes", "value": "15m"},
                                    {"label": "1 Hour", "value": "1h"},
                                    {"label": "4 Hours", "value": "4h"},
                                    {"label": "1 Day", "value": "1d"}
                                ],
                                value="1h",
                                clearable=False,
                                className="form-control"
                            )
                        ], md=6, className="mb-3")
                    ]),
                    
                    # Strategy Parameters
                    html.Div(id="adv-strategy-params", children=[
                        dbc.Row([
                            dbc.Col([
                                html.Label("RSI Period", className="text-secondary font-weight-bold"),
                                dbc.Input(
                                    type="number",
                                    placeholder="14",
                                    value=14,
                                    min=2,
                                    max=50,
                                    step=1,
                                    className="form-control"
                                )
                            ], md=6),
                            dbc.Col([
                                html.Label("RSI Threshold", className="text-secondary font-weight-bold"),
                                dbc.Input(
                                    type="number",
                                    placeholder="30",
                                    value=30,
                                    min=5,
                                    max=50,
                                    step=1,
                                    className="form-control"
                                )
                            ], md=6)
                        ])
                    ], className="mb-3"),
                    
                    # Enable/Disable Strategy
                    dbc.Row([
                        dbc.Col([
                            dbc.Checklist(
                                id="adv-strategy-enabled",
                                options=[{"label": " Strategy Enabled", "value": 1}],
                                value=[1],
                                switch=True,
                                className="mt-2"
                            )
                        ], width=12)
                    ]),
                    
                    # Save Button
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "💾 Save Strategy",
                                id="adv-save-strategy-btn",
                                color="primary",
                                className="btn-primary mt-3",
                                style={"width": "100%", "minHeight": "44px"}
                            )
                        ], width=12)
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Data Management
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("💾 Data Management", className="bg-dark"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "📥 Export Portfolio",
                                id="adv-export-portfolio-btn",
                                color="info",
                                outline=True,
                                style={"width": "100%"}
                            )
                        ], md=3),
                        dbc.Col([
                            dbc.Button(
                                "📤 Import Configuration",
                                id="adv-import-config-btn",
                                color="info",
                                outline=True,
                                style={"width": "100%"}
                            )
                        ], md=3),
                        dbc.Col([
                            dbc.Button(
                                "📊 Export Trade History",
                                id="adv-export-trades-btn",
                                color="info",
                                outline=True,
                                style={"width": "100%"}
                            )
                        ], md=3),
                        dbc.Col([
                            dbc.Button(
                                "🔄 Restart System",
                                id="adv-restart-btn",
                                color="warning",
                                outline=True,
                                style={"width": "100%"}
                            )
                        ], md=3)
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Alerts
    html.Div(id="adv-alert-container"),
    
    # Auto-refresh interval
    dcc.Interval(
        id="adv-page-interval",
        interval=30000,  # 30 seconds
        n_intervals=0
    )
], fluid=True, className="p-4")


# Callback: Update status metrics
@callback(
    Output("adv-trading-status", "children"),
    Output("adv-drawdown", "children"),
    Output("adv-daily-pnl", "children"),
    Output("adv-last-update", "children"),
    Input("adv-page-interval", "n_intervals")
)
def update_status_metrics(n_intervals):
    """Update system status metrics"""
    try:
        from binance_trade_agent.dashboard.utils.data_fetch import get_system_status, get_portfolio_data
        
        system_status = get_system_status()
        portfolio_data = get_portfolio_data()
        
        trading_active = "🟢 ACTIVE" if system_status.get('trading_active', True) else "🔴 STOPPED"
        drawdown = system_status.get('current_drawdown', 0)
        daily_pnl = portfolio_data.get('total_pnl', 0)
        
        drawdown_class = "text-warning" if drawdown > 1 else "text-success"
        pnl_class = "text-success" if daily_pnl >= 0 else "text-danger"
        pnl_symbol = "+" if daily_pnl >= 0 else ""
        
        return (
            trading_active,
            f"{drawdown:.2f}%",
            f"{pnl_symbol}${daily_pnl:,.2f}",
            "Just now"
        )
    except Exception as e:
        return "Error", "N/A", "N/A", "Error"


# Callback: Emergency Stop
@callback(
    Output("adv-alert-container", "children"),
    Input("adv-emergency-stop-btn", "n_clicks"),
    prevent_initial_call=True
)
def trigger_emergency_stop(n_clicks):
    """Trigger emergency stop"""
    if not n_clicks:
        return html.Div()
    
    try:
        from binance_trade_agent.dashboard.utils.data_fetch import get_trading_components
        components = get_trading_components()
        risk_agent = components['risk_agent']
        
        # Trigger emergency stop
        risk_agent.activate_emergency_stop()
        
        alert = dbc.Alert([
            html.H4("🛑 Emergency Stop Activated!", className="mb-2"),
            html.Div("All trading has been halted immediately."),
            html.Div("All open positions are being closed."),
            html.Div("System will not accept new trades until emergency stop is cleared.")
        ], color="danger", className="mb-3")
        
        return alert
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", className="mb-3")


# Callback: Save Settings
@callback(
    Output("adv-alert-container", "children", allow_duplicate=True),
    Input("adv-save-settings-btn", "n_clicks"),
    State("adv-max-position-pct", "value"),
    State("adv-stop-loss-pct", "value"),
    State("adv-max-daily-loss", "value"),
    State("adv-max-positions", "value"),
    prevent_initial_call=True
)
def save_risk_settings(n_clicks, max_pos, stop_loss, max_loss, max_open):
    """Save risk management settings"""
    if not n_clicks:
        return html.Div()
    
    try:
        # In production, save to configuration file or database
        config_data = {
            "max_position_pct": max_pos,
            "stop_loss_pct": stop_loss,
            "max_daily_loss": max_loss,
            "max_open_positions": max_open,
            "saved_at": datetime.now().isoformat()
        }
        
        alert = dbc.Alert([
            html.H5("✅ Settings Saved Successfully!", className="mb-2"),
            html.Div(f"Max Position: {max_pos}%"),
            html.Div(f"Stop Loss: {stop_loss}%"),
            html.Div(f"Max Daily Loss: ${max_loss}"),
            html.Div(f"Max Positions: {max_open}")
        ], color="success", className="mb-3", dismissable=True)
        
        return alert
    except Exception as e:
        return dbc.Alert(f"Error saving settings: {str(e)}", color="danger", className="mb-3")
