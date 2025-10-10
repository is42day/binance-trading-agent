# binance_trade_agent/utils.py

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
