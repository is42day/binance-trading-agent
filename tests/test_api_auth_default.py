"""
Regression coverage for require_api_token's fail-closed default.

API_AUTH_REQUIRED used to default to "false" in code — safe only because
docker-compose.yml overrides it to "true". A bare `uvicorn` run outside
compose (or any other invocation that doesn't source that env override)
would silently serve every request unauthenticated. The default now assumes
production intent (auth required) unless explicitly opted out.
"""

import pytest
from fastapi import HTTPException


def test_defaults_to_auth_required_and_rejects_missing_token(monkeypatch):
    from binance_trade_agent.api.api import require_api_token

    monkeypatch.delenv("API_AUTH_REQUIRED", raising=False)
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        require_api_token(authorization=None)

    assert exc_info.value.status_code == 503


def test_explicit_opt_out_restores_unauthenticated_access(monkeypatch):
    from binance_trade_agent.api.api import require_api_token

    monkeypatch.setenv("API_AUTH_REQUIRED", "false")
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)

    require_api_token(authorization=None)  # must not raise


def test_configured_token_is_still_enforced_by_default(monkeypatch):
    from binance_trade_agent.api.api import require_api_token

    monkeypatch.delenv("API_AUTH_REQUIRED", raising=False)
    monkeypatch.setenv("API_AUTH_TOKEN", "a-real-token")

    with pytest.raises(HTTPException) as exc_info:
        require_api_token(authorization="Bearer wrong-token")
    assert exc_info.value.status_code == 401

    require_api_token(authorization="Bearer a-real-token")  # must not raise
