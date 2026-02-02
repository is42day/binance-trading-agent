"""
Trading Strategies Module

This module provides a modular approach to trading strategies, making them
easily testable and swappable.
"""

from .base_strategy import BaseStrategy, SignalType, StrategyResult
from .bollinger_strategy import BollingerBandsStrategy
from .combined_edge_strategy import (
    CombinedEdgeStrategy,
    create_balanced_edge_strategy,
    create_conservative_edge_strategy,
)
from .combined_strategy import CombinedStrategy
from .edge_strategy import EdgeStrategy
from .macd_strategy import MACDStrategy
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
    "SmartEntryStrategy",
    "CombinedEdgeStrategy",
    "create_balanced_edge_strategy",
    "create_conservative_edge_strategy",
    "StrategyManager",
]
