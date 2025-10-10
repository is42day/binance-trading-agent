# tests/test_market_data_agent.py

from binance_trade_agent.market_data_agent import MarketDataAgent

class DummyClient:
    def get_latest_price(self, symbol):
        return 65000.0
    def get_order_book(self, symbol, limit=10):
        return {'bids': [['64990', '1']], 'asks': [['65010', '2']]}
    def get_balance(self, asset):
        return 1000.0

def test_market_data_agent_fetch_price():
    agent = MarketDataAgent(binance_client=DummyClient())
    assert agent.fetch_price("BTCUSDT") == 65000.0

def test_market_data_agent_fetch_order_book():
    agent = MarketDataAgent(binance_client=DummyClient())
    order_book = agent.fetch_order_book("BTCUSDT")
    assert 'bids' in order_book and 'asks' in order_book

def test_market_data_agent_fetch_balance():
    agent = MarketDataAgent(binance_client=DummyClient())
    assert agent.fetch_balance("USDT") == 1000.0
