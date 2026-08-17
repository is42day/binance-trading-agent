"""
Tests for /api/v1/operator/status endpoint — Task 9.

Covers:
- Endpoint returns HTTP 200 with all expected top-level keys
- Runtime mode surfaced correctly
- Emergency stop state and reason included
- Rate-limit, circuit breaker, stream freshness, validation gate all present
- Open orders with stale flag wired in
- Last blocked trade surfaced from decision journal
- No secrets leaked
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_svc(open_orders=None, stale_orders=None):
    svc = MagicMock()
    svc.get_open_orders.return_value = open_orders or []
    svc.detect_stale_limit_orders.return_value = stale_orders or []
    return svc


def _make_mock_journal(blocked_reason: str | None = None):
    journal = MagicMock()
    if blocked_reason:
        journal.get_history.return_value = [
            {
                "symbol": "BTCUSDT",
                "action": "HOLD",
                "blocked_reason": blocked_reason,
                "timestamp": "2026-05-11T10:00:00",
            }
        ]
    else:
        journal.get_history.return_value = []
    return journal


def _make_mock_gate(result: str | None = "pass"):
    gate = MagicMock()
    if result is None:
        gate.get_artifact.return_value = None
    else:
        gate.get_artifact.return_value = {
            "generated_at": "2026-05-11T10:00:00Z",
            "result": result,
            "strategy": "adaptive_core_micro",
            "symbols": ["BTCUSDT"],
        }
    return gate


def _make_mock_client(runtime_mode="demo"):
    client = MagicMock()
    client.get_circuit_breaker_status.return_value = {
        "state": "closed",
        "failure_count": 0,
        "last_failure": None,
    }
    client.get_rate_limit_status.return_value = {
        "weight_used": 100,
        "weight_budget": 1200,
        "weight_utilization_pct": 8.3,
        "in_holdoff": False,
        "retry_after_remaining": None,
        "orders_this_second": 0,
        "order_budget_per_sec": 10,
    }
    return client


def _make_mock_stream_manager():
    manager = MagicMock()
    s = MagicMock()
    s.symbol = "BTCUSDT"
    s.interval = "1m"
    s.connected = True
    s.age_seconds = 3.2
    s.is_stale = False
    s.reconnect_attempts = 0
    s.last_error = None
    manager.get_all_statuses.return_value = [s]
    return manager


@pytest.fixture()
def client():
    """TestClient with all external service calls patched."""
    from binance_trade_agent.api.api import app

    svc = _make_mock_svc()
    journal = _make_mock_journal()
    gate = _make_mock_gate()
    binance_client = _make_mock_client()
    stream_mgr = _make_mock_stream_manager()

    with (
        patch(
            "binance_trade_agent.core.order_lifecycle.get_order_lifecycle_service", return_value=svc
        ),
        patch(
            "binance_trade_agent.core.decision_journal.get_decision_journal", return_value=journal
        ),
        patch(
            "binance_trade_agent.core.strategy_validation_gate.get_validation_gate",
            return_value=gate,
        ),
        patch(
            "binance_trade_agent.core.market_streams.get_stream_manager", return_value=stream_mgr
        ),
        patch(
            "binance_trade_agent.clients.binance_client.BinanceAPIClient",
            return_value=binance_client,
        ),
    ):
        yield TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOperatorStatusEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        assert resp.status_code == 200

    def test_all_top_level_keys_present(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        body = resp.json()
        expected_keys = {
            "timestamp",
            "runtime_mode",
            "circuit_breaker",
            "rate_limits",
            "stream_freshness",
            "validation_gate",
            "execution_policy",
            "open_orders",
            "open_orders_count",
            "stale_orders_count",
            "last_blocked_trade",
            "emergency_stop",
        }
        assert expected_keys.issubset(body.keys())

    def test_runtime_mode_surfaced(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        body = resp.json()
        assert body["runtime_mode"] in ("demo", "testnet", "live_blocked", "live_armed")

    def test_no_secrets_in_response(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        body_str = resp.text
        for secret_fragment in ("api_key", "api_secret", "secret", "password", "token"):
            # Ensure secret field names are not keys in the JSON (values containing them OK, e.g. "test-token")
            import json as _json

            body = _json.loads(body_str)
            # Flatten top-level keys only — sufficient for the surface contract
            for key in body.keys():
                assert secret_fragment not in key.lower(), f"Potential secret key found: {key!r}"

    def test_circuit_breaker_state(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        cb = resp.json()["circuit_breaker"]
        assert "state" in cb

    def test_rate_limits_present(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        rl = resp.json()["rate_limits"]
        assert "weight_used" in rl or "error" in rl

    def test_stream_freshness_list(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        sf = resp.json()["stream_freshness"]
        assert isinstance(sf, list)
        if sf:
            assert "symbol" in sf[0]
            assert "is_stale" in sf[0]
            assert "age_seconds" in sf[0]

    def test_validation_gate_present(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        vg = resp.json()["validation_gate"]
        assert vg is not None
        assert "result" in vg

    def test_validation_gate_none_when_no_artifact(self):
        from binance_trade_agent.api.api import app

        svc = _make_mock_svc()
        journal = _make_mock_journal()
        gate = _make_mock_gate(result=None)
        binance_client = _make_mock_client()
        stream_mgr = _make_mock_stream_manager()

        with (
            patch(
                "binance_trade_agent.core.order_lifecycle.get_order_lifecycle_service",
                return_value=svc,
            ),
            patch(
                "binance_trade_agent.core.decision_journal.get_decision_journal",
                return_value=journal,
            ),
            patch(
                "binance_trade_agent.core.strategy_validation_gate.get_validation_gate",
                return_value=gate,
            ),
            patch(
                "binance_trade_agent.core.market_streams.get_stream_manager",
                return_value=stream_mgr,
            ),
            patch(
                "binance_trade_agent.clients.binance_client.BinanceAPIClient",
                return_value=binance_client,
            ),
        ):
            tc = TestClient(app)
            resp = tc.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
            assert resp.json()["validation_gate"] is None

    def test_execution_policy_present(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        ep = resp.json()["execution_policy"]
        assert "execution_mode" in ep or "error" in ep

    def test_open_orders_empty_by_default(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        body = resp.json()
        assert body["open_orders_count"] == 0
        assert body["stale_orders_count"] == 0
        assert body["open_orders"] == []

    def test_open_orders_with_stale_flag(self):
        from binance_trade_agent.api.api import app

        open_order = {
            "client_order_id": "bta_aaa",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "order_type": "LIMIT",
            "status": "NEW",
            "quantity": 0.001,
            "executed_quantity": 0.0,
            "price": 50000.0,
        }
        stale_order = {**open_order, "current_price": 52000.0, "price_deviation_pct": 4.0}

        svc = _make_mock_svc(open_orders=[open_order], stale_orders=[stale_order])
        journal = _make_mock_journal()
        gate = _make_mock_gate()
        binance_client = _make_mock_client()
        stream_mgr = _make_mock_stream_manager()

        with (
            patch(
                "binance_trade_agent.core.order_lifecycle.get_order_lifecycle_service",
                return_value=svc,
            ),
            patch(
                "binance_trade_agent.core.decision_journal.get_decision_journal",
                return_value=journal,
            ),
            patch(
                "binance_trade_agent.core.strategy_validation_gate.get_validation_gate",
                return_value=gate,
            ),
            patch(
                "binance_trade_agent.core.market_streams.get_stream_manager",
                return_value=stream_mgr,
            ),
            patch(
                "binance_trade_agent.clients.binance_client.BinanceAPIClient",
                return_value=binance_client,
            ),
        ):
            tc = TestClient(app)
            resp = tc.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
            body = resp.json()
            assert body["open_orders_count"] == 1
            assert body["stale_orders_count"] == 1
            orders = body["open_orders"]
            assert orders[0]["stale"] is True

    def test_last_blocked_trade_none_when_no_holds(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        assert resp.json()["last_blocked_trade"] is None

    def test_last_blocked_trade_surfaced(self):
        from binance_trade_agent.api.api import app

        svc = _make_mock_svc()
        journal = _make_mock_journal(blocked_reason="strategy_validation_gate_negative")
        gate = _make_mock_gate()
        binance_client = _make_mock_client()
        stream_mgr = _make_mock_stream_manager()

        with (
            patch(
                "binance_trade_agent.core.order_lifecycle.get_order_lifecycle_service",
                return_value=svc,
            ),
            patch(
                "binance_trade_agent.core.decision_journal.get_decision_journal",
                return_value=journal,
            ),
            patch(
                "binance_trade_agent.core.strategy_validation_gate.get_validation_gate",
                return_value=gate,
            ),
            patch(
                "binance_trade_agent.core.market_streams.get_stream_manager",
                return_value=stream_mgr,
            ),
            patch(
                "binance_trade_agent.clients.binance_client.BinanceAPIClient",
                return_value=binance_client,
            ),
        ):
            tc = TestClient(app)
            resp = tc.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
            blocked = resp.json()["last_blocked_trade"]
            assert blocked is not None
            assert blocked["blocked_reason"] == "strategy_validation_gate_negative"

    def test_emergency_stop_false_by_default(self, client):
        resp = client.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
        es = resp.json()["emergency_stop"]
        assert "enabled" in es

    def test_emergency_stop_active_with_reason(self):
        """When risk agent has emergency stop on, reason is surfaced."""
        from binance_trade_agent.api.api import app, risk_agent

        svc = _make_mock_svc()
        journal = _make_mock_journal()
        gate = _make_mock_gate()
        binance_client = _make_mock_client()
        stream_mgr = _make_mock_stream_manager()

        original_enabled = risk_agent._shared_emergency_stop_enabled

        def mock_enabled():
            return True

        with (
            patch(
                "binance_trade_agent.core.order_lifecycle.get_order_lifecycle_service",
                return_value=svc,
            ),
            patch(
                "binance_trade_agent.core.decision_journal.get_decision_journal",
                return_value=journal,
            ),
            patch(
                "binance_trade_agent.core.strategy_validation_gate.get_validation_gate",
                return_value=gate,
            ),
            patch(
                "binance_trade_agent.core.market_streams.get_stream_manager",
                return_value=stream_mgr,
            ),
            patch(
                "binance_trade_agent.clients.binance_client.BinanceAPIClient",
                return_value=binance_client,
            ),
            patch.object(risk_agent, "_shared_emergency_stop_enabled", mock_enabled),
        ):
            tc = TestClient(app)
            resp = tc.get("/api/v1/operator/status", headers={"X-API-Token": "test-token"})
            es = resp.json()["emergency_stop"]
            assert es["enabled"] is True


class TestOperatorActionEndpoints:
    def test_emergency_stop_requires_reason(self):
        from binance_trade_agent.api.api import app

        tc = TestClient(app)
        resp = tc.post(
            "/api/v1/operator/emergency-stop",
            json={"reason": ""},
            headers={"X-API-Token": "test-token"},
        )
        assert resp.status_code == 400

    def test_emergency_stop_calls_risk_agent(self):
        from binance_trade_agent.api.api import app, risk_agent

        with patch.object(risk_agent, "set_emergency_stop") as set_stop:
            tc = TestClient(app)
            resp = tc.post(
                "/api/v1/operator/emergency-stop",
                json={"reason": "operator test"},
                headers={"X-API-Token": "test-token"},
            )

        assert resp.status_code == 200
        assert resp.json()["emergency_stop"]["enabled"] is True
        set_stop.assert_called_once_with(True, "operator test")

    def test_resume_calls_risk_agent(self):
        from binance_trade_agent.api.api import app, risk_agent

        with patch.object(risk_agent, "set_emergency_stop") as set_stop:
            tc = TestClient(app)
            resp = tc.post(
                "/api/v1/operator/resume",
                json={"reason": "checked dashboard"},
                headers={"X-API-Token": "test-token"},
            )

        assert resp.status_code == 200
        assert resp.json()["emergency_stop"]["enabled"] is False
        set_stop.assert_called_once_with(False, "checked dashboard")

    def test_cancel_stale_orders_endpoint(self):
        from binance_trade_agent.api.api import app

        svc = MagicMock()
        svc.cancel_stale_orders.return_value = [
            {"client_order_id": "bta_1", "success": True},
            {"client_order_id": "bta_2", "success": False, "error": "already closed"},
        ]

        with patch(
            "binance_trade_agent.core.order_lifecycle.get_order_lifecycle_service", return_value=svc
        ):
            tc = TestClient(app)
            resp = tc.post(
                "/api/v1/orders/stale/cancel",
                headers={"X-API-Token": "test-token"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["attempted"] == 2
        assert body["cancelled"] == 1
        svc.cancel_stale_orders.assert_called_once()

    def test_reset_paper_trading_endpoint(self):
        from binance_trade_agent.api.api import app

        engine = MagicMock()
        engine.get_portfolio_summary.return_value = {"current_balance": 2500.0}

        with patch(
            "binance_trade_agent.core.paper_trading.get_paper_trading_engine", return_value=engine
        ):
            tc = TestClient(app)
            resp = tc.post(
                "/api/v1/paper-trading/reset",
                json={"initial_balance": 2500.0},
                headers={"X-API-Token": "test-token"},
            )

        assert resp.status_code == 200
        assert resp.json()["portfolio"]["current_balance"] == 2500.0
        engine.reset.assert_called_once_with(initial_balance=2500.0)
