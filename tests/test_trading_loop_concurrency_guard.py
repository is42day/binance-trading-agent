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


def test_release_heartbeat_marks_stopped(bare_loop):
    bare_loop._check_no_concurrent_instance()

    bare_loop.release_heartbeat()

    heartbeat = bare_loop._heartbeat_portfolio.get_heartbeat(HEARTBEAT_SERVICE_NAME)
    assert heartbeat["status"] == "stopped"


def test_release_then_start_never_blocks_on_the_now_stale_check(bare_loop):
    """
    Simulates the dashboard restart path: stop (which releases the lease)
    immediately followed by start. Must succeed without waiting for the
    heartbeat to go stale, since release_heartbeat marks it "stopped".
    """
    bare_loop._check_no_concurrent_instance()
    bare_loop.release_heartbeat()

    bare_loop._check_no_concurrent_instance()  # must not raise


class TestAtomicClaim:
    """
    A plain read-then-write (get_heartbeat + update_heartbeat) has a TOCTOU
    race: two instances starting together can both observe "no live
    heartbeat" before either writes. try_claim_heartbeat closes this with a
    single UPDATE...WHERE / INSERT rather than a separate read and write.
    """

    def test_second_claim_of_a_fresh_lease_fails(self, bare_loop):
        portfolio = bare_loop._heartbeat_portfolio

        first = portfolio.try_claim_heartbeat(HEARTBEAT_SERVICE_NAME, stale_after_seconds=180)
        second = portfolio.try_claim_heartbeat(HEARTBEAT_SERVICE_NAME, stale_after_seconds=180)

        assert first is True
        assert second is False

    def test_claim_of_a_stale_lease_succeeds(self, bare_loop):
        portfolio = bare_loop._heartbeat_portfolio
        portfolio.update_heartbeat(HEARTBEAT_SERVICE_NAME, status="healthy")

        claimed = portfolio.try_claim_heartbeat(HEARTBEAT_SERVICE_NAME, stale_after_seconds=-1)

        assert claimed is True

    def test_claim_of_a_stopped_lease_succeeds_regardless_of_freshness(self, bare_loop):
        portfolio = bare_loop._heartbeat_portfolio
        portfolio.update_heartbeat(HEARTBEAT_SERVICE_NAME, status="stopped")

        claimed = portfolio.try_claim_heartbeat(HEARTBEAT_SERVICE_NAME, stale_after_seconds=180)

        assert claimed is True

    def test_claim_records_status_and_details(self, bare_loop):
        portfolio = bare_loop._heartbeat_portfolio

        portfolio.try_claim_heartbeat(
            HEARTBEAT_SERVICE_NAME, stale_after_seconds=180, details={"pid": 4242}
        )

        heartbeat = portfolio.get_heartbeat(HEARTBEAT_SERVICE_NAME)
        assert heartbeat["status"] == "starting"
        assert heartbeat["details"]["pid"] == 4242


class TestHeartbeatRefreshedDuringCycle:
    @pytest.mark.asyncio
    async def test_heartbeat_refreshed_after_each_symbol_not_just_once_per_cycle(self):
        """
        Regression: refreshing only once at the top of the cycle meant a
        cycle covering many symbols (or a slow one) could let the heartbeat
        go stale before the *next* cycle's refresh, letting another
        instance start while this one is still live and trading.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        with tempfile.TemporaryDirectory() as _tmpdir:
            tmp_path = Path(_tmpdir)
            portfolio = PortfolioManager(str(tmp_path / "portfolio.db"), use_shared_session=False)

            loop = AutonomousTradingLoop.__new__(AutonomousTradingLoop)
            loop.logger = logging.getLogger("test-autonomous-loop")
            loop.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            loop.trade_interval = 60
            loop.duration_minutes = 0
            loop.heartbeat_stale_after_seconds = 180
            loop._heartbeat_portfolio = portfolio
            loop.stop_flag = False
            loop.trades_executed = 0
            loop.stream_trailing_stop_watcher_enabled = False
            loop.orchestrator = MagicMock()
            loop.orchestrator.risk_agent._shared_emergency_stop_enabled = MagicMock(
                return_value=False
            )
            loop.orchestrator.execute_trading_workflow = AsyncMock(
                side_effect=Exception("no orchestrator behavior needed for this test")
            )
            loop._update_trailing_stops = AsyncMock()

            refresh_calls = []
            original_refresh = loop._refresh_heartbeat

            def _tracking_refresh(status="healthy", details=None):
                refresh_calls.append(details)
                return original_refresh(status=status, details=details)

            loop._refresh_heartbeat = _tracking_refresh

            async def _stop_after_sleep(*_args, **_kwargs):
                loop.stop_flag = True

            with patch("asyncio.sleep", side_effect=_stop_after_sleep):
                await loop.run()

            portfolio.engine.dispose()

        # One refresh at the top of the cycle, plus one per symbol.
        assert len(refresh_calls) >= len(loop.symbols)
        per_symbol_refreshes = [d for d in refresh_calls if d and "symbol" in d]
        assert {d["symbol"] for d in per_symbol_refreshes} == set(loop.symbols)
