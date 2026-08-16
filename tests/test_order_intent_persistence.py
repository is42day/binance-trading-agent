"""
Regression coverage for the orphaned-order gap: an order Binance accepts but
whose local write never happens (lost response, timeout, crash) used to be
invisible to the system, since exchange_orders only ever got a row *after* a
successful response was parsed.

TradeExecutionAgent.place_order now writes a PENDING_NEW intent row before
calling the exchange, so reconciliation can discover the order afterwards
even if the create_order call never returns locally.
"""

import tempfile
from pathlib import Path

import pytest

from binance_trade_agent.agents.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.core.exchange_reconciliation import ExchangeReconciliationService
from binance_trade_agent.core.portfolio_manager import PortfolioManager


class StubClient:
    """Minimal Binance client stub for place_order/get_order."""

    def __init__(self, create_order_result=None, create_order_error=None, get_order_result=None):
        self._create_order_result = create_order_result
        self._create_order_error = create_order_error
        self._get_order_result = get_order_result

    def create_order(self, symbol, side, order_type, quantity, price=None, client_order_id=None):
        if self._create_order_error is not None:
            raise self._create_order_error
        return self._create_order_result

    def get_order(self, symbol, order_id=None, client_order_id=None):
        return self._get_order_result

    def get_account_trades(self, symbol, order_id=None, limit=100):
        return []


@pytest.fixture
def agent_with_temp_portfolio(monkeypatch):
    with tempfile.TemporaryDirectory() as _tmpdir:
        tmp_path = Path(_tmpdir)
        monkeypatch.setenv("DB_PATH", str(tmp_path / "portfolio.db"))
        monkeypatch.delenv("DATABASE_URL", raising=False)

        portfolio = PortfolioManager(str(tmp_path / "portfolio.db"), use_shared_session=False)
        agent = TradeExecutionAgent.__new__(TradeExecutionAgent)
        agent.portfolio = portfolio
        yield agent
        portfolio.engine.dispose()


def test_intent_is_persisted_before_the_exchange_call(agent_with_temp_portfolio):
    agent = agent_with_temp_portfolio
    agent.client = StubClient(
        create_order_result={
            "symbol": "BTCUSDT",
            "orderId": 5001,
            "clientOrderId": "bta_intent_1",
            "status": "FILLED",
            "executedQty": "0.001",
            "origQty": "0.001",
            "price": "50000",
            "fills": [{"price": "50000", "commission": "0.001"}],
        }
    )

    result = agent.place_order("BTCUSDT", "BUY", "MARKET", 0.001, client_order_id="bta_intent_1")

    assert result["success"] is True
    # The final upsert overwrote the pre-submit PENDING_NEW row with the real
    # exchange response — no orphaned intent left behind on the happy path.
    order = agent.portfolio.get_exchange_order("bta_intent_1")
    assert order["status"] == "FILLED"


def test_lost_response_still_leaves_a_recoverable_intent_row(agent_with_temp_portfolio):
    """
    Simulates the exact failure this fix targets: create_order reaches Binance
    (conceptually) but raises locally (timeout/connection reset) before a
    response can be parsed. The PENDING_NEW intent row must still exist so
    reconciliation can find the order later.
    """
    agent = agent_with_temp_portfolio
    agent.client = StubClient(create_order_error=ConnectionError("response lost"))

    result = agent.place_order("BTCUSDT", "BUY", "MARKET", 0.001, client_order_id="bta_intent_lost")

    assert result["success"] is False

    order = agent.portfolio.get_exchange_order("bta_intent_lost")
    assert order is not None
    assert order["status"] == "PENDING_NEW"
    assert order["symbol"] == "BTCUSDT"
    assert order["quantity"] == 0.001

    # And it's actually picked up as reconcilable, not silently dropped.
    open_orders = agent.portfolio.get_open_exchange_orders(symbol="BTCUSDT")
    assert any(o["client_order_id"] == "bta_intent_lost" for o in open_orders)


def test_orphaned_intent_is_recovered_by_reconciliation(agent_with_temp_portfolio):
    """
    End-to-end recovery: after a lost response leaves a PENDING_NEW row,
    reconciliation discovers the order actually filled on the exchange and
    books the trade — closing the gap where the order would otherwise vanish
    from the system's view of exposure.
    """
    agent = agent_with_temp_portfolio
    agent.client = StubClient(create_order_error=TimeoutError("no response"))

    result = agent.place_order(
        "BTCUSDT", "SELL", "MARKET", 0.002, client_order_id="bta_intent_recover"
    )
    assert result["success"] is False

    reconciliation_client = StubClient(
        get_order_result={
            "symbol": "BTCUSDT",
            "orderId": 7001,
            "clientOrderId": "bta_intent_recover",
            "origQty": "0.002",
            "executedQty": "0.002",
            "cummulativeQuoteQty": "100",
            "status": "FILLED",
            "type": "MARKET",
            "side": "SELL",
        }
    )
    service = ExchangeReconciliationService(client=reconciliation_client, portfolio=agent.portfolio)

    outcome = service.reconcile_open_orders("BTCUSDT")

    assert outcome["checked"] == 1
    assert outcome["booked_trades"] == 1
    trade = agent.portfolio.get_trade_by_client_order_id("bta_intent_recover")
    assert trade is not None
    assert trade["order_id"] == "7001"
