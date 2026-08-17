"""
Tests for the Decision Journal (Priority 7 — Tasks 7.1 and 7.2).

Verifies:
- record() persists a decision and returns a UUID
- get_latest() without a symbol filter returns the newest decision overall
- get_latest(symbol=...) filters correctly
- get_history() returns records newest-first up to limit
- Missing/stale/blocked scenarios are stored with correct blocked_reason
- API endpoints /decisions/latest and /decisions/history respond correctly
"""

from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from binance_trade_agent.core.decision_journal import DecisionJournal
from binance_trade_agent.core.portfolio_manager import Base

# ---------------------------------------------------------------------------
# In-memory SQLite session factory for tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_session_factory():
    # StaticPool: all sessions share the same connection → same in-memory DB
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    @contextmanager
    def _session():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    return _session


@pytest.fixture()
def journal(in_memory_session_factory):
    return DecisionJournal(session_factory=in_memory_session_factory)


# ---------------------------------------------------------------------------
# DecisionJournal.record() tests
# ---------------------------------------------------------------------------


class TestDecisionJournalRecord:
    def test_record_returns_uuid(self, journal):
        decision_id = journal.record("BTCUSDT", "HOLD")
        assert isinstance(decision_id, str)
        assert len(decision_id) == 36  # UUID4 string

    def test_record_stores_all_fields(self, journal):
        policy = {"mode": "maker_first", "max_spread_pct": 0.05}
        meta = {"component": "micro"}
        journal.record(
            "BTCUSDT",
            "BUY",
            strategy="adaptive_core_micro",
            confidence=0.8,
            blocked_reason=None,
            risk_approved=True,
            execution_policy=policy,
            metadata=meta,
        )
        decision = journal.get_latest("BTCUSDT")
        assert decision["signal"] == "BUY"
        assert decision["strategy"] == "adaptive_core_micro"
        assert decision["confidence"] == pytest.approx(0.8)
        assert decision["blocked_reason"] is None
        assert decision["risk_approved"] is True
        assert decision["execution_policy"] == policy
        assert decision["metadata"] == meta

    def test_record_hold_with_blocked_reason(self, journal):
        journal.record(
            "ETHUSDT",
            "HOLD",
            blocked_reason="strategy_validation_gate_negative",
            risk_approved=False,
        )
        decision = journal.get_latest("ETHUSDT")
        assert decision["signal"] == "HOLD"
        assert decision["blocked_reason"] == "strategy_validation_gate_negative"
        assert decision["risk_approved"] is False

    def test_record_normalises_symbol_to_upper(self, journal):
        journal.record("btcusdt", "SELL")
        decision = journal.get_latest("btcusdt")
        assert decision["symbol"] == "BTCUSDT"


# ---------------------------------------------------------------------------
# DecisionJournal.get_latest() tests
# ---------------------------------------------------------------------------


class TestDecisionJournalGetLatest:
    def test_returns_none_when_empty(self, journal):
        assert journal.get_latest("BTCUSDT") is None

    def test_returns_most_recent(self, journal):
        t0 = datetime(2026, 5, 10, 12, 0, 0)
        t1 = datetime(2026, 5, 10, 12, 1, 0)
        journal.record("BTCUSDT", "HOLD", timestamp=t0)
        journal.record("BTCUSDT", "BUY", timestamp=t1)
        decision = journal.get_latest("BTCUSDT")
        assert decision["signal"] == "BUY"

    def test_filters_by_symbol(self, journal):
        journal.record("BTCUSDT", "BUY")
        journal.record("ETHUSDT", "SELL")
        assert journal.get_latest("BTCUSDT")["symbol"] == "BTCUSDT"
        assert journal.get_latest("ETHUSDT")["symbol"] == "ETHUSDT"

    def test_no_symbol_returns_global_latest(self, journal):
        t0 = datetime(2026, 5, 10, 12, 0, 0)
        t1 = datetime(2026, 5, 10, 12, 5, 0)
        journal.record("BTCUSDT", "HOLD", timestamp=t0)
        journal.record("ETHUSDT", "BUY", timestamp=t1)
        decision = journal.get_latest()
        assert decision["symbol"] == "ETHUSDT"


# ---------------------------------------------------------------------------
# DecisionJournal.get_history() tests
# ---------------------------------------------------------------------------


class TestDecisionJournalGetHistory:
    def test_returns_empty_list_when_no_records(self, journal):
        assert journal.get_history("BTCUSDT") == []

    def test_returns_newest_first(self, journal):
        base_time = datetime(2026, 5, 10, 12, 0, 0)
        for i in range(3):
            journal.record("BTCUSDT", "HOLD", timestamp=base_time + timedelta(minutes=i))
        history = journal.get_history("BTCUSDT")
        timestamps = [h["timestamp"] for h in history]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_respects_limit(self, journal):
        base_time = datetime(2026, 5, 10, 12, 0, 0)
        for i in range(10):
            journal.record("BTCUSDT", "HOLD", timestamp=base_time + timedelta(minutes=i))
        history = journal.get_history("BTCUSDT", limit=3)
        assert len(history) == 3

    def test_filters_by_symbol(self, journal):
        journal.record("BTCUSDT", "BUY")
        journal.record("ETHUSDT", "SELL")
        btc_history = journal.get_history("BTCUSDT")
        assert all(d["symbol"] == "BTCUSDT" for d in btc_history)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def api_journal(in_memory_session_factory, monkeypatch):
    """
    DecisionJournal backed by in-memory SQLite, monkeypatched into the API module.
    Tests that need to pre-populate decisions should use THIS fixture so they
    share the same database that the endpoint will query.
    """
    from binance_trade_agent.core import decision_journal as dj_module

    monkeypatch.setenv("API_AUTH_REQUIRED", "false")

    test_journal = DecisionJournal(session_factory=in_memory_session_factory)
    monkeypatch.setattr(dj_module, "_journal", test_journal)
    return test_journal


@pytest.fixture()
def api_client(api_journal):
    """TestClient with decision journal patched to use in-memory DB."""
    from binance_trade_agent.api import api as api_module

    return TestClient(api_module.app)


class TestDecisionJournalAPI:
    def test_latest_endpoint_empty(self, api_client):
        resp = api_client.get("/api/v1/trading/decisions/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] is None

    def test_latest_endpoint_returns_decision(self, api_client, api_journal):
        api_journal.record("BTCUSDT", "HOLD", blocked_reason="rate_limit_budget_exceeded")
        resp = api_client.get("/api/v1/trading/decisions/latest?symbol=BTCUSDT")
        assert resp.status_code == 200
        decision = resp.json()["decision"]
        assert decision["signal"] == "HOLD"
        assert decision["blocked_reason"] == "rate_limit_budget_exceeded"

    def test_history_endpoint_empty(self, api_client):
        resp = api_client.get("/api/v1/trading/decisions/history")
        assert resp.status_code == 200
        assert resp.json()["decisions"] == []

    def test_history_endpoint_returns_records(self, api_client, api_journal):
        base_time = datetime(2026, 5, 10, 12, 0, 0)
        for i in range(5):
            api_journal.record("BTCUSDT", "HOLD", timestamp=base_time + timedelta(minutes=i))
        resp = api_client.get("/api/v1/trading/decisions/history?symbol=BTCUSDT&limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["decisions"]) == 3

    def test_history_endpoint_rejects_bad_limit(self, api_client):
        resp = api_client.get("/api/v1/trading/decisions/history?limit=0")
        assert resp.status_code == 400
