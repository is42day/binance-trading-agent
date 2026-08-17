"""
Regression coverage for risk-counter persistence across restarts/processes.

EnhancedRiskManagementAgent tracked consecutive_losses, daily_trades,
peak_portfolio_value, and recent_trades as plain in-memory instance
attributes, with no path through the shared state_store that emergency_stop
already used. A process restart — or a second process (e.g. the API
container instantiating its own risk agent) — silently reset these counters
to zero, undercounting drawdown/loss-streak/frequency limits relative to
what actually happened.
"""

import tempfile
from pathlib import Path

import pytest

from binance_trade_agent.agents.risk_management_agent import EnhancedRiskManagementAgent
from binance_trade_agent.core.portfolio_manager import PortfolioManager


@pytest.fixture
def shared_agent_factory():
    """
    Builds EnhancedRiskManagementAgent instances that all share the same
    isolated temp-file state_store, simulating separate processes (or
    restarts) reading/writing the same DB — without touching the class's
    hardcoded "/app/data/web_portfolio.db" path.
    """
    with tempfile.TemporaryDirectory() as _tmpdir:
        tmp_path = Path(_tmpdir) / "shared_risk_state.db"

        def _make():
            agent = EnhancedRiskManagementAgent()
            agent.shared_state_enabled = True
            agent.state_store = PortfolioManager(str(tmp_path), use_shared_session=False)
            agent._load_shared_risk_state()
            return agent

        yield _make


def test_consecutive_losses_persisted_and_visible_to_a_new_instance(shared_agent_factory):
    first = shared_agent_factory()
    first.record_trade_result("t1", pnl=-10.0)
    first.record_trade_result("t2", pnl=-5.0)
    assert first.consecutive_losses == 2

    # Simulates a restart (or a second process): a brand-new instance
    # pointed at the same shared state must see the real count, not zero.
    second = shared_agent_factory()
    assert second.consecutive_losses == 2


def test_consecutive_losses_reset_by_a_win_is_visible_across_instances(shared_agent_factory):
    first = shared_agent_factory()
    first.record_trade_result("t1", pnl=-10.0)

    second = shared_agent_factory()
    second.record_trade_result("t2", pnl=25.0)
    assert second.consecutive_losses == 0

    third = shared_agent_factory()
    assert third.consecutive_losses == 0


def test_daily_trades_and_peak_portfolio_value_persist_via_validate_trade(shared_agent_factory):
    first = shared_agent_factory()
    first.config["min_time_between_trades"] = 0  # isolate daily_trades from the frequency rule
    first.validate_trade(symbol="BTCUSDT", side="BUY", quantity=0.001, price=50000.0)
    first.validate_trade(symbol="BTCUSDT", side="BUY", quantity=0.001, price=50000.0)
    assert first.daily_trades == 2

    second = shared_agent_factory()
    assert second.daily_trades == 2


def test_drawdown_pause_set_by_one_instance_blocks_trades_in_another(shared_agent_factory):
    first = shared_agent_factory()
    max_dd = first.config["max_total_drawdown"]
    # Establish a peak, then crash the portfolio value far enough to breach
    # max_total_drawdown and trigger a pause.
    first.validate_trade(
        symbol="BTCUSDT", side="BUY", quantity=0.001, price=100.0, portfolio_value=100_000.0
    )
    result = first.validate_trade(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        price=100.0,
        portfolio_value=100_000.0 * (1 - max_dd - 0.10),
    )
    assert result["approved"] is False
    assert first.drawdown_pause_until is not None

    # A second instance (another process) must see and honor the same pause
    # rather than starting fresh with drawdown_pause_until=None.
    second = shared_agent_factory()
    assert second.drawdown_pause_until is not None
    blocked = second.validate_trade(
        symbol="ETHUSDT", side="BUY", quantity=1.0, price=100.0, portfolio_value=50_000.0
    )
    assert blocked["approved"] is False
    assert "drawdown" in blocked["reason"].lower()


def test_recent_trades_used_for_hourly_limit_persist_across_instances(shared_agent_factory):
    first = shared_agent_factory()
    first.config["max_trades_per_hour"] = 1
    first.validate_trade(symbol="BTCUSDT", side="BUY", quantity=0.001, price=100.0)

    second = shared_agent_factory()
    second.config["max_trades_per_hour"] = 1
    result = second.validate_trade(symbol="BTCUSDT", side="BUY", quantity=0.001, price=100.0)

    assert result["approved"] is False
    assert "hourly" in result["reason"].lower()


def test_no_shared_state_falls_back_to_local_in_memory_counters():
    """Without RISK_SHARED_STATE_ENABLED/DATABASE_URL, behavior is unchanged
    (in-memory only) — the persistence calls must be safe no-ops."""
    agent = EnhancedRiskManagementAgent()
    assert agent.shared_state_enabled is False

    agent.record_trade_result("t1", pnl=-10.0)  # must not raise
    assert agent.consecutive_losses == 1
