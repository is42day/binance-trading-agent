"""
Structured Logging and Monitoring System for Trading Agent
"""
import logging
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from functools import wraps
from contextlib import contextmanager
import threading
from collections import defaultdict, deque
import statistics

from .config import config


@dataclass
class MetricEvent:
    """Represents a metric event"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    event_type: str  # 'counter', 'gauge', 'histogram', 'timing'


@dataclass
class LogEvent:
    """Represents a structured log event"""
    timestamp: datetime
    level: str
    message: str
    module: str
    function: str
    correlation_id: Optional[str]
    event_type: str
    context: Dict[str, Any]
    duration_ms: Optional[float] = None


class CorrelationContext:
    """Thread-local correlation context"""
    _local = threading.local()
    
    @classmethod
    def set_correlation_id(cls, correlation_id: str):
        """Set correlation ID for current thread"""
        cls._local.correlation_id = correlation_id
    
    @classmethod
    def get_correlation_id(cls) -> Optional[str]:
        """Get correlation ID for current thread"""
        return getattr(cls._local, 'correlation_id', None)
    
    @classmethod
    def clear(cls):
        """Clear correlation context"""
        if hasattr(cls._local, 'correlation_id'):
            delattr(cls._local, 'correlation_id')


class MetricsCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.events: deque = deque(maxlen=max_events)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def record_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Record a counter metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            self._add_event(name, value, 'counter', labels or {})
    
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a gauge metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            self._add_event(name, value, 'gauge', labels or {})
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.histograms[key].append(value)
            # Keep only last 1000 values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            self._add_event(name, value, 'histogram', labels or {})
    
    def record_timing(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None):
        """Record a timing metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.timings[key].append(duration_ms)
            # Keep only last 1000 values
            if len(self.timings[key]) > 1000:
                self.timings[key] = self.timings[key][-1000:]
            self._add_event(name, duration_ms, 'timing', labels or {})
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create metric key from name and labels"""
        if not labels:
            return name
        label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
        return f'{name}{{{label_str}}}'
    
    def _add_event(self, name: str, value: float, event_type: str, labels: Dict[str, str]):
        """Add metric event to history"""
        event = MetricEvent(
            name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels,
            event_type=event_type
        )
        self.events.append(event)
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value"""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get gauge value"""
        key = self._make_key(name, labels)
        return self.gauges.get(key)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._make_key(name, labels)
        values = self.histograms.get(key, [])
        if not values:
            return {}
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'p95': self._percentile(values, 0.95),
            'p99': self._percentile(values, 0.99)
        }
    
    def get_timing_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get timing statistics"""
        key = self._make_key(name, labels)
        values = self.timings.get(key, [])
        if not values:
            return {}
        
        return {
            'count': len(values),
            'min_ms': min(values),
            'max_ms': max(values),
            'mean_ms': statistics.mean(values),
            'median_ms': statistics.median(values),
            'p95_ms': self._percentile(values, 0.95),
            'p99_ms': self._percentile(values, 0.99)
        }
    
    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * p
        f = int(k)
        c = k - f
        if f + 1 < len(sorted_values):
            return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
        else:
            return sorted_values[f]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        with self._lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histogram_count': len(self.histograms),
                'timing_count': len(self.timings),
                'total_events': len(self.events),
                'timestamp': datetime.now().isoformat()
            }


