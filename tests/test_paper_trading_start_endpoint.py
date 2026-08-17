"""
Regression coverage for POST /api/v1/paper-trading/start staying body-less
compatible. Refactoring individual Body() parameters into a single
StartPaperTradingRequest Pydantic model risked making the whole request body
required — a body-less POST previously started the loop with the documented
defaults (every Body() parameter had one of its own).
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


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


@pytest.mark.asyncio
async def test_concurrent_start_requests_do_not_both_start_a_loop():
    """
    Regression: PaperTradingLoop construction is awaited via
    run_in_threadpool, which yields the event loop. Without serializing the
    check-then-start sequence, two /start requests arriving close together
    could both pass the "already running" check before either one finishes
    constructing, each spin up its own loop/thread, and silently overwrite
    the module-level globals — orphaning the first loop (still placing
    duplicate paper trades) while /stop can only ever signal the second.
    """
    import binance_trade_agent.api.api as api_module

    api_module._paper_loop_instance = None
    api_module._paper_loop_thread = None

    construct_calls = []

    class _SlowFakeLoop:
        def __init__(self, **kwargs):
            construct_calls.append(kwargs)
            time.sleep(0.2)  # widen the race window across the threadpool await

        async def run(self):
            # A real PaperTradingLoop.run() loops continuously until
            # stopped, keeping _paper_loop_thread.is_alive() True for the
            # loop's whole lifetime. If this returned immediately instead,
            # the background thread could finish before a second (correctly
            # serialized, but later) /start request even checks is_alive(),
            # making the "already running" guard spuriously pass through —
            # a test-only artifact, not something a real loop would do.
            await asyncio.sleep(3600)

    with patch(
        "binance_trade_agent.core.paper_trading_loop.PaperTradingLoop",
        side_effect=_SlowFakeLoop,
    ):
        transport = ASGITransport(app=api_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await asyncio.gather(
                client.post(
                    "/api/v1/paper-trading/start",
                    headers={"X-API-Token": "test-token"},
                ),
                client.post(
                    "/api/v1/paper-trading/start",
                    headers={"X-API-Token": "test-token"},
                ),
            )

    api_module._paper_loop_instance = None
    api_module._paper_loop_thread = None

    bodies = [r.json() for r in responses]
    successes = [b for b in bodies if b.get("success") is True]
    already_running = [b for b in bodies if b.get("success") is False]

    assert len(construct_calls) == 1
    assert len(successes) == 1
    assert len(already_running) == 1
    assert "already running" in already_running[0]["message"]
