"""
Trading Strategies Module

This module provides a modular approach to trading strategies, making them
easily testable and swappable.
"""

from .base_strategy import BaseStrategy, SignalType, StrategyResult
from .bollinger_strategy import BollingerBandsStrategy
from .buy_strategy_aggressive import BuyStrategyAggressive
from .combined_edge_strategy import (
    CombinedEdgeStrategy,
    create_balanced_edge_strategy,
    create_conservative_edge_strategy,
)
from .combined_strategy import CombinedStrategy
from .edge_strategy import EdgeStrategy
from .execution_strategy import ExecutionStrategy
from .macd_strategy import MACDStrategy
from .micro_trading_strategy import MicroTradingStrategy
from .rsi_strategy import RSIStrategy
from .smart_entry_strategy import SmartEntryStrategy
from .strategy_manager import StrategyManager

__all__ = [
    "BaseStrategy",
    "StrategyResult",
    "SignalType",
    "RSIStrategy",
    "MACDStrategy",
    "CombinedStrategy",
    "BollingerBandsStrategy",
    "EdgeStrategy",
    "ExecutionStrategy",
    "SmartEntryStrategy",
    "MicroTradingStrategy",
    "BuyStrategyAggressive",
    "CombinedEdgeStrategy",
    "create_balanced_edge_strategy",
    "create_conservative_edge_strategy",
    "StrategyManager",
]
