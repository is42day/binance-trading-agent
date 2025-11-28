"""
Trading Strategies Module

This module provides a modular approach to trading strategies, making them
easily testable and swappable.
"""

from .base_strategy import BaseStrategy, SignalType, StrategyResult
from .combined_strategy import CombinedStrategy
from .macd_strategy import MACDStrategy
from .rsi_strategy import RSIStrategy
from .strategy_manager import StrategyManager

__all__ = [
    "BaseStrategy",
    "StrategyResult",
    "SignalType",
    "RSIStrategy",
    "MACDStrategy",
    "CombinedStrategy",
    "StrategyManager",
]
