"""
Logs Page - System logs and monitoring with filtering and search
"""

import csv
import logging
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, ctx, dcc, html

try:
    from binance_trade_agent.monitoring import monitoring
except Exception as e:
    monitoring = None

logger = logging.getLogger(__name__)

# Log levels
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
LOGS_PER_PAGE = 50
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_FILE_PATHS = [LOG_DIR / "agent.log", LOG_DIR / "auto_trading.log"]
DEFAULT_LOG_LIMIT = 800
DEFAULT_LOG_RANGE_DAYS = 1

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
                                                            date=(datetime.now() - timedelta(days=1)).date().isoformat(),
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
                                                            date=datetime.now().date().isoformat(),
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
                                        html.Div(id="log-action-alert", className="mt-3"),
                                        dcc.Download(id="log-export-download"),
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
    Output("log-action-alert", "children"),
    Output("log-page-store", "data"),
    Input("log-page-interval", "n_intervals"),  # Primary trigger for initial load
    Input("log-filter-btn", "n_clicks"),
    Input("log-next-btn", "n_clicks"),
    Input("log-prev-btn", "n_clicks"),
    Input("log-clear-btn", "n_clicks"),
    State("log-level-filter", "value"),
    State("log-search-box", "value"),
    State("log-start-date", "date"),
    State("log-end-date", "date"),
    State("log-page-store", "data"),
    prevent_initial_call=False,
)
def update_logs(
    interval,
    filter_clicks,
    next_clicks,
    prev_clicks,
    clear_clicks,
    level,
    search,
    start_date,
    end_date,
    page_data,
):
    """Update logs table with filtering and pagination"""
    print(f"DEBUG: update_logs called - interval={interval}, level={level}, search={search}")
    try:
        logger.info(f"update_logs called - level={level}, search={search}, start_date={start_date}, end_date={end_date}")
        trigger_id = ctx.triggered_id if ctx else None
        logger.info(f"Triggered by: {trigger_id}")
        
        filtered_logs = get_filtered_logs(level, search, start_date, end_date)
        logger.info(f"Got {len(filtered_logs)} filtered logs")

        total_count = len(filtered_logs)
        error_count = len([log for log in filtered_logs if log.get("level") == "ERROR"])
        warning_count = len([log for log in filtered_logs if log.get("level") == "WARNING"])

        total_pages = max(1, (total_count + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE)
        stored_page = page_data.get("current_page", 0) if page_data else 0
        page_num = stored_page

        if trigger_id == "log-next-btn":
            page_num = min(stored_page + 1, total_pages - 1)
        elif trigger_id == "log-prev-btn":
            page_num = max(stored_page - 1, 0)
        else:
            page_num = 0

        start_idx = page_num * LOGS_PER_PAGE
        end_idx = start_idx + LOGS_PER_PAGE
        page_logs = filtered_logs[start_idx:end_idx]

        if not page_logs:
            table = dbc.Alert("No logs found matching filters", color="info")
        else:
            table = build_logs_table(page_logs)

        action_alert = html.Div()
        if trigger_id == "log-clear-btn":
            action_alert = dbc.Alert(
                "Clearing log files is not supported from the dashboard."
                " Rotate or delete the log files on disk instead.",
                color="warning",
                className="mb-0",
            )

        last_update = datetime.now().strftime("%H:%M:%S")
        page_info = f"Page {page_num + 1} of {total_pages}"

        store_payload = {"current_page": page_num}

        logger.info(f"Returning: {total_count} logs, {error_count} errors, {warning_count} warnings")
        return (
            table,
            total_count,
            error_count,
            warning_count,
            last_update,
            page_info,
            action_alert,
            store_payload,
        )

    except Exception as e:
        logger.exception(f"Error loading logs: {str(e)}")
        error_alert = dbc.Alert(f"Error loading logs: {str(e)}", color="danger")
        return error_alert, 0, 0, 0, "Error", "Page 0", html.Div(), {"current_page": 0}


@callback(
    Output("log-level-filter", "value"),
    Output("log-search-box", "value"),
    Output("log-start-date", "date"),
    Output("log-end-date", "date"),
    Output("log-page-store", "data"),
    Input("log-reset-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(n_clicks):
    """Reset log filters to defaults"""
    start = (datetime.now() - timedelta(days=DEFAULT_LOG_RANGE_DAYS)).date().isoformat()
    end = datetime.now().date().isoformat()
    return "ALL", "", start, end, {"current_page": 0}


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
    """Export filtered logs"""
    logs = get_filtered_logs(level, search, start_date, end_date, limit=DEFAULT_LOG_LIMIT)
    csv_payload = logs_to_csv(logs)
    filename = f"system-logs-{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return dcc.send_string(csv_payload, filename)


def build_logs_table(logs: List[Dict]) -> dbc.Table:
    """Construct the log table from filtered records"""
    rows = []
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

    for log in logs:
        level = log.get("level", "INFO").upper()
        color_class = level_color_map.get(level, "text-secondary")
        icon = level_icon_map.get(level, "●")
        correlation_id = log.get("correlation_id") or "N/A"
        timestamp_value = log.get("timestamp")
        timestamp = format_timestamp(timestamp_value)

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
                        style={"width": "55%", "fontSize": "0.9rem"},
                    ),
                    html.Td(
                        correlation_id,
                        className="text-primary",
                        style={
                            "width": "20%",
                            "fontSize": "0.85rem",
                            "fontFamily": "monospace",
                        },
                    ),
                    html.Td(
                        timestamp or "N/A",
                        className="text-secondary",
                        style={"width": "17%", "fontSize": "0.85rem"},
                    ),
                ]
            )
        )

    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Level", style={"width": "8%"}),
                        html.Th("Message", style={"width": "55%"}),
                        html.Th("Correlation ID", style={"width": "20%"}),
                        html.Th("Timestamp", style={"width": "17%"}),
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


