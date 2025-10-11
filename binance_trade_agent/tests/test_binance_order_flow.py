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
    import pytest
    from binance.exceptions import BinanceAPIException
    symbol = "BTCUSDT"
    qty = 0.001

    order = client.create_order(symbol, "BUY", "MARKET", qty)
    assert "orderId" in order
    order_id = order["orderId"]

    status = client.client.get_order(symbol=symbol, orderId=order_id)["status"]

    if status in ("NEW", "PARTIALLY_FILLED"):
        # Cancel should succeed (or raise if already gone)
        try:
            client.cancel_order(symbol, order_id)
        except BinanceAPIException as e:
            # Allow a race where it just got filled before cancel
            assert "Unknown order sent" in str(e)
    else:
        # FILLED orders aren’t cancellable; canceling should raise -2011
        with pytest.raises(BinanceAPIException) as exc:
            client.cancel_order(symbol, order_id)
        assert "Unknown order sent" in str(exc.value)

def test_error_handling_invalid_symbol(client):
    try:
        client.get_latest_price("FAKEUSDT")
    except Exception as ex:
        assert "Invalid symbol" in str(ex)
