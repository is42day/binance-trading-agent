# binance_trade_agent/async_signal_agent.py
"""
Async SignalAgent: High-performance, non-blocking signal generation.
"""
import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from ..common.config import config
from ..strategies import StrategyManager, StrategyResult
from .async_market_data_agent import AsyncMarketDataAgent


class AsyncSignalAgent:
    """
    Asynchronous Signal Agent using modular trading strategies.
    Designed for high-throughput, concurrent signal generation.
    """

    def __init__(self, market_data_agent: AsyncMarketDataAgent, strategy_name: str = None,
                 strategy_parameters: Dict[str, Any] = None, test_mode: bool = False):
        """
        Initialize AsyncSignalAgent.

        Args:
            market_data_agent: An instance of AsyncMarketDataAgent.
            strategy_name: Name of the strategy to use.
            strategy_parameters: Custom parameters for the strategy.
            test_mode: Enable for predictable signals.
        """
        self.market_agent = market_data_agent
        self.strategy_manager = StrategyManager()
        self.test_mode = test_mode or bool(os.environ.get("SIGNAL_AGENT_TEST_MODE", "").lower() in ("1", "true", "yes"))
        self.current_strategy_name = strategy_name or 'combined_default'

        if strategy_parameters and strategy_name:
            strategy_type = strategy_parameters.get('type', 'combined')
            custom_name = f"{strategy_name}_custom"
            if self.strategy_manager.create_strategy(strategy_type, custom_name, strategy_parameters):
                self.current_strategy_name = custom_name

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"AsyncSignalAgent initialized with strategy: {self.current_strategy_name}")

    async def generate_signal(self, symbol: str, strategy_name: str = None) -> Dict[str, Any]:
        """
        Generate a trading signal asynchronously.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT').
            strategy_name: Override the default strategy for this call.

        Returns:
            A dictionary with the signal, confidence, and other data.
        """
        if self.test_mode:
            import random
            forced_signal = random.choice(["buy", "sell"])
            return {"signal": forced_signal, "confidence": 0.9, "test_mode": True}

        if not self.market_agent:
            return {"signal": "buy", "confidence": 0.8, "mode": "demo"}

        try:
            # Asynchronously fetch OHLCV data
            ohlcv_data = await self.market_agent.fetch_klines(symbol, interval='1h', limit=50)

            if not ohlcv_data or len(ohlcv_data) < 20:
                return {"signal": "hold", "confidence": 0.5, "reason": "insufficient_data"}

            strategy_to_use = strategy_name or self.current_strategy_name
            result = self.strategy_manager.analyze_with_strategy(strategy_to_use, ohlcv_data, symbol)

            if result is None:
                return {"signal": "hold", "confidence": 0.5, "reason": "strategy_analysis_failed"}

            return self._convert_strategy_result(result)

        except Exception as e:
            self.logger.error(f"Async signal generation failed for {symbol}: {str(e)}")
            return {"signal": "hold", "confidence": 0.5, "reason": "error", "error": str(e)}

    async def compare_strategies(self, symbol: str) -> Dict[str, Any]:
        """
        Compare all available strategies for a symbol asynchronously.
        """
        try:
            if not self.market_agent:
                return {"error": "No market data agent available"}

            ohlcv_data = await self.market_agent.fetch_klines(symbol, interval='1h', limit=50)

            if not ohlcv_data or len(ohlcv_data) < 20:
                return {"error": "Insufficient market data"}

            # This part is CPU-bound, so it can remain synchronous
            return self.strategy_manager.compare_strategies(ohlcv_data, symbol)

        except Exception as e:
            self.logger.error(f"Async strategy comparison failed for {symbol}: {str(e)}")
            return {"error": str(e)}

    def _convert_strategy_result(self, result: StrategyResult) -> Dict[str, Any]:
        """Convert StrategyResult to a dictionary."""
        return {
            "signal": result.signal.value.lower(),
            "confidence": result.confidence,
            "indicators": result.indicators,
            "metadata": result.metadata,
            "price_target": result.price_target,
            "stop_loss": result.stop_loss,
            "take_profit": result.take_profit,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None
        }

    def set_strategy(self, strategy_name: str) -> bool:
        """Change the current strategy."""
        if strategy_name in self.strategy_manager.list_strategies():
            self.current_strategy_name = strategy_name
            self.logger.info(f"Strategy changed to: {strategy_name}")
            return True
        else:
            self.logger.error(f"Strategy not found: {strategy_name}")
            return False

    def get_available_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get a list of available strategies."""
        return self.strategy_manager.list_strategies()

    def create_custom_strategy(self, name: str, strategy_type: str, parameters: Dict[str, Any]) -> bool:
        """Create and register a custom strategy."""
        return self.strategy_manager.create_strategy(strategy_type, name, parameters)
