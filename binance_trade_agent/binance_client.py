import os
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException
from .config import config

class BinanceAPIClient:
    """
    Binance API wrapper for price, order book, balance, and order management.
    """

    def __init__(self):
        self.config = config

        if self.config.demo_mode:
            print("⚠️  WARNING: Running in DEMO MODE with mock data. Set BINANCE_API_KEY and BINANCE_API_SECRET for live trading.")
            self.client = None
        else:
            self.client = Client(self.config.binance_api_key, self.config.binance_api_secret)
            # Use testnet for safety unless explicitly disabled
            if self.config.binance_testnet:
                self.client.API_URL = 'https://testnet.binance.vision/api'
                print("🔧 Using Binance Testnet for safe testing")
            else:
                print("🚨 PRODUCTION MODE: Using live Binance API - USE WITH CAUTION!")

    def get_latest_price(self, symbol: str) -> float:
        if self.config.demo_mode:
            # Return mock price data for demo purposes
            mock_prices = {
                'BTCUSDT': 50000.0,
                'ETHUSDT': 3000.0,
                'BNBUSDT': 400.0,
                'ADAUSDT': 0.5,
                'SOLUSDT': 100.0
            }
            return mock_prices.get(symbol, 100.0)

        try:
            response = self.client.get_symbol_ticker(symbol=symbol)
            return float(response['price'])
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise

    def get_order_book(self, symbol: str, limit: int = 10):
        if self.config.demo_mode:
            # Return mock order book data
            base_price = self.get_latest_price(symbol)
            return {
                'bids': [[f"{base_price - i * 0.1:.2f}", f"{10 + i}"] for i in range(min(limit, 5))],
                'asks': [[f"{base_price + i * 0.1:.2f}", f"{10 + i}"] for i in range(min(limit, 5))]
            }

        try:
            response = self.client.get_order_book(symbol=symbol, limit=limit)
            return response
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise

    def get_balance(self, asset: str) -> float:
        if self.config.demo_mode:
            # Return mock balance data
            mock_balances = {
                'BTC': 0.5,
                'ETH': 2.0,
                'USDT': 10000.0,
                'BNB': 10.0,
                'ADA': 1000.0,
                'SOL': 50.0
            }
            return mock_balances.get(asset, 0.0)

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

    def get_24h_ticker(self, symbol: str):
        """
        Get 24-hour ticker price change statistics.
        Returns comprehensive 24h statistics for the symbol.
        """
        if self.config.demo_mode:
            # Return mock 24h ticker data
            base_price = self.get_latest_price(symbol)
            price_change = (base_price * 0.02) * (1 if symbol.startswith('BTC') else -1)  # Mock change
            price_change_percent = (price_change / (base_price - price_change)) * 100
            
            return {
                'symbol': symbol,
                'priceChange': f"{price_change:.2f}",
                'priceChangePercent': f"{price_change_percent:.2f}",
                'weightedAvgPrice': f"{base_price:.2f}",
                'prevClosePrice': f"{base_price - price_change:.2f}",
                'lastPrice': f"{base_price:.2f}",
                'lastQty': "0.00100000",
                'bidPrice': f"{base_price - 0.01:.2f}",
                'bidQty': "10.00000000",
                'askPrice': f"{base_price + 0.01:.2f}",
                'askQty': "10.00000000",
                'openPrice': f"{base_price - price_change:.2f}",
                'highPrice': f"{base_price + price_change * 0.5:.2f}",
                'lowPrice': f"{base_price - price_change * 0.5:.2f}",
                'volume': "1000.00000000",
                'quoteVolume': f"{base_price * 1000:.2f}",
                'openTime': str(int(time.time() * 1000) - 86400000),  # 24h ago
                'closeTime': str(int(time.time() * 1000)),
                'firstId': 1,
                'lastId': 1000,
                'count': 1000
            }

        try:
            ticker = self.client.get_24hr_ticker(symbol=symbol)
            return ticker
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise

    def create_order(self, symbol: str, side: str, order_type: str, quantity: float, price=None):
        if self.config.demo_mode:
            # Return mock order data
            import time
            order_id = int(time.time() * 1000)  # Mock order ID
            return {
                'symbol': symbol,
                'orderId': order_id,
                'orderListId': -1,
                'clientOrderId': f'mock_{order_id}',
                'transactTime': int(time.time() * 1000),
                'price': str(price) if price else '0.00000000',
                'origQty': str(quantity),
                'executedQty': str(quantity),
                'cummulativeQuoteQty': '0.00000000',
                'status': 'FILLED',
                'timeInForce': 'GTC',
                'type': order_type,
                'side': side
            }

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
        if self.config.demo_mode:
            # Return mock cancel result
            return {
                'symbol': symbol,
                'origClientOrderId': f'mock_{order_id}',
                'orderId': order_id,
                'orderListId': -1,
                'clientOrderId': f'mock_{order_id}',
                'price': '0.00000000',
                'origQty': '0.00000000',
                'executedQty': '0.00000000',
                'cummulativeQuoteQty': '0.00000000',
                'status': 'CANCELED',
                'timeInForce': 'GTC',
                'type': 'LIMIT',
                'side': 'BUY'
            }

        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            return result
        except Exception as ex:
            print(f"Binance API error: {ex}")
            raise
