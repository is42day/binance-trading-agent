"""
Logs Page - System logs and monitoring with filtering and search
"""

import csv
import logging
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, ctx, dcc, html

logger = logging.getLogger(__name__)

# Log levels
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
LOGS_PER_PAGE = 50
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_FILE_PATHS = [LOG_DIR / "agent.log", LOG_DIR / "auto_trading.log"]


def read_log_files(limit: int = 100) -> list:
    """Read recent log entries from log files"""
    results = []
    try:
        for path in LOG_FILE_PATHS:
            if not path.exists():
                logger.debug(f"Log file not found: {path}")
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-limit:]
                
                for line in lines:
                    if not line.strip():
                        continue
                    # Parse log line - handle two formats:
                    # Format 1: "2024-01-01 12:00:00,123 - LEVEL - message"
                    # Format 2: "2024-01-01 12:00:00,123 - module.name - LEVEL - message"
                    parts = line.strip().split(" - ")
                    if len(parts) < 2:
                        continue
                    
                    timestamp = parts[0]
                    
                    # Detect format by checking if parts[1] is a log level
                    LOG_LEVEL_KEYWORDS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
                    
                    if parts[1].upper() in LOG_LEVEL_KEYWORDS:
                        # Format 1: timestamp - LEVEL - message
                        level = parts[1]
                        message = " - ".join(parts[2:]) if len(parts) > 2 else ""
                        module = "unknown"
                    else:
                        # Format 2: timestamp - module - LEVEL - message
                        module = parts[1]
                        if len(parts) >= 3 and parts[2].upper() in LOG_LEVEL_KEYWORDS:
                            level = parts[2]
                            message = " - ".join(parts[3:]) if len(parts) > 3 else ""
                        else:
                            # Fallback if format is unexpected
                            level = "INFO"
                            message = " - ".join(parts[1:])
                    
                    results.append({
                        "timestamp": timestamp,
                        "level": level.strip().upper(),
                        "message": message.strip(),
                        "correlation_id": "N/A",
                        "module": module
                    })
            except Exception as e:
                logger.warning(f"Error reading {path}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error in read_log_files: {e}")
    
    return results


def read_monitoring_events(limit: int = 100) -> list:
    """Read recent events from monitoring system"""
    results = []
    try:
        from binance_trade_agent.monitoring import monitoring
        
        if not monitoring:
            logger.debug("Monitoring system not available")
            return results
        
        # Try to get logs from monitoring loggers
        if hasattr(monitoring, 'loggers') and monitoring.loggers:
            for logger_name, monitor_logger in monitoring.loggers.items():
                try:
                    # Try to get recent logs from the monitoring logger
                    if hasattr(monitor_logger, 'get_recent_logs'):
                        events = monitor_logger.get_recent_logs(limit=limit)
                        for event in events:
                            results.append({
                                "timestamp": event.get("timestamp", "N/A"),
                                "level": event.get("level", "INFO"),
                                "message": event.get("message", ""),
                                "correlation_id": event.get("correlation_id", "N/A")
                            })
                except Exception as e:
                    logger.debug(f"Error reading from monitoring logger {logger_name}: {e}")
                    continue
    except ImportError:
        logger.debug("Monitoring module not available")
    except Exception as e:
        logger.warning(f"Error in read_monitoring_events: {e}")
    
    return results


