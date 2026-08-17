"""
Order lifecycle service.

Responsible for:
  - Polling individual orders until they reach a terminal state.
  - Booking partial-fill deltas so reconciliation runs never double-book.
  - Cancelling stale limit orders with a recorded reason.
  - Placing OCO orders as an explicit separate operation.

Normalized Binance order statuses
----------------------------------
  OPEN (non-terminal):    NEW, PARTIALLY_FILLED, PENDING_NEW
  TERMINAL:               FILLED, CANCELED, REJECTED, EXPIRED
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status sets
# ---------------------------------------------------------------------------

OPEN_STATUSES: frozenset[str] = frozenset({"NEW", "PARTIALLY_FILLED", "PENDING_NEW"})
TERMINAL_STATUSES: frozenset[str] = frozenset({"FILLED", "CANCELED", "REJECTED", "EXPIRED"})
ALL_KNOWN_STATUSES: frozenset[str] = OPEN_STATUSES | TERMINAL_STATUSES


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class OrderLifecycleService:
    """Manage the full lifecycle of Binance orders."""

    def __init__(self, client=None, portfolio=None):
        from ..clients.binance_client import BinanceAPIClient
        from ..core.portfolio_manager import PortfolioManager

        self.client = client or BinanceAPIClient()
        self.portfolio = portfolio or PortfolioManager("/app/data/web_portfolio.db")

    # ------------------------------------------------------------------
    # Poll
    # ------------------------------------------------------------------

    def poll_order(self, client_order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Fetch the latest status from Binance, book any unbooked fill delta,
        and persist the updated order record locally.

        Returns the updated local order dict.
        """
        local = self.portfolio.get_exchange_order(client_order_id)
        if not local:
            raise ValueError(f"Order not found locally: {client_order_id!r}")

        order_id = int(local["order_id"]) if local.get("order_id") else None
        exchange = self.client.get_order(
            symbol=symbol,
            order_id=order_id,
            client_order_id=client_order_id if order_id is None else None,
        )

        status = str(exchange.get("status") or "UNKNOWN").upper()
        current_exec_qty = float(exchange.get("executedQty") or 0)
        avg_price = self._extract_avg_price(exchange)
        now = datetime.now()

        # Book only the delta since the last reconciliation
        last_booked = float(local.get("last_booked_quantity") or 0)
        delta = current_exec_qty - last_booked
        if delta > 0 and avg_price and avg_price > 0:
            self._book_fill_delta(
                local_order=local,
                delta_qty=delta,
                avg_price=avg_price,
                current_exec_qty=current_exec_qty,
            )
            new_booked = current_exec_qty
        else:
            new_booked = last_booked

        updated: Dict[str, Any] = {
            **local,
            "status": status,
            "executed_quantity": current_exec_qty,
            "last_booked_quantity": new_booked,
            "avg_fill_price": avg_price or local.get("avg_fill_price"),
            "raw_response": exchange,
            "last_reconciled_at": now,
        }
        self.portfolio.upsert_exchange_order(updated)
        result = self.portfolio.get_exchange_order(client_order_id)
        return result or updated

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def cancel_order(
        self,
        client_order_id: str,
        symbol: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Cancel an open order and record the cancellation reason locally.

        Args:
            client_order_id: Local client order ID.
            symbol: Trading pair.
            reason: Human-readable reason for the cancellation.

        Returns:
            Updated local order dict.
        """
        local = self.portfolio.get_exchange_order(client_order_id)
        if not local:
            raise ValueError(f"Order not found locally: {client_order_id!r}")

        order_id = int(local["order_id"]) if local.get("order_id") else None
        if order_id is None:
            raise ValueError(
                f"Cannot cancel order without an exchange order_id: {client_order_id!r}"
            )

        self.client.cancel_order(symbol, order_id)
        logger.info("Cancelled order %s / %s: %s", client_order_id, order_id, reason)

        updated = {
            **local,
            "status": "CANCELED",
            "cancel_reason": reason,
            "updated_at": datetime.now(),
        }
        self.portfolio.upsert_exchange_order(updated)
        result = self.portfolio.get_exchange_order(client_order_id)
        return result or updated

    # ------------------------------------------------------------------
    # Stale order detection
    # ------------------------------------------------------------------

    def detect_stale_limit_orders(
        self,
        symbol: Optional[str] = None,
        price_pct_threshold: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Return open LIMIT orders whose limit price has drifted more than
        ``price_pct_threshold`` percent from the current market price.

        Args:
            symbol: If given, restrict to this symbol.
            price_pct_threshold: Percentage deviation that classifies an order as stale.

        Returns:
            List of order dicts augmented with ``current_price`` and
            ``price_deviation_pct``.
        """
        open_orders = self.portfolio.get_open_exchange_orders(symbol=symbol)
        stale: List[Dict[str, Any]] = []

        for order in open_orders:
            if order.get("order_type", "").upper() != "LIMIT":
                continue
            if order.get("status", "").upper() not in OPEN_STATUSES:
                continue
            limit_price = order.get("price")
            if not limit_price:
                continue

            try:
                current_price = self.client.get_latest_price(order["symbol"])
            except Exception as exc:
                logger.debug("Could not fetch price for %s: %s", order["symbol"], exc)
                continue

            pct_deviation = abs(current_price - float(limit_price)) / float(limit_price) * 100
            if pct_deviation > price_pct_threshold:
                stale.append(
                    {
                        **order,
                        "current_price": current_price,
                        "price_deviation_pct": round(pct_deviation, 4),
                    }
                )

        return stale

    def cancel_stale_orders(
        self,
        symbol: Optional[str] = None,
        price_pct_threshold: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Detect and cancel all stale limit orders.

        Returns the list of cancellation results (one per order).
        """
        stale = self.detect_stale_limit_orders(
            symbol=symbol, price_pct_threshold=price_pct_threshold
        )
        results: List[Dict[str, Any]] = []
        for order in stale:
            coid = order["client_order_id"]
            reason = (
                f"stale: limit_price={order['price']}, "
                f"current_price={order['current_price']}, "
                f"deviation={order['price_deviation_pct']:.2f}%"
            )
            try:
                result = self.cancel_order(coid, order["symbol"], reason)
                results.append({"client_order_id": coid, "success": True, "order": result})
            except Exception as exc:
                logger.warning("Failed to cancel stale order %s: %s", coid, exc)
                results.append({"client_order_id": coid, "success": False, "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # OCO
    # ------------------------------------------------------------------

    def place_oco(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        stop_limit_price: float,
        client_order_id: Optional[str] = None,
        stop_client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place an OCO (One-Cancels-the-Other) order.

        Both legs are recorded as separate exchange orders locally.

        Returns:
            Binance OCO response dict augmented with local
            ``limit_client_order_id`` and ``stop_client_order_id`` keys.
        """
        import hashlib
        import uuid as _uuid

        def _make_coid(tag: str) -> str:
            seed = f"{symbol}:{side}:{quantity}:{tag}:{_uuid.uuid4()}"
            return "bta_" + hashlib.sha256(seed.encode()).hexdigest()[:20]

        limit_coid = client_order_id or _make_coid("lmt")
        stop_coid = stop_client_order_id or _make_coid("stp")

        response = self.client.create_oco_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            stop_limit_price=stop_limit_price,
            client_order_id=limit_coid,
            stop_client_order_id=stop_coid,
        )

        now = datetime.now()
        # Record both legs in the local order ledger
        for report in response.get("orderReports", []):
            order_type = str(report.get("type", "LIMIT")).upper()
            coid = report.get("clientOrderId") or limit_coid
            self.portfolio.upsert_exchange_order(
                {
                    "client_order_id": coid,
                    "order_id": str(report.get("orderId") or ""),
                    "symbol": symbol,
                    "side": side,
                    "order_type": order_type,
                    "status": str(report.get("status", "NEW")).upper(),
                    "quantity": quantity,
                    "executed_quantity": float(report.get("executedQty") or 0),
                    "last_booked_quantity": 0.0,
                    "price": float(report.get("price") or 0) or None,
                    "avg_fill_price": None,
                    "fee": 0.0,
                    "correlation_id": f"oco_{response.get('orderListId', '')}",
                    "raw_response": report,
                    "created_at": now,
                }
            )

        return {
            **response,
            "limit_client_order_id": limit_coid,
            "stop_client_order_id": stop_coid,
        }

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return locally tracked orders in an open (non-terminal) state."""
        return [
            o
            for o in self.portfolio.get_open_exchange_orders(symbol=symbol)
            if o.get("status", "").upper() in OPEN_STATUSES
        ]

    def get_terminal_orders(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return locally tracked orders in a terminal state."""
        return self.portfolio.get_terminal_exchange_orders(symbol=symbol, limit=limit)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _book_fill_delta(
        self,
        local_order: Dict[str, Any],
        delta_qty: float,
        avg_price: float,
        current_exec_qty: float,
    ) -> None:
        """Book a portfolio trade for the fill delta since the last booking."""
        # trade_id encodes the fill level to prevent double-booking on retry
        trade_id = f"{local_order['client_order_id']}" f"_fill_{int(round(current_exec_qty * 1e8))}"
        try:
            self.portfolio.add_trade(
                trade_id=trade_id,
                symbol=local_order["symbol"],
                side=local_order["side"],
                quantity=delta_qty,
                price=avg_price,
                fee=0.0,
                order_id=None,  # delta fills; avoid UNIQUE constraint on order_id
                client_order_id=None,  # delta fills share parent order; avoid UNIQUE constraint
                correlation_id=local_order.get("correlation_id"),
            )
            logger.info(
                "Booked fill delta %.8f %s @ %.8f (order %s)",
                delta_qty,
                local_order["symbol"],
                avg_price,
                local_order["client_order_id"],
            )
        except Exception as exc:
            # Detect duplicate primary-key errors (idempotency guard)
            if "UNIQUE" in str(exc).upper() or "IntegrityError" in type(exc).__name__:
                logger.debug("Fill delta already booked: %s", trade_id)
            else:
                raise

    def _extract_avg_price(self, exchange_order: Dict[str, Any]) -> Optional[float]:
        """Compute average fill price from cummulativeQuoteQty / executedQty."""
        try:
            quote = float(exchange_order.get("cummulativeQuoteQty") or 0)
            qty = float(exchange_order.get("executedQty") or 0)
            if quote > 0 and qty > 0:
                return quote / qty
        except (TypeError, ValueError):
            pass

        try:
            price = float(exchange_order.get("price") or 0)
            if price > 0:
                return price
        except (TypeError, ValueError):
            pass

        return None


# ---------------------------------------------------------------------------
# Module singleton
# ---------------------------------------------------------------------------

_service: Optional[OrderLifecycleService] = None


def get_order_lifecycle_service(
    client=None,
    portfolio=None,
) -> OrderLifecycleService:
    global _service
    if _service is None:
        _service = OrderLifecycleService(client=client, portfolio=portfolio)
    return _service
