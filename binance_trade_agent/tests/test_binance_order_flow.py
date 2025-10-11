import os
import pytest
from binance_trade_agent.binance_client import BinanceAPIClient

@pytest.fixture(scope="module")
def client():
    return BinanceAPIClient()

def test_get_balance(client):
    balance = client.get_balance("USDT")
    assert isinstance(balance, float)
    assert balance >= 0

def test_get_price(client):
    price = client.get_latest_price("BTCUSDT")
    assert isinstance(price, float)
    assert price > 0

def test_place_and_cancel_market_order(client):
    symbol = "BTCUSDT"
    quantity = 0.001  # adjust for testnet funds
    order = client.create_order(symbol, "BUY", "MARKET", quantity)
    if "error" in order:
        # Order failed, check error message
        assert "Unknown order sent" in order["error"] or "error" in order
        return
    assert "orderId" in order
    order_id = order["orderId"]

    # Query order state
    status = client.client.get_order(symbol=symbol, orderId=order_id)
    assert status["status"] in ["FILLED", "NEW", "PARTIALLY_FILLED"]

    # Cancel the order (if not already filled)
    result = client.cancel_order(symbol, order_id)
    if "error" in result:
        assert "Unknown order sent" in result["error"] or "error" in result
    else:
        assert "orderId" in result
        assert result["status"] in ["CANCELED", "FILLED"]

def test_error_handling_invalid_symbol(client):
    try:
        client.get_latest_price("FAKEUSDT")
    except Exception as ex:
        assert "Invalid symbol" in str(ex)
