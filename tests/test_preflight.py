from binance_trade_agent.scripts.preflight import run_preflight


def _set_valid_common(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@postgres:5432/db")
    monkeypatch.setenv("POSTGRES_PASSWORD", "db-secret-value-12345")
    monkeypatch.setenv("API_AUTH_REQUIRED", "true")
    monkeypatch.setenv("API_AUTH_TOKEN", "api-token-value-that-is-long-enough")
    monkeypatch.setenv("DASHBOARD_AUTH_ENABLED", "true")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "dashboard-secret-value")


def test_api_preflight_rejects_placeholder_secrets(monkeypatch):
    _set_valid_common(monkeypatch)
    monkeypatch.setenv("API_AUTH_TOKEN", "replace_with_a_long_random_api_token")

    errors = run_preflight("api")

    assert any("API_AUTH_TOKEN" in error for error in errors)


def test_dashboard_preflight_accepts_valid_vps_env(monkeypatch):
    _set_valid_common(monkeypatch)

    assert run_preflight("dashboard") == []


def test_trading_preflight_requires_explicit_live_opt_in(monkeypatch):
    _set_valid_common(monkeypatch)
    monkeypatch.setenv("BINANCE_API_KEY", "binance-key-value")
    monkeypatch.setenv("BINANCE_API_SECRET", "binance-secret-value")
    monkeypatch.setenv("BINANCE_TESTNET", "false")
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "false")
    monkeypatch.setenv("BINANCE_API_URL", "https://api.binance.com")
    monkeypatch.setenv("TRADING_SYMBOLS", "BTCUSDT")
    monkeypatch.setenv("TRADING_INTERVAL_SECONDS", "120")

    errors = run_preflight("trading-agent")

    assert any("ALLOW_LIVE_TRADING" in error for error in errors)


def test_trading_preflight_accepts_testnet_env(monkeypatch):
    _set_valid_common(monkeypatch)
    monkeypatch.setenv("BINANCE_API_KEY", "binance-key-value")
    monkeypatch.setenv("BINANCE_API_SECRET", "binance-secret-value")
    monkeypatch.setenv("BINANCE_TESTNET", "true")
    monkeypatch.setenv("ALLOW_LIVE_TRADING", "false")
    monkeypatch.setenv("BINANCE_API_URL", "https://testnet.binance.vision")
    monkeypatch.setenv("TRADING_SYMBOLS", "BTCUSDT")
    monkeypatch.setenv("TRADING_INTERVAL_SECONDS", "120")

    assert run_preflight("trading-agent") == []
