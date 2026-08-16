"""
Tests that emergency stop actually halts the autonomous trading loop.

Regression coverage for the gap where triggering emergency stop only blocked
*new* validated entries (via risk_agent.validate_trade) while the loop kept
cycling, and trailing-stop closes bypassed validate_trade entirely and could
still place real orders.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _no_exchange_reconcile(monkeypatch):
    # Avoid hitting the reconciliation path (network/DB) during construction.
    monkeypatch.setenv("EXCHANGE_RECONCILE_ON_START", "false")


def _build_loop():
    from binance_trade_agent.core.autonomous_trading_loop import AutonomousTradingLoop

    loop = AutonomousTradingLoop(
        symbols=["BTCUSDT"],
        trade_interval_seconds=60,
        duration_minutes=1,
        strategy_name="combined_default",
    )
    loop.orchestrator.execution_agent = MagicMock()
    loop.orchestrator.market_agent = MagicMock()
    return loop


class TestTrailingStopsRespectEmergencyStop:
    @pytest.mark.asyncio
    async def test_triggered_trailing_stop_is_not_closed_during_emergency_stop(self):
        loop = _build_loop()
        risk_agent = loop.orchestrator.risk_agent
        risk_agent.set_emergency_stop(True, "test halt")

        # Even if a stop would otherwise trigger, place_sell_order/place_buy_order
        # must never be called while emergency stop is active.
        risk_agent.get_trailing_stop_info = MagicMock(
            return_value={"positions": {"BTCUSDT": {}}, "active_stops": 1}
        )
        risk_agent.update_all_trailing_stops = MagicMock(
            return_value={
                "BTCUSDT": {
                    "stop_triggered": True,
                    "side": "buy",
                    "entry_price": 100.0,
                    "current_stop": 95.0,
                    "current_price": 94.0,
                }
            }
        )

        await loop._update_trailing_stops()

        loop.orchestrator.execution_agent.place_sell_order.assert_not_called()
        loop.orchestrator.execution_agent.place_buy_order.assert_not_called()
        risk_agent.get_trailing_stop_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_trailing_stop_closes_normally_when_not_stopped(self):
        loop = _build_loop()
        risk_agent = loop.orchestrator.risk_agent
        assert risk_agent._shared_emergency_stop_enabled() is False

        risk_agent.get_trailing_stop_info = MagicMock(
            return_value={"positions": {"BTCUSDT": {}}, "active_stops": 1}
        )
        loop.orchestrator.market_agent.get_latest_price = MagicMock(return_value=94.0)
        risk_agent.update_all_trailing_stops = MagicMock(
            return_value={
                "BTCUSDT": {
                    "stop_triggered": True,
                    "side": "buy",
                    "entry_price": 100.0,
                    "current_stop": 95.0,
                    "current_price": 94.0,
                }
            }
        )
        risk_agent.close_trailing_stop = MagicMock(return_value={"pnl_pct": -0.06})
        loop.orchestrator.execution_agent.place_sell_order = MagicMock(
            return_value={"orderId": "123"}
        )

        await loop._update_trailing_stops()

        loop.orchestrator.execution_agent.place_sell_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_emergency_stop_activated_mid_call_still_blocks_the_order(self):
        """
        Emergency stop is cross-process shared state — it can be activated by
        another process after the once-per-call check at the top of
        _update_trailing_stops but before a specific triggered stop's order
        is placed. The per-order recheck must catch this.
        """
        loop = _build_loop()
        risk_agent = loop.orchestrator.risk_agent

        # False for the top-of-method check, True for the per-order recheck.
        risk_agent._shared_emergency_stop_enabled = MagicMock(side_effect=[False, True])

        risk_agent.get_trailing_stop_info = MagicMock(
            return_value={"positions": {"BTCUSDT": {}}, "active_stops": 1}
        )
        loop.orchestrator.market_agent.get_latest_price = MagicMock(return_value=94.0)
        risk_agent.update_all_trailing_stops = MagicMock(
            return_value={
                "BTCUSDT": {
                    "stop_triggered": True,
                    "side": "buy",
                    "entry_price": 100.0,
                    "current_stop": 95.0,
                    "current_price": 94.0,
                }
            }
        )

        await loop._update_trailing_stops()

        loop.orchestrator.execution_agent.place_sell_order.assert_not_called()
        loop.orchestrator.execution_agent.place_buy_order.assert_not_called()


class TestRunLoopRespectsEmergencyStop:
    @pytest.mark.asyncio
    async def test_run_skips_trade_execution_while_emergency_stop_active(self):
        loop = _build_loop()
        loop.duration_minutes = 0
        loop.orchestrator.risk_agent.set_emergency_stop(True, "test halt")
        loop.orchestrator.execute_trading_workflow = AsyncMock()

        async def _stop_after_sleep(*_args, **_kwargs):
            loop.stop_flag = True

        with patch("asyncio.sleep", side_effect=_stop_after_sleep):
            await loop.run()

        loop.orchestrator.execute_trading_workflow.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_executes_trades_when_not_stopped(self):
        from binance_trade_agent.core.orchestrator import TradeDecision

        loop = _build_loop()
        loop.duration_minutes = 0
        loop.orchestrator.execute_trading_workflow = AsyncMock(
            return_value=TradeDecision(
                symbol="BTCUSDT",
                signal_type="hold",
                confidence=0.5,
                price=100.0,
                quantity=0.001,
                timestamp=datetime.now(),
                correlation_id="test",
                risk_approved=False,
                executed=False,
            )
        )

        async def _stop_after_sleep(*_args, **_kwargs):
            loop.stop_flag = True

        with patch("asyncio.sleep", side_effect=_stop_after_sleep):
            await loop.run()

        loop.orchestrator.execute_trading_workflow.assert_called_once()
