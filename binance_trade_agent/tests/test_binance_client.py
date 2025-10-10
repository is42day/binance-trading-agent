def test_get_balance(patched_client):
    balance = patched_client.get_balance("BTC")
    assert balance == 0.1234
    balance_none = patched_client.get_balance("ETH")
    assert balance_none == 0.0

def test_create_order(patched_client):
    order = patched_client.create_order("BTCUSDT", side="BUY", order_type="MARKET", quantity=0.01)
    assert order['orderId'] == 12345
    assert order['status'] == 'FILLED'

def test_cancel_order(patched_client):
    result = patched_client.cancel_order("BTCUSDT", order_id=12345)
    assert result['orderId'] == 12345
    assert result['status'] == 'CANCELED'

# Unit tests for BinanceAPIClient using mocking (sync version)
import pytest
import os
from binance_trade_agent.binance_client import BinanceAPIClient

class DummyClient:
    def get_symbol_ticker(self, symbol):
        return {'price': '42000.00'}

    def get_order_book(self, symbol, limit):
        return {
            'bids': [['42000.0', '1.5']],
            'asks': [['42100.0', '2.1']]
        }

def test_binance_client_get_latest_price(monkeypatch):
    monkeypatch.setenv('BINANCE_API_KEY', 'testkey')
    monkeypatch.setenv('BINANCE_API_SECRET', 'testsecret')
    client = BinanceAPIClient()
    client.client = DummyClient()  # Bypass real init for test
    price = client.get_latest_price("BTCUSDT")
    assert price == 42000.00

def test_binance_client_get_order_book(monkeypatch):
    monkeypatch.setenv('BINANCE_API_KEY', 'testkey')
    monkeypatch.setenv('BINANCE_API_SECRET', 'testsecret')
    client = BinanceAPIClient()
    client.client = DummyClient()
    orderbook = client.get_order_book("BTCUSDT", limit=1)
    assert 'bids' in orderbook and 'asks' in orderbook
    assert float(orderbook['bids'][0][0]) == 42000.0
    assert float(orderbook['asks'][0][0]) == 42100.0
