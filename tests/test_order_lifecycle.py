"""
Tests for OrderLifecycleService — Task 8.

Covers:
- poll_order: status normalization for NEW, PARTIALLY_FILLED, FILLED, CANCELED, EXPIRED, REJECTED
- PARTIALLY_FILLED does NOT double-book across reconciliation runs (delta tracking)
- A NEW limit order stays in open (non-terminal) state
- cancel_order records cancellation reason and marks order CANCELED
- detect_stale_limit_orders finds orders where price drifted
- place_oco delegates to BinanceAPIClient and records both legs locally
- API endpoints for open / terminal / stale / cancel
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from binance_trade_agent.core.portfolio_manager import Base, PortfolioManager
from binance_trade_agent.core.order_lifecycle import (
    OrderLifecycleService,
    OPEN_STATUSES,
    TERMINAL_STATUSES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    e = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    return e


@pytest.fixture()
def portfolio(engine):
    """PortfolioManager backed by the test in-memory engine (use_shared_session=False)."""
    # Inject the test engine via the db module globals so PortfolioManager picks it up
    import binance_trade_agent.core.db as _db
    from sqlalchemy.orm import sessionmaker as _SM

    old_engine = _db._engine
    old_factory = _db._session_factory
    _db._engine = engine
    _db._session_factory = _SM(bind=engine)

    pm = PortfolioManager(use_shared_session=True)
    yield pm

    _db._engine = old_engine
    _db._session_factory = old_factory


def _make_coid():
    return f"bta_{uuid.uuid4().hex[:20]}"


def _seed_order(portfolio, **overrides) -> Dict[str, Any]:
    """Insert a minimal exchange order into the portfolio DB."""
    coid = overrides.pop("client_order_id", _make_coid())
    record = {
        "client_order_id": coid,
        "order_id": overrides.pop("order_id", str(int(datetime.now().timestamp() * 1000))),
        "symbol": overrides.pop("symbol", "BTCUSDT"),
        "side": overrides.pop("side", "BUY"),
        "order_type": overrides.pop("order_type", "LIMIT"),
        "status": overrides.pop("status", "NEW"),
        "quantity": overrides.pop("quantity", 0.001),
        "executed_quantity": overrides.pop("executed_quantity", 0.0),
        "last_booked_quantity": overrides.pop("last_booked_quantity", 0.0),
        "price": overrides.pop("price", 50000.0),
        "avg_fill_price": overrides.pop("avg_fill_price", None),
        "fee": overrides.pop("fee", 0.0),
        "correlation_id": overrides.pop("correlation_id", None),
        **overrides,
    }
    portfolio.upsert_exchange_order(record)
    return portfolio.get_exchange_order(coid)


def _make_exchange_response(status, exec_qty=0.0, price=50000.0, orig_qty=0.001):
    """Minimal Binance get_order response."""
    quote_qty = exec_qty * price if exec_qty > 0 else 0.0
    return {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "clientOrderId": "test",
        "status": status,
        "origQty": str(orig_qty),
        "executedQty": str(exec_qty),
        "cummulativeQuoteQty": str(quote_qty),
        "price": str(price),
        "type": "LIMIT",
        "side": "BUY",
    }


@pytest.fixture()
def mock_client():
    c = MagicMock()
    c.get_latest_price.return_value = 50000.0
    c.config.demo_mode = True
    return c


@pytest.fixture()
def svc(mock_client, portfolio):
    return OrderLifecycleService(client=mock_client, portfolio=portfolio)


# ---------------------------------------------------------------------------
# Status normalization
# ---------------------------------------------------------------------------


class TestPollOrderStatusNormalization:
    def test_new_order_stays_new(self, svc, mock_client, portfolio):
        local = _seed_order(portfolio, status="NEW")
        coid = local["client_order_id"]
        mock_client.get_order.return_value = _make_exchange_response("NEW")

        result = svc.poll_order(coid, "BTCUSDT")
        assert result["status"] == "NEW"
        assert result["status"] in OPEN_STATUSES

    def test_filled_order_becomes_terminal(self, svc, mock_client, portfolio):
        local = _seed_order(portfolio, status="NEW")
        coid = local["client_order_id"]
        mock_client.get_order.return_value = _make_exchange_response(
            "FILLED", exec_qty=0.001, price=50000.0
        )

        result = svc.poll_order(coid, "BTCUSDT")
        assert result["status"] == "FILLED"
        assert result["status"] in TERMINAL_STATUSES

    def test_canceled_order_becomes_terminal(self, svc, mock_client, portfolio):
        local = _seed_order(portfolio, status="NEW")
        coid = local["client_order_id"]
        mock_client.get_order.return_value = _make_exchange_response("CANCELED")

        result = svc.poll_order(coid, "BTCUSDT")
        assert result["status"] == "CANCELED"
        assert result["status"] in TERMINAL_STATUSES

    def test_expired_order_becomes_terminal(self, svc, mock_client, portfolio):
        local = _seed_order(portfolio, status="NEW")
        coid = local["client_order_id"]
        mock_client.get_order.return_value = _make_exchange_response("EXPIRED")

        result = svc.poll_order(coid, "BTCUSDT")
        assert result["status"] == "EXPIRED"
        assert result["status"] in TERMINAL_STATUSES

    def test_rejected_order_becomes_terminal(self, svc, mock_client, portfolio):
        local = _seed_order(portfolio, status="NEW")
        coid = local["client_order_id"]
        mock_client.get_order.return_value = _make_exchange_response("REJECTED")

        result = svc.poll_order(coid, "BTCUSDT")
        assert result["status"] == "REJECTED"
        assert result["status"] in TERMINAL_STATUSES

    def test_partially_filled_stays_open(self, svc, mock_client, portfolio):
        local = _seed_order(portfolio, status="NEW")
        coid = local["client_order_id"]
        mock_client.get_order.return_value = _make_exchange_response(
            "PARTIALLY_FILLED", exec_qty=0.0005
        )

        result = svc.poll_order(coid, "BTCUSDT")
        assert result["status"] == "PARTIALLY_FILLED"
        assert result["status"] in OPEN_STATUSES

    def test_poll_raises_for_unknown_local_order(self, svc):
        with pytest.raises(ValueError, match="not found"):
            svc.poll_order("nonexistent_id", "BTCUSDT")


# ---------------------------------------------------------------------------
# Partial-fill delta tracking — no double-booking
# ---------------------------------------------------------------------------


class TestPartialFillDelta:
    def test_first_partial_fill_books_delta(self, svc, mock_client, portfolio):
        local = _seed_order(portfolio, status="NEW", executed_quantity=0.0, last_booked_quantity=0.0)
        coid = local["client_order_id"]
        mock_client.get_order.return_value = _make_exchange_response(
            "PARTIALLY_FILLED", exec_qty=0.0005, price=50000.0
        )

        svc.poll_order(coid, "BTCUSDT")

        trades = portfolio.get_trade_history()
        # Should have exactly one trade for 0.0005
        assert len(trades) == 1
        assert abs(trades[0]["quantity"] - 0.0005) < 1e-10

    def test_second_poll_books_only_additional_delta(self, svc, mock_client, portfolio):
        """PARTIALLY_FILLED at 0.0005 → then at 0.0008. Only 0.0003 extra should be booked."""
        local = _seed_order(portfolio, status="NEW")
        coid = local["client_order_id"]

        # First poll: 0.0005 filled
        mock_client.get_order.return_value = _make_exchange_response(
            "PARTIALLY_FILLED", exec_qty=0.0005, price=50000.0
        )
        svc.poll_order(coid, "BTCUSDT")

        # Second poll: 0.0008 filled total
        mock_client.get_order.return_value = _make_exchange_response(
            "PARTIALLY_FILLED", exec_qty=0.0008, price=50000.0
        )
        svc.poll_order(coid, "BTCUSDT")

        trades = portfolio.get_trade_history()
        total_booked = sum(t["quantity"] for t in trades)
        assert len(trades) == 2
        assert abs(total_booked - 0.0008) < 1e-10

    def test_final_fill_books_remaining_delta(self, svc, mock_client, portfolio):
        """PARTIALLY_FILLED at 0.0005 → FILLED at 0.001. Delta of 0.0005 booked second."""
        local = _seed_order(portfolio, status="NEW", quantity=0.001)
        coid = local["client_order_id"]

        mock_client.get_order.return_value = _make_exchange_response(
            "PARTIALLY_FILLED", exec_qty=0.0005, price=50000.0
        )
        svc.poll_order(coid, "BTCUSDT")

        mock_client.get_order.return_value = _make_exchange_response(
            "FILLED", exec_qty=0.001, price=50000.0
        )
        svc.poll_order(coid, "BTCUSDT")

        trades = portfolio.get_trade_history()
        total_booked = sum(t["quantity"] for t in trades)
        assert len(trades) == 2
        assert abs(total_booked - 0.001) < 1e-10

    def test_idempotent_poll_does_not_double_book(self, svc, mock_client, portfolio):
        """Polling the same status twice should not add a second trade."""
        local = _seed_order(portfolio, status="NEW")
        coid = local["client_order_id"]

        filled_response = _make_exchange_response("FILLED", exec_qty=0.001, price=50000.0)
        mock_client.get_order.return_value = filled_response

        svc.poll_order(coid, "BTCUSDT")
        svc.poll_order(coid, "BTCUSDT")  # Second call — should not re-book

        trades = portfolio.get_trade_history()
        assert len(trades) == 1


# ---------------------------------------------------------------------------
# Cancel order
# ---------------------------------------------------------------------------


class TestCancelOrder:
    def test_cancel_records_reason(self, svc, mock_client, portfolio):
        local = _seed_order(portfolio, status="NEW", order_id="99001")
        coid = local["client_order_id"]
        mock_client.cancel_order.return_value = {"status": "CANCELED"}

        result = svc.cancel_order(coid, "BTCUSDT", "stale_price")

        assert result["status"] == "CANCELED"
        assert result["cancel_reason"] == "stale_price"
        mock_client.cancel_order.assert_called_once()

    def test_cancel_requires_local_order(self, svc):
        with pytest.raises(ValueError, match="not found"):
            svc.cancel_order("no_such_id", "BTCUSDT", "test")

    def test_cancel_requires_exchange_order_id(self, svc, portfolio):
        local = _seed_order(portfolio, status="NEW", order_id="")
        coid = local["client_order_id"]
        with pytest.raises(ValueError, match="without an exchange order_id"):
            svc.cancel_order(coid, "BTCUSDT", "stale")


# ---------------------------------------------------------------------------
# Stale order detection
# ---------------------------------------------------------------------------


class TestStaleOrderDetection:
    def test_detects_stale_limit_buy(self, svc, mock_client, portfolio):
        """A limit buy at 50 000 with market at 48 000 (4 % down) is stale."""
        _seed_order(portfolio, status="NEW", order_type="LIMIT", price=50000.0)
        mock_client.get_latest_price.return_value = 48000.0

        stale = svc.detect_stale_limit_orders(price_pct_threshold=1.0)
        assert len(stale) == 1
        assert stale[0]["price_deviation_pct"] > 1.0

    def test_fresh_order_not_stale(self, svc, mock_client, portfolio):
        """A limit buy at 50 000 with market at 50 200 (0.4 %) is not stale at 1 % threshold."""
        _seed_order(portfolio, status="NEW", order_type="LIMIT", price=50000.0)
        mock_client.get_latest_price.return_value = 50200.0

        stale = svc.detect_stale_limit_orders(price_pct_threshold=1.0)
        assert len(stale) == 0

    def test_market_orders_not_stale(self, svc, mock_client, portfolio):
        _seed_order(portfolio, status="NEW", order_type="MARKET", price=None)
        mock_client.get_latest_price.return_value = 40000.0

        stale = svc.detect_stale_limit_orders(price_pct_threshold=1.0)
        assert len(stale) == 0

    def test_terminal_orders_not_stale(self, svc, mock_client, portfolio):
        _seed_order(portfolio, status="FILLED", order_type="LIMIT", price=50000.0)
        mock_client.get_latest_price.return_value = 40000.0

        stale = svc.detect_stale_limit_orders(price_pct_threshold=1.0)
        assert len(stale) == 0


# ---------------------------------------------------------------------------
# OCO
# ---------------------------------------------------------------------------


class TestPlaceOco:
    def test_oco_records_both_legs(self, svc, mock_client, portfolio):
        now = int(datetime.now().timestamp() * 1000)
        mock_client.create_oco_order.return_value = {
            "orderListId": now,
            "contingencyType": "OCO",
            "listStatusType": "EXEC_STARTED",
            "listOrderStatus": "EXECUTING",
            "listClientOrderId": "test_oco",
            "transactionTime": now,
            "symbol": "BTCUSDT",
            "orders": [],
            "orderReports": [
                {
                    "symbol": "BTCUSDT",
                    "orderId": now,
                    "clientOrderId": "lmt_leg",
                    "price": "51000",
                    "origQty": "0.001",
                    "executedQty": "0.0",
                    "status": "NEW",
                    "type": "LIMIT_MAKER",
                    "side": "SELL",
                },
                {
                    "symbol": "BTCUSDT",
                    "orderId": now + 1,
                    "clientOrderId": "stp_leg",
                    "price": "49000",
                    "stopPrice": "49500",
                    "origQty": "0.001",
                    "executedQty": "0.0",
                    "status": "NEW",
                    "type": "STOP_LOSS_LIMIT",
                    "side": "SELL",
                },
            ],
        }

        result = svc.place_oco(
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.001,
            price=51000.0,
            stop_price=49500.0,
            stop_limit_price=49000.0,
        )

        assert result["contingencyType"] == "OCO"
        assert "limit_client_order_id" in result
        assert "stop_client_order_id" in result

        # Both legs should be in the local ledger
        open_orders = portfolio.get_open_exchange_orders()
        coids = [o["client_order_id"] for o in open_orders]
        assert "lmt_leg" in coids
        assert "stp_leg" in coids


# ---------------------------------------------------------------------------
# Terminal orders query
# ---------------------------------------------------------------------------


class TestTerminalOrdersQuery:
    def test_get_terminal_returns_filled(self, svc, portfolio):
        _seed_order(portfolio, status="FILLED")
        _seed_order(portfolio, status="CANCELED")
        _seed_order(portfolio, status="NEW")

        terminal = svc.get_terminal_orders()
        statuses = {o["status"] for o in terminal}
        assert "FILLED" in statuses
        assert "CANCELED" in statuses
        assert "NEW" not in statuses

    def test_get_open_returns_new(self, svc, portfolio):
        _seed_order(portfolio, status="NEW")
        _seed_order(portfolio, status="FILLED")

        open_orders = svc.get_open_orders()
        statuses = {o["status"] for o in open_orders}
        assert "NEW" in statuses
        assert "FILLED" not in statuses


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


class TestOrderLifecycleEndpoints:
    @pytest.fixture(autouse=True)
    def _patch_svc(self):
        """Patch get_order_lifecycle_service with a full MagicMock to avoid real DB access."""
        mock_svc = MagicMock()
        mock_svc.get_open_orders.return_value = []
        mock_svc.get_terminal_orders.return_value = []
        mock_svc.detect_stale_limit_orders.return_value = []
        mock_svc.cancel_order.side_effect = ValueError("not found")
        with patch(
            "binance_trade_agent.core.order_lifecycle.get_order_lifecycle_service",
            return_value=mock_svc,
        ):
            yield

    def test_open_orders_endpoint(self):
        from fastapi.testclient import TestClient
        from binance_trade_agent.api.api import app

        client = TestClient(app)
        resp = client.get("/api/v1/orders/open", headers={"X-API-Token": "test-token"})
        assert resp.status_code == 200
        assert "orders" in resp.json()

    def test_terminal_orders_endpoint(self):
        from fastapi.testclient import TestClient
        from binance_trade_agent.api.api import app

        client = TestClient(app)
        resp = client.get("/api/v1/orders/terminal", headers={"X-API-Token": "test-token"})
        assert resp.status_code == 200
        assert "orders" in resp.json()

    def test_stale_orders_endpoint(self):
        from fastapi.testclient import TestClient
        from binance_trade_agent.api.api import app

        client = TestClient(app)
        resp = client.get("/api/v1/orders/stale", headers={"X-API-Token": "test-token"})
        assert resp.status_code == 200
        assert "orders" in resp.json()

    def test_cancel_order_endpoint_not_found(self):
        from fastapi.testclient import TestClient
        from binance_trade_agent.api.api import app

        client = TestClient(app)
        resp = client.post(
            "/api/v1/orders/nonexistent/cancel",
            params={"symbol": "BTCUSDT", "reason": "test"},
            headers={"X-API-Token": "test-token"},
        )
        assert resp.status_code == 404
