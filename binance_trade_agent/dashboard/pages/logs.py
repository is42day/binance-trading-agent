"""
Logs Page - System logs and monitoring with filtering and search
"""

import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ctx
from datetime import datetime, timedelta
import json

# Log levels
LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
LOGS_PER_PAGE = 50

layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("📋 System Logs & Monitoring", style={'marginTop': '2rem', 'marginBottom': '1rem'})
        ])
    ]),
    
    # Filters Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🔍 Log Filters", className="bg-dark"),
                dbc.CardBody([
                    dbc.Row([
                        # Log Level Filter
                        dbc.Col([
                            html.Label("Log Level", className="text-secondary font-weight-bold"),
                            dcc.Dropdown(
                                id="log-level-filter",
                                options=[
                                    {"label": "All Levels", "value": "ALL"},
                                    {"label": "🔴 ERROR", "value": "ERROR"},
                                    {"label": "🟡 WARNING", "value": "WARNING"},
                                    {"label": "🟢 INFO", "value": "INFO"},
                                    {"label": "⚪ DEBUG", "value": "DEBUG"}
                                ],
                                value="ALL",
                                clearable=False,
                                className="form-control"
                            )
                        ], md=3),
                        
                        # Date Range
                        dbc.Col([
                            html.Label("Start Date", className="text-secondary font-weight-bold"),
                            dcc.DatePickerSingle(
                                id="log-start-date",
                                date=datetime.now() - timedelta(days=1),
                                display_format="YYYY-MM-DD",
                                className="form-control",
                                style={"width": "100%"}
                            )
                        ], md=3),
                        
                        dbc.Col([
                            html.Label("End Date", className="text-secondary font-weight-bold"),
                            dcc.DatePickerSingle(
                                id="log-end-date",
                                date=datetime.now(),
                                display_format="YYYY-MM-DD",
                                className="form-control",
                                style={"width": "100%"}
                            )
                        ], md=3),
                        
                        # Search Box
                        dbc.Col([
                            html.Label("Search / Correlation ID", className="text-secondary font-weight-bold"),
                            dbc.Input(
                                id="log-search-box",
                                type="text",
                                placeholder="Search logs or correlation ID...",
                                className="form-control"
                            )
                        ], md=3)
                    ], className="mb-3"),
                    
                    # Filter Buttons
                    dbc.Row([
                        dbc.Col([
                            dbc.Button(
                                "🔍 Apply Filters",
                                id="log-filter-btn",
                                color="primary",
                                className="btn-primary",
                                style={"width": "100%"}
                            )
                        ], md=3),
                        
                        dbc.Col([
                            dbc.Button(
                                "🔄 Reset",
                                id="log-reset-btn",
                                color="secondary",
                                style={"width": "100%"}
                            )
                        ], md=3),
                        
                        dbc.Col([
                            dbc.Button(
                                "📥 Export",
                                id="log-export-btn",
                                color="info",
                                style={"width": "100%"}
                            )
                        ], md=3),
                        
                        dbc.Col([
                            dbc.Button(
                                "🗑️ Clear Old Logs",
                                id="log-clear-btn",
                                color="danger",
                                outline=True,
                                style={"width": "100%"}
                            )
                        ], md=3)
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Stats Section
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div([
                    html.Div("Total Logs", className="metric-label"),
                    html.Div("0", id="log-total-count", className="metric-value"),
                ], className="metric-card")
            ])
        ], md=3),
        
        dbc.Col([
            html.Div([
                html.Div([
                    html.Div("Errors", className="metric-label"),
                    html.Div("0", id="log-error-count", className="metric-value text-danger"),
                ], className="metric-card")
            ])
        ], md=3),
        
        dbc.Col([
            html.Div([
                html.Div([
                    html.Div("Warnings", className="metric-label"),
                    html.Div("0", id="log-warning-count", className="metric-value text-warning"),
                ], className="metric-card")
            ])
        ], md=3),
        
        dbc.Col([
            html.Div([
                html.Div([
                    html.Div("Last Updated", className="metric-label"),
                    html.Div("Just now", id="log-last-update", className="metric-value text-success"),
                ], className="metric-card")
            ])
        ], md=3)
    ], className="mb-4"),
    
    # Logs Table
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📝 Log Entries", className="bg-dark"),
                dbc.CardBody([
                    html.Div(id="logs-table-container", children=[
                        dbc.Alert("Loading logs...", color="info")
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Pagination
    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("⬅️ Previous", id="log-prev-btn", outline=True),
                        dbc.Button("Next ➡️", id="log-next-btn", outline=True)
                    ], style={"width": "100%"})
                ], width=8),
                dbc.Col([
                    html.Div(
                        "Page 1",
                        id="log-pagination-info",
                        className="text-center text-secondary"
                    )
                ], width=4)
            ])
        ], width=12)
    ]),
    
    # Auto-refresh interval
    dcc.Interval(
        id="log-page-interval",
        interval=60000,  # 60 seconds
        n_intervals=0
    ),
    
    # Store for pagination
    dcc.Store(id="log-page-store", data={"current_page": 0})
    
], fluid=True, className="p-4")


