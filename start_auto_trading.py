#!/usr/bin/env python3
"""
Automated Trading Loop - CLI wrapper around binance_trade_agent.main

Thin argument-parsing wrapper: translates the --strategy/--symbols/--interval
CLI flags into the STRATEGY_NAME/TRADING_SYMBOLS/TRADING_INTERVAL_SECONDS env
vars that binance_trade_agent.main.main() already reads, then delegates to
it. Flags left unset fall through to main()'s own env-var defaults, which
match this script's historical defaults exactly (combined / BTCUSDT / 60s).

This used to be a second, independent trading-loop implementation
(AutomatedTradingAgent) that duplicated core/autonomous_trading_loop.py's
AutonomousTradingLoop without any of its safety mechanisms — no
concurrent-instance heartbeat guard, no emergency-stop handling, no
shared-risk-state startup guard, no config.validate(). Both `make start`
and the README's documented quick-start `docker run` command invoke this
script directly, so that gap wasn't theoretical: it was the actual,
documented, commonly-used entrypoint. Delegating to the same code
binance_trade_agent.main.py / docker-compose's trading-agent service use
closes it by construction — there is now exactly one trading-loop
implementation, and this script can't drift out of sync with its safety
fixes again.

Usage:
    python start_auto_trading.py [--strategy STRATEGY] [--symbols SYMBOL1,SYMBOL2] [--interval SECONDS]

Examples:
    python start_auto_trading.py                          # Default: combined strategy, BTCUSDT, 60s
    python start_auto_trading.py --strategy rsi           # RSI strategy
    python start_auto_trading.py --strategy macd          # MACD strategy
    python start_auto_trading.py --symbols BTCUSDT,ETHUSDT --interval 30
"""

import argparse
import os


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated Trading Agent",
        epilog="Examples:\n"
        "  python start_auto_trading.py\n"
        "  python start_auto_trading.py --strategy rsi --interval 30\n"
        "  python start_auto_trading.py --symbols BTCUSDT,ETHUSDT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--strategy",
        default=None,
        help="Strategy name (default: $STRATEGY_NAME, or 'combined')",
    )
    parser.add_argument(
        "--symbols",
        default=None,
        help="Comma-separated symbols (default: $TRADING_SYMBOLS, or 'BTCUSDT')",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Seconds between trading cycles (default: $TRADING_INTERVAL_SECONDS, or 60)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.strategy is not None:
        os.environ["STRATEGY_NAME"] = args.strategy
    if args.symbols is not None:
        os.environ["TRADING_SYMBOLS"] = args.symbols
    if args.interval is not None:
        os.environ["TRADING_INTERVAL_SECONDS"] = str(args.interval)

    from binance_trade_agent.main import main as run_trading_agent

    run_trading_agent()


if __name__ == "__main__":
    main()