def _log_in_date_range(timestamp: str, start_date: str, end_date: str) -> bool:
    """Check if log timestamp falls within date range"""
    try:
        # Parse timestamp - handle multiple formats
        log_date = None
        for fmt in ["%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
            try:
                log_date = datetime.strptime(timestamp, fmt).date()
                break
            except ValueError:
                continue
        
        if not log_date:
            return True  # If we can't parse, include it
        
        if start_date:
            try:
                start = datetime.fromisoformat(start_date).date()
                if log_date < start:
                    return False
            except Exception:
                pass
        
        if end_date:
            try:
                end = datetime.fromisoformat(end_date).date()
                if log_date > end:
                    return False
            except Exception:
                pass
        
        return True
    except Exception as e:
        logger.debug(f"Error in date range check: {e}")
        return True



LOGS_PER_PAGE = 50

layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "📋 System Logs & Monitoring",
                            style={"marginTop": "2rem", "marginBottom": "1rem"},
                        )
                    ]
                )
            ]
        ),
        # Filters Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("🔍 Log Filters", className="bg-dark"),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                # Log Level Filter
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Log Level",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.Dropdown(
                                                            id="log-level-filter",
                                                            options=[
                                                                {
                                                                    "label": "All Levels",
                                                                    "value": "ALL",
                                                                },
                                                                {
                                                                    "label": "🔴 ERROR",
                                                                    "value": "ERROR",
                                                                },
                                                                {
                                                                    "label": "🟡 WARNING",
                                                                    "value": "WARNING",
                                                                },
                                                                {
                                                                    "label": "🟢 INFO",
                                                                    "value": "INFO",
                                                                },
                                                                {
                                                                    "label": "⚪ DEBUG",
                                                                    "value": "DEBUG",
                                                                },
                                                            ],
                                                            value="ALL",
                                                            clearable=False,
                                                            className="form-control",
                                                        ),
                                                    ],
                                                    md=3,
                                                ),
                                                # Date Range
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Start Date",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.DatePickerSingle(
                                                            id="log-start-date",
                                                            date=datetime.now() - timedelta(days=1),
                                                            display_format="YYYY-MM-DD",
                                                            className="form-control",
                                                            style={"width": "100%"},
                                                        ),
                                                    ],
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "End Date",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dcc.DatePickerSingle(
                                                            id="log-end-date",
                                                            date=datetime.now(),
                                                            display_format="YYYY-MM-DD",
                                                            className="form-control",
                                                            style={"width": "100%"},
                                                        ),
                                                    ],
                                                    md=3,
                                                ),
                                                # Search Box
                                                dbc.Col(
                                                    [
                                                        html.Label(
                                                            "Search / Correlation ID",
                                                            className="text-secondary font-weight-bold",
                                                        ),
                                                        dbc.Input(
                                                            id="log-search-box",
                                                            type="text",
                                                            placeholder="Search logs or correlation ID...",
                                                            className="form-control",
                                                        ),
                                                    ],
                                                    md=3,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        # Filter Buttons
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "🔍 Apply Filters",
                                                            id="log-filter-btn",
                                                            color="primary",
                                                            className="btn-primary",
                                                            style={"width": "100%"},
                                                        )
                                                    ],
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "🔄 Reset",
                                                            id="log-reset-btn",
                                                            color="secondary",
                                                            style={"width": "100%"},
                                                        )
                                                    ],
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "📥 Export",
                                                            id="log-export-btn",
                                                            color="info",
                                                            style={"width": "100%"},
                                                        )
                                                    ],
                                                    md=3,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            "🗑️ Clear Old Logs",
                                                            id="log-clear-btn",
                                                            color="danger",
                                                            outline=True,
                                                            style={"width": "100%"},
                                                        )
                                                    ],
                                                    md=3,
                                                ),
                                            ]
                                        ),
                                    ]
                                ),
                            ],
                            className="mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # Stats Section
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Total Logs", className="metric-label"),
                                        html.Div(
                                            "0",
                                            id="log-total-count",
                                            className="metric-value",
                                        ),
                                    ],
                                    className="metric-card",
                                )
                            ]
                        )
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Errors", className="metric-label"),
                                        html.Div(
                                            "0",
                                            id="log-error-count",
                                            className="metric-value text-danger",
                                        ),
                                    ],
                                    className="metric-card",
                                )
                            ]
                        )
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Warnings", className="metric-label"),
                                        html.Div(
                                            "0",
                                            id="log-warning-count",
                                            className="metric-value text-warning",
                                        ),
                                    ],
                                    className="metric-card",
                                )
                            ]
                        )
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Last Updated", className="metric-label"),
                                        html.Div(
                                            "Just now",
                                            id="log-last-update",
                                            className="metric-value text-success",
                                        ),
                                    ],
                                    className="metric-card",
                                )
                            ]
                        )
                    ],
                    md=3,
                ),
            ],
            className="mb-4",
        ),
        # Logs Table
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("📝 Log Entries", className="bg-dark"),
                                dbc.CardBody(
                                    [
                                        html.Div(
                                            id="logs-table-container",
                                            children=[dbc.Alert("Loading logs...", color="info")],
                                        )
                                    ]
                                ),
                            ],
                            className="mb-4",
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # Pagination
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    "⬅️ Previous",
                                                    id="log-prev-btn",
                                                    outline=True,
                                                ),
                                                dbc.Button(
                                                    "Next ➡️",
                                                    id="log-next-btn",
                                                    outline=True,
                                                ),
                                            ],
                                            style={"width": "100%"},
                                        )
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        html.Div(
                                            "Page 1",
                                            id="log-pagination-info",
                                            className="text-center text-secondary",
                                        )
                                    ],
                                    width=4,
                                ),
                            ]
                        )
                    ],
                    width=12,
                )
            ]
        ),
        # Auto-refresh interval
        dcc.Interval(id="log-page-interval", interval=60000, n_intervals=0),  # 60 seconds
        # Store for pagination
        dcc.Store(id="log-page-store", data={"current_page": 0}),
        # Download component for CSV export
        dcc.Download(id="log-export-download"),
    ],
    fluid=True,
    className="p-4",
)


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
    prevent_initial_call=False,
)
def update_logs(
    filter_clicks,
    interval,
    next_clicks,
    prev_clicks,
    level,
    search,
    start_date,
    end_date,
    page_data,
):
    """Update logs table with filtering and pagination"""
    try:
        # Get sample logs (in production, this would query actual log storage)
        sample_logs = generate_sample_logs()

        # Apply filters
        filtered_logs = sample_logs

        if level and level != "ALL":
            filtered_logs = [log for log in filtered_logs if log.get("level") == level]

        if search:
            search_lower = search.lower()
            filtered_logs = [
                log
                for log in filtered_logs
                if search_lower in log.get("message", "").lower()
                or search_lower in log.get("correlation_id", "").lower()
            ]
        
        # Filter by date range
        if start_date or end_date:
            filtered_logs = [
                log for log in filtered_logs
                if _log_in_date_range(log.get("timestamp"), start_date, end_date)
            ]

        # Pagination
        page_num = page_data.get("current_page", 0)
        if ctx and "log-next-btn" in ctx.triggered_prop_ids:
            page_num += 1
        elif ctx and "log-prev-btn" in ctx.triggered_prop_ids:
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
                    "ERROR": "text-danger",
                    "WARNING": "text-warning",
                    "INFO": "text-success",
                    "DEBUG": "text-muted",
                }
                level_icon_map = {
                    "ERROR": "🔴",
                    "WARNING": "🟡",
                    "INFO": "🟢",
                    "DEBUG": "⚪",
                }

                level = log.get("level", "INFO")
                color_class = level_color_map.get(level, "text-secondary")
                icon = level_icon_map.get(level, "●")
                module = log.get("module", "N/A")
                # Shorten module name for display (last part after last dot)
                module_short = module.split(".")[-1] if module != "N/A" else "N/A"

                rows.append(
                    html.Tr(
                        [
                            html.Td(
                                f"{icon} {level}",
                                className=f"font-weight-bold {color_class}",
                                style={"width": "8%"},
                            ),
                            html.Td(
                                log.get("message", ""),
                                style={"width": "45%", "fontSize": "0.9rem"},
                            ),
                            html.Td(
                                module_short,
                                className="text-info",
                                style={
                                    "width": "15%",
                                    "fontSize": "0.85rem",
                                    "fontFamily": "monospace",
                                    "title": module,  # Full module name on hover
                                },
                            ),
                            html.Td(
                                log.get("timestamp", "N/A"),
                                className="text-secondary",
                                style={"width": "17%", "fontSize": "0.85rem"},
                            ),
                            html.Td(
                                log.get("correlation_id", "N/A"),
                                className="text-muted",
                                style={
                                    "width": "15%",
                                    "fontSize": "0.8rem",
                                    "fontFamily": "monospace",
                                },
                            ),
                        ]
                    )
                )

            table = dbc.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Level", style={"width": "8%"}),
                                html.Th("Message", style={"width": "45%"}),
                                html.Th("Module", style={"width": "15%"}),
                                html.Th("Timestamp", style={"width": "17%"}),
                                html.Th("Correlation ID", style={"width": "15%"}),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ],
                dark=True,
                hover=True,
                responsive=True,
                className="mb-0",
            )

        # Stats
        error_count = len([log for log in filtered_logs if log.get("level") == "ERROR"])
        warning_count = len([log for log in filtered_logs if log.get("level") == "WARNING"])
        total_count = len(filtered_logs)
        last_update = datetime.now().strftime("%H:%M:%S")

        total_pages = (total_count + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE
        page_info = f"Page {page_num + 1} of {max(1, total_pages)}"

        return table, total_count, error_count, warning_count, last_update, page_info

    except Exception as e:
        error_alert = dbc.Alert(f"Error loading logs: {str(e)}", color="danger")
        return error_alert, 0, 0, 0, "Error", "Page 0"


def generate_sample_logs():
    """Generate logs from real files, monitoring system, and sample data"""
    # Try to get real logs from files (read more to get recent entries)
    real_logs = read_log_files(limit=200)
    
    # Try to get logs from monitoring system
    monitoring_logs = read_monitoring_events(limit=50)
    
    # Generate minimal sample logs for demonstration (optional, mostly for testing)
    sample_logs = [
        {
            "timestamp": (datetime.now() - timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": ["INFO", "WARNING", "ERROR", "DEBUG"][i % 4],
            "message": f"Sample log message #{i}: Operation completed successfully",
            "correlation_id": f'trade_{datetime.now().strftime("%Y%m%d")}_000{i:03d}',
            "module": "binance_trade_agent.dashboard"
        }
        for i in range(5)  # Minimal samples, focus on real data
    ]
    
    # Combine all log sources (real first, monitoring, then sample)
    logs = real_logs + monitoring_logs + sample_logs
    return logs


@callback(
    Output("log-export-download", "data"),
    Input("log-export-btn", "n_clicks"),
    State("log-level-filter", "value"),
    State("log-search-box", "value"),
    State("log-start-date", "date"),
    State("log-end-date", "date"),
    prevent_initial_call=True,
)
def export_logs(n_clicks, level, search, start_date, end_date):
    """Export filtered logs to CSV"""
    try:
        # Get all logs
        all_logs = generate_sample_logs()
        
        # Apply same filters
        filtered_logs = all_logs
        
        if level and level != "ALL":
            filtered_logs = [log for log in filtered_logs if log.get("level") == level]
        
        if search:
            search_lower = search.lower()
            filtered_logs = [
                log for log in filtered_logs
                if search_lower in log.get("message", "").lower()
                or search_lower in log.get("correlation_id", "").lower()
            ]
        
        if start_date or end_date:
            filtered_logs = [
                log for log in filtered_logs
                if _log_in_date_range(log.get("timestamp"), start_date, end_date)
            ]
        
        # Convert to CSV
        csv_str = _logs_to_csv(filtered_logs)
        
        filename = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return dcc.send_string(csv_str, filename)
    
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        return None


def _logs_to_csv(logs: list) -> str:
    """Convert logs to CSV format"""
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Timestamp", "Level", "Module", "Message", "Correlation ID"])
    
    # Write log rows
    for log in logs:
        writer.writerow([
            log.get("timestamp", ""),
            log.get("level", ""),
            log.get("module", ""),
            log.get("message", ""),
            log.get("correlation_id", ""),
        ])
    
    return output.getvalue()
