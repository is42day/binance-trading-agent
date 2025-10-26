"""
Trading Strategies Module

This module provides a modular approach to trading strategies, making them
easily testable and swappable.
"""

from .base_strategy import BaseStrategy, StrategyResult
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy
from .combined_strategy import CombinedStrategy
from .strategy_manager import StrategyManager

__all__ = [
    'BaseStrategy',
    'StrategyResult', 
    'RSIStrategy',
    'MACDStrategy',
    'CombinedStrategy',
    'StrategyManager'
]