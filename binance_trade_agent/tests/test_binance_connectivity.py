import os
import pytest
from binance_trade_agent.binance_client import BinanceAPIClient

def test_binance_connectivity():
    client = BinanceAPIClient()
    # Test connectivity to testnet
    price = client.get_latest_price('BTCUSDT')
    assert price is not None
    assert isinstance(price, float)

    order_book = client.get_order_book('BTCUSDT')
    assert order_book is not None
    assert 'bids' in order_book and 'asks' in order_book

    # Test balance fetch (should work if testnet account is funded)
    balance = client.get_balance('BTC')
    assert balance is not None
    assert isinstance(balance, float)
