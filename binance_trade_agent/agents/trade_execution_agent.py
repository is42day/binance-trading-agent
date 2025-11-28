"""
TradeExecutionAgent: Handles order placement, status, and cancellation via BinanceAPIClient.
"""

from binance.exceptions import BinanceAPIException

from ..clients.binance_client import BinanceAPIClient


class TradeExecutionAgent:
    def __init__(self):
        self.client = BinanceAPIClient()

    def place_order(self, symbol, side, order_type, quantity, price=None):
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
        import uuid

        from ..core.portfolio_manager import PortfolioManager

        try:
            order = self.client.create_order(symbol, side, order_type, quantity, price)

            # Persist trade whether or not orderId is present (for testnet compatibility)
            if isinstance(order, dict):
                # Use web_portfolio.db for all trades (shown in dashboard)
                pm = PortfolioManager("/app/data/web_portfolio.db")

                # Generate a trade ID - use orderId if available, otherwise generate UUID
                trade_id = str(order.get("orderId", str(uuid.uuid4())[:16]))

                # Get executed quantity - fallback to requested quantity if not available
                exec_qty = float(order.get("executedQty", quantity))

                # Get price - try multiple sources
                order_price = price
                if "price" in order and order["price"] and float(order["price"]) > 0:
                    order_price = float(order["price"])
                elif "fills" in order and order["fills"]:
                    order_price = float(order["fills"][0].get("price", price or 0))

                # If price still not found, fetch current market price
                if not order_price or order_price == 0:
                    try:
                        current_price = self.client.get_ticker(symbol).get("lastPrice")
                        if current_price:
                            order_price = float(current_price)
                    except Exception:  # noqa: E722
                        pass  # Use 0 as fallback

                # Call add_trade with individual parameters
                pm.add_trade(
                    trade_id=trade_id,
                    symbol=symbol,
                    side=side,
                    quantity=exec_qty,
                    price=order_price or 0,
                    fee=0.0,  # Fee can be parsed from fills if needed
                    order_id=order.get("orderId", trade_id),
                )

                # Return structured response that includes the extracted price
                return {
                    "order_id": order.get("orderId", trade_id),
                    "price": order_price or 0,
                    "quantity": exec_qty,
                    "side": side,
                    "symbol": symbol,
                    "status": order.get("status", "UNKNOWN"),
                    "original_response": order,
                }

            # If order is not a dict, still try to extract useful info
            return {"error": "Invalid order response", "original_response": order}

        except BinanceAPIException as ex:
            return {"error": str(ex)}
        except Exception as ex:
            return {"error": str(ex)}

    def get_order_status(self, order_id, symbol):
        """
        Get status of an order.
        Args:
            order_id (int): Binance order ID.
            symbol (str): Trading pair symbol.
        Returns:
            dict: Order status or error info.
        """
        try:
            status = self.client.client.get_order(symbol=symbol, orderId=order_id)
            return status
        except BinanceAPIException as ex:
            return {"error": str(ex)}
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

    def place_buy_order(self, symbol, quantity, order_type="MARKET", price=None):
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
        return self.place_order(symbol, "BUY", order_type, quantity, price)

    def place_sell_order(self, symbol, quantity, order_type="MARKET", price=None):
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
        return self.place_order(symbol, "SELL", order_type, quantity, price)


if __name__ == "__main__":
    agent = TradeExecutionAgent()
    print(agent.place_order("BTCUSDT", "BUY", "MARKET", 0.001))
    print(agent.get_order_status(123456, "BTCUSDT"))
    print(agent.cancel_order(123456, "BTCUSDT"))
