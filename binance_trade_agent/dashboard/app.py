"""
Binance Trading Agent - Plotly Dash Dashboard
Production-ready financial trading dashboard with real-time data
"""

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance_trade_agent.dashboard.components import navbar
from binance_trade_agent.dashboard.pages import (
    portfolio, market_data, signals_risk, execute_trade,
    system_health, logs, advanced
)


# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP,
    ],
    suppress_callback_exceptions=True  # Allow callbacks to reference IDs that don't exist yet
)

# Configure app metadata
app.title = "Binance Trading Agent"
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Define page routes
PAGES = {
    '/': {'component': portfolio.layout, 'name': 'Portfolio', 'icon': '📊'},
    '/market-data': {'component': market_data.layout, 'name': 'Market Data', 'icon': '💰'},
    '/signals-risk': {'component': signals_risk.layout, 'name': 'Signals & Risk', 'icon': '🎯'},
    '/execute-trade': {'component': execute_trade.layout, 'name': 'Execute Trade', 'icon': '💼'},
    '/system-health': {'component': system_health.layout, 'name': 'System Health', 'icon': '🏥'},
    '/logs': {'component': logs.layout, 'name': 'Logs', 'icon': '📋'},
    '/advanced': {'component': advanced.layout, 'name': 'Advanced', 'icon': '⚙️'},
}


# Main app layout
app.layout = dbc.Container([
    # URL for multi-page routing
    dcc.Location(id='url', refresh=False),
    
    # Navbar component
    navbar.create_navbar(PAGES),
    
    # Main content area
    dbc.Container([
        html.Div(id='page-content', style={
            'minHeight': '80vh',
            'padding': '2rem 0'
        })
    ], fluid=True, style={
        'backgroundColor': '#1a1d23',
        'color': '#f4f2ee'
    }),
    
    # Footer
    html.Div([
        html.Hr(style={'borderColor': 'rgba(255, 145, 77, 0.2)', 'marginTop': '2rem'}),
        html.Div([
            html.Span("Binance Trading Agent Dashboard", style={'color': '#ff914d', 'fontWeight': 'bold'}),
            html.Span(" | ", style={'color': '#666'}),
            html.Span("Production-ready Trading System", style={'color': '#999'})
        ], style={
            'textAlign': 'center',
            'padding': '1rem',
            'fontSize': '0.875rem',
            'color': '#b8b4b0'
        })
    ], style={
        'backgroundColor': '#23242a',
        'borderTop': '1px solid rgba(255, 145, 77, 0.2)',
        'marginTop': 'auto'
    }),
    
    # Interval for auto-refresh
    dcc.Interval(
        id='refresh-interval',
        interval=30 * 1000,  # 30 seconds
        n_intervals=0
    )
], fluid=True, style={
    'backgroundColor': '#1a1d23',
    'color': '#f4f2ee',
    'minHeight': '100vh',
    'display': 'flex',
    'flexDirection': 'column'
})


# Callback for page routing
@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    prevent_initial_call=False
)
def display_page(pathname):
    """Route to the selected page based on URL pathname"""
    
    # Default to portfolio if path not found
    if pathname not in PAGES:
        pathname = '/'
    
    try:
        page_component = PAGES[pathname]['component']
        return page_component
    except Exception as e:
        return dbc.Container([
            dbc.Alert(
                [
                    html.H4("Page Not Found", className="alert-heading"),
                    html.P(f"Error loading page: {str(e)}")
                ],
                color="danger"
            )
        ], style={'marginTop': '2rem'})


if __name__ == '__main__':
    # Run on all interfaces for Docker
    app.run(
        host='0.0.0.0',
        port=8050,
        debug=False,
        threaded=True
    )
