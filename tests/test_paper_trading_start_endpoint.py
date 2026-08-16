"""
Regression coverage for POST /api/v1/paper-trading/start staying body-less
compatible. Refactoring individual Body() parameters into a single
StartPaperTradingRequest Pydantic model risked making the whole request body
required — a body-less POST previously started the loop with the documented
defaults (every Body() parameter had one of its own).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_start_with_no_body_uses_documented_defaults():
    from binance_trade_agent.api.api import app

    client = TestClient(app)

    with patch("binance_trade_agent.core.paper_trading_loop.PaperTradingLoop") as mock_loop_cls:
        mock_loop_cls.return_value.run = AsyncMock(return_value=None)
        response = client.post("/api/v1/paper-trading/start")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["symbols"] == ["BTCUSDT"]
    assert body["strategy"] == "combined_edge"
    mock_loop_cls.assert_called_once_with(
        symbols=["BTCUSDT"],
        strategy_name="combined_edge",
        initial_balance=10000.0,
        trade_interval_seconds=60,
    )


def test_start_with_partial_body_overrides_only_given_fields():
    from binance_trade_agent.api.api import app

    client = TestClient(app)

    with patch("binance_trade_agent.core.paper_trading_loop.PaperTradingLoop") as mock_loop_cls:
        mock_loop_cls.return_value.run = AsyncMock(return_value=None)
        response = client.post(
            "/api/v1/paper-trading/start",
            json={"symbols": ["ETHUSDT"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["symbols"] == ["ETHUSDT"]
    assert body["strategy"] == "combined_edge"
    mock_loop_cls.assert_called_once_with(
        symbols=["ETHUSDT"],
        strategy_name="combined_edge",
        initial_balance=10000.0,
        trade_interval_seconds=60,
    )
