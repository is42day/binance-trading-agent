"""
Configuration management for Binance Trading Agent
Loads settings from environment variables with sensible defaults
"""
import os
from typing import Dict, Any
from pathlib import Path


class Config:
    def validate(self):
        """
        Validate configuration for required API keys and testnet settings.
        Raises SystemExit with error if invalid.
        """
        if self.binance_testnet:
            if not self.binance_api_key or not self.binance_api_secret:
                print("[ERROR] Testnet mode requires BINANCE_API_KEY and BINANCE_API_SECRET to be set in the environment.")
                print("Set these variables and restart the agent.")
                raise SystemExit(1)
        if not self.demo_mode and (not self.binance_api_key or not self.binance_api_secret):
            print("[ERROR] Live trading mode requires BINANCE_API_KEY and BINANCE_API_SECRET.")
            raise SystemExit(1)
    """Centralized configuration management"""

    def __init__(self):
        # API Configuration
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_api_secret = os.getenv('BINANCE_API_SECRET')
        self.binance_testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'

        # Server Configuration
        self.mcp_server_port = int(os.getenv('MCP_SERVER_PORT', '8080'))
        self.web_ui_port = int(os.getenv('WEB_UI_PORT', '8501'))
        self.monitoring_port = int(os.getenv('MONITORING_PORT', '9090'))

        # Demo Mode Configuration
        self.demo_mode = os.getenv('DEMO_MODE', 'false').lower() == 'true'
        if not self.binance_api_key or not self.binance_api_secret:
            self.demo_mode = True  # Force demo mode if no API keys

        # Risk Management Configuration
        self.risk_max_position_per_symbol = float(os.getenv('RISK_MAX_POSITION_PER_SYMBOL', '0.05'))
        self.risk_max_total_exposure = float(os.getenv('RISK_MAX_TOTAL_EXPOSURE', '0.8'))
        self.risk_max_single_trade_size = float(os.getenv('RISK_MAX_SINGLE_TRADE_SIZE', '0.02'))
        self.risk_default_stop_loss_pct = float(os.getenv('RISK_DEFAULT_STOP_LOSS_PCT', '0.02'))
        self.risk_default_take_profit_pct = float(os.getenv('RISK_DEFAULT_TAKE_PROFIT_PCT', '0.06'))
        self.risk_trailing_stop_pct = float(os.getenv('RISK_TRAILING_STOP_PCT', '0.01'))
        self.risk_max_daily_drawdown = float(os.getenv('RISK_MAX_DAILY_DRAWDOWN', '0.05'))
        self.risk_max_total_drawdown = float(os.getenv('RISK_MAX_TOTAL_DRAWDOWN', '0.15'))
        self.risk_volatility_threshold = float(os.getenv('RISK_VOLATILITY_THRESHOLD', '0.05'))

        # Trading Configuration
        self.trading_default_quantity_btc = float(os.getenv('TRADING_DEFAULT_QUANTITY_BTC', '0.001'))
        self.trading_default_quantity_eth = float(os.getenv('TRADING_DEFAULT_QUANTITY_ETH', '0.01'))
        self.trading_default_quantity_usdt = float(os.getenv('TRADING_DEFAULT_QUANTITY_USDT', '10.0'))
        self.trading_min_order_size_btc = float(os.getenv('TRADING_MIN_ORDER_SIZE_BTC', '0.000001'))
        self.trading_min_order_size_eth = float(os.getenv('TRADING_MIN_ORDER_SIZE_ETH', '0.00001'))

        # Signal Configuration
        self.signal_rsi_overbought = int(os.getenv('SIGNAL_RSI_OVERBOUGHT', '70'))
        self.signal_rsi_oversold = int(os.getenv('SIGNAL_RSI_OVERSOLD', '30'))
        self.signal_macd_signal_window = int(os.getenv('SIGNAL_MACD_SIGNAL_WINDOW', '9'))

        # Monitoring Configuration
        self.monitoring_error_rate_threshold = float(os.getenv('MONITORING_ERROR_RATE_THRESHOLD', '0.1'))
        self.monitoring_api_error_rate_threshold = float(os.getenv('MONITORING_API_ERROR_RATE_THRESHOLD', '0.05'))

        # Portfolio Configuration
        self.portfolio_initial_value = float(os.getenv('PORTFOLIO_INITIAL_VALUE', '100000.0'))

        # Symbol-specific risk overrides
        self.symbol_risk_overrides = {
            'BTCUSDT': {
                'max_position': float(os.getenv('BTC_MAX_POSITION', '0.1')),
                'volatility_multiplier': float(os.getenv('BTC_VOLATILITY_MULTIPLIER', '1.0'))
            },
            'ETHUSDT': {
                'max_position': float(os.getenv('ETH_MAX_POSITION', '0.08')),
                'volatility_multiplier': float(os.getenv('ETH_VOLATILITY_MULTIPLIER', '1.2'))
            }
        }

    def get_symbol_risk_config(self, symbol: str) -> Dict[str, Any]:
        """Get risk configuration for a specific symbol"""
        return self.symbol_risk_overrides.get(symbol, {
            'max_position': 0.05,
            'volatility_multiplier': 1.0
        })

    def get_default_quantity(self, symbol: str) -> float:
        """Get default trading quantity for a symbol"""
        symbol_base = symbol.replace('USDT', '').upper()
        defaults = {
            'BTC': self.trading_default_quantity_btc,
            'ETH': self.trading_default_quantity_eth,
            'USDT': self.trading_default_quantity_usdt,
        }
        return defaults.get(symbol_base, 0.001)

    def is_production_ready(self) -> bool:
        """Check if configuration is ready for production use"""
        return not self.demo_mode and self.binance_api_key and self.binance_api_secret

    def get_risk_config(self) -> Dict[str, Any]:
        """Get all risk-related configuration"""
        return {
            'max_position_per_symbol': self.risk_max_position_per_symbol,
            'max_total_exposure': self.risk_max_total_exposure,
            'max_single_trade_size': self.risk_max_single_trade_size,
            'default_stop_loss_pct': self.risk_default_stop_loss_pct,
            'default_take_profit_pct': self.risk_default_take_profit_pct,
            'trailing_stop_pct': self.risk_trailing_stop_pct,
            'max_daily_drawdown': self.risk_max_daily_drawdown,
            'max_total_drawdown': self.risk_max_total_drawdown,
            'volatility_threshold': self.risk_volatility_threshold,
        }


# Global configuration instance
config = Config()

# Backward compatibility
BINANCE_API_KEY = config.binance_api_key
BINANCE_API_SECRET = config.binance_api_secret
MCP_SERVER_PORT = config.mcp_server_port