@callback(
    Output("logs-table-container", "children"),
    Output("log-total-count", "children"),
    Output("log-error-count", "children"),
    Output("log-warning-count", "children"),
    Output("log-last-update", "children"),
    Output("log-pagination-info", "children"),
    Input("log-filter-btn", "n_clicks"),
    Input("log-page-interval", "n_intervals"),
    Input("log-next-btn", "n_clicks"),
    Input("log-prev-btn", "n_clicks"),
    State("log-level-filter", "value"),
    State("log-search-box", "value"),
    State("log-start-date", "date"),
    State("log-end-date", "date"),
    State("log-page-store", "data"),
    prevent_initial_call=False
)
def update_logs(filter_clicks, interval, next_clicks, prev_clicks, level, search, start_date, 
                end_date, page_data):
    """Update logs table with filtering and pagination"""
    try:
        # Get sample logs (in production, this would query actual log storage)
        sample_logs = generate_sample_logs()
        
        # Apply filters
        filtered_logs = sample_logs
        
        if level and level != "ALL":
            filtered_logs = [log for log in filtered_logs if log.get('level') == level]
        
        if search:
            search_lower = search.lower()
            filtered_logs = [
                log for log in filtered_logs
                if search_lower in log.get('message', '').lower() or 
                   search_lower in log.get('correlation_id', '').lower()
            ]
        
        # Pagination
        page_num = page_data.get('current_page', 0)
        if ctx and 'log-next-btn' in ctx.triggered_prop_ids:
            page_num += 1
        elif ctx and 'log-prev-btn' in ctx.triggered_prop_ids:
            page_num = max(0, page_num - 1)
        
        start_idx = page_num * LOGS_PER_PAGE
        end_idx = start_idx + LOGS_PER_PAGE
        page_logs = filtered_logs[start_idx:end_idx]
        
        # Build table
        if not page_logs:
            table = dbc.Alert("No logs found matching filters", color="info")
        else:
            rows = []
            for log in page_logs:
                level_color_map = {
                    'ERROR': 'text-danger',
                    'WARNING': 'text-warning',
                    'INFO': 'text-success',
                    'DEBUG': 'text-muted'
                }
                level_icon_map = {
                    'ERROR': '🔴',
                    'WARNING': '🟡',
                    'INFO': '🟢',
                    'DEBUG': '⚪'
                }
                
                level = log.get('level', 'INFO')
                color_class = level_color_map.get(level, 'text-secondary')
                icon = level_icon_map.get(level, '●')
                
                rows.append(html.Tr([
                    html.Td(f"{icon} {level}", className=f"font-weight-bold {color_class}", style={"width": "8%"}),
                    html.Td(log.get('message', ''), style={"width": "55%", "fontSize": "0.9rem"}),
                    html.Td(log.get('correlation_id', 'N/A'), className="text-primary", style={"width": "20%", "fontSize": "0.85rem", "fontFamily": "monospace"}),
                    html.Td(log.get('timestamp', 'N/A'), className="text-secondary", style={"width": "17%", "fontSize": "0.85rem"})
                ]))
            
            table = dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Level", style={"width": "8%"}),
                    html.Th("Message", style={"width": "55%"}),
                    html.Th("Correlation ID", style={"width": "20%"}),
                    html.Th("Timestamp", style={"width": "17%"})
                ])),
                html.Tbody(rows)
            ], dark=True, hover=True, responsive=True, className="mb-0")
        
        # Stats
        error_count = len([log for log in filtered_logs if log.get('level') == 'ERROR'])
        warning_count = len([log for log in filtered_logs if log.get('level') == 'WARNING'])
        total_count = len(filtered_logs)
        last_update = datetime.now().strftime("%H:%M:%S")
        
        total_pages = (total_count + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE
        page_info = f"Page {page_num + 1} of {max(1, total_pages)}"
        
        return table, total_count, error_count, warning_count, last_update, page_info
        
    except Exception as e:
        error_alert = dbc.Alert(f"Error loading logs: {str(e)}", color="danger")
        return error_alert, 0, 0, 0, "Error", "Page 0"


def generate_sample_logs():
    """Generate sample logs for demonstration"""
    logs = [
        {
            'timestamp': (datetime.now() - timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
            'level': ['INFO', 'WARNING', 'ERROR', 'DEBUG'][i % 4],
            'message': f'Sample log message #{i}: Operation completed successfully',
            'correlation_id': f'trade_{datetime.now().strftime("%Y%m%d")}_000{i:03d}'
        }
        for i in range(100)
    ]
    return logs