class StructuredLogger:
    """Enhanced logger with structured logging and correlation tracking"""
    
    def __init__(self, name: str, metrics_collector: Optional[MetricsCollector] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.metrics = metrics_collector or MetricsCollector()
        self.log_events: deque = deque(maxlen=1000)
        self._setup_formatter()
    
    def _setup_formatter(self):
        """Setup structured log formatter"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _log_with_context(self, level: str, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log with structured context"""
        correlation_id = CorrelationContext.get_correlation_id() or 'unknown'
        
        # Create log event
        log_event = LogEvent(
            timestamp=datetime.now(),
            level=level,
            message=message,
            module=self.name,
            function=kwargs.get('function', 'unknown'),
            correlation_id=correlation_id,
            event_type=kwargs.get('event_type', 'log'),
            context=context or {},
            duration_ms=kwargs.get('duration_ms')
        )
        
        # Store structured event
        self.log_events.append(log_event)
        
        # Log to standard logger with correlation ID
        extra = {'correlation_id': correlation_id}
        if context:
            extra.update(context)
        
        getattr(self.logger, level.lower())(message, extra=extra)
        
        # Record metrics
        self.metrics.record_counter(f'log_events_total', labels={'level': level, 'module': self.name})
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message"""
        self._log_with_context('INFO', message, context, **kwargs)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message"""
        self._log_with_context('WARNING', message, context, **kwargs)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log error message"""
        self._log_with_context('ERROR', message, context, **kwargs)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log critical message"""
        self._log_with_context('CRITICAL', message, context, **kwargs)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message"""
        self._log_with_context('DEBUG', message, context, **kwargs)
    
    def trade_event(self, event_type: str, symbol: str, context: Dict[str, Any]):
        """Log trading-specific event"""
        self.info(
            f"Trade event: {event_type}",
            context={'symbol': symbol, 'event_type': event_type, **context},
            event_type='trade'
        )
        self.metrics.record_counter('trade_events_total', labels={'type': event_type, 'symbol': symbol})
    
    def api_call(self, endpoint: str, duration_ms: float, status_code: int, context: Optional[Dict[str, Any]] = None):
        """Log API call with timing"""
        self.info(
            f"API call: {endpoint}",
            context={'endpoint': endpoint, 'status_code': status_code, 'duration_ms': duration_ms, **(context or {})},
            event_type='api_call',
            duration_ms=duration_ms
        )
        
        # Record API metrics
        self.metrics.record_counter('api_calls_total', labels={'endpoint': endpoint, 'status': str(status_code)})
        self.metrics.record_timing('api_call_duration_ms', duration_ms, labels={'endpoint': endpoint})
        
        if status_code >= 400:
            self.metrics.record_counter('api_errors_total', labels={'endpoint': endpoint, 'status': str(status_code)})
    
    def get_recent_logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent log events"""
        events = list(self.log_events)
        
        if level:
            events = [e for e in events if e.level == level.upper()]
        
        events = sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [asdict(event) for event in events]


class MonitoringSystem:
    """Complete monitoring system for trading agent"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.loggers: Dict[str, StructuredLogger] = {}
        self.start_time = datetime.now()
        
        # Trading-specific metrics
        self.initialize_trading_metrics()
    
    def initialize_trading_metrics(self):
        """Initialize trading-specific metrics"""
        # Reset key counters
        self.metrics.record_counter('trades_total', 0)
        self.metrics.record_counter('trades_successful', 0)
        self.metrics.record_counter('trades_failed', 0)
        self.metrics.record_counter('signals_generated', 0)
        self.metrics.record_counter('risk_approvals', 0)
        self.metrics.record_counter('risk_rejections', 0)
        
        # Initialize gauges
        self.metrics.record_gauge('portfolio_value', 0.0)
        self.metrics.record_gauge('total_pnl', 0.0)
        self.metrics.record_gauge('open_positions', 0.0)
        self.metrics.record_gauge('daily_trades', 0.0)
    
    def get_logger(self, name: str) -> StructuredLogger:
        """Get or create logger for module"""
        if name not in self.loggers:
            self.loggers[name] = StructuredLogger(name, self.metrics)
        return self.loggers[name]
    
    def record_trade_execution(self, symbol: str, side: str, quantity: float, price: float, success: bool, duration_ms: float):
        """Record trade execution metrics"""
        labels = {'symbol': symbol, 'side': side}
        
        self.metrics.record_counter('trades_total', labels=labels)
        if success:
            self.metrics.record_counter('trades_successful', labels=labels)
        else:
            self.metrics.record_counter('trades_failed', labels=labels)
        
        self.metrics.record_timing('trade_execution_duration_ms', duration_ms, labels=labels)
        self.metrics.record_histogram('trade_quantity', quantity, labels=labels)
        self.metrics.record_histogram('trade_price', price, labels=labels)
    
    def record_signal_generation(self, symbol: str, signal_type: str, confidence: float, duration_ms: float):
        """Record signal generation metrics"""
        labels = {'symbol': symbol, 'signal': signal_type}
        
        self.metrics.record_counter('signals_generated', labels=labels)
        self.metrics.record_histogram('signal_confidence', confidence, labels=labels)
        self.metrics.record_timing('signal_generation_duration_ms', duration_ms, labels=labels)
    
    def record_risk_assessment(self, symbol: str, approved: bool, risk_level: str, duration_ms: float):
        """Record risk assessment metrics"""
        labels = {'symbol': symbol, 'risk_level': risk_level}
        
        if approved:
            self.metrics.record_counter('risk_approvals', labels=labels)
        else:
            self.metrics.record_counter('risk_rejections', labels=labels)
        
        self.metrics.record_timing('risk_assessment_duration_ms', duration_ms, labels=labels)
    
    def update_portfolio_metrics(self, portfolio_value: float, total_pnl: float, open_positions: int, daily_trades: int):
        """Update portfolio-level metrics"""
        self.metrics.record_gauge('portfolio_value', portfolio_value)
        self.metrics.record_gauge('total_pnl', total_pnl)
        self.metrics.record_gauge('open_positions', float(open_positions))
        self.metrics.record_gauge('daily_trades', float(daily_trades))
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate error rates
        total_trades = self.metrics.get_counter('trades_total')
        failed_trades = self.metrics.get_counter('trades_failed')
        error_rate = (failed_trades / total_trades) if total_trades > 0 else 0
        
        total_api_calls = self.metrics.get_counter('api_calls_total')
        api_errors = self.metrics.get_counter('api_errors_total')
        api_error_rate = (api_errors / total_api_calls) if total_api_calls > 0 else 0
        
        return {
            'status': 'healthy' if error_rate < config.monitoring_error_rate_threshold and api_error_rate < config.monitoring_api_error_rate_threshold else 'degraded',
            'uptime_seconds': uptime,
            'trade_error_rate': error_rate,
            'api_error_rate': api_error_rate,
            'total_trades': total_trades,
            'portfolio_value': self.metrics.get_gauge('portfolio_value', {}),
            'open_positions': int(self.metrics.get_gauge('open_positions', {}) or 0),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'trade_execution': self.metrics.get_timing_stats('trade_execution_duration_ms'),
            'signal_generation': self.metrics.get_timing_stats('signal_generation_duration_ms'),
            'risk_assessment': self.metrics.get_timing_stats('risk_assessment_duration_ms'),
            'api_calls': self.metrics.get_timing_stats('api_call_duration_ms'),
            'signal_confidence': self.metrics.get_histogram_stats('signal_confidence'),
            'trade_volumes': self.metrics.get_histogram_stats('trade_quantity')
        }
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Add help and type information
        lines.append('# HELP trades_total Total number of trades executed')
        lines.append('# TYPE trades_total counter')
        
        # Export counters
        for key, value in self.metrics.counters.items():
            metric_name = key.split('{')[0]
            labels = ''
            if '{' in key:
                labels = '{' + key.split('{')[1]
            lines.append(f'{metric_name}{labels} {value}')
        
        # Export gauges
        lines.append('# HELP portfolio_value Current portfolio value')
        lines.append('# TYPE portfolio_value gauge')
        for key, value in self.metrics.gauges.items():
            metric_name = key.split('{')[0]
            labels = ''
            if '{' in key:
                labels = '{' + key.split('{')[1]
            lines.append(f'{metric_name}{labels} {value}')
        
        return '\n'.join(lines)


# Global monitoring instance
monitoring = MonitoringSystem()


# Decorators for automatic monitoring
def monitor_execution(operation_type: str, include_args: bool = False):
    """Decorator to monitor function execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            correlation_id = CorrelationContext.get_correlation_id() or str(uuid.uuid4())
            CorrelationContext.set_correlation_id(correlation_id)
            
            logger = monitoring.get_logger(func.__module__)
            start_time = time.time()
            
            try:
                # Log function start
                context = {'operation': operation_type, 'function': func.__name__}
                if include_args and args:
                    context['args'] = str(args[:2])  # Limit args for security
                
                logger.info(f"Starting {operation_type}: {func.__name__}", context=context, function=func.__name__)
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Log success
                logger.info(
                    f"Completed {operation_type}: {func.__name__}",
                    context={'operation': operation_type, 'function': func.__name__, 'duration_ms': duration_ms},
                    function=func.__name__,
                    duration_ms=duration_ms
                )
                
                # Record timing metric
                monitoring.metrics.record_timing(f'{operation_type}_duration_ms', duration_ms, labels={'function': func.__name__})
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log error
                logger.error(
                    f"Failed {operation_type}: {func.__name__} - {str(e)}",
                    context={'operation': operation_type, 'function': func.__name__, 'error': str(e), 'duration_ms': duration_ms},
                    function=func.__name__,
                    duration_ms=duration_ms
                )
                
                # Record error metric
                monitoring.metrics.record_counter(f'{operation_type}_errors_total', labels={'function': func.__name__})
                
                raise
        
        return wrapper
    return decorator


@contextmanager
def correlation_context(correlation_id: Optional[str] = None):
    """Context manager for correlation tracking"""
    original_id = CorrelationContext.get_correlation_id()
    
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    try:
        CorrelationContext.set_correlation_id(correlation_id)
        yield correlation_id
    finally:
        if original_id:
            CorrelationContext.set_correlation_id(original_id)
        else:
            CorrelationContext.clear()


# Demo function
def demo_monitoring_system():
    """Demo the monitoring and logging system"""
    print("=== Monitoring & Logging System Demo ===")
    
    # Get logger
    logger = monitoring.get_logger('demo')
    
    # Demo correlation context
    with correlation_context('demo-session-123') as corr_id:
        logger.info("Starting demo", context={'demo_type': 'monitoring'})
        
        # Simulate some trading operations
        monitoring.record_signal_generation('BTCUSDT', 'BUY', 0.85, 15.5)
        monitoring.record_risk_assessment('BTCUSDT', True, 'low', 8.2)
        monitoring.record_trade_execution('BTCUSDT', 'BUY', 0.001, 50000.0, True, 120.5)
        
        # Log trade event
        logger.trade_event('order_filled', 'BTCUSDT', {'quantity': 0.001, 'price': 50000.0})
        
        # Simulate API call
        logger.api_call('/api/v3/order', 95.3, 200, {'order_id': 'test_123'})
        
        # Update portfolio metrics
        monitoring.update_portfolio_metrics(105000.0, 5000.0, 3, 15)
    
    # Show health status
    print("\n--- Health Status ---")
    health = monitoring.get_health_status()
    for key, value in health.items():
        print(f"{key}: {value}")
    
    # Show performance metrics
    print("\n--- Performance Metrics ---")
    perf = monitoring.get_performance_metrics()
    for category, stats in perf.items():
        if stats:
            print(f"{category}: {stats}")
    
    # Show recent logs
    print("\n--- Recent Logs ---")
    recent_logs = logger.get_recent_logs(limit=5)
    for log in recent_logs:
        print(f"{log['timestamp']}: {log['level']} - {log['message']}")
    
    # Show metrics summary
    print("\n--- Metrics Summary ---")
    summary = monitoring.metrics.get_summary()
    for key, value in summary.items():
        if isinstance(value, dict) and len(value) > 0:
            print(f"{key}: {len(value)} entries")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    demo_monitoring_system()