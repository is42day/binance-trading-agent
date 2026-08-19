"""
Regression coverage for start_auto_trading.py delegating to
binance_trade_agent.main instead of maintaining a second, independent
trading-loop implementation.

start_auto_trading.py used to run its own AutomatedTradingAgent class that
never touched core/autonomous_trading_loop.py's AutonomousTradingLoop — no
concurrent-instance heartbeat guard, no emergency-stop handling, no
shared-risk-state startup guard, no config.validate(). Both `make start`
and the README's documented quick-start `docker run` command invoke this
script directly, so it was the actual, commonly-used entrypoint bypassing
all of that safety work, not just dead code.
"""

from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import patch


def _reload_script():
    """
    start_auto_trading.py isn't a package module (no binance_trade_agent.
    prefix) and importing it executes the module — import fresh each time
    so tests don't share state via sys.modules caching.
    """
    sys.modules.pop("start_auto_trading", None)
    return importlib.import_module("start_auto_trading")


class TestParseArgs:
    def test_defaults_are_none_so_main_py_env_defaults_apply(self):
        script = _reload_script()
        args = script.parse_args([])
        assert args.strategy is None
        assert args.symbols is None
        assert args.interval is None

    def test_parses_all_three_flags(self):
        script = _reload_script()
        args = script.parse_args(
            ["--strategy", "rsi", "--symbols", "BTCUSDT,ETHUSDT", "--interval", "30"]
        )
        assert args.strategy == "rsi"
        assert args.symbols == "BTCUSDT,ETHUSDT"
        assert args.interval == 30


class TestMainDelegatesToBinanceTradeAgentMain:
    def test_explicit_flags_set_the_matching_env_vars(self, monkeypatch):
        monkeypatch.delenv("STRATEGY_NAME", raising=False)
        monkeypatch.delenv("TRADING_SYMBOLS", raising=False)
        monkeypatch.delenv("TRADING_INTERVAL_SECONDS", raising=False)

        script = _reload_script()
        with patch("binance_trade_agent.main.main") as mock_main:
            script.main(["--strategy", "rsi", "--symbols", "BTCUSDT,ETHUSDT", "--interval", "30"])

        assert os.environ["STRATEGY_NAME"] == "rsi"
        assert os.environ["TRADING_SYMBOLS"] == "BTCUSDT,ETHUSDT"
        assert os.environ["TRADING_INTERVAL_SECONDS"] == "30"
        mock_main.assert_called_once_with()

    def test_omitted_flags_do_not_touch_env_vars(self, monkeypatch):
        monkeypatch.setenv("STRATEGY_NAME", "already-set-by-docker-compose")

        script = _reload_script()
        with patch("binance_trade_agent.main.main") as mock_main:
            script.main([])

        # Untouched — main()'s own os.getenv(..., "combined") default applies.
        assert os.environ["STRATEGY_NAME"] == "already-set-by-docker-compose"
        mock_main.assert_called_once_with()

    def test_delegates_to_the_real_safety_checked_entrypoint(self):
        """
        The whole point of this rewrite: there is exactly one trading-loop
        implementation now. Confirm main() actually imports and calls
        binance_trade_agent.main.main — the same function
        `python -m binance_trade_agent.main` and docker-compose's
        trading-agent service both use, with AutonomousTradingLoop's
        concurrent-instance guard, emergency-stop handling, and
        shared-risk-state startup check all in the call path.
        """
        script = _reload_script()
        with patch("binance_trade_agent.main.main") as mock_main:
            script.main([])

        mock_main.assert_called_once_with()

    def test_no_second_trading_loop_implementation_remains(self):
        script = _reload_script()
        assert not hasattr(script, "AutomatedTradingAgent")
