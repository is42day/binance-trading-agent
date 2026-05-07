"""Testnet smoke checks for VPS deployment.

By default this checks connectivity and local reconciliation without placing an
order. Passing --place-order will submit a tiny Binance testnet market order,
but only when BINANCE_TESTNET=true and CONFIRM_TESTNET_ORDER=true.
"""

from __future__ import annotations

import argparse
import os
import sys

from binance_trade_agent.agents.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.clients.binance_client import BinanceAPIClient
from binance_trade_agent.common.config import config
from binance_trade_agent.core.exchange_reconciliation import ExchangeReconciliationService


def _fail(message: str) -> int:
    print(f"[TESTNET] ERROR: {message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Binance testnet smoke checks")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--quantity", type=float, default=None)
    parser.add_argument("--place-order", action="store_true")
    args = parser.parse_args(argv)

    if not config.binance_testnet:
        return _fail("BINANCE_TESTNET must be true for this smoke test")
    if not config.binance_api_key or not config.binance_api_secret:
        return _fail("BINANCE_API_KEY and BINANCE_API_SECRET are required")
    if os.getenv("TESTNET_AGGRESSIVE_MODE", "false").lower() == "true":
        return _fail("TESTNET_AGGRESSIVE_MODE must be false for this smoke test")

    client = BinanceAPIClient()
    price = client.get_latest_price(args.symbol)
    print(f"[TESTNET] Connectivity OK: {args.symbol} price={price}")

    reconciliation = ExchangeReconciliationService(client=client)
    reconcile_result = reconciliation.reconcile_open_orders(symbol=args.symbol)
    print(
        "[TESTNET] Reconciliation OK: "
        f"checked={reconcile_result['checked']} "
        f"updated={reconcile_result['updated']} "
        f"booked_trades={reconcile_result['booked_trades']} "
        f"errors={len(reconcile_result['errors'])}"
    )

    if not args.place_order:
        print("[TESTNET] Order placement skipped. Add --place-order for a tiny testnet order.")
        return 0

    if os.getenv("CONFIRM_TESTNET_ORDER", "false").lower() != "true":
        return _fail("Set CONFIRM_TESTNET_ORDER=true before using --place-order")

    quantity = args.quantity or config.get_default_quantity(args.symbol)
    execution_agent = TradeExecutionAgent()
    result = execution_agent.place_buy_order(
        symbol=args.symbol,
        quantity=quantity,
        correlation_id=f"testnet_smoke_{args.symbol}",
    )

    if not result.get("success"):
        return _fail(f"Testnet order failed: {result}")

    print(
        "[TESTNET] Testnet BUY submitted: "
        f"order_id={result.get('order_id')} "
        f"client_order_id={result.get('client_order_id')} "
        f"status={result.get('status')} "
        f"quantity={result.get('quantity')} "
        f"price={result.get('price')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
