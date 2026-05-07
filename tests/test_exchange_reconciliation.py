from binance_trade_agent.agents.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.core.exchange_reconciliation import ExchangeReconciliationService
from binance_trade_agent.core.portfolio_manager import PortfolioManager


class StubClient:
    def __init__(self, order):
        self.order = order

    def get_order(self, symbol, order_id=None, client_order_id=None):
        return self.order

    def get_account_trades(self, symbol, order_id=None, limit=100):
        return [{"commission": "0.001"}]


def test_client_order_id_is_stable_for_same_correlation():
    agent = TradeExecutionAgent.__new__(TradeExecutionAgent)

    first = agent._build_client_order_id("BTCUSDT", "BUY", "MARKET", 0.001, "corr-1")
    second = agent._build_client_order_id("BTCUSDT", "BUY", "MARKET", 0.001, "corr-1")

    assert first == second
    assert first.startswith("bta_")
    assert len(first) <= 36


def test_reconciliation_books_missing_filled_trade(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "portfolio.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    portfolio = PortfolioManager(str(tmp_path / "portfolio.db"), use_shared_session=False)
    portfolio.upsert_exchange_order(
        {
            "client_order_id": "bta_reconcile_1",
            "order_id": "1001",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "status": "NEW",
            "quantity": 0.001,
            "executed_quantity": 0.0,
            "correlation_id": "corr-1",
        }
    )

    service = ExchangeReconciliationService(
        client=StubClient(
            {
                "symbol": "BTCUSDT",
                "orderId": 1001,
                "clientOrderId": "bta_reconcile_1",
                "origQty": "0.001",
                "executedQty": "0.001",
                "cummulativeQuoteQty": "50",
                "status": "FILLED",
                "type": "MARKET",
                "side": "BUY",
            }
        ),
        portfolio=portfolio,
    )

    result = service.reconcile_open_orders("BTCUSDT")

    assert result["checked"] == 1
    assert result["booked_trades"] == 1
    trade = portfolio.get_trade_by_client_order_id("bta_reconcile_1")
    assert trade["order_id"] == "1001"
    assert trade["price"] == 50000.0


def test_reconciliation_picks_up_filled_order_without_local_trade(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "portfolio.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    portfolio = PortfolioManager(str(tmp_path / "portfolio.db"), use_shared_session=False)
    portfolio.upsert_exchange_order(
        {
            "client_order_id": "bta_reconcile_filled",
            "order_id": "1003",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "status": "FILLED",
            "quantity": 0.001,
            "executed_quantity": 0.001,
            "avg_fill_price": 50000.0,
        }
    )

    service = ExchangeReconciliationService(
        client=StubClient(
            {
                "symbol": "BTCUSDT",
                "orderId": 1003,
                "clientOrderId": "bta_reconcile_filled",
                "origQty": "0.001",
                "executedQty": "0.001",
                "cummulativeQuoteQty": "50",
                "status": "FILLED",
                "type": "MARKET",
                "side": "BUY",
            }
        ),
        portfolio=portfolio,
    )

    result = service.reconcile_open_orders("BTCUSDT")

    assert result["checked"] == 1
    assert result["booked_trades"] == 1
    assert portfolio.get_trade_by_client_order_id("bta_reconcile_filled") is not None


def test_reconciliation_does_not_book_duplicate_trade(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "portfolio.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    portfolio = PortfolioManager(str(tmp_path / "portfolio.db"), use_shared_session=False)
    portfolio.upsert_exchange_order(
        {
            "client_order_id": "bta_reconcile_2",
            "order_id": "1002",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "MARKET",
            "status": "NEW",
            "quantity": 0.001,
            "executed_quantity": 0.0,
        }
    )
    portfolio.add_trade(
        trade_id="1002",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        price=50000.0,
        fee=0.0,
        order_id="1002",
        client_order_id="bta_reconcile_2",
    )

    service = ExchangeReconciliationService(
        client=StubClient(
            {
                "symbol": "BTCUSDT",
                "orderId": 1002,
                "clientOrderId": "bta_reconcile_2",
                "origQty": "0.001",
                "executedQty": "0.001",
                "cummulativeQuoteQty": "50",
                "status": "FILLED",
                "type": "MARKET",
                "side": "BUY",
            }
        ),
        portfolio=portfolio,
    )

    result = service.reconcile_open_orders("BTCUSDT")

    assert result["booked_trades"] == 0
    assert len(portfolio.get_trade_history()) == 1
