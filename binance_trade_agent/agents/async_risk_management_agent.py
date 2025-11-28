# binance_trade_agent/async_risk_management_agent.py
"""
Async Risk Management Agent: High-performance, non-blocking risk assessment.
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..common.config import config
from .risk_management_agent import EnhancedRiskManagementAgent, RiskAssessment, RiskLevel


class AsyncRiskManagementAgent:
    """
    Asynchronous wrapper for the EnhancedRiskManagementAgent.
    This allows the synchronous, CPU-bound risk logic to be run in a
    non-blocking manner within an async application.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the async risk agent.
        It holds an instance of the synchronous agent.
        """
        self.sync_agent = EnhancedRiskManagementAgent(config_file=config_file)
        self.logger = logging.getLogger(__name__)
        self.logger.info("AsyncRiskManagementAgent initialized.")

    async def validate_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        portfolio_value: float = 100000.0,
        current_positions: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run the synchronous trade validation in a thread pool to avoid
        blocking the asyncio event loop.

        Args:
            All arguments are passed directly to the synchronous agent.

        Returns:
            The risk assessment result dictionary.
        """
        loop = asyncio.get_running_loop()

        try:
            # Use run_in_executor to run the blocking function in a separate thread
            result = await loop.run_in_executor(
                None,  # Use the default thread pool executor
                self.sync_agent.validate_trade,
                symbol,
                side,
                quantity,
                price,
                portfolio_value,
                current_positions,
                market_data
            )
            return result
        except Exception as e:
            self.logger.error(f"Async risk validation failed for {symbol}: {e}")
            # Return a default rejection on error
            assessment = RiskAssessment(
                approved=False,
                risk_level=RiskLevel.CRITICAL,
                reasons=[f"An unexpected error occurred during risk validation: {e}"],
                warnings=[]
            )
            return self.sync_agent._format_assessment_result(assessment)

    async def record_trade_result(self, trade_id: str, pnl: float):
        """
        Run the synchronous trade recording in the executor.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self.sync_agent.record_trade_result,
            trade_id,
            pnl
        )

    async def set_emergency_stop(self, enabled: bool, reason: str = ""):
        """

        Run the synchronous emergency stop setting in the executor.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self.sync_agent.set_emergency_stop,
            enabled,
            reason
        )

    async def get_risk_status(self) -> Dict[str, Any]:
        """
        Run the synchronous status retrieval in the executor.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self.sync_agent.get_risk_status
        )
