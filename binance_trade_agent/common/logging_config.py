"""
Structured Logging Module - 12-factor app style logging

Provides centralized logging configuration with:
- JSON-formatted logs (recommended for production)
- Service name and correlation ID tracking
- Structured context (order_id, symbol, call_id)
- Stdout/stderr only (no file logs)
- Timestamp, level, and message standardization
"""

import json
import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict

# Context variables for correlation tracking (thread-safe)
SERVICE_NAME: ContextVar[str] = ContextVar("service_name", default="unknown")
CORRELATION_ID: ContextVar[str] = ContextVar("correlation_id", default="")
CALL_ID: ContextVar[str] = ContextVar("call_id", default="")


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in JSON format with:
    - timestamp (ISO 8601)
    - level (ERROR, WARNING, INFO, DEBUG)
    - service_name
    - correlation_id / call_id
    - message
    - extra fields (symbol, order_id, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": SERVICE_NAME.get(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation tracking if present
        correlation_id = CORRELATION_ID.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        call_id = CALL_ID.get()
        if call_id:
            log_entry["call_id"] = call_id

        # Add extra fields (symbol, order_id, etc.)
        if hasattr(record, "symbol"):
            log_entry["symbol"] = record.symbol
        if hasattr(record, "order_id"):
            log_entry["order_id"] = record.order_id
        if hasattr(record, "trade_id"):
            log_entry["trade_id"] = record.trade_id
        if hasattr(record, "quantity"):
            log_entry["quantity"] = record.quantity
        if hasattr(record, "price"):
            log_entry["price"] = record.price

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class PlainFormatter(logging.Formatter):
    """
    Plain text formatter for development/console use.

    Outputs in human-readable format:
    2025-12-19 12:34:56 [SERVICE] [LEVEL] logger_name: message [symbol=BTC, order_id=123]
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as plain text"""
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        service = SERVICE_NAME.get()
        level = record.levelname

        # Build message with context
        msg = record.getMessage()

        # Add context fields if present
        context_fields = []
        if hasattr(record, "symbol"):
            context_fields.append(f"symbol={record.symbol}")
        if hasattr(record, "order_id"):
            context_fields.append(f"order_id={record.order_id}")
        if hasattr(record, "trade_id"):
            context_fields.append(f"trade_id={record.trade_id}")
        if hasattr(record, "correlation_id"):
            context_fields.append(f"corr={record.correlation_id}")

        context_str = f" [{', '.join(context_fields)}]" if context_fields else ""

        # Add exception if present
        if record.exc_info:
            msg = f"{msg}\n{self.formatException(record.exc_info)}"

        return f"{timestamp} [{service}] [{level}] {record.name}: {msg}{context_str}"


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    use_json: bool = False,
) -> None:
    """
    Configure structured logging for a service.

    Args:
        service_name: Name of the service (e.g., "api", "trading-agent", "dashboard")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: If True, use JSON formatter; else use plain formatter

    Usage:
        setup_logging("trading-agent", log_level="INFO", use_json=False)
        logger = logging.getLogger(__name__)
        logger.info("Message", extra={"symbol": "BTCUSDT", "order_id": "12345"})
    """
    # Set service name in context
    SERVICE_NAME.set(service_name)

    # Determine log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stdout handler (12-factor: logs to stdout/stderr)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    # Choose formatter based on environment
    if use_json or os.getenv("LOG_FORMAT", "plain").lower() == "json":
        formatter = StructuredFormatter()
    else:
        formatter = PlainFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Also write to file for dashboard logs tab
    log_dir = os.getenv("LOG_DIR", "/app/logs")
    if os.path.isdir(log_dir):
        log_file = os.path.join(log_dir, f"{service_name.replace('-', '_')}.log")
        try:
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=3  # 10MB
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(PlainFormatter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file handler: {e}")


def get_logger(name: str) -> logging.LoggerAdapter:
    """
    Get a logger with built-in context support.

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing trade", extra={"symbol": "BTCUSDT", "order_id": "123"})
    """
    logger = logging.getLogger(name)

    class ContextAwareAdapter(logging.LoggerAdapter):
        """Adapter that automatically includes context in all log calls"""

        def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
            # Extract extra fields if present
            extra = kwargs.get("extra", {})

            # Add correlation/call IDs from context
            if CORRELATION_ID.get():
                extra["correlation_id"] = CORRELATION_ID.get()
            if CALL_ID.get():
                extra["call_id"] = CALL_ID.get()

            if extra:
                kwargs["extra"] = extra

            return msg, kwargs

    return ContextAwareAdapter(logger, {})


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for tracing related operations"""
    CORRELATION_ID.set(correlation_id)


def set_call_id(call_id: str) -> None:
    """Set the call ID for tracing within a single operation"""
    CALL_ID.set(call_id)


def generate_call_id() -> str:
    """Generate a new unique call ID"""
    return str(uuid.uuid4())[:8]


def clear_context() -> None:
    """Clear all context variables"""
    CORRELATION_ID.set("")
    CALL_ID.set("")