def get_filtered_logs(
    level: Optional[str],
    search: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    limit: int = DEFAULT_LOG_LIMIT,
) -> List[Dict]:
    """Fetch logs and apply filters"""
    raw_logs = fetch_recent_logs(limit)
    return apply_log_filters(raw_logs, level, search, start_date, end_date)


def fetch_recent_logs(limit: int = DEFAULT_LOG_LIMIT) -> List[Dict]:
    """Gather logs from files and monitoring events"""
    try:
        entries: List[Dict] = []
        logger.info(f"fetch_recent_logs: starting, limit={limit}")
        
        try:
            file_logs = read_log_files(limit)
            logger.info(f"fetch_recent_logs: got {len(file_logs)} logs from files")
            entries.extend(file_logs)
        except Exception as e:
            logger.warning(f"fetch_recent_logs: error reading log files: {e}")
            pass
        
        try:
            monitoring_logs = read_monitoring_events(limit)
            logger.info(f"fetch_recent_logs: got {len(monitoring_logs)} logs from monitoring")
            entries.extend(monitoring_logs)
        except Exception as e:
            logger.warning(f"fetch_recent_logs: error reading monitoring events: {e}")
            pass
        
        logger.info(f"fetch_recent_logs: total entries before sort: {len(entries)}")
        
        # If we got some logs, sort them
        if entries:
            entries.sort(
                key=lambda entry: entry.get("_timestamp_obj") or datetime.min, reverse=True
            )
            result = entries[:limit]
            logger.info(f"fetch_recent_logs: returning {len(result)} logs")
            return result
        
        # Fallback: return empty list if no logs found
        logger.info("fetch_recent_logs: no logs found, returning empty list")
        return []
    except Exception as e:
        logger.exception(f"fetch_recent_logs: unexpected error: {e}")
        return []


def read_log_files(limit: int) -> List[Dict]:
    """Read recent entries from configured log files"""
    results: List[Dict] = []
    try:
        logger.info(f"read_log_files: starting, limit={limit}")
        logger.info(f"read_log_files: checking paths: {LOG_FILE_PATHS}")
        
        for path in LOG_FILE_PATHS:
            logger.info(f"read_log_files: checking {path}, exists={path.exists()}")
            if not path.exists():
                logger.warning(f"read_log_files: {path} does not exist")
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    lines = handle.readlines()[-limit:]
                logger.info(f"read_log_files: read {len(lines)} lines from {path}")
            except OSError as e:
                logger.warning(f"read_log_files: OSError reading {path}: {e}")
                continue

            for line in lines:
                if not line.strip():
                    continue
                try:
                    entry = parse_file_log(line, path.stem)
                    results.append(entry)
                except Exception as e:
                    logger.debug(f"read_log_files: error parsing line '{line[:50]}': {e}")
                    continue
        
        logger.info(f"read_log_files: returning {len(results)} entries")
    except Exception as e:
        logger.exception(f"read_log_files: unexpected error: {e}")
    
    return results


