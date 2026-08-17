"""
Regression coverage: dashboard auth must hard-fail on default credentials.

require_auth() previously only printed a warning when DASHBOARD_PASSWORD was
still the default "changeme" and otherwise proceeded to serve the dashboard
with those well-known credentials. It must now refuse to start instead,
unless the operator explicitly opts out via DASHBOARD_AUTH_ENABLED=false.
"""

from types import SimpleNamespace

import pytest
from flask import Flask


def _fake_app():
    return SimpleNamespace(server=Flask(__name__))


def test_refuses_to_start_with_default_password_when_auth_enabled(monkeypatch):
    from binance_trade_agent.dashboard.auth import require_auth

    monkeypatch.delenv("DASHBOARD_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="DASHBOARD_PASSWORD is still the default"):
        require_auth(_fake_app())


def test_starts_with_a_real_password_configured(monkeypatch):
    from binance_trade_agent.dashboard.auth import require_auth

    monkeypatch.delenv("DASHBOARD_AUTH_ENABLED", raising=False)
    monkeypatch.setenv("DASHBOARD_PASSWORD", "a-real-secret-value")

    require_auth(_fake_app())  # must not raise


def test_explicit_opt_out_allows_default_password(monkeypatch):
    from binance_trade_agent.dashboard.auth import require_auth

    monkeypatch.setenv("DASHBOARD_AUTH_ENABLED", "false")
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)

    require_auth(_fake_app())  # must not raise — auth is off entirely
