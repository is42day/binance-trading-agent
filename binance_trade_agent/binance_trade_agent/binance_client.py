
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException

class BinanceAPIClient:
    """
    Async Binance API wrapper for price, order book, and test connectivity.
    API keys are read from environment variables.
    """


    def __init__(self):
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        if not api_key or not api_secret:
            raise ValueError("Missing BINANCE_API_KEY or BINANCE_API_SECRET in environment!")
        self.client = Client(api_key, api_secret)


    def get_latest_price(self, symbol: str) -> float:
        try:
            response = self.client.get_symbol_ticker(symbol=symbol)
            return float(response['price'])
        except BinanceAPIException as ex:
            print(f"Binance API error: {ex}")
            return None

    def get_order_book(self, symbol: str, limit: int = 10):
        try:
            response = self.client.get_order_book(symbol=symbol, limit=limit)
            return response
        except BinanceAPIException as ex:
            print(f"Binance API error: {ex}")
            return None

    def get_balance(self, asset: str) -> float:
        """
        Retrieve account balance for a given asset, e.g. 'BTC', 'USDT'
        """
        try:
            balances = self.client.get_asset_balance(asset=asset)
            if balances:
                return float(balances['free'])
            else:
                print(f"No balance found for asset {asset}")
                return 0.0
        except BinanceAPIException as ex:
            print(f"Binance API error: {ex}")
            return 0.0

    def create_order(self, symbol: str, side: str, order_type: str, quantity: float, price=None):
        """
        Place a trade order (e.g., MARKET or LIMIT)
        """
        try:
            if order_type == 'MARKET':
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity
                )
            elif order_type == 'LIMIT':
                if price is None:
                    raise ValueError("Limit orders require price")
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    timeInForce='GTC',
                    quantity=quantity,
                    price=str(price)
                )
            else:
                raise ValueError("Unsupported order type")
            return order
        except BinanceAPIException as ex:
            print(f"Binance API error: {ex}")
            return None

    def cancel_order(self, symbol: str, order_id: int):
        """
        Cancel an open order.
        """
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            return result
        except BinanceAPIException as ex:
            print(f"Binance API error: {ex}")
            return None


