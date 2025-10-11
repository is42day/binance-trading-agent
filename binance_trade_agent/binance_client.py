import os
from binance.client import Client
from binance.exceptions import BinanceAPIException

class BinanceAPIClient:
    """
    Binance API wrapper for price, order book, balance, and order management.
    """

    def __init__(self):
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        if not api_key or not api_secret:
            raise ValueError("Missing BINANCE_API_KEY or BINANCE_API_SECRET in environment!")
        self.client = Client(api_key, api_secret)
        # Use Binance testnet endpoints for safe testing
        self.client.API_URL = 'https://testnet.binance.vision/api'

    def get_latest_price(self, symbol: str) -> float:
        try:
            response = self.client.get_symbol_ticker(symbol=symbol)
            return float(response['price'])
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise

    def get_order_book(self, symbol: str, limit: int = 10):
        try:
            response = self.client.get_order_book(symbol=symbol, limit=limit)
            return response
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise

    def get_balance(self, asset: str) -> float:
        try:
            balances = self.client.get_asset_balance(asset=asset)
            if balances:
                return float(balances['free'])
            else:
                print(f"No balance found for asset {asset}")
                return 0.0
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise

    def create_order(self, symbol: str, side: str, order_type: str, quantity: float, price=None):
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
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise

    def cancel_order(self, symbol: str, order_id: int):
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            return result
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise
