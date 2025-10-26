"""
TradeExecutionAgent: Handles order placement, status, and cancellation via BinanceAPIClient.
"""
from binance_trade_agent.binance_client import BinanceAPIClient
from binance.exceptions import BinanceAPIException

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
            dict: Order response or error info.
        """
        from binance_trade_agent.portfolio_manager import PortfolioManager, Trade
        from datetime import datetime
        try:
            order = self.client.create_order(symbol, side, order_type, quantity, price)
            # Only persist if orderId is present (success)
            if isinstance(order, dict) and order.get('orderId'):
                # Use web_portfolio.db for all trades (shown in dashboard)
                pm = PortfolioManager("/app/data/web_portfolio.db")
                trade_id = str(order.get('orderId'))
                trade = Trade(
                    trade_id=trade_id,
                    symbol=symbol,
                    side=side,
                    quantity=float(order.get('executedQty', quantity)),
                    price=float(order.get('price') or order.get('fills', [{}])[0].get('price', price) or 0),
                    fee=0.0,  # Fee can be parsed from fills if needed
                    timestamp=datetime.now(),
                    order_id=order.get('orderId')
                )
                pm.add_trade(trade)
            return order
        except BinanceAPIException as ex:
            return {'error': str(ex)}
        except Exception as ex:
            return {'error': str(ex)}

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
            return {'error': str(ex)}
        except Exception as ex:
            return {'error': str(ex)}

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
            return {'error': str(ex)}
        except Exception as ex:
            return {'error': str(ex)}

if __name__ == "__main__":
    agent = TradeExecutionAgent()
    print(agent.place_order('BTCUSDT', 'BUY', 'MARKET', 0.001))
    print(agent.get_order_status(123456, 'BTCUSDT'))
    print(agent.cancel_order(123456, 'BTCUSDT'))
