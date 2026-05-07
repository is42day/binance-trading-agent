"""Exchange order reconciliation.

This module keeps the local exchange-order ledger aligned with Binance after
restarts or transient API failures. It only books portfolio trades when an
exchange order is confirmed filled and a matching local trade does not exist.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List

from binance_trade_agent.clients.binance_client import BinanceAPIClient
from binance_trade_agent.core.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)


TERMINAL_ORDER_STATUSES = {"FILLED", "CANCELED", "REJECTED", "EXPIRED"}


class ExchangeReconciliationService:
    """Reconcile locally tracked exchange orders with Binance."""

    def __init__(
        self,
        client: BinanceAPIClient | None = None,
        portfolio: PortfolioManager | None = None,
    ):
        self.client = client or BinanceAPIClient()
        self.portfolio = portfolio or PortfolioManager("/app/data/web_portfolio.db")

    def reconcile_open_orders(self, symbol: str | None = None) -> Dict[str, Any]:
        """Reconcile locally tracked open orders."""
        local_orders = self.portfolio.get_open_exchange_orders(symbol=symbol)
        results = [self.reconcile_order(order) for order in local_orders]
        return {
            "checked": len(local_orders),
            "updated": sum(1 for result in results if result.get("updated")),
            "booked_trades": sum(1 for result in results if result.get("booked_trade")),
            "errors": [result for result in results if result.get("error")],
            "results": results,
        }

    def reconcile_order(self, local_order: Dict[str, Any]) -> Dict[str, Any]:
        """Reconcile one locally tracked order."""
        client_order_id = local_order["client_order_id"]
        symbol = local_order["symbol"]

        try:
            exchange_order = self.client.get_order(
                symbol=symbol,
                order_id=local_order.get("order_id") or None,
                client_order_id=client_order_id,
            )
            normalized = self._normalize_exchange_order(
                exchange_order=exchange_order,
                local_order=local_order,
            )
            normalized["last_reconciled_at"] = datetime.now()
            self.portfolio.upsert_exchange_order(normalized)

            booked_trade = False
            if normalized["status"] in {"FILLED", "PARTIALLY_FILLED"}:
                booked_trade = self._book_missing_trade(normalized)

            return {
                "client_order_id": client_order_id,
                "order_id": normalized.get("order_id"),
                "status": normalized["status"],
                "updated": True,
                "booked_trade": booked_trade,
            }
        except Exception as exc:
            logger.warning("Failed to reconcile order %s: %s", client_order_id, exc)
            return {
                "client_order_id": client_order_id,
                "updated": False,
                "booked_trade": False,
                "error": str(exc),
            }

    def _normalize_exchange_order(
        self,
        exchange_order: Dict[str, Any],
        local_order: Dict[str, Any],
    ) -> Dict[str, Any]:
        order_id = exchange_order.get("orderId") or local_order.get("order_id")
        executed_quantity = float(exchange_order.get("executedQty") or 0)
        avg_fill_price = self._extract_average_fill_price(exchange_order, local_order)
        fee = self._extract_fee(
            symbol=local_order["symbol"],
            order_id=order_id,
            raw_order=exchange_order,
        )

        return {
            "client_order_id": exchange_order.get("clientOrderId") or local_order["client_order_id"],
            "order_id": order_id,
            "symbol": exchange_order.get("symbol") or local_order["symbol"],
            "side": exchange_order.get("side") or local_order["side"],
            "order_type": exchange_order.get("type") or local_order["order_type"],
            "status": str(exchange_order.get("status") or local_order["status"]).upper(),
            "quantity": float(exchange_order.get("origQty") or local_order["quantity"] or 0),
            "executed_quantity": executed_quantity,
            "price": self._optional_float(exchange_order.get("price")) or local_order.get("price"),
            "avg_fill_price": avg_fill_price,
            "fee": fee,
            "correlation_id": local_order.get("correlation_id"),
            "raw_response": exchange_order,
        }

    def _book_missing_trade(self, order: Dict[str, Any]) -> bool:
        order_id = str(order.get("order_id") or "")
        client_order_id = order["client_order_id"]

        if self.portfolio.get_trade_by_client_order_id(client_order_id):
            return False
        if order_id and self.portfolio.get_trade_by_order_id(order_id):
            return False

        executed_quantity = float(order.get("executed_quantity") or 0)
        avg_fill_price = float(order.get("avg_fill_price") or 0)
        if executed_quantity <= 0 or avg_fill_price <= 0:
            return False

        trade_id = order_id or client_order_id
        self.portfolio.add_trade(
            trade_id=str(trade_id),
            symbol=order["symbol"],
            side=order["side"],
            quantity=executed_quantity,
            price=avg_fill_price,
            fee=float(order.get("fee") or 0),
            order_id=order_id or None,
            correlation_id=order.get("correlation_id"),
            client_order_id=client_order_id,
        )
        return True

    def _extract_average_fill_price(
        self,
        exchange_order: Dict[str, Any],
        local_order: Dict[str, Any],
    ) -> float | None:
        quote_qty = self._optional_float(exchange_order.get("cummulativeQuoteQty"))
        executed_qty = self._optional_float(exchange_order.get("executedQty"))
        if quote_qty and executed_qty:
            return quote_qty / executed_qty

        order_price = self._optional_float(exchange_order.get("price"))
        if order_price:
            return order_price

        return local_order.get("avg_fill_price")

    def _extract_fee(self, symbol: str, order_id: str | int | None, raw_order: Dict[str, Any]) -> float:
        fills = raw_order.get("fills") or []
        if fills:
            return self._sum_commissions(fills)

        if not order_id:
            return 0.0

        try:
            account_trades = self.client.get_account_trades(symbol=symbol, order_id=int(order_id))
            return self._sum_commissions(account_trades)
        except Exception as exc:
            logger.debug("Could not fetch account fills for %s/%s: %s", symbol, order_id, exc)
            return 0.0

    def _sum_commissions(self, fills: Iterable[Dict[str, Any]]) -> float:
        total_fee = 0.0
        for fill in fills:
            try:
                total_fee += float(fill.get("commission") or 0)
            except (TypeError, ValueError):
                continue
        return total_fee

    def _optional_float(self, value: Any) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None
