"""
Regression coverage for the concurrency gap: nothing prevented two
AutonomousTradingLoop instances from running against the same portfolio at
once (e.g. an accidental scale-out, or a stale container left over from a
redeploy). The 'heartbeat' table/methods already existed but were never
wired into the trading loop.
"""

import logging
import tempfile
from pathlib import Path

import pytest

from binance_trade_agent.core.autonomous_trading_loop import (
    HEARTBEAT_SERVICE_NAME,
    AutonomousTradingLoop,
    DuplicateTradingLoopError,
)
from binance_trade_agent.core.portfolio_manager import PortfolioManager


@pytest.fixture
def bare_loop():
    """A minimally-constructed loop with an isolated, non-shared portfolio DB."""
    with tempfile.TemporaryDirectory() as _tmpdir:
        tmp_path = Path(_tmpdir)
        portfolio = PortfolioManager(str(tmp_path / "portfolio.db"), use_shared_session=False)

        loop = AutonomousTradingLoop.__new__(AutonomousTradingLoop)
        loop.logger = logging.getLogger("test-autonomous-loop")
        loop.trade_interval = 60
        loop.heartbeat_stale_after_seconds = 180
        loop._heartbeat_portfolio = portfolio

        yield loop
        portfolio.engine.dispose()


def test_allows_start_when_no_prior_heartbeat(bare_loop):
    bare_loop._check_no_concurrent_instance()  # must not raise

    heartbeat = bare_loop._heartbeat_portfolio.get_heartbeat(HEARTBEAT_SERVICE_NAME)
    assert heartbeat["status"] == "starting"


def test_blocks_start_when_heartbeat_is_fresh(bare_loop):
    bare_loop._heartbeat_portfolio.update_heartbeat(HEARTBEAT_SERVICE_NAME, status="healthy")

    with pytest.raises(DuplicateTradingLoopError):
        bare_loop._check_no_concurrent_instance()


def test_allows_start_when_heartbeat_is_stale(bare_loop):
    bare_loop._heartbeat_portfolio.update_heartbeat(HEARTBEAT_SERVICE_NAME, status="healthy")
    # Force the just-written heartbeat to be treated as stale, rather than
    # depending on real wall-clock time passing in the test.
    bare_loop.heartbeat_stale_after_seconds = -1

    bare_loop._check_no_concurrent_instance()  # must not raise

    heartbeat = bare_loop._heartbeat_portfolio.get_heartbeat(HEARTBEAT_SERVICE_NAME)
    assert heartbeat["status"] == "starting"


def test_allows_start_when_previous_instance_stopped_cleanly(bare_loop):
    bare_loop._heartbeat_portfolio.update_heartbeat(HEARTBEAT_SERVICE_NAME, status="stopped")

    bare_loop._check_no_concurrent_instance()  # must not raise despite freshness


def test_refresh_heartbeat_records_status_and_details(bare_loop):
    bare_loop._refresh_heartbeat(status="healthy", details={"cycle": 3})

    heartbeat = bare_loop._heartbeat_portfolio.get_heartbeat(HEARTBEAT_SERVICE_NAME)
    assert heartbeat["status"] == "healthy"
    assert heartbeat["details"]["cycle"] == 3
    assert "pid" in heartbeat["details"]
