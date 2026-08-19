"""
Tests for the live-trading arming gate (Priority 0).

Verifies that:
- demo mode is returned when keys are absent or DEMO_MODE=true
- testnet mode is returned when BINANCE_TESTNET=true
- live_blocked is returned when testnet=false but arming fields are incomplete
- live_armed is returned only when all four conditions are satisfied
- BinanceAPIClient.create_order() refuses live orders unless live_armed
- Testnet and demo paths are unaffected by the arming check
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(env: dict):
    """
    Build a fresh Config instance with an isolated environment.

    Config() is a plain class — every call re-runs __init__ and re-reads
    os.environ regardless of module caching, so no sys.modules trickery is
    needed. Deleting binance_trade_agent.common.config from sys.modules
    (as this used to do) forces the module to re-execute its own
    module-level `config = Config()` singleton, replacing it with a new
    instance — but every module that already did
    `from ...config import config` (e.g. autonomous_trading_loop.py) keeps
    its own reference to the old one. That silently splits the singleton in
    two for the rest of the test session: any test that later does a fresh
    `from ...config import config` gets the new object, while
    already-imported application code keeps reading the old one — so a
    monkeypatch on one is invisible to the other.
    """
    with patch.dict("os.environ", env, clear=True):
        from binance_trade_agent.common.config import Config

        return Config()


# ---------------------------------------------------------------------------
# Config.runtime_mode derivation tests
# ---------------------------------------------------------------------------


class TestRuntimeMode:
    def test_demo_mode_no_keys(self):
        """No API keys → demo mode forced."""
        cfg = _make_config({})
        assert cfg.runtime_mode == "demo"

    def test_demo_mode_explicit_flag(self):
        """DEMO_MODE=true → demo even with keys present."""
        cfg = _make_config(
            {
                "DEMO_MODE": "true",
                "BINANCE_API_KEY": "key",
                "BINANCE_API_SECRET": "secret",
            }
        )
        assert cfg.runtime_mode == "demo"

    def test_testnet_mode(self):
        """Real keys + testnet=true → testnet."""
        cfg = _make_config(
            {
                "BINANCE_API_KEY": "key",
                "BINANCE_API_SECRET": "secret",
                "BINANCE_TESTNET": "true",
                "DEMO_MODE": "false",
            }
        )
        assert cfg.runtime_mode == "testnet"

    def test_live_blocked_missing_enabled(self):
        """testnet=false + no LIVE_TRADING_ENABLED → live_blocked."""
        cfg = _make_config(
            {
                "BINANCE_API_KEY": "key",
                "BINANCE_API_SECRET": "secret",
                "BINANCE_TESTNET": "false",
                "DEMO_MODE": "false",
                "LIVE_TRADING_ACK": "I_ACCEPT_LIVE_BINANCE_SPOT_RISK",
            }
        )
        assert cfg.runtime_mode == "live_blocked"

    def test_live_blocked_missing_ack(self):
        """testnet=false + LIVE_TRADING_ENABLED=true but no ACK → live_blocked."""
        cfg = _make_config(
            {
                "BINANCE_API_KEY": "key",
                "BINANCE_API_SECRET": "secret",
                "BINANCE_TESTNET": "false",
                "DEMO_MODE": "false",
                "LIVE_TRADING_ENABLED": "true",
            }
        )
        assert cfg.runtime_mode == "live_blocked"

    def test_live_blocked_wrong_ack(self):
        """testnet=false + LIVE_TRADING_ENABLED=true + wrong ACK phrase → live_blocked."""
        cfg = _make_config(
            {
                "BINANCE_API_KEY": "key",
                "BINANCE_API_SECRET": "secret",
                "BINANCE_TESTNET": "false",
                "DEMO_MODE": "false",
                "LIVE_TRADING_ENABLED": "true",
                "LIVE_TRADING_ACK": "yes_i_agree",
            }
        )
        assert cfg.runtime_mode == "live_blocked"

    def test_live_blocked_enabled_false(self):
        """LIVE_TRADING_ENABLED=false with correct ACK → still live_blocked."""
        cfg = _make_config(
            {
                "BINANCE_API_KEY": "key",
                "BINANCE_API_SECRET": "secret",
                "BINANCE_TESTNET": "false",
                "DEMO_MODE": "false",
                "LIVE_TRADING_ENABLED": "false",
                "LIVE_TRADING_ACK": "I_ACCEPT_LIVE_BINANCE_SPOT_RISK",
            }
        )
        assert cfg.runtime_mode == "live_blocked"

    def test_live_armed_all_conditions_met(self):
        """All four arming conditions satisfied → live_armed."""
        cfg = _make_config(
            {
                "BINANCE_API_KEY": "key",
                "BINANCE_API_SECRET": "secret",
                "BINANCE_TESTNET": "false",
                "DEMO_MODE": "false",
                "LIVE_TRADING_ENABLED": "true",
                "LIVE_TRADING_ACK": "I_ACCEPT_LIVE_BINANCE_SPOT_RISK",
            }
        )
        assert cfg.runtime_mode == "live_armed"


# ---------------------------------------------------------------------------
# BinanceAPIClient.create_order() live-arming guard tests
# ---------------------------------------------------------------------------


def _make_armed_client(runtime_mode: str):
    """
    Create a BinanceAPIClient whose config.runtime_mode is mocked to
    the given value, and whose validate_order_params always returns valid.
    The underlying Binance client.create_order is mocked too.
    """
    # NOTE: We use BinanceAPIClient.__new__ (no __init__), so we do NOT need to
    # purge sys.modules. A full purge would break other tests by causing module
    # identity splits (two different db module objects for the same logical module).

    dummy_env = {
        "BINANCE_API_KEY": "k",
        "BINANCE_API_SECRET": "s",
        "BINANCE_TESTNET": "false",
        "DEMO_MODE": "false",
    }
    with patch.dict("os.environ", dummy_env, clear=True):
        # Prevent actual Binance SDK connection
        with patch("binance.client.Client.__init__", return_value=None):
            from binance_trade_agent.clients.binance_client import BinanceAPIClient

            client = BinanceAPIClient.__new__(BinanceAPIClient)
            # Minimal attribute setup
            mock_cfg = MagicMock()
            mock_cfg.demo_mode = False
            mock_cfg.runtime_mode = runtime_mode
            client.config = mock_cfg
            client.client = MagicMock()
            client.client.create_order = MagicMock(return_value={"status": "FILLED", "orderId": 1})
            client._circuit_breaker = MagicMock()
            client._circuit_breaker.can_execute.return_value = True

            # Patch validate_order_params to always pass
            client.validate_order_params = MagicMock(
                return_value={
                    "valid": True,
                    "normalized_quantity": 0.001,
                    "normalized_price": 50000.0,
                }
            )
            return client


class TestCreateOrderArmingGate:
    def test_live_armed_allows_market_order(self):
        """live_armed → order call reaches Binance SDK."""
        client = _make_armed_client("live_armed")
        with patch.object(
            client, "_api_call_with_retry", return_value={"status": "FILLED", "orderId": 1}
        ):
            result = client.create_order("BTCUSDT", "BUY", "MARKET", 0.001)
        assert result["status"] == "FILLED"

    def test_live_blocked_raises_error(self):
        """live_blocked → ValueError raised before any API call."""
        client = _make_armed_client("live_blocked")
        with pytest.raises(ValueError, match="runtime_mode is 'live_blocked'"):
            client.create_order("BTCUSDT", "BUY", "MARKET", 0.001)

    def test_testnet_mode_raises_error(self):
        """testnet mode is not live_armed → ValueError raised."""
        client = _make_armed_client("testnet")
        with pytest.raises(ValueError, match="runtime_mode is 'testnet'"):
            client.create_order("BTCUSDT", "BUY", "MARKET", 0.001)

    def test_demo_mode_bypasses_gate(self):
        """demo_mode path short-circuits before the arming check → returns mock fill."""
        # NOTE: We use BinanceAPIClient.__new__ (no __init__), so no sys.modules purge needed.
        with patch.dict("os.environ", {}, clear=True):
            with patch("binance.client.Client.__init__", return_value=None):
                from binance_trade_agent.clients.binance_client import BinanceAPIClient

                client = BinanceAPIClient.__new__(BinanceAPIClient)
                mock_cfg = MagicMock()
                mock_cfg.demo_mode = True
                mock_cfg.runtime_mode = "demo"
                client.config = mock_cfg
                client._circuit_breaker = MagicMock()

                # validate_order_params and get_latest_price needed by demo path
                client.validate_order_params = MagicMock(
                    return_value={
                        "valid": True,
                        "normalized_quantity": 0.001,
                        "normalized_price": None,
                    }
                )
                result = client.create_order("BTCUSDT", "BUY", "MARKET", 0.001)
        assert result["status"] == "FILLED"
