"""
Regression coverage for blocking sync calls inside async route handlers.

All api.py route handlers are `async def`, but the underlying
PortfolioManager/BinanceAPIClient/etc. calls they made were synchronous
(SQLAlchemy ORM, python-binance REST) and were called directly with no
dispatch to a thread pool. A sync call blocking inside an `async def`
handler blocks uvicorn's single event-loop thread — so under concurrent
load, requests serialize behind whatever blocking call happens to be in
flight, regardless of how many workers/clients are hitting the API.

This test proves the fix empirically: two concurrent requests to an
endpoint whose underlying call is patched to sleep synchronously must
complete in roughly one sleep duration (running in parallel via
run_in_threadpool), not two (serialized behind the event loop).
"""

from __future__ import annotations

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_concurrent_requests_to_a_slow_sync_call_run_in_parallel(monkeypatch):
    from binance_trade_agent.api import api as api_module

    SLEEP_SECONDS = 0.3

    def _slow_blocking_stats():
        time.sleep(SLEEP_SECONDS)  # simulates a slow synchronous DB call
        return {"total_value": 100000.0, "total_pnl": 0.0}

    monkeypatch.setattr(api_module.portfolio_manager, "get_portfolio_stats", _slow_blocking_stats)

    # Bypass the cache so both requests actually hit the (patched) blocking call.
    async def _cache_miss(key):
        return None

    async def _cache_noop_set(key, value):
        return None

    monkeypatch.setattr(api_module.cache, "get", _cache_miss)
    monkeypatch.setattr(api_module.cache, "set", _cache_noop_set)

    transport = ASGITransport(app=api_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = time.perf_counter()
        responses = await asyncio.gather(
            client.get("/api/v1/portfolio/summary"),
            client.get("/api/v1/portfolio/summary"),
        )
        elapsed = time.perf_counter() - start

    for response in responses:
        assert response.status_code == 200

    # If the two blocking calls ran sequentially on the event loop thread,
    # elapsed would be close to 2 * SLEEP_SECONDS. Running in parallel via
    # run_in_threadpool, it should be close to 1 * SLEEP_SECONDS. Assert
    # comfortably below the serialized threshold to avoid flakiness while
    # still catching a regression back to inline blocking calls.
    assert elapsed < SLEEP_SECONDS * 1.5, (
        f"Requests took {elapsed:.2f}s — expected ~{SLEEP_SECONDS:.2f}s if run in "
        f"parallel via run_in_threadpool, not ~{SLEEP_SECONDS * 2:.2f}s serialized"
    )
