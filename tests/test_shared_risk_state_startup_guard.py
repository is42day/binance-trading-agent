"""
Regression coverage for the live-trading shared-risk-state startup guard.

EnhancedRiskManagementAgent.shared_state_enabled silently defaults to False
(in-memory, per-process risk counters) unless RISK_SHARED_STATE_ENABLED or
DATABASE_URL is set — which docker-compose sets, but a bare
`python start_auto_trading.py` (or any invocation outside compose) does not.
With shared state off, the Emergency Stop button in the API/dashboard
process has no effect on a separately-running trading-agent process. This
is only a real problem once real money is at risk, so the guard only fires
for config.runtime_mode == "live_armed" — testnet/demo trading is unaffected.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _no_exchange_reconcile(monkeypatch):
    # Avoid hitting the reconciliation path (network/DB) during construction.
    monkeypatch.setenv("EXCHANGE_RECONCILE_ON_START", "false")


@pytest.fixture(autouse=True)
def _release_heartbeat_after_each_test():
    """
    _check_no_concurrent_instance() claims the process-wide trading-agent
    heartbeat lease before this module's new check runs, so a test that
    triggers the new check's RuntimeError still leaves a live-looking
    lease behind (construction never reaches release_heartbeat). Without
    clearing it, the next test in this file to construct a real
    AutonomousTradingLoop collides with DuplicateTradingLoopError — same
    root cause as tests/test_autonomous_loop_emergency_stop.py.
    """
    yield
    from binance_trade_agent.core.autonomous_trading_loop import (
        HEARTBEAT_SERVICE_NAME,
    )
    from binance_trade_agent.core.portfolio_manager import PortfolioManager

    PortfolioManager("/app/data/web_portfolio.db").update_heartbeat(
        HEARTBEAT_SERVICE_NAME, status="stopped"
    )


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


def test_refuses_live_armed_start_without_shared_risk_state(monkeypatch):
    from binance_trade_agent.common.config import config

    monkeypatch.delenv("RISK_SHARED_STATE_ENABLED", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "runtime_mode", "live_armed")

    with pytest.raises(RuntimeError, match="risk state is not shared across processes"):
        _build_loop()


def test_rejected_start_does_not_block_an_immediate_retry(monkeypatch):
    """
    Regression: this check must run before _check_no_concurrent_instance()
    claims the heartbeat lease. Claim-then-raise would leave the lease in
    "starting" status with nothing to release it (construction never
    returns), forcing an operator who fixes the config to wait out
    heartbeat_stale_after_seconds (>= 180s) before a retry could succeed,
    even though no loop is actually running.
    """
    from binance_trade_agent.common.config import config

    monkeypatch.delenv("RISK_SHARED_STATE_ENABLED", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "runtime_mode", "live_armed")
    with pytest.raises(RuntimeError):
        _build_loop()

    monkeypatch.setenv("RISK_SHARED_STATE_ENABLED", "true")
    loop = _build_loop()  # must not raise DuplicateTradingLoopError

    loop.release_heartbeat()


def test_allows_live_armed_start_with_risk_shared_state_enabled(monkeypatch):
    from binance_trade_agent.common.config import config

    monkeypatch.setenv("RISK_SHARED_STATE_ENABLED", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "runtime_mode", "live_armed")

    loop = _build_loop()

    loop.release_heartbeat()


@pytest.mark.parametrize("mode", ["demo", "testnet", "live_blocked"])
def test_allows_non_live_armed_start_without_shared_risk_state(monkeypatch, mode):
    from binance_trade_agent.common.config import config

    monkeypatch.delenv("RISK_SHARED_STATE_ENABLED", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "runtime_mode", mode)

    loop = _build_loop()

    loop.release_heartbeat()
