"""
TradeExecutionAgent: Handles order placement, status, and cancellation via BinanceAPIClient.
"""

import hashlib
import uuid

from binance.exceptions import BinanceAPIException

from ..clients.binance_client import BinanceAPIClient
from ..core.portfolio_manager import PortfolioManager


class TradeExecutionAgent:
    def __init__(self):
        self.client = BinanceAPIClient()
        self.portfolio = PortfolioManager("/app/data/web_portfolio.db")

    def _build_client_order_id(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        correlation_id: str | None = None,
    ) -> str:
        """Build a Binance-compatible idempotency key for an order intent."""
        seed = correlation_id or f"{symbol}:{side}:{order_type}:{quantity}:{uuid.uuid4()}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
        return f"bta_{digest}"

    def place_order(
        self,
        symbol,
        side,
        order_type,
        quantity,
        price=None,
        correlation_id=None,
        client_order_id=None,
    ):
        """
        Place an order on Binance and persist it to the portfolio DB if successful.
        Args:
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
            side (str): 'BUY' or 'SELL'.
            order_type (str): 'MARKET' or 'LIMIT'.
            quantity (float): Amount to trade.
            price (float, optional): Price for LIMIT orders.
        Returns:
            dict: Structured response with order_id and price.
        """
        try:
            client_order_id = client_order_id or self._build_client_order_id(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                correlation_id=correlation_id,
            )
            order = self.client.create_order(
                symbol,
                side,
                order_type,
                quantity,
                price,
                client_order_id=client_order_id,
            )

            if not isinstance(order, dict):
                return {
                    "success": False,
                    "error": "Invalid order response",
                    "original_response": order,
                }

            if order.get("error"):
                return {"success": False, "error": order["error"], "original_response": order}

            status = str(order.get("status", "UNKNOWN")).upper()
            if status not in {"FILLED", "PARTIALLY_FILLED", "NEW"}:
                return {
                    "success": False,
                    "error": f"Order not accepted by exchange: status={status}",
                    "status": status,
                    "original_response": order,
                }

            trade_id = str(order.get("orderId", str(uuid.uuid4())[:16]))
            exchange_client_order_id = order.get("clientOrderId") or client_order_id

            exec_qty = float(order.get("executedQty", quantity))

            order_price = price
            if "price" in order and order["price"] and float(order["price"]) > 0:
                order_price = float(order["price"])
            elif "fills" in order and order["fills"]:
                order_price = float(order["fills"][0].get("price", price or 0))

            if not order_price or order_price == 0:
                try:
                    current_price = self.client.get_24h_ticker(symbol).get("lastPrice")
                    if current_price:
                        order_price = float(current_price)
                except Exception:
                    return {
                        "success": False,
                        "error": "Order accepted but execution price could not be determined",
                        "status": status,
                        "original_response": order,
                    }

            order_record = {
                "client_order_id": exchange_client_order_id,
                "order_id": order.get("orderId", trade_id),
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "status": status,
                "quantity": quantity,
                "executed_quantity": exec_qty,
                "price": price,
                "avg_fill_price": order_price,
                "fee": self._extract_fee(order),
                "correlation_id": correlation_id,
                "raw_response": order,
            }
            self.portfolio.upsert_exchange_order(order_record)

            if status in {"FILLED", "PARTIALLY_FILLED"} and exec_qty > 0:
                self.portfolio.add_trade(
                    trade_id=trade_id,
                    symbol=symbol,
                    side=side,
                    quantity=exec_qty,
                    price=order_price,
                    fee=order_record["fee"],
                    order_id=order.get("orderId", trade_id),
                    client_order_id=exchange_client_order_id,
                    correlation_id=correlation_id,
                )

            return {
                "success": True,
                "order_id": order.get("orderId", trade_id),
                "client_order_id": exchange_client_order_id,
                "price": order_price,
                "quantity": exec_qty,
                "side": side,
                "symbol": symbol,
                "status": status,
                "original_response": order,
            }

        except BinanceAPIException as ex:
            return {"success": False, "error": str(ex)}
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def _extract_fee(self, order) -> float:
        """Extract executed commission from Binance fills when present."""
        total_fee = 0.0
        for fill in order.get("fills", []) or []:
            try:
                total_fee += float(fill.get("commission", 0))
            except (TypeError, ValueError):
                continue
        return total_fee

    def get_order_status(self, order_id, symbol):
        """
        Get status of an order via the BinanceAPIClient wrapper
        (includes demo mode, retry logic, and rate-limit accounting).

        Args:
            order_id (int): Binance order ID.
            symbol (str): Trading pair symbol.
        Returns:
            dict: Order status or error info.
        """
        try:
            status = self.client.get_order(symbol=symbol, order_id=int(order_id))
            return status
        except Exception as ex:
            return {"error": str(ex)}

    def cancel_order(self, order_id, symbol):
        """
        Cancel an order.
        Args:
            order_id (int): Binance order ID.
            symbol (str): Trading pair symbol.
        Returns:
            dict: Cancel response or error info.
        """
        try:
            result = self.client.cancel_order(symbol, order_id)
            return result
        except BinanceAPIException as ex:
            return {"error": str(ex)}
        except Exception as ex:
            return {"error": str(ex)}

    def place_buy_order(
        self,
        symbol,
        quantity,
        order_type="MARKET",
        price=None,
        correlation_id=None,
        client_order_id=None,
    ):
        """
        Place a BUY order.
        Args:
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
            quantity (float): Amount to buy.
            order_type (str): 'MARKET' or 'LIMIT'.
            price (float, optional): Price for LIMIT orders.
        Returns:
            dict: Order response or error info.
        """
        return self.place_order(
            symbol,
            "BUY",
            order_type,
            quantity,
            price,
            correlation_id=correlation_id,
            client_order_id=client_order_id,
        )

    def place_sell_order(
        self,
        symbol,
        quantity,
        order_type="MARKET",
        price=None,
        correlation_id=None,
        client_order_id=None,
    ):
        """
        Place a SELL order.
        Args:
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
            quantity (float): Amount to sell.
            order_type (str): 'MARKET' or 'LIMIT'.
            price (float, optional): Price for LIMIT orders.
        Returns:
            dict: Order response or error info.
        """
        return self.place_order(
            symbol,
            "SELL",
            order_type,
            quantity,
            price,
            correlation_id=correlation_id,
            client_order_id=client_order_id,
        )


if __name__ == "__main__":
    agent = TradeExecutionAgent()
    print(agent.place_order("BTCUSDT", "BUY", "MARKET", 0.001))
    print(agent.get_order_status(123456, "BTCUSDT"))
    print(agent.cancel_order(123456, "BTCUSDT"))