def read_monitoring_events(limit: int) -> List[Dict]:
    """Pull structured logs captured by the monitoring system"""
    results: List[Dict] = []
    try:
        logger.info(f"read_monitoring_events: starting, limit={limit}")
        
        if not monitoring:
            logger.warning("read_monitoring_events: monitoring is None, skipping")
            return results
        
        logger.info(f"read_monitoring_events: monitoring={monitoring}, has loggers={hasattr(monitoring, 'loggers')}")
        
        if hasattr(monitoring, 'loggers') and monitoring.loggers:
            logger.info(f"read_monitoring_events: found {len(monitoring.loggers)} loggers")
            for logger_name, monitor_logger in monitoring.loggers.items():
                try:
                    logger.info(f"read_monitoring_events: processing logger '{logger_name}'")
                    events = monitor_logger.get_recent_logs(limit=limit)
                    logger.info(f"read_monitoring_events: got {len(events)} events from '{logger_name}'")
                    
                    for event in events:
                        timestamp = parse_timestamp(event.get("timestamp"))
                        results.append(
                            {
                                "timestamp": timestamp,
                                "level": event.get("level"),
                                "message": event.get("message"),
                                "correlation_id": event.get("correlation_id"),
                                "module": event.get("module"),
                                "source": monitor_logger.name,
                                "_timestamp_obj": timestamp,
                            }
                        )
                except Exception as e:
                    logger.warning(f"read_monitoring_events: error processing logger '{logger_name}': {e}")
                    continue
        else:
            logger.warning("read_monitoring_events: monitoring.loggers not found or empty")
    except Exception as e:
        logger.exception(f"read_monitoring_events: unexpected error: {e}")
    
    logger.info(f"read_monitoring_events: returning {len(results)} entries")
    return results


def parse_file_log(line: str, source: str) -> Dict:
    """Parse a single log line from a file"""
    parts = line.strip().split(" - ", 2)
    timestamp_value = parts[0] if parts else ""
    level = parts[1] if len(parts) > 1 else "INFO"
    message = parts[2] if len(parts) > 2 else ""
    timestamp = parse_timestamp(timestamp_value)
    return {
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "correlation_id": "N/A",
        "module": source,
        "source": source,
        "_timestamp_obj": timestamp,
    }


def apply_log_filters(
    logs: List[Dict],
    level: Optional[str],
    search: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> List[Dict]:
    """Filter logs based on search, level, and date range"""
    filtered: List[Dict] = []
    level_filter = level.upper() if level else None
    search_lower = search.strip().lower() if search else None
    start = parse_date(start_date)
    end = parse_date(end_date)

    for log in logs:
        log_level = log.get("level", "").upper()
        timestamp = log.get("_timestamp_obj")

        if level_filter and level_filter != "ALL" and log_level != level_filter:
            continue
        if search_lower:
            if search_lower not in (log.get("message") or "").lower() and search_lower not in (
                log.get("correlation_id") or ""
            ).lower():
                continue
        if start and timestamp and timestamp.date() < start:
            continue
        if end and timestamp and timestamp.date() > end:
            continue

        filtered.append(log)

    return filtered


def format_timestamp(value: Optional[str]) -> Optional[str]:
    """Format log timestamps for display"""
    dt = parse_timestamp(value)
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse timestamp strings into datetime objects"""
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_date(value: Optional[str]) -> Optional[datetime.date]:
    """Parse DatePicker values into date objects"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def logs_to_csv(logs: List[Dict]) -> str:
    """Render filtered logs as CSV"""
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["timestamp", "level", "message", "correlation_id", "module", "source"])
    for log in logs:
        writer.writerow(
            [
                format_timestamp(log.get("timestamp")) or "",
                log.get("level", ""),
                log.get("message", ""),
                log.get("correlation_id", ""),
                log.get("module", ""),
                log.get("source", ""),
            ]
        )
    return buffer.getvalue()
